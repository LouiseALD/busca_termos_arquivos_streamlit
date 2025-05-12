# app_refatorado.py - Versão simplificada do assistente de conversão SQL
import streamlit as st
import os
import logging
import traceback
import boto3

# Importando nossos novos componentes
from mapeamento_loader import MapeamentoLoader
from sql_converter import SQLConverter
from campo_searcher import CampoSearcher

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Caminho base para os mapeamentos
MAPEAMENTOS_PATH = "mapeamentos-de-para"

# Configuração da página Streamlit
st.set_page_config(
    page_title="Assistente de Conversão SQL", 
    layout="wide",
    menu_items={
        'Get Help': 'https://github.com/seu-usuario/assistente-sql-converter',
        'Report a bug': "https://github.com/seu-usuario/assistente-sql-converter/issues",
        'About': "### Assistente de Conversão SQL\nConverte queries entre sistemas diferentes - OC3, DataMesh e SAC."
    }
)

# Inicialização do estado da sessão
def inicializar_estado():
    """Inicializa o estado da sessão Streamlit."""
    # Estado da interface
    if "mensagens" not in st.session_state:
        st.session_state["mensagens"] = []
    if "resultado_query" not in st.session_state:
        st.session_state["resultado_query"] = None
    if "tabelas_utilizadas" not in st.session_state:
        st.session_state["tabelas_utilizadas"] = []
    if "tipo_conversao" not in st.session_state:
        st.session_state["tipo_conversao"] = "OC3_PARA_DATAMESH"  # Valor padrão
    
    # Componentes
    if "mapeamento_loader" not in st.session_state:
        st.session_state["mapeamento_loader"] = MapeamentoLoader(MAPEAMENTOS_PATH)
    if "campo_searcher" not in st.session_state:
        st.session_state["campo_searcher"] = CampoSearcher(MAPEAMENTOS_PATH)
    
    # Inicializar cliente Bedrock (se credenciais estiverem disponíveis)
    if "bedrock_client" not in st.session_state:
        try:
            bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name="us-east-1",
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                aws_session_token=os.getenv("AWS_SESSION_TOKEN")
            )
            st.session_state["bedrock_client"] = bedrock_client
            logger.info("Cliente Bedrock inicializado com sucesso")
        except Exception as e:
            logger.warning(f"Não foi possível inicializar cliente Bedrock: {e}")
            st.session_state["bedrock_client"] = None
    
    # Inicializar conversor SQL
    if "sql_converter" not in st.session_state:
        st.session_state["sql_converter"] = SQLConverter(st.session_state.get("bedrock_client"))

# Função para adicionar mensagem ao histórico
def adicionar_mensagem(role, texto, is_result=False):
    """
    Adiciona uma mensagem ao histórico do chat.
    
    Args:
        role: Papel da mensagem ('user' ou 'assistant')
        texto: Texto da mensagem
        is_result: Flag para indicar se é um resultado
    """
    if "mensagens" not in st.session_state:
        st.session_state["mensagens"] = []
    
    mensagem = {
        "role": role,
        "text": texto,
        "is_result": is_result
    }
    
    st.session_state["mensagens"].append(mensagem)

