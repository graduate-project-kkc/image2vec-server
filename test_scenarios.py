import os
import random
import requests
import time
import paramiko
import threading
import traceback
import re
from multiprocessing.pool import ThreadPool, AsyncResult
from requests_toolbelt.multipart.encoder import MultipartEncoder

from src.timer import SimpleTimer

"""
vmstat -t 1
- procs
r = 현재 실행 중인 프로세스 (cpu에 접근 대기 중)
b = io자원을 할당받지 못해서 block된 프로세스
- memory
- swap
si = swap-in (disk -> memory)
so = swap-out (memory -> disk)
- io
bi = block input (블록 장치로부터 입력된 블록 수)
bo = block output (블록 장치로부터 쓰기된 블록 수)
- system
in = 초당 인터럽트
cs = 초당 context switch
- cpu
us = user level 코드 실행%
sy = system level 코드 실행%
id = 100 - us - sy
wa = 디스크 등 IO작업으로 CPU가 대기하는 비율
"""

THIS_TIME = time.time_ns()

# ENDPOINT = "http://52.79.227.178:8080/api/"
# ENDPOINT = "http://127.0.0.1:8000/api/"
# ENDPOINT = "http://13.211.29.27:3000/api/"
ENDPOINT = "http://3.38.180.4:3000/api/"

USE_SCHEDULER = False

if USE_SCHEDULER:
    ENDPOINT_SEARCH = ENDPOINT + "search/batch?query="
    ENDPOINT_UPLOAD = ENDPOINT + "upload/batch"
else:
    ENDPOINT_SEARCH = ENDPOINT + "search?query="
    ENDPOINT_UPLOAD = ENDPOINT + "upload"

# random.seed(1226)

TEST_IMG_DIR = os.path.join(".", "test_images", "ToBeUploaded2")
test_img_list = os.listdir(TEST_IMG_DIR)
for excluded_img in ["20250902_133843.jpg", "20250510_151332.jpg", "20250510_151333.jpg", 
                     "20250510_151335.jpg", "20250510_171121.jpg", "20250425_122634.jpg"]:
    test_img_list.remove(excluded_img)
test_img_list = list(filter(lambda x: os.path.getsize(os.path.join(TEST_IMG_DIR, x)) <= 10*1024*1024, test_img_list)) * 100
random.shuffle(test_img_list)
test_img_iter = iter(test_img_list)

with open("test_images/output.txt", "r", encoding="utf-8") as f:
    test_img_ids = list(map(lambda x: x.strip().split()[-1], f.readlines()))
random.shuffle(test_img_ids)
test_img_id_iter = iter(test_img_ids)

pattern = re.compile(r"^rand(\d+)(half)?_(\d)[.]jpg$")
test_random_image_files = os.listdir(r"C:\Users\frien\Desktop\random_images")
test_random_images = []
for img in test_random_image_files:
    m = pattern.match(img)
    if m:
        size, is_half, idx = m.groups()
        test_random_images.append((int(size), not bool(is_half), int(idx), img))
test_random_images.sort()
test_random_iter = iter(map(lambda x: x[-1], test_random_images))

text_list = """
A man wearing a blue shirt
A man wearing sunglasses
Two cats
A cat sitting on a microwave
A sky half covered with clouds
Three man cooking at the kitchen
A man sitting on the floor and mixing some food in a bowl
Men watching TV
Men standing in a line
A plane wing
People in airport
Pasta
Hamburger
A cat wearing pants
A monkey under the bed
A man wanting banana
A man swimming in the pool
""".strip().split('\n') * 100
random.shuffle(text_list)
text_iter = iter(text_list)

scenario_idx = 0
task_idx = 0

tasks: list[AsyncResult] = []
results = []
timer = SimpleTimer()

HOST = "ec2-3-38-180-4.ap-northeast-2.compute.amazonaws.com"
ID = "ubuntu"
# TODO: modify the path of private key by your local environment
KEY = paramiko.RSAKey.from_private_key_file(r"C:\Users\frien\Desktop\workplace\keys\ai-server.pem")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # WARN: On private PC only
ssh.connect(HOST, username=ID, pkey=KEY)
# sftp = None

print("[SSH] Connection held.")

def init_scenario():
    global scenario_idx, task_idx, tasks
    scenario_idx += 1
    task_idx = 0
    tasks.clear()
    print(f"[Test] Scenario {scenario_idx} start.")
    timer.start()

