# chatbot/converters/conversion_utils.py
# Funções para manipular e converter os formatos de mapeamento



def agrupar_mapeamentos_para_lambda(mapeamentos_selecionados):
    """
    Agrupa os mapeamentos no formato adequado para envio à Lambda, organizando por tabela e campo.
    
    Args:
        mapeamentos_selecionados: Lista de mapeamentos selecionados pelo usuário
        
    Returns:
        Dicionário agrupado no formato:
        {
            "tabela_original": {
                "campo_original": {
                    "tabela_datamesh": "nova_tabela",
                    "campo_datamesh": "novo_campo",
                    "tipo_dado": "tipo",
                    "tipo": "categoria",
                    "sigla": "alias"
                }
            }
        }
    """
    print("\n--- AGRUPANDO MAPEAMENTOS PARA LAMBDA ---")
    
    mapeamentos_agrupados = {}
    
    # Verificar se temos mapeamentos válidos
    if not mapeamentos_selecionados:
        print("Aviso: Nenhum mapeamento selecionado para agrupar.")
        return mapeamentos_agrupados
    
    print(f"Total de mapeamentos a serem agrupados: {len(mapeamentos_selecionados)}")
    
    # Verificar o tipo de conversão analisando os campos disponíveis
    tipo_conversao = "OC3_PARA_DATAMESH"  # padrão
    if mapeamentos_selecionados and "TABELA SAC" in mapeamentos_selecionados[0]:
        tipo_conversao = "SAC_PARA_OC3"
    
    print(f"Tipo de conversão detectado: {tipo_conversao}")
    
    for item in mapeamentos_selecionados:
        if not isinstance(item, dict):
            print(f"Aviso: Item não é um dicionário - {item}")
            continue
        
        # Definir campos com base no tipo de conversão
        if tipo_conversao == "OC3_PARA_DATAMESH":
            tabela_original = item.get("TABELA OC3 LIGHT", "")
            campo_original = item.get("CAMPO OC3 LIGHT", "")
            tabela_destino = item.get("TABELA DATA MESH", "")
            campo_destino = item.get("CAMPO DATA MESH FINAL", "")
            tipo_dado = item.get("TIPO DE DADO", "")
            categoria = item.get("tipo", "cadastro")
            sigla = item.get("sigla", tabela_original[:1].lower())
        else:  # SAC_PARA_OC3
            tabela_original = item.get("TABELA SAC", "")
            campo_original = item.get("CAMPO SAC", "")
            tabela_destino = item.get("TABELA OC3", "")
            campo_destino = item.get("CAMPO OC3", "")
            tipo_dado = item.get("TIPO DE DADO", "")
            categoria = item.get("tipo", "")
            sigla = item.get("sigla", tabela_original[:1].lower())
        
        # Pular se tabela ou campo estiverem vazios
        if not tabela_original or not campo_original:
            print(f"Aviso: Item com tabela ou campo vazios - Tabela: '{tabela_original}', Campo: '{campo_original}'")
            continue
            
        # Inicializar a estrutura de nível tabela se não existir
        if tabela_original not in mapeamentos_agrupados:
            mapeamentos_agrupados[tabela_original] = {}
            print(f"Nova tabela adicionada: {tabela_original}")
        
        # Adicionar mapeamento de campo
        mapeamentos_agrupados[tabela_original][campo_original] = {
            "tabela_datamesh": tabela_destino,
            "campo_datamesh": campo_destino,
            "tipo_dado": tipo_dado,
            "tipo": categoria,
            "sigla": sigla
        }
        print(f"Campo adicionado: {tabela_original}.{campo_original} -> {tabela_destino}.{campo_destino}")
    
    print(f"Agrupamento concluído. Total de tabelas agrupadas: {len(mapeamentos_agrupados)}")
    print("--- FIM DO AGRUPAMENTO ---\n")
    
    return mapeamentos_agrupados

