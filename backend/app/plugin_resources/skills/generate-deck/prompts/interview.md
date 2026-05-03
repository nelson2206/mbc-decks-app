# Guion de Entrevista Guiada — `mbc-decks` · ADAPTATIVA POR TEMA

Ejecutar **antes** de cualquier agente. Captura el brief completo del deck.

## Estructura adaptativa

La entrevista tiene **dos partes**:

1. **Bloques 0-6 base** (este archivo) — comunes a todos los temas
2. **Bloque 7 específico del tema** — cargado dinámicamente desde `knowledge/<tema>/interview_questions.md` después de identificar el tema en P0.1

**Flujo:**

```
P0.1 (tipo + tema del deck) → cargar knowledge/<tema>/
                                        ↓
P0.2-P0.5 → P1 → P2 → P3 → P4 → P5 → P6 (base, este archivo)
                                        ↓
                              P7 (knowledge/<tema>/interview_questions.md)
                                        ↓
              Brief consolidado → Investigador A2 + Estructurador A3 + Contenido A4
```

**Importante:** el A4 Contenido debe leer `knowledge/<tema>/concepts.md` antes de redactar. Sin ese conocimiento del campo, las preguntas y respuestas dan contenido genérico.

## Bloque 0 — Orientación del deck (5 preguntas, **siempre**)

### P0.1 — Tipo de deck
> ¿Qué tipo de deck necesitas crear?

Opciones:
- Propuesta comercial — venta a un cliente con énfasis consultivo
- Oferta técnica (OT/OE) — documento técnico-económico con stack y arquitectura
- Capabilities — capacidades de Minsait en una práctica o sector
- Assessment — diagnóstico de madurez de un cliente
- Iniciación de proyecto — kickoff post-venta
- Capacitación interna — formación para equipos Minsait/cliente

### P0.2 — Tema/título de trabajo
Texto libre. Una frase que capture el tema (ej: "Modelo de atención de consultas para BEI").

### P0.3 — Cliente/audiencia
Texto libre. Si es capacitación interna: nombre del programa o equipo destinatario.

### P0.4 — Fecha de entrega
Fecha objetivo del deck.

### P0.5 — Longitud
Opciones: ejecutiva (≤20 slides) · estándar (30-45) · extensa (50+)

---

## Bloque 1 — Cliente y co-branding (6 preguntas, **si NO es capacitación interna**)

### P1.1 — Razón social formal
Texto libre.

### P1.2 — Sector/industria
Opciones: Banca y Finanzas · Minería · Retail · Energía · Sector Público · Telco · Industria/Manufactura · Salud · Construcción · Agro · Educación · Otro

### P1.3 — Logo del cliente
**Pedir al usuario subir el archivo** (PNG transparente o SVG).

### P1.4 — Color institucional primario
HEX. Si no se conoce, ofrecer extraerlo del logo automáticamente.

### P1.5 — Imagen representativa
Opcional. Foto de planta, oficina, producto, etc. Para portada y/o contexto.

### P1.6 — Persona de contacto
Nombre + cargo + relación con MBC (sponsor, comprador, técnico).

---

## Bloque 2 — Contexto y reto (5 preguntas)

### P2.1 — Situación actual
Texto libre, 3-5 frases. ¿Cuál es la situación del cliente respecto al tema?

### P2.2 — Tres dolores principales
Lista breve de 3 dolores experimentados.

### P2.3 — Iniciativas previas (opcional)
¿Han intentado algo antes? ¿Por qué no funcionó?

### P2.4 — Evento detonante
¿Hay un trigger detrás del pedido? (regulación, M&A, cambio de CEO, presión competitiva, deadline, etc.)

### P2.5 — Sponsor cliente
¿Quién es el sponsor del lado cliente y qué necesita demostrar internamente?

---

## Bloque 3 — Propuesta de valor y solución (5 preguntas)

### P3.1 — Answer first
En 1 frase, ¿qué proponemos hacer?

### P3.2 — Tres pilares
Los 3 pilares de la propuesta de valor (cada uno en 1 frase).

### P3.3 — Resultados esperados
¿Qué resultados específicos debe esperar el cliente? Con métricas si las hay (% reducción, días, S/. ahorrados, NPS, etc.).

### P3.4 — Diferenciación
¿Por qué Minsait y no un competidor (Deloitte, EY, PwC, Accenture, McKinsey, BCG)? 1-3 razones diferenciales.

### P3.5 — Casos de éxito relevantes
¿Hay casos previos relevantes que debamos citar? Cliente + outcome breve.

---

## Bloque 4 — Metodología y ejecución (5 preguntas)

### P4.1 — Fases
¿Cuántas fases tendrá el proyecto y qué entrega cada una? Típico: 2-4 fases.

