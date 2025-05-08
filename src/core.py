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
        # image_data should be bytes gotten by reading a raw file, not using PIL or something.
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


class FakeDB:
    def __init__(self):
        self.filename_to_byte: dict[str, bytes] = dict()
        self.index_to_filename: list[str] = []
        self.features = torch.empty((0, 768), dtype=torch.float32).to(device=CPU)
    
    def count(self):
        return len(self.index_to_filename)
    
    def push(self, filename: str, data: bytes, feature_vector: torch.FloatTensor):
        if feature_vector.size(dim=1) != 768:
            raise ValueError("The given feature vector's shape is incorrect.")
        if filename in self.filename_to_byte:
            raise ValueError("The given file name already exists.")
        self.filename_to_byte[filename] = data
        self.index_to_filename.append(filename)
        feature_vector = feature_vector / feature_vector.norm(p=2, dim=-1, keepdim=True)
        feature_vector = feature_vector.to(device=CPU)
        self.features = torch.cat((self.features, feature_vector))
        return len(self.index_to_filename) - 1  # index
    
    def get(self, index: int):
        filename = self.index_to_filename[index]
        return {'name': filename, 'data': self.filename_to_byte[filename]}
    
    def search(self, text_features: torch.FloatTensor):
        if text_features.size(dim=1) != 768:
            raise ValueError("The given feature vector's shape is incorrect.")
        text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
        text_features = text_features.to(device=CPU)
        similarities = self.features @ text_features.T
        similarities = similarities.reshape((-1,))
        similarities_with_idx = list(zip(similarities, range(similarities.numel())))
        similarities_with_idx.sort(reverse=True)
        return similarities_with_idx
