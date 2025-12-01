from pinecone import Pinecone, ServerlessSpec
import torch
from dotenv import load_dotenv
import os


load_dotenv(dotenv_path='.env.local')  # .env 파일 로드
# 설정값
API_KEY = os.getenv("API_KEY")
ENVIRONMENT = "your-environment"
INDEX_NAME = "clip768"
DIMENSION = 768  # 예: CLIP, BERT 등의 임베딩 차원
METRIC = "cosine"





class PineconeDB():
    def __init__(self, api_key: str, environment: str, index_name: str):
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
        
        self.index = pc.Index(name=INDEX_NAME)

    def count(self, username: str):
        return self.index.describe_index_stats()[username]['vector_count']

    # def push(self, filename: str, data: bytes, feature_vector: torch.FloatTensor):
    def push(self, username: str, filename: str, feature_vector: torch.FloatTensor):
        if feature_vector.size(dim=1) != 768:
            raise ValueError("The given feature vector's shape is incorrect.")

        feature_vector = feature_vector / feature_vector.norm(p=2, dim=-1, keepdim=True)
        vector = feature_vector.squeeze().tolist()

        # 인덱싱
        
        return self.index.upsert([(filename, vector)], namespace=username)


    def search(self, username: str, text_features: torch.FloatTensor):
        if text_features.size(dim=1) != 768:
            raise ValueError("The given feature vector's shape is incorrect.")
        text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
        vector = text_features.squeeze().tolist()
        result = self.index.query(vector=vector, top_k=10, include_values=True, namespace=username)

        # Pinecone는 id와 score를 제공함
        return [(match['score'], match['id'])
                for match in result['matches']]
