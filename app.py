import streamlit as st
import json
import os

st.title("Busca com Caminho em JSON")

# Mostra o caminho atual de execução
cwd = os.getcwd()
json_path = os.path.join(cwd, "dados.json")

st.markdown("### 🔍 Logs de execução")
st.write(f"📁 Caminho atual: `{cwd}`")
st.write(f"📄 Tentando carregar o JSON em: `{json_path}`")

# Verifica se o arquivo existe
if not os.path.exists(json_path):
    st.error("❌ Arquivo JSON não encontrado!")
    st.stop()
else:
    st.success("✅ Arquivo JSON encontrado com sucesso!")

# Carrega o JSON
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Campo de busca
search_term = st.text_input("Digite o termo que deseja buscar")

# Função recursiva de busca
def buscar_json(obj, termo, caminho=""):
    resultados = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            novo_caminho = f"{caminho}.{k}" if caminho else k
            if termo.lower() in str(k).lower() or termo.lower() in str(v).lower():
                resultados.append({"caminho": novo_caminho, "valor": v})
            resultados.extend(buscar_json(v, termo, novo_caminho))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            novo_caminho = f"{caminho}[{i}]"
            resultados.extend(buscar_json(item, termo, novo_caminho))
    return resultados

# Executa a busca
if search_term:
    resultados = buscar_json(data, search_term)
    st.markdown("### 🔎 Resultados")
    if resultados:
        for res in resultados:
            st.write(f"**Caminho:** `{res['caminho']}`")
            st.write("**Valor:**")
            st.json(res["valor"])
            st.markdown("---")
    else:
        st.warning("Nenhum resultado encontrado.")
