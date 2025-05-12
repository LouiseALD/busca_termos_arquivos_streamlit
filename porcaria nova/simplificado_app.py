import streamlit as st
import os
import boto3
import logging
import traceback
import re
from typing import Dict, List, Any, Optional, Tuple

# Importando nossas novas classes
from mapeamento_loader import MapeamentoLoader
from sql_converter import SQLConverter

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuração de caminhos
MAPEAMENTOS_PATH = "mapeamentos-de-para"

class AssistenteConversorSQL:
    """
    Classe principal do aplicativo Streamlit para conversão de SQL.
    """
    
    def __init__(self):
        """Inicializa o Assistente de Conversão SQL."""
        self.inicializar_estado()
        self.inicializar_componentes()
        
    def inicializar_estado(self):
        """Inicializa o estado da sessão Streamlit."""
        # Estado da interface
        if "mensagens" not in st.session_state:
            st.session_state["mensagens"] = []
        if "aguardando_selecao" not in st.session_state:
            st.session_state["aguardando_selecao"] = False
        if "resultado_query" not in st.session_state:
            st.session_state["resultado_query"] = None
        if "tabelas_utilizadas" not in st.session_state:
            st.session_state["tabelas_utilizadas"] = []
        if "tipo_conversao" not in st.session_state:
            st.session_state["tipo_conversao"] = "OC3_PARA_DATAMESH"  # Valor padrão
        
        # Carregadores e conversores
        if "mapeamento_loader" not in st.session_state:
            st.session_state["mapeamento_loader"] = MapeamentoLoader(MAPEAMENTOS_PATH)
        
        # Tentar inicializar cliente Bedrock (se credenciais estiverem disponíveis)
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
    
    def inicializar_componentes(self):
        """Inicializa os componentes da interface."""
        # Configuração da página
        st.set_page_config(
            page_title="Assistente SQL Converter", 
            layout="wide",
            menu_items={
                'Get Help': 'https://github.com/seu-usuario/assistente-sql-converter',
                'Report a bug': "https://github.com/seu-usuario/assistente-sql-converter/issues",
                'About': "### Assistente de Conversão SQL\nConverte queries entre sistemas diferentes - OC3, DataMesh e SAC."
            }
        )
        
        # Importar CSS
        try:
            with open("styles.css", "r", encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        except Exception as e:
            logger.error(f"Erro ao carregar CSS: {str(e)}")
    
    def carregar_mapeamentos(self, tipo_conversao: str) -> List[Dict[str, Any]]:
        """
        Carrega os mapeamentos para o tipo de conversão selecionado.
        
        Args:
            tipo_conversao: Tipo de conversão ('OC3_PARA_DATAMESH' ou 'SAC_PARA_OC3')
            
        Returns:
            Lista de mapeamentos carregados
        """
        loader = st.session_state["mapeamento_loader"]
        return loader.carregar_mapeamentos(tipo_conversao)
    
    def adicionar_mensagem(self, role: str, texto: str, is_result: bool = False):
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
    
    def reiniciar_chat(self):
        """Reinicia o chat, limpando o histórico e o estado."""
        # Preservar tipo de conversão
        tipo_conversao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")
        
        # Limpar mensagens e resultados
        st.session_state["mensagens"] = []
        st.session_state["aguardando_selecao"] = False
        st.session_state["resultado_query"] = None
        st.session_state["tabelas_utilizadas"] = []
        
        # Restaurar tipo de conversão
        st.session_state["tipo_conversao"] = tipo_conversao
        
        # Recarregar a página
        st.rerun()
    
    def exibir_historico_chat(self):
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
    
    def exibir_resultado(self):
        """Exibe o resultado da conversão da query."""
        # Verificar se há um resultado para exibir
        result = st.session_state.get("resultado_query")
        if not result:
            return
        
        # Definir o texto a ser exibido
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
                self.reiniciar_chat()
    
    def extrair_query_sql(self, texto: str) -> Tuple[str, bool]:
        """
        Extrai uma query SQL de um texto, se existir.
        
        Args:
            texto: Texto a ser analisado
            
        Returns:
            Tuple (query extraída, flag indicando se contém SQL)
        """
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
            matches = re.finditer(padrao, texto, re.IGNORECASE | re.DOTALL)
            for match in matches:
                start_idx = match.start()
                
                # A posição onde a query começa
                query_text = texto[start_idx:]
                
                # Limpar espaços extras e quebras de linha
                query_text = re.sub(r'\s+', ' ', query_text).strip()
                
                return query_text, True
        
        # Se não encontrou padrões SQL, retorna o texto original
        return texto, False
    
    def validar_query_simplificada(self, query: str) -> Dict[str, str]:
        """
        Valida uma query SQL de forma simplificada.
        
        Args:
            query: Query SQL a ser validada
            
        Returns:
            Dicionário com status e mensagem
        """
        # Verificações básicas
        if not query.strip():
            return {"status": "Erro", "mensagem": "A query está vazia."}
        
        # Verificar se tem SELECT e FROM
        if "SELECT" not in query.upper():
            return {"status": "Erro", "mensagem": "Query inválida: falta a cláusula SELECT"}
        if "FROM" not in query.upper():
            return {"status": "Erro", "mensagem": "Query inválida: falta a cláusula FROM"}
        
        # Assumir que a query é válida
        return {"status": "Sucesso", "mensagem": "A query é válida"}
    
    def processar_mensagem_usuario(self, mensagem: str):
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
        self.adicionar_mensagem("user", mensagem)
        
        # Tentar extrair uma query SQL do texto
        query_texto, contem_sql = self.extrair_query_sql(mensagem)
        
        # Guardar query e mensagem original para referência
        st.session_state["ultima_query"] = query_texto
        st.session_state["mensagem_original"] = mensagem
        
        # Se contém SQL, processar como query
        if contem_sql:
            # Mostrar mensagem se o texto foi diferente da query extraída
            if query_texto.strip() != mensagem.strip():
                tipo_conversao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")
                self.adicionar_mensagem(
                    "assistant", 
                    f"Identifiquei uma query SQL em sua mensagem. Vou processar no modo {tipo_conversao}: ```sql\n{query_texto}\n```"
                )
            
            # Validar a query
            validacao_resultado = self.validar_query_simplificada(query_texto)
                    
            if validacao_resultado["status"] == "Sucesso":
                # Processar query SQL válida
                self.processar_query(query_texto)
            else:
                # Query SQL inválida
                mensagem_erro = validacao_resultado["mensagem"]
                
                # Mostrar resposta com erro de validação
                self.adicionar_mensagem(
                    "assistant", 
                    f"⚠️ {mensagem_erro}"
                )
        else:
            # Processar como conversa normal
            tipo_conversao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")
            resposta = f"Entendi! Por favor, digite uma query SQL para que eu possa converter no modo {tipo_conversao}."
            
            # Adicionar resposta ao histórico
            self.adicionar_mensagem(
                "assistant", 
                resposta
            )
        
        # Recarregar para exibir nova mensagem
        st.rerun()
    
    def processar_query(self, query: str):
        """
        Processa uma query SQL para conversão.
        
        Args:
            query: Query SQL a ser processada
        """
        try:
            tipo_conversao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")
            
            # Carregar mapeamentos
            loader = st.session_state["mapeamento_loader"]
            
            # Buscar mapeamentos relacionados à query
            mapeamentos, elementos_query = loader.buscar_por_query(tipo_conversao, query)
            
            # Adicionar mensagem informativa
            self.adicionar_mensagem(
                "assistant",
                f"Analisando sua query SQL... Encontrei {len(mapeamentos)} mapeamentos relacionados."
            )
            
            if mapeamentos:
                # Filtrar mapeamentos
                mapeamentos_filtrados = loader.filtrar_mapeamentos(tipo_conversao, mapeamentos)
                
                # Agrupar mapeamentos por tabela e campo
                mapeamentos_agrupados = loader.agrupar_mapeamentos(tipo_conversao, mapeamentos_filtrados)
                
                # Adicionar mensagem de processamento
                self.adicionar_mensagem(
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
                self.adicionar_mensagem(
                    "assistant",
                    f"Resultado da conversão ({tipo_conversao})",
                    is_result=True
                )
            else:
                # Caso não encontre mapeamentos
                self.adicionar_mensagem(
                    "assistant",
                    "Não encontrei mapeamentos correspondentes para sua query. Por favor, verifique se as tabelas estão corretas."
                )
        except Exception as e:
            logger.error(f"Erro ao processar query: {e}")
            logger.error(traceback.format_exc())
            
            # Mostrar erro ao usuário
            self.adicionar_mensagem(
                "assistant",
                f"Ocorreu um erro ao processar sua query: {str(e)}"
            )
        
        # Recarregar a página
        st.rerun()
    
    def mostrar_interface(self):
        """Exibe a interface principal do assistente."""
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
            self.exibir_historico_chat()
            
            # Exibir o resultado, se houver
            self.exibir_resultado()
            
            # Campo de entrada para mensagem do usuário
            mensagem_usuario = st.chat_input("Digite sua query SQL ou mensagem...")
            
            if mensagem_usuario:
                self.processar_mensagem_usuario(mensagem_usuario)
        
        # Aba de Busca de Campos
        with tab2:
            # Implementar a busca de campos (simplificada)
            st.write("Esta funcionalidade será implementada em uma próxima fase.")
            
            # Implementação básica da busca (placeholder)
            st.write("#### Busca de Campos")
            query_busca = st.text_input("Digite o termo a ser buscado:")
            tipo_busca = st.radio("Tipo de busca:", ["Tabela", "Campo"])
            
            if st.button("Buscar"):
                if query_busca:
                    loader = st.session_state["mapeamento_loader"]
                    tipo_conversao = st.session_state["tipo_conversao"]
                    
                    # Apenas para demonstrar a funcionalidade
                    mapeamentos = loader.carregar_mapeamentos(tipo_conversao)
                    st.write(f"Encontrados {len(mapeamentos)} mapeamentos para o tipo {tipo_conversao}")
                    
                    # Mostrar resultado da busca em uma tabela
                    if mapeamentos:
                        # Mostrar apenas os primeiros 10 resultados
                        st.write("Amostra dos mapeamentos disponíveis:")
                        st.json(mapeamentos[:5])

# Função principal para iniciar o aplicativo
def main():
    assistente = AssistenteConversorSQL()
    assistente.mostrar_interface()

if __name__ == "__main__":
    main()