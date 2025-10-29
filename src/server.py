import os
import requests
import logging
import click
import threading

from uvicorn.logging import AccessFormatter, DefaultFormatter

from contextlib import asynccontextmanager
from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse

from .core import Model
from .pincone_db import PineconeDB, API_KEY, ENVIRONMENT, INDEX_NAME
from .timer import SimpleTimer
from .scheduler import TaskQueue

logger = logging.getLogger()

model = Model(logger)

task_queue = TaskQueue(model.get_image_vectors, model.get_text_vectors)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # When service starts
    
    uvicorn_logger = logging.getLogger("uvicorn.access")
    console_formatter = AccessFormatter("[{asctime}]  {levelprefix}{client_addr} - {request_line} {status_code}", style='{', use_colors=True)
    uvicorn_logger.handlers[0].setFormatter(console_formatter)
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(DefaultFormatter(
        "[{asctime}]  {levelprefix}{message}", style='{', use_colors=True
    ))
    logger.setLevel(logging.INFO)
    logger.addHandler(stream_handler)
    
    task_queue.start()
    
    yield
    # When service ends

app = FastAPI(lifespan=lifespan)

db = PineconeDB(API_KEY, ENVIRONMENT, INDEX_NAME)

s3_URL = os.getenv("S3_URL")
SPECIAL_KEY = os.getenv("SPECIAL_KEY")  # Temporary authentication key

def upload_to_db(image_id: str):
    timer = SimpleTimer()
    timer.start()
    with requests.get(s3_URL + image_id) as response:
        if response.status_code != 200:
            return {"image_id": image_id, "status": "failed", "error_msg": f"Error on communicating to image server - {response.status_code}"}
        data = response.content
    elapsed = timer.stop()
    logger.info(f"[{threading.get_ident()} - Upload] Loaded data of {image_id} from ImgDB ({elapsed:.3f} sec)")
    timer.start()
    vector = model.get_image_vector(data)
    elapsed = timer.stop()
    logger.info(f"[{threading.get_ident()} - Upload] Computed feature vector of {image_id} ({elapsed:.3f} sec)")
    timer.start()
    try:
        db.push(image_id, vector)
    except ValueError as e:
        return {"image_id": image_id, "status": "failed", "error_msg": f"{type(e)}: {e}"}
    elapsed = timer.stop()
    logger.info(f"[{threading.get_ident()} - Upload] Uploaded feature vector of {image_id} ({elapsed:.3f} sec)")
    return {"image_id": image_id, "status": "success"}

# def upload_batch_to_db(image_ids: list[str]):
#     result_id = {id_: None for id_ in image_ids}
#     timer = SimpleTimer()
#     timer.start()
#     image_id_order = []
#     image_datas = []
#     str_of_images = ", ".join([image_id[:5] for image_id in image_ids])
#     for image_id in image_ids:
#         with requests.get(s3_URL + image_id) as response:
#             if response.status_code != 200:
#                 result_id[image_id] = {"image_id": image_id, "status": "failed", "error_msg": f"Error on communicating to image server - {response.status_code}"}
#                 continue
#             data = response.content
#         image_id_order.append(image_id)
#         image_datas.append(data)
#     elapsed = timer.stop()
#     logger.info(f"[{threading.get_ident()} - Uploads] Loaded datas of {str_of_images} from ImgDB ({elapsed:.3f} sec)")
#     timer.start()
#     queue_items = [task_queue.put_image(image_data) for image_data in image_datas]
#     vectors = [item.get_result() for item in queue_items]
#     elapsed = timer.stop()
#     logger.info(f"[{threading.get_ident()} - Uploads] Computed feature vectors of {str_of_images} ({elapsed:.3f} sec)")
#     timer.start()
#     for image_id, vector in zip(image_id_order, vectors):
#         try:
#             db.push(image_id, vector.reshape((1, -1)))
#             result_id[image_id] = {"image_id": image_id, "status": "success"}
#         except ValueError as e:
#             result_id[image_id] = {"image_id": image_id, "status": "failed", "error_msg": f"{type(e)}: {e}"}
#     elapsed = timer.stop()
#     logger.info(f"[{threading.get_ident()} - Uploads] Uploaded feature vectors of {str_of_images} ({elapsed:.3f} sec)")
#     return result_id

def upload_batch_to_db(image_id: str):
    timer = SimpleTimer()
    timer.start()
    with requests.get(s3_URL + image_id) as response:
        if response.status_code != 200:
            return {"image_id": image_id, "status": "failed", "error_msg": f"Error on communicating to image server - {response.status_code}"}
        data = response.content
    elapsed = timer.stop()
    logger.info(f"[{threading.get_ident()} - Upload] Loaded data of {image_id} from ImgDB ({elapsed:.3f} sec)")
    timer.start()
    vector = task_queue.put_image(data).get_result()
    elapsed = timer.stop()
    logger.info(f"[{threading.get_ident()} - Upload] Computed feature vector of {image_id} ({elapsed:.3f} sec)")
    timer.start()
    try:
        db.push(image_id, vector.reshape((1, -1)))
    except ValueError as e:
        return {"image_id": image_id, "status": "failed", "error_msg": f"{type(e)}: {e}"}
    elapsed = timer.stop()
    logger.info(f"[{threading.get_ident()} - Upload] Uploaded feature vector of {image_id} ({elapsed:.3f} sec)")
    return {"image_id": image_id, "status": "success"}

