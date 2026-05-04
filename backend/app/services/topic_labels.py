"""Mapeo de IDs internos de tema a labels legibles para mostrar en frontend."""

TOPIC_LABELS = {
    "pmo":                     "PMO · Project Management",
    "data_analytics":          "Data & Analytics",
    "ia_genai":                "Generative AI / Agentes",
    "transformacion_digital":  "Transformación Digital",
    "modelo_operativo":        "Modelo Operativo",
    "capabilities":            "Capabilities · Capacidades MBC",
    "ciberseguridad":          "Ciberseguridad",
    "esg":                     "ESG · Sostenibilidad",
    "eficiencia_operacional":  "Eficiencia Operacional",
}


def label_for(topic_id: str) -> str:
    return TOPIC_LABELS.get(topic_id, topic_id.replace("_", " ").title())
