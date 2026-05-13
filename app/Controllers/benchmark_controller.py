from flask import Blueprint, render_template, jsonify
from app.Controllers import get_pipeline
from app.Config.settings import settings
from app.Services.benchmark_metrics import compute_metrics
from app.Services.benchmark_chart import render_score_chart
from pathlib import Path
import json

bp = Blueprint("benchmark", __name__, url_prefix="/benchmark")

DEFAULT_QUERIES = [
    "How does the system handle peak load?",
    "What happens when too many users hit the API at once?",
    "Explain the failover mechanism during outages.",
]


def run_benchmark(queries: list[str] | None = None, top_k: int = 3) -> dict:
    queries = queries or DEFAULT_QUERIES
    pipe = get_pipeline()
    rows = []
    for q in queries:
        a_results, _, a_t = pipe.retrieve(q, strategy="A", top_k=top_k)
        b_results, expanded, b_t = pipe.retrieve(q, strategy="B", top_k=top_k)
        rows.append({
            "query": q,
            "strategy_a": {
                "results": [r.to_dict() for r in a_results],
                "timings_ms": a_t,
            },
            "strategy_b": {
                "expanded_query": expanded,
                "results": [r.to_dict() for r in b_results],
                "timings_ms": b_t,
            },
        })
    benchmark = {"top_k": top_k, "queries": rows}
    benchmark["metrics"] = compute_metrics(benchmark)
    return benchmark


@bp.get("/")
def page():
    return render_template("benchmark.html", queries=DEFAULT_QUERIES)


@bp.post("/run")
def run():
    result = run_benchmark()
    out_path = Path(settings.root) / "docs" / "retrieval_benchmark.md"
    _write_markdown(result, out_path)
    return jsonify({"ok": True, "result": result,
                    "markdown_path": str(out_path.relative_to(settings.root))})


