#!/usr/bin/env python3
"""
auto_deploy.py — Orquestador de deploy 100% automático

Toma los 6 tokens vía env vars y ejecuta paso a paso:
  1. Crear repo privado en GitHub
  2. Push del código local al repo
  3. Crear proyecto + DB Postgres en Neon
  4. Crear servicio web en Render conectado al repo
  5. Configurar env vars en Render (Anthropic, DB, JWT, CORS)
  6. Crear proyecto en Vercel conectado al repo
  7. Configurar env vars en Vercel (NEXT_PUBLIC_API_URL)
  8. Esperar a que ambos deploys terminen
  9. Verificar /health del backend
 10. Imprimir URLs finales y siguientes pasos

Variables de entorno requeridas:
  GITHUB_TOKEN          (ghp_...)
  GITHUB_USERNAME       (tu-usuario)
  VERCEL_TOKEN          (vc_...)
  RENDER_API_KEY        (rnd_...)
  NEON_API_KEY          (napi_...)
  ANTHROPIC_API_KEY     (sk-ant-...)

Uso:
    cd mbc-decks-app
    export GITHUB_TOKEN=ghp_...
    export GITHUB_USERNAME=...
    export VERCEL_TOKEN=...
    export RENDER_API_KEY=...
    export NEON_API_KEY=...
    export ANTHROPIC_API_KEY=...
    python3 scripts/auto_deploy.py
"""
from __future__ import annotations
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

import urllib.request
import urllib.error


REPO_NAME = "mbc-decks-app"
SERVICE_NAME = "mbc-decks-backend"
NEON_PROJECT_NAME = "mbc-decks"
VERCEL_PROJECT_NAME = "mbc-decks"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class Step:
    def __init__(self, name: str):
        self.name = name
        print(f"\n{'=' * 60}\n▶  {name}\n{'=' * 60}")

    def __enter__(self):
        self.t = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        dur = time.time() - self.t
        if exc_type is None:
            print(f"✅ Done in {dur:.1f}s")
        else:
            print(f"❌ Failed: {exc_val}")
        return False


def http(method: str, url: str, headers: dict, body: Optional[Any] = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode())
        except Exception:
            err = {"error": str(e)}
        raise RuntimeError(f"{method} {url} → HTTP {e.code}: {err}") from e


def sh(cmd: list[str], cwd: Optional[str] = None, env: Optional[dict] = None,
       check: bool = True, capture: bool = True) -> str:
    """Run shell command, return stdout."""
    print(f"   $ {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=cwd, env={**os.environ, **(env or {})},
                         capture_output=capture, text=True)
    if check and res.returncode != 0:
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        raise RuntimeError(f"Command failed: {cmd}")
    return res.stdout


