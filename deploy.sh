#!/usr/bin/env bash
set -eo pipefail

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "🚀 Starting Cloud Run deployment process..."

# Ensure we are in the correct directory
cd "$(dirname "$0")"

PROJECT_ID="${GCP_PROJECT_ID:-your-gcp-project-id}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${GCP_SERVICE_NAME:-gcp-cost-analyzer-app}"

echo -e "📍 Configuring active billing project to: ${GREEN}${PROJECT_ID}${NC}"
gcloud config set project "${PROJECT_ID}" || {
    echo -e "${RED}Error: Failed to set gcloud project.${NC}"
    exit 1
}

IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo -e "🔨 Submitting build to Google Cloud Build: ${GREEN}${IMAGE_TAG}${NC}"
gcloud builds submit --tag "${IMAGE_TAG}" || {
    echo -e "${RED}Error: Cloud Build failed.${NC}"
    exit 1
}

echo -e "🚀 Deploying to Google Cloud Run..."
echo -e "🔧 Scaling Configuration: ${GREEN}min-instances=0${NC} (Scales to zero!)"

gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_TAG}" \
  --platform managed \
  --region "${REGION}" \
  --min-instances 0 \
  --max-instances 1 \
  --ingress all \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT="${PROJECT_ID}",GCP_CONFIG_NAME="default" || {
    echo -e "${RED}Error: Cloud Run deployment failed.${NC}"
    exit 1
}

echo -e "\n${GREEN}======================================================================${NC}"
echo -e "🎉 ${GREEN}Success! Cost Analyzer Web App deployed to Cloud Run.${NC}"
echo -e "======================================================================\n"
echo -e "🌐 Cloud Run Service URL:"
gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format='value(status.url)'
echo -e "\n🔒 Security & SSO Note:"
echo -e "1. To configure Identity-Aware Proxy (IAP) for secure Single Sign-On (SSO):"
echo -e "   - Create a Serverless Network Endpoint Group (NEG) pointing to this service."
echo -e "   - Create an External Application Load Balancer (ALB) with this Serverless NEG backend."
echo -e "   - Enable IAP on the ALB's Backend Service."
echo -e "   - Set Cloud Run Ingress to 'Internal and Cloud Load Balancing' using:"
echo -e "     ${GREEN}gcloud run services update ${SERVICE_NAME} --ingress internal-and-cloud-load-balancing --region ${REGION}${NC}"
echo -e "2. To set up dynamic daily automatic refreshes via Cloud Scheduler:"
echo -e "   - Create a Cloud Scheduler Job pointing to the app's '/cron/refresh' endpoint daily."
echo -e "======================================================================"
