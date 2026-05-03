# PMO · Conceptos Clave que el Agente debe Dominar

> Este documento es la "biblioteca mental" del agente A4 (Contenido) para el tema PMO. Antes de redactar contenido sobre PMO, el agente DEBE leer este archivo + frameworks.md + metrics.md + minsait_differentiators.md. La regla es: cada afirmación que escribimos en un deck PMO debe poder rastrearse a un concepto establecido en este knowledge base, o marcarse explícitamente como [opinión Minsait].

---

## 1. Definición y propósito de una PMO

**PMO (Project Management Office)** es la unidad organizacional responsable de gobernar el portafolio, programa y/o proyectos. Su misión es maximizar el valor entregado por la inversión en proyectos a través de estandarización, gobierno, soporte y/o ejecución directa.

PMI define 3 funciones principales:
1. **Estandarizar** prácticas, herramientas y plantillas
2. **Soportar** a project managers (entrenamiento, coaching, herramientas)
3. **Ejecutar** o gobernar directamente el portafolio (depende del tipo)

## 2. Tipologías de PMO (PMI · 3 tipos canónicos)

| Tipo | Nivel de control | Cuándo aplica |
|---|---|---|
| **Supportive PMO** | Bajo · provee templates, training, mejores prácticas | Organizaciones maduras donde los PMs ya son competentes y necesitan asistencia |
| **Controlling PMO** | Medio · provee soporte + audita cumplimiento de estándares | Organizaciones que necesitan estandarización pero respetan autonomía de PMs |
| **Directive PMO** | Alto · gestiona directamente los proyectos (los PMs reportan a la PMO) | Programas grandes, proyectos críticos, baja madurez de PM en la organización |

**Variante moderna:** **Strategic PMO / EPMO (Enterprise PMO)** — gobierna el portafolio completo y conecta con la estrategia. Muy común en empresas grandes.

## 3. Niveles de evolución de una PMO (modelo Gartner)

```
Nivel 1 — Tácticas / "Apaga incendios"
Nivel 2 — Project-focused / Estandarización de proyecto único
Nivel 3 — Program-focused / Gestión de programas
Nivel 4 — Portfolio-focused / Optimización del portafolio
Nivel 5 — Enterprise / Conectada con estrategia y resultados de negocio
```

Una "PMO Avanzada" típicamente está en niveles **4 o 5**: gobierno digital del portafolio, vista predictiva, integración con ERP/CRM, decisiones data-driven.

## 4. Modelos de Madurez de PMO

- **P3M3** (Portfolio, Programme & Project Management Maturity Model) — del UK Office of Government Commerce. 5 niveles, 7 perspectivas (governance, management control, benefits, risk, stakeholder, finance, resource).
- **OPM3** (Organizational Project Management Maturity Model) — PMI. Mide capacidad organizacional para entregar.
- **CMMI for Services** — útil para PMOs que ofrecen servicios internos.

## 5. Frameworks metodológicos que la PMO orquesta

| Familia | Frameworks principales | Cuándo usarlos |
|---|---|---|
| **Predictivo / Cascada** | PMI PMBOK, PRINCE2 | Proyectos con alcance fijo (construcción, infraestructura, regulatorios) |
| **Ágil** | Scrum, Kanban, XP | Producto digital, software, donde el alcance evoluciona |
| **Escalado** | SAFe, LeSS, Nexus, Spotify model | Programas con muchos equipos coordinados |
| **Híbrido** | Disciplined Agile (PMI-DA), Hybrid PMI | Empresas con cartera mixta — el caso más común en industria |

**Regla de Minsait:** rara vez es 100% predictivo o 100% ágil. Lo correcto es hybrid model documentado.

## 6. Procesos core de una PMO

1. **Project intake** (recepción de iniciativas) — desde la idea hasta la priorización
2. **Caso de negocio** — justificación económica, cuantificación de beneficios
3. **Aprobación y financiamiento** — gates de inversión, comités
4. **Planificación** — alcance, cronograma, recursos, riesgos, presupuesto
5. **Ejecución y seguimiento** — status semanal, hitos, riesgos, comunicación
6. **Gestión del cambio** — change requests, control integrado de cambios
7. **Cierre** — lessons learned, transferencia operacional, beneficios capturados

## 7. Componentes de gobierno

