"""Tools the agent uses to diagnose and fix a broken pipeline model.

The important one is `dry_run_sql`. BigQuery's dry-run mode validates a query
against real table schemas without executing it or incurring cost, which gives
the agent a ground-truth oracle: it can test a candidate fix and get a real
compiler error back instead of guessing. That closes the loop -- the agent is
not asked to be right first time, it is asked to iterate until the warehouse
says the SQL is valid.
"""

from __future__ import annotations

from pathlib import Path

from google.api_core.exceptions import BadRequest, NotFound
from google.cloud import bigquery

from app.config import config

MODELS_DIR = Path(__file__).resolve().parent.parent / "demo" / "models"

_client: bigquery.Client | None = None


def _bq() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=config.project_id)
    return _client


def list_models() -> dict:
    """List the SQL models in the pipeline that this agent can inspect.

    Returns:
        A dict with a "models" key holding the model names (no .sql suffix).
    """
    if not MODELS_DIR.exists():
        return {"models": [], "error": f"models directory not found: {MODELS_DIR}"}
    return {"models": sorted(p.stem for p in MODELS_DIR.glob("*.sql"))}


def read_model_sql(model_name: str) -> dict:
    """Read the current SQL source of a pipeline model.

    Args:
        model_name: Model name without the .sql suffix, e.g. "dim_customers".

    Returns:
        A dict with "model_name" and "sql", or an "error" key if not found.
    """
    path = MODELS_DIR / f"{model_name}.sql"
    if not path.exists():
        return {"error": f"no such model: {model_name}", "available": list_models()["models"]}
    return {"model_name": model_name, "sql": path.read_text(encoding="utf-8")}


def get_table_schema(table_name: str) -> dict:
    """Inspect the live column names and types of a table in the warehouse.

    Use this to find out what the upstream data actually looks like now, which
    is often different from what the model SQL assumes.

    Args:
        table_name: Table name within the demo dataset, e.g. "raw_customers".

    Returns:
        A dict with "table" and "columns" (a list of {name, type} dicts).
    """
    table_id = f"{config.project_id}.{config.bq_dataset}.{table_name}"
    try:
        table = _bq().get_table(table_id)
    except NotFound:
        return {"error": f"table not found: {table_id}"}
    return {
        "table": table_id,
        "columns": [{"name": f.name, "type": f.field_type} for f in table.schema],
    }


def list_tables() -> dict:
    """List every table available in the demo warehouse dataset.

    Returns:
        A dict with a "tables" key holding table names.
    """
    dataset_id = f"{config.project_id}.{config.bq_dataset}"
    try:
        tables = list(_bq().list_tables(dataset_id))
    except NotFound:
        return {"error": f"dataset not found: {dataset_id}"}
    return {"tables": sorted(t.table_id for t in tables)}


def dry_run_sql(sql: str) -> dict:
    """Validate SQL against the real warehouse without running it.

    This is the agent's oracle for whether a proposed fix actually works. A
    dry run type-checks the query against live schemas, costs nothing, and
    returns BigQuery's own error message when the SQL is wrong.

    Args:
        sql: The full SQL query to validate.

    Returns:
        {"valid": true, "bytes_scanned": N} when the SQL compiles, otherwise
        {"valid": false, "error": "<BigQuery's error message>"}.
    """
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    try:
        job = _bq().query(sql, job_config=job_config, location=config.bq_location)
    except BadRequest as exc:
        return {"valid": False, "error": str(exc.message or exc)}
    except Exception as exc:  # surface anything else to the model verbatim
        return {"valid": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"valid": True, "bytes_scanned": job.total_bytes_processed}


def open_pull_request(
    model_name: str,
    fixed_sql: str,
    root_cause: str,
    explanation: str,
    run_id: str,
) -> dict:
    """Open a pull request containing a validated fix.

    Call this ONLY after dry_run_sql has confirmed the SQL is valid. Never
    call it with SQL you have not validated -- the whole point of this agent
    is that it does not propose guesses.

    Args:
        model_name: The model being fixed, e.g. "dim_customers".
        fixed_sql: The full corrected SQL, already validated.
        root_cause: One or two sentences on what actually broke.
        explanation: What changed and why, for the pull request body.
        run_id: The triage run id given to you in the task.

    Returns:
        {"opened": true, "pr_url": ...} on success, or {"opened": false,
        "reason": ...} if pull requests are disabled or GitHub rejected it.
    """
    if not config.allow_pull_requests:
        return {
            "opened": False,
            "reason": "pull requests are disabled (MEDIC_ALLOW_PRS is false)",
        }

    # Imported here so a missing token or GitHub outage can never stop the
    # rest of the triage from running.
    from app import github_pr

    try:
        result = github_pr.open_fix_pull_request(
            model_name=model_name,
            fixed_sql=fixed_sql,
            root_cause=root_cause,
            explanation=explanation,
            run_id=run_id,
        )
    except Exception as exc:
        return {"opened": False, "reason": f"{type(exc).__name__}: {exc}"}
    return {"opened": True, **result}


def _jsonable(value):
    """Coerce BigQuery values into something JSON-serializable.

    Rows come back holding date/datetime/Decimal/bytes objects. These have to
    survive a json.dumps on their way into the next model turn, so anything
    the encoder won't accept becomes a string.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return str(value)


def run_query(sql: str, max_rows: int = 20) -> dict:
    """Execute a SELECT query and return a small sample of rows.

    Use sparingly, and only after dry_run_sql reports the query is valid --
    this one actually scans data. Useful for confirming a fix returns sensible
    values rather than merely compiling.

    Args:
        sql: The SQL to execute.
        max_rows: Maximum rows to return (capped at 50).

    Returns:
        A dict with "rows", or an "error" key.
    """
    capped = min(max_rows, 50)
    try:
        job = _bq().query(sql, location=config.bq_location)
        rows = [_jsonable(dict(r)) for r in job.result(max_results=capped)]
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    return {"row_count": len(rows), "rows": rows}
