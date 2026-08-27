# Recording runbook

Everything you need to produce the demo video and get its URL. The narration is in [demo-script.md](demo-script.md); this is the mechanical side.

Budget about 45 minutes including retakes.

---

## 1 · Pre-flight (5 min, do this before recording)

**Hide work material.** Every screenshot you've taken so far shows Nextiva, OBIEE, MSTR, and HADOOP bookmark folders. A recording will capture them.

- `Ctrl+Shift+B` in Chrome hides the bookmarks bar
- Close work tabs, or record in a **separate Chrome profile** signed into your personal account only
- Close Outlook, Teams, Slack — notification popups land in the middle of takes

**Make the terminal readable.** This is the single most common way a good demo loses points. In Windows Terminal: `Ctrl+,` → Appearance → font size **16–18**. Judges watch on laptops.

**Set the credentials in the shell you'll record.** Without this, BigQuery calls fail on camera:

```powershell
cd C:\Users\DamowdharMallem\hackathon\pipeline-medic
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\Users\DamowdharMallem\hackathon\.gcloud\application_default_credentials.json"
```

**Warm up Cloud Run.** It scales to zero, so the first request after idling has a cold start that stalls your demo:

```powershell
curl.exe -s https://pipeline-medic-333215501397.us-central1.run.app/health
```

**Confirm the pipeline is still broken** (it should be — the agent proposes fixes, it never edits the file):

```powershell
.\.venv\Scripts\python.exe -m demo.break_it --local
```

Press `Ctrl+C` when it tries to connect. You only want to see the failure message.

---

## 2 · Window layout

Two windows side by side:

- **Left:** terminal, in the project directory
- **Right:** Chrome with four tabs pre-opened, in this order:

```
1. https://console.cloud.google.com/run/detail/us-central1/pipeline-medic/metrics?project=dm-agentic-hackathon-2026
2. https://pipeline-medic-333215501397.us-central1.run.app/health
3. https://pipeline-medic-333215501397.us-central1.run.app/runs
4. https://console.cloud.google.com/firestore/databases/hackathon/data/panel/triage_runs?project=dm-agentic-hackathon-2026
```

Tick **Pretty-print** on tabs 2 and 3 before you start. Raw JSON is unreadable on video.

---

## 3 · The command sequence

Run these in order while narrating. Nothing else.

**Show the failure (0:00):**

```powershell
.\.venv\Scripts\python.exe -m demo.break_it
```

This prints the real BigQuery error *and* publishes to Pub/Sub. One command covers your opening and your trigger.

**Then take your hands off the keyboard** and start the log tail:

```powershell
gcloud run services logs read pipeline-medic --region us-central1 --project dm-agentic-hackathon-2026 --limit 30
```

Triage takes about 90 seconds. Narrate the Gemini turns as they scroll. This is the heart of the demo — the agent working while nobody drives.

**Show the verdict** — switch to Chrome tab 3 (`/runs`) and refresh. Your newest run is first.

**Then the Cloud Console tabs**, in order: Cloud Run service → `/health` → Firestore collection.

---

## 4 · Record

**Xbox Game Bar** — built in, no install:

1. `Win+G`
2. Turn the **microphone on** (mic icon) — narration matters more than the visuals
3. Click record, or `Win+Alt+R` to start and stop
4. Output lands in `Videos\Captures`

**OBS Studio** if you want the split-screen layout or a webcam corner. More setup, better result.

Record it in **one take** if you can. A slightly rough continuous take reads as more genuine than a polished edit, and the brief rewards showing real work.

---

## 5 · Upload and get the link

1. Go to https://youtube.com → **Create** → **Upload video**
2. Title: `Pipeline Medic — Autonomous Data Pipeline Triage | All Things Agentic Hackathon`
3. Description — paste this:

```
Pipeline Medic is an autonomous on-call agent for data pipelines. When a pipeline
model breaks, it diagnoses the root cause, writes a fix, and proves the fix works
against BigQuery before any human sees it.

Built for the All Things Agentic Hackathon with Gemini 3.7 Flash on Vertex AI,
Google ADK, Cloud Run, Pub/Sub, Firestore, and BigQuery.

Live: https://pipeline-medic-333215501397.us-central1.run.app/health
Code: https://github.com/damowdhar/pipeline-medic
```

4. **Visibility: Public.** The brief states "must be public (not unlisted)" for the *bonus content* item; it doesn't spell out a visibility rule for the demo video itself. Public is still the safe choice — judges have to be able to watch it without friction. Check the Rules tab if you want certainty, and whether YouTube/Vimeo specifically is required.
5. Set "Not made for kids"
6. Copy the URL from the address bar once published — `https://www.youtube.com/watch?v=XXXXXXXXXXX`

That URL is your **Video demo link** on Devpost.

---

## 6 · Paste into Devpost

On the Project details page:

| Field | Value |
|---|---|
| Video demo link | your YouTube URL |
| "Try it out" link 1 | `https://pipeline-medic-333215501397.us-central1.run.app/health` |
| "Try it out" link 2 | `https://pipeline-medic-333215501397.us-central1.run.app/runs` |
| "Try it out" link 3 | `https://github.com/damowdhar/pipeline-medic` |
| Image gallery | upload `docs/architecture.png` |

---

## Final checklist

- [ ] Under 4 minutes
- [ ] Cloud Console visible on screen (explicitly required)
- [ ] The `.run.app` URL readable at least once
- [ ] Terminal text legible at laptop size
- [ ] YouTube visibility is **Public**
- [ ] No Nextiva material anywhere in frame
- [ ] No credentials or billing IDs on screen
