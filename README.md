# MBC Decks · Webapp

Herramienta web para Minsait Business Consulting que genera presentaciones .pptx con sistema multi-agente (Claude API), auditoría visual automática y biblioteca de credenciales.

```
mbc-decks-app/
├── backend/                    # FastAPI · Python 3.10+
│   ├── app/
│   │   ├── main.py             # FastAPI entry
│   │   ├── core/               # config, security, anthropic_client
│   │   ├── api/endpoints/      # auth, decks, interview, generate, audit, credentials
│   │   ├── services/           # orchestrator multi-agente, knowledge, visual_auditor
│   │   ├── db/                 # SQLAlchemy models + session
│   │   └── plugin_resources/   # ← copia del plugin mbc-decks (knowledge, archetypes, prompts, brand)
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/                   # Next.js 14 · TypeScript · Tailwind
│   ├── app/
│   │   ├── login/page.tsx
│   │   ├── dashboard/page.tsx
│   │   ├── new/                # wizard: tipo + entrevista + review
│   │   └── credentials/        # buscador de credenciales
│   ├── components/             # Sidebar, AuthGuard
│   ├── lib/                    # api client, store
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml          # postgres + backend + frontend
├── .env.example
└── README.md
```

## Arquitectura

```
┌─────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│   Next.js 14    │  HTTP   │    FastAPI       │  HTTP   │  Anthropic API   │
│   (frontend)    │◄───────►│    (backend)     │◄───────►│  Claude Sonnet   │
│                 │         │                  │         │  Claude Haiku    │
│  · Login        │         │  · Auth (JWT)    │         └──────────────────┘
│  · Wizard       │         │  · Multi-agente  │
│  · Audit UI     │         │  · A9 Auditor    │         ┌──────────────────┐
│  · Credenciales │         │  · python-pptx   │  CRUD   │   PostgreSQL     │
└─────────────────┘         │                  │◄───────►│  users, decks,   │
                            │                  │         │  credentials     │
                            └──────────────────┘         └──────────────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │ plugin_resources/│
                            │ (knowledge base, │
                            │  prompts,        │
                            │  archetypes,     │
                            │  brand JSONs)    │
                            └──────────────────┘
```

## Quickstart local con Docker

```bash
# 1. Clonar el repo y copiar el plugin
git clone <repo-url>
cd mbc-decks-app

# Copiar el plugin v0.3.0 a backend/app/plugin_resources/
cp -r ../mbc-decks/* backend/app/plugin_resources/
# (asegúrate de incluir skills/, assets/, knowledge/)

# 2. Configurar el entorno
cp .env.example .env
# Editar .env y poner tu ANTHROPIC_API_KEY corporativa MBC

# 3. Levantar todo
docker compose up --build

# 4. Aplicación disponible en
#    http://localhost:3000  (frontend)
#    http://localhost:8000  (backend)
#    http://localhost:8000/docs  (Swagger)

# 5. Crear primer usuario admin
docker compose exec backend python -c "
from app.db.session import SessionLocal
from app.db.models import User
from app.core.security import hash_password
db = SessionLocal()
db.add(User(email='admin@minsait.com', full_name='Admin MBC',
            role='admin', hashed_password=hash_password('cambiar123')))
db.commit()
"
```

## Quickstart sin Docker (desarrollo)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...
export DATABASE_URL=postgresql+psycopg2://localhost/mbcdecks
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Endpoints REST principales

| Método | Path | Descripción |
|---|---|---|
| POST | `/api/auth/login` | Login (email + password) → JWT |
| POST | `/api/auth/register` | Registrar usuario |
| GET | `/api/decks` | Listar decks del usuario |
| POST | `/api/decks` | Crear deck (tipo + tema + cliente) |
| GET | `/api/decks/{id}` | Detalle del deck |
| GET | `/api/decks/{id}/download` | Descargar .pptx (bloqueado si A9 marca BLOCKED) |
| GET | `/api/interview/topics` | Lista de temas con knowledge base |
| GET | `/api/interview/{deck_id}/questions` | Guion adaptativo por tema |
| POST | `/api/interview/submit` | Enviar respuestas |
| POST | `/api/generate/{deck_id}` | Disparar pipeline multi-agente (background) |
| POST | `/api/audit/{deck_id}` | Re-auditar visualmente |
| GET | `/api/audit/{deck_id}/report` | Obtener reporte A9 |
| GET | `/api/credentials` | Buscar credenciales (filtros: topic, industry, keyword) |

Documentación Swagger interactiva: `http://localhost:8000/docs`.

## Sistema multi-agente (9 agentes)

| # | Agente | Modelo | Rol |
|---|---|---|---|
| A1 | Orquestador | Haiku | Coordina flujo + handoffs |
| A2 | Investigador | Sonnet | Recopila data con fuentes citables |
| A3 | Estructurador (MBB) | Sonnet | Define narrative skeleton |
| A4 | Contenido (Redactor) | Sonnet | Escribe slides usando knowledge base |
| A5 | Visual (Diseñador) | Haiku | Mapea slides a layouts |
| A6 | Manager MBC | Haiku | Primer filtro de calidad |
| A7 | Socio Consultoría | Sonnet | Revisión estratégica |
| A8 | Socio Tech/Data | Sonnet | Revisión técnica |
| A9 | Auditor Visual | Haiku + Vision | **Bloquea entrega si hay branding hostil** |

## Deploy en producción

### Opción A — Vercel (frontend) + Railway/Render (backend + Postgres)

```bash
# Frontend en Vercel
vercel --prod

# Backend en Railway
railway up
# Configurar env vars: ANTHROPIC_API_KEY, JWT_SECRET, DATABASE_URL
```

### Opción B — AWS ECS + RDS

Ver `docs/deploy-aws.md` (a construir).

### Opción C — On-prem corporativo Minsait

Docker compose en VM dedicada Minsait. Recomendado para producción interna por compliance de datos cliente.

## Roadmap

- [ ] SSO con cuenta corporativa Minsait (Azure AD)
- [ ] Multi-tenant (separación de decks por práctica/país)
- [ ] Editor inline del deck generado (modificar antes de descargar)
- [ ] Conector OneDrive/SharePoint corporativo
- [ ] Integración con CRM (Salesforce) para auto-poblar datos del cliente
- [ ] Vision API completa para imágenes >50KB sin OCR
- [ ] Composición v4 (compose_deck.py con merge XML real)
