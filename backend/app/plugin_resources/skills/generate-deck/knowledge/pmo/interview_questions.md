# PMO · Preguntas Específicas del Tema (Bloque 7)

> Este bloque se ejecuta DESPUÉS del bloque 0-6 estándar de la entrevista. Solo aplica si el deck es de tema PMO. Las respuestas alimentan al A4 Contenido para profundizar correctamente.

## P7 — Bloque PMO específico

### P7.1 — Tipo de PMO objetivo
> ¿Qué tipo de PMO está buscando el cliente?

Opciones:
- Supportive (asesoramiento + templates, sin control)
- Controlling (estándares + auditoría de cumplimiento)
- Directive (PMs reportan a la PMO directamente)
- Strategic / Enterprise (gobierno del portafolio completo conectado a estrategia)
- No está definido — recomendarlo nosotros

### P7.2 — Nivel de madurez actual del cliente
> ¿En qué nivel de evolución de PMO está hoy el cliente?

Opciones:
- Nivel 1 — sin PMO formal, "apaga incendios"
- Nivel 2 — proyecto único / departamental
- Nivel 3 — programa-focused
- Nivel 4 — portafolio-focused
- Nivel 5 — enterprise / estratégico
- No sé — diagnóstico parte del proyecto

### P7.3 — Volumen del portafolio
> ¿Cuántos proyectos en paralelo gestiona la organización?

Opciones:
- < 10 proyectos
- 10-30 proyectos
- 30-100 proyectos
- 100+ proyectos
- No está medido

### P7.4 — Frameworks metodológicos en uso
> ¿Qué frameworks usa hoy el cliente? (multi-select)

Opciones:
- PMBOK / PMI
- PRINCE2
- Scrum / Kanban
- SAFe u otro escalado ágil
- Híbrido (mix de varios)
- Sin metodología formal

### P7.5 — Stack tecnológico actual
> ¿Qué herramientas usa hoy el cliente para gestión de proyectos?

Opciones:
- MS Project + Excel + PowerPoint (lo más común)
- Smartsheet o Planview
- Jira / Azure DevOps
- SAP PS o módulo PPM de SAP
- Power Platform / Power BI ya implementado
- Otro / mezcla

### P7.6 — Ambición de IA en la PMO
> ¿Qué nivel de IA quieren incorporar?

Opciones:
- Solo digitalización (dashboards en Power BI)
- Predictive analytics (forecasts de riesgo, capacity)
- IA generativa (auto-status, lessons learned searchable)
- Agentes autónomos (parcialmente automatizar decisiones)
- Sin IA — solo PMO tradicional avanzada

### P7.7 — Sponsor y nivel ejecutivo
> ¿Quién es el sponsor del lado cliente?

Opciones:
- CEO / Gerente General
- CFO / Gerente de Finanzas
- COO / Gerente de Operaciones
- CIO / CTO / Gerente de TI
- Director de Estrategia / Transformación
- Director de PMO existente (caso de evolución)

### P7.8 — Casos sectoriales esperados
> ¿Quieren ver casos de éxito específicos en su sector?

Opciones:
- Minería (Minsur, Marcobre, Codelco)
- Energía (Endesa, EGP, AES Andes, Petroperú)
- Banca (no aplica si cliente es industria)
- Multi-sectorial / experiencia global
- No mencionar casos (deck más conceptual)

### P7.9 — Métricas objetivo prioritarias
> ¿Cuáles son los 1-3 KPIs más importantes para el cliente? (multi-select)

Opciones:
- On-time delivery rate
- Budget variance / CPI
- Resource utilization
- Time-to-decision (cascadeo de cambios)
- Stakeholder satisfaction
- ROI de proyectos cerrados
- Risk realization rate

### P7.10 — Especificidades del cliente
> ¿Hay algo del contexto del cliente que el agente debe saber para no dar genérico?

Texto libre. Ejemplos:
- Operación distribuida (sites mineros, depots)
- Compliance Caterpillar (caso Ferreyros)
- Stack legado complejo (mainframe, SAP ECC)
- Acuerdos de servicio CSA/MARC
- Programas estratégicos en curso (M&A, transformación)

---

## Output esperado

Las respuestas se inyectan al `deck_brief.json` bajo `topic_specific.pmo`:

```json
{
  "topic_specific": {
    "pmo": {
      "target_pmo_type": "directive",
      "current_maturity_level": 2,
      "portfolio_volume": "30-100",
      "current_frameworks": ["PMBOK", "Híbrido"],
      "current_stack": ["MS Project + Excel"],
      "ai_ambition": "predictive_analytics",
      "sponsor_role": "CIO_CTO",
      "case_studies_preference": ["mineria", "energia"],
      "kpis_priority": ["on_time_delivery", "time_to_decision"],
      "client_specifics": "Operaciones distribuidas en sites mineros + compliance Caterpillar..."
    }
  }
}
```

El A4 Contenido usa esto para:
- Adaptar el "tipo de PMO" propuesto al cliente
- Calibrar el roadmap a la madurez actual
- Citar los casos correctos
- Proponer KPIs alineados a sus prioridades
