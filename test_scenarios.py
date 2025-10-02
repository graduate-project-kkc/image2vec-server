import os
import random
import requests
import time
from multiprocessing.pool import ThreadPool
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
test_img_list = list(filter(lambda x: os.path.getsize(os.path.join(TEST_IMG_DIR, x)) <= 10*1024*1024, test_img_list))
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

def search(scenario_idx: int, task_idx: int, query: str):
    try:
        timer = SimpleTimer()
        timer.start()
        with requests.Session() as session:
            response = session.get(ENDPOINT_SEARCH + query)
            et = timer.stop()
            return scenario_idx, task_idx, "text", len(query), timer.t, et, response.status_code, response.content.decode('utf-8')
    except BaseException as e:
        et = timer.stop()
        return scenario_idx, task_idx, "text", len(query), timer.t, 0, -1, f"{e.__class__.__name__}: {e}"

def upload(scenario_idx: int, task_idx: int, imgs):
    try:
        timer = SimpleTimer()
        timer.start()
        data = MultipartEncoder([("files", (img, open(os.path.join(TEST_IMG_DIR, img), "rb"), "image/jpeg")) for img in imgs])
        with requests.Session() as session:
            response = session.post(ENDPOINT_UPLOAD, data=data, headers={"Content-Type": data.content_type})
            et = timer.stop()
            return scenario_idx, task_idx, "image", sum(map(len, (open(os.path.join(TEST_IMG_DIR, img), "rb").read() for img in imgs))), \
                timer.t, et, response.status_code, response.content.decode('utf-8')
    except BaseException as e:
        et = timer.stop()
        return scenario_idx, task_idx, "image", sum(map(len, (open(os.path.join(TEST_IMG_DIR, img), "rb").read() for img in imgs))), \
            timer.t, 0, -1, f"{e.__class__.__name__}: {e}"

timer = SimpleTimer()

def callback(args):
    scenario_idx, task_id, work_type, data, start_timestamp, elapsed_time, status_code, content = args
    print(f"Task #{scenario_idx}-{task_id} / {work_type} / {data} / {start_timestamp} / {elapsed_time:.4f} sec / "
          f"{status_code} / {content if len(content) < 150 else content[:150] + '...'}")

scenario_idx += 1
print("""
시나리오 1
- 사진 1장 업로드
""")

with ThreadPool(processes=1) as pool:
    img = next(test_img_iter)
    task_idx += 1
    pool.apply_async(upload, (scenario_idx, task_idx, [img],), callback=callback).wait()

time.sleep(5)

scenario_idx += 1
print("""
시나리오 2
- 텍스트 검색 1번
""")

with ThreadPool(processes=1) as pool:
    text = next(text_iter)
    task_idx += 1
    pool.apply_async(search, (scenario_idx, task_idx, text,), callback=callback).wait()

time.sleep(5)

scenario_idx += 1
print("""
시나리오 3
- 시나리오 2를 완료하고 이어서
- 텍스트 검색 1번
""")

with ThreadPool(processes=1) as pool:
    text = next(text_iter)
    task_idx += 1
    pool.apply_async(search, (scenario_idx, task_idx, text,), callback=callback).wait()

time.sleep(5)

scenario_idx += 1
print("""
시나리오 4
- 시나리오 3을 완료하고 이어서
- 사진 1장 업로드
- 이전 요청 결과를 기다리고 텍스트 검색 1번
""")

with ThreadPool(processes=1) as pool:
    img = next(test_img_iter)
    task_idx += 1
    pool.apply_async(upload, (scenario_idx, task_idx, [img],), callback=callback).wait()
    text = next(text_iter)
    task_idx += 1
    pool.apply_async(search, (scenario_idx, task_idx, text,), callback=callback).wait()

time.sleep(5)

scenario_idx += 1
print("""
시나리오 5
- 사진을 연속으로 5장 업로드
""")

async_results = []
with ThreadPool(processes=5) as pool:
    for _ in range(5):
        img = next(test_img_iter)
        task_idx += 1
        async_results.append(pool.apply_async(upload, (scenario_idx, task_idx, [img],), callback=callback))
    for r in async_results:
        r.wait()

time.sleep(5)

scenario_idx += 1
print("""
시나리오 6
- 다음을 5번 반복
  - 사진 1장 업로드 후 기다림
""")

with ThreadPool(processes=1) as pool:
    for _ in range(5):
        img = next(test_img_iter)
        task_idx += 1
        pool.apply_async(upload, (scenario_idx, task_idx, [img],), callback=callback).wait()

time.sleep(5)

scenario_idx += 1
print("""
시나리오 7
- 텍스트 연속 10번 검색
""")

async_results = []
with ThreadPool(processes=10) as pool:
    for _ in range(10):
        text = next(text_iter)
        task_idx += 1
        async_results.append(pool.apply_async(search, (scenario_idx, task_idx, text,), callback=callback))
    for r in async_results:
        r.wait()

time.sleep(5)

scenario_idx += 1
print("""
시나리오 8
- 다음을 10번 반복
  - 텍스트 1번 검색 후 기다림
""")

with ThreadPool(processes=10) as pool:
    for _ in range(10):
        text = next(text_iter)
        task_idx += 1
        pool.apply_async(search, (scenario_idx, task_idx, text,), callback=callback).wait()

time.sleep(5)

scenario_idx += 1
print("""
시나리오 9
- 다음을 5번 반복
  - 이전 요청 결과를 기다리고 텍스트 검색 1번
  - 이전 요청 결과를 기다리고 사진 1장 업로드
""")

with ThreadPool(processes=1) as pool:
    for _ in range(5):
        text = next(text_iter)
        task_idx += 1
        pool.apply_async(search, (scenario_idx, task_idx, text,), callback=callback).wait()
        img = next(test_img_iter)
        task_idx += 1
        pool.apply_async(upload, (scenario_idx, task_idx, [img],), callback=callback).wait()

time.sleep(5)

scenario_idx += 1
print("""
시나리오 10
- 다음을 3번 반복
  - 텍스트 검색 1번
  - 사진 1장 업로드
""")

async_results = []
with ThreadPool(processes=6) as pool:
    for _ in range(3):
        img = next(test_img_iter)
        task_idx += 1
        async_results.append(pool.apply_async(upload, (scenario_idx, task_idx, [img],), callback=callback))
        text = next(text_iter)
        task_idx += 1
        async_results.append(pool.apply_async(search, (scenario_idx, task_idx, text,), callback=callback))
    for r in async_results:
        r.wait()
