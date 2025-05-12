import streamlit as st

# Importações relativas dentro do pacote chatbot

from .state_manager import inicializar_estado
from .query_processing import processar_mensagem_usuario, processar_conversao
from .ui_components import (
    exibir_historico_chat,
    exibir_resultado,
    mostrar_opcoes_selecao,
    mostrar_selecao_manual,
    exibir_mensagem_usuario
)

def handle_chat():
    """Função principal que coordena o fluxo do chat."""
    # Inicializar estado da sessão
    inicializar_estado()
    
    # Exibir histórico do chat
    exibir_historico_chat()
    
    # Exibir resultado se houver
    exibir_resultado()
    
    # Verificar os diferentes estados e executar o comportamento apropriado
    if st.session_state.get("aguardando_selecao", False):
        mostrar_opcoes_selecao()
        mostrar_selecao_manual()
    elif st.session_state.get("esperando_resultado", False):
        processar_conversao()
    
    # Entrada do usuário
    mensagem_usuario = st.chat_input("Digite sua query SQL ou mensagem...")
    
    if mensagem_usuario:
        # Exibir mensagem do usuário imediatamente
        exibir_mensagem_usuario(mensagem_usuario)
        
        # Processar a mensagem do usuário
        processar_mensagem_usuario(mensagem_usuario)