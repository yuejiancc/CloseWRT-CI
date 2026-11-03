#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE/wrt"
PROFILE="$GITHUB_WORKSPACE/Config/KONKA-A31"
REPORT="$GITHUB_WORKSPACE/build-reports"

# Keep the original source's DTS, FIT/DSA layout, firewall4 and package manager.
./scripts/feeds update -a
./scripts/feeds install -a

# Same feed compatibility fix as the original CI's Scripts/Handles.sh.
if grep -q '^define Package/weechat-minimal$' feeds/packages/net/weechat/Makefile; then
  sed -i 's/ +weechat / +!PACKAGE_weechat-full:weechat-minimal +PACKAGE_weechat-full:weechat-full /g' \
    feeds/luci/applications/luci-app-weechat/Makefile
fi

# Native radio defaults without a shared preinstalled password or enabled open AP.
python3 - <<'PY'
from pathlib import Path
p = Path('package/mtk/applications/mtwifi-cfg-ucode/files/lib/wifi/mtwifi.uc')
if p.exists():
    s = p.read_text()
    assert '"channel": "auto"' in s
    p.write_text(s.replace('"channel": "auto"', '"channel": band == "5g" ? "36" : "auto", "disabled": 1'))
else:
    p = Path('package/mtk/applications/mtwifi-cfg/files/mtwifi.sh')
    s = p.read_text()
    marker = 'set wireless.${dev}.country=CN'
    assert marker in s
    p.write_text(s.replace(marker, marker + '\n\t\t\t\t\tset wireless.${dev}.disabled=1'))
PY
mkdir -p files/etc/uci-defaults
cp "$PROFILE/99-a31-defaults" files/etc/uci-defaults/99-a31-defaults
chmod 755 files/etc/uci-defaults/99-a31-defaults
cp "$PROFILE/COMPATIBILITY.md" "$REPORT/COMPATIBILITY.md"
{
  printf 'source=%s\nrepository=%s\nbranch=%s\nrevision=%s\n' \
    "$SOURCE_ID" "$SOURCE_REPO" "$SOURCE_BRANCH" "$(git rev-parse HEAD)"
  printf '\nFeeds resolved at build time:\n'
  for feed in feeds/*/.git; do
    printf '%s ' "$(dirname "$feed")"
    git -C "$(dirname "$feed")" rev-parse HEAD
  done
} > "$REPORT/sources.txt"
git diff > "$REPORT/compatibility-source.patch"
sha256sum target/linux/mediatek/dts/*konka-komi-a31* > "$REPORT/native-device-dts.sha256"
