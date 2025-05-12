from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key="pcsk_3QPVVP_A12nXysSbNQVqxaAkQcyMe8M8Rm7QwaWUaiHZSeUTGLVCUYw4dfsH6XMaMbp6at")
index_name = "quickstart"

if not pc.has_index(index_name):
    pc.create_index(
        name=index_name,
        dimension=2, # Replace with your model dimensions
        metric="cosine", # Replace with your model metric
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        ) 
    )

vectors = [
    ("vec-A", [1, 0], {"desc": "x축"}),
    ("vec-B", [0, 1], {"desc": "y축"}),
    ("vec-C", [0, 0], {"desc": "z축"}),
    ("vec-D", [1, 1], {"desc": "xy 방향"}),
    ("vec-E", [1, 1], {"desc": "xyz 대각선"})
]
index = pc.Index(name=index_name)
index.upsert(vectors=vectors)

# 4. 검색 쿼리 (예: [1, 1, 0])
query_vector = [1, 1]

result = index.query(vector=query_vector, top_k=3, include_metadata=True)

print("\n🔍 검색 결과 (쿼리: [1, 1])")
for match in result['matches']:
    score = match['score']
    vector_id = match['id']
    desc = match['metadata'].get('desc', '')
    print(f"- {vector_id} ({desc}): 유사도 {score:.4f}")
