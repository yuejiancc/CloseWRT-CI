#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE/wrt"
PROFILE="$GITHUB_WORKSPACE/Config/KONKA-A31"
REPORT="$GITHUB_WORKSPACE/build-reports"

# Use the original repositories' native device DTS and FIT image recipe unchanged.
# Replace default fw4 packages, otherwise target defaults can re-enable them.
python3 - <<'PY'
from pathlib import Path
p = Path('include/target.mk')
s = p.read_text()
s = s.replace('\tfirewall4 \\', '\tfirewall \\')
s = s.replace('\tnftables \\', '\tiptables-zz-legacy \\')
s = s.replace('\tkmod-nft-offload \\', '\tkmod-ipt-offload \\')
p.write_text(s)
PY
./scripts/feeds update -a
./scripts/feeds install -a
./scripts/feeds uninstall chinadns-ng || true
mkdir -p package/a31
cp -a "$PROFILE/chinadns-ng" package/a31/chinadns-ng

# Only the currently used extra applications; no unrelated generic CI plugin bundle.
git clone --quiet https://github.com/Zesuy/UA-Mask.git package/a31/UAmask
git -C package/a31/UAmask checkout --quiet 1e5a5ce38fc207136ba21a3f82a6a3e892a3c572
if [ "$SOURCE_ID" = chasey-25.12 ]; then
  ARGON_REF=4b8b7849551c558ec905c40b0ebb864641c9fa32
else
  ARGON_REF=fcd054536aa8641c5b2b8ec371e1895ad14d1cfb
fi
./scripts/feeds uninstall luci-theme-argon || true
git clone --quiet https://github.com/sbwml/luci-theme-argon.git package/a31/luci-theme-argon
git -C package/a31/luci-theme-argon checkout --quiet "$ARGON_REF"

# LuCI collection must follow fw3 too. Individual dependencies are audited later.
find feeds/luci/collections -name Makefile -type f -exec sed -i 's/+firewall4/+firewall/g' {} +

mkdir -p files/etc/uci-defaults
cp "$PROFILE/99-a31-defaults" files/etc/uci-defaults/99-a31-defaults
chmod 755 files/etc/uci-defaults/99-a31-defaults
cp "$PROFILE/COMPATIBILITY.md" "$REPORT/COMPATIBILITY.md"
{
  printf 'source=%s\nrepository=%s\nbranch=%s\nrevision=%s\n' \
    "$SOURCE_ID" "$SOURCE_REPO" "$SOURCE_BRANCH" "$(git rev-parse HEAD)"
  printf '\nFeeds resolved at build time (recorded exact revisions):\n'
  for feed in feeds/*/.git; do
    printf '%s ' "$(dirname "$feed")"
    git -C "$(dirname "$feed")" rev-parse HEAD
  done
  printf '\nUA-Mask=%s\nArgon=%s\n' \
    "$(git -C package/a31/UAmask rev-parse HEAD)" "$ARGON_REF"
} > "$REPORT/sources.txt"
git diff -- include/target.mk > "$REPORT/compatibility-source.patch"
sha256sum target/linux/mediatek/dts/*konka-komi-a31* > "$REPORT/native-device-dts.sha256"
