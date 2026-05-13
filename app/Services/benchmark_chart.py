"""Render a cosine-score comparison chart as PNG using matplotlib."""
from __future__ import annotations
from pathlib import Path


def render_score_chart(benchmark: dict, output_path: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    queries = [r["query"] for r in benchmark["queries"]]
    n = len(queries)
    short_labels = [f"Q{i+1}" for i in range(n)]

    a_top1 = [r["strategy_a"]["results"][0]["score"] if r["strategy_a"]["results"] else 0
              for r in benchmark["queries"]]
    a_top3_mean = [
        sum(x["score"] for x in r["strategy_a"]["results"]) / max(1, len(r["strategy_a"]["results"]))
        for r in benchmark["queries"]
    ]
    b_top1 = [r["strategy_b"]["results"][0]["score"] if r["strategy_b"]["results"] else 0
              for r in benchmark["queries"]]
    b_top3_mean = [
        sum(x["score"] for x in r["strategy_b"]["results"]) / max(1, len(r["strategy_b"]["results"]))
        for r in benchmark["queries"]
    ]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    width = 0.36
    x = np.arange(n)

    ax = axes[0]
    ax.bar(x - width/2, a_top1, width, label="Strategy A (Raw)", color="#5F6368")
    ax.bar(x + width/2, b_top1, width, label="Strategy B (AI-Enhanced)", color="#1A73E8")
    ax.set_title("Top-1 Cosine Score per Query")
    ax.set_ylabel("cosine similarity")
    ax.set_xticks(x)
    ax.set_xticklabels(short_labels)
    ax.set_ylim(0, max(max(a_top1 + b_top1, default=0), 1.0) * 1.1)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    ax = axes[1]
    ax.bar(x - width/2, a_top3_mean, width, label="Strategy A (Raw)", color="#5F6368")
    ax.bar(x + width/2, b_top3_mean, width, label="Strategy B (AI-Enhanced)", color="#1A73E8")
    ax.set_title("Mean Top-3 Cosine Score per Query")
    ax.set_ylabel("cosine similarity")
    ax.set_xticks(x)
    ax.set_xticklabels(short_labels)
    ax.set_ylim(0, max(max(a_top3_mean + b_top3_mean, default=0), 1.0) * 1.1)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    fig.suptitle("Strategy A vs Strategy B: cosine similarity comparison",
                 fontsize=13, fontweight="bold", color="#202124")
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    plt.savefig(output_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return output_path
