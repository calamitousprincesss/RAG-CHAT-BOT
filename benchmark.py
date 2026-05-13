"""Run Strategy A vs B benchmark and write reports to docs/."""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.Controllers.benchmark_controller import (
    run_benchmark, _write_markdown, DEFAULT_QUERIES
)


def main():
    print("-> Running benchmark on", len(DEFAULT_QUERIES), "queries…")
    result = run_benchmark()

    json_path = ROOT / "docs" / "retrieval_benchmark.json"
    md_path = ROOT / "docs" / "retrieval_benchmark.md"
    json_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    _write_markdown(result, md_path)

    print(f"[OK] Wrote {json_path.relative_to(ROOT)}")
    print(f"[OK] Wrote {md_path.relative_to(ROOT)}")

    print("\n── Summary ──────────────────────────────────────────")
    for i, row in enumerate(result["queries"], 1):
        print(f"\nQ{i}: {row['query']}")
        print(f"  expanded: {row['strategy_b']['expanded_query']}")
        print("  Strategy A top:",
              [(r["source"], r["score"]) for r in row["strategy_a"]["results"]])
        print("  Strategy B top:",
              [(r["source"], r["score"]) for r in row["strategy_b"]["results"]])


if __name__ == "__main__":
    main()
