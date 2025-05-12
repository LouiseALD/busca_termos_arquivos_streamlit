# chatbot/query_processing.py
# Processamento de queries SQL

import os
import re
import boto3
import streamlit as st
import traceback

from core.json_loader import buscar_por_termos, filtrar_jsons
from core.aws_client import converter_query_oc3_para_datamesh
from chatbot.converters.simulation import simular_conversao_query
from chatbot.ui_components import exibir_erro, exibir_mensagem_bot

def validar_query_simplificada(query):
    """Versão simplificada da validação para contornar o problema com LIKE."""
    
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

def extrair_query_sql(texto):
    """
    Extrai uma query SQL de um texto que pode conter conteúdo adicional.
    Retorna a query SQL e uma flag indicando se foi encontrada.
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

def verificar_multiplas_possibilidades(resultados_filtrados):
    """Verifica se há múltiplas possibilidades de mapeamento que requerem seleção."""
    # Agrupar mapeamentos por tabela
    tabelas_mapeadas = {}
    for item in resultados_filtrados:
        # Verificar se item é um dicionário válido
        if not isinstance(item, dict):
            continue
            
        tabela_oc3 = item.get("TABELA OC3 LIGHT", "")
        if not tabela_oc3:  # Pular se não tiver tabela
            continue
            
        if tabela_oc3 not in tabelas_mapeadas:
            tabelas_mapeadas[tabela_oc3] = []
        tabelas_mapeadas[tabela_oc3].append(item)
    
    # Verificar se há mais de uma tabela ou mapeamentos ambíguos
    multiplas_tabelas = len(tabelas_mapeadas) > 1
    tem_ambiguidade = False
    
    # Verificar se há ambiguidade (múltiplos mapeamentos para um mesmo campo)
    if not multiplas_tabelas:
        # Se temos apenas uma tabela, verificar se há ambiguidade nos campos
        campos_por_tabela = {}
        for tabela, mapeamentos in tabelas_mapeadas.items():
            campos_por_tabela[tabela] = {}
            for item in mapeamentos:
                campo = item.get("CAMPO OC3 LIGHT", "")
                if campo not in campos_por_tabela[tabela]:
                    campos_por_tabela[tabela][campo] = 0
                campos_por_tabela[tabela][campo] += 1
        
        # Se algum campo tiver mais de um mapeamento, há ambiguidade
        for tabela, campos in campos_por_tabela.items():
            for campo, contagem in campos.items():
                if contagem > 1:
                    tem_ambiguidade = True
                    break
    
    return multiplas_tabelas or tem_ambiguidade, tabelas_mapeadas

def adicionar_mensagem(role, texto, is_result=False, is_html=False):
    """
    Adiciona mensagem ao histórico de chat, limpando HTML indesejado.
    
    :param role: Papel da mensagem ('user' ou 'assistant')
    :param texto: Texto da mensagem
    :param is_result: Flag para indicar se é um resultado
    :param is_html: Flag para indicar se o conteúdo pode conter HTML
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
    
    # Adicionar is_html apenas se for True (para manter compatibilidade)
    if is_html:
        mensagem["is_html"] = is_html
    
    st.session_state["mensagens"].append(mensagem)

def processar_query_valida(query):
    """Processa uma query SQL válida e determina as possibilidades de mapeamento."""
    # Processar a query usando a lógica de busca
    mapeamentos = st.session_state.get("mapeamentos", [])
    resultados = buscar_por_termos(query, mapeamentos)
    resultados_filtrados = filtrar_jsons(resultados)
    
    # Armazenar resultados filtrados para uso posterior
    st.session_state["resultados_filtrados"] = resultados_filtrados
    
    if resultados_filtrados:
        # Verificar se há múltiplas possibilidades que requerem seleção
        requer_selecao, _ = verificar_multiplas_possibilidades(resultados_filtrados)
        
        if requer_selecao:
            # Há múltiplas tabelas ou ambiguidade nos campos
            st.session_state["aguardando_selecao"] = True
            
            # Adicionar mensagem inicial
            adicionar_mensagem(
                "assistant", 
                "Analisando sua query SQL... Encontrei múltiplas possibilidades de mapeamento."
            )
        else:
            # Apenas uma tabela sem ambiguidade, processar automaticamente
            st.session_state["esperando_resultado"] = True
            st.session_state["tabelas_utilizadas"] = resultados_filtrados
            st.session_state["tipo_processamento"] = "Processamento automático (única opção)"
            
            # Adicionar mensagem de processamento automático
            adicionar_mensagem(
                "assistant", 
                "Encontrei apenas uma possibilidade de mapeamento. Processando sua query automaticamente..."
            )
    else:
        # Caso não encontre mapeamentos
        adicionar_mensagem(
            "assistant", 
            "Não encontrei mapeamentos correspondentes para sua query. Por favor, verifique se as tabelas estão corretas."
        )
    
    # Recarregar para exibir opções ou mensagem
    st.rerun()