def _search(query: str):
    try:
        timer = SimpleTimer()
        timer.start()
        with requests.Session() as session:
            response = session.get(ENDPOINT_SEARCH + query)
            et = timer.stop()
            return len(query), timer.t, et, response.status_code, response.content.decode('utf-8')
    except BaseException as e:
        et = timer.stop()
        return len(query), timer.t, 0, -1, f"{e.__class__.__name__}: {e}"

def _upload(imgs: list[str]):
    try:
        timer = SimpleTimer()
        timer.start()
        data = MultipartEncoder([("files", (img, open(os.path.join(TEST_IMG_DIR, img), "rb"), "image/jpeg")) for img in imgs])
        with requests.Session() as session:
            response = session.post(ENDPOINT_UPLOAD, data=data, headers={"Content-Type": data.content_type})
            et = timer.stop()
            return sum(map(len, (open(os.path.join(TEST_IMG_DIR, img), "rb").read() for img in imgs))), \
                timer.t, et, response.status_code, response.content.decode('utf-8')
    except BaseException as e:
        et = timer.stop()
        return sum(map(len, (open(os.path.join(TEST_IMG_DIR, img), "rb").read() for img in imgs))), \
            timer.t, 0, -1, f"{e.__class__.__name__}: {e}"

def search(pool: ThreadPool):
    global task_idx
    task_idx += 1
    query = next(text_iter)
    task = pool.apply_async(_search, (query,))
    tasks.append((task_idx, 't', task))
    return task

def upload(pool: ThreadPool):
    global task_idx
    task_idx += 1
    # img = next(test_img_iter)
    # img = next(test_img_id_iter)
    img = "random_images/" + next(test_random_iter)
    task = pool.apply_async(_upload, ([img],))
    tasks.append((task_idx, 'i', task))
    return task

def search_block(pool: ThreadPool):
    search(pool).wait()

def upload_block(pool: ThreadPool):
    upload(pool).wait()

def wait_results():
    for _, _, task in tasks:
        task.wait()

def end_scenario():
    global results
    task_results = [(scenario_idx, idx, task_type, task.get()) for idx, task_type, task in tasks]
    et = timer.stop()
    print(f"[Test] Scenario {scenario_idx} - {et:.4f} sec.")
    results.append((et, task_results))
    time.sleep(5)


end_log = False

def log_smem(ssh: paramiko.SSHClient, pid: int):
    print(f"[SMEM] SERVER_PID = {pid}")
    
    COMMAND = f"sudo smem -c \"pid swap uss pss\" | grep \"^{pid}\" | awk '{{print systime(), $0}}'"
    
    f = open(f"test_result/{THIS_TIME}_test_smem_log.txt", "w", encoding="utf-8")
    try:
        while not end_log:
            _, stdout, _ = ssh.exec_command(COMMAND.encode("utf-8"), get_pty=True)
            time.sleep(1)
            f.write(stdout.readlines()[0].replace("\r\n", "\n"))
            f.flush()
    except Exception as e:
        print(f"[SMEM] Error: {e.__class__.__name__}: {e}")
    finally:
        f.close()
        print(f"[SMEM] Good bye")

def log_vmstat(ssh: paramiko.SSHClient, pid: int):
    print(f"[VMSTAT] SERVER_PID = {pid}")
    
    COMMAND = f"vmstat -t 1 2"
    
    f = open(f"test_result/{THIS_TIME}_test_vmstat_log.txt", "w", encoding="utf-8")
    try:
        while not end_log:
            _, stdout, _ = ssh.exec_command(COMMAND.encode("utf-8"), get_pty=True)
            time.sleep(1)
            f.write(stdout.readlines()[3].replace("\r\n", "\n"))
            f.flush()
    except Exception as e:
        print(f"[VMSTAT] Error: {e.__class__.__name__}: {e}")
    finally:
        f.close()
        print(f"[VMSTAT] Good bye")

