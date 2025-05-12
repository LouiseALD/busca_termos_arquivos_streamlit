# query_processing.py - Versão refatorada
# no início do arquivo
import streamlit as st
import traceback
import json
import boto3
import os

# Importações relativas dentro do pacote chatbot
from .sql_utils import validar_query_simplificada, extrair_query_sql
from .state_manager import adicionar_mensagem, adicionar_mensagens_multiplas
from .mapping_utils import MappingManager
from .query_converter import criar_conversor
from logger_config import setup_logger  # Este é externo ao pacote chatbot

logger = setup_logger()

def processar_mensagem_multilinhas(mensagem):
    """
    Processa mensagens com múltiplas linhas, lidando com qualquer número de tabelas.
    
    Args:
        mensagem: Mensagem multilinhas a ser processada
    
    Returns:
        Lista de mensagens a serem adicionadas sequencialmente
    """
    import re
    
    # Verificar se a mensagem contém padrões específicos de múltiplas tabelas
    linhas = mensagem.split('\n')
    mensagens_processadas = []
    
    # Padrões para identificar diferentes partes da mensagem
    padrao_inicio = r"Analisando sua query SQL.*"
    padrao_tabela = r"Foi encontrado para a tabela.*"
    padrao_final = r"Por favor, selecione.*"
    
    for linha in linhas:
        # Limpar espaços extras
        linha = linha.strip()
        
        # Pular linhas vazias
        if not linha:
            continue
        
        # Verificar padrões de mensagem
        if (re.match(padrao_inicio, linha, re.IGNORECASE) or 
            re.match(padrao_tabela, linha, re.IGNORECASE) or 
            re.match(padrao_final, linha, re.IGNORECASE)):
            mensagens_processadas.append(linha)
    
    return mensagens_processadas

def processar_query_valida(query):
    """
    Processa uma query SQL válida e determina as possibilidades de mapeamento.
    
    Args:
        query: Query SQL a ser processada
    """
    # Obter o tipo de conversão e o gerenciador de mapeamentos
    tipo_conversao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")
    mapping_manager = st.session_state.get("mapping_manager")

    if not mapping_manager or not mapping_manager.mapeamentos:
            logger.error("Nenhum mapeamento foi carregado. Impossível processar a query.")
            # Mensagem de erro para o usuário
            adicionar_mensagem(
                "assistant", 
                "⚠️ **Erro**: Não foi possível encontrar arquivos de mapeamento para o tipo de conversão " +
                f"'{tipo_conversao}'. Por favor, verifique se os arquivos JSON de mapeamento existem em " +
                "'/app/src/mapeamentos-de-para/mapeamentos-oc3-datamesh' ou '/app/src/mapeamentos-de-para/mapeamentos-sac-oc3'."
            )
            return
        
    # Buscar mapeamentos para a query
    resultados = mapping_manager.buscar_por_termos(query)
    resultados_filtrados = mapping_manager.filtrar_mapeamentos(resultados)
    
    # Armazenar resultados filtrados para uso posterior
    st.session_state["resultados_filtrados"] = resultados_filtrados
    
    if resultados_filtrados:
        # Verificar se há múltiplas possibilidades de mapeamento
        requer_selecao, info_mapeamentos, tabelas_multiplos_destinos = mapping_manager.verificar_multiplas_possibilidades(resultados_filtrados)
        
        # Armazenar informações de mapeamento para uso na interface
        st.session_state["info_mapeamentos"] = info_mapeamentos
        st.session_state["tabelas_multiplos_destinos"] = tabelas_multiplos_destinos
        
        # Sempre mostrar opções de seleção quando houver qualquer mapeamento
        st.session_state["aguardando_selecao"] = True
        
        # Mensagem inicial
        adicionar_mensagem("assistant", "**Analisando sua query SQL... Encontrei possibilidades de mapeamento.**")
        
        # Criar mensagens separadas para cada tabela
        todas_tabelas = list(info_mapeamentos.keys())
        
        for tabela in todas_tabelas:
            # Mensagem para cada tabela
            mensagem_tabela = f"Foi encontrado para a tabela (nome da tabela oc3) <{tabela}>:\n"
            
            # Se tem múltiplos destinos
            if tabela in tabelas_multiplos_destinos:
                destinos = tabelas_multiplos_destinos[tabela]
                for numero, nome_destino in destinos:
                    mensagem_tabela += f"{numero}- {nome_destino}\n"
            else:
                # Tabela com apenas uma opção
                destino = next(iter(info_mapeamentos[tabela]["destinos_info"].values()))["nome"]
                mensagem_tabela += f"1- {destino}\n"
            
            # Adicionar mensagem de cada tabela separadamente
            adicionar_mensagem("assistant", mensagem_tabela.rstrip())
        
        # Mensagem final de solicitação de seleção
        adicionar_mensagem("assistant", "Por favor, selecione os mapeamentos apropriados.")
    else:
        # Caso não encontre mapeamentos
        adicionar_mensagem(
            "assistant", 
            "Não encontrei mapeamentos correspondentes para sua query. Por favor, verifique se as tabelas estão corretas."
        )
    
    # Recarregar para exibir opções ou mensagem
    st.rerun()

