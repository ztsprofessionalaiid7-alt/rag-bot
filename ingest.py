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


if __name__ == "__main__":
    total = 0
    for name, text in load_docs():
        n = len(chunk(text))
        total += n
        print(name, n)
    print("total chunks:", total)