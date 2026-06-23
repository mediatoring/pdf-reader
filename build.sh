#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "=== PDF Reader — build ==="

# Aktivuj venv
source venv/bin/activate

# Vytvoř ikonu
echo "→ Generuji ikonu..."
pip install Pillow -q
python make_icon.py

# Build .app
echo "→ Builduji .app bundle..."
rm -rf build dist
python setup.py py2app 2>&1 | grep -v "^running\|^creating\|^copying\|^byte"

APP="dist/PDF Reader.app"
if [ -d "$APP" ]; then
    echo ""
    echo "✅ Hotovo: $APP"
    echo ""
    echo "Chceš přidat do Applications? Spusť:"
    echo "  cp -r \"$APP\" /Applications/"
    echo ""
    echo "Nebo rovnou otevřít:"
    echo "  open \"$APP\""
else
    echo "❌ Build selhal"
    exit 1
fi