def extrair_elementos_query_sql(query):
    """
    Extrai tabelas e campos de uma query SQL.
    
    Args:
        query: Query SQL a ser analisada
        
    Returns:
        Dicionário com tabelas e campos extraídos
    """
    import re
    
    # Extrair tabelas
    tabelas = re.findall(r'(?:FROM|JOIN)\s+(\w+)', query, re.IGNORECASE)
    tabelas = [tabela.upper() for tabela in tabelas]
    
    # Extrair campos
    campos_match = re.findall(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
    
    campos = []
    if campos_match:
        campos_str = campos_match[0]
        # Dividir por vírgula, respeitando parênteses
        campos_raw = re.findall(r'([^,]+(?:\([^)]*\)[^,]*)?)', campos_str)
        
        for campo_raw in campos_raw:
            # Extrair o nome do campo, removendo aliases e funções
            campo_limpo = re.sub(r'.*?\.([a-zA-Z0-9_]+)(?:\s+AS\s+[a-zA-Z0-9_]+)?', r'\1', campo_raw.strip())
            # Se não houver ponto (tabela.campo), pegar o campo diretamente
            if '.' not in campo_raw and not re.match(r'^[A-Za-z0-9_]+\(', campo_raw):
                campo_limpo = re.sub(r'([a-zA-Z0-9_]+)(?:\s+AS\s+[a-zA-Z0-9_]+)?', r'\1', campo_raw.strip())
            
            # Ignorar funções como COUNT, SUM, etc.
            if not re.match(r'^[A-Za-z0-9_]+\(', campo_limpo):
                campos.append(campo_limpo.upper())
    
    # Extrair campos de condições (WHERE, JOIN, etc.)
    condicoes_match = re.findall(r'\b(?:WHERE|AND|OR|ON)\s+([a-zA-Z0-9_.]+)', query, re.IGNORECASE)
    for condicao in condicoes_match:
        # Extrair apenas o nome do campo
        if '.' in condicao:
            campo = condicao.split('.')[-1].upper()
            if campo not in campos:
                campos.append(campo)
    
    return {
        "tabelas": tabelas,
        "campos": campos
    }

def filtrar_mapeamentos_por_query(mapeamentos, query):
    """
    Filtra os mapeamentos com base nos elementos da query.
    
    Args:
        mapeamentos: Lista de mapeamentos disponíveis
        query: Query SQL
        
    Returns:
        Lista de mapeamentos filtrados relevantes para a query
    """
    # Extrair elementos da query
    elementos = extrair_elementos_query_sql(query)
    tabelas_query = elementos["tabelas"]
    campos_query = elementos["campos"]
    
    # Verificar o tipo de conversão
    tipo_conversao = "OC3_PARA_DATAMESH"  # padrão
    if mapeamentos and "TABELA SAC" in mapeamentos[0]:
        tipo_conversao = "SAC_PARA_OC3"
    
    mapeamentos_filtrados = []
    
    for item in mapeamentos:
        if not isinstance(item, dict):
            continue
            
        # Determinar tabela e campo com base no tipo de conversão
        if tipo_conversao == "OC3_PARA_DATAMESH":
            tabela = item.get("TABELA OC3 LIGHT", "").upper()
            campo = item.get("CAMPO OC3 LIGHT", "").upper()
        else:  # SAC_PARA_OC3
            tabela = item.get("TABELA SAC", "").upper()
            campo = item.get("CAMPO SAC", "").upper()
        
        # Verificar se a tabela está na query
        if tabela in tabelas_query:
            # Se o campo está na query ou o campo não é especificado, incluir o mapeamento
            if not campo or campo in campos_query:
                # Adicionar uma lista de campos que deram match na query
                item_with_match = item.copy()
                item_with_match["campos_match"] = [c for c in campos_query if c in campos_query]
                mapeamentos_filtrados.append(item_with_match)
    
    return mapeamentos_filtrados