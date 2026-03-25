import ollama

_ASSETS_CHECKED = False

def _extract_model_names(models):
    names = []
    for model in models:
        if isinstance(model, dict):
            name = model.get("name") or model.get("model")
        else:
            name = getattr(model, "name", None) or getattr(model, "model", None)

        if name:
            names.append(name)
    return names

def assets_check():
    global _ASSETS_CHECKED
    if _ASSETS_CHECKED:
        return
    
    models = ["qwen3-embedding:0.6b"]
    try:
        listed_models = ollama.list()
        if isinstance(listed_models, dict):
            models_data = listed_models.get("models", [])
        else:
            models_data = getattr(listed_models, "models", [])

        existing = _extract_model_names(models_data)
        for m in models:
            if m not in existing and f"{m}:latest" not in existing:
                ollama.pull(m)
        _ASSETS_CHECKED = True
    except Exception as e:
        print(f"⚠️ Ollama connection failed: {e}")
        