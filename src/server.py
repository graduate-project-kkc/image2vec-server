import os
import requests

from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse

from .core import Model
from .pincone_db import PineconeDB, API_KEY, ENVIRONMENT, INDEX_NAME

app = FastAPI()

model = Model()

db = PineconeDB(API_KEY, ENVIRONMENT, INDEX_NAME)

s3_URL = os.getenv("S3_URL")
SPECIAL_KEY = os.getenv("SPECIAL_KEY")  # Temporary authentication key

def upload_to_db(image_id):
    with requests.get(s3_URL + image_id) as response:
        if response.status_code != 200:
            result = {"status": "failed", "error_msg": "Error on communicating to image server."}
            print("Upload to db :", result)
            return result
        data = response.content
    vector = model.get_image_vector(data)
    try:
        db.push(image_id, vector)
    except ValueError as e:
        result = {"status": "failed", "error_msg": f"{type(e)}: {e}"}
        print("Upload to db :", result)
        return result
    result = {"status": "success"}
    print("Upload to db :", result)
    return result

@app.get("/api/count")
def api_get_uploaded_images():
    return JSONResponse(content={"count": db.count()})

@app.post("/api/upload")
def api_upload_image(image_ids: list[str] = Body(...)):
    resp_json = {"status": {"success": 0, "failed": 0}, "results": []}
    for image_id in image_ids:
        result = upload_to_db(image_id)
        resp_json["results"].append(result)
        resp_json["status"][result["status"]] += 1
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
