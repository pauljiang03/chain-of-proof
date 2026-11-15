#!/usr/bin/env bash
# Download the NIST CFReDS Data Leakage Case images into data/.
#
#   scripts/fetch_data.sh          removable media only (about 430 MB)
#   scripts/fetch_data.sh --pc     also the PC image, E01-E04 (about 7.3 GB)
#
# E01 images are read directly, so no 7-Zip or 20 GB raw extraction is needed.
# Downloads resume if interrupted. Compare MD5/SHA-1 with the hashes published on
# the case page before using an image.
set -euo pipefail

BASE="https://cfreds-archive.nist.gov/data_leakage_case/images"
DEST="$(cd "$(dirname "$0")/.." && pwd)/data"
mkdir -p "$DEST"

fetch() {  # fetch <url path> <local name>
  local url="$BASE/$1" out="$DEST/$2" want have
  want=$(curl -sIL "$url" | awk 'tolower($1)=="content-length:"{n=$2} END{print n+0}')
  have=$(stat -f%z "$out" 2>/dev/null || stat -c%s "$out" 2>/dev/null || echo 0)
  if [[ "$want" -gt 0 && "$have" -eq "$want" ]]; then
    echo "== $2 (already complete)"
    return
  fi
  echo ">> $2"
  curl --fail --location --continue-at - --output "$out" "$url"
}

fetch "rm%231/cfreds_2015_data_leakage_rm%231.E01"        rm1.E01
fetch "rm%232/cfreds_2015_data_leakage_rm%232.E01"        rm2.E01
fetch "rm%233/cfreds_2015_data_leakage_rm%233_type3.E01"  rm3.E01

if [[ "${1:-}" == "--pc" ]]; then
  for n in 1 2 3 4; do
    fetch "pc/cfreds_2015_data_leakage_pc.E0$n" "pc.E0$n"
  done
fi

echo "Done. Images are in $DEST"
echo "Hashes to compare: https://cfreds-archive.nist.gov/data_leakage_case/data-leakage-case.html"
