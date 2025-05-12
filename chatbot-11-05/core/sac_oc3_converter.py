import json

import re
import boto3
from typing import Dict, List, Any, Optional, Union
from logger_config import setup_logger
from core.sac_mappings_loader import (
    buscar_tabelas_por_nome,
    buscar_campos_por_nome,
    extrair_mapeamentos_para_query,
    formatar_mapeamentos_para_bedrock
)


logger = setup_logger()

def extrair_elementos_query(query: str) -> Dict[str, List[str]]:
    """
    Extrai tabelas e campos de uma query SQL com mais precisão.
    
    Args:
        query: Query SQL a ser analisada
        
    Returns:
        Dicionário com tabelas e campos extraídos
    """
    # Extrair tabelas usando regex
    # Busca por padrões como "FROM tb_tabela" ou "JOIN tb_tabela"
    # Melhorado para lidar com aliases e espaços
    tabelas_regex = re.findall(r'\b(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)(?:\s+[a-zA-Z0-9_]+)?', query, re.IGNORECASE)
    tabelas = list(set(tabelas_regex))
    
    print(f"DEBUG: Tabelas extraídas: {tabelas}")
    
    # Extrair campos
    # Busca campos entre SELECT e FROM, e também após WHERE, GROUP BY, etc.
    campos_select = []
    
    # Extrair campos do SELECT
    select_match = re.search(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
    if select_match:
        select_clause = select_match.group(1)
        # Dividir por vírgulas, ignorando vírgulas dentro de funções
        campos_raw = re.findall(r'([^,]+(?:\([^)]*\)[^,]*)?)', select_clause)
        for campo_raw in campos_raw:
            # Remover qualquer referência de tabela (como tab.campo)
            campo_limpo = re.sub(r'.*?\.([a-zA-Z0-9_]+)(?:\s+AS\s+[a-zA-Z0-9_]+|\s*,.*)?$', r'\1', campo_raw.strip())
            
            # Se não houver ponto, tentar extrair apenas o nome do campo
            if '.' not in campo_raw:
                campo_limpo = re.sub(r'([a-zA-Z0-9_]+)(?:\s+AS\s+[a-zA-Z0-9_]+|\s*,.*)?$', r'\1', campo_raw.strip())
            
            # Ignorar funções como COUNT, SUM, etc.
            if not re.match(r'^[A-Za-z0-9_]+\(', campo_limpo):
                campos_select.append(campo_limpo)
    
    # Extrair campos de condições (WHERE, JOIN, etc.)
    condicoes_match = re.findall(r'\b(?:WHERE|AND|OR|ON)\s+([a-zA-Z0-9_.]+)', query, re.IGNORECASE)
    campos_condicoes = []
    for condicao in condicoes_match:
        # Extrair apenas o nome do campo
        if '.' in condicao:
            campo = condicao.split('.')[-1]
            campos_condicoes.append(campo)
        else:
            campos_condicoes.append(condicao)
    
    # Juntar todos os campos e remover duplicados
    todos_campos = list(set(campos_select + campos_condicoes))
    
    # Filtrar campos que não são palavras reservadas ou funções
    palavras_reservadas = {"SELECT", "FROM", "WHERE", "JOIN", "ON", "AND", "OR", "GROUP", "ORDER", "BY", "HAVING", "AS", "IS", "NOT", "NULL", "LIKE", "BETWEEN", "IN", "DESC", "ASC"}
    campos_filtrados = [campo for campo in todos_campos if campo.upper() not in palavras_reservadas]
    
    print(f"DEBUG: Campos extraídos: {campos_filtrados}")
    
    return {
        "tabelas": tabelas,
        "campos": campos_filtrados
    }

def converter_query_sac_para_oc3(
    bedrock_runtime: Optional[Any], 
    query: str, 
    mapeamentos_sac_oc3: Dict[str, Any],
    contexto_adicional: Optional[str] = None
) -> str:
    """
    Converte uma query SQL do padrão SAC para o padrão OC3 usando os mapeamentos.
    
    Args:
        bedrock_runtime: Cliente do Bedrock Runtime (opcional)
        query: Query SQL no padrão SAC
        mapeamentos_sac_oc3: Dicionário com mapeamentos de SAC para OC3
        contexto_adicional: Mensagem original completa do usuário (opcional)
        
    Returns:
        Query SQL convertida para o padrão OC3
    """
    try:
        # Extrair tabelas e campos da query
        elementos_query = extrair_elementos_query(query)
        tabelas_query = elementos_query["tabelas"]
        campos_query = elementos_query["campos"]
        
        logger.info(f"Tabelas encontradas: {tabelas_query}")
        logger.info(f"Campos encontrados: {campos_query}")
        
        # Extrair mapeamentos relevantes para a query
        mapeamentos_extraidos = extrair_mapeamentos_para_query(
            mapeamentos_sac_oc3, tabelas_query, campos_query
        )
        
        # Formatar mapeamentos para uso no Bedrock
        mapeamentos_formatados = formatar_mapeamentos_para_bedrock(mapeamentos_extraidos)
        
        # Se não temos Bedrock, fazer a conversão manual
        if not bedrock_runtime:
            return simular_conversao_manual(query, mapeamentos_formatados)
        
        # Preparar o prompt para o Bedrock
        prompt = """
        Você é um assistente especializado em conversão de queries SQL.
        
        Instruções:
        1. Converter a query do SAC (SQL Server) para OC3 (SQL)
        2. Substituir nomes de tabelas e colunas conforme o mapeamento fornecido
        3. Para tabelas SAC com prefixo 'tb_', remover este prefixo na OC3 e colocar em maiúsculas
        4. NÃO modificar os prefixos dos campos (como dt_, cd_, vl_, etc) a menos que estejam especificamente listados no mapeamento
        5. Não adicione nada além da query convertida à sua resposta
        """
        
        # Adicionar informações sobre o contexto se estiver disponível
        if contexto_adicional and contexto_adicional != query:
            prompt += f"""
            
        Contexto adicional:
        O usuário enviou a seguinte mensagem completa:
        "{contexto_adicional}"
            
        Extraí a seguinte query SQL dessa mensagem para conversão:
        """
            
        # Finalizar o prompt
        prompt += f"""
        
        Query original (SAC):
        {query}
        
        Mapeamentos a serem aplicados:
        {json.dumps(mapeamentos_formatados, indent=2)}
        
        Retorne apenas a query convertida em OC3, sem explicações ou comentários adicionais.
        """
        
        # Calcular o max_tokens baseado nos mapeamentos
        max_tokens = 2000
        
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens
        }
        
        # Faz a chamada ao modelo
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload).encode("utf-8")
        )
        
        # Processa a resposta
        response_body = json.loads(response["body"].read().decode("utf-8"))
        
        # Extrair a query convertida da resposta
        query_convertida = ""
        if "content" in response_body and len(response_body["content"]) > 0:
            query_convertida = response_body["content"][0]["text"]
            
            # Limpar formatação de código se presente
            if query_convertida.startswith("```") and query_convertida.endswith("```"):
                # Remover os backticks e a indicação de linguagem
                linhas = query_convertida.split("\n")
                if len(linhas) > 2:
                    query_convertida = "\n".join(linhas[1:-1])  # Remove primeira e última linha
            
            # Remover qualquer texto adicional antes ou depois da query
            query_convertida = query_convertida.strip()
            
        return query_convertida

    except Exception as e:
        logger.error(f"Erro ao converter query SAC para OC3: {e}")
        return f"Erro na conversão: {str(e)}"

