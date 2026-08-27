## Inspiration

A pipeline fails at 3am. The alert says `Name customer_id not found inside c`.

That message is a symptom, not a cause. Someone gets paged, opens six tabs, compares the model SQL against the current warehouse schema, and eventually discovers that an upstream team renamed a column three days ago. The fix is one line. Finding it took forty minutes — almost all of it spent re-deriving context a machine could have gathered in seconds.

I wanted to automate the part that actually hurts. Not the typing — the diagnosis.

## What it does

Pipeline Medic is an autonomous on-call agent for a data warehouse. When a pipeline model breaks, it:

1. Reads the failing model's SQL
2. Inspects what the upstream tables **actually** contain right now — not what the error claims
3. Forms a hypothesis about the root cause
4. Writes a corrected version of the model
5. **Proves the fix works** by dry-running it against BigQuery
6. If BigQuery rejects it, reads the real compiler error, revises, and tries again
7. **Opens a pull request** with the validated fix — branch, commit, and a PR body explaining the root cause

Then it records the verdict, the reasoning, and the validated SQL — and goes back to sleep.

Step 7 is what makes it a Taskmaster rather than an advisor. It doesn't hand you a suggestion to evaluate; it does the work and leaves a reviewable pull request. [PR #1 on the repo](https://github.com/damowdhar/pipeline-medic/pull/1) was opened by the agent, unattended, from a single Pub/Sub message.

It never writes to the default branch. Merging stays a human decision — an agent that can put code into production unreviewed is a different risk category, and nothing here needs that to be useful.

## The part I care about most: it isn't allowed to guess

Most "AI fixes your code" demos produce a plausible patch and hand it to a human to evaluate. That doesn't remove the work, it relocates it. You still have to read the diff, reason about whether it's right, and test it — which is most of the original job.

Pipeline Medic is required to *demonstrate* that its fix is correct before it says anything. Its key tool is BigQuery's **dry-run** mode, which type-checks a query against live table schemas without executing it and without cost. That gives the agent a ground-truth oracle it can consult as many times as it needs.

So the agent is never trusted to be right the first time. It's required to iterate until the warehouse itself confirms the SQL compiles. A fix that never validates is reported honestly as `needs_human`, with what was ruled out — rather than dressed up as an answer. An honest non-answer is more useful than a confident wrong one.

## A real run

The demo scenario is an upstream column rename (`customer_id` → `cust_id`). From a cold start:

```
root cause  : The upstream table raw_customers renamed the customer_id column
              to cust_id, causing references to c.customer_id to fail.
validated   : True
confidence  : high
tool calls  : 6
dry runs    : 1
```

The detail I didn't expect: the agent kept `AS customer_id` as the *output* column name while switching the source to `c.cust_id` — preserving the contract for every downstream consumer. Nothing in the prompt told it to do that. Renaming the output column would also have compiled cleanly and silently broken everything downstream.

## How I built it

- **Gemini 3.7 Flash** on Vertex AI does the reasoning
- **Google ADK** (`google-adk` 2.7.1) provides the agent loop — an `LlmAgent` with six function tools: `read_model_sql`, `list_tables`, `get_table_schema`, `dry_run_sql`, `run_query`, `list_models`
- **Cloud Run** hosts a FastAPI service
- **Pub/Sub** delivers failure events from the scheduler
- **Firestore** stores every triage run
- **BigQuery** is both the warehouse being repaired and the oracle that validates the repairs

**Asynchronous by design.** The Pub/Sub endpoint acknowledges the message *immediately* and runs triage in a background task. Triage takes several model turns and multiple BigQuery round trips — far longer than Pub/Sub's ack deadline. Acking first is what prevents redelivery from running the same triage twice, and it's what makes the agent genuinely fire-and-forget. Nobody is waiting on an HTTP response.

**Memory.** Every run is written to Firestore. When a model that has failed before fails again, prior confirmed fixes are fed back as context, so recurring breakages get faster rather than being re-derived from scratch each time.

## Challenges I ran into

**Gemini 3.x is not served from regional Vertex endpoints.** Every quickstart hardcodes something like `us-central1`. With a regional location, every Gemini 3.x model returns HTTP 404 — which reads exactly like a permissions or allowlist problem, and sends you off to check IAM for an hour. The models are only available at `location=global`. I found this by probing `generateContent` across both model IDs and locations, and it's now documented in the config module so nobody repeats it.

**Firestore silently ignores your database.** My database is named `hackathon`. Every client library defaults to `(default)` unless you pass the database ID explicitly — and it doesn't error, it just reads and writes an empty database that nobody looks at. Writes appeared to succeed. Nothing was there.

**A false negative that cost real time.** My first availability probe returned HTTP 417 for *every* model, including ones I knew existed. That turned out to be PowerShell's `Expect: 100-continue` header, not Vertex at all. The lesson I keep relearning: when every case fails identically, suspect the harness before the system under test.

**Dates aren't JSON.** BigQuery returns `datetime.date` objects, which can't be serialized back into the next model turn. The agent crashed mid-run the first time it sampled data. Every value crossing the tool boundary now gets coerced.

## What I learned

The most valuable thing I did was give the agent a **ground-truth oracle** rather than a better prompt. Once `dry_run_sql` existed, the quality of the output stopped depending on whether the model happened to reason correctly on the first pass. It could just check. That reframes the whole design problem: instead of asking "how do I make the model right more often," ask "what can this agent consult to find out whether it's right?"

The second lesson is about honesty as a feature. Building in an explicit `needs_human` path — with reasoning about what was ruled out — made the agent more useful, not less. An autonomous system you can't trust to say "I don't know" is one you have to double-check every time, which defeats the point.

## What's next

- Learn from rejected fixes, not just accepted ones — a closed PR is a signal, and right now it's ignored
- Expand beyond schema drift to data-quality failures: row-count collapses, null spikes, grain changes
