"""Aggregate IR metrics for Strategy A vs B comparison."""
from __future__ import annotations
from statistics import mean


GROUND_TRUTH = {
    "How does the system handle peak load?": [
        "auto_scaling.txt", "load_balancer.txt", "rate_limiting.txt",
    ],
    "What happens when too many users hit the API at once?": [
        "rate_limiting.txt", "auto_scaling.txt", "load_balancer.txt",
    ],
    "Explain the failover mechanism during outages.": [
        "database_failover.txt", "disaster_recovery.txt", "load_balancer.txt",
    ],
}


def hit_rate_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    top = retrieved[:k]
    return 1.0 if any(r in relevant for r in top) else 0.0


def mrr(retrieved: list[str], relevant: list[str]) -> float:
    for i, r in enumerate(retrieved, 1):
        if r in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    import math
    dcg = 0.0
    for i, r in enumerate(retrieved[:k], 1):
        if r in relevant:
            dcg += 1.0 / math.log2(i + 1)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
    return dcg / idcg if idcg else 0.0


def compute_metrics(benchmark: dict) -> dict:
    per_query = []
    a_scores_all, b_scores_all = [], []
    a_top1, b_top1 = [], []
    a_latency, b_latency = [], []
    a_hit3, b_hit3 = [], []
    a_mrr, b_mrr = [], []
    a_ndcg3, b_ndcg3 = [], []
    wins_a, wins_b, ties = 0, 0, 0

    for row in benchmark["queries"]:
        q = row["query"]
        a_res = row["strategy_a"]["results"]
        b_res = row["strategy_b"]["results"]
        a_sources = [r["source"] for r in a_res]
        b_sources = [r["source"] for r in b_res]
        a_scores = [r["score"] for r in a_res]
        b_scores = [r["score"] for r in b_res]

        relevant = GROUND_TRUTH.get(q, [])
        a_hit = hit_rate_at_k(a_sources, relevant, 3) if relevant else None
        b_hit = hit_rate_at_k(b_sources, relevant, 3) if relevant else None
        a_m = mrr(a_sources, relevant) if relevant else None
        b_m = mrr(b_sources, relevant) if relevant else None
        a_n = ndcg_at_k(a_sources, relevant, 3) if relevant else None
        b_n = ndcg_at_k(b_sources, relevant, 3) if relevant else None

        a_mean = mean(a_scores) if a_scores else 0.0
        b_mean = mean(b_scores) if b_scores else 0.0

        if b_mean > a_mean + 0.01:
            winner = "B"
            wins_b += 1
        elif a_mean > b_mean + 0.01:
            winner = "A"
            wins_a += 1
        else:
            winner = "tie"
            ties += 1

        a_t = row["strategy_a"]["timings_ms"]
        b_t = row["strategy_b"]["timings_ms"]
        a_total = a_t["embed_ms"] + a_t["search_ms"]
        b_total = b_t["expand_ms"] + b_t["embed_ms"] + b_t["search_ms"]

        per_query.append({
            "query": q,
            "winner": winner,
            "mean_score_a": round(a_mean, 4),
            "mean_score_b": round(b_mean, 4),
            "uplift": round(b_mean - a_mean, 4),
            "hit_rate_3_a": a_hit, "hit_rate_3_b": b_hit,
            "mrr_a": round(a_m, 4) if a_m is not None else None,
            "mrr_b": round(b_m, 4) if b_m is not None else None,
            "ndcg_3_a": round(a_n, 4) if a_n is not None else None,
            "ndcg_3_b": round(b_n, 4) if b_n is not None else None,
            "latency_ms_a": round(a_total, 1),
            "latency_ms_b": round(b_total, 1),
            "expansion_overhead_ms": round(b_t["expand_ms"], 1),
        })

        a_scores_all.extend(a_scores)
        b_scores_all.extend(b_scores)
        if a_scores:
            a_top1.append(a_scores[0])
        if b_scores:
            b_top1.append(b_scores[0])
        a_latency.append(a_total)
        b_latency.append(b_total)
        if a_hit is not None:
            a_hit3.append(a_hit)
            b_hit3.append(b_hit)
            a_mrr.append(a_m)
            b_mrr.append(b_m)
            a_ndcg3.append(a_n)
            b_ndcg3.append(b_n)

    aggregate = {
        "n_queries": len(benchmark["queries"]),
        "wins_strategy_a": wins_a,
        "wins_strategy_b": wins_b,
        "ties": ties,
        "mean_top1_score_a": round(mean(a_top1), 4) if a_top1 else 0,
        "mean_top1_score_b": round(mean(b_top1), 4) if b_top1 else 0,
        "mean_top3_score_a": round(mean(a_scores_all), 4) if a_scores_all else 0,
        "mean_top3_score_b": round(mean(b_scores_all), 4) if b_scores_all else 0,
        "score_uplift_top1": round(mean(b_top1) - mean(a_top1), 4) if a_top1 else 0,
        "score_uplift_top3": round(mean(b_scores_all) - mean(a_scores_all), 4) if a_scores_all else 0,
        "hit_rate_3_a": round(mean(a_hit3), 4) if a_hit3 else None,
        "hit_rate_3_b": round(mean(b_hit3), 4) if b_hit3 else None,
        "mrr_a": round(mean(a_mrr), 4) if a_mrr else None,
        "mrr_b": round(mean(b_mrr), 4) if b_mrr else None,
        "ndcg_3_a": round(mean(a_ndcg3), 4) if a_ndcg3 else None,
        "ndcg_3_b": round(mean(b_ndcg3), 4) if b_ndcg3 else None,
        "mean_latency_ms_a": round(mean(a_latency), 1) if a_latency else 0,
        "mean_latency_ms_b": round(mean(b_latency), 1) if b_latency else 0,
        "latency_overhead_ms": round(mean(b_latency) - mean(a_latency), 1) if a_latency else 0,
    }
    return {"per_query": per_query, "aggregate": aggregate}
