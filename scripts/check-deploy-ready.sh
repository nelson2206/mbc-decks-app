#!/usr/bin/env bash
# check-deploy-ready.sh — Verifica que el repo está listo para deploy.
#
# Ejecuta antes de git push para evitar errores en producción.

set -euo pipefail
cd "$(dirname "$0")/.."

ERRORS=0
WARNINGS=0

echo "=== Verificación pre-deploy ==="
echo ""

# 1. Plugin copiado
if [ ! -d "backend/app/plugin_resources/skills" ]; then
  echo "❌ ERROR: Plugin no copiado. Ejecuta: bash scripts/copy-plugin.sh <ruta-plugin>"
  ERRORS=$((ERRORS+1))
else
  echo "✅ Plugin copiado en backend/app/plugin_resources/"
fi

# 2. Plantilla
if [ ! -f "backend/app/plugin_resources/assets/template/PPT_MINSAIT_Template_esp.potx" ]; then
  echo "❌ ERROR: Plantilla .potx no encontrada"
  ERRORS=$((ERRORS+1))
else
  echo "✅ Plantilla Minsait presente"
fi

# 3. Knowledge base
if [ ! -f "backend/app/plugin_resources/skills/generate-deck/knowledge/pmo/concepts.md" ]; then
  echo "⚠️  WARNING: Knowledge PMO no encontrado"
  WARNINGS=$((WARNINGS+1))
else
  echo "✅ Knowledge base PMO presente"
fi

# 4. Archetypes
if [ ! -f "backend/app/plugin_resources/skills/generate-deck/archetypes/proposal_commercial.json" ]; then
  echo "❌ ERROR: Archetypes faltan"
  ERRORS=$((ERRORS+1))
else
  echo "✅ Archetypes presentes ($(ls backend/app/plugin_resources/skills/generate-deck/archetypes/*.json | wc -l) archivos)"
fi

# 5. .env NO debe estar en git
if [ -f ".env" ] && git ls-files .env 2>/dev/null | grep -q .env; then
  echo "❌ ERROR CRÍTICO: .env está siendo trackeado por git! Removerlo: git rm --cached .env"
  ERRORS=$((ERRORS+1))
else
  echo "✅ .env no está en git (correcto)"
fi

# 6. .gitignore correcto
for pattern in "node_modules" ".env" "__pycache__"; do
  if ! grep -q "$pattern" .gitignore 2>/dev/null; then
    echo "⚠️  WARNING: $pattern falta en .gitignore"
    WARNINGS=$((WARNINGS+1))
  fi
done

# 7. Tamaño del repo
SIZE=$(du -sh . 2>/dev/null | awk '{print $1}')
echo "ℹ️  Tamaño del repo: $SIZE"

echo ""
echo "=== Resultado ==="
if [ $ERRORS -gt 0 ]; then
  echo "❌ $ERRORS errores · $WARNINGS warnings — RESOLVER ANTES DE DEPLOY"
  exit 1
else
  echo "✅ Listo para git push y deploy"
  if [ $WARNINGS -gt 0 ]; then
    echo "   ($WARNINGS warnings — no bloquean pero recomendado revisar)"
  fi
fi
