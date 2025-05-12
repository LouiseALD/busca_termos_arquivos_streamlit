# chatbot/converters/simulation.py
# Funções para simular conversões quando o Bedrock não está disponível

import re
from chatbot.converters.conversion_utils import agrupar_mapeamentos_para_lambda


def simular_conversao_query(query_original, mapeamentos):
    """
    Simula a conversão de uma query SQL usando os mapeamentos selecionados.
    
    Args:
        query_original: Query SQL original para converter
        mapeamentos_selecionados: Lista de mapeamentos a serem utilizados
        
    Returns:
        Query SQL convertida (simulada)
    """
    # Verificar se os mapeamentos já estão no formato agrupado
    if isinstance(mapeamentos, dict) and all(isinstance(v, dict) for v in mapeamentos.values()):
        # Já está no formato agrupado
        mapeamentos_agrupados = mapeamentos
        
        # Determinar o tipo de conversão pelos nomes dos campos
        # Se tiver tabela_datamesh, assumimos OC3_PARA_DATAMESH
        for tabela, campos in mapeamentos_agrupados.items():
            for campo, info in campos.items():
                if "tabela_datamesh" in info:
                    tipo_conversao = "OC3_PARA_DATAMESH"
                    break
                else:
                    tipo_conversao = "SAC_PARA_OC3"
    else:
        # Converter para o formato agrupado
        from chatbot.converters.conversion_utils import agrupar_mapeamentos_para_lambda
        mapeamentos_agrupados = agrupar_mapeamentos_para_lambda(mapeamentos)
        
        # Detectar o tipo de conversão
        tipo_conversao = detectar_tipo_conversao(mapeamentos)
    
    # Usar a simulação correspondente ao tipo de conversão
    if tipo_conversao == "OC3_PARA_DATAMESH":
        return simular_conversao_oc3_para_datamesh_agrupado(query_original, mapeamentos_agrupados)
    elif tipo_conversao == "SAC_PARA_OC3":
        return simular_conversao_sac_para_oc3_agrupado(query_original, mapeamentos_agrupados)
    else:
        return f"# Tipo de conversão não reconhecido\n{query_original}"

def simular_conversao_oc3_para_datamesh_agrupado(query_original, mapeamentos_agrupados):
    """
    Simula a conversão de uma query OC3 para DataMesh usando mapeamentos agrupados.
    
    Args:
        query_original: Query SQL no formato OC3
        mapeamentos_agrupados: Dicionário de mapeamentos no formato agrupado
        
    Returns:
        Query SQL convertida para DataMesh
    """
    import re
    
    # Converter a query
    query_convertida = query_original
    
    # Substituir tabelas com prefixos
    for tabela_oc3, campos in mapeamentos_agrupados.items():
        # Pegar o primeiro campo para determinar o tipo da tabela
        primeiro_campo = next(iter(campos.values()), {})
        tipo = primeiro_campo.get("tipo", "cadastro")
        tabela_datamesh = primeiro_campo.get("tabela_datamesh", "")
        
        if tabela_datamesh:
            prefixo = "spec_" if tipo == "cadastro" else "hub_"
            
            # Usar regex para substituir apenas o nome completo da tabela
            padrao_tabela = r'\b' + re.escape(tabela_oc3) + r'\b'
            query_convertida = re.sub(padrao_tabela, f"{prefixo}{tabela_datamesh}", query_convertida, flags=re.IGNORECASE)
    
    # Substituir nomes de campos
    for tabela_oc3, campos in mapeamentos_agrupados.items():
        for campo_oc3, info in campos.items():
            campo_datamesh = info.get("campo_datamesh", "")
            if not campo_datamesh:
                continue
                
            # Buscar o padrão tabela.campo ou apenas campo
            padrao_campo_com_tabela = r'\b' + re.escape(tabela_oc3) + r'\.' + re.escape(campo_oc3) + r'\b'
            
            # Determinar o prefixo da tabela
            tipo = info.get("tipo", "cadastro")
            tabela_datamesh = info.get("tabela_datamesh", "")
            prefixo = "spec_" if tipo == "cadastro" else "hub_"
            
            # Substituir tabela.campo
            query_convertida = re.sub(
                padrao_campo_com_tabela, 
                f"{prefixo}{tabela_datamesh}.{campo_datamesh}", 
                query_convertida, 
                flags=re.IGNORECASE
            )
            
            # Substituir campo isolado (se não for palavra reservada)
            # Isto é mais arriscado pois pode substituir palavras incorretamente
            if campo_oc3 not in ["SELECT", "FROM", "WHERE", "AND", "OR", "JOIN", "ON", "GROUP", "BY", "ORDER"]:
                padrao_campo = r'\b' + re.escape(campo_oc3) + r'\b'
                query_convertida = re.sub(padrao_campo, campo_datamesh, query_convertida, flags=re.IGNORECASE)
    
    # Substituir funções e sintaxe específicas
    query_convertida = query_convertida.replace("GETDATE()", "current_date")
    query_convertida = re.sub(r'TOP\s+(\d+)', r'LIMIT \1', query_convertida, flags=re.IGNORECASE)
    query_convertida = re.sub(r'ISNULL\(([^,]+),\s*([^)]+)\)', r'COALESCE(\1, \2)', query_convertida, flags=re.IGNORECASE)
    
    # Converter concatenação com + para função concat()
    query_convertida = re.sub(r'(\w+)\s*\+\s*(\w+)', r'concat(\1, \2)', query_convertida)
    
    # Adicionar comentário explicativo
    query_convertida = f"-- Query convertida de OC3 para DataMesh (Presto SQL / Athena)\n{query_convertida}"
    
    return query_convertida

