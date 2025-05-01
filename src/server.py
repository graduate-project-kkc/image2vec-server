from typing import Union
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"data": "Hello, world! 202012364"}

@app.get("/echo/{string}")
def echo_msg(string: str, q: Union[str, None] = None):
    return {"input": string, "q": q}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