def _write_markdown(result: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    from app.Services.llm_provider import LLMFactory
    active = LLMFactory.active()

    metrics = result.get("metrics", {})
    agg = metrics.get("aggregate", {})
    per_q = metrics.get("per_query", [])

    chart_path = path.parent / "benchmark_chart.png"
    try:
        render_score_chart(result, chart_path)
    except Exception as e:
        chart_path = None

    lines: list[str] = []
    lines.append("# Retrieval Benchmark - Strategy A vs Strategy B\n")
    lines.append("Auto-generated comparison of Raw Vector Search (A) vs AI-Enhanced Retrieval (B).\n")
    lines.append(f"- Top-K: **{result['top_k']}**")
    lines.append("- Similarity metric: **cosine**")
    lines.append("- Embedding model: **sentence-transformers/all-MiniLM-L6-v2** (mocks Vertex `textembedding-gecko`)")
    lines.append("- Vector store: **FAISS** `IndexFlatIP` (file-backed, PDF-compliant)")
    lines.append(f"- Query expander: **{active['provider']}** ({active.get('model', 'n/a')})")
    lines.append(f"- Queries evaluated: **{agg.get('n_queries', 0)}**\n")

    if chart_path and chart_path.exists():
        lines.append(f"![Cosine similarity comparison](./{chart_path.name})\n")

    lines.append("## Aggregate Results\n")
    lines.append("| Metric | Strategy A (Raw) | Strategy B (AI-Enhanced) | Delta |")
    lines.append("|---|---|---|---|")
    lines.append(f"| Mean top-1 cosine score | {agg.get('mean_top1_score_a', 0):.4f} | "
                 f"{agg.get('mean_top1_score_b', 0):.4f} | "
                 f"**{agg.get('score_uplift_top1', 0):+.4f}** |")
    lines.append(f"| Mean top-3 cosine score | {agg.get('mean_top3_score_a', 0):.4f} | "
                 f"{agg.get('mean_top3_score_b', 0):.4f} | "
                 f"**{agg.get('score_uplift_top3', 0):+.4f}** |")
    if agg.get("hit_rate_3_a") is not None:
        lines.append(f"| Hit Rate @ 3 | {agg['hit_rate_3_a']:.4f} | "
                     f"{agg['hit_rate_3_b']:.4f} | "
                     f"**{agg['hit_rate_3_b'] - agg['hit_rate_3_a']:+.4f}** |")
        lines.append(f"| MRR | {agg['mrr_a']:.4f} | {agg['mrr_b']:.4f} | "
                     f"**{agg['mrr_b'] - agg['mrr_a']:+.4f}** |")
        lines.append(f"| nDCG @ 3 | {agg['ndcg_3_a']:.4f} | {agg['ndcg_3_b']:.4f} | "
                     f"**{agg['ndcg_3_b'] - agg['ndcg_3_a']:+.4f}** |")
    lines.append(f"| Mean latency (ms) | {agg.get('mean_latency_ms_a', 0):.1f} | "
                 f"{agg.get('mean_latency_ms_b', 0):.1f} | "
                 f"**{agg.get('latency_overhead_ms', 0):+.1f}** |")
    lines.append("")
    lines.append(f"**Per-query winner:** Strategy A wins {agg.get('wins_strategy_a', 0)}, "
                 f"Strategy B wins {agg.get('wins_strategy_b', 0)}, ties {agg.get('ties', 0)} "
                 f"(threshold: cosine delta > 0.01)\n")

    lines.append("## Per-Query Summary\n")
    lines.append("| # | Query | Winner | Mean A | Mean B | Uplift | Hit@3 A/B | MRR A/B |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, m in enumerate(per_q, 1):
        q_short = m["query"][:50] + ("..." if len(m["query"]) > 50 else "")
        hit = (f"{m['hit_rate_3_a']:.2f}/{m['hit_rate_3_b']:.2f}"
               if m.get("hit_rate_3_a") is not None else "n/a")
        mr = (f"{m['mrr_a']:.2f}/{m['mrr_b']:.2f}"
              if m.get("mrr_a") is not None else "n/a")
        winner_disp = {"A": "A", "B": "B", "tie": "tie"}[m["winner"]]
        lines.append(f"| Q{i} | {q_short} | **{winner_disp}** | {m['mean_score_a']:.4f} | "
                     f"{m['mean_score_b']:.4f} | {m['uplift']:+.4f} | {hit} | {mr} |")
    lines.append("")

    for i, row in enumerate(result["queries"], 1):
        lines.append(f"## Query {i}: \"{row['query']}\"\n")
        lines.append(f"**Strategy B expanded query:** `{row['strategy_b']['expanded_query']}`\n")
        lines.append("| Rank | Strategy A (Raw) | Score | Strategy B (Expanded) | Score |")
        lines.append("|------|------------------|-------|------------------------|-------|")
        a = row["strategy_a"]["results"]
        b = row["strategy_b"]["results"]
        for r in range(max(len(a), len(b))):
            a_txt = a[r]["text"][:80].replace("|", "/") + "..." if r < len(a) else "-"
            a_sc = a[r]["score"] if r < len(a) else "-"
            b_txt = b[r]["text"][:80].replace("|", "/") + "..." if r < len(b) else "-"
            b_sc = b[r]["score"] if r < len(b) else "-"
            lines.append(f"| {r+1} | {a_txt} | {a_sc} | {b_txt} | {b_sc} |")
        lines.append("")
        lines.append(f"_Latency A: embed {row['strategy_a']['timings_ms']['embed_ms']:.1f}ms / "
                     f"search {row['strategy_a']['timings_ms']['search_ms']:.1f}ms_ - "
                     f"_Latency B: expand {row['strategy_b']['timings_ms']['expand_ms']:.1f}ms / "
                     f"embed {row['strategy_b']['timings_ms']['embed_ms']:.1f}ms / "
                     f"search {row['strategy_b']['timings_ms']['search_ms']:.1f}ms_\n")

    lines.append("## Methodology\n")
    lines.append(
        "- **Hit Rate @ K** - fraction of queries where at least one of the top-K retrieved "
        "documents is in the ground-truth relevant set.")
    lines.append(
        "- **MRR (Mean Reciprocal Rank)** - 1 / position of the first relevant result, "
        "averaged across queries.")
    lines.append(
        "- **nDCG @ K** - normalized discounted cumulative gain, rewards relevant results "
        "appearing at higher ranks.")
    lines.append(
        "- **Ground truth** - hand-labeled per query in "
        "`app/Services/benchmark_metrics.py :: GROUND_TRUTH`.")
    lines.append(
        "- **Winner** - strategy with higher mean cosine score across the top-K results "
        "(threshold 0.01 to flag ties).")
    lines.append(
        "- **Latency** - end-to-end retrieval time excluding generation. Strategy B includes "
        "an additional LLM call for query expansion.\n")

    lines.append("## Raw JSON\n\n```json")
    lines.append(json.dumps(result, indent=2, default=str))
    lines.append("```")
    path.write_text("\n".join(lines), encoding="utf-8")