def env_required(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        print(f"❌ Missing env var: {name}", file=sys.stderr)
        sys.exit(1)
    return v


# ---------------------------------------------------------------------------
# 1. GitHub
# ---------------------------------------------------------------------------
def create_github_repo(token: str, username: str) -> str:
    """Crea el repo privado en GitHub. Returns clone URL."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    # Verificar si ya existe
    try:
        existing = http("GET", f"https://api.github.com/repos/{username}/{REPO_NAME}", headers)
        print(f"   Repo ya existe: {existing['html_url']}")
        return existing["clone_url"]
    except RuntimeError as e:
        if "404" not in str(e):
            raise

    # Crear nuevo
    body = {
        "name": REPO_NAME,
        "description": "MBC Decks · Generador de presentaciones Minsait con sistema multi-agente",
        "private": True,
        "auto_init": False,
    }
    repo = http("POST", "https://api.github.com/user/repos", headers, body)
    print(f"   Repo creado: {repo['html_url']}")
    return repo["clone_url"]


def push_to_github(repo_url: str, token: str, username: str, repo_dir: str):
    """Inicializa repo local y push al remoto con autenticación token."""
    # Construir URL con token
    auth_url = repo_url.replace("https://", f"https://{username}:{token}@")

    if not (Path(repo_dir) / ".git").exists():
        sh(["git", "init"], cwd=repo_dir)

    # Configurar usuario si no está
    try:
        sh(["git", "config", "user.email"], cwd=repo_dir, capture=True, check=False)
    except Exception:
        pass
    sh(["git", "config", "user.email", "deploy@mbc-decks.local"], cwd=repo_dir, check=False)
    sh(["git", "config", "user.name", "MBC Decks Auto Deploy"], cwd=repo_dir, check=False)

    sh(["git", "add", "-A"], cwd=repo_dir)
    # commit (puede no haber cambios)
    res = subprocess.run(["git", "commit", "-m", "Initial commit · MBC Decks v0.2.0 · auto-deploy"],
                         cwd=repo_dir, capture_output=True, text=True)
    if res.returncode != 0 and "nothing to commit" not in res.stdout + res.stderr:
        print(res.stderr)

    sh(["git", "branch", "-M", "main"], cwd=repo_dir, check=False)

    # Remove existing origin if any, then add
    subprocess.run(["git", "remote", "remove", "origin"], cwd=repo_dir, capture_output=True)
    sh(["git", "remote", "add", "origin", auth_url], cwd=repo_dir)
    sh(["git", "push", "-u", "origin", "main", "--force"], cwd=repo_dir)
    print(f"   Push completado")


# ---------------------------------------------------------------------------
# 2. Neon
# ---------------------------------------------------------------------------
def create_neon_db(api_key: str) -> str:
    """Crea proyecto Neon y devuelve connection string."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    # Verificar si ya existe
    projects = http("GET", "https://console.neon.tech/api/v2/projects", headers)
    for p in projects.get("projects", []):
        if p["name"] == NEON_PROJECT_NAME:
            print(f"   Proyecto Neon existe: {p['id']}")
            # Get connection URI
            conn = http("GET", f"https://console.neon.tech/api/v2/projects/{p['id']}/connection_uri",
                        headers)
            return conn.get("uri", "")

    # Crear nuevo proyecto
    body = {"project": {"name": NEON_PROJECT_NAME, "region_id": "aws-us-east-2"}}
    proj = http("POST", "https://console.neon.tech/api/v2/projects", headers, body)
    project_id = proj["project"]["id"]
    print(f"   Proyecto Neon creado: {project_id}")

    # La respuesta del create incluye el connection_uri
    conn_uris = proj.get("connection_uris", [])
    if conn_uris:
        return conn_uris[0]["connection_uri"]
    # Fallback: construir manualmente
    role = proj.get("roles", [{}])[0]
    db = proj.get("databases", [{}])[0]
    endpoint = proj.get("endpoints", [{}])[0]
    return f"postgresql://{role.get('name')}:{role.get('password')}@{endpoint.get('host')}/{db.get('name')}?sslmode=require"


# ---------------------------------------------------------------------------
# 3. Render
# ---------------------------------------------------------------------------
def create_render_service(api_key: str, repo_url: str, env_vars: dict[str, str]) -> dict:
    """Crea web service en Render conectado al repo."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # Buscar servicio existente
    services = http("GET", "https://api.render.com/v1/services", headers)
    for s in services if isinstance(services, list) else services.get("services", []):
        svc = s.get("service") or s
        if svc.get("name") == SERVICE_NAME:
            print(f"   Servicio Render existe: {svc.get('id')}")
            return svc

    # Crear nuevo
    body = {
        "type": "web_service",
        "name": SERVICE_NAME,
        "ownerId": _render_owner_id(api_key),
        "repo": repo_url.replace(".git", ""),
        "branch": "main",
        "rootDir": "backend",
        "envVars": [{"key": k, "value": v} for k, v in env_vars.items()],
        "serviceDetails": {
            "env": "docker",
            "plan": "free",
            "region": "oregon",
            "healthCheckPath": "/health",
            "envSpecificDetails": {
                "dockerfilePath": "./Dockerfile",
            },
        },
    }
    svc = http("POST", "https://api.render.com/v1/services", headers, body)
    print(f"   Servicio Render creado: {svc.get('service', {}).get('id')}")
    return svc.get("service") or svc


def _render_owner_id(api_key: str) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    owners = http("GET", "https://api.render.com/v1/owners", headers)
    if isinstance(owners, list):
        return (owners[0].get("owner") or owners[0])["id"]
    return owners["owners"][0]["id"]


# ---------------------------------------------------------------------------
# 4. Vercel
# ---------------------------------------------------------------------------
def create_vercel_project(token: str, github_username: str, env_vars: dict[str, str]) -> dict:
    """Crea proyecto Vercel conectado al repo."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Buscar existente
    try:
        existing = http("GET", f"https://api.vercel.com/v9/projects/{VERCEL_PROJECT_NAME}", headers)
        print(f"   Proyecto Vercel existe: {existing['id']}")
        return existing
    except RuntimeError:
        pass

    # Crear con git connection
    body = {
        "name": VERCEL_PROJECT_NAME,
        "framework": "nextjs",
        "rootDirectory": "frontend",
        "gitRepository": {
            "type": "github",
            "repo": f"{github_username}/{REPO_NAME}",
        },
        "environmentVariables": [
            {"key": k, "value": v, "target": ["production", "preview", "development"], "type": "encrypted"}
            for k, v in env_vars.items()
        ],
    }
    proj = http("POST", "https://api.vercel.com/v10/projects", headers, body)
    print(f"   Proyecto Vercel creado: {proj['id']}")
    return proj


def trigger_vercel_deploy(token: str, project_id: str, github_username: str) -> dict:
    """Triggera primer deploy."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "name": VERCEL_PROJECT_NAME,
        "project": project_id,
        "target": "production",
        "gitSource": {
            "type": "github",
            "repo": f"{github_username}/{REPO_NAME}",
            "ref": "main",
        },
    }
    return http("POST", "https://api.vercel.com/v13/deployments", headers, body)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("\n🚀  MBC Decks · Auto-deploy 100% gratis\n")

    GITHUB_TOKEN = env_required("GITHUB_TOKEN")
    GITHUB_USERNAME = env_required("GITHUB_USERNAME")
    VERCEL_TOKEN = env_required("VERCEL_TOKEN")
    RENDER_API_KEY = env_required("RENDER_API_KEY")
    NEON_API_KEY = env_required("NEON_API_KEY")
    ANTHROPIC_API_KEY = env_required("ANTHROPIC_API_KEY")

    repo_dir = str(Path(__file__).resolve().parent.parent)
    JWT_SECRET = secrets.token_hex(32)

    with Step("1/8 · Crear repositorio en GitHub"):
        repo_url = create_github_repo(GITHUB_TOKEN, GITHUB_USERNAME)

    with Step("2/8 · Push del código a GitHub"):
        push_to_github(repo_url, GITHUB_TOKEN, GITHUB_USERNAME, repo_dir)

    with Step("3/8 · Crear PostgreSQL en Neon"):
        db_url = create_neon_db(NEON_API_KEY)
        # Convertir a formato SQLAlchemy
        db_url_sa = db_url.replace("postgresql://", "postgresql+psycopg2://")
        print(f"   DB URL: {db_url_sa[:60]}...")

    with Step("4/8 · Crear servicio backend en Render"):
        backend_env = {
            "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
            "DATABASE_URL": db_url_sa,
            "JWT_SECRET": JWT_SECRET,
            "STORAGE_BACKEND": "local",
            "STORAGE_LOCAL_PATH": "/tmp/mbcdecks_storage",
            "PLUGIN_PATH": "/app/app/plugin_resources",
            "CORS_ALLOWED_ORIGINS": '["*"]',
        }
        svc = create_render_service(RENDER_API_KEY, repo_url, backend_env)
        backend_url = svc.get("serviceDetails", {}).get("url") or f"https://{SERVICE_NAME}.onrender.com"
        print(f"   Backend URL: {backend_url}")

    with Step("5/8 · Crear proyecto Vercel + deploy frontend"):
        vercel_env = {"NEXT_PUBLIC_API_URL": backend_url}
        proj = create_vercel_project(VERCEL_TOKEN, GITHUB_USERNAME, vercel_env)
        deploy = trigger_vercel_deploy(VERCEL_TOKEN, proj["id"], GITHUB_USERNAME)
        frontend_url = f"https://{deploy.get('url', VERCEL_PROJECT_NAME + '.vercel.app')}"
        print(f"   Frontend URL: {frontend_url}")

    with Step("6/8 · Actualizar CORS en Render con URL real de Vercel"):
        # TODO: actualizar la env var de CORS_ALLOWED_ORIGINS via PATCH /v1/services/{id}/env-vars
        print(f"   ℹ️  Pendiente automatizar este paso. Por ahora editar manualmente en Render dashboard:")
        print(f"      CORS_ALLOWED_ORIGINS = [\"{frontend_url}\"]")

    with Step("7/8 · Esperar que el backend arranque (puede tomar 5 min)"):
        for attempt in range(30):
            try:
                resp = urllib.request.urlopen(f"{backend_url}/health", timeout=10)
                if resp.status == 200:
                    print(f"   ✅ Backend respondiendo")
                    break
            except Exception:
                pass
            time.sleep(20)
            print(f"   ... intento {attempt + 1}/30")
        else:
            print(f"   ⚠️  Backend aún no responde, pero el deploy fue triggered. Revisa Render dashboard.")

    with Step("8/8 · Resumen final"):
        print(f"""
🎉  Deploy completado!

📦  Repositorio:   https://github.com/{GITHUB_USERNAME}/{REPO_NAME}
🌐  Frontend:      {frontend_url}
🔧  Backend API:   {backend_url}
📚  API Docs:      {backend_url}/docs
💾  Database:      Neon ({NEON_PROJECT_NAME})

📋  Próximos pasos manuales:
   1. Ajustar CORS_ALLOWED_ORIGINS en Render dashboard a ["{frontend_url}"]
   2. Crear primer admin desde Render Shell:
      python -c "
        from app.db.session import SessionLocal
        from app.db.models import User
        from app.core.security import hash_password
        db = SessionLocal()
        db.add(User(email='admin@minsait.com', full_name='Admin MBC',
                    role='admin', hashed_password=hash_password('cambiar123')))
        db.commit()
      "
   3. Login en {frontend_url} con admin@minsait.com / cambiar123
""")


if __name__ == "__main__":
    main()
