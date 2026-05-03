# Guía de Deploy · MBC Decks 100% gratis

Esta guía te lleva de "tengo este zip" a "tengo la herramienta corriendo en producción" en ~30-45 minutos. Stack 100% gratis.

## Stack final

| Pieza | Servicio | URL ejemplo | Plan free |
|---|---|---|---|
| Repositorio | GitHub | `github.com/<tu-user>/mbc-decks-app` | Repos privados ilimitados |
| Frontend | Vercel | `mbc-decks.vercel.app` | 100GB/mes |
| Backend | Render | `mbc-decks-backend.onrender.com` | 750h/mes (sleeps tras 15min sin tráfico) |
| Database | Neon.tech | conn string | Postgres 500MB |
| Storage de .pptx | Cloudflare R2 | bucket | 10GB · sin egress |
| LLM | Anthropic API | API key | $5 USD trial al registrarse |

---

## Paso 0 · Prerrequisitos

- [ ] Cuenta de email
- [ ] `git` instalado en tu máquina (`git --version`)
- [ ] Tarjeta de crédito o débito (algunos servicios la piden para verificar identidad — ninguno te cobra automáticamente)
- [ ] El zip `mbc-decks-app-v0.2.0.zip` descomprimido en tu computadora

---

## Paso 1 · Crear cuentas (10 minutos)

Crea cuentas en estos servicios. Todos aceptan login con GitHub (más rápido):

1. **GitHub** → https://github.com/signup
2. **Vercel** → https://vercel.com/signup (login con GitHub)
3. **Render** → https://render.com (login con GitHub)
4. **Neon** → https://console.neon.tech (login con GitHub)
5. **Cloudflare** → https://dash.cloudflare.com/sign-up (para R2)
6. **Anthropic Console** → https://console.anthropic.com (API key)

---

## Paso 2 · Subir código a GitHub (5 minutos)

Abre terminal en la carpeta `mbc-decks-app/` y ejecuta:

```bash
# Inicializar repo
git init
git add .
git commit -m "Initial commit · MBC Decks v0.2.0"

# Crear repo en GitHub
# Ir a https://github.com/new
#   - Nombre: mbc-decks-app
#   - Privado (recomendado para no exponer config)
#   - NO inicializar con README (ya tenemos uno)
#   - Click "Create repository"

# GitHub te da un comando — copialo y pegalo. Algo así:
git remote add origin https://github.com/<TU-USUARIO>/mbc-decks-app.git
git branch -M main
git push -u origin main
```

> **Nota:** si tu repo es público, asegúrate de que NO incluya `.env` ni secretos. El `.gitignore` que viene en el zip ya los excluye.

---

## Paso 3 · Configurar PostgreSQL en Neon (5 minutos)

1. Entra a https://console.neon.tech
2. Click **"New Project"**
3. Nombre: `mbc-decks` · Región: **AWS US East** (más cercana a Perú con free tier) · Postgres 16
4. Click **"Create project"**
5. En la pestaña **"Connection Details"** copia el **"Connection string"** completo. Se ve así:
   ```
   postgresql://user:password@ep-xxx-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
6. Pégalo en `.env.local` de tu computadora (lo usarás en pasos siguientes).

---

## Paso 4 · Configurar Cloudflare R2 (5 minutos)

R2 = "S3 sin egress fees", gratis 10GB.

1. Entra a https://dash.cloudflare.com → **R2 Object Storage** → **Create bucket**
2. Nombre del bucket: `mbc-decks-storage` · Locación: **Eastern North America (ENAM)**
3. Click **"Create bucket"**
4. En el bucket → **Settings** → **R2.dev subdomain** → Allow Access (público para que los .pptx se puedan descargar directo)
5. Volver a **R2** → **Manage R2 API Tokens** → **Create API token**:
   - Permissions: **Object Read & Write**
   - Specify bucket: solo `mbc-decks-storage`
   - TTL: ilimitado
6. Copia los valores que te muestra:
   - **Access Key ID** → `S3_ACCESS_KEY`
   - **Secret Access Key** → `S3_SECRET_KEY`
   - **Endpoint** → `S3_ENDPOINT_URL` (algo como `https://<account>.r2.cloudflarestorage.com`)
7. Guarda estos 3 valores en tu `.env.local`. **No se vuelven a mostrar.**

---

## Paso 5 · Obtener API key de Anthropic (3 minutos)

1. Entra a https://console.anthropic.com → **API Keys** → **Create Key**
2. Nombre: `mbc-decks-prod`
3. Copia la key (`sk-ant-...`)
4. Anthropic da $5 USD de trial gratis al registrarse — alcanza para ~5,800 decks generados (a $0.86/deck).

> **Recomendado para producción:** activar billing y poner un límite de spend mensual.

---

## Paso 6 · Deploy del Backend en Render (10 minutos)

1. Entra a https://dashboard.render.com → **New +** → **Blueprint**
2. **Connect a repository**: selecciona tu repo `mbc-decks-app`
3. Render detecta `render.yaml` y propone el servicio. Click **"Apply"**.
4. Después de que se cree el servicio, ir al servicio y configurar las **Environment Variables**:

| Variable | Valor |
|---|---|
| `ANTHROPIC_API_KEY` | el `sk-ant-...` del Paso 5 |
| `DATABASE_URL` | el connection string de Neon (Paso 3) — cambiar `postgresql://` por `postgresql+psycopg2://` |
| `S3_BUCKET` | `mbc-decks-storage` |
| `S3_ENDPOINT_URL` | el endpoint de R2 (Paso 4) |
| `S3_ACCESS_KEY` | (Paso 4) |
| `S3_SECRET_KEY` | (Paso 4) |
| `CORS_ALLOWED_ORIGINS` | `["*"]` por ahora (lo ajustamos al final) |

