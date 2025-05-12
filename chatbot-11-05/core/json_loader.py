import json

import os
import re

from logger_config import setup_logger
logger = setup_logger()

def carregar_mapeamentos(pasta_json: str) -> list:
    """Carrega mapeamentos de arquivos JSON em uma pasta especificada.

    :param pasta_json: Caminho para a pasta contendo arquivos JSON.
    :return: Lista de dicionários com mapeamentos carregados.
    """
    logger.info(f"Carregando mapeamentos da pasta: {pasta_json}")
    mapeamentos = []

    for root, _, files in os.walk(pasta_json):
        for file in files:
            if file.endswith(".json"):
                caminho_json = os.path.join(root, file)
                try:
                    with open(caminho_json, "r", encoding="utf-8") as f:
                        dados = json.load(f)
                        if isinstance(dados, list):
                            for item in dados:
                                if isinstance(item, dict):
                                    mapeamentos.append(item)
                except Exception as e:
                    print(f"Erro ao processar o arquivo {caminho_json}: {e}")

    return mapeamentos

def buscar_por_termos(query, mapeamentos):
    def extrair_elementos_query(query):
        # Extrair tabelas usando regex mais abrangente
        tabela_match = re.findall(r'(?:FROM|JOIN)\s+(\w+)', query, re.IGNORECASE)
        tabelas = [tabela.upper() for tabela in tabela_match if tabela]

        # Extrair campos
        campos_match = re.findall(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
        if campos_match:
            campos_str = campos_match[0]
            # Dividir por vírgula, respeitando parênteses
            campos_raw = re.findall(r'([^,]+(?:\([^)]*\)[^,]*)?)', campos_str)
            # Limpar cada campo
            campos = []
            for campo_raw in campos_raw:
                # Extrair apenas o nome do campo, removendo aliases e referências de tabela
                campo_limpo = re.sub(r'.*?\.([a-zA-Z0-9_]+)(?:\s+AS\s+[a-zA-Z0-9_]+)?', r'\1', campo_raw.strip())
                campos.append(campo_limpo.upper())
        else:
            campos = []
        
        return {
            'tabelas': tabelas,
            'campos': campos
        }

    # Extrair elementos da query
    elementos_query = extrair_elementos_query(query)
    
    print("\n" + "=" * 50)
    print(f"QUERY ORIGINAL: {query}")
    print(f"Tabelas extraídas: {elementos_query['tabelas']}")
    print(f"Campos extraídos: {elementos_query['campos']}")
    print(f"Total de mapeamentos: {len(mapeamentos)}")

    resultados = []

    # Iterar sobre todos os mapeamentos
    for item in mapeamentos:
        # Verificar correspondência de tabela
        tabela_oc3 = item.get("TABELA OC3 LIGHT", "").upper()
        tabela_match = any(
            tabela_oc3 == tabela_query or 
            tabela_oc3 in tabela_query or 
            tabela_query in tabela_oc3
            for tabela_query in elementos_query['tabelas']
        )

        # Se não encontrou tabela, continue
        if not tabela_match:
            continue

        # Verificar campos
        campos_match = []
        for campo_query in elementos_query['campos']:
            # Lista de possíveis campos relacionados
            possiveis_campos = [
                item.get("CAMPO OC3 LIGHT", "").upper(),
                item.get("CAMPO DATA MESH FINAL", "").upper(),
                # Adicionar variações de nomes de campos
                campo_query.replace("ID_", "").upper(),
                campo_query.replace("_", "").upper()
            ]

            # Verificar se o campo da query corresponde a algum campo do mapeamento
            campo_encontrado = any(
                campo_query.upper() in campo_possivel or 
                campo_possivel in campo_query.upper()
                for campo_possivel in possiveis_campos
            )

            if campo_encontrado:
                campos_match.append(campo_query)

        # Se encontrou campos correspondentes, adicionar o item
        if campos_match:
            novo_item = {
                "tipo": item.get("tipo", ""),
                "TABELA OC3 LIGHT": item.get("TABELA OC3 LIGHT", ""),
                "TABELA DATA MESH": item.get("TABELA DATA MESH", ""),
                "CAMPO OC3 LIGHT": item.get("CAMPO OC3 LIGHT", ""),
                "CAMPO DATA MESH FINAL": item.get("CAMPO DATA MESH FINAL", ""),
                "campos_match": campos_match
            }
            resultados.append(novo_item)

    # Debug final
    print(f"\nResultados encontrados: {len(resultados)}")
    for resultado in resultados:
        print(f"Resultado: {json.dumps(resultado, indent=2)}")
    print("=" * 50 + "\n")

    return resultados

def filtrar_jsons(resultados: list) -> list:
    """Filtra resultados JSON para incluir apenas itens com campos válidos.

    :param resultados: Lista de dicionários a serem filtrados.
    :return: Lista de dicionários filtrados.
    """
    
    resultados_filtrados = [
        {
            "tipo": item.get("tipo"),
            "TABELA OC3 LIGHT": item.get("TABELA OC3 LIGHT"),
            "CAMPO OC3 LIGHT": item.get("CAMPO OC3 LIGHT"),
            "TABELA DATA MESH": item.get("TABELA DATA MESH"),
            "CAMPO DATA MESH FINAL": item.get("CAMPO DATA MESH FINAL"),
            "TIPO DE DADO": item.get("TIPO DE DADO")
        }
        for item in resultados
        if item.get("tipo") != "nan"
        and item.get("TABELA OC3 LIGHT") != "nan"
        and item.get("CAMPO OC3 LIGHT") != "nan"
        and item.get("TABELA DATA MESH") != "nan"
        and item.get("CAMPO DATA MESH FINAL") != "nan"
        and item.get("TIPO DE DADO") != "nan"
    ]

    return resultados_filtrados
