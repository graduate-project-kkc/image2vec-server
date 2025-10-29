import torch
import io
import threading
from transformers import CLIPProcessor, CLIPModel
from PIL import Image, ImageOps
from logging import Logger

from memory_profiler import profile

from .timer import SimpleTimer

Image.MAX_IMAGE_PIXELS = None

GPU = "cuda" if torch.cuda.is_available() else "cpu"
CPU = "cpu"

class Model:
    logger: Logger
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self.model = CLIPModel.from_pretrained("./model", local_files_only=True).to(GPU)
        self.processor = CLIPProcessor.from_pretrained("./model", local_files_only=True)

    # @profile
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
    
    # @profile
    def get_image_vectors(self, image_datas: list[bytes]):
        if not image_datas:
            return []
        timer = SimpleTimer()
        image_objects = []
        for idx, image_data in enumerate(image_datas):
            timer.start()
            image_data_stream = io.BytesIO(image_data)
            image_object = Image.open(image_data_stream)
            ImageOps.exif_transpose(image_object, in_place=True)
            elapsed = timer.stop()
            image_objects.append(image_object)
            self.logger.info(f"[{threading.get_ident()} - Model.get_image_vectors] Converting the bytes to PIL Image object #{idx+1} took {elapsed:.3f} sec.")
        with torch.no_grad():
            timer.start()
            inputs = self.processor(images=image_objects, return_tensors="pt").to(GPU)
            elapsed = timer.stop()
            self.logger.info(f"[{threading.get_ident()} - Model.get_image_vectors] Converting PIL Image object(s) to input tensor took {elapsed:.3f} sec.")
            timer.start()
            image_features = self.model.get_image_features(**inputs)
            elapsed = timer.stop()
            self.logger.info(f"[{threading.get_ident()} - Model.get_image_vectors] Calculating image features took {elapsed:.3f} sec.")
        return image_features

    # @profile
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

    # @profile
    def get_text_vectors(self, queries: list[str]):
        if not queries:
            return []
        timer = SimpleTimer()
        with torch.no_grad():
            timer.start()
            inputs = self.processor(text=queries, return_tensors="pt", padding=True).to(GPU)
            elapsed = timer.stop()
            self.logger.info(f"[{threading.get_ident()} - Model.get_text_vectors] Converting strings to input tensor took {elapsed:.3f} sec.")
            timer.start()
            text_features = self.model.get_text_features(**inputs)
            elapsed = timer.stop()
            self.logger.info(f"[{threading.get_ident()} - Model.get_text_vectors] Calculating text features took {elapsed:.3f} sec.")
        return text_features


@profile
def test_memory():
    import logging
    def print_gpu_mem():
        if torch.cuda.is_available():
            device = torch.device('cuda:0') # Specify the GPU device, e.g., 0 for the first GPU

            # Get total memory
            total_memory = torch.cuda.get_device_properties(device).total_memory / (1024**3) # in GB
            print(f"Total GPU memory: {total_memory:.2f} GB")

            # Get allocated memory (currently used by tensors)
            allocated_memory = torch.cuda.memory_allocated(device) / (1024**3) # in GB
            print(f"Allocated GPU memory: {allocated_memory:.2f} GB")

            # Get reserved memory (cached by the allocator)
            reserved_memory = torch.cuda.memory_reserved(device) / (1024**3) # in GB
            print(f"Reserved GPU memory: {reserved_memory:.2f} GB")
        else:
            print("CUDA is not available. GPU memory usage cannot be checked.")

    logging.basicConfig(level=logging.INFO)
    print_gpu_mem()
    model = Model(logging.getLogger())
    print_gpu_mem()
    
    Image.MAX_IMAGE_PIXELS = None
    
    # First try
    image_data = open("./test_images/ToBeUploaded2/20250902_133843.jpg", "rb").read()
    image_vector = model.get_image_vector(image_data)
    print("20250902_133843.jpg", image_vector.shape)
    del image_data, image_vector
    text = "A man wearing a blue shirt"
    text_vector = model.get_text_vector(text)
    print(text, text_vector.shape)
    del text, text_vector
    
    # Do it one more time
    image_data = open("./test_images/ToBeUploaded2/20250722_170555.jpg", "rb").read()
    image_vector = model.get_image_vector(image_data)
    print("20250722_170555.jpg", image_vector.shape)
    del image_data, image_vector
    text = "A mahjong table"
    text_vector = model.get_text_vector(text)
    print(text, text_vector.shape)
    del text, text_vector
    
    # Big file
    image_data = open("./test_images/ToBeUploaded2/20250728_150030.jpg", "rb").read()
    image_vector = model.get_image_vector(image_data)
    print("20250728_150030.jpg", image_vector.shape)
    del image_data, image_vector
    
    print_gpu_mem()


if __name__ == "__main__":
    test_memory()