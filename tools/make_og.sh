#!/bin/sh
# 把 tools/og.html 渲染成仓库根目录的 og.png（1200×630）。需要本机装有 Edge 或 Chrome。
# 用法：sh tools/make_og.sh
set -e
cd "$(dirname "$0")/.."
for B in "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
         "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
         "$(command -v google-chrome 2>/dev/null)" "$(command -v chromium 2>/dev/null)" "$(command -v microsoft-edge 2>/dev/null)"; do
  if [ -n "$B" ] && [ -x "$B" ]; then
    "$B" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
      --window-size=1200,630 --screenshot="$PWD/og.png" "file://$PWD/tools/og.html" >/dev/null 2>&1
    echo "已生成 og.png"; exit 0
  fi
done
echo "没有找到 Edge/Chrome，请手动用浏览器打开 tools/og.html 截图为 1200×630 的 og.png" >&2; exit 1
