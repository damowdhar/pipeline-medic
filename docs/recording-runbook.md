# Recording runbook — complete step by step

Everything from a cold laptop to a YouTube URL pasted into Devpost. Narration is written out verbatim; you can read it as-is.

**Total time:** ~60 minutes including setup and one or two retakes.
**Target length:** 4 minutes. The script below is ~580 spoken words, which lands around 3:50 at a normal pace.

---

# Part 1 · Install and set up Descript (15 min, one time)

Use the **desktop app**, not web.descript.com. Browser capture can only reliably grab a single tab or window, and this demo switches between a terminal and Chrome.

1. Download from **https://www.descript.com/download** → install → sign in
2. **New Project** → **Record** (or `Ctrl+Shift+R`)
3. In the record panel set:
   - **Screen:** Entire Screen
   - **Microphone:** your laptop mic — speak and check the meter moves
   - **Camera:** Off
   - **Transcription:** On
4. Turn on **Studio Sound** in the right-hand panel afterwards — it removes room echo and fan noise, and makes a laptop mic sound dramatically better

**Why Descript rather than just recording:** you edit the video by editing its transcript. Delete a sentence of text and that footage disappears. It removes "um" automatically. For hitting a hard 4-minute limit without re-recording, nothing else is close.

> **Free plan exports carry a Descript watermark.** Check the export preview before uploading. If you'd rather not have one, you don't need to re-record — import the raw capture into **Clipchamp** (built into Windows 11, free, no watermark), make the single cut, and export. About five minutes.

---

# Part 2 · Pre-flight on your laptop (10 min, before every session)

### 2.1 Hide anything work-related

Your screenshots so far show Nextiva, OBIEE, MSTR, HADOOP, and BICS bookmark folders. A recording captures all of it.

- `Ctrl+Shift+B` in Chrome — hides the bookmarks bar
- Close Outlook, Teams, and Slack completely — notification toasts land mid-take
- `Win+D`, clear your desktop of anything with a work filename

### 2.2 Make the terminal readable

Open **Windows PowerShell** → `Ctrl+,` → Appearance → **font size 18**.

This is the most common way a good demo loses points. Judges watch on laptops.

### 2.3 Prepare the terminal

```powershell
cd C:\Users\DamowdharMallem\hackathon\pipeline-medic
```

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\Users\DamowdharMallem\hackathon\.gcloud\application_default_credentials.json"
```

Silence gcloud's chatter so update notices don't appear mid-demo:

```powershell
gcloud config set survey/disable_prompts true
gcloud config set component_manager/disable_update_check true
```

### 2.4 Warm up Cloud Run

It scales to zero. Without this you get ~15 seconds of dead air on the first request.

```powershell
curl.exe -s https://pipeline-medic-333215501397.us-central1.run.app/health
```

Expect: `{"ok":true,"model":"gemini-3.7-flash","vertex_location":"global","firestore_database":"hackathon"}`

### 2.5 Confirm the demo is still broken

```powershell
.\.venv\Scripts\python.exe -c "from demo.break_it import run_model; print('BROKEN - good' if run_model() else 'FIXED - run: python -m demo.reset')"
```

If it says FIXED:

```powershell
.\.venv\Scripts\python.exe -m demo.reset
```

### 2.6 Clear the PR list

Close any open PRs at https://github.com/damowdhar/pipeline-medic/pulls so the one that appears on camera is unmistakably new.

### 2.7 Clear the terminal

```powershell
cls
```

---

# Part 3 · Open your tabs

One Chrome window, these six tabs, **in this order**:

| # | Tab | URL |
|---|---|---|
| 1 | Cloud Run logs | `https://console.cloud.google.com/run/detail/us-central1/pipeline-medic/observability/logs?project=dm-agentic-hackathon-2026` |
| 2 | Pull requests | `https://github.com/damowdhar/pipeline-medic/pulls` |
| 3 | Cloud Run service | `https://console.cloud.google.com/run/detail/us-central1/pipeline-medic?project=dm-agentic-hackathon-2026` |
| 4 | Health check | `https://pipeline-medic-333215501397.us-central1.run.app/health` |
| 5 | Firestore | `https://console.cloud.google.com/firestore/databases/hackathon/data/panel/triage_runs?project=dm-agentic-hackathon-2026` |
| 6 | Pub/Sub topic | `https://console.cloud.google.com/cloudpubsub/topic/detail/pipeline-failures?project=dm-agentic-hackathon-2026` |