def simular_conversao_sac_para_oc3_agrupado(query_original, mapeamentos_agrupados):
    """
    Simula a conversão de uma query SAC para OC3 usando mapeamentos agrupados.
    
    Args:
        query_original: Query SQL no formato SAC
        mapeamentos_agrupados: Dicionário de mapeamentos no formato agrupado
        
    Returns:
        Query SQL convertida para OC3
    """
    import re
    
    # Converter a query
    query_convertida = query_original
    
    # Substituir tabelas
    for tabela_sac, campos in mapeamentos_agrupados.items():
        # Pegar o primeiro campo para determinar a tabela OC3
        primeiro_campo = next(iter(campos.values()), {})
        tabela_oc3 = primeiro_campo.get("tabela_datamesh", "")  # A chave ainda é tabela_datamesh no dicionário
        
        if tabela_oc3:
            # Usar regex para substituir apenas o nome completo da tabela
            padrao_tabela = r'\b' + re.escape(tabela_sac) + r'\b'
            query_convertida = re.sub(padrao_tabela, tabela_oc3, query_convertida, flags=re.IGNORECASE)
    
    # Substituir nomes de campos
    for tabela_sac, campos in mapeamentos_agrupados.items():
        for campo_sac, info in campos.items():
            campo_oc3 = info.get("campo_datamesh", "")  # A chave ainda é campo_datamesh no dicionário
            if not campo_oc3:
                continue
                
            # Pegar tabela OC3
            tabela_oc3 = info.get("tabela_datamesh", "")
            
            # Buscar o padrão tabela.campo ou apenas campo
            padrao_campo_com_tabela = r'\b' + re.escape(tabela_sac) + r'\.' + re.escape(campo_sac) + r'\b'
            
            # Substituir tabela.campo
            query_convertida = re.sub(padrao_campo_com_tabela, f"{tabela_oc3}.{campo_oc3}", query_convertida, flags=re.IGNORECASE)
            
            # Substituir campo isolado (se não for palavra reservada)
            if campo_sac not in ["select", "from", "where", "and", "or", "join", "on", "group", "by", "order"]:
                padrao_campo = r'\b' + re.escape(campo_sac) + r'\b'
                query_convertida = re.sub(padrao_campo, campo_oc3, query_convertida, flags=re.IGNORECASE)
    
    # Remover prefixo tb_ de tabelas que não estão nos mapeamentos
    query_convertida = re.sub(r'\b(tb_\w+)\b', lambda m: m.group(1).replace('tb_', '').upper(), query_convertida, flags=re.IGNORECASE)
    
    # Adicionar comentário explicativo
    query_convertida = f"-- Query convertida de SAC para OC3\n{query_convertida}"
    
    return query_convertida

# Adicione esta função ao arquivo chatbot/converters/simulation.py

def detectar_tipo_conversao(mapeamentos):
    """
    Detecta o tipo de conversão com base nos mapeamentos selecionados.
    
    Args:
        mapeamentos: Lista de mapeamentos
        
    Returns:
        String indicando o tipo de conversão ("OC3_PARA_DATAMESH" ou "SAC_PARA_OC3")
    """
    if not mapeamentos:
        return "DESCONHECIDO"
    
    # Verificar se é lista ou dicionário
    if isinstance(mapeamentos, dict):
        # Se já está no formato agrupado, tentar inferir pelo conteúdo
        for tabela, campos in mapeamentos.items():
            if campos and isinstance(next(iter(campos.values()), {}), dict):
                campo_info = next(iter(campos.values()))
                # Se tem tabela_datamesh, assumimos OC3_PARA_DATAMESH
                if "tabela_datamesh" in campo_info:
                    return "OC3_PARA_DATAMESH"
        return "DESCONHECIDO"
    
    # Verificar campos comuns em cada tipo de mapeamento
    primeiro_mapeamento = mapeamentos[0] if mapeamentos else {}
    
    # Verificar se é mapeamento OC3 para DataMesh
    if "TABELA OC3 LIGHT" in primeiro_mapeamento and "TABELA DATA MESH" in primeiro_mapeamento:
        return "OC3_PARA_DATAMESH"
    
    # Verificar se é mapeamento SAC para OC3
    if "TABELA SAC" in primeiro_mapeamento and "TABELA OC3" in primeiro_mapeamento:
        return "SAC_PARA_OC3"
    
    return "DESCONHECIDO"