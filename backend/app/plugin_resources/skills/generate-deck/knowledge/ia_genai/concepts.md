# IA / GenAI / Agentes · Conceptos Clave

## 1. Pirámide de capacidades IA
1. **Reglas/heurísticas** — sin ML
2. **ML clásico** — regresión, clasificación, clustering
3. **Deep Learning** — visión, NLP, secuencias
4. **LLMs / Foundation Models** — GPT-4, Claude, Gemini, Llama
5. **Agentes autónomos** — múltiples LLMs + tools + memoria

## 2. Antes de hacer GenAI: Data Foundation
**Regla MBC:** Sin Data Foundation no hay GenAI productiva. Verificar:
- Datos con calidad medida (>85%)
- Catálogo activo + glosario de negocio
- Acceso seguro (ABAC, RBAC)
- Pipelines reproducibles

## 3. Patrones de GenAI productiva
| Patrón | Cuándo usar |
|---|---|
| **RAG (Retrieval Augmented Generation)** | Q&A sobre docs propios, soporte, búsqueda corporativa |
| **Agentes con tools** | Automatización de tareas multi-paso |
| **Fine-tuning** | Tono específico, dominio muy técnico |
| **Embeddings + búsqueda semántica** | Buscador interno, lessons learned |
| **Chain of Thought / ReAct** | Razonamiento sobre data estructurada |

## 4. Stack GenAI 2025-2026
- **Providers:** Anthropic Claude, OpenAI GPT-4o, Google Gemini, AWS Bedrock, Azure OpenAI
- **Vector DBs:** Pinecone, Weaviate, pgvector, Qdrant
- **Frameworks:** LangChain, LlamaIndex, Semantic Kernel, Pydantic AI
- **Observability:** LangSmith, Langfuse, Helicone, Phoenix
- **Plataformas low-code:** Microsoft Copilot Studio, Anthropic Skills, Amazon Q

## 5. MLOps + LLMOps
- Experiment tracking (MLflow, Weights & Biases)
- Model registry y versionamiento
- Eval suites (golden sets, judge LLMs, A/B testing)
- Guardrails (validación, content filtering)
- Costos y latencia monitoreados (token spend per use case)

## 6. Métricas clave
- **Accuracy / F1** (modelos clásicos)
- **Eval scores** vs golden set (LLM apps)
- **Hallucination rate**
- **Latencia P95** (UX de agentes)
- **Cost per query / per user**
- **Adoption rate** (% usuarios activos del producto IA)

## 7. Riesgos a abordar siempre
- **Privacidad y PII** — datos del cliente nunca al training del modelo
- **Compliance** (GDPR, LPDP Perú 29733)
- **Hallucinations** — toda salida debe poder verificarse
- **Bias** — auditar fairness antes de productivizar
- **Prompt injection** — validar inputs maliciosos

## 8. Frases a evitar y reformular
| ❌ | ✅ |
|---|---|
| "Implementaremos IA" | "Desplegaremos un agente RAG sobre documentación interna usando Claude Sonnet + pgvector" |
| "Solución cognitiva" | "Asistente conversacional con accuracy >90% en eval suite de 200 preguntas" |
| "Modelo personalizado" | "Fine-tuning de Llama 3.1 70B sobre 50K conversaciones del cliente" |
| "IA generativa" | el caso de uso específico (Q&A · resumen · generación de reportes · etc.) |

## 9. Diferenciadores Minsait
- Centro de Excelencia Data & AI
- Alianzas: Anthropic, Microsoft Copilot, AWS Bedrock, Azure OpenAI
- Casos productivos: BBVA (IA), Alpayana (assessment IA)
- Framework propio de evaluación de modelos