Tick **Pretty-print** on tab 4. Raw JSON is unreadable on video.

> Console paths move around. If tab 1 or 3 gives "URL not found", navigate by hand: **Cloud Run → Services → pipeline-medic → Observability → Logs**. Or use Logs Explorer, which is stable:
> `https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_revision%22%20resource.labels.service_name%3D%22pipeline-medic%22?project=dm-agentic-hackathon-2026`

---

# Part 4 · Record

In Descript: **Record** → **Screen** → choose **Entire Screen** → **microphone on** → **Record**.

Give yourself 3 seconds of silence before speaking. It makes trimming the start clean.

---

## 0:00 – 0:35 · The problem

**[SHOW: terminal, full screen]**

**[TYPE and run:]**

```powershell
.\.venv\Scripts\python.exe -m demo.break_it
```

> "This is a data pipeline failing at three in the morning.
>
> The error says: *Name customer_id not found inside c*.
>
> That's a symptom, not a cause. Somebody now gets paged. They open six tabs, compare the model against the warehouse schema, and eventually work out that an upstream team renamed a column three days ago. The fix is one line. Finding it takes forty minutes.
>
> I wanted to automate the part that actually hurts — not the typing, the diagnosis."

---

## 0:35 – 1:05 · What it is

**[SHOW: still on the terminal — the published-to-Pub/Sub line is visible]**

> "This is Pipeline Medic. It's an autonomous agent built with Google's ADK, running Gemini 3.7 Flash on Vertex AI, hosted on Cloud Run and triggered by Pub/Sub.
>
> That command did two things: it ran the model so you could see the real error, and it published that failure to a Pub/Sub topic. That's the last thing I type. From here, nobody is driving.
>
> And the thing I care about most is this: it isn't allowed to guess. Most AI-fixes-your-code demos hand you a plausible patch and ask you to check it — which doesn't remove the work, it just moves it. This one has to *prove* its fix before it says anything. It uses BigQuery's dry-run mode as an oracle: it can test a candidate fix against real schemas, for free, as many times as it needs. If BigQuery rejects it, it reads the actual error and tries again."

---

## 1:05 – 2:00 · The agent working

**[SWITCH TO: Chrome tab 1 — Cloud Run logs, streaming live]**

> "Here are the live logs from Cloud Run.
>
> First thing you see — it acknowledged the Pub/Sub message immediately, before doing any work. That's deliberate. Triage takes about two minutes, far longer than Pub/Sub's acknowledgement deadline, so acking first is what stops the same job running twice.
>
> Now it's working. Reading the model. Listing the tables. And there — it's inspecting what `raw_customers` actually contains today, and finding `cust_id` where the model expects `customer_id`.
>
> Now it writes a fix and dry-runs it against BigQuery."

**[The run takes ~2 minutes. In Descript, cut here — see Part 5. Then say:]**

> "About two minutes later, with nobody watching…"

---

## 2:00 – 2:45 · The pull request

**[SWITCH TO: Chrome tab 2 — GitHub pull requests. Refresh.]**

> "…it opened a pull request."

**[CLICK into the PR. Scroll to show the body, then the Files changed tab.]**

> "Root cause, in plain language. A note that the SQL was validated against BigQuery before this PR was opened. And the diff — the one line that was actually wrong.
>
> And look at this detail. It kept `AS customer_id` as the *output* column name, while switching the source to `cust_id`. Renaming the output would also have compiled perfectly — and silently broken every dashboard downstream. Nothing in the prompt told it to be careful about that.
>
> It opens the pull request. It never merges, and it never writes to main. Merging stays a human decision."