def simular_conversao_manual(query: str, mapeamentos: List[Dict[str, Any]]) -> str:
    """
    Simula a conversão manual de uma query SAC para OC3.
    
    Args:
        query: Query SQL no padrão SAC
        mapeamentos: Lista de mapeamentos formatados
        
    Returns:
        Query SQL convertida para o padrão OC3
    """
    # Query convertida simulada
    result_query = "-- Query convertida de SAC para OC3\n"
    
    # Criar dicionários de mapeamento para tabelas e campos
    mapeamento_tabelas = {}
    mapeamento_campos = {}
    
    for item in mapeamentos:
        # Mapeamento de tabelas
        if "TABELA SAC" in item and "TABELA OC3" in item:
            mapeamento_tabelas[item["TABELA SAC"].lower()] = item["TABELA OC3"]
        
        # Mapeamento de campos
        if "CAMPO SAC" in item and "CAMPO OC3" in item:
            mapeamento_campos[item["CAMPO SAC"].lower()] = item["CAMPO OC3"]
    
    # Converter query
    query_modificada = query
    
    # Substituir tabelas
    for tabela_sac, tabela_oc3 in mapeamento_tabelas.items():
        # Utilizar regex para substituir apenas nomes completos de tabela
        padrao = r'\b' + re.escape(tabela_sac) + r'\b'
        query_modificada = re.sub(padrao, tabela_oc3, query_modificada, flags=re.IGNORECASE)
    
    # Substituir campos específicos mapeados
    for campo_sac, campo_oc3 in mapeamento_campos.items():
        padrao = r'\b' + re.escape(campo_sac) + r'\b'
        query_modificada = re.sub(padrao, campo_oc3, query_modificada, flags=re.IGNORECASE)
    
    # Remover prefixo tb_ de tabelas que não estão nos mapeamentos
    query_modificada = re.sub(r'\b(tb_\w+)\b', lambda m: m.group(1).replace('tb_', '').upper(), query_modificada, flags=re.IGNORECASE)
    
    # Adicionar a query modificada ao resultado
    result_query += query_modificada
    
    return result_query