#!/usr/bin/env bash
# One-time import of legacy PMI data (see src/apps/projects/management/commands/import_pmi.py).
# Usage: bash scripts/import_pmi.sh --file /app/backups/pmi_export.json [--dry-run] [--report /app/logs/pmi_report.json]
set -euo pipefail
cd "$(dirname "$0")/../docker"
docker-compose --env-file ../.envs/.env exec web python manage.py import_pmi "$@"