def main_test():
    global scenario_idx, task_idx, tasks, results, timer
    """
    각 시나리오 진행 후 다음 시나리오까지 5초간 대기
    """
    
    assert len(test_random_images) % 5 == 0
    for i, img_id in enumerate(test_random_images):
        if i % 5 == 0:
            init_scenario()
        print("Test images:", img_id)
        with ThreadPool(1) as pool:
            upload_block(pool)
            if i % 5 == 4:
                end_scenario()
    
    return
    
    """
    시나리오 1
    사진 업로드 1장 5번 순차적으로 요청
    """
    
    init_scenario()
    with ThreadPool(1) as pool:
        for _ in range(5):
            upload_block(pool)
        end_scenario()
    
    """
    시나리오 2
    텍스트 검색 5번 순차적으로 요청
    """
    
    init_scenario()
    with ThreadPool(1) as pool:
        for _ in range(5):
            search_block(pool)
        end_scenario()
    
    """
    시나리오 3
    다시 사진 업로드 1장 5번 순차적으로 요청
    """
    
    init_scenario()
    with ThreadPool(1) as pool:
        for _ in range(5):
            upload_block(pool)
        end_scenario()
    
    """
    시나리오 4
    사진 업로드와 텍스트 검색을 번갈아가며 5번씩 순차적으로 요청
    (이전 요청의 결과를 기다림)
    """
    
    init_scenario()
    with ThreadPool(1) as pool:
        for _ in range(5):
            upload_block(pool)
            search_block(pool)
        end_scenario()
    
    """
    시나리오 5
    사진 업로드 또는 텍스트 검색을 랜덤하게 10번 순차적으로 요청
    (이전 요청의 결과를 기다림)
    """
    
    init_scenario()
    with ThreadPool(1) as pool:
        for _ in range(10):
            if random.random() < 0.5:
                upload_block(pool)
            else:
                search_block(pool)
        end_scenario()

    """
    시나리오 6-15
    사진 업로드 1, 2, 3, ..., 9, 10장
    각 시나리오 내 업로드 작업은 병렬로 요청 (이전 요청의 결과를 기다리지 않음)
    """

    img_amount = list(range(1, 11))
    for a in img_amount:
        init_scenario()
        with ThreadPool(10) as pool:
            for _ in range(a):
                upload(pool)
            end_scenario()
    
    return

    """
    시나리오 16-20
    사진 업로드 1, 2, 3, 4, 5장
    각 시나리오 내 업로드 작업은 순차적으로 요청 (이전 요청의 결과를 기다림)
    """
    img_amount = list(range(1, 6))
    for a in img_amount:
        init_scenario()
        with ThreadPool(1) as pool:
            for _ in range(a):
                upload_block(pool)
            end_scenario()

    """
    시나리오 21-30
    사진 업로드 1, 2, 3, ..., 9, 10장
    각 시나리오 내 업로드 작업은 병렬로 요청하되, 이전 요청 이후 5초를 기다림
    """

    img_amount = list(range(1, 11))
    for a in img_amount:
        init_scenario()
        with ThreadPool(10) as pool:
            for _ in range(a):
                upload(pool)
                time.sleep(5)
            end_scenario()

    """
    시나리오 31-40
    텍스트 검색 1, 2, 3, ..., 9, 10번
    각 시나리오 내 검색 작업은 병렬로 요청 (이전 요청의 결과를 기다리지 않음)
    """

    text_amount = list(range(1, 11))
    for a in text_amount:
        init_scenario()
        with ThreadPool(10) as pool:
            for _ in range(a):
                search(pool)
            end_scenario()

    """
    시나리오 41-45
    텍스트 검색 1, 2, 3, 4, 5장
    각 시나리오 내 검색 작업은 순차적으로 요청 (이전 요청의 결과를 기다림)
    """
    text_amount = list(range(1, 6))
    for a in text_amount:
        init_scenario()
        with ThreadPool(1) as pool:
            for _ in range(a):
                search_block(pool)
            end_scenario()

    """
    시나리오 46-55
    텍스트 검색 1, 2, 3, ..., 9, 10번
    각 시나리오 내 검색 작업은 병렬로 요청하되, 이전 요청 이후 0.5초를 기다림
    """

    text_amount = list(range(1, 11))
    for a in text_amount:
        init_scenario()
        with ThreadPool(10) as pool:
            for _ in range(a):
                search(pool)
                time.sleep(0.5)
            end_scenario()

    """
    시나리오 56-80
    이미지 업로드와 텍스트 검색를 동시에 1, 2, 3, 4, 5번 요청
    1번씩 요청 후 딜레이를 0, 1, 2, 3, 5초로 설정
    
    시나리오 #61 : 1번, 0초
    시나리오 #62 : 2번, 0초
    시나리오 #63 : 3번, 0초
    시나리오 #64 : 4번, 0초
    시나리오 #65 : 5번, 0초
    시나리오 #66 : 1번, 1초
    시나리오 #67 : 2번, 1초
    ...
    시나리오 #84 : 4번, 5초
    시나리오 #85 : 5번, 5초
    """

    delay_list = [0, 1, 2, 3, 5]
    rep_list = list(range(1, 6))
    for delay in delay_list:
        for task_rep in rep_list:
            init_scenario()
            with ThreadPool(2 * task_rep) as pool:
                for i in range(task_rep):
                    upload(pool)
                    search(pool)
                    if i < task_rep - 1:
                        time.sleep(delay)
                end_scenario()

    """
    시나리오 81-90
    이미지 업로드 동시 1, 2, 3, ..., 10번 요청,
    모든 요청의 결과를 기다리고 텍스트 검색 1, 2, 3, ..., 10번 요청
    """
    
    amount = list(range(1, 11))
    for a in amount:
        init_scenario()
        with ThreadPool(10) as pool:
            for _ in range(a):
                upload(pool)
            wait_results()
            for _ in range(a):
                search(pool)
            end_scenario()
    
    """
    시나리오 91-100
    이미지 업로드, 텍스트 검색 5번씩 요청
    각 요청은 랜덤한 시간에 전송
    """
    for _ in range(10):
        init_scenario()
        start_time = [0] + [i + random.random() + 0.5 for i in range(9)]
        intervals = [start_time[i + 1] - start_time[i] for i in range(9)] + [0]
        task_order = list("iiiiittttt")
        random.shuffle(task_order)
        with ThreadPool(10) as pool:
            for i, it in enumerate(intervals):
                if task_order[i] == 'i':
                    upload(pool)
                else:
                    search(pool)
                time.sleep(it)
            end_scenario()