@app.get("/api/count")
def api_get_uploaded_images():
    logger.info(f"[{threading.get_ident()}] ====== /api/count ======", extra={"color_message": f"[{threading.get_ident()}] ====== {click.style('/api/count', bold=True)} ======"})
    content = {"count": db.count()}
    logger.info(f"[{threading.get_ident()}] VecDB count = {content['count']}")
    return JSONResponse(content=content)

@app.post("/api/upload")
def api_upload_image(image_ids: list[str] = Body(...)):
    logger.info(f"[{threading.get_ident()}] ====== /api/upload ======", extra={"color_message": f"[{threading.get_ident()}] ====== {click.style('/api/upload', bold=True)} ======"})
    resp_json = {"status": {"success": 0, "failed": 0}, "results": []}
    timer = SimpleTimer()
    timer.start()
    subtimer = SimpleTimer()
    for image_id in image_ids:
        subtimer.start()
        result = upload_to_db(image_id)
        elapsed = subtimer.stop()
        logger.info(f"[{threading.get_ident()}] Uploaded {image_id} to VecDB : {result.get('error_msg', 'Success')} ({elapsed:.3f} sec)")
        resp_json["results"].append(result)
        resp_json["status"][result["status"]] += 1
    elapsed = timer.stop()
    logger.info(f"[{threading.get_ident()}] Uploaded images to VecDB : "
                f"Total {resp_json['status']['success']} success, {resp_json['status']['failed']} failed "
                f"({elapsed:.3f} sec)")
    return JSONResponse(content=resp_json)

@app.post("/api/upload/batch")
def api_upload_image_multiple(image_ids: list[str] = Body(...)):
    logger.info(f"[{threading.get_ident()}] ====== /api/upload/batch ======", extra={"color_message": f"[{threading.get_ident()}] ====== {click.style('/api/upload/batch', bold=True)} ======"})
    # resp_json = {"status": {"success": 0, "failed": 0}, "results": []}
    # timer = SimpleTimer()
    # timer.start()
    # result = upload_batch_to_db(image_ids)
    # for res in result.values():
    #     resp_json["results"].append(res)
    #     resp_json["status"][res["status"]] += 1
    # elapsed = timer.stop()
    # logger.info(f"[{threading.get_ident()}] Uploaded images to VecDB : "
    #             f"Total {resp_json['status']['success']} success, {resp_json['status']['failed']} failed "
    #             f"({elapsed:.3f} sec)")
    # return JSONResponse(content=resp_json)
    resp_json = {"status": {"success": 0, "failed": 0}, "results": []}
    timer = SimpleTimer()
    timer.start()
    subtimer = SimpleTimer()
    for image_id in image_ids:
        subtimer.start()
        result = upload_batch_to_db(image_id)
        elapsed = subtimer.stop()
        logger.info(f"[{threading.get_ident()}] Uploaded {image_id} to VecDB : {result.get('error_msg', 'Success')} ({elapsed:.3f} sec)")
        resp_json["results"].append(result)
        resp_json["status"][result["status"]] += 1
    elapsed = timer.stop()
    logger.info(f"[{threading.get_ident()}] Uploaded images to VecDB : "
                f"Total {resp_json['status']['success']} success, {resp_json['status']['failed']} failed "
                f"({elapsed:.3f} sec)")
    return JSONResponse(content=resp_json)

@app.get("/api/search")
def api_search(query: str):
    logger.info(f"[{threading.get_ident()}] ====== /api/search ======", extra={"color_message": f"[{threading.get_ident()}] ====== {click.style('/api/search', bold=True)} ======"})
    try:
        timer = SimpleTimer()
        timer.start()
        feature = model.get_text_vector(query)
        feature = feature.reshape((-1,)).tolist()
        resp_json = {"status": "success", "vector": feature}
        elapsed = timer.stop()
        feature_string = ", ".join([f"{v:.3f}" for v in (0, 1, 2)] + ["... "] + [f"{feature[-1]:.3f}"])
        logger.info(f"[{threading.get_ident()}] Response text vector : \"{query}\" => (Success, {elapsed:.3f} sec) [{feature_string}]")
        return JSONResponse(content=resp_json)
    except Exception as e:
        resp_json = {"status": "failed", "error_msg": f"{type(e)}: {e}"}
        logger.info(f"[{threading.get_ident()}] Response text vector : \"{query}\" => (Failed) {resp_json['error_msg']}")
        return JSONResponse(content=resp_json)

@app.get("/api/search/batch")
def api_search_multiple(query: str):
    logger.info(f"[{threading.get_ident()}] ====== /api/search/batch ======", extra={"color_message": f"[{threading.get_ident()}] ====== {click.style('/api/search/batch', bold=True)} ======"})
    try:
        timer = SimpleTimer()
        timer.start()
        feature = task_queue.put_text(query).get_result()
        feature = feature.reshape((-1,)).tolist()
        resp_json = {"status": "success", "vector": feature}
        elapsed = timer.stop()
        feature_string = ", ".join([f"{v:.3f}" for v in (0, 1, 2)] + ["... "] + [f"{feature[-1]:.3f}"])
        logger.info(f"[{threading.get_ident()}] Response text vector : \"{query}\" => (Success, {elapsed:.3f} sec) [{feature_string}]")
        return JSONResponse(content=resp_json)
    except Exception as e:
        resp_json = {"status": "failed", "error_msg": f"{type(e)}: {e}"}
        logger.info(f"[{threading.get_ident()}] Response text vector : \"{query}\" => (Failed) {resp_json['error_msg']}")
        return JSONResponse(content=resp_json)