---

## 2:45 – 3:30 · Running on Google Cloud

**[SWITCH TO: tab 3 — Cloud Run service. Then 4, 5, 6.]**

> "All of this runs on Google Cloud.
>
> Cloud Run hosting the agent — here's the service and its URL.
>
> The health endpoint, confirming Gemini 3.7 Flash on Vertex AI, on the global endpoint.
>
> Firestore, holding every triage run — root cause, validated SQL, the pull request link.
>
> And Pub/Sub, the topic that started the whole thing."

---

## 3:30 – 3:50 · Close

**[SHOW: back to the pull request]**

> "Every run is recorded, so when a model that's failed before fails again, those confirmed fixes come back as context.
>
> And when it *can't* find a validated fix, it says so, and explains what it ruled out. It doesn't dress up a guess as an answer. An autonomous system you can't trust to say 'I don't know' is one you have to check every time — which defeats the point.
>
> That's Pipeline Medic. I published one message, walked away, and it came back with a pull request."

**[Stop recording. Stay silent 3 seconds first.]**

---

# Part 5 · Edit in Descript

1. Descript transcribes automatically — wait for it
2. **Trim the two-minute wait.** Find where the logs are scrolling, select that stretch of transcript, press **Delete**. Then add a **Jump Cut** or a short cross-dissolve so it doesn't jar.
   - *Alternative:* select the stretch → right-click → **Speed** → **4x**, and keep talking over it. Better if you'd rather not cut.
3. **Remove filler words:** right panel → **Remove Filler Words** → Apply
4. **Trim the silence** at the start and end
5. **Check the length** — bottom right. If over 4:00, cut from the 0:35–1:05 section first; it's the most compressible.
6. **Export** → **Publish** → **Export file** → MP4, 1080p

---

# Part 6 · Upload and submit

### YouTube

1. https://youtube.com → **Create** → **Upload video**
2. **Title:** `Pipeline Medic — Autonomous Data Pipeline Triage | All Things Agentic Hackathon`
3. **Description:**

```
Pipeline Medic is an autonomous on-call agent for data pipelines. When a pipeline
model breaks, it diagnoses the root cause, writes a fix, proves the fix works
against BigQuery, and opens a pull request — before any human sees it.

Built for the All Things Agentic Hackathon with Gemini 3.7 Flash on Vertex AI,
Google ADK, Cloud Run, Pub/Sub, Firestore, and BigQuery.

Live: https://pipeline-medic-333215501397.us-central1.run.app/health
Code: https://github.com/damowdhar/pipeline-medic
```

4. **Visibility: Public**
5. "Not made for kids"
6. Copy the URL — `https://www.youtube.com/watch?v=…`

### Devpost

| Field | Value |
|---|---|
| Video demo link | your YouTube URL |
| "Try it out" 1 | `https://pipeline-medic-333215501397.us-central1.run.app/health` |
| "Try it out" 2 | `https://pipeline-medic-333215501397.us-central1.run.app/runs` |
| "Try it out" 3 | `https://github.com/damowdhar/pipeline-medic` |
| About the project | paste `docs/devpost-story.md` |
| Built with | google-adk, gemini, vertex-ai, google-cloud, cloud-run, pub-sub, firestore, bigquery, python, fastapi, docker, uvicorn, sql |
| Image gallery | upload `docs/architecture.png` |

---

# Final checklist

- [ ] Under 4:00
- [ ] Cloud Console visible on screen
- [ ] The `.run.app` URL readable at least once
- [ ] The pull request shown, with its diff
- [ ] Terminal legible at laptop size
- [ ] No Nextiva material anywhere in frame
- [ ] No tokens, credentials, or billing IDs on screen
- [ ] YouTube visibility set to Public

---

# After recording

Close the PR the demo created, so the repo stays tidy for judges:
https://github.com/damowdhar/pipeline-medic/pulls

If you merge it instead, restore the fixture before the next take:

```powershell
.\.venv\Scripts\python.exe -m demo.reset
```