### P4.2 — Duración
Duración total estimada y por fase (semanas o meses).

### P4.3 — Equipo Minsait
Composición del equipo: Partner, Manager, Consultores, especialistas. Con nombres si los hay.

### P4.4 — Inputs/dependencias del cliente
¿Qué necesitamos del cliente para arrancar?

### P4.5 — Riesgos
Riesgos principales a mencionar y cómo se mitigan.

---

## Bloque 5 — Inversión (3 preguntas, **solo si el deck incluye económica**)

### P5.1 — Honorarios totales
Monto total + moneda. Rango si aún no es definitivo.

### P5.2 — Modalidad de facturación
Opciones: por fase · mensual · por hito · ad-hoc · híbrida

### P5.3 — Condiciones comerciales
Validez de oferta, gastos no incluidos, escalamiento de tarifas, condiciones de pago, etc.

---

## Bloque 7 — TEMA-ESPECÍFICO (cargado dinámicamente)

Después de completar bloques 0-6, **cargar y ejecutar** `knowledge/<deck.topic>/interview_questions.md`. Este bloque tiene 8-12 preguntas calibradas al tema:

- **PMO** → tipo de PMO, madurez, volumen portafolio, frameworks, stack, ambición IA, sponsor, KPIs
- **Data Analytics** → madurez del dato, plataforma actual, governance, casos de uso, equipo data
- **IA / GenAI** → use cases, data foundation, MLOps, riesgos éticos, vendor strategy
- **Modelo Operativo** → procesos a transformar, organización actual, stakeholders impactados, cambio
- **Transformación Digital** → palancas digitales, estado de modernización, capabilities de TI
- **Ciberseguridad** → marco (NIST, ISO 27001), incidentes recientes, regulaciones, compliance
- **ESG** → estado de reporting, compromisos públicos, marcos (GRI, SASB, TCFD), inversores
- **Eficiencia Operacional** → procesos a optimizar, KPIs de costo, automatización RPA/IA
- **Capabilities** → audiencia, qué capacidad mostrar, cliente objetivo

Si no existe `knowledge/<tema>/interview_questions.md`, saltar este bloque y dejar nota `[NEED-KNOWLEDGE-BASE: <tema>]` para que el equipo MBC lo construya.

## Bloque 6 — Avanzado (3 preguntas, **opcional**)

### P6.1 — Ángulos sensibles
¿Hay temas que cuidar? (incumbentes, conflictos previos, política interna del cliente, sensibilidades culturales).

### P6.2 — Research solicitado
¿Quieres que el Investigador busque algún dato específico del sector/cliente? (ranking, market share, benchmarks, etc.)

### P6.3 — Tono preferido
Opciones: institucional formal · consultivo cercano · técnico detallado

---

## Modo express (alternativa a la entrevista completa)

Si el usuario pide ir más rápido, ejecutar solo:
- P0.1, P0.2, P0.3 (tipo, tema, cliente)
- P1.2, P1.3 (sector, logo del cliente)
- P2.1 (situación actual)
- P3.1, P3.2 (answer first + 3 pilares)
- P4.1, P4.2 (fases y duración)
- P5.1 (honorarios)

Total: 10 preguntas. El resto se infiere o se marca como `[ASK-USER]` en la revisión final.

---

## Output del bloque de entrevista

Generar un archivo `deck_brief.json` con la estructura:

```json
{
  "deck": {
    "type": "proposal_commercial",
    "topic": "...",
    "title_working": "...",
    "delivery_date": "...",
    "length_target": "estandar",
    "tone": "consultivo_cercano"
  },
  "client": {
    "name_commercial": "...",
    "name_legal": "...",
    "sector": "...",
    "logo_path": "...",
    "brand_color_hex": "...",
    "image_cover_path": "...",
    "contact": {"name": "...", "role": "..."}
  },
  "context": {
    "current_situation": "...",
    "pains": ["...", "...", "..."],
    "previous_attempts": "...",
    "trigger_event": "...",
    "client_sponsor": "..."
  },
  "value_proposition": {
    "one_liner": "...",
    "pillars": ["...", "...", "..."],
    "expected_results": "...",
    "differentiation": ["...", "...", "..."],
    "case_studies_relevant": ["..."]
  },
  "methodology": {
    "phases": [{"name": "...", "deliverables": [...], "duration_weeks": ...}],
    "total_duration": "...",
    "team": [{"role": "Partner", "name": "..."}, ...],
    "client_dependencies": ["..."],
    "risks": [{"risk": "...", "mitigation": "..."}]
  },
  "investment": {
    "total_amount": "...",
    "currency": "PEN",
    "billing_modality": "...",
    "commercial_conditions": "..."
  },
  "advanced": {
    "sensitive_topics": "...",
    "research_requested": ["..."],
    "tone": "..."
  }
}
```
