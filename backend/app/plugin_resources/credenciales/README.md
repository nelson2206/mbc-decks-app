# Biblioteca de Credenciales

Las credenciales individuales (.pptx por caso de éxito) NO vienen empaquetadas en el plugin
para mantenerlo liviano. Se regeneran ejecutando:

```
python skills/generate-deck/scripts/extract_credentials.py <deck.pptx> \
    --output-dir credenciales/<topic>/ --topic <topic> --industry <industry>
```

El `_index.json` de este directorio contiene la metadata de las credenciales esperadas.
