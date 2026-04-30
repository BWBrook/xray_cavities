#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "$script_dir/.." && pwd)
onboarding_dir="$repo_root/docs/onboarding"
default_export_dir="/mnt/c/Users/bwbrook/OneDrive - University of Tasmania/EXCHANGE/xray_cavities_files/reports"
export_dir="${XRAY_CAVITIES_REPORT_EXPORT_DIR:-$default_export_dir}"

cd "$onboarding_dir"
quarto render

pdfs=()
while IFS= read -r pdf; do
  pdfs+=("$pdf")
done < <(find "$onboarding_dir/_build" -maxdepth 3 -type f -name '*.pdf' | sort)

if [ -d "$(dirname "$export_dir")" ]; then
  mkdir -p "$export_dir"
  for pdf in "${pdfs[@]}"; do
    cp "$pdf" "$export_dir/"
  done
  copied_reports=true
else
  copied_reports=false
fi

echo
echo "Built onboarding reports in:"
echo "  $onboarding_dir/_build"
echo
find "$onboarding_dir/_build" -maxdepth 3 -type f \( -name '*.html' -o -name '*.pdf' \) | sort
echo
if [ "$copied_reports" = true ]; then
  echo "Copied PDFs to:"
  echo "  $export_dir"

  for pdf in "${pdfs[@]}"; do
    echo "  $export_dir/$(basename "$pdf")"
  done
else
  echo "Skipped PDF export because this parent directory does not exist:"
  echo "  $(dirname "$export_dir")"
  echo "Set XRAY_CAVITIES_REPORT_EXPORT_DIR to copy PDFs elsewhere."
fi
