import chromadb
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
col = chromadb.PersistentClient(path="chroma_db").get_collection("fastapi_docs")


def retrieve(question, k=4):
    emb = model.encode([question]).tolist()
    r = col.query(query_embeddings=emb, n_results=k)
    out = []
    for doc, meta, dist in zip(r["documents"][0], r["metadatas"][0], r["distances"][0]):
        out.append({"text": doc, "source": meta["source"], "distance": dist})
    return out


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "Which URL shows the interactive API docs?"
    for h in retrieve(q):
        print(round(h["distance"], 3), h["source"])
        print(h["text"][:150].replace("\n", " "))
        print("---")