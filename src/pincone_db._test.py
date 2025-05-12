import torch
from pinecone import PineconeException
from pincone_db import PineconeDB 

# 필요한 클래스 import
# from your_module import PineconeDB

from dotenv import load_dotenv
import os


load_dotenv(dotenv_path='.env.local')  # .env 파일 로드
# 설정값
API_KEY = os.getenv("API_KEY")
print("api-key",API_KEY)
ENVIRONMENT = "your-environment"
INDEX_NAME = "test-index"

# 테스트용 함수
def test_pinecone_db():
    try:
        # PineconeDB 인스턴스 생성
        db = PineconeDB(API_KEY, ENVIRONMENT, INDEX_NAME)

        # 테스트용 feature vector 생성 (768차원, 정규화 전)
        vec1 = torch.randn(1, 768)
        vec2 = torch.randn(1, 768)
        vec_query = vec1.clone()  # vec1과 유사한 벡터로 검색 테스트

        # 데이터 push
        idx1 = db.push("file1.jpg", b"fake-image-data-1", vec1)
        idx2 = db.push("file2.jpg", b"fake-image-data-2", vec2)

        print(f"Pushed file1 at index {idx1}, file2 at index {idx2}")

        # 검색 테스트
        results = db.search(vec_query)
        print("🔍 Search Results:")
        for score, idx in results:
            print(f" - [{idx}] , score: {score:.4f}")

        # 개수 확인
        print(f"📦 Total Count in DB: {db.count()}")

    except PineconeException as e:
        print("Pinecone 오류:", e)
    except Exception as e:
        print("일반 오류:", e)

# 실행
if __name__ == "__main__":
    test_pinecone_db()
