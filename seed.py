"""Seed the knowledge base with 8 technical paragraphs."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.Services.embedding_service import SentenceTransformerEmbedder
from app.Services.rag_pipeline import RAGPipeline
from app.Controllers import _make_vector_store
from app.Models.document_model import DocumentModel, init_db


PARAGRAPHS = [
    ("auto_scaling.txt",
     "The system handles peak load through horizontal auto-scaling powered by "
     "Kubernetes HPA. When CPU utilization crosses 70% or request latency p95 "
     "exceeds 300ms, new pods are spun up from a warm pool. A predictive "
     "scaler also pre-provisions capacity during known traffic spikes such as "
     "marketing campaigns. Connection draining ensures in-flight requests "
     "complete before pods are terminated during scale-down."),
    ("load_balancer.txt",
     "Incoming traffic is distributed across regional load balancers operating "
     "at both L4 and L7. The L7 layer performs path-based routing, TLS "
     "termination, and weighted canary deployments. Sticky sessions are used "
     "only for stateful upload flows; everything else is fully stateless to "
     "permit any-node routing. Health checks at 5-second intervals remove "
     "unhealthy backends from rotation within 15 seconds."),
    ("database_failover.txt",
     "The primary database operates in a multi-AZ configuration with "
     "synchronous replication to a standby replica in a separate availability "
     "zone. During an outage, automatic failover promotes the replica to "
     "primary within 30 seconds, achieving an RTO of under one minute. Async "
     "read replicas in additional regions absorb heavy analytics queries. "
     "Point-in-time recovery is supported through continuous WAL archival."),
    ("rate_limiting.txt",
     "APIs are protected by a tiered rate-limiting system using token-bucket "
     "and leaky-bucket algorithms. Anonymous traffic is capped per IP at 60 "
     "requests per minute, while authenticated users get per-key quotas based "
     "on plan. Burst credits accumulate to absorb sudden spikes without "
     "starvation. Throttled clients receive a 429 response with a "
     "Retry-After header to enable polite client backoff."),
    ("caching.txt",
     "Multi-layer caching mitigates database load. The CDN caches static "
     "assets at the edge with TTLs of 24 hours and stale-while-revalidate. "
     "Redis serves as the application-level cache for session data, hot "
     "object lookups, and computed aggregates with TTLs from seconds to "
     "minutes. Query-level caches in the ORM eliminate redundant reads. "
     "Cache invalidation uses pub/sub fan-out and versioned keys to avoid "
     "thundering herds."),
    ("disaster_recovery.txt",
     "Disaster recovery procedures define an RPO of 5 minutes and an RTO of "
     "30 minutes. Cross-region replication maintains warm standbys, and "
     "quarterly game-day exercises validate the failover runbook. Incident "
     "commanders coordinate response via a runbook playbook with auto-paging "
     "to on-call engineers. Post-incident reviews are blameless and "
     "action-item driven, fed back into reliability work."),
    ("observability.txt",
     "Observability is built on three pillars: metrics, traces, and logs. "
     "Prometheus scrapes service metrics; OpenTelemetry traces span every "
     "request across services with parent-child relationships; logs are "
     "shipped to a central indexed store with structured JSON. Grafana "
     "dashboards surface RED metrics — Rate, Errors, Duration. Alerts route "
     "to on-call rotations with severity-aware paging."),
    ("zero_trust_security.txt",
     "Security follows zero-trust principles. Every service-to-service call "
     "is authenticated with mTLS using SPIFFE identities. A Web Application "
     "Firewall guards against OWASP top-10 attacks at the edge. DDoS "
     "protection uses rate-based rules and challenge pages for suspected "
     "bots. Secrets are rotated automatically every 90 days and stored in a "
     "vault with audit logging on every access."),
]


def main():
    print("-> Initializing DB…")
    init_db()
    print("-> Loading embedder (downloads model on first run)…")
    pipe = RAGPipeline(
        embedder=SentenceTransformerEmbedder(),
        vector_store=_make_vector_store(),
    )

    existing = {d["filename"] for d in DocumentModel.list_all()}
    added = 0
    for name, text in PARAGRAPHS:
        if name in existing:
            print(f"  . skip (exists): {name}")
            continue
        res = pipe.ingest_text(text, source=name)
        DocumentModel.insert(
            res.doc_id, filename=name, source=name,
            size_bytes=len(text.encode("utf-8")),
            char_count=res.char_count, chunk_count=res.chunk_count,
            file_type="txt",
        )
        print(f"  [OK] {name} -> {res.chunk_count} chunk(s)")
        added += 1

    print(f"\n[OK] Done. {added} new documents seeded "
          f"({pipe.store.count()} vectors total).")


if __name__ == "__main__":
    main()
