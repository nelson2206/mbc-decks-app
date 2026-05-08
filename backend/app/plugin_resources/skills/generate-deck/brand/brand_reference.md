# Manual de Marca · Minsait Powerpoint Guidelines

Resumen ejecutivo del brandbook oficial Minsait (Oct 2024) más patrones extraídos del corpus real de propuestas Minsait Business Consulting.

---

## 1 · Tipografía oficial · ForFuture Sans

**Fuente única en TODA la presentación: ForFuture Sans** (variantes Regular y Bold). NO usar Arial, Calibri, Helvetica.

| Uso | Variante | Tamaño |
|---|---|---|
| Título principal (en separatas/portadas) | ForFuture Regular | **32pt** |
| Subtítulo | ForFuture Regular | **14pt** |
| Cuerpo de texto / bullets | ForFuture Regular | **11pt** |
| Cuerpo en destacados/técnicos | ForFuture Sans Bold | secundario |
| Footer | ForFuture Regular | 8-9pt |
| Tablas y gráficos · mínimo legible | ForFuture Regular | **8pt** |
| Texto en visores/destacados | ForFuture Bold | a definir |

**Regla:** títulos máximo 2 líneas. Si el título no cabe en 2 líneas a 32pt, **acortar** o reescribir más answer-first.

**Énfasis:**
- Bold o Italic SOLO para citas o énfasis específico
- Para acentuar palabras clave dentro de un título, **cambiar color a Púrpura (Magenta)** en lugar de bold

---

## 2 · Paleta corporativa

### Primarios (fondos)

| Color | Hex | Uso |
|---|---|---|
| **Pruno (Morado)** | `#4F062A` | **Mayoría** · portadas, separatas de primer nivel, cierres |
| **Morado Oscuro** | `#33041B` | Mismos usos pero tono más sobrio |
| **Cerámica (Gris)** | `#E8DDD2` | **Slides interiores** y contenido neutro |
| **Blanco** | `#FFFFFF` | Slides estándar de contenido |

### Secundarios (texto, accents, gráficos)

| Color | Hex | Uso |
|---|---|---|
| **Cerámica/Blanco** | varios | Texto sobre fondos OSCUROS |
| **Azul Amazónico** | (consultar template) | Texto sobre fondos CLAROS |
| **Púrpura/Magenta** | `#C8217A` | **Resaltado** · títulos clave, palabras destacadas, accents |

### Reglas de contraste

- Pruno o Morado Oscuro de fondo → texto en Blanco/Cerámica
- Cerámica o Blanco de fondo → texto en Pruno/Azul Amazónico
- Púrpura es para **acentuación**, no para bloques grandes de texto

---

## 3 · Layout y márgenes

**Módulo M = 1/32 del lado más largo** del slide (en 16:9 a 13.33in → **M ≈ 0.417in**).

### Reglas duras

1. **Márgenes:** mínimo M en todo el perímetro (≈ 0.42in en 16:9)
2. **Distancia mínima entre elementos:** 1/3 de M (≈ 0.14in)
3. **Líneas decorativas:** grosor por default **0.5pt**
4. **NO escalar contenedores manualmente** — usar los pre-diseñados del template para preservar chaflanes (esquinas redondeadas)

### Ratios disponibles

- 16:9 horizontal (default propuestas)
- 9:16 vertical
- 1:1 cuadrado

---

## 4 · Anatomía de slide (patrones extraídos del corpus real)

Análisis de Marzo26_Formación PM, OE Ferreyros PMO, Alpayana Assessment:

### Slide standard de contenido

```
┌──────────────────────────────────────────────────────┐
│ 01. CAPÍTULO (antetitle 11pt magenta caps)         │
│ Título answer-first largo (16-22pt pruno)           │
│ Subtítulo o descripción intro (12-14pt gris) ────  │ ← línea decorativa 0.5pt
│                                                      │
│ Sección 1 (10-11pt)        Sección 2 (10-11pt)     │
│ · bullet                    · bullet                │
│ · bullet                    · bullet                │
│                                                      │
│ MINSAIT | Nombre doc · dd/mm/aaaa            (8pt) │ ← footer corporativo
└──────────────────────────────────────────────────────┘
```

**Distancia título → body:** 1/3 M
**Distancia body → footer:** 1 M
**Footer position:** abajo izquierda o abajo derecha

