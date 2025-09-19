import os
import random
import requests
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

random.seed(1226)

TEST_IMG_DIR = os.path.join(".", "test_images", "ToBeUploaded2")
test_img_list = os.listdir(TEST_IMG_DIR)
for excluded_img in ["20250902_133843.jpg", "20250510_151332.jpg", "20250510_151333.jpg", 
                     "20250510_151335.jpg", "20250510_171121.jpg", "20250425_122634.jpg"]:
    test_img_list.remove(excluded_img)
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
""".strip().split('\n')
random.shuffle(text_list)
text_iter = iter(text_list)

task_idx = 0



def search(query: str):
    try:
        global task_idx
        task_idx += 1
        my_task_id = task_idx
        timer = SimpleTimer()
        timer.start()
        with requests.Session() as session:
            response = session.get(ENDPOINT_SEARCH + query)
            return my_task_id, query, timer.stop(), response.status_code, response.content.decode('utf-8')
    except BaseException as e:
        return my_task_id, query, timer.stop(), -1, f"{e.__class__.__name__}: {e}"

def upload(imgs):
    try:
        global task_idx
        task_idx += 1
        my_task_id = task_idx
        timer = SimpleTimer()
        timer.start()
        data = MultipartEncoder([("files", (img, open(os.path.join(TEST_IMG_DIR, img), "rb"), "image/jpeg")) for img in imgs])
        with requests.Session() as session:
            response = session.post(ENDPOINT_UPLOAD, data=data, headers={"Content-Type": data.content_type})
            return my_task_id, imgs, timer.stop(), response.status_code, response.content.decode('utf-8')
    except BaseException as e:
        return my_task_id, imgs, 0, -1, f"{e.__class__.__name__}: {e}"

timer = SimpleTimer()

def callback(args):
    task_id, data, elapsed_time, status_code, content = args
    print(f"Task #{task_id} {data} : {elapsed_time:.4f} sec / {status_code} / {content if len(content) < 150 else content[:150] + '...'}")

print("""
시나리오 1
- 사진 1장 업로드
""")

with ThreadPool(processes=1) as pool:
    img = next(test_img_iter)
    pool.apply_async(upload, ([img],), callback=callback).wait()

print("""
시나리오 2
- 텍스트 검색 1번
""")

with ThreadPool(processes=1) as pool:
    text = next(text_iter)
    pool.apply_async(search, (text,), callback=callback).wait()

print("""
시나리오 3
- 시나리오 2를 완료하고 이어서
- 텍스트 검색 1번
""")

with ThreadPool(processes=1) as pool:
    text = next(text_iter)
    pool.apply_async(search, (text,), callback=callback).wait()

print("""
시나리오 4
- 시나리오 3을 완료하고 이어서
- 사진 1장 업로드
- 이전 요청 결과를 기다리고 텍스트 검색 1번
""")

with ThreadPool(processes=1) as pool:
    img = next(test_img_iter)
    pool.apply_async(upload, ([img],), callback=callback).wait()
    text = next(text_iter)
    pool.apply_async(search, (text,), callback=callback).wait()

print("""
시나리오 5
- 사진을 연속으로 5장 업로드
""")

async_results = []
with ThreadPool(processes=5) as pool:
    for _ in range(5):
        img = next(test_img_iter)
        async_results.append(pool.apply_async(upload, ([img],), callback=callback))
    for r in async_results:
        r.wait()

print("""
시나리오 6
- 다음을 5번 반복
  - 이전 요청 결과를 기다리고 텍스트 검색 1번
  - 이전 요청 결과를 기다리고 사진 1장 업로드
""")

with ThreadPool(processes=1) as pool:
    for _ in range(5):
        text = next(text_iter)
        pool.apply_async(search, (text,), callback=callback).wait()
        img = next(test_img_iter)
        pool.apply_async(upload, ([img],), callback=callback).wait()

print("""
시나리오 7
- 다음을 3번 반복
  - 텍스트 검색 1번
  - 사진 1장 업로드
""")

async_results = []
with ThreadPool(processes=6) as pool:
    for _ in range(3):
        img = next(test_img_iter)
        async_results.append(pool.apply_async(upload, ([img],), callback=callback))
        text = next(text_iter)
        async_results.append(pool.apply_async(search, (text,), callback=callback))
    for r in async_results:
        r.wait()