def summary_result():
    # Print for analyze with ipynb program
    with open(f"test_result/{THIS_TIME}_test_local_log.txt", "w", encoding="utf-8") as f:
        t_num = 1
        for _, scenario in results:
            for task in scenario:
                s_idx, _, work_type, (data_len, start_timestamp, elapsed_time, status_code, content) = task
                print(f"Task #{s_idx}-{t_num} / {work_type} / {data_len} / {start_timestamp} / {elapsed_time:.4f} sec / "
                        f"{status_code} / {content if len(content) < 150 else content[:150] + '...'}", file=f)
                t_num += 1


    # Summary data
    print("#Scenario | Time taken (sec) | Upload(#task) - Min / Avg / Max (sec) | Search(#task) - Min / Avg / Max (sec)")
    for scenario_time, scenario in results:
        s_num = scenario[0][0]
        stime_min = float('inf')
        stime_max = float('-inf')
        stime_sum = 0
        stime_count = 0
        utime_min = float('inf')
        utime_max = float('-inf')
        utime_sum = 0
        utime_count = 0
        for task in scenario:
            _, _, work_type, (data_len, start_timestamp, elapsed_time, status_code, _) = task
            if status_code != 200:
                continue
            if work_type == 't':
                stime_count += 1
                stime_sum += elapsed_time
                stime_min = min(stime_min, elapsed_time)
                stime_max = max(stime_max, elapsed_time)
            else:
                utime_count += 1
                utime_sum += elapsed_time
                utime_min = min(utime_min, elapsed_time)
                utime_max = max(utime_max, elapsed_time)
        if stime_count == 0:
            stime_str = "( 0)  -------- / -------- / -------- "
        else:
            stime_str = f"({stime_count:>2d})  {stime_min:>8.4f} / {stime_sum/stime_count:>8.4f} / {stime_max:>8.4f} "
        if utime_count == 0:
            utime_str = "( 0)  -------- / -------- / -------- "
        else:
            utime_str = f"({utime_count:>2d})  {utime_min:>8.4f} / {utime_sum/utime_count:>8.4f} / {utime_max:>8.4f} "
        print(f"{s_num:>9d} | {scenario_time:>16.4f} | {utime_str} | {stime_str}")

try:
    stdin, stdout, stderr = ssh.exec_command(b"sudo docker inspect -f \"{{.State.Pid}}\" ai-server\n", get_pty=True)
    while not stdout.channel.exit_status_ready():
        time.sleep(0.1)

    SERVER_PID = int(stdout.read().strip())
    print(f"[SSH] SERVER_PID = {SERVER_PID}")
    
    th_smem = threading.Thread(target=log_smem, args=(ssh, SERVER_PID))
    th_vmstat = threading.Thread(target=log_vmstat, args=(ssh, SERVER_PID))
    
    th_smem.start()
    th_vmstat.start()
    
    print("[Test] starting in 5 sec.")
    time.sleep(5)
    
    main_test()
    summary_result()
    print("[Test] finished.")
    
    print("[SSH] Set a flag for stopping log in 5 sec and waiting to join.")
    time.sleep(5)
    
    end_log = True
    th_smem.join()
    th_vmstat.join()

except Exception as e:
    print(f"[Error] {e.__class__.__name__}: {e}")

finally:
    if not stdin.closed:
        stdin.close()
    ssh.close()

    print("[SSH] Connection closed.")
    pass
