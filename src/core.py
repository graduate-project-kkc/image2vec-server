import torch
import io
import threading
from transformers import CLIPProcessor, CLIPModel
from PIL import Image, ImageOps
from logging import Logger

from .timer import SimpleTimer

GPU = "cuda" if torch.cuda.is_available() else "cpu"
CPU = "cpu"

class Model:
    logger: Logger
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self.model = CLIPModel.from_pretrained("./model", local_files_only=True).to(GPU)
        self.processor = CLIPProcessor.from_pretrained("./model", local_files_only=True)

    def get_image_vector(self, image_data: bytes):
        timer = SimpleTimer()
        with torch.no_grad():
            timer.start()
            image_data_stream = io.BytesIO(image_data)
            image_object = Image.open(image_data_stream)
            ImageOps.exif_transpose(image_object, in_place=True)
            elapsed = timer.stop()
            self.logger.info(f"[{threading.get_ident()} - Model.get_image_vector] Converting the bytes to PIL Image object took {elapsed:.3f} sec.")
            timer.start()
            inputs = self.processor(images=image_object, return_tensors="pt").to(GPU)
            elapsed = timer.stop()
            self.logger.info(f"[{threading.get_ident()} - Model.get_image_vector] Converting PIL Image object to input tensor took {elapsed:.3f} sec.")
            timer.start()
            image_features = self.model.get_image_features(**inputs)
            elapsed = timer.stop()
            self.logger.info(f"[{threading.get_ident()} - Model.get_image_vector] Calculating image features took {elapsed:.3f} sec.")
        return image_features

    def get_text_vector(self, query: str):
        timer = SimpleTimer()
        with torch.no_grad():
            timer.start()
            inputs = self.processor(text=[query], return_tensors="pt", padding=True).to(GPU)
            elapsed = timer.stop()
            self.logger.info(f"[{threading.get_ident()} - Model.get_text_vector] Converting string to input tensor took {elapsed:.3f} sec.")
            timer.start()
            text_features = self.model.get_text_features(**inputs)
            elapsed = timer.stop()
            self.logger.info(f"[{threading.get_ident()} - Model.get_text_vector] Calculating text features took {elapsed:.3f} sec.")
        return text_features
