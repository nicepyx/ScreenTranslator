#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv-build ]; then
  python3 -m venv .venv-build
fi
source .venv-build/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-build.txt

rm -rf build dist release
pyinstaller --noconfirm ScreenTranslator.spec
mkdir -p release

codesign --deep --force --sign - dist/ScreenTranslator.app || true
hdiutil create \
  -volname "Screen Translator" \
  -srcfolder dist/ScreenTranslator.app \
  -ov -format UDZO \
  release/ScreenTranslator-v0.8.0-macOS.dmg

echo "Created release/ScreenTranslator-v0.8.0-macOS.dmg"
