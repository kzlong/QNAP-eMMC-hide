#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$ROOT/.build"
DIST="$ROOT/dist"
APP_TGZ="$WORK/app.tgz"
VERSION="$(awk -F= '/^[[:space:]]*version[[:space:]]*=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "$ROOT/manifest")"
[[ -n "$VERSION" ]] || { echo "无法从 manifest 读取版本号" >&2; exit 1; }
OUT="$DIST/qnap-emmc-hide-${VERSION}.fpk"

command -v tar >/dev/null || { echo "缺少 tar" >&2; exit 1; }
command -v md5sum >/dev/null || { echo "缺少 md5sum" >&2; exit 1; }

rm -rf "$WORK" "$DIST"
mkdir -p "$WORK" "$DIST"

# FPK 内部应用资源包。保留相对路径和可执行位。
tar -czf "$APP_TGZ" -C "$ROOT/app" .
APP_MD5="$(md5sum "$APP_TGZ" | awk '{print $1}')"

# 更新 manifest 的 app.tgz 校验值；保留其他元数据。
awk -v md5="$APP_MD5" '
  /^checksum[[:space:]]*=/ { print "checksum              = " md5; next }
  { print }
' "$ROOT/manifest" > "$WORK/manifest"

# 按 FPK 格式将 app.tgz 与生命周期、配置、向导、图标打包。
cp -a "$ROOT/cmd" "$ROOT/config" "$ROOT/wizard" "$WORK/"
cp "$ROOT/ICON.PNG" "$ROOT/ICON_256.PNG" "$WORK/"

tar -czf "$OUT" -C "$WORK" \
  app.tgz cmd config wizard manifest ICON.PNG ICON_256.PNG

echo "FPK 已生成：$OUT"
echo "内部 app.tgz MD5：$APP_MD5"
echo "文件大小：$(wc -c < "$OUT") bytes"
