import os
import requests

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from pydantic import BaseModel

from .core import Model
from .pincone_db import PineconeDB, API_KEY, ENVIRONMENT, INDEX_NAME

app = FastAPI()

model = Model()

db = PineconeDB(API_KEY, ENVIRONMENT, INDEX_NAME)

s3_URL = os.getenv("S3_URL")
SPECIAL_KEY = os.getenv("SPECIAL_KEY")  # Temporary authentication key

class UploadItem(BaseModel):
    image_id: str

@app.get("/api/count")
def api_get_uploaded_images():
    return JSONResponse(content={"count": db.count()})

@app.post("/api/upload")
def api_upload_image(item: UploadItem):
    image_id = item.image_id
    with requests.get(s3_URL + image_id) as response:
        if response.status_code != 200:
            return JSONResponse(content={"result": "failed", "error_msg": "Error on communicating to image server."})
        data = response.content
    vector = model.get_image_vector(data)
    try:
        db.push(image_id, vector)
    except ValueError as e:
        return JSONResponse(content={"result": "failed", "error_msg": f"{type(e)}: {e}"})
    return JSONResponse(content={"result": "success"})

@app.get("/api/search")
def api_search(query: str):
    try:
        feature = model.get_text_vector(query)
        return JSONResponse(content={"status": "success", "vector": feature.tolist()})
    except Exception as e:
        return JSONResponse(content={"status": "failed", "error_msg": f"{type(e)}: {e}"})
