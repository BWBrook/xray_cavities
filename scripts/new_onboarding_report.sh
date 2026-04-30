#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 YYYY-MM-DD slug report-title"
  exit 1
fi

report_date="$1"
report_slug="$2"
shift 2
report_title="$*"

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "$script_dir/.." && pwd)
template="$repo_root/docs/onboarding/templates/report-template.qmd"
target="$repo_root/docs/onboarding/reports/${report_date}-${report_slug}.qmd"

if [ -e "$target" ]; then
  echo "Refusing to overwrite existing report: $target"
  exit 1
fi

cp "$template" "$target"
REPORT_TITLE="$report_title" REPORT_DATE="$report_date" perl -0pi -e '
  s/REPORT TITLE/$ENV{REPORT_TITLE}/g;
  s/YYYY-MM-DD/$ENV{REPORT_DATE}/g;
' "$target"

echo "Created $target"
