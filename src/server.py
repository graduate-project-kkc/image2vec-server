from typing import Union
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .core import Model

app = FastAPI()
model = Model()
templates = Jinja2Templates(directory="src/templates")

@app.get("/", response_class=HTMLResponse)
def main_page(request: Request):
    return templates.TemplateResponse(request=request, name="main.html")

@app.post("/feature/image/")
def get_feature_of_image(request: Request, image_file: UploadFile):
    image = image_file.file.read()
    feature = model.get_image_vector(image)
    return {"image_filename": image_file.filename, "data": feature.flatten().tolist()}

@app.post("/feature/text/")
def get_feature_of_text(request: Request, text: str):
    feature = model.get_text_vector(text)
    return {"query": text, "data": feature.flatten().tolist()}