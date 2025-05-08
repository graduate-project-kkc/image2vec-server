FROM pytorch/pytorch:2.6.0-cuda11.8-cudnn9-runtime

COPY ./requirements.txt ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY ./src ./src
COPY ./cache ./cache
ENV HF_HOME=./cache

EXPOSE 3000

CMD ["uvicorn", "src.server:app", "--host=0.0.0.0", "--port=3000"]