import os
import random
import requests
import time
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

ENDPOINT_SEARCH = "http://52.79.227.178:8080/api/search?query="
ENDPOINT_UPLOAD = "http://52.79.227.178:8080/api/images"

# random.seed(1226)

TEST_IMG_DIR = os.path.join(".", "test_images", "ToBeUploaded2")
test_img_list = os.listdir(TEST_IMG_DIR)
for excluded_img in ["20250902_133843.jpg", "20250510_151332.jpg", "20250510_151333.jpg", 
                     "20250510_151335.jpg", "20250510_171121.jpg", "20250425_122634.jpg"]:
    test_img_list.remove(excluded_img)
test_img_list = list(filter(lambda x: os.path.getsize(os.path.join(TEST_IMG_DIR, x)) <= 10*1024*1024, test_img_list)) * 100
random.shuffle(test_img_list)
test_img_iter = iter(test_img_list)

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

def init_scenario():
    global scenario_idx, task_idx, tasks
    scenario_idx += 1
    task_idx = 0
    tasks.clear()
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
    img = next(test_img_iter)
    task = pool.apply_async(_upload, ([img],))
    tasks.append((task_idx, 'i', task))
    return task

def get_result():
    global results
    task_results = [(scenario_idx, idx, task_type, task.get()) for idx, task_type, task in tasks]
    results.append((timer.stop(), task_results))

"""
시나리오 1-15
사진 업로드 1, 1, 1, 1, 1, 1, 2, 3, ..., 9, 10장
각 시나리오 내 업로드 작업은 병렬로 요청 (이전 요청의 결과를 기다리지 않음)
"""

img_amount = [1]*5 + list(range(1, 11))
for a in img_amount:
    init_scenario()
    with ThreadPool(10) as pool:
        for _ in range(a):
            upload(pool)
        get_result()

"""
시나리오 16-30
사진 업로드 1, 1, 1, 1, 1, 1, 2, 3, ..., 9, 10장
각 시나리오 내 업로드 작업은 병렬로 요청하되, 이전 요청 이후 1초를 기다림
"""

img_amount = [1]*5 + list(range(1, 11))
for a in img_amount:
    init_scenario()
    with ThreadPool(10) as pool:
        for _ in range(a):
            upload(pool)
            time.sleep(1)
        get_result()

"""
시나리오 31-45
텍스트 검색 1, 1, 1, 1, 1, 1, 2, 3, ..., 9, 10번
각 시나리오 내 검색 작업은 병렬로 요청 (이전 요청의 결과를 기다리지 않음)
"""

text_amount = [1]*5 + list(range(1, 11))
for a in text_amount:
    init_scenario()
    with ThreadPool(10) as pool:
        for _ in range(a):
            search(pool)
        get_result()

"""
시나리오 46-60
텍스트 검색 1, 1, 1, 1, 1, 1, 2, 3, ..., 9, 10번
각 시나리오 내 검색 작업은 병렬로 요청하되, 이전 요청 이후 1초를 기다림
"""

text_amount = [1]*5 + list(range(1, 11))
for a in text_amount:
    init_scenario()
    with ThreadPool(10) as pool:
        for _ in range(a):
            search(pool)
            time.sleep(1)
        get_result()

"""
시나리오 61-65
이미지 업로드와 텍스트 검색을 5번 번갈아 가며 수행
각 요청간 딜레이를 0, 1, 2, 3, 5초로 설정
"""

delay_list = [0, 1, 2, 3, 5]
for delay in delay_list:
    init_scenario()
    with ThreadPool(10) as pool:
        for i in range(5):
            upload(pool)
            time.sleep(delay)
            search(pool)
            if i < 4:
                time.sleep(delay)
        get_result()


# Print for analyze with ipynb program
with open(f"{time.time_ns()}_test_local_log.txt", "w", encoding="utf-8") as f:
    t_num = 1
    for _, scenario in results:
        for task in scenario:
            s_idx, _, work_type, (data_len, start_timestamp, elapsed_time, status_code, content) = task
            print(f"Task #{scenario_idx}-{t_num} / {work_type} / {data_len} / {start_timestamp} / {elapsed_time:.4f} sec / "
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
        if status_code == 200:
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
        stime_str = f"({stime_count:>2d})  {stime_min:>8.5f} / {stime_sum/stime_count:>8.5f} / {stime_max:>8.5f} "
    if utime_count == 0:
        utime_str = "( 0)  -------- / -------- / -------- "
    else:
        utime_str = f"({utime_count:>2d})  {utime_min:>8.5f} / {utime_sum/utime_count:>8.5f} / {utime_max:>8.5f} "
    print(f"{s_num:>9d} | {scenario_time:>16.4f} | {utime_str} | {stime_str}")
