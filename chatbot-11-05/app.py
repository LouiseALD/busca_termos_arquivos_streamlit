# app.py - Versão simplificada
import streamlit as st
from ui import show_ui
from chatbot.main import handle_chat
import traceback
import os
import json
from logger_config import setup_logger
from config import PATH_CONFIG  

# Configura o logger
logger = setup_logger()
logger.info("Aplicação Streamlit iniciada com sucesso!")

# Configuração da Página
st.set_page_config(
    page_title="Assistente SQL Converter", 
    layout="wide",
    menu_items={
        'Get Help': 'https://github.com/seu-usuario/assistente-sql-converter',
        'Report a bug': "https://github.com/seu-usuario/assistente-sql-converter/issues",
        'About': "### Assistente de Conversão SQL\nConverte queries entre sistemas diferentes - OC3, DataMesh e SAC."
    }
)

def garantir_diretorios_mapeamentos():
    """Cria os diretórios de mapeamentos se não existirem."""
    diretorios = [
        PATH_CONFIG["MAPEAMENTOS_BASE"],
        PATH_CONFIG["MAPEAMENTOS_OC3_DATAMESH"],
        PATH_CONFIG["MAPEAMENTOS_SAC_OC3"]
    ]
    
    for diretorio in diretorios:
        try:
            os.makedirs(diretorio, exist_ok=True)
            logger.info(f"Diretório verificado: {diretorio}")
        except Exception as e:
            logger.error(f"Erro ao criar diretório {diretorio}: {e}")

def corrigir_mapping_utils():
    """Injeta a implementação corrigida na classe MappingManager."""
    try:
        from chatbot.mapping_utils import MappingManager
        
        # Substituir o método carregar_mapeamentos
        def carregar_mapeamentos_corrigido(self, pasta_json=None):
            """Versão simplificada do carregamento de mapeamentos."""
            if pasta_json is None:
                # Definir caminhos diretos baseados no tipo de conversão
                if self.tipo_conversao == "OC3_PARA_DATAMESH":
                    pasta_json = "/app/src/mapeamentos-de-para/mapeamentos-oc3-datamesh"
                else:  # SAC_PARA_OC3
                    pasta_json = "/app/src/mapeamentos-de-para/mapeamentos-sac-oc3"
            
            logger.info(f"Carregando mapeamentos de: {pasta_json}")
            mapeamentos = []

            try:
                # Criar o diretório se não existir
                os.makedirs(pasta_json, exist_ok=True)
                
                # Processar arquivos JSON no diretório
                for arquivo in os.listdir(pasta_json):
                    if arquivo.endswith(".json"):
                        caminho_json = os.path.join(pasta_json, arquivo)
                        try:
                            with open(caminho_json, "r", encoding="utf-8") as f:
                                dados = json.load(f)
                                if isinstance(dados, list):
                                    for item in dados:
                                        if isinstance(item, dict):
                                            mapeamentos.append(item)
                                elif isinstance(dados, dict) and "tabelas" in dados:
                                    for item in dados.get("tabelas", []):
                                        if isinstance(item, dict):
                                            mapeamentos.append(item)
                        except Exception as e:
                            logger.error(f"Erro ao processar o arquivo {caminho_json}: {e}")
            except Exception as e:
                logger.error(f"Erro ao acessar diretório {pasta_json}: {e}")

            self.mapeamentos = mapeamentos
            logger.info(f"Total de mapeamentos carregados: {len(mapeamentos)}")
            return mapeamentos
        
        # Adicionar método para descobrir caminho de mapeamentos
        def descobrir_caminho_mapeamentos(self):
            """Retorna o caminho correto dos mapeamentos com base no tipo de conversão."""
            if self.tipo_conversao == "OC3_PARA_DATAMESH":
                return "/app/src/mapeamentos-de-para/mapeamentos-oc3-datamesh"
            else:  # SAC_PARA_OC3
                return "/app/src/mapeamentos-de-para/mapeamentos-sac-oc3"
        
        # Substituir os métodos na classe
        MappingManager.carregar_mapeamentos = carregar_mapeamentos_corrigido
        MappingManager.descobrir_caminho_mapeamentos = descobrir_caminho_mapeamentos
        logger.info("Métodos da classe MappingManager substituídos com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao corrigir MappingManager: {e}")
        logger.error(traceback.format_exc())
        return False

try:
    # Garantir que os diretórios de mapeamentos existam
    garantir_diretorios_mapeamentos()
    
    # Corrigir a classe MappingManager para buscar arquivos JSON no local correto
    corrigir_mapping_utils()
    
    # Exibir UI (Interface)
    logger.info("Carregando interface da aplicação...")
    show_ui()
    logger.info("Interface carregada com sucesso.")

    # Rodar Chatbot
    logger.info("Iniciando execução do chatbot...")
    handle_chat()
    logger.info("Chatbot executado com sucesso.")

except Exception as e:
    logger.error(f"Erro na aplicação: {str(e)}")
    logger.error(traceback.format_exc())

    st.error(f"Erro na aplicação: {str(e)}")
    with st.expander("Detalhes do erro"):
        st.code(traceback.format_exc(), language="python")