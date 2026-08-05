#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 4 ]; then
  echo "usage: archive_file_list_payload.sh SNAPSHOT_ROOT PAYLOAD_DIR ARCHIVE_FILE_LIST SUMMARY_ARCHIVE" >&2
  exit 2
fi

SNAPSHOT_ROOT="$1"
PAYLOAD_DIR="$2"
ARCHIVE_FILE_LIST="$3"
SUMMARY_ARCHIVE="$4"

test -d "$SNAPSHOT_ROOT" || { echo "missing snapshot root: $SNAPSHOT_ROOT" >&2; exit 2; }
test -d "$PAYLOAD_DIR" || { echo "missing payload directory: $PAYLOAD_DIR" >&2; exit 2; }
test ! -e "$ARCHIVE_FILE_LIST" || { echo "archive file list already exists: $ARCHIVE_FILE_LIST" >&2; exit 3; }
test ! -e "$SUMMARY_ARCHIVE" || { echo "summary archive already exists: $SUMMARY_ARCHIVE" >&2; exit 3; }

SNAPSHOT_ROOT="$(cd "$SNAPSHOT_ROOT" && pwd -P)"
PAYLOAD_DIR="$(cd "$PAYLOAD_DIR" && pwd -P)"
case "$PAYLOAD_DIR/" in
  "$SNAPSHOT_ROOT/"*) ;;
  *) echo "payload directory is outside snapshot root" >&2; exit 2 ;;
esac

for name in archive_manifest.tsv archive_checksums.sha256 archive_file_list.txt; do
  test ! -e "$PAYLOAD_DIR/$name" || { echo "reserved archive file already exists: $PAYLOAD_DIR/$name" >&2; exit 3; }
done
if find "$PAYLOAD_DIR" -type l -print -quit | grep -q .; then
  echo "symlinks are not allowed in archive payload" >&2
  exit 3
fi

digest_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

CONTENT_LIST="$(mktemp "$SNAPSHOT_ROOT/.archive-content.XXXXXX")"
MANIFEST_TMP="$PAYLOAD_DIR/archive_manifest.tsv.tmp.$$"
CHECKSUMS_TMP="$PAYLOAD_DIR/archive_checksums.sha256.tmp.$$"
FILE_LIST_TMP="$ARCHIVE_FILE_LIST.tmp.$$"
mkdir -p "$(dirname "$SUMMARY_ARCHIVE")"
ARCHIVE_TMP="$(mktemp "$(dirname "$SUMMARY_ARCHIVE")/.archive-summary.XXXXXX")"
cleanup() {
  rm -f "$CONTENT_LIST" "$MANIFEST_TMP" "$CHECKSUMS_TMP" "$FILE_LIST_TMP" "$ARCHIVE_TMP"
}
trap cleanup EXIT

find "$PAYLOAD_DIR" -type f -print | LC_ALL=C sort > "$CONTENT_LIST"
test -s "$CONTENT_LIST" || { echo "archive payload is empty" >&2; exit 3; }

{
  printf 'relative_path\tbytes\tsha256\n'
  while IFS= read -r path; do
    relative="${path#"$SNAPSHOT_ROOT/"}"
    bytes="$(wc -c < "$path" | tr -d '[:space:]')"
    printf '%s\t%s\t%s\n' "./$relative" "$bytes" "$(digest_file "$path")"
  done < "$CONTENT_LIST"
} > "$MANIFEST_TMP"
mv "$MANIFEST_TMP" "$PAYLOAD_DIR/archive_manifest.tsv"

while IFS= read -r path; do
  relative="${path#"$SNAPSHOT_ROOT/"}"
  printf '%s  ./%s\n' "$(digest_file "$path")" "$relative"
done < "$CONTENT_LIST" > "$CHECKSUMS_TMP"
mv "$CHECKSUMS_TMP" "$PAYLOAD_DIR/archive_checksums.sha256"

find "$PAYLOAD_DIR" -type f -print | LC_ALL=C sort | while IFS= read -r path; do
  relative="${path#"$SNAPSHOT_ROOT/"}"
  printf './%s\n' "$relative"
done > "$FILE_LIST_TMP"
mv "$FILE_LIST_TMP" "$ARCHIVE_FILE_LIST"

tar -czf "$ARCHIVE_TMP" -C "$SNAPSHOT_ROOT" --files-from "$ARCHIVE_FILE_LIST"
tar -tzf "$ARCHIVE_TMP" >/dev/null
mv "$ARCHIVE_TMP" "$SUMMARY_ARCHIVE"

echo "archive=$SUMMARY_ARCHIVE"
echo "archive_sha256=$(digest_file "$SUMMARY_ARCHIVE")"
