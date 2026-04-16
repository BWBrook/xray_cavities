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

repo_root="/home/bwbrook/papers/xray_cavities"
template="$repo_root/docs/onboarding/templates/report-template.qmd"
target="$repo_root/docs/onboarding/reports/${report_date}-${report_slug}.qmd"

if [ -e "$target" ]; then
  echo "Refusing to overwrite existing report: $target"
  exit 1
fi

cp "$template" "$target"
sed -i \
  -e "s/REPORT TITLE/${report_title//\//\\/}/" \
  -e "s/YYYY-MM-DD/$report_date/" \
  "$target"

echo "Created $target"
