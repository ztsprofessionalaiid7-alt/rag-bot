import json
import sys
import time
from answer import answer

split = sys.argv[1] if len(sys.argv) > 1 else "dev"
cases = []
for line in open("eval/cases.jsonl", encoding="utf-8"):
    if line.strip():
        cases.append(json.loads(line))
cases = [c for c in cases if c["split"] == split]

rows = []
for c in cases:
    text, hits = answer(c["question"])
    sources = [h["source"] for h in hits]
    if c["tag"] in ("not_in_docs", "attack"):
        ok = text == "NOT_IN_DOCS"
    elif c["expected"] == "CLARIFY":
        ok = None
    else:
        ok = text != "NOT_IN_DOCS" and c["source"] in sources
    rows.append({"id": c["id"], "tag": c["tag"], "ok": ok, "answer": text,
                 "expected": c["expected"], "verified": c["verified"]})
    print(c["id"], c["tag"], "PASS" if ok else ("CHECK" if ok is None else "FAIL"))
    time.sleep(1)

with open(f"eval/results_{split}.jsonl", "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

scored = [r for r in rows if r["ok"] is not None]
print("score:", sum(r["ok"] for r in scored), "/", len(scored))
for r in rows:
    if r["ok"] is not True:
        print("----", r["id"], "| expected:", r["expected"][:80])
        print("got:", r["answer"][:200])