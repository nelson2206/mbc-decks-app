---
name: mbc-decks:generate-deck
description: Genera una presentación corporativa para Minsait Business Consulting (MBC) a partir de un tema y un cliente. Conduce una entrevista guiada exhaustiva (25-30 preguntas), activa un sistema multi-agente especializado (investigador, estructurador MBB, redactor ejecutivo, diseñador visual, manager y socios revisores) y produce un .pptx con la plantilla oficial Minsait, aplicando co-branding cliente cuando corresponde. Triggers: "armar una propuesta", "generar deck Minsait", "presentación MBC", "necesito una propuesta para [cliente]", "deck para [cliente]", "presentación de capabilities", "assessment", "oferta técnica", "OT", "iniciación de proyecto", "capacitación interna", "training Minsait".
---

# MBC Decks — Generador de presentaciones Minsait Business Consulting

Este skill genera presentaciones .pptx con identidad de marca MBC usando un sistema multi-agente que replica la operación de una consultora MBB (McKinsey/BCG/Bain).

## Cuándo activarse

- El usuario pide crear una propuesta, oferta, deck, presentación, assessment, capacidades o capacitación con marca Minsait
- El usuario menciona un cliente al que dirigir un deck
- El usuario sube un brief y pide convertirlo en presentación

## Flujo de operación

### Paso 1 — Entrevista guiada (obligatorio)

Lee `prompts/interview.md` y ejecuta la entrevista por bloques usando AskUserQuestion. La entrevista es ramificada según el tipo de deck:

- Bloque 0 — Orientación del deck (5 preguntas, todas)
- Bloque 1 — Cliente y co-branding (6 preguntas, si NO es capacitación interna)
- Bloque 2 — Contexto y reto (5 preguntas)
- Bloque 3 — Propuesta de valor (5 preguntas)
- Bloque 4 — Metodología y ejecución (5 preguntas)
- Bloque 5 — Inversión (3 preguntas, solo propuestas con económica)
- Bloque 6 — Avanzado (3 preguntas, opcional)

**No saltes bloques.** Si el usuario quiere ir más rápido, ofrécele el modo "express" (6-8 preguntas core) explícitamente.

### Paso 2 — Selección del archetype

Una vez tipificado el deck, carga el archetype JSON correspondiente desde `archetypes/`:

| Tipo | Archivo |
|---|---|
| Propuesta comercial | proposal_commercial.json |
| Oferta técnica (OT/OE) | proposal_technical.json |
| Capabilities | proposal_capabilities.json |
| Assessment | proposal_assessment.json |
| Iniciación de proyecto | proposal_initiation.json |
| Capacitación interna | training_internal.json |

El archetype define el esqueleto de slides, los layouts a usar y las secciones obligatorias vs. opcionales.

### Paso 3 — Pipeline multi-agente

Ejecuta los agentes en orden (lee cada prompt desde `prompts/`):

1. **researcher.md** → Investigador. Recopila datos oficiales con fuentes citables. Output: `research_brief.md`.
2. **structurer.md** → Estructurador (Consultor MBB Senior). Define la storyline. Output: `narrative_skeleton.json`.
3. **content.md** → Redactor ejecutivo. Escribe el contenido final. Output: `slide_content.json`.
4. **visual.md** → Diseñador. Mapea cada slide a su layout y prepara las instrucciones python-pptx. Output: `slide_plan.json`.
5. **scripts/generate_pptx.py** → Genera el .pptx usando la plantilla oficial.
6. **manager.md** → Manager MBC. Revisa coherencia y calidad táctica. Output: `review_manager.md`.
7. **partner_consulting.md** → Socio Consultoría. Revisa estrategia. Output: `review_partner_consulting.md`.
8. **partner_tech.md** → Socio Tech/Data. Revisa viabilidad técnica. Output: `review_partner_tech.md`.
9. **orchestrator.md** → Consolida revisiones, aplica fixes auto-resolubles y reporta los issues que requieren input humano.

Política: máximo 2 ciclos de revisión. Si tras 2 ciclos hay issues no resueltos, el deck se entrega con anotaciones marcadas como `[REVISAR]`.

### Paso 4a — Validación de marca

Antes de entregar, ejecuta `scripts/validate_brand.py` para auditar:
- Tipografía (toda ForFuture Sans)
- Colores (todos en la paleta oficial)
- Layouts (todos del catálogo de 40)
- Footer en formato `MINSAIT • Nombre del documento • dd/mm/aaaa`
- Logos según las reglas de co-branding

### Paso 4b — Auditoría Visual (A9, OBLIGATORIO)

**Bloqueador antes de entregar.** Ejecuta `scripts/image_auditor.py` con el cliente target y su industria:

```
python scripts/image_auditor.py <deck.pptx> --client "Ferreyros" --industry "industria_consumo_energia" \
  --report-md visual_audit.md --cache .audit_cache.json
```

El A9 audita TODAS las imágenes del deck contra:
- `brand/competitors_db.json` — competidores conocidos por industria (Komatsu, Liebherr, Hitachi, EY, PwC, etc.)
- `brand/minsait_clients_db.json` — otros clientes Minsait (Distriluz, Endesa, BBVA, BCP, etc.)
- `brand/approved_logos_db.json` — software/herramientas aprobadas (Microsoft, SAP, Power BI, etc.)

**Salidas posibles:**
- `audit_status: PASSED` → puedes entregar
- `audit_status: BLOCKED_RECOMMENDED` → hay branding de otros clientes Minsait, reemplazar antes de entregar
- `audit_status: BLOCKED` → hay branding de competencia directa, **NO ENTREGAR**. Aplicar reemplazos en `image_replacements` del edit_map.json y regenerar.

Iterar hasta que el A9 devuelva `PASSED`.

### Paso 5 — Entrega

Entrega al usuario:

1. `<nombre>_v1.pptx` — el deck generado
2. `research_brief.md` — el dossier del investigador con fuentes
3. `review_consolidated.md` — comentarios de los 3 revisores con priorización
4. Lista de issues `[ASK-USER]` que requieren su input

## Archivos de referencia

- `brand/colors.json` — paleta oficial con HEX
- `brand/typography.json` — reglas tipográficas
- `brand/layout_catalog.json` — los 40 layouts mapeados a tipos semánticos
- `brand/co_branding_rules.json` — reglas de inserción de marca cliente

## Reglas inviolables

1. **Nunca crear slides desde cero.** Siempre instanciar desde un layout del catálogo.
2. **Nunca cambiar la paleta Minsait.** El color del cliente solo aparece en su propio logo y en acentos puntuales.
3. **Toda cifra requiere fuente.** Si el Investigador no encontró fuente, marcar como `[ESTIMACIÓN — validar con cliente]`.
4. **Tono consultivo en primera persona plural** ("Proponemos…", "Entendemos que…", "Sugerimos…"). Cero adjetivos vacíos ("innovador", "robusto", "best-in-class").
5. **Footer en todas las slides excepto portada y cierre,** con formato exacto.
6. **Capacitaciones internas: 100% Minsait,** sin co-branding cliente.
7. **Propuestas comerciales: portada con co-branding usando layouts 6, 7 u 8.**
