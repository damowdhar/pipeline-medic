# Deploy Pipeline Medic to Cloud Run and wire up the Pub/Sub trigger.
# Idempotent -- safe to re-run. Requires: gcloud, and an active config
# pointing at the hackathon project.
#
#   .\deploy.ps1

# NOT "Stop": gcloud writes ordinary progress to stderr, and Windows
# PowerShell turns any native stderr output into a terminating
# NativeCommandError under "Stop" -- aborting the script on success messages.
# Exit codes are checked explicitly instead.
$ErrorActionPreference = "Continue"

$PROJECT  = "dm-agentic-hackathon-2026"
$REGION   = "us-central1"
$SERVICE  = "pipeline-medic"
$TOPIC    = "pipeline-failures"
$SA       = "pipeline-medic-sa"
$SA_EMAIL = "$SA@$PROJECT.iam.gserviceaccount.com"

Write-Host "==> Service account" -ForegroundColor Cyan
$exists = gcloud iam service-accounts list --project $PROJECT --filter="email:$SA_EMAIL" --format="value(email)"
if (-not $exists) {
    gcloud iam service-accounts create $SA --project $PROJECT --display-name "Pipeline Medic agent"
}

# Least privilege that still lets the agent do its job: call Gemini, run
# BigQuery dry runs and queries, and read/write its own Firestore records.
$roles = @(
    "roles/aiplatform.user",
    "roles/bigquery.jobUser",
    "roles/bigquery.dataEditor",
    "roles/datastore.user"
)
foreach ($r in $roles) {
    Write-Host "    granting $r"
    gcloud projects add-iam-policy-binding $PROJECT `
        --member="serviceAccount:$SA_EMAIL" --role=$r --quiet | Out-Null
}

Write-Host "==> Pub/Sub topic" -ForegroundColor Cyan
$topicExists = gcloud pubsub topics list --project $PROJECT --filter="name:$TOPIC" --format="value(name)"
if (-not $topicExists) {
    gcloud pubsub topics create $TOPIC --project $PROJECT
}

Write-Host "==> Deploying to Cloud Run (builds the container; takes a few minutes)" -ForegroundColor Cyan
# NOTE: --allow-unauthenticated so hackathon judges can hit the URL directly.
# For anything real, drop it and require an OIDC token.
gcloud run deploy $SERVICE `
    --project $PROJECT `
    --region $REGION `
    --source . `
    --service-account $SA_EMAIL `
    --allow-unauthenticated `
    --memory 1Gi `
    --timeout 900 `
    --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT,GOOGLE_CLOUD_LOCATION=global,MEDIC_MODEL=gemini-3.7-flash,FIRESTORE_DATABASE=hackathon,MEDIC_BQ_DATASET=medic_demo"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Cloud Run deploy failed (exit $LASTEXITCODE). See the build log above." -ForegroundColor Red
    exit 1
}

$URL = gcloud run services describe $SERVICE --project $PROJECT --region $REGION --format="value(status.url)"
Write-Host "==> Deployed: $URL" -ForegroundColor Green

Write-Host "==> Pub/Sub push subscription" -ForegroundColor Cyan
$subExists = gcloud pubsub subscriptions list --project $PROJECT --filter="name:$SERVICE-push" --format="value(name)"
if (-not $subExists) {
    gcloud pubsub subscriptions create "$SERVICE-push" `
        --project $PROJECT `
        --topic $TOPIC `
        --push-endpoint "$URL/pubsub" `
        --ack-deadline 60
}

Write-Host ""
Write-Host "Done. Try it:" -ForegroundColor Green
Write-Host "  curl $URL/health"
Write-Host "  python -m demo.break_it            # async, via Pub/Sub"
Write-Host "  python -m demo.break_it --url $URL # synchronous, watch the verdict"