5. Click **"Manual Deploy"** → **"Deploy latest commit"**
6. Espera ~5 minutos. El primer deploy compila el Docker image.
7. Cuando termine, copia el URL del backend (algo como `https://mbc-decks-backend.onrender.com`)
8. Verifica que funciona: en el navegador, abre `https://mbc-decks-backend.onrender.com/health`. Debe responder `{"status":"ok"}`.

---

## Paso 7 · Deploy del Frontend en Vercel (5 minutos)

1. Entra a https://vercel.com/new
2. **Import Git Repository** → selecciona `mbc-decks-app`
3. **Configure Project**:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Next.js (auto-detectado)
   - **Build Command**: `npm run build` (default)
4. **Environment Variables**:
   | Variable | Valor |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | el URL del backend de Render (Paso 6) |
5. Click **"Deploy"**
6. Espera 2-3 minutos. Vercel te dará un URL (`https://mbc-decks.vercel.app` o similar).

---

## Paso 8 · Conectar frontend ↔ backend (CORS) (3 minutos)

1. En Render, edita la env var `CORS_ALLOWED_ORIGINS`:
   ```
   ["https://mbc-decks.vercel.app"]
   ```
   (usar el URL real de Vercel del Paso 7)
2. Click **"Manual Deploy"** → **"Clear cache & deploy"** para que tome el cambio.

---

## Paso 9 · Crear primer usuario admin (3 minutos)

1. Abre el frontend en `https://mbc-decks.vercel.app`
2. Te lleva a `/login`. Por ahora no hay registro abierto.
3. Para crear el primer usuario admin, en el shell de Render:
   - Render dashboard → tu servicio → **"Shell"** (botón en la parte superior)
   - Ejecuta:
   ```bash
   python -c "
   from app.db.session import SessionLocal
   from app.db.models import User
   from app.core.security import hash_password
   db = SessionLocal()
   db.add(User(
     email='admin@minsait.com',
     full_name='Admin MBC',
     role='admin',
     hashed_password=hash_password('CAMBIAR_ESTE_PASSWORD')
   ))
   db.commit()
   "
   ```
4. Vuelve al frontend y haz login con `admin@minsait.com` / `CAMBIAR_ESTE_PASSWORD`.

---

## Paso 10 · Verificar funcionamiento end-to-end (5 minutos)

1. Login → debe llevarte a `/dashboard`
2. Click **"Nuevo deck"** → llena el wizard
3. Avanza a la entrevista guiada → completa al menos los bloques 0-2
4. **Iniciar generación con IA**
5. Espera 2-5 min. El estado debe ir cambiando: `generating` → `researching` → `structuring` → `writing` → `audit`
6. Si el A9 detecta branding hostil → `BLOCKED` y verás los hallazgos
7. Si todo OK → `ready` y aparece el botón **"Descargar .pptx"**

---

## Costos esperados

Free tier alcanza para ~5-15 usuarios concurrentes y ~50 decks/mes. Si pasas eso:

| Servicio | Plan free | Cuándo upgradearás |
|---|---|---|
| Vercel | 100GB bandwidth/mes | >100 sesiones/día |
| Render | 750h/mes (1 servicio) | nunca, salvo si necesitas >1 instancia |
| Neon | 500MB | >500 decks total guardados |
| R2 | 10GB | >100 decks de 100MB cada uno |
| Anthropic | $5 trial → pay-as-you-go | trial alcanza ~5,800 decks; producción ~$0.86/deck |

---

## Troubleshooting

### "Backend no responde" después de 15 min de inactividad
Es Render free pausando el servicio. Primer request tras pausa toma ~30s en arrancar. Para evitar: upgrade a Render Starter ($7/mes) o moverse a Fly.io.

### "Database error: SSL connection required"
Asegúrate de que el connection string de Neon termine en `?sslmode=require`.

### "ANTHROPIC_API_KEY invalid"
Verifica en console.anthropic.com que la key está activa y que tienes saldo o trial disponible.

### "CORS error: Origin not allowed"
Re-revisar `CORS_ALLOWED_ORIGINS` en Render — debe ser un JSON array string, ej: `["https://mbc-decks.vercel.app"]`.

### "El .pptx no se descarga"
Probablemente el A9 marcó `BLOCKED` por branding hostil. Revisa el reporte en el frontend y aplica reemplazos. Es comportamiento intencional.

### "El plugin no se encuentra"
El backend espera el plugin en `app/plugin_resources/`. Asegúrate de haber copiado el contenido del plugin `mbc-decks/` ahí ANTES de hacer push a GitHub.

---

## Mejoras post-deploy (opcionales)

- [ ] **Custom domain** en Vercel (`decks.minsait.pe`) — gratis con Cloudflare DNS
- [ ] **Auth por SSO** Microsoft Azure AD (cuando crezca el equipo)
- [ ] **CDN** ya viene con Vercel — no requiere acción
- [ ] **Backups automáticos** de Neon — incluido en pro plan
- [ ] **Monitoring** con Sentry (free 5k events/mes)
- [ ] **Logs centralizados** Render → Logtail (free)

---

¿Atascado en algún paso? Avísame con el error exacto y te ayudo a desbloquearlo.
