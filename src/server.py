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
            resp_json = {"status": "failed", "error_msg": "Error on communicating to image server."}
            print("Response :", resp_json)
            return JSONResponse(content=resp_json)
        data = response.content
    vector = model.get_image_vector(data)
    try:
        db.push(image_id, vector)
    except ValueError as e:
        resp_json = {"status": "failed", "error_msg": f"{type(e)}: {e}"}
        print("Response :", resp_json)
        return JSONResponse(content=resp_json)
    resp_json = {"status": "success"}
    print("Response :", resp_json)
    return JSONResponse(content=resp_json)

@app.get("/api/search")
def api_search(query: str):
    try:
        feature = model.get_text_vector(query)
        feature = feature.reshape((-1,)).tolist()
        resp_json = {"status": "success", "vector": feature}
        print(f"Response : {{\"status\": \"success\", \"vector\": [{feature[0]}, {feature[1]}, {feature[2]}, ..., {feature[-1]}]}}")
        return JSONResponse(content=resp_json)
    except Exception as e:
        resp_json = {"status": "failed", "error_msg": f"{type(e)}: {e}"}
        print("Response :", resp_json)
        return JSONResponse(content=resp_json)