def processar_mensagem_usuario(mensagem):
    """
    Processa a mensagem do usuário e determina a ação apropriada.
    
    Args:
        mensagem: Mensagem do usuário
    """
    # Limpar resultado anterior se existir
    if st.session_state.get("resultado_query"):
        st.session_state["resultado_query"] = None
        st.session_state["tabelas_utilizadas"] = []
    
    # Adiciona a mensagem original do usuário ao histórico
    adicionar_mensagem("user", mensagem)
    
    # Verificar se a mensagem parece ser uma mensagem multilinhas com múltiplas tabelas
    if ("\n" in mensagem and 
        ("Analisando sua query SQL" in mensagem or 
         "Foi encontrado para a tabela" in mensagem or 
         "Por favor" in mensagem)):
        
        # Processar mensagem multilinhas
        mensagens_processadas = processar_mensagem_multilinhas(mensagem)
        
        # Adicionar mensagens sequencialmente
        adicionar_mensagens_multiplas(mensagens_processadas)
        
        # Acionar rerun para mostrar as mensagens
        st.rerun()
        return

    # Tentar extrair uma query SQL do texto
    query_texto, contém_sql = extrair_query_sql(mensagem)
    
    # Guardar a query para referência (seja a original ou a extraída)
    st.session_state["ultima_query"] = query_texto
    
    # Armazenar o texto original completo também
    st.session_state["mensagem_original"] = mensagem
    
    # Se contém SQL, processar como query
    if contém_sql:
        # Mostrar mensagem se o texto foi diferente da query extraída
        if query_texto.strip() != mensagem.strip():
            tipo_conversao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")
            adicionar_mensagem(
                "assistant", 
                f"Identifiquei uma query SQL em sua mensagem. Vou processar no modo {tipo_conversao}: ```sql\n{query_texto}\n```"
            )
        
        # Validar a query
        validacao_resultado = validar_query_simplificada(query_texto)
                
        if validacao_resultado["status"] == "Sucesso":
            # Processar como query SQL válida
            processar_query_valida(query_texto)
        else:
            # Query SQL inválida
            mensagem_erro = validacao_resultado["mensagem"]
            
            # Mostrar resposta com erro de validação
            adicionar_mensagem(
                "assistant", 
                f"⚠️ {mensagem_erro}"
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

def processar_conversao():
    """Processa a conversão da query usando Lambda ou simulação."""
    logger.info("INICIANDO PROCESSAMENTO DE CONVERSÃO")
    
    with st.spinner("Processando a conversão..."):
        try:
            # Obter o tipo de conversão atual
            tipo_conversao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")
            
            # Obter a query SQL e a mensagem original completa do usuário
            query_original = st.session_state.get("ultima_query", "")
            mensagem_original = st.session_state.get("mensagem_original", query_original)
            mapeamentos_selecionados = st.session_state.get("tabelas_utilizadas", [])
            
            logger.info(f"Query original: {query_original}")
            logger.info(f"Total de mapeamentos selecionados: {len(mapeamentos_selecionados)}")
            
            # Obter o gerenciador de mapeamentos atual
            mapping_manager = st.session_state.get("mapping_manager")
            
            # Agrupar os mapeamentos no formato desejado para processamento
            mapeamentos_agrupados = mapping_manager.agrupar_mapeamentos_para_lambda(mapeamentos_selecionados)
            
            # Tentar inicializar cliente Bedrock
            bedrock_runtime = None
            try:
                bedrock_runtime = boto3.client(
                    'bedrock-runtime',
                    region_name="us-east-1",
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                    aws_session_token=os.getenv("AWS_SESSION_TOKEN")
                )
                logger.info("Cliente Bedrock Runtime inicializado com sucesso")
            except Exception as e:
                logger.warning(f"Não foi possível inicializar cliente Bedrock: {e}")
                logger.info("Usando modo de simulação para converter a query")
            
            # Criar conversor apropriado
            conversor = criar_conversor(tipo_conversao, bedrock_runtime)
            
            # Converter a query
            query_convertida = conversor.converter_query(
                query_original, 
                mapeamentos_agrupados,
                contexto_adicional=mensagem_original if mensagem_original != query_original else None
            )
            
            # Armazenar o resultado no estado da sessão
            logger.info(f"Query convertida: {query_convertida}")
            st.session_state["resultado_query"] = {
                "original": query_original,
                "convertida": query_convertida,
                "mensagem_original": mensagem_original,
                "tipo_conversao": tipo_conversao
            }
            
            # Adicionar uma mensagem marcadora para o resultado
            adicionar_mensagem(
                "assistant", 
                f"Resultado da conversão ({tipo_conversao})",
                is_result=True  # Marcador especial para identificar o resultado
            )
            
            logger.info("Processamento concluído com sucesso!")
            
        except Exception as e:
            logger.error(f"ERRO no processamento: {str(e)}")
            error_traceback = traceback.format_exc()
            logger.error(error_traceback)
            
            # Adicionar mensagem de erro
            adicionar_mensagem(
                "assistant", 
                f"Ocorreu um erro ao processar sua query: {str(e)}"
            )
        
        # Limpar estado de espera
        st.session_state["esperando_resultado"] = False
        
        # Recarregar a página
        st.rerun()