import base64
from fastapi import FastAPI, Request, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .core import Model, FakeDB
from .pincone_db import PineconeDB, API_KEY, ENVIRONMENT, INDEX_NAME

app = FastAPI()
templates = Jinja2Templates(directory="src/templates")

model = Model()
fake_db = FakeDB()
db = PineconeDB(API_KEY, ENVIRONMENT, INDEX_NAME)

@app.get("/", response_class=HTMLResponse)
def main_page(request: Request):
    return templates.TemplateResponse(request=request, name="main.html", context={"n_imgs": db.count()})

@app.post("/upload", response_class=HTMLResponse)
def upload_image(request: Request, image_file: UploadFile):
    filename = image_file.filename
    data = image_file.file.read()
    if len(data) == 0:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    vector = model.get_image_vector(data)
    try:
        fake_db.push(filename, data, vector)
        db.push(filename, data, vector)
    except ValueError as e:
        return templates.TemplateResponse(request=request, name="upload.html", context={"result": f"Error - {e.args}"})
    return templates.TemplateResponse(request=request, name="upload.html", context={"result": "success"})

@app.get("/search", response_class=HTMLResponse)
def search(request: Request, text: str):
    feature = model.get_text_vector(text)
    image_indices = db.search(feature)
    result = []
    # for i in range(min(5, len(image_indices))):
        # score = image_indices[i][0].item()
        # image_data = fake_db.get(image_indices[i][1])
        # image_filename = image_data['name']
        # image_content = image_data['data']
    for i in range(len(image_indices)):
        score = image_indices[i][0]
        image_filename = image_indices[i][1]
        image_content = fake_db.filename_to_byte[image_filename]
        image_base64_encoded = base64.b64encode(image_content).decode("utf-8")
        result.append((i+1, image_filename, score, image_base64_encoded))
    return templates.TemplateResponse(request=request, name="search.html", context={"query": text, "images": result})

@app.get("/api/count")
def api_get_uploaded_images():
    return JSONResponse(content={"count": db.count()})

@app.post("/api/upload")
def api_upload_image(image: UploadFile):
    filename = image.filename
    data = image.file.read()
    if len(data) == 0:
        return JSONResponse(content={"result": "failed", "error_msg": "Empty file"})
    vector = model.get_image_vector(data)
    try:
        fake_db.push(filename, data, vector)
        db.push(filename, data, vector)
    except ValueError as e:
        return JSONResponse(content={"result": "failed", "error_msg": e.args})
    return JSONResponse(content={"result": "success"})

@app.get("/api/search")
def api_search(text: str):
    feature = model.get_text_vector(text)
    image_indices = db.search(feature)
    result = []
    # for _, idx in image_indices:
    #     data = db.get(idx)
    #     filename = data["name"]
    #     content = data["data"]
    for _, filename in image_indices:
        content = fake_db.filename_to_byte[filename]
        content_base64 = base64.b64encode(content).decode("utf-8")
        result.append((filename, content_base64))
    return JSONResponse(content=result)
