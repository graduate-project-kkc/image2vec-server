import os
import requests
import time
import logging
import click

from uvicorn.logging import AccessFormatter, DefaultFormatter

from contextlib import asynccontextmanager
from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse

from .core import Model
from .pincone_db import PineconeDB, API_KEY, ENVIRONMENT, INDEX_NAME

logger = logging.getLogger()

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
    logger.setLevel(logging.DEBUG)
    logger.addHandler(stream_handler)
    
    yield
    # When service ends

app = FastAPI(lifespan=lifespan)

model = Model()

db = PineconeDB(API_KEY, ENVIRONMENT, INDEX_NAME)

s3_URL = os.getenv("S3_URL")
SPECIAL_KEY = os.getenv("SPECIAL_KEY")  # Temporary authentication key

def upload_to_db(image_id):
    with requests.get(s3_URL + image_id) as response:
        if response.status_code != 200:
            return {"status": "failed", "error_msg": "Error on communicating to image server."}
        data = response.content
    vector = model.get_image_vector(data)
    try:
        db.push(image_id, vector)
    except ValueError as e:
        return {"status": "failed", "error_msg": f"{type(e)}: {e}"}
    return {"status": "success"}

@app.get("/api/count")
def api_get_uploaded_images():
    logger.info("====== /api/count ======", extra={"color_message": f"====== {click.style('/api/count', bold=True)} ======"})
    content = {"count": db.count()}
    logger.info(f"VecDB count = {content['count']}")
    return JSONResponse(content=content)

@app.post("/api/upload")
def api_upload_image(image_ids: list[str] = Body(...)):
    logger.info("====== /api/upload ======", extra={"color_message": f"====== {click.style('/api/upload', bold=True)} ======"})
    resp_json = {"status": {"success": 0, "failed": 0}, "results": []}
    ttime = 0
    for image_id in image_ids:
        dtime = time.time()
        result = upload_to_db(image_id)
        dtime = time.time() - dtime
        ttime += dtime
        logger.info(f"Uploaded {image_id} to VecDB : {result.get('error_msg', 'Success')} ({dtime:.3f} seconds)")
        resp_json["results"].append(result)
        resp_json["status"][result["status"]] += 1
    logger.info(f"Uploaded images to VecDB : "
                f"Total {resp_json['status']['success']} success, {resp_json['status']['failed']} failed"
                f"({ttime:.3f} seconds)")
    return JSONResponse(content=resp_json)

@app.get("/api/search")
def api_search(query: str):
    logger.info("====== /api/search ======", extra={"color_message": f"====== {click.style('/api/search', bold=True)} ======"})
    try:
        dtime = time.time()
        feature = model.get_text_vector(query)
        feature = feature.reshape((-1,)).tolist()
        resp_json = {"status": "success", "vector": feature}
        dtime = time.time() - dtime
        feature_string = ", ".join([f"{v:.3f}" for v in (0, 1, 2)] + ["... "] + [f"{feature[-1]:.3f}"])
        logger.info(f"Response text vector : \"{query}\" => (Success) [{feature_string}]")
        return JSONResponse(content=resp_json)
    except Exception as e:
        resp_json = {"status": "failed", "error_msg": f"{type(e)}: {e}"}
        logger.info(f"Response text vector : \"{query}\" => (Failed) {resp_json['error_msg']}")
        return JSONResponse(content=resp_json)