# Função para exibir o histórico do chat
def exibir_historico_chat():
    """Exibe o histórico do chat."""
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    
    for msg in st.session_state.get("mensagens", []):
        # Pular o resultado final que será mostrado separadamente
        if msg.get("is_result", False):
            continue
            
        if msg["role"] == "assistant":
            st.markdown(f"""
            <div class='msg-container' style="margin-bottom: 15px;">
                <div class='message-box bot-msg'>
                    {msg['text']}
                </div>
                <div style="width:40%;"></div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='msg-container' style="margin-bottom: 15px;">
                <div style="width:40%;"></div>
                <div class='message-box user-msg'>
                    {msg['text']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# Função para exibir o resultado da conversão
def exibir_resultado():
    """Exibe o resultado da conversão da query."""
    # Verificar se há um resultado para exibir
    result = st.session_state.get("resultado_query")
    if not result:
        return
    
    # Determinar tipo de conversão
    tipo_conversao = result.get("tipo_conversao", st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH"))
    
    # Define o texto amigável para o tipo de conversão
    if tipo_conversao == "OC3_PARA_DATAMESH":
        tipo_conversao_texto = "OC3 para DataMesh (Athena)"
    elif tipo_conversao == "SAC_PARA_OC3":
        tipo_conversao_texto = "SAC para OC3"
    else:
        tipo_conversao_texto = tipo_conversao
    
    # Título do resultado
    st.markdown(f"### Resultado da Conversão ({tipo_conversao_texto})")
    
    # Mostrar query original
    with st.expander("Query Original", expanded=True):
        st.code(result.get("original", ""), language="sql")
    
    # Mostrar query convertida
    with st.expander("Query Convertida", expanded=True):
        st.code(result.get("convertida", ""), language="sql")
        
        # Adicionar botão para copiar o resultado
        if st.button("📋 Copiar Query Convertida"):
            # Usar JavaScript para copiar para a área de transferência
            st.write("Query copiada para a área de transferência!")
            st.markdown(f"""
            <script>
                navigator.clipboard.writeText(`{result.get("convertida", "")}`)
                    .then(() => console.log('Texto copiado!'))
                    .catch(err => console.error('Erro ao copiar texto:', err));
            </script>
            """, unsafe_allow_html=True)
    
    # Adicionar botão para novo chat
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Iniciar Nova Conversão", use_container_width=True, type="primary"):
            reiniciar_chat()

# Função para reiniciar o chat
def reiniciar_chat():
    """Reinicia o chat, limpando o histórico e o estado."""
    # Preservar tipo de conversão
    tipo_conversao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")
    
    # Preservar componentes importantes
    mapeamento_loader = st.session_state.get("mapeamento_loader")
    campo_searcher = st.session_state.get("campo_searcher")
    bedrock_client = st.session_state.get("bedrock_client")
    sql_converter = st.session_state.get("sql_converter")
    
    # Limpar mensagens e resultados
    st.session_state["mensagens"] = []
    st.session_state["resultado_query"] = None
    st.session_state["tabelas_utilizadas"] = []
    
    # Restaurar componentes e configurações
    st.session_state["tipo_conversao"] = tipo_conversao
    st.session_state["mapeamento_loader"] = mapeamento_loader
    st.session_state["campo_searcher"] = campo_searcher
    st.session_state["bedrock_client"] = bedrock_client
    st.session_state["sql_converter"] = sql_converter
    
    # Recarregar a página
    st.rerun()

# Função para processar a query SQL
def processar_query(query):
    """
    Processa uma query SQL para conversão.
    
    Args:
        query: Query SQL a ser processada
    """
    try:
        tipo_conversao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")
        
        # Carregar mapeamentos
        loader = st.session_state["mapeamento_loader"]
        
        # Verificar se os diretórios existem
        caminho = loader.caminhos.get(tipo_conversao)
        if not os.path.exists(caminho):
            adicionar_mensagem(
                "assistant",
                f"❌ **Erro**: Diretório de mapeamentos não encontrado: `{caminho}`\n\n"
                f"Por favor, certifique-se de que o diretório existe e contém os arquivos JSON de mapeamento."
            )
            st.rerun()
            return
        
        # Buscar mapeamentos relacionados à query
        mapeamentos, elementos_query = loader.buscar_por_query(tipo_conversao, query)
        
        if not mapeamentos:
            # Verificar se existem arquivos JSON no caminho
            arquivos_json = [f for f in os.listdir(caminho) if f.endswith('.json')]
            if not arquivos_json:
                adicionar_mensagem(
                    "assistant",
                    f"❌ **Erro**: Nenhum arquivo JSON encontrado no diretório: `{caminho}`\n\n"
                    f"Por favor, adicione arquivos JSON de mapeamento ao diretório."
                )
                st.rerun()
                return
            
            # Se existem arquivos mas não encontrou mapeamentos, provavelmente a query não tem correspondências
            adicionar_mensagem(
                "assistant",
                f"ℹ️ Não encontrei mapeamentos correspondentes para sua query. Por favor, verifique se as tabelas estão corretas."
            )
            st.rerun()
            return
            
        # Adicionar mensagem informativa
        adicionar_mensagem(
            "assistant",
            f"Analisando sua query SQL... Encontrei {len(mapeamentos)} mapeamentos relacionados."
        )
        
        # Filtrar mapeamentos
        mapeamentos_filtrados = loader.filtrar_mapeamentos(tipo_conversao, mapeamentos)
        
        # Agrupar mapeamentos por tabela e campo
        mapeamentos_agrupados = loader.agrupar_mapeamentos(tipo_conversao, mapeamentos_filtrados)
        
        # Adicionar mensagem de processamento
        adicionar_mensagem(
            "assistant",
            "Processando a conversão com os mapeamentos encontrados..."
        )
        
        # Converter a query
        conversor = st.session_state["sql_converter"]
        query_convertida = conversor.converter_query(
            query, 
            mapeamentos_agrupados, 
            tipo_conversao, 
            st.session_state.get("mensagem_original")
        )
        
        # Armazenar o resultado
        st.session_state["resultado_query"] = {
            "original": query,
            "convertida": query_convertida,
            "tipo_conversao": tipo_conversao
        }
        
        # Armazenar mapeamentos utilizados
        st.session_state["tabelas_utilizadas"] = mapeamentos_filtrados
        
        # Adicionar mensagem marcadora para o resultado
        adicionar_mensagem(
            "assistant",
            f"Resultado da conversão ({tipo_conversao})",
            is_result=True
        )
        
        # Recarregar para mostrar o resultado
        st.rerun()
        
    except Exception as e:
        logger.error(f"Erro ao processar query: {e}")
        logger.error(traceback.format_exc())
        
        # Mostrar erro ao usuário
        adicionar_mensagem(
            "assistant",
            f"❌ **Erro ao processar sua query**: {str(e)}\n\n"
            f"Por favor, verifique se a query está correta e os arquivos de mapeamento existem."
        )
        
        # Recarregar a página
        st.rerun()

# Função para extrair e validar uma query SQL
def extrair_e_validar_query(mensagem):
    """
    Extrai e valida uma query SQL de uma mensagem.
    
    Args:
        mensagem: Mensagem de texto
        
    Returns:
        Tupla (query, contém_sql, mensagem_validação)
    """
    import re
    
    # Padrões comuns de início de query SQL
    inicios_sql = [
        (r'SELECT\s+.+?\s+FROM\s+.+?', 'SELECT'),
        (r'UPDATE\s+.+?\s+SET\s+.+?', 'UPDATE'),
        (r'INSERT\s+INTO\s+.+?', 'INSERT'),
        (r'DELETE\s+FROM\s+.+?', 'DELETE'),
        (r'CREATE\s+TABLE\s+.+?', 'CREATE')
    ]
    
    # Procurar por padrões SQL no texto
    for padrao, keyword in inicios_sql:
        # Encontrar todas as ocorrências do padrão
        matches = re.finditer(padrao, mensagem, re.IGNORECASE | re.DOTALL)
        for match in matches:
            start_idx = match.start()
            
            # A posição onde a query começa
            query_text = mensagem[start_idx:]
            
            # Limpar espaços extras e quebras de linha
            query_text = re.sub(r'\s+', ' ', query_text).strip()
            
            # Validar a query
            if "SELECT" not in query_text.upper():
                return query_text, True, {"status": "Erro", "mensagem": "Query inválida: falta a cláusula SELECT"}
            if "FROM" not in query_text.upper():
                return query_text, True, {"status": "Erro", "mensagem": "Query inválida: falta a cláusula FROM"}
            
            # Query válida
            return query_text, True, {"status": "Sucesso", "mensagem": "A query é válida"}
    
    # Se não encontrou padrões SQL, retorna o texto original
    return mensagem, False, {"status": "Não é SQL", "mensagem": "A mensagem não contém uma query SQL"}

# Função para processar a mensagem do usuário
def processar_mensagem_usuario(mensagem):
    """
    Processa a mensagem do usuário.
    
    Args:
        mensagem: Mensagem do usuário
    """
    # Limpar resultado anterior se existir
    if st.session_state.get("resultado_query"):
        st.session_state["resultado_query"] = None
        st.session_state["tabelas_utilizadas"] = []
    
    # Adicionar mensagem ao histórico
    adicionar_mensagem("user", mensagem)
    
    # Extrair e validar query SQL
    query_texto, contem_sql, validacao = extrair_e_validar_query(mensagem)
    
    # Guardar query e mensagem original para referência
    st.session_state["ultima_query"] = query_texto
    st.session_state["mensagem_original"] = mensagem
    
    # Se contém SQL, processar como query
    if contem_sql:
        # Mostrar mensagem se o texto foi diferente da query extraída
        if query_texto.strip() != mensagem.strip():
            tipo_conversao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")
            adicionar_mensagem(
                "assistant", 
                f"Identifiquei uma query SQL em sua mensagem. Vou processar no modo {tipo_conversao}: ```sql\n{query_texto}\n```"
            )
        
        # Verificar resultado da validação
        if validacao["status"] == "Sucesso":
            # Processar query SQL válida
            processar_query(query_texto)
        else:
            # Query SQL inválida
            adicionar_mensagem(
                "assistant", 
                f"⚠️ {validacao['mensagem']}"
            )
    else:
        # Processar como conversa normal
        tipo_conversao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")
        resposta = f"Entendi! Por favor, digite uma query SQL para que eu possa converter no modo {tipo_conversao}."
        
        # Adicionar resposta ao histórico
        adicionar_mensagem(
            "assistant", 
            resposta
        )
    
    # Recarregar para exibir nova mensagem
    st.rerun()

# Interface principal da aplicação
def mostrar_interface():
    """Exibe a interface principal do assistente."""
    # Importar CSS
    try:
        with open("styles.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Erro ao carregar CSS: {str(e)}")
    
    # Título
    st.markdown("<h2 class='title'>Assistente De Conversão SQL</h2>", unsafe_allow_html=True)
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
        
        def atualizar_tipo_conversao():
            st.session_state["tipo_conversao"] = st.session_state["seletor_conversao"]
        
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
        
        # Exibir o histórico do chat
        exibir_historico_chat()
        
        # Exibir o resultado, se houver
        exibir_resultado()
        
        # Campo de entrada para mensagem do usuário
        mensagem_usuario = st.chat_input("Digite sua query SQL ou mensagem...")
        
        if mensagem_usuario:
            processar_mensagem_usuario(mensagem_usuario)
    
    # Aba de Busca de Campos
    with tab2:
        # Usar o componente de busca de campos
        campo_searcher = st.session_state.get("campo_searcher")
        if campo_searcher:
            campo_searcher.mostrar_interface_busca()
        else:
            st.error("Componente de busca de campos não inicializado corretamente")

# Função principal para iniciar o aplicativo
def main():
    # Inicializar estado da sessão
    inicializar_estado()
    
    # Mostrar interface
    mostrar_interface()

if __name__ == "__main__":
    main()