"""RAG evaluation runner.

Usage (from backend/ directory):

    python -m evals.run_eval --baseline
    python -m evals.run_eval --sweep-chunks
    python -m evals.run_eval --sweep-topk
    python -m evals.run_eval --baseline --end-to-end       # also runs the LLM

The runner uses an isolated FAISS index under evals/.eval_index/ so it never
touches your real data/ folder.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
SAMPLE_DOCS_DIR = EVALS_DIR / "datasets" / "sample_docs"
GOLDEN_SET = EVALS_DIR / "datasets" / "golden_set.json"
RESULTS_DIR = EVALS_DIR / "results"
EVAL_INDEX_DIR = EVALS_DIR / ".eval_index"


def _isolate_index() -> None:
    """Point the vector store at an isolated, ephemeral directory before importing it."""
    EVAL_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["FAISS_INDEX_PATH"] = str(EVAL_INDEX_DIR / "faiss_index")


def _reset_index() -> None:
    if EVAL_INDEX_DIR.exists():
        shutil.rmtree(EVAL_INDEX_DIR)
    EVAL_INDEX_DIR.mkdir(parents=True, exist_ok=True)

#The first time you import a module, Python runs all its code (including reading env vars) and stores the result in sys.modules. Every subsequent import just returns the cached version — none of the module code runs again.
def _fresh_vector_store(chunk_size: int | None = None, chunk_overlap: int | None = None):
    """Reset the on-disk index, reload modules so config picks up overrides, return store."""
    _reset_index()
    if chunk_size is not None:
        os.environ["CHUNK_SIZE"] = str(chunk_size)
    if chunk_overlap is not None:
        os.environ["CHUNK_OVERLAP"] = str(chunk_overlap)

    # Force re-import so env overrides take effect on module-level constants.
    for mod_name in [
        "app.core.config",
        "app.services.chunker",
        "app.services.embeddings",
        "app.services.vector_store",
    ]:
        if mod_name in sys.modules:
            del sys.modules[mod_name]

    from app.services.chunker import chunk_text
    from app.services.vector_store import vector_store
    return vector_store, chunk_text


def _ingest_sample_docs(vector_store, chunk_text) -> int:
    total = 0
    for doc_path in sorted(SAMPLE_DOCS_DIR.glob("*.txt")):
        text = doc_path.read_text(encoding="utf-8")
        chunks = chunk_text(text)
        topic = _topic_for(doc_path.stem)
        total += vector_store.add_chunks(chunks, source=doc_path.stem, topic=topic)
    return total


def _topic_for(stem: str) -> str:
    return {
        "http_basics": "HTTP",
        "photosynthesis": "Biology",
        "mahatma_gandhi": "History",
    }.get(stem, "General")


def _load_golden_set() -> list[dict]:
    with GOLDEN_SET.open() as f:
        return json.load(f)["questions"]


def _run_retrieval(vector_store, questions: list[dict], top_k: int):
    from evals.metrics import RetrievalResult

    results: list[RetrievalResult] = []
    for q in questions:
        if q["expected_source"] is None:
            continue
        start = time.perf_counter()
        retrieved = vector_store.search(q["question"], top_k=top_k)
        latency_ms = (time.perf_counter() - start) * 1000.0
        results.append(
            RetrievalResult(
                question_id=q["id"],
                retrieved_sources=[r["source"] for r in retrieved],
                retrieved_texts=[r["text"] for r in retrieved],
                expected_source=q["expected_source"],
                expected_text_contains=q.get("expected_text_contains"),
                latency_ms=latency_ms,
            )
        )
    return results


def _run_end_to_end(vector_store, questions: list[dict], top_k: int):
    """Optional: run the full RAG chain (retrieve + Gemini) and score keyword recall."""
    from app.services.llm import ask_llm, build_rag_prompt
    from evals.metrics import answer_keyword_recall

    rows: list[dict] = []
    for q in questions:
        start = time.perf_counter()
        retrieved = vector_store.search(q["question"], top_k=top_k)
        retrieval_ms = (time.perf_counter() - start) * 1000.0

        gen_start = time.perf_counter()
        answer = ask_llm(build_rag_prompt(retrieved, q["question"], mode="intermediate"))
        generation_ms = (time.perf_counter() - gen_start) * 1000.0

        keywords = q.get("expected_keywords", []) or []
        rows.append(
            {
                "id": q["id"],
                "category": q["category"],
                "answer": answer,
                "keyword_recall": round(answer_keyword_recall(answer, keywords), 3),
                "retrieval_ms": round(retrieval_ms, 2),
                "generation_ms": round(generation_ms, 2),
                "total_ms": round(retrieval_ms + generation_ms, 2),
            }
        )
    return rows


def _summarize_retrieval(results, top_k: int) -> dict:
    from evals.metrics import (
        latency_percentiles,
        mean_reciprocal_rank,
        precision_at_k,
        recall_at_k,
    )

    latencies = [r.latency_ms for r in results]
    return {
        "n_questions": len(results),
        "top_k": top_k,
        "recall_at_k_source": round(recall_at_k(results, top_k, by="source"), 3),
        "recall_at_k_text": round(recall_at_k(results, top_k, by="text"), 3),
        "mrr_source": round(mean_reciprocal_rank(results, by="source"), 3),
        "mrr_text": round(mean_reciprocal_rank(results, by="text"), 3),
        "precision_at_k": round(precision_at_k(results, top_k), 3),
        "retrieval_latency_ms": latency_percentiles(latencies),
    }


def _print_table(rows: list[dict], columns: list[str], title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    widths = {c: max(len(c), max((len(str(r.get(c, ""))) for r in rows), default=0)) for c in columns}
    header = "  ".join(c.ljust(widths[c]) for c in columns)
    print(header)
    print("  ".join("-" * widths[c] for c in columns))
    for r in rows:
        print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in columns))


def _save(results: dict, label: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out = RESULTS_DIR / f"{stamp}_{label}.json"
    out.write_text(json.dumps(results, indent=2))
    return out


def cmd_baseline(args, questions):
    print(f"\n=== Baseline (chunk={os.getenv('CHUNK_SIZE','default')}, top_k={args.top_k}) ===")
    vector_store, chunk_text = _fresh_vector_store()
    n = _ingest_sample_docs(vector_store, chunk_text)
    print(f"Ingested {n} chunks across {len(list(SAMPLE_DOCS_DIR.glob('*.txt')))} docs.")

    results = _run_retrieval(vector_store, questions, top_k=args.top_k)
    summary = _summarize_retrieval(results, top_k=args.top_k)
    print("\nRetrieval metrics:")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    payload = {"type": "baseline", "summary": summary, "per_question": [r.__dict__ for r in results]}

    if args.end_to_end:
        print("\nRunning end-to-end (this calls Gemini for each question)...")
        e2e = _run_end_to_end(vector_store, questions, top_k=args.top_k)
        _print_table(e2e, ["id", "keyword_recall", "retrieval_ms", "generation_ms", "total_ms"], "End-to-end per question")
        avg_kw = round(sum(r["keyword_recall"] for r in e2e) / len(e2e), 3) if e2e else 0.0
        avg_total = round(sum(r["total_ms"] for r in e2e) / len(e2e), 2) if e2e else 0.0
        print(f"\nAvg keyword recall: {avg_kw}   Avg total latency: {avg_total} ms")
        payload["end_to_end"] = {"avg_keyword_recall": avg_kw, "avg_total_ms": avg_total, "rows": e2e}

    out = _save(payload, "baseline")
    print(f"\nSaved → {out.relative_to(EVALS_DIR.parent)}")


def cmd_sweep_chunks(args, questions):
    print("\n=== Chunk-size sweep ===")
    sweeps = [(200, 40), (400, 80), (800, 160)]
    rows: list[dict] = []
    for size, overlap in sweeps:
        vector_store, chunk_text = _fresh_vector_store(chunk_size=size, chunk_overlap=overlap)
        n = _ingest_sample_docs(vector_store, chunk_text)
        results = _run_retrieval(vector_store, questions, top_k=args.top_k)
        s = _summarize_retrieval(results, top_k=args.top_k)
        rows.append(
            {
                "chunk_size": size,
                "overlap": overlap,
                "n_chunks_indexed": n,
                "recall@k": s["recall_at_k_source"],
                "mrr": s["mrr_source"],
                "p@k": s["precision_at_k"],
                "p95_ms": s["retrieval_latency_ms"]["p95"],
            }
        )
    _print_table(rows, ["chunk_size", "overlap", "n_chunks_indexed", "recall@k", "mrr", "p@k", "p95_ms"], f"Sweep results (top_k={args.top_k})")
    out = _save({"type": "sweep_chunks", "top_k": args.top_k, "rows": rows}, "sweep_chunks")
    print(f"\nSaved → {out.relative_to(EVALS_DIR.parent)}")


def cmd_sweep_topk(args, questions):
    print("\n=== Top-K sweep ===")
    vector_store, chunk_text = _fresh_vector_store()
    _ingest_sample_docs(vector_store, chunk_text)
    rows: list[dict] = []
    for k in [1, 3, 5, 10]:
        results = _run_retrieval(vector_store, questions, top_k=k)
        s = _summarize_retrieval(results, top_k=k)
        rows.append(
            {
                "top_k": k,
                "recall@k": s["recall_at_k_source"],
                "mrr": s["mrr_source"],
                "p@k": s["precision_at_k"],
                "p95_ms": s["retrieval_latency_ms"]["p95"],
            }
        )
    _print_table(rows, ["top_k", "recall@k", "mrr", "p@k", "p95_ms"], "Top-K sweep")
    out = _save({"type": "sweep_topk", "rows": rows}, "sweep_topk")
    print(f"\nSaved → {out.relative_to(EVALS_DIR.parent)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baseline", action="store_true", help="Run the baseline retrieval eval")
    parser.add_argument("--sweep-chunks", action="store_true", help="Sweep chunk sizes")
    parser.add_argument("--sweep-topk", action="store_true", help="Sweep top-K")
    parser.add_argument("--end-to-end", action="store_true", help="Also run the full RAG chain (calls Gemini)")
    parser.add_argument("--top-k", type=int, default=5, help="Top-K for retrieval (default 5)")
    args = parser.parse_args()

    if not (args.baseline or args.sweep_chunks or args.sweep_topk):
        parser.print_help()
        return 1

    _isolate_index()
    questions = _load_golden_set()

    if args.baseline:
        cmd_baseline(args, questions)
    if args.sweep_chunks:
        cmd_sweep_chunks(args, questions)
    if args.sweep_topk:
        cmd_sweep_topk(args, questions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
