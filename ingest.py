from pathlib import Path


def load_docs():
    docs = []
    for p in sorted(Path("data").glob("*.md")):
        docs.append((p.name, p.read_text(encoding="utf-8")))
    return docs


def chunk(text, size=800, overlap=100):
    out = []
    i = 0
    while i < len(text):
        out.append(text[i:i + size])
        i += size - overlap
    return out

import chromadb
from sentence_transformers import SentenceTransformer


def build_index():
    model = SentenceTransformer("all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path="chroma_db")
    try:
        client.delete_collection("fastapi_docs")
    except Exception:
        pass
    col = client.create_collection("fastapi_docs")

    ids, texts, metas = [], [], []
    for name, text in load_docs():
        for i, c in enumerate(chunk(text)):
            ids.append(f"{name}-{i}")
            texts.append(c)
            metas.append({"source": name, "chunk": i})

    embeddings = model.encode(texts, show_progress_bar=True).tolist()
    col.add(ids=ids, documents=texts, metadatas=metas, embeddings=embeddings)
    print("indexed:", col.count())


if __name__ == "__main__":
    build_index()