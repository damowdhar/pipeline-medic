# Demo video script (~4 minutes)

The brief asks for three things: the problem, the value proposition, and the app in action — plus visible proof the backend runs on Google Cloud. Judges reward *autonomous action over chat*, so the centrepiece is the agent working while nobody touches the keyboard.

**Record at 1080p minimum. Increase your terminal font size before you start** — judges often watch on laptops, and unreadable terminal text is the most common way a good demo loses points.

---

## 0:00 – 0:30 · The problem

**Screen:** the failing pipeline. Run `python -m demo.break_it` and let the real error land on screen.

> "This is a data pipeline failing at three in the morning. The error says `Name customer_id not found inside c`.
>
> That tells you a symptom, not a cause. Somebody now gets paged, opens six tabs, compares the model against the warehouse schema, and eventually finds that an upstream team renamed a column three days ago. The fix is one line. Finding it takes forty minutes."

Don't rush this. The pain has to land before the solution means anything — and not every judge is a data engineer.

## 0:30 – 1:00 · What it does, and why it's different

**Screen:** the architecture diagram (`docs/architecture.png`).

> "Pipeline Medic is an autonomous agent that does that diagnosis itself. Gemini 3.7 Flash on Vertex AI, built with Google's ADK, running on Cloud Run and triggered by Pub/Sub.
>
> But the thing I care about most is this: it isn't allowed to guess.
>
> Most AI-fixes-your-code demos hand you a plausible patch and ask you to check it — which doesn't remove the work, it just moves it. Pipeline Medic has to *prove* its fix works before it says anything. It uses BigQuery's dry-run mode as an oracle: it can test a candidate fix against real schemas, for free, as many times as it needs. If BigQuery rejects it, it reads the real error and tries again."

## 1:00 – 2:30 · The agent working, autonomously

**Screen:** split view — terminal on the left, Cloud Run logs streaming on the right.

Publish the failure to Pub/Sub, then **take your hands off the keyboard**:

```bash
python -m demo.break_it
gcloud run services logs read pipeline-medic --region us-central1 --limit 30
```

> "I've published the failure to Pub/Sub. That's the last thing I do — from here nobody is driving.
>
> The service acknowledges the message immediately and triages in the background. That's deliberate: triage takes several model turns and multiple BigQuery round trips, far longer than Pub/Sub's ack deadline. Acking first is what stops the same triage running twice."

Narrate the tool calls as they scroll past — reading the model, listing tables, inspecting the live schema, then the dry run.

> "There — it just inspected what `raw_customers` actually contains today, and found `cust_id` where the model expects `customer_id`. Now it's writing a fix and dry-running it against BigQuery."

**Screen:** the verdict.

> "Root cause identified. Validated: true — BigQuery itself confirmed this compiles. Six tool calls, no human input.
>
> And look at this detail. It kept `AS customer_id` as the *output* column while switching the source to `cust_id`. Renaming the output would also have compiled — and silently broken every dashboard downstream. Nothing in the prompt told it to be careful about that."

That last beat is the strongest thirty seconds in the demo. Don't cut it.

## 2:30 – 3:15 · Proof it runs on Google Cloud

**Screen:** the Cloud Console. This is explicitly required — show real infrastructure, not localhost.

Show, in order:

1. **Cloud Run** → the `pipeline-medic` service, green, with its `.run.app` URL
2. **The live URL** → hit `/health` in a browser, showing `gemini-3.7-flash` and `location: global`
3. **Cloud Run logs** → the triage that just ran
4. **Firestore** → the `triage_runs` collection, with real verdicts
5. **Pub/Sub** → the `pipeline-failures` topic and its push subscription

> "Everything you just saw ran on Google Cloud. Cloud Run hosting the agent, Pub/Sub delivering the failure, Firestore holding every verdict, and BigQuery serving as both the warehouse being repaired and the oracle validating the repair."

## 3:15 – 4:00 · Memory, honesty, and close

**Screen:** the `/runs` endpoint or the Firestore collection.

> "Every run is recorded. When a model that's failed before fails again, those confirmed fixes come back as context — so recurring breakages get faster instead of being re-derived from scratch.
>
> And when it *can't* find a validated fix, it says so, with what it ruled out. It doesn't dress up a guess as an answer. An autonomous system you can't trust to say 'I don't know' is one you have to double-check every time — which defeats the point of it being autonomous.
>
> That's Pipeline Medic. It takes the forty-minute part of a 3am page and does it before anyone wakes up."

---

## Checklist before you upload

- [ ] Under 4 minutes (hard limit — overruns are penalised)
- [ ] Cloud Console visibly on screen (explicitly required)
- [ ] The `.run.app` URL readable at least once
- [ ] Terminal font large enough to read on a laptop
- [ ] Uploaded to **YouTube or Vimeo**, set **public** — not unlisted, not private
- [ ] No Nextiva material anywhere on screen: close work tabs, clear bookmarks bar, use a clean browser profile
- [ ] No credentials, project numbers, or billing IDs visible

That second-to-last point deserves a real check. Your bookmarks bar shows work folders, and a browser recording will capture them.
