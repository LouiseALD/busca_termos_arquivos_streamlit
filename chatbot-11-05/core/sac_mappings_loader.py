import json

import os
from typing import Dict, List, Any
from logger_config import setup_logger
logger = setup_logger()

def carregar_mapeamentos_sac_oc3(caminho_arquivo_ou_pasta: str) -> Dict[str, Any]:
    """
    Carrega os mapeamentos de SAC para OC3 a partir de um arquivo JSON ou pasta.
    
    Args:
        caminho_arquivo_ou_pasta: Caminho para o arquivo JSON ou pasta contendo mapeamentos
        
    Returns:
        Dicionário com os mapeamentos carregados
    """
    mapeamentos_combinados = {
        "aba": "Mapeamentos SAC-OC3",
        "tabelas": []
    }
    
    try:
        # Verificar se é um diretório ou arquivo
        if os.path.isdir(caminho_arquivo_ou_pasta):
            # Processar diretório
            for arquivo in os.listdir(caminho_arquivo_ou_pasta):
                if arquivo.endswith('.json'):
                    caminho_completo = os.path.join(caminho_arquivo_ou_pasta, arquivo)
                    try:
                        with open(caminho_completo, 'r', encoding='utf-8') as f:
                            dados = json.load(f)
                            
                            # Verificar estrutura do arquivo
                            if isinstance(dados, dict) and "tabelas" in dados:
                                mapeamentos_combinados["tabelas"].extend(dados["tabelas"])
                            elif isinstance(dados, list):
                                # Se for uma lista direta de tabelas
                                mapeamentos_combinados["tabelas"].extend(dados)
                    except Exception as e:
                        logger.error(f"Erro ao processar arquivo {caminho_completo}: {e}")
        else:
            # Processar arquivo único
            with open(caminho_arquivo_ou_pasta, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                
                if isinstance(dados, dict) and "tabelas" in dados:
                    mapeamentos_combinados["tabelas"] = dados["tabelas"]
                elif isinstance(dados, list):
                    mapeamentos_combinados["tabelas"] = dados
    except Exception as e:
        logger.error(f"Erro ao carregar mapeamentos SAC-OC3: {e}")
    
    logger.info(f"Carregados {len(mapeamentos_combinados['tabelas'])} tabelas de mapeamento SAC-OC3")
    return mapeamentos_combinados

def buscar_tabelas_por_nome(mapeamentos: Dict[str, Any], nome_tabela: str) -> List[Dict[str, Any]]:
    """
    Busca tabelas pelo nome no mapeamento.
    
    Args:
        mapeamentos: Dicionário contendo os mapeamentos
        nome_tabela: Nome da tabela a ser buscada
        
    Returns:
        Lista de tabelas encontradas
    """
    resultados = []
    
    if not mapeamentos or "tabelas" not in mapeamentos:
        return resultados
    
    for tabela in mapeamentos["tabelas"]:
        if nome_tabela.lower() in tabela.get("tabela", "").lower():
            resultados.append(tabela)
    
    return resultados

def buscar_campos_por_nome(mapeamentos: Dict[str, Any], nome_campo: str) -> List[Dict[str, Any]]:
    """
    Busca campos pelo nome no mapeamento.
    
    Args:
        mapeamentos: Dicionário contendo os mapeamentos
        nome_campo: Nome do campo a ser buscado
        
    Returns:
        Lista de campos encontrados com informação da tabela
    """
    resultados = []
    
    if not mapeamentos or "tabelas" not in mapeamentos:
        return resultados
    
    for tabela in mapeamentos["tabelas"]:
        if "campos" not in tabela:
            continue
            
        for campo in tabela["campos"]:
            if nome_campo.lower() in campo.get("campo", "").lower():
                # Incluir informação da tabela junto com o campo
                resultados.append({
                    "tabela": tabela.get("tabela"),
                    "descritivoTabela": tabela.get("descritivoTabela"),
                    "tipo": tabela.get("tipo"),
                    "campo": campo
                })
    
    return resultados

def extrair_mapeamentos_para_query(mapeamentos: Dict[str, Any], tabelas_query: List[str], campos_query: List[str]) -> Dict[str, Any]:
    """
    Extrai mapeamentos relevantes para uma query específica.
    
    Args:
        mapeamentos: Dicionário contendo os mapeamentos
        tabelas_query: Lista de nomes de tabelas presentes na query
        campos_query: Lista de nomes de campos presentes na query
        
    Returns:
        Dicionário com mapeamentos relevantes
    """
    resultado = {
        "tabelas": {},
        "campos": {}
    }
    
    # Processar tabelas
    for tabela_nome in tabelas_query:
        tabelas_encontradas = buscar_tabelas_por_nome(mapeamentos, tabela_nome)
        if tabelas_encontradas:
            resultado["tabelas"][tabela_nome] = tabelas_encontradas
    
    # Processar campos
    for campo_nome in campos_query:
        campos_encontrados = buscar_campos_por_nome(mapeamentos, campo_nome)
        if campos_encontrados:
            resultado["campos"][campo_nome] = campos_encontrados
    
    return resultado

def formatar_mapeamentos_para_bedrock(mapeamentos_extraidos: Dict[str, Any]) -> List[Dict[str, Any]]:
    resultado = []
    
    # Processar tabelas mapeadas
    for tabela_nome, tabelas in mapeamentos_extraidos["tabelas"].items():
        for tabela in tabelas:
            # Se existem campos específicos de match, usar apenas esses
            if "campos_match" in tabela:
                for campo in tabela["campos_match"]:
                    item = {
                        "tipo": tabela.get("tipo", ""),
                        "TABELA SAC": tabela.get("TABELA SAC", ""),
                        "CAMPO SAC": campo.get("campo", ""),
                        "TIPO DE DADO": campo.get("tipoCampo", ""),
                        "TABELA ORIGEM": campo.get("tabelaOrigem", ""),
                        "CAMPO ORIGEM": campo.get("campoOrigem", ""),
                        "CAMPO OC3": campo.get("campo", "") # Manter o nome original do campo
                    }
                    resultado.append(item)
            else:
                # Manter lógica original para casos sem match específico
                item = {
                    "tipo": tabela.get("tipo", ""),
                    "TABELA SAC": tabela.get("tabela", ""),
                    "DESCRITIVO": tabela.get("descritivoTabela", ""),
                    "TABELA OC3": tabela.get("tabela", "").replace("tb_", "").upper()
                }
                resultado.append(item)
    
    return resultado