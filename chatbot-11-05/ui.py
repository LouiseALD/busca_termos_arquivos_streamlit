# ui.py
import streamlit as st
import traceback
from campo_search import show_campo_search
from chatbot.ui_components import bloquear_interacoes  # ajuste o path se necessário


def show_ui():
    # Inicializa estado do botão de "Como funciona?"
    if "mostrar_tutorial" not in st.session_state:
        st.session_state["mostrar_tutorial"] = False
    
    # Inicializa o tipo de conversão se não existir
    if "tipo_conversao" not in st.session_state:
        st.session_state["tipo_conversao"] = "OC3_PARA_DATAMESH"

    # Função para alternar exibição do tutorial
    def toggle_tutorial():
        st.session_state["mostrar_tutorial"] = not st.session_state["mostrar_tutorial"]
    
    # Função para atualizar o tipo de conversão
    def atualizar_tipo_conversao():
        st.session_state["tipo_conversao"] = st.session_state["seletor_conversao"]

    # Importar o CSS
    try:
        with open("styles.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Erro ao carregar CSS: {str(e)}")

    # Layout do título e botão ao lado
    col1, col2 = st.columns([0.8, 0.2])

    with col1:
        st.markdown("<h2 class='title'>Assistente De Conversão SQL</h2>", unsafe_allow_html=True)

    with col2:
        st.button("ℹ️ Como funciona?", on_click=toggle_tutorial)

    st.markdown("<div class='line'></div>", unsafe_allow_html=True)  # Linha separadora
    
    # Abas do aplicativo
    tab1, tab2 = st.tabs(["🔄 Conversor SQL", "🔍 Busca de Campos"])
    
    # Aba do Conversor SQL
    with tab1:
        # Seleção do tipo de conversão
        tipo_conversao_opcoes = {
            "OC3_PARA_DATAMESH": "OC3 para DataMesh (Athena)",
            "SAC_PARA_OC3": "SAC para OC3"
        }
        
        # Determinar título dinâmico baseado na seleção
        subtitulo = f"Assistente De {tipo_conversao_opcoes[st.session_state['tipo_conversao']]}"
        st.markdown(f"<h3>{subtitulo}</h3>", unsafe_allow_html=True)
        
        # Criar duas colunas para o layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.selectbox(
                "Selecione o tipo de conversão:",
                options=list(tipo_conversao_opcoes.keys()),
                format_func=lambda x: tipo_conversao_opcoes[x],
                key="seletor_conversao",
                on_change=atualizar_tipo_conversao,
                index=list(tipo_conversao_opcoes.keys()).index(st.session_state["tipo_conversao"])
            )
        
        with col2:
            # Exibir informações específicas sobre o tipo de conversão selecionado
            if st.session_state["tipo_conversao"] == "OC3_PARA_DATAMESH":
                st.info("Converte queries do sistema OC3 para o padrão DataMesh/Athena")
            elif st.session_state["tipo_conversao"] == "SAC_PARA_OC3":
                st.info("Converte queries do sistema SAC para o padrão OC3")

        # Mostrar tutorial apenas se o botão foi ativado
        if st.session_state["mostrar_tutorial"]:
            st.write(f"""
            O **{subtitulo}** ajuda na conversão de nomenclaturas e queries SQL entre diferentes sistemas.  
            ### 🔹 Como usar:
            1️⃣ **Selecione o tipo de conversão** desejado acima.  
            2️⃣ **Digite uma query SQL** na caixa de texto.  
            3️⃣ **Aguarde a resposta** do assistente.  
            4️⃣ **Se houver múltiplas possibilidades de mapeamento, selecione a desejada**.  
            5️⃣ **Veja o resultado da conversão** exibido na tela.
            
            ### 📝 Exemplos de conversão:
            
            **OC3 para DataMesh**:
            ```sql
            SELECT id_cliente, nome FROM CLIENTE WHERE status = 'ATIVO'
            ```
            
            **SAC para OC3**:
            ```sql
            SELECT tb_fluxo.dt_sistema, tb_fluxo.cd_caixa, tb_usuarios.nm_usuario 
            FROM tb_fluxo 
            JOIN tb_usuarios ON tb_fluxo.id_usuario = tb_usuarios.id_usuario
            ```
            """)
    
    # Aba de Busca de Campos
    with tab2:
        bloquear_interacoes()  # <-- aqui ele impede o acesso se estiver processando
        show_campo_search()
