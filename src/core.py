import torch
import io
from transformers import CLIPProcessor, CLIPModel
from PIL import Image, ImageOps

GPU = "cuda" if torch.cuda.is_available() else "cpu"
CPU = "cpu"

class Model:
    def __init__(self):
        self.model = CLIPModel.from_pretrained("openai/clip-vit-large-patch14").to(GPU)
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")

    def get_image_vector(self, image_data: bytes):
        with torch.no_grad():
            image_data_stream = io.BytesIO(image_data)
            image_object = Image.open(image_data_stream)
            ImageOps.exif_transpose(image_object, in_place=True)
            inputs = self.processor(images=image_object, return_tensors="pt").to(GPU)
            image_features = self.model.get_image_features(**inputs)
        return image_features

    def get_text_vector(self, query: str):
        with torch.no_grad():
            inputs = self.processor(text=[query], return_tensors="pt", padding=True).to(GPU)
            text_features = self.model.get_text_features(**inputs)
        return text_features

