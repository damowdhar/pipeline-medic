"""Run one triage locally, end to end, without deploying anything.

    python -m demo.local_test
"""

from __future__ import annotations

import asyncio
import json

from app.agent import triage
from demo.break_it import run_model


async def main() -> None:
    failure = run_model()
    if not failure:
        print("Model compiles cleanly -- nothing to triage. Re-run demo.seed?")
        return

    print("=" * 70)
    print("PIPELINE FAILURE")
    print("=" * 70)
    print(f"model: {failure['model_name']}")
    print(f"error: {failure['error'][:400]}")
    print()
    print("Handing to agent...\n")

    verdict = await triage(failure)

    print("=" * 70)
    print("AGENT VERDICT")
    print("=" * 70)
    print(f"root cause     : {verdict.get('root_cause')}")
    print(f"validated      : {verdict.get('validated')}")
    print(f"confidence     : {verdict.get('confidence')}")
    print(f"dry runs       : {verdict.get('dry_run_attempts')}")
    print(f"tool calls     : {verdict.get('tool_calls')}")
    print(f"run id         : {verdict.get('run_id')}")
    print()
    print("fixed SQL:")
    print(verdict.get("fixed_sql", "(none)"))
    print()
    if "error" in verdict:
        print("RAW OUTPUT (parse failed):")
        print(json.dumps(verdict, indent=2)[:3000])


if __name__ == "__main__":
    asyncio.run(main())
