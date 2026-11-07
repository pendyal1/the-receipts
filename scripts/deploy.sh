#!/bin/sh
set -eu
# Run from the repository root after gcloud sign-in and local tests.
gcloud run deploy the-receipts --source . \
  --project ieor-4570-f26-ap4839 --account ap4839@columbia.edu --region us-east1 \
  --service-account 1027747864849-compute@developer.gserviceaccount.com \
  --set-env-vars GOOGLE_CLOUD_PROJECT=ieor-4570-f26-ap4839,GEMINI_MODEL=gemini-3.5-flash-lite \
  --timeout 300 --memory 1Gi --cpu 1 --concurrency 32 --min-instances 0 --max-instances 1 \
  --allow-unauthenticated --quiet
