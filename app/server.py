"""Cloud Run service: the always-on half of the agent.

The Pub/Sub push endpoint acknowledges immediately and does the triage in a
background task. That is deliberate -- triage involves several model turns and
BigQuery round trips and will blow past Pub/Sub's ack deadline, causing the
message to be redelivered and the whole triage to run twice. Acking first and
working after is what makes this genuinely asynchronous: nobody is waiting on
the HTTP response, and the agent keeps working after the caller has gone.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import uuid

from fastapi import BackgroundTasks, FastAPI, Request, Response

from app import state
from app.agent import triage
from app.config import config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pipeline-medic")

app = FastAPI(title="Pipeline Medic")


# NOT "/healthz": Google's frontend reserves that path on *.run.app and
# intercepts it before the request reaches the container, returning its own
# 404. The route registers fine and shows up in /openapi.json, it just never
# receives traffic. Any other path works.
@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "model": config.model,
        "vertex_location": config.vertex_location,
        "firestore_database": config.firestore_database,
    }


async def _run_triage(failure: dict, run_id: str) -> None:
    try:
        verdict = await triage(failure, run_id=run_id)
        log.info(
            "triage %s finished: validated=%s attempts=%s",
            run_id,
            verdict.get("validated"),
            verdict.get("dry_run_attempts"),
        )
    except Exception:
        log.exception("triage %s failed", run_id)
        state.finish_run(run_id, "error", {"error": "triage raised; see logs"})


@app.post("/pubsub")
async def pubsub_push(request: Request, background: BackgroundTasks) -> Response:
    """Pub/Sub push endpoint. Acks immediately, triages in the background."""
    envelope = await request.json()
    message = (envelope or {}).get("message") or {}

    raw = message.get("data")
    if not raw:
        # Nothing to work with. Ack anyway -- returning an error would make
        # Pub/Sub redeliver a message that will never be valid.
        log.warning("pubsub message had no data field; acking")
        return Response(status_code=204)

    try:
        failure = json.loads(base64.b64decode(raw).decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        log.warning("undecodable pubsub payload (%s); acking to avoid redelivery", exc)
        return Response(status_code=204)

    run_id = failure.get("run_id") or message.get("messageId") or f"run-{uuid.uuid4().hex[:12]}"
    log.info("accepted failure for model=%s run_id=%s", failure.get("model_name"), run_id)

    background.add_task(_run_triage, failure, run_id)
    return Response(status_code=204)


@app.post("/triage")
async def triage_now(request: Request) -> dict:
    """Synchronous triage, for local testing and for the demo video.

    Same code path as the Pub/Sub route, but waits for the verdict so you can
    watch it happen.
    """
    failure = await request.json()
    return await triage(failure)


@app.get("/runs")
def runs(limit: int = 20) -> dict:
    """Recent triage runs, newest first."""
    return {"runs": state.recent_runs(limit=limit)}


@app.get("/runs/{run_id}")
def run_detail(run_id: str) -> dict:
    return state.get_run(run_id) or {"error": "not found", "run_id": run_id}
