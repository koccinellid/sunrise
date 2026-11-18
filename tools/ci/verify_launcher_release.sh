#!/usr/bin/env bash
# Checks a sunrise-org/sunrise-launcher release folder before launcher-bridge.yml signs it here: SHA256SUMS signed for "sunrise-launcher release <tag>\n" by a key in KEYS, and every listed file's SHA-256.
# It calls only the runner's sha256sum, base64 and OpenSSL; KEYS lists one base64 Ed25519 public key per line (# starts a comment).
#   tools/ci/verify_launcher_release.sh v1.1.0 dist tools/ci/launcher-release-keys.txt
set -euo pipefail
tag=$1 dir=$2 keys=$3
openssl=${OPENSSL:-openssl}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mapfile -t listed < <(grep -v '^[[:space:]]*\(#\|$\)' "$keys" || true)
[[ ${#listed[@]} -gt 0 ]] || { echo "$keys lists no launcher key: nothing can be checked, so nothing is bridged" >&2; exit 1; }
[[ -f "$dir/SHA256SUMS" && -f "$dir/SHA256SUMS.sig" ]] || { echo "$tag has no SHA256SUMS and SHA256SUMS.sig" >&2; exit 1; }
{ printf 'sunrise-launcher release %s\n' "$tag"; cat "$dir/SHA256SUMS"; } > "$work/message"
signed=
while read -r signature; do
  [[ -n "$signature" ]] || continue
  base64 --decode <<< "$signature" > "$work/signature" 2> /dev/null || continue
  for key in "${listed[@]}"; do
    # An Ed25519 public key's DER: the fixed SubjectPublicKeyInfo header, then its 32 bytes.
    { printf '\x30\x2a\x30\x05\x06\x03\x2b\x65\x70\x03\x21\x00'; base64 --decode <<< "$key"; } > "$work/key.der"
    if "$openssl" pkeyutl -verify -pubin -inkey "$work/key.der" -keyform DER -rawin -in "$work/message" -sigfile "$work/signature" > /dev/null 2>&1; then
      signed=yes
    fi
  done
done < "$dir/SHA256SUMS.sig"
[[ -n "$signed" ]] || { echo "$tag: SHA256SUMS isn't signed by a launcher key in $keys" >&2; exit 1; }
(cd "$dir" && sha256sum --check --strict --quiet SHA256SUMS) || { echo "$tag: a file doesn't match its signed checksum" >&2; exit 1; }
echo "$tag: SHA256SUMS signed for the launcher, and every file matches"
