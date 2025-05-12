from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path='.env.local')  # .env 파일 로드
# 설정값
API_KEY = os.getenv("API_KEY")
ENVIRONMENT = "your-environment"
INDEX_NAME = "clip768"
DIMENSION = 768  # 예: CLIP, BERT 등의 임베딩 차원
METRIC = "cosine"

# 초기화 및 인덱스 생성
pc = Pinecone(api_key=API_KEY)

if not pc.has_index(INDEX_NAME):
    pc.create_index(
        name=INDEX_NAME,
        dimension=DIMENSION,
        metric=METRIC,
        spec=ServerlessSpec(
            cloud="aws",  # 또는 "gcp"
            region="us-east-1"  # region은 계정에 따라 다름
        )
    )
    print(f"✅ '{INDEX_NAME}' 인덱스를 새로 생성했습니다.")
else:
    print(f"ℹ️ '{INDEX_NAME}' 인덱스가 이미 존재합니다.")
