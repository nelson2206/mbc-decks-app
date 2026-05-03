#!/usr/bin/env bash
# copy-plugin.sh — Copia el plugin mbc-decks v0.3.0 al backend antes del deploy.
#
# Uso:
#   bash scripts/copy-plugin.sh /ruta/a/mbc-decks/
#
# El argumento debe ser la ruta donde está el plugin descomprimido.

set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Uso: bash scripts/copy-plugin.sh /ruta/a/mbc-decks/"
  exit 1
fi

SRC="$1"
DST="backend/app/plugin_resources"

if [ ! -d "$SRC/skills" ] || [ ! -d "$SRC/assets" ]; then
  echo "ERROR: $SRC no parece ser el plugin mbc-decks (faltan skills/ o assets/)"
  exit 1
fi

cd "$(dirname "$0")/.."

mkdir -p "$DST"
cp -r "$SRC/skills" "$DST/"
cp -r "$SRC/assets" "$DST/"
cp -r "$SRC/credenciales" "$DST/" 2>/dev/null || mkdir -p "$DST/credenciales"
cp -r "$SRC/slide_bank" "$DST/" 2>/dev/null || mkdir -p "$DST/slide_bank"
cp "$SRC/plugin.json" "$DST/" 2>/dev/null || true

# Conservar el .pptx convertido si existe
if [ -f "$DST/assets/template/PPT_MINSAIT_Template_esp.pptx" ]; then
  echo "✅ Plantilla .pptx ya convertida"
fi

echo "✅ Plugin copiado a $DST"
echo ""
echo "Tamaño: $(du -sh $DST | cut -f1)"
echo ""
echo "Siguiente: bash scripts/setup-github.sh"
