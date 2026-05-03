# MBC Decks · Quickstart de 30 minutos

Sigue estos pasos en orden y al final tendrás la herramienta corriendo en producción 100% gratis.

```
┌─────────────────────────────────────────────────────────┐
│   1. Descomprimir mbc-decks-app-v0.2.0.zip              │
│   2. Copiar el plugin: bash scripts/copy-plugin.sh      │
│   3. Inicializar repo: bash scripts/setup-github.sh     │
│   4. Verificar: bash scripts/check-deploy-ready.sh      │
│   5. git push origin main                               │
│   6. Seguir DEPLOY.md desde el Paso 3                   │
└─────────────────────────────────────────────────────────┘
```

## TL;DR — Comandos exactos

```bash
# 1. Descomprimir
unzip mbc-decks-app-v0.2.0.zip
cd mbc-decks-app

# 2. Copiar el plugin (asegúrate de tener mbc-decks-v0.3.0.plugin descomprimido)
unzip ../mbc-decks-v0.3.0.plugin -d ../mbc-decks-plugin
bash scripts/copy-plugin.sh ../mbc-decks-plugin/mbc-decks/

# 3. Inicializar repo
bash scripts/setup-github.sh

# 4. Verificar antes de push
bash scripts/check-deploy-ready.sh

# 5. Crear repo en GitHub.com → "New repo" → privado → "mbc-decks-app" → Create
# Luego pegar lo que GitHub te dé:
git remote add origin https://github.com/<TU-USUARIO>/mbc-decks-app.git
git push -u origin main

# 6. Continuar deploy en DEPLOY.md (Pasos 3-10)
```

## Servicios que debes crear (con tu cuenta de email)

1. **GitHub** (https://github.com/signup)
2. **Vercel** (https://vercel.com/signup) — para el frontend
3. **Render** (https://render.com) — para el backend
4. **Neon** (https://console.neon.tech) — para la base de datos
5. **Cloudflare** (https://dash.cloudflare.com/sign-up) — para storage R2
6. **Anthropic Console** (https://console.anthropic.com) — para la API key

Todos con login por GitHub para ir más rápido.

## Una vez deployed

URL final: `https://mbc-decks-<tu-nombre>.vercel.app`

Crear primer admin desde el shell de Render (DEPLOY.md Paso 9).

## Costos

- **Mes 1 (trial):** $0
- **Después:** $0 si usas <50 decks/mes y <15 usuarios concurrentes
- **Anthropic API:** ~$0.86 por deck generado (Sonnet + Haiku)

## Si te atascas

Lee `DEPLOY.md` — la sección de Troubleshooting cubre los errores típicos. Si nada funciona, comparte el error específico para destrabarlo.