### Footer · formato OBLIGATORIO

```
MINSAIT • Nombre del documento • dd/mm/aaaa
```

(separador `•` punto medio, no `·` ni `|` en el brandbook oficial — pero el corpus usa ambos)

Tamaño 8-9pt, color Pruno o Cerámica según fondo.

### Antetitle (etiqueta de capítulo)

Formato típico: `"01 · CONTEXTO"` o `"01. Marco conceptual"` en magenta CAPS, 10-11pt bold.

---

## 5 · Tablas y gráficos

### Tablas

- Header en Pruno con texto blanco bold
- Filas alternadas (Cerámica + Blanco) para legibilidad
- Mínimo 8pt en celdas
- Fila TOTAL destacada en Pruno
- Texto vertical-anchor MIDDLE en celdas
- Margen interno 0.04-0.12in

### Gráficos

- Fondos Pruno o Morado Oscuro para mejor contraste
- Paleta secundaria para barras/líneas (mezclar magenta + cerámica + amazónico)
- Texto mínimo 8pt
- Contenedores sólidos para enmarcar

---

## 6 · Visores y nodos (decoración corporativa)

Los visores son marcos de 4 nodos en las esquinas que encapsulan imágenes o textos importantes. Versión positiva (claros) o negativa (oscuros).

**Regla:** siempre 4 nodos por visor para mantener coherencia.

---

## 7 · Imágenes y fotografías

- Colores vibrantes alineados a paleta morada
- Luz creativa (neones, haces de luz morados) que enfatiza tecnología y futurismo
- Simetría y orden, enfoque en precisión y eficiencia
- Dentro de contenedores con chaflán O a tamaño completo si calidad lo permite
- Método de máscara: Shape Format > Merge > Intersect

---

## 8 · Animaciones

- **SOLO efecto Fade** (transiciones suaves)
- Aplicar puntualmente, no en todas las slides
- Casos: generar expectativa, introducir información gradualmente, separar secciones

---

## 9 · Layouts pre-construidos (en el .potx)

40 layouts disponibles. Usar SIEMPRE estos, NO crear desde cero:

| Familia | Índices | Cuándo |
|---|---|---|
| Portadas | 0-10 | Cover con/sin partner, fondos varios |
| Índices | 11-12 | Tabla de contenidos |
| Separatas | 13-16 | Dividers de capítulo |
| Contenido texto | 17-24 | Slides estándar |
| Contenido imagen | 25-26 | Imagen dominante |
| Contenido split | 27 | Texto + imagen lado a lado |
| Idea principal | 28-29 | Quote/key idea destacada |
| Vacías | 30-32 | Para layouts custom |
| Cierres | 33-38 | Closing con/sin datos |
| Portada Básica | 39 | Cover simple |

---

## 10 · Reglas de oro · checklist final

✅ ForFuture Sans en TODO el deck (no Arial, no Calibri)
✅ Títulos máx 2 líneas a 32pt en separatas, 22-28pt en contenido
✅ Footer "MINSAIT • Cliente · dd/mm/aaaa" en TODOS los slides excepto cover/closing
✅ Antetitle "0X · CAPÍTULO" en magenta caps en cada content slide
✅ Paleta solo de la corporativa Minsait (Pruno, Magenta, Cerámica, Blanco, Amazónico)
✅ Líneas decorativas 0.5pt
✅ Contenedores sin escalar (preservan chaflán)
✅ Body 11pt · headers tabla 11pt · footnote 8pt
✅ Animaciones solo Fade
✅ Nodos en visores: SIEMPRE 4

## 11 · Patrones extraídos del corpus real (override sobre brandbook donde aplica)

**Análisis de 5 decks reales (Ferreyros PMO, Marzo26 PM, Alpayana, Izipay, Corporativa):**

- Tamaño dominante de body: **10.5-12pt** (no 11pt estricto)
- Tamaño de subtítulos importantes: **14pt regular**
- Tamaño de títulos de slide standard: **16pt** (más usado), 18pt, hasta 24pt
- Tamaño de portadas/separatas: **48pt** (mucho mayor que el 32pt del brandbook)
- Antetitle en corpus: pequeño (8-10pt), magenta caps
- Footer en corpus: 8pt grey

**Tolerar 10.5pt y 12pt como body sizes válidos** (no flaggear como issue).