- **Comité Ejecutivo / Steering Committee**: aprobaciones de cambios mayores, escalamiento
- **Comité de Seguimiento**: cadencia regular (semanal/quincenal), status del programa
- **Comité Técnico**: decisiones técnicas, integración entre frentes
- **Comité de Cambio (CCB)**: aprobación formal de change requests

## 8. Roles típicos en una PMO

- **PMO Lead / Director PMO**: cabeza, reporta al sponsor ejecutivo
- **Manager PMO**: día a día, gobernanza, reporting consolidado
- **Consultor Senior PMO**: gestión de proyectos críticos, mentoring
- **Consultor PMO / Analista**: tracking, status reports, análisis
- **Especialistas funcionales**: por dominio (data, IA, change management)

## 9. Tools del ecosistema PMO

| Categoría | Herramientas líderes |
|---|---|
| **Project Management individual** | MS Project, Smartsheet, Asana, Monday |
| **Portfolio management** | Planview, Clarity (Broadcom), Sciforma, ProjectPlace |
| **Agile** | Jira, Azure DevOps, Trello, Rally |
| **Reporting / Dashboards** | Power BI, Tableau, Qlik |
| **Colaboración** | Microsoft Teams, Slack, Confluence |
| **ERP integrado (capex/opex)** | SAP PS, Oracle Project Portfolio Management |
| **IA-augmented PMO** | Copilot Studio, Microsoft 365 Copilot, Claude (vía API), agentes RAG |

## 10. PMO Avanzada / "PMO Aumentada con IA"

**Capacidades emergentes 2024-2026:**
- **Predictive risk scoring** — modelos ML que predicen probabilidad de retraso/sobrecosto basado en histórico
- **Auto-generación de status reports** — agentes RAG sobre data del proyecto
- **Análisis de minutas con LLMs** — extracción automática de decisiones, action items, riesgos
- **Capacity planning predictivo** — forecasting de utilización de PMs y especialistas
- **Conversational PMO** — chatbots que responden "¿cuál es el status del proyecto X?" en lenguaje natural
- **Lessons learned searchable** — vector DB sobre cierres pasados, RAG conversacional

## 11. Conceptos a contrastar (red flags al redactar)

Si el agente está redactando un deck y aparece una de estas frases, **debe cuestionarlas y refinar:**

| ❌ Frase ambigua o incorrecta | ✅ Reformulación correcta |
|---|---|
| "Implementaremos una PMO" | "Implementaremos una PMO de tipo {Controlling/Directive} en nivel de madurez {3/4} según P3M3" |
| "Daremos visibilidad del portafolio" | "Construiremos un dashboard ejecutivo en Power BI con KPIs SPI/CPI por proyecto, refresh diario" |
| "Reduciremos riesgos" | "Implementaremos risk register con scoring cuantitativo y revisión semanal en comité técnico" |
| "Mejoraremos la gestión" | (no decir nada genérico — describir el cambio operativo concreto) |
| "Aplicaremos IA" | "Desplegaremos un agente RAG sobre la base de status reports históricos para Q&A conversacional" |
| "Modelo ágil" | "Modelo {híbrido SAFe/Scrum} con sprints de 2 semanas y release planning trimestral" |

## 12. Diferenciadores Minsait Business Consulting en PMO

- **Framework metodológico propio PPM** — recopila buenas prácticas PMI/Scrum/Lean adaptadas
- **Aceleradores y plantillas reutilizables** — librería de templates probados en clientes industriales y FS
- **Experiencia comprobada en programas SAP S/4HANA** — caso Minsur/Marcobre · Codelco · Petroperú
- **Alianza tecnológica Microsoft Power Platform + Copilot Studio** — implementaciones de IA en PMO con stack Microsoft
- **Centro de excelencia en gestión de proyectos** — escala internacional Indra
- **Capacidad de Change Management integrada** — práctica conjunta MBC

## 13. Métricas estándar que el agente debe conocer

(ver `metrics.md` para detalle de cálculo y benchmarks)

- **SPI** (Schedule Performance Index)
- **CPI** (Cost Performance Index)
- **EVM** (Earned Value Management)
- **On-time delivery rate**
- **Budget variance**
- **Resource utilization**
- **Scope creep rate**
- **Risk realization rate**
- **Stakeholder satisfaction (NPS interno del PMO)**