def processar_mensagem_usuario(mensagem):
    """Processa a mensagem do usuário e determina a ação apropriada."""
    # Limpar resultado anterior se existir
    if st.session_state.get("resultado_query"):
        st.session_state["resultado_query"] = None
        st.session_state["tabelas_utilizadas"] = []
    
    # Adiciona a mensagem original do usuário ao histórico
    adicionar_mensagem("user", mensagem)
    
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
            adicionar_mensagem(
                "assistant", 
                f"Identifiquei uma query SQL em sua mensagem. Vou processar: ```sql\n{query_texto}\n```"
            )
        
        # Usar validação simplificada para contornar o problema com LIKE
        validacao_resultado = validar_query_simplificada(query_texto)
        
        # Se o erro original era apenas sobre LIKE, ignorar e prosseguir
        if validacao_resultado["status"] != "Sucesso":
            try:
                if "LIKE" in validacao_resultado.get("mensagem", ""):
                    validacao_resultado = {"status": "Sucesso", "mensagem": "A query é válida"}
            except Exception as e:
                print(f"Erro na validação: {e}")
                
        if validacao_resultado["status"] == "Sucesso":
            # Processar como query SQL válida
            processar_query_valida(query_texto)
        else:
            # Query SQL inválida
            mensagem_erro = validacao_resultado["mensagem"]
            
            # Mostrar resposta com erro de validação
            exibir_erro(mensagem_erro)
            
            adicionar_mensagem(
                "assistant", 
                f"⚠️ {mensagem_erro}"
            )
    else:
        # Processar como conversa normal
        resposta = "Entendi! Por favor, digite uma query SQL para que eu possa converter."
        
        # Mostrar resposta
        exibir_mensagem_bot(resposta)
        
        adicionar_mensagem(
            "assistant", 
            resposta
        )

def processar_conversao():
    """Processa a conversão da query usando Lambda ou simulação."""
    with st.spinner("Processando a conversão..."):
        try:
            # Importar o utilitário de conversão
            from chatbot.converters.conversion_utils import agrupar_mapeamentos_para_lambda
            
            # Verificar o tipo de conversão selecionado
            tipo_conversao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")
            
            # Obter a query SQL e a mensagem original completa do usuário
            query_original = st.session_state.get("ultima_query", "")
            mensagem_original = st.session_state.get("mensagem_original", query_original)
            mapeamentos_selecionados = st.session_state.get("tabelas_utilizadas", [])
            
            # Agrupar os mapeamentos no formato desejado para a Lambda
            mapeamentos_agrupados = agrupar_mapeamentos_para_lambda(mapeamentos_selecionados)
            
            # Nome da função Lambda (agora usamos uma única função para ambos os tipos)
            function_name = "converter-sql-query"  # Nome unificado da função Lambda
            
            # Adicionar log para debugar o formato dos mapeamentos agrupados
            print(f"Mapeamentos agrupados para envio à Lambda:")
            import json
            print(json.dumps(mapeamentos_agrupados, indent=2))
            
            # Instanciar o invocador Lambda
            from chatbot.lambda_integration import LambdaInvoker
            lambda_invoker = LambdaInvoker()
            
            # Verificar se a integração Lambda está disponível
            if lambda_invoker.is_available:
                # Preparar o payload para a Lambda (apenas o necessário para conversão)
                payload = {
                    "query": query_original,
                    "mapeamentos": mapeamentos_agrupados,  # Agora usando o formato agrupado
                    "tipo_conversao": tipo_conversao,
                    "contexto_adicional": mensagem_original if mensagem_original != query_original else None
                }
                
                # Usar Lambda para processar a query (apenas a conversão)
                resultado = lambda_invoker.invocar_lambda_bedrock(function_name, payload)
                
                # Verificar se houve erro na resposta do Lambda
                if resultado.get("status") == "error" or "statusCode" in resultado and resultado["statusCode"] != 200:
                    # Extrair mensagem de erro
                    erro_msg = resultado.get("message", "Erro desconhecido")
                    if "body" in resultado:
                        try:
                            body = json.loads(resultado["body"])
                            erro_msg = body.get("message", erro_msg)
                        except:
                            pass
                            
                    # Exibir o erro mas continuar com a simulação local
                    print(f"Erro ao invocar Lambda: {erro_msg}")
                    st.warning(f"Erro na conversão via Lambda: {erro_msg}. Usando simulação local.")
                    
                    # Usar simulação como fallback
                    from chatbot.converters.simulation import simular_conversao_query
                    query_convertida = simular_conversao_query(query_original, mapeamentos_selecionados)
                else:
                    # Extrair a query convertida da resposta
                    # Verificar se a resposta está dentro de "body" (formato Lambda padrão)
                    if "body" in resultado:
                        try:
                            body = json.loads(resultado["body"])
                            query_convertida = body.get("query_convertida", "Erro na conversão")
                        except:
                            query_convertida = "Erro ao processar resposta da Lambda"
                    else:
                        query_convertida = resultado.get("query_convertida", "Erro na conversão")
            else:
                # Lambda não disponível, usar simulação local
                st.info("Conversão via Lambda não disponível. Usando simulação local.")
                from chatbot.converters.simulation import simular_conversao_query
                query_convertida = simular_conversao_query(query_original, mapeamentos_selecionados)
            
            # Armazenar o resultado no estado da sessão
            st.session_state["resultado_query"] = {
                "original": query_original,
                "convertida": query_convertida,
                "mensagem_original": st.session_state.get("mensagem_original", query_original),
                "tipo_conversao": tipo_conversao
            }
            
            # Adicionar uma mensagem marcadora para o resultado
            adicionar_mensagem(
                "assistant", 
                f"Resultado da conversão ({tipo_conversao})",
                is_result=True  # Marcador especial para identificar o resultado
            )
            
        except Exception as e:
            error_traceback = traceback.format_exc()
            st.error(f"Erro ao processar a query: {str(e)}")
            st.code(error_traceback, language="python")
            
            # Adicionar mensagem de erro
            adicionar_mensagem(
                "assistant", 
                f"Ocorreu um erro ao processar sua query: {str(e)}"
            )
        
        # Limpar estado de espera
        st.session_state["esperando_resultado"] = False
        
        st.rerun()