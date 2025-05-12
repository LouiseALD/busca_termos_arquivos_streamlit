# state_manager.py
import os
import json
import streamlit as st
# Importar do mesmo diretório usando importação relativa
from .mapping_utils import MappingManager
from logger_config import setup_logger
from config import PATH_CONFIG

logger = setup_logger()


def inicializar_estado():
    """Inicializa o estado da sessão Streamlit."""
    # Inicializar estado da interface do chat
    if "mensagens" not in st.session_state:
        st.session_state["mensagens"] = []
    if "aguardando_selecao" not in st.session_state:
        st.session_state["aguardando_selecao"] = False
    if "mostrar_selecao" not in st.session_state:
        st.session_state["mostrar_selecao"] = False
    if "esperando_resultado" not in st.session_state:
        st.session_state["esperando_resultado"] = False
    if "ultima_query" not in st.session_state:
        st.session_state["ultima_query"] = ""
    if "resultado_query" not in st.session_state:
        st.session_state["resultado_query"] = None
    if "tabelas_utilizadas" not in st.session_state:
        st.session_state["tabelas_utilizadas"] = []
    if "tipo_processamento" not in st.session_state:
        st.session_state["tipo_processamento"] = ""
    if "resultados_filtrados" not in st.session_state:
        st.session_state["resultados_filtrados"] = []
    if "tipo_conversao" not in st.session_state:
        st.session_state["tipo_conversao"] = "OC3_PARA_DATAMESH"  # Valor padrão
    
    # Carregar mapeamentos
    _carregar_mapeamentos()

def _carregar_mapeamentos():
    """Carrega os mapeamentos para os diferentes tipos de conversão."""
    # Inicializar gerenciadores de mapeamentos
    if "mapping_manager_oc3_datamesh" not in st.session_state:
        logger.info("Inicializando gerenciador de mapeamentos OC3-DataMesh")
        
        # Caminho específico para mapeamentos OC3-DataMesh
        caminho_mapeamentos = PATH_CONFIG["MAPEAMENTOS_OC3_DATAMESH"]
        logger.info(f"Caminhos de mapeamentos configurados: {PATH_CONFIG}")

        # Verificação explícita de existência
        if not os.path.exists(caminho_mapeamentos):
            logger.info(f"Criando diretório: {caminho_mapeamentos}")
            try:
                os.makedirs(caminho_mapeamentos, exist_ok=True)
            except Exception as e:
                logger.error(f"Não foi possível criar diretório: {e}")
        
        # Criar e armazenar o gerenciador
        manager = MappingManager(tipo_conversao="OC3_PARA_DATAMESH")
        mapeamentos = manager.carregar_mapeamentos(caminho_mapeamentos)
        
        if not mapeamentos:
            logger.warning("Nenhum mapeamento OC3-DataMesh encontrado")
            mapeamentos = []  # Garantir que seja uma lista vazia em vez de None
        
        st.session_state["mapping_manager_oc3_datamesh"] = manager
        st.session_state["mapeamentos_oc3_datamesh"] = mapeamentos
    
    if "mapping_manager_sac_oc3" not in st.session_state:
        logger.info("Inicializando gerenciador de mapeamentos SAC-OC3")
        
        # Caminho específico para mapeamentos SAC-OC3
        caminho_mapeamentos = PATH_CONFIG["MAPEAMENTOS_SAC_OC3"]
        
        # Verificação explícita de existência
        if not os.path.exists(caminho_mapeamentos):
            logger.info(f"Criando diretório: {caminho_mapeamentos}")
            try:
                os.makedirs(caminho_mapeamentos, exist_ok=True)
            except Exception as e:
                logger.error(f"Não foi possível criar diretório: {e}")
        
        # Criar e armazenar o gerenciador
        manager = MappingManager(tipo_conversao="SAC_PARA_OC3")
        mapeamentos = manager.carregar_mapeamentos(caminho_mapeamentos)
        
        if not mapeamentos:
            logger.warning("Nenhum mapeamento SAC-OC3 encontrado")
            mapeamentos = []  # Garantir que seja uma lista vazia em vez de None
        
        st.session_state["mapping_manager_sac_oc3"] = manager
        st.session_state["mapeamentos_sac_oc3"] = mapeamentos
    
    # Compatibilidade com código existente - usar os mapeamentos do tipo atual
    tipo_conversao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")
    if tipo_conversao == "OC3_PARA_DATAMESH":
        st.session_state["mapeamentos"] = st.session_state["mapeamentos_oc3_datamesh"]
        st.session_state["mapping_manager"] = st.session_state["mapping_manager_oc3_datamesh"]
    else:  # SAC_PARA_OC3
        st.session_state["mapeamentos"] = st.session_state["mapeamentos_sac_oc3"]
        st.session_state["mapping_manager"] = st.session_state["mapping_manager_sac_oc3"]

def adicionar_mensagem(role, texto, is_result=False, is_html=False):
    """
    Adiciona mensagem ao histórico de chat.
    
    Args:
        role: Papel da mensagem ('user' ou 'assistant')
        texto: Texto da mensagem
        is_result: Flag para indicar se é um resultado
        is_html: Flag para indicar se o conteúdo pode conter HTML
    """
    # Limpar HTML indesejado, exceto quando explicitamente permitido
    if not is_html:
        texto = texto.replace('</div>', '').replace('<div>', '').strip()
    
    if "mensagens" not in st.session_state:
        st.session_state["mensagens"] = []
    
    # Preparar o dicionário de mensagem
    mensagem = {
        "role": role,
        "text": texto,
        "is_result": is_result
    }
    
    # Adicionar is_html apenas se for True
    if is_html:
        mensagem["is_html"] = is_html
    
    st.session_state["mensagens"].append(mensagem)

def adicionar_mensagens_multiplas(mensagens):
    """
    Adiciona múltiplas mensagens sequencialmente ao histórico do chat.
    
    Args:
        mensagens: Lista de mensagens a serem adicionadas
    """
    for mensagem in mensagens:
        adicionar_mensagem("assistant", mensagem)

def limpar_historico():
    """Limpa o histórico de mensagens."""
    st.session_state["mensagens"] = []

def limpar_resultado():
    """Limpa o resultado de uma consulta anterior."""
    st.session_state["resultado_query"] = None
    st.session_state["tabelas_utilizadas"] = []

def atualizar_tipo_conversao(tipo_conversao):
    """
    Atualiza o tipo de conversão atual.
    
    Args:
        tipo_conversao: Novo tipo de conversão
    """
    if tipo_conversao != st.session_state.get("tipo_conversao"):
        st.session_state["tipo_conversao"] = tipo_conversao
        
        # Atualizar mapeamentos ativos
        if tipo_conversao == "OC3_PARA_DATAMESH":
            st.session_state["mapeamentos"] = st.session_state["mapeamentos_oc3_datamesh"]
            st.session_state["mapping_manager"] = st.session_state["mapping_manager_oc3_datamesh"]
        else:  # SAC_PARA_OC3
            st.session_state["mapeamentos"] = st.session_state["mapeamentos_sac_oc3"]
            st.session_state["mapping_manager"] = st.session_state["mapping_manager_sac_oc3"]