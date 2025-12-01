from pydantic import BaseModel


class CountRequest(BaseModel):
    userId: str


class UploadImageRequest(BaseModel):
    userId: str
    imageIds: list[str]