#!/usr/bin/env bash
#
# Portable deploy script for the GCP Cost Analyzer web app.
#
# Deploys the FastAPI dashboard to Cloud Run and (optionally) secures it with
# Identity-Aware Proxy (IAP). Everything is configured through environment
# variables so the same script works for any project / billing export.
#
# Quick start:
#   cp .env.example .env     # then edit .env
#   ./deploy.sh
#
# Or inline:
#   PROJECT_ID=my-app BILLING_PROJECT_ID=my-billing BILLING_DATASET=billing_export ./deploy.sh
#
set -euo pipefail

# Color definitions
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; BOLD='\033[1m'; NC='\033[0m'

# Run from the script's own directory.
cd "$(dirname "$0")"

# Load .env if present (lines like KEY=value). Does not override values already
# set in the environment.
if [[ -f .env ]]; then
  echo -e "📄 Loading configuration from ${BOLD}.env${NC}"
  set -a; # shellcheck disable=SC1091
  source .env; set +a
fi

# ----------------------------------------------------------------------------
# Configuration (all overridable via environment / .env)
# ----------------------------------------------------------------------------
PROJECT_ID="${PROJECT_ID:-${GCP_PROJECT_ID:-}}"          # Cloud Run deploy target (required)
BILLING_PROJECT_ID="${BILLING_PROJECT_ID:-${PROJECT_ID}}" # Where the BigQuery billing export lives
BILLING_DATASET="${BILLING_DATASET:-billing_export}"      # Billing export dataset name
REGION="${REGION:-${GCP_REGION:-us-central1}}"
SERVICE_NAME="${SERVICE_NAME:-${GCP_SERVICE_NAME:-gcp-cost-analyzer-app}}"
RUNTIME_SA_NAME="${RUNTIME_SA_NAME:-cost-analyzer-run}"   # Short name; created in PROJECT_ID
ENABLE_IAP="${ENABLE_IAP:-true}"                          # true => private + IAP; false => public
IAP_MEMBERS="${IAP_MEMBERS:-}"                            # Comma-separated: user:a@b.com,domain:example.com
MIN_INSTANCES="${MIN_INSTANCES:-0}"
MAX_INSTANCES="${MAX_INSTANCES:-1}"
IMAGE="${IMAGE:-gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo -e "${RED}Error: PROJECT_ID is required.${NC} Set it in .env or the environment." >&2
  echo -e "Example: ${BOLD}PROJECT_ID=my-app ./deploy.sh${NC}" >&2
  exit 1
fi

RUNTIME_SA_EMAIL="${RUNTIME_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo -e "\n${BOLD}🚀 GCP Cost Analyzer — Cloud Run deployment${NC}"
echo -e "   Deploy project : ${GREEN}${PROJECT_ID}${NC}"
echo -e "   Billing project: ${GREEN}${BILLING_PROJECT_ID}${NC} (dataset: ${GREEN}${BILLING_DATASET}${NC})"
echo -e "   Region         : ${GREEN}${REGION}${NC}"
echo -e "   Service        : ${GREEN}${SERVICE_NAME}${NC}"
echo -e "   Runtime SA     : ${GREEN}${RUNTIME_SA_EMAIL}${NC}"
echo -e "   IAP            : ${GREEN}${ENABLE_IAP}${NC}\n"

# ----------------------------------------------------------------------------
# 1. Enable required APIs
# ----------------------------------------------------------------------------
echo -e "🔧 Enabling required APIs on ${BOLD}${PROJECT_ID}${NC}..."
APIS="run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com bigquery.googleapis.com"
[[ "${ENABLE_IAP}" == "true" ]] && APIS="${APIS} iap.googleapis.com"
gcloud services enable ${APIS} --project="${PROJECT_ID}"

# ----------------------------------------------------------------------------
# 2. Runtime service account (created if missing)
# ----------------------------------------------------------------------------
echo -e "👤 Ensuring runtime service account exists..."
if ! gcloud iam service-accounts describe "${RUNTIME_SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${RUNTIME_SA_NAME}" \
    --project="${PROJECT_ID}" \
    --display-name="GCP Cost Analyzer Cloud Run runtime"
else
  echo -e "   ${YELLOW}Already exists.${NC}"
fi

