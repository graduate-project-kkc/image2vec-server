import os
import requests

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .core import Model
from .pincone_db import PineconeDB, API_KEY, ENVIRONMENT, INDEX_NAME

app = FastAPI()

model = Model()

db = PineconeDB(API_KEY, ENVIRONMENT, INDEX_NAME)

s3_URL = os.getenv("S3_URL")

@app.get("/api/count")
def api_get_uploaded_images():
    return JSONResponse(content={"count": db.count()})

@app.post("/api/upload")
def api_upload_image(filename: str, image_id: str):
    with requests.get(s3_URL + image_id) as response:
        if response.status_code != 200:
            return JSONResponse(content={"result": "failed", "error_msg": "Error on communicating to image server."})
        data = response.content()
    vector = model.get_image_vector(data)
    try:
        db.push(filename, vector)
    except ValueError as e:
        return JSONResponse(content={"result": "failed", "error_msg": f"{type(e)}: {e}"})
    return JSONResponse(content={"result": "success"})

@app.get("/api/search")
def api_search(text: str):
    try:
        feature = model.get_text_vector(text)
        image_indices = db.search(feature)
        result = [x[1] for x in image_indices]
        return JSONResponse(content={"status": "success", "image_ids": result})
    except Exception as e:
        return JSONResponse(content={"status": "failed", "error_msg": f"{type(e)}: {e}"})
