"""Pure-stdlib retrieval and answer-quality metrics for the RAG eval harness."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean


@dataclass
class RetrievalResult:
    """One question's retrieved chunks, paired with the gold expectations."""

    question_id: str
    retrieved_sources: list[str]
    retrieved_texts: list[str]
    expected_source: str | None
    expected_text_contains: str | None
    latency_ms: float


def source_hit_rank(retrieved_sources: list[str], expected_source: str) -> int | None:
    """1-indexed rank of the first retrieved chunk whose source matches. None if absent."""
    for i, src in enumerate(retrieved_sources, start=1):
        if _source_matches(src, expected_source):
            return i
    return None


def text_hit_rank(retrieved_texts: list[str], expected_text_contains: str) -> int | None:
    """1-indexed rank of the first chunk containing the expected phrase. Case-insensitive."""
    needle = expected_text_contains.lower()
    for i, text in enumerate(retrieved_texts, start=1):
        if needle in text.lower():
            return i
    return None


def _source_matches(retrieved_source: str, expected_source: str) -> bool:
    """Match `mahatma_gandhi` against `mahatma_gandhi.txt`, paths, etc."""
    rs = retrieved_source.lower().replace("\\", "/").split("/")[-1]
    if rs.endswith(".txt"):
        rs = rs[:-4]
    return rs == expected_source.lower()

#Out of 15 questions, on how many did the right document show up somewhere in the top 5?
def recall_at_k(results: list[RetrievalResult], k: int, by: str = "source") -> float:
    """Fraction of in-corpus questions where the gold item appears in top-K."""
    if by == "source":
        scope = [r for r in results if r.expected_source is not None]
    elif by == "text":
        scope = [r for r in results if r.expected_text_contains is not None]
    else:
        raise ValueError(f"unknown 'by': {by}")
    if not scope:
        return 0.0

    hits = 0
    for r in scope:
        if by == "source":
            rank = source_hit_rank(r.retrieved_sources[:k], r.expected_source)
        else:
            rank = text_hit_rank(r.retrieved_texts[:k], r.expected_text_contains)
        if rank is not None:
            hits += 1
    return hits / len(scope)

#On average, how high up in the rankings does the right answer appear?
def mean_reciprocal_rank(results: list[RetrievalResult], by: str = "source") -> float:
    """MRR across in-corpus questions. Missing hits contribute 0."""
    relevant = [r for r in results if r.expected_source is not None]
    if not relevant:
        return 0.0

    rr_values: list[float] = []
    for r in relevant:
        if by == "source":
            rank = source_hit_rank(r.retrieved_sources, r.expected_source)
        elif by == "text":
            if r.expected_text_contains is None:
                rr_values.append(0.0)
                continue
            rank = text_hit_rank(r.retrieved_texts, r.expected_text_contains)
        else:
            raise ValueError(f"unknown 'by': {by}")
        rr_values.append(1.0 / rank if rank else 0.0)
    return mean(rr_values)

#For each question, what fraction of the 5 returned chunks were from the right document? Average across questions.
def precision_at_k(results: list[RetrievalResult], k: int) -> float:
    """Mean fraction of top-K chunks whose source matches the expected source."""
    relevant = [r for r in results if r.expected_source is not None]
    if not relevant:
        return 0.0

    precisions: list[float] = []
    for r in relevant:
        top_k = r.retrieved_sources[:k]
        if not top_k:
            precisions.append(0.0)
            continue
        matches = sum(1 for s in top_k if _source_matches(s, r.expected_source))
        precisions.append(matches / len(top_k))
    return mean(precisions)

#p50 = median value
#P95 = the 15th smallest value (the worst one)
#P99 = also the 15th smallest value (still just the worst one)
def latency_percentiles(latencies_ms: list[float]) -> dict[str, float]:
    """Return P50/P95/P99 + mean. Uses nearest-rank with ceil — fine for small N."""
    if not latencies_ms:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0}
    sorted_ms = sorted(latencies_ms)
    n = len(sorted_ms)

    def pct(p: float) -> float:
        idx = max(0, min(n - 1, math.ceil(p * n) - 1))
        return sorted_ms[idx]

    return {
        "p50": round(pct(0.50), 2),
        "p95": round(pct(0.95), 2),
        "p99": round(pct(0.99), 2),
        "mean": round(mean(sorted_ms), 2),
    }


def answer_keyword_recall(answer: str, expected_keywords: list[str]) -> float:
    """Fraction of expected keywords present (case-insensitive) in the answer."""
    if not expected_keywords:
        return 1.0
    haystack = answer.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in haystack)
    return hits / len(expected_keywords)