# ----------------------------------------------------------------------------
# 3. Cross-project BigQuery permissions (read billing data)
# ----------------------------------------------------------------------------
echo -e "🔑 Granting BigQuery roles to runtime SA on ${BOLD}${BILLING_PROJECT_ID}${NC}..."
for ROLE in roles/bigquery.jobUser roles/bigquery.dataViewer; do
  gcloud projects add-iam-policy-binding "${BILLING_PROJECT_ID}" \
    --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
    --role="${ROLE}" --condition=None --quiet >/dev/null
  echo -e "   ✅ ${ROLE}"
done

# ----------------------------------------------------------------------------
# 4. Build the container image
# ----------------------------------------------------------------------------
echo -e "🔨 Building image via Cloud Build: ${GREEN}${IMAGE}${NC}"
gcloud builds submit --tag "${IMAGE}" --project="${PROJECT_ID}"

# ----------------------------------------------------------------------------
# 5. Deploy to Cloud Run
# ----------------------------------------------------------------------------
echo -e "🚀 Deploying to Cloud Run (min=${MIN_INSTANCES}, max=${MAX_INSTANCES}, scales to zero)..."
AUTH_FLAG="--allow-unauthenticated"
[[ "${ENABLE_IAP}" == "true" ]] && AUTH_FLAG="--no-allow-unauthenticated"

gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --platform managed \
  --service-account "${RUNTIME_SA_EMAIL}" \
  --min-instances "${MIN_INSTANCES}" \
  --max-instances "${MAX_INSTANCES}" \
  --ingress all \
  ${AUTH_FLAG} \
  --set-env-vars "GCP_PROJECT=${BILLING_PROJECT_ID},GCP_DATASET=${BILLING_DATASET}"

# ----------------------------------------------------------------------------
# 6. Enable IAP (direct Cloud Run integration — no load balancer)
# ----------------------------------------------------------------------------
if [[ "${ENABLE_IAP}" == "true" ]]; then
  PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
  IAP_SA="service-${PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com"

  echo -e "🔒 Configuring Identity-Aware Proxy..."
  gcloud beta services identity create --service=iap.googleapis.com --project="${PROJECT_ID}" >/dev/null

  echo -e "   Granting the IAP service agent permission to invoke the service..."
  gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
    --region="${REGION}" --project="${PROJECT_ID}" \
    --member="serviceAccount:${IAP_SA}" \
    --role="roles/run.invoker" --quiet >/dev/null

  echo -e "   Enabling IAP on the service..."
  gcloud beta run services update "${SERVICE_NAME}" \
    --region="${REGION}" --project="${PROJECT_ID}" --iap

  if [[ -n "${IAP_MEMBERS}" ]]; then
    echo -e "   Granting dashboard access to: ${GREEN}${IAP_MEMBERS}${NC}"
    IFS=',' read -ra MEMBERS <<< "${IAP_MEMBERS}"
    for M in "${MEMBERS[@]}"; do
      M="$(echo "${M}" | xargs)" # trim whitespace
      [[ -z "${M}" ]] && continue
      gcloud iap web add-iam-policy-binding \
        --resource-type=cloud-run \
        --service="${SERVICE_NAME}" \
        --region="${REGION}" --project="${PROJECT_ID}" \
        --member="${M}" \
        --role="roles/iap.httpsResourceAccessor" >/dev/null
      echo -e "      ✅ ${M}"
    done
  else
    echo -e "   ${YELLOW}No IAP_MEMBERS set — nobody can access the dashboard yet.${NC}"
    echo -e "   Grant access with: ${BOLD}./share.sh add user:you@example.com${NC}"
  fi
fi

# ----------------------------------------------------------------------------
# 7. Summary
# ----------------------------------------------------------------------------
URL="$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --project "${PROJECT_ID}" --format='value(status.url)')"
echo -e "\n${GREEN}======================================================================${NC}"
echo -e "🎉 ${GREEN}${BOLD}Deployed successfully.${NC}"
echo -e "${GREEN}======================================================================${NC}"
echo -e "🌐 URL: ${BOLD}${URL}${NC}"
if [[ "${ENABLE_IAP}" == "true" ]]; then
  echo -e "🔒 IAP is ON. Manage who can access it with ${BOLD}./share.sh${NC}."
  echo -e "   IAM grants can take 1–3 minutes to propagate on first access."
else
  echo -e "⚠️  ${YELLOW}IAP is OFF — this service is PUBLIC.${NC} Set ENABLE_IAP=true to secure it."
fi
echo -e "🔄 Optional: schedule a daily GET on ${BOLD}${URL}/cron/refresh${NC} via Cloud Scheduler."
echo -e "${GREEN}======================================================================${NC}"
