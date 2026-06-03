#!/usr/bin/env bash
#
# Manage who can access the IAP-protected Cost Analyzer dashboard.
#
# Usage:
#   ./share.sh list
#   ./share.sh add    <member>
#   ./share.sh remove <member>
#
# <member> is any IAM principal, e.g.:
#   user:alice@example.com
#   group:finance@example.com
#   domain:example.com
#   serviceAccount:svc@project.iam.gserviceaccount.com
#
# Configuration is read from .env (or the environment): PROJECT_ID, REGION, SERVICE_NAME.
#
set -euo pipefail
cd "$(dirname "$0")"

RED='\033[0;31m'; GREEN='\033[0;32m'; BOLD='\033[1m'; NC='\033[0m'

if [[ -f .env ]]; then
  set -a; # shellcheck disable=SC1091
  source .env; set +a
fi

PROJECT_ID="${PROJECT_ID:-${GCP_PROJECT_ID:-}}"
REGION="${REGION:-${GCP_REGION:-us-central1}}"
SERVICE_NAME="${SERVICE_NAME:-${GCP_SERVICE_NAME:-gcp-cost-analyzer-app}}"
ROLE="roles/iap.httpsResourceAccessor"

if [[ -z "${PROJECT_ID}" ]]; then
  echo -e "${RED}Error: PROJECT_ID is required${NC} (set it in .env or the environment)." >&2
  exit 1
fi

ACTION="${1:-}"
MEMBER="${2:-}"

usage() {
  echo "Usage: ./share.sh list | add <member> | remove <member>" >&2
  echo "Example: ./share.sh add user:alice@example.com" >&2
  exit 1
}

iap_args=(--resource-type=cloud-run --service="${SERVICE_NAME}" --region="${REGION}" --project="${PROJECT_ID}")

case "${ACTION}" in
  list)
    echo -e "${BOLD}IAP access for ${SERVICE_NAME} (${PROJECT_ID}/${REGION}):${NC}"
    gcloud iap web get-iam-policy "${iap_args[@]}" \
      --format="table(bindings.role, bindings.members)" 2>/dev/null || \
      echo "(no policy / IAP not configured yet)"
    ;;
  add)
    [[ -z "${MEMBER}" ]] && usage
    gcloud iap web add-iam-policy-binding "${iap_args[@]}" --member="${MEMBER}" --role="${ROLE}" >/dev/null
    echo -e "${GREEN}✅ Granted access to ${MEMBER}${NC} (may take 1–3 min to propagate)."
    ;;
  remove)
    [[ -z "${MEMBER}" ]] && usage
    gcloud iap web remove-iam-policy-binding "${iap_args[@]}" --member="${MEMBER}" --role="${ROLE}" >/dev/null
    echo -e "${GREEN}✅ Revoked access from ${MEMBER}.${NC}"
    ;;
  *)
    usage
    ;;
esac
