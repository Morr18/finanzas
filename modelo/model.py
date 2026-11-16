from transformers import AutoModel, AutoTokenizer

model_name = "Qwen/Qwen2.5-Coder-3B"

# Descarga y carga el tokenizador y el modelo
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)

# Si quieres guardarlo explícitamente en una carpeta local específica:
tokenizer.save_pretrained("./mi_modelo_local")
model.save_pretrained("./mi_modelo_local")
