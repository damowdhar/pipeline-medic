"""Run the pipeline, let it fail, and hand the failure to the agent.

This stands in for whatever scheduler you actually use. It executes the model
SQL, captures the real BigQuery error, and emits it the same way a production
scheduler would -- as a Pub/Sub message the agent picks up asynchronously.

Run:
    python -m demo.break_it                 # publish to Pub/Sub (async path)
    python -m demo.break_it --local         # POST to a locally running server
    python -m demo.break_it --url <URL>     # POST to a deployed Cloud Run URL
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from google.cloud import bigquery

from app.config import config

MODEL_NAME = "dim_customers"
MODEL_PATH = Path(__file__).resolve().parent / "models" / f"{MODEL_NAME}.sql"


def run_model() -> dict:
    """Execute the model and return a failure payload, or None if it passed."""
    sql = MODEL_PATH.read_text(encoding="utf-8")
    client = bigquery.Client(project=config.project_id)
    try:
        client.query(
            sql,
            job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False),
            location=config.bq_location,
        )
    except Exception as exc:
        message = getattr(exc, "message", None) or str(exc)
        return {
            "run_id": f"run-{uuid.uuid4().hex[:12]}",
            "model_name": MODEL_NAME,
            "error": message,
            "scheduler": "demo",
        }
    return {}


def publish(failure: dict) -> None:
    from google.cloud import pubsub_v1

    publisher = pubsub_v1.PublisherClient()
    topic = publisher.topic_path(config.project_id, config.pubsub_topic)
    future = publisher.publish(topic, json.dumps(failure).encode("utf-8"))
    print(f"published to {topic} (message id {future.result()})")
    print("The agent will pick this up asynchronously. Watch it with:")
    print(f"  gcloud run services logs tail pipeline-medic --region {config.region}")


def post(url: str, failure: dict) -> None:
    import urllib.request

    req = urllib.request.Request(
        url.rstrip("/") + "/triage",
        data=json.dumps(failure).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        print(json.dumps(json.loads(resp.read()), indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true", help="POST to http://localhost:8080")
    parser.add_argument("--url", help="POST to a deployed service URL")
    args = parser.parse_args()

    failure = run_model()
    if not failure:
        print(f"{MODEL_NAME} compiled cleanly -- nothing to triage.")
        print("Has the agent already fixed it? Check demo/models/ or re-run demo.seed.")
        return 0

    print("Pipeline failed as expected:\n")
    print(f"  model: {failure['model_name']}")
    print(f"  error: {failure['error'][:300]}\n")

    if args.url:
        post(args.url, failure)
    elif args.local:
        post("http://localhost:8080", failure)
    else:
        publish(failure)
    return 0


if __name__ == "__main__":
    sys.exit(main())
