"""Open a pull request with the agent's validated fix.

Everything here goes through the GitHub REST API rather than shelling out to
git. The Cloud Run container has no git binary and no clone -- only a copy of
the model files baked into the image -- so branch/commit/PR are done as API
calls against the remote repository.

The deliberate constraint: this only ever writes to a new branch and opens a
pull request. It never pushes to the default branch. An agent that can put
code into production unreviewed is a different risk category, and nothing here
needs that to be useful.
"""

from __future__ import annotations

import base64
import logging
import time

import requests

from app.config import config

log = logging.getLogger("pipeline-medic")

API = "https://api.github.com"
TIMEOUT = 30


class GitHubError(RuntimeError):
    pass


def _clip(text: str, limit: int) -> str:
    """Trim to `limit` characters on a word boundary.

    A hard slice cuts mid-word -- "renamed the customer_id column to cus" --
    which looks like a bug in a PR title.
    """
    text = " ".join(text.split())
    if len(text) <= limit:
        return text.rstrip(".")
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:") + "…"


def _headers() -> dict:
    token = config.github_token()
    if not token:
        raise GitHubError(
            "no GitHub token available: set GITHUB_TOKEN, or mount the "
            "github-token secret into the service"
        )
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _request(method: str, path: str, payload: dict | None = None) -> dict:
    """One GitHub API call, retried through transient network failures.

    Only connection-level failures are retried. A 4xx is a real answer --
    a bad token, a branch that already exists -- and retrying would just
    delay the error by three seconds.
    """
    last: Exception | None = None
    for attempt in range(3):
        try:
            r = requests.request(
                method,
                f"{API}{path}",
                headers=_headers(),
                json=payload,
                timeout=TIMEOUT,
            )
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as exc:
            last = exc
            if attempt < 2:
                time.sleep(1.0 * (2**attempt))
            continue
        if r.status_code >= 400:
            raise GitHubError(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json()
    raise GitHubError(f"{method} {path} failed after retries: {last}")


def _get(path: str) -> dict:
    return _request("GET", path)


def _post(path: str, payload: dict) -> dict:
    return _request("POST", path, payload)


def _put(path: str, payload: dict) -> dict:
    return _request("PUT", path, payload)


def open_fix_pull_request(
    model_name: str,
    fixed_sql: str,
    root_cause: str,
    explanation: str,
    run_id: str,
) -> dict:
    """Create a branch, commit the fixed SQL, and open a pull request.

    Returns {"pr_url": ..., "branch": ...} on success.
    Raises GitHubError with a readable message on any failure.
    """
    repo = config.github_repo
    path = f"demo/models/{model_name}.sql"
    branch = f"pipeline-medic/fix-{model_name}-{run_id}"

    # Base the branch on whatever the repo's default branch currently is,
    # rather than assuming "main".
    default_branch = _get(f"/repos/{repo}")["default_branch"]
    base_sha = _get(f"/repos/{repo}/git/ref/heads/{default_branch}")["object"]["sha"]

    _post(f"/repos/{repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": base_sha})

    # Updating a file requires the blob sha of the version being replaced.
    current_sha = _get(f"/repos/{repo}/contents/{path}?ref={default_branch}")["sha"]

    content = fixed_sql if fixed_sql.endswith("\n") else fixed_sql + "\n"
    _put(
        f"/repos/{repo}/contents/{path}",
        {
            "message": f"Fix {model_name}: {_clip(root_cause, 60)}",
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "sha": current_sha,
            "branch": branch,
        },
    )

    body = f"""### Root cause

{root_cause}

### What changed

{explanation}

### Validation

This SQL was validated against BigQuery with a dry run before this pull
request was opened. The warehouse confirmed it compiles against the current
table schemas.

---

Opened autonomously by [Pipeline Medic](https://github.com/{repo}) · triage run `{run_id}`
"""

    pr = _post(
        f"/repos/{repo}/pulls",
        {
            "title": f"Fix {model_name}: {_clip(root_cause, 70)}",
            "head": branch,
            "base": default_branch,
            "body": body,
        },
    )
    log.info("opened PR %s for run %s", pr.get("html_url"), run_id)
    return {"pr_url": pr.get("html_url"), "branch": branch}
