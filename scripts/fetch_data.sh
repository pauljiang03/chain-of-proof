#!/usr/bin/env bash
# Download the NIST CFReDS Data Leakage Case images into data/.
#
#   scripts/fetch_data.sh          removable media only (about 430 MB)
#   scripts/fetch_data.sh --pc     also the PC image, E01-E04 (about 7.3 GB)
#
# The E01 files are read directly by libewf, The Sleuth Kit and plaso, so
# nothing needs 7-Zip or a 20 GB raw extraction. Downloads resume if interrupted.
# Compare MD5/SHA-1 with the hashes published on the case page before using an image.
set -euo pipefail

BASE="https://cfreds-archive.nist.gov/data_leakage_case/images"
DEST="$(cd "$(dirname "$0")/.." && pwd)/data"
mkdir -p "$DEST"

fetch() {  # fetch <url path> <local name>
  echo ">> $2"
  curl --fail --location --continue-at - --output "$DEST/$2" "$BASE/$1"
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
