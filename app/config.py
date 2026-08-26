"""Central configuration for Pipeline Medic.

Two settings here are load-bearing and easy to get wrong:

1. VERTEX_LOCATION is "global", not a region. Gemini 3.x is only served from
   the global endpoint on Vertex AI -- a regional location (us-central1 etc.)
   returns HTTP 404 "model not found", which reads like a permissions problem
   but isn't. Cloud Run itself still runs in a region; only the model client
   uses "global".

2. FIRESTORE_DATABASE is "hackathon", not "(default)". Every Firestore client
   library silently connects to "(default)" unless the database id is passed
   explicitly, so leaving this unset produces empty reads rather than an error.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


@dataclass(frozen=True)
class Config:
    project_id: str = _env("GOOGLE_CLOUD_PROJECT", "dm-agentic-hackathon-2026")

    # Vertex AI. See note 1 above -- must stay "global" for Gemini 3.x.
    vertex_location: str = _env("GOOGLE_CLOUD_LOCATION", "global")
    model: str = _env("MEDIC_MODEL", "gemini-3.7-flash")

    # Firestore. See note 2 above -- the database is named, not "(default)".
    firestore_database: str = _env("FIRESTORE_DATABASE", "hackathon")
    runs_collection: str = _env("MEDIC_RUNS_COLLECTION", "triage_runs")

    # Where the demo warehouse lives.
    bq_dataset: str = _env("MEDIC_BQ_DATASET", "medic_demo")
    bq_location: str = _env("MEDIC_BQ_LOCATION", "US")

    # Cloud Run / Pub/Sub.
    region: str = _env("MEDIC_REGION", "us-central1")
    pubsub_topic: str = _env("MEDIC_PUBSUB_TOPIC", "pipeline-failures")
    port: int = int(_env("PORT", "8080"))

    # Safety rail: the agent proposes fixes but never pushes without this on.
    allow_pull_requests: bool = _env("MEDIC_ALLOW_PRS", "false").lower() == "true"

    def use_vertex_env(self) -> None:
        """Point the google-genai SDK at Vertex AI rather than the public API.

        The SDK reads these from the environment at client construction time,
        so this must run before any model client is built.
        """
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
        os.environ["GOOGLE_CLOUD_PROJECT"] = self.project_id
        os.environ["GOOGLE_CLOUD_LOCATION"] = self.vertex_location


config = Config()
