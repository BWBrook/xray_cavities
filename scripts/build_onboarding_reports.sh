#!/usr/bin/env bash
set -euo pipefail

repo_root="/home/bwbrook/papers/xray_cavities"
onboarding_dir="$repo_root/docs/onboarding"
export_dir="/mnt/c/Users/bwbrook/OneDrive - University of Tasmania/EXCHANGE/xray_cavities_files/reports"

cd "$onboarding_dir"
quarto render

mkdir -p "$export_dir"
mapfile -t pdfs < <(find "$onboarding_dir/_build" -maxdepth 3 -type f -name '*.pdf' | sort)

for pdf in "${pdfs[@]}"; do
  cp "$pdf" "$export_dir/"
done

echo
echo "Built onboarding reports in:"
echo "  $onboarding_dir/_build"
echo
find "$onboarding_dir/_build" -maxdepth 3 -type f \( -name '*.html' -o -name '*.pdf' \) | sort
echo
echo "Copied PDFs to:"
echo "  $export_dir"

for pdf in "${pdfs[@]}"; do
  echo "  $export_dir/$(basename "$pdf")"
done
