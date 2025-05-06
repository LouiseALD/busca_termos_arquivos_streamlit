import streamlit as st
import json
import os

st.title("Busca com Caminho em JSON")

# Carrega o JSON local
json_path = "dados.json"  # coloque o caminho correto se estiver em subpastas
if not os.path.exists(json_path):
    st.error("Arquivo JSON não encontrado!")
else:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Campo de busca
    search_term = st.text_input("Digite o termo que deseja buscar")

    # Função de busca com caminho
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
        if resultados:
            st.write(f"Resultados encontrados para '{search_term}':")
            for res in resultados:
                st.write(f"**Caminho:** `{res['caminho']}`")
                st.write("**Valor:**")
                st.json(res["valor"])
                st.markdown("---")
        else:
            st.warning("Nenhum resultado encontrado.")
