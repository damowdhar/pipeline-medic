"""The Pipeline Medic agent.

Given a failed pipeline run, the agent works the problem the way an on-call
data engineer would: read the model, look at what the upstream tables actually
contain now, form a hypothesis, then *prove* it by dry-running a candidate fix
against BigQuery before proposing anything.

The dry-run loop is what makes this autonomous rather than suggestive. The
agent is not trusted to be right -- it is required to demonstrate it is right,
and it keeps iterating while BigQuery says no.
"""

from __future__ import annotations

import json
import uuid

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from app import state, tools
from app.config import config

config.use_vertex_env()  # must run before any model client is constructed

INSTRUCTION = """
You are Pipeline Medic, an autonomous on-call agent for a data warehouse.

A pipeline model has failed. Your job is to find the true root cause and
produce a fix that you have PROVEN works. You are not writing a suggestion for
a human to evaluate -- you are doing the repair.

Work in this order:

1. Read the failing model's SQL with read_model_sql.
2. Inspect what the upstream tables actually look like right now, using
   list_tables and get_table_schema. Do not trust the error message alone;
   it names a symptom, not always the cause.
3. Form a specific hypothesis about the root cause. Common causes are an
   upstream column being renamed, retyped, or dropped; a join key changing
   grain; or a filter referencing a value that no longer exists.
4. Write a corrected version of the FULL model SQL.
5. Validate it with dry_run_sql. If it reports valid: false, read BigQuery's
   error, revise, and try again. Keep going until it is valid. Do not give up
   after one attempt and do not propose SQL you have not validated.
6. Optionally sanity-check the result with run_query on a small sample to
   confirm the fix returns plausible data, not just compilable SQL.
7. Once — and only once — dry_run_sql reports valid, call open_pull_request
   with the validated SQL. Never call it with SQL you have not validated.
   If it returns opened: false, that is fine; carry on and report the fix
   anyway. The reason will be recorded.

When you are done, reply with ONLY a JSON object, no prose and no code fences:

{
  "model_name": "<the model you fixed>",
  "root_cause": "<one or two sentences, plain language, no jargon>",
  "confidence": "high" | "medium" | "low",
  "fixed_sql": "<the full corrected SQL, validated>",
  "validated": true | false,
  "dry_run_attempts": <integer>,
  "explanation": "<what you changed and why, for the pull request body>",
  "pr_url": "<the pull request URL, or null if none was opened>"
}

If you genuinely cannot find a fix, return the same object with
"validated": false and explain in "root_cause" what you ruled out. An honest
non-answer is more useful than an unvalidated guess.
""".strip()


def build_agent() -> LlmAgent:
    return LlmAgent(
        name="pipeline_medic",
        model=config.model,
        description="Diagnoses and repairs failed data pipeline models.",
        instruction=INSTRUCTION,
        tools=[
            tools.list_models,
            tools.read_model_sql,
            tools.list_tables,
            tools.get_table_schema,
            tools.dry_run_sql,
            tools.run_query,
            tools.open_pull_request,
        ],
        generate_content_config=types.GenerateContentConfig(temperature=0.0),
    )


def _extract_json(text: str) -> dict:
    """Pull the JSON verdict out of the model's final message.

    Models occasionally wrap JSON in fences despite instructions, so fall back
    to the outermost brace pair rather than failing the whole run over it.
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    return {"error": "could not parse agent verdict", "raw": text[:2000]}


async def triage(failure: dict, run_id: str | None = None) -> dict:
    """Run one full triage. Returns the agent's verdict as a dict."""
    run_id = run_id or f"run-{uuid.uuid4().hex[:12]}"
    state.start_run(run_id, failure)

    prior = state.similar_past_fixes(failure.get("model_name", ""))
    prior_note = ""
    if prior:
        prior_note = (
            "\n\nThis model has failed before. Previously confirmed fixes:\n"
            + json.dumps([p.get("result", {}) for p in prior], indent=2)[:4000]
        )

    prompt = (
        f"A pipeline run failed.\n\n"
        f"Model: {failure.get('model_name', '(unknown)')}\n"
        f"Run id: {run_id}\n"
        f"Error reported by the scheduler:\n{failure.get('error', '(none provided)')}"
        f"{prior_note}"
    )

    runner = InMemoryRunner(agent=build_agent(), app_name="pipeline-medic")
    session = await runner.session_service.create_session(
        app_name="pipeline-medic", user_id="scheduler"
    )

    final_text = ""
    tool_calls = 0
    async for event in runner.run_async(
        user_id="scheduler",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "function_call", None):
                    tool_calls += 1
                if getattr(part, "text", None):
                    final_text = part.text

    verdict = _extract_json(final_text)
    verdict["tool_calls"] = tool_calls
    verdict["run_id"] = run_id

    status = "fixed" if verdict.get("validated") else "needs_human"
    state.finish_run(run_id, status, verdict)
    return verdict
