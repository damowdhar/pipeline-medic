"""Firestore-backed record of every triage run.

Note the explicit `database=` argument. This project's Firestore database is
named "hackathon"; the client library defaults to "(default)" and would
silently read and write an empty database that nobody ever looks at.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from google.cloud import firestore

from app.config import config

_db: firestore.Client | None = None


def db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(
            project=config.project_id,
            database=config.firestore_database,  # see module docstring
        )
    return _db


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def start_run(run_id: str, failure: dict[str, Any]) -> None:
    """Record that triage has begun for a failed pipeline run."""
    db().collection(config.runs_collection).document(run_id).set(
        {
            "run_id": run_id,
            "status": "in_progress",
            "failure": failure,
            "started_at": _now(),
        }
    )


def finish_run(run_id: str, status: str, result: dict[str, Any]) -> None:
    """Record the agent's verdict for a run."""
    db().collection(config.runs_collection).document(run_id).set(
        {
            "status": status,
            "result": result,
            "finished_at": _now(),
        },
        merge=True,
    )


def get_run(run_id: str) -> dict[str, Any] | None:
    snap = db().collection(config.runs_collection).document(run_id).get()
    return snap.to_dict() if snap.exists else None


def recent_runs(limit: int = 20) -> list[dict[str, Any]]:
    query = (
        db()
        .collection(config.runs_collection)
        .order_by("started_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )
    return [d.to_dict() for d in query.stream()]


def similar_past_fixes(model_name: str, limit: int = 5) -> list[dict[str, Any]]:
    """Past successful fixes for the same model.

    Fed to the agent as prior context so repeated breakages get faster and more
    consistent rather than being re-derived from scratch every time.
    """
    query = (
        db()
        .collection(config.runs_collection)
        .where(filter=firestore.FieldFilter("result.model_name", "==", model_name))
        .where(filter=firestore.FieldFilter("status", "==", "fixed"))
        .limit(limit)
    )
    try:
        return [d.to_dict() for d in query.stream()]
    except Exception:
        # A composite index may not exist yet; prior context is a nicety, not
        # a requirement, so degrade quietly rather than failing the triage.
        return []
