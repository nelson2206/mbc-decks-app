# mbc-decks · Generador de presentaciones Minsait Business Consulting

Plugin de Cowork/Claude que genera presentaciones .pptx con la marca y los arquetipos narrativos oficiales de Minsait Business Consulting.

## ¿Qué hace?

Toma un tema y un cliente, ejecuta una entrevista guiada exhaustiva (25-30 preguntas) y produce un deck completo aplicando:

- Plantilla oficial de Minsait (40 layouts categorizados)
- Paleta de colores con HEX exactos (Pruno, Cerámica, Magenta, Azul Amazónico, etc.)
- Tipografía ForFuture Sans con tamaños del brandbook
- Reglas de co-branding cliente cuando corresponda
- Arquetipos narrativos según el tipo de deck (propuesta comercial, oferta técnica, capabilities, assessment, iniciación, capacitación)

## Sistema multi-agente

El plugin opera con 8 agentes especializados que replican el flujo de una consultora MBB:

1. **Orquestador** — coordina el flujo y los handoffs
2. **Investigador** — recopila data oficial con fuentes citables
3. **Estructurador (MBB Senior)** — define la storyline
4. **Contenido (Redactor ejecutivo)** — escribe el contenido final
5. **Visual (Diseñador)** — mapea cada slide a su layout y prepara python-pptx
6. **Manager** — primer filtro de calidad
7. **Socio Consultoría** — revisa estrategia y comercial
8. **Socio Tech/Data** — revisa viabilidad técnica

## Estructura del plugin

```
mbc-decks/
├── plugin.json                  # manifest
├── README.md                    # este archivo
├── skills/
│   └── generate-deck/
│       ├── SKILL.md             # entry point
│       ├── prompts/             # 8 prompts de agentes + interview.md
│       ├── archetypes/          # 6 sub-tipos de deck
│       ├── brand/               # JSONs de marca
│       └── scripts/             # generate_pptx.py, validate_brand.py
├── assets/
│   ├── template/                # plantilla .potx oficial + brandbook
│   ├── fonts/                   # ForFuture Sans (OTF)
│   └── logos/                   # logos Minsait
└── samples/                     # decks de ejemplo generados
```

## Uso típico

```
Usuario → "Necesito una propuesta para Banco X sobre transformación de cierre contable"
Cowork detecta el trigger del skill y carga `generate-deck`
↓
[Entrevista guiada — 25 preguntas en bloques]
↓
[Investigador] busca data sectorial con fuentes
↓
[Estructurador] arma la storyline consultiva
↓
[Contenido] redacta cada slide
↓
[Visual] mapea a layouts y prepara python-pptx
↓
[generate_pptx.py] produce el .pptx
↓
[Manager + Socios] revisan
↓
[Orquestador] aplica fixes y entrega:
   - {{deck}}_v1.pptx
   - research_brief.md
   - review_consolidated.md
```

## Instalación

### Como plugin de Cowork

1. Descarga el archivo `mbc-decks.plugin` (resultado de empaquetar este árbol)
2. En Cowork, instala desde la sección de plugins
3. Reinicia o recarga la sesión
4. Activa con cualquiera de los triggers documentados en `SKILL.md`

### Manual (modo desarrollo)

```bash
# Instalar dependencias
pip install python-pptx Pillow pypdf --break-system-packages

# Probar el motor de generación con un brief de muestra
python skills/generate-deck/scripts/generate_pptx.py \
  samples/sample_slide_plan.json \
  samples/sample_slide_content.json \
  samples/sample_deck_brief.json \
  samples/output_test.pptx

# Validar marca
python skills/generate-deck/scripts/validate_brand.py samples/output_test.pptx
```

## Reglas inviolables

1. Nunca crear slides desde cero — siempre desde un layout del catálogo
2. Nunca cambiar la paleta Minsait (el color del cliente solo aparece en su logo)
3. Toda cifra requiere fuente
4. Tono consultivo en primera persona plural · cero adjetivos vacíos
5. Footer en todas las slides excepto portada y cierre
6. Capacitaciones internas: 100% Minsait, sin co-branding cliente
7. Propuestas comerciales: portada con co-branding usando layouts 5, 6 u 7

## Licencia

Uso interno Minsait Business Consulting.

## Versión

`v0.1.0` — Mayo 2026 · Generación inicial del plugin.
