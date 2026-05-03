#!/usr/bin/env bash
# setup-github.sh — Inicializa el repo y deja todo listo para git push.
#
# Uso:
#   cd mbc-decks-app
#   bash scripts/setup-github.sh
#
# Después:
#   1. Ir a https://github.com/new y crear el repo (privado recomendado)
#   2. Copiar la URL HTTPS y ejecutar lo que el script imprime al final

set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== MBC Decks · Setup GitHub repo ==="
echo ""

# Verificar git
if ! command -v git &> /dev/null; then
  echo "ERROR: git no está instalado. Instalar desde https://git-scm.com/downloads"
  exit 1
fi

# Verificar que estamos en la raíz del proyecto
if [ ! -f "docker-compose.yml" ] || [ ! -d "backend" ] || [ ! -d "frontend" ]; then
  echo "ERROR: ejecuta este script desde la raíz de mbc-decks-app/"
  exit 1
fi

# Inicializar repo si no existe
if [ ! -d .git ]; then
  git init
  echo "✅ Repo git inicializado"
else
  echo "ℹ️  Ya existe un repo git en este directorio"
fi

# Configurar usuario si no está
if [ -z "$(git config user.email)" ]; then
  read -p "Tu email para los commits: " email
  read -p "Tu nombre: " name
  git config user.email "$email"
  git config user.name "$name"
fi

# Verificar que .gitignore está OK
if ! grep -q "\.env" .gitignore 2>/dev/null; then
  echo "⚠️  ADVERTENCIA: .gitignore no incluye .env — agregándolo"
  echo "" >> .gitignore
  echo ".env" >> .gitignore
  echo ".env.local" >> .gitignore
fi

# Verificar que no hay .env real
if [ -f .env ]; then
  echo "⚠️  Detecté un archivo .env real. Por seguridad NO se sube a GitHub."
  echo "   (.gitignore ya lo excluye)"
fi

# Stage + commit
git add -A
if ! git diff --staged --quiet; then
  git commit -m "Initial commit · MBC Decks v0.2.0"
  echo "✅ Commit inicial creado"
fi

git branch -M main

echo ""
echo "=== Pasos siguientes ==="
echo ""
echo "1. Ir a https://github.com/new"
echo "   - Nombre: mbc-decks-app"
echo "   - Visibilidad: Private (recomendado)"
echo "   - NO inicializar con README"
echo ""
echo "2. Pegar este comando (reemplazando <TU-USUARIO>):"
echo ""
echo "   git remote add origin https://github.com/<TU-USUARIO>/mbc-decks-app.git"
echo "   git push -u origin main"
echo ""
echo "3. Continuar con DEPLOY.md a partir del Paso 3 (Neon database)"
echo ""
