import re

def extrair_tabelas_aliases(query):
    padrao_tanela_alias = re.findall(r"FROM\s+(\w+)\s+(\w+)?JOIN\s+(\w+)\s+(\w+)?", query, re.IGNORECASE)
    tabela_alias_dict = {}

    for match in padrao_tanela_alias:
        tabela_real = match[0] if match[0] else match[2]
        alias = match[1] if match[1] else match[3]
        tabela_alias_dict[alias] = tabela_real

    return tabela_alias_dict

def extrair_colunas_usadas(query, resultados_filtrados):
    colunas_usadas = {}

    matches = re.findall(r"(\w+)\.(\w+)", query)
    matches = [(a.upper(), b) for (a, b) in matches]

    for alias, coluna in matches:
        if alias not in colunas_usadas:
            colunas_usadas[alias] = set()
        colunas_usadas[alias].add(coluna)

    colunas_isoladas = re.findall(r"\b(\w+)\b", query)
    palavras_reservadas = {"SELECT", "FROM", "JOIN", "ON", "WHERE", "ORDER", "BY", "HAVING", "GROUP", "CASE"}

    for coluna in colunas_isoladas:
        if coluna.upper() not in palavras_reservadas and not coluna.isdigit():
            if "sem_alias" not in colunas_usadas:
                colunas_usadas["sem_alias"] = set()
            colunas_usadas["sem_alias"].add(coluna)

    return colunas_usadas

def compactar_mapeamentos_otimizados(resultados_filtrados, tabelas_query, colunas_query):
    """
    Otimiza o processo de compactação de mapeamentos para formato de múltiplas possibilidades.
    """
    # Estrutura para armazenar mapeamentos
    mapeamentos_otimizados = {}
    
    # Processar cada tabela distinta
    tabelas_unicas = set(item.get("TABELA OC3 LIGHT", "") for item in resultados_filtrados)
    
    for tabela_origem in tabelas_unicas:
        # Filtrar resultados apenas para esta tabela
        resultados_tabela = [
            item for item in resultados_filtrados 
            if item.get("TABELA OC3 LIGHT", "") == tabela_origem
        ]
        
        # Extrair campos únicos
        campos_tabela = set(
            item.get("CAMPO OC3 LIGHT", "") 
            for item in resultados_tabela
        )
        
        # Extrair destinos e seus campos
        destinos = {}
        for item in resultados_tabela:
            tabela_destino = item.get("TABELA DATA MESH", "")
            campo_origem = item.get("CAMPO OC3 LIGHT", "")
            
            if tabela_destino not in destinos:
                destinos[tabela_destino] = set()
            destinos[tabela_destino].add(campo_origem)
        
        # Preparar estrutura final para esta tabela
        mapeamento_tabela = {
            "total_mapeamentos": len(resultados_tabela),
            "campos": list(campos_tabela),
            "destinos": {}
        }
        
        # Processar cada destino
        for tabela_destino, campos_destino in destinos.items():
            # Preparar detalhes para cada campo no destino
            detalhes_destino = {
                "campos": list(campos_destino),
                "detalhes": {}
            }
            
            # Adicionar detalhes específicos para cada campo
            for campo_origem in campos_destino:
                # Encontrar o item de mapeamento específico
                item_mapeamento = next(
                    (item for item in resultados_tabela 
                     if (item.get("CAMPO OC3 LIGHT") == campo_origem and 
                         item.get("TABELA DATA MESH") == tabela_destino)), 
                    None
                )
                
                if item_mapeamento:
                    detalhes = {
                        "tabela_origem": tabela_origem,
                        "campo_origem": campo_origem,
                        "tabela_destino": tabela_destino,
                        "campo_destino": item_mapeamento.get("CAMPO DATA MESH FINAL", ""),
                        "tipo_dado": item_mapeamento.get("TIPO DE DADO", ""),
                        "tipo": item_mapeamento.get("tipo", ""),
                        "sigla": tabelas_query.get(tabela_origem.lower(), tabela_origem[:1])
                    }
                    
                    detalhes_destino["detalhes"][campo_origem] = detalhes
            
            # Adicionar destino à estrutura da tabela
            mapeamento_tabela["destinos"][tabela_destino] = detalhes_destino
        
        # Adicionar à estrutura final
        mapeamentos_otimizados[tabela_origem] = mapeamento_tabela
    
    return mapeamentos_otimizados

def calcular_max_tokens(mapeamentos_otimizados):
    """
    Calcula o número máximo de tokens com base nos mapeamentos otimizados.
    """
    # Base de tokens
    base_tokens = 300  # Token inicial para o prompt
    
    # Calcular tokens adicionais baseado nos mapeamentos
    tokens_por_mapeamento = 0
    
    for tabela, dados in mapeamentos_otimizados.items():
        # Tokens base por tabela
        tokens_por_mapeamento += 50
        
        # Tokens por total de mapeamentos
        tokens_por_mapeamento += dados["total_mapeamentos"] * 10
        
        # Tokens por destinos
        tokens_por_mapeamento += len(dados.get("destinos", {})) * 20
        
        # Tokens por campos
        tokens_por_mapeamento += len(dados.get("campos", [])) * 15
    
    # Limitar tokens máximos
    max_tokens = min(base_tokens + tokens_por_mapeamento, 2500)
    
    return max_tokens

def demonstrar_mapeamentos(query, resultados_filtrados):
    """
    Demonstra os mapeamentos no formato de múltiplas possibilidades.
    """
    import json
    
    # Extrair tabelas e aliases
    tabelas_alias_map = extrair_tabelas_aliases(query)
    
    # Extrair colunas usadas
    colunas_usadas = extrair_colunas_usadas(query, resultados_filtrados)
    
    # Compactar mapeamentos no formato otimizado
    mapeamentos_otimizados = compactar_mapeamentos_otimizados(
        resultados_filtrados, 
        tabelas_alias_map, 
        colunas_usadas
    )
    
    # Calcular tokens
    estimated_tokens = calcular_max_tokens(mapeamentos_otimizados)
    
    # Imprimir resultados formatados
    print("\n--- Mapeamentos de Múltiplas Possibilidades ---")
    print(f"Tokens Estimados: {estimated_tokens}")
    print("Mapeamentos:")
    print(json.dumps(mapeamentos_otimizados, indent=2))
    
    return mapeamentos_otimizados

def processar_query(query, resultados_filtrados):
    # 1. Debug inicial
    print("\n--- Início do Processamento de Query ---")
    print(f"Query Original: {query}")
    print(f"Total de Resultados Filtrados: {len(resultados_filtrados)}")
    
    # 2. Extrair tabelas e aliases
    tabelas_alias_map = extrair_tabelas_aliases(query)
    print("\n--- Tabelas e Aliases ---")
    print("Mapeamento de Tabelas:")
    for alias, tabela in tabelas_alias_map.items():
        print(f"  Alias: {alias} -> Tabela: {tabela}")
    
    # 3. Extrair colunas usadas
    colunas_usadas = extrair_colunas_usadas(query, resultados_filtrados)
    print("\n--- Colunas Usadas ---")
    for alias, colunas in colunas_usadas.items():
        print(f"  {alias}: {', '.join(colunas)}")
    
    # 4. Compactar mapeamentos com logs detalhados
    mapeamentos_compactados = compactar_mapeamentos_otimizados(
        resultados_filtrados, 
        tabelas_alias_map, 
        colunas_usadas
    )
    print("\n--- Mapeamentos Compactados ---")
    for tipo, dados in mapeamentos_compactados.items():
        print(f"\nTipo de Registro: {tipo}")
        print(f"Total de Mapeamentos: {dados['total_mapeamentos']}")
        print("Tabelas de Destino:", dados['tabelas_destino'])
        
        print("Campos Mapeados:")
        for tabela_origem, campos in dados['campos_mapeados'].items():
            print(f"  Tabela Origem: {tabela_origem}")
            for campo_origem, info_campo in campos.items():
                print(f"    {campo_origem} -> {info_campo}")
    
    # 5. Calcular e mostrar tokens
    estimated_tokens = calcular_max_tokens(mapeamentos_compactados)
    print(f"\n--- Análise de Tokens ---")
    print(f"Tokens Estimados: {estimated_tokens}")
    
    # Continuar com o processamento existente
    mapeamentos_tabelas_oc3_para_mesh_filtrado = retorna_selecao_de_tabelas_para_usuario(
        tabelas_alias_map, 
        colunas_usadas, 
        mapeamentos_compactados
    )
    
    tabelas_mapeadas_usuario = registrar_mapeamento_usuario(
        tabelas_alias_map, 
        colunas_usadas, 
        mapeamentos_tabelas_oc3_para_mesh_filtrado
    )
    
    return tabelas_mapeadas_usuario

def retorna_selecao_de_tabelas_para_usuario(tabelas_alias_map, colunas_usadas, mapeamento_tabelas_oc3_para_mesh_total):
    tabelas_match = {}

    for sigla, tabela_oc3 in tabelas_alias_map.items():
        tabelas_match[tabela_oc3] = {}

        for coluna_oc3 in colunas_usadas[sigla]:
            if tabela_oc3 in mapeamento_tabelas_oc3_para_mesh_total and coluna_oc3 in mapeamento_tabelas_oc3_para_mesh_total[tabela_oc3]:
                tabelas_match[tabela_oc3][coluna_oc3] = [{**campos[coluna_oc3], "sigla": sigla} for campos in mapeamento_tabelas_oc3_para_mesh_total[tabela_oc3].values()]

    return tabelas_match

def registrar_mapeamento_usuario(tabelas_alias_map, colunas_usadas, mapeamento_tabelas_oc3_para_mesh_filtrado):
    tabelas_mapeadas = {}

    for sigla, tabela_oc3 in tabelas_alias_map.items():
        tabelas_mapeadas[tabela_oc3] = {}

        for coluna_oc3 in colunas_usadas[sigla]:
            if tabela_oc3 in mapeamento_tabelas_oc3_para_mesh_filtrado and coluna_oc3 in mapeamento_tabelas_oc3_para_mesh_filtrado[tabela_oc3]:
                tabelas_mesh_names = [campos["tabela_data_mesh"] for campos in mapeamento_tabelas_oc3_para_mesh_filtrado[tabela_oc3][coluna_oc3]]

                if len(tabelas_mesh_names) > 1:
                    print("Mais de 1 correspondência OC3 -> Mesh para tabela {} - coluna {}".format(tabela_oc3, coluna_oc3))
                    for i, tabela_mesh in enumerate(tabelas_mesh_names):
                        print("[{}]: {}".format(i, tabela_mesh))
                    print("Digite o índice desejado:")
                    desired_column = int(input())
                    tabelas_mapeadas[tabela_oc3][coluna_oc3] = mapeamento_tabelas_oc3_para_mesh_filtrado[tabela_oc3][coluna_oc3][desired_column]
                else:
                    tabelas_mapeadas[tabela_oc3][coluna_oc3] = mapeamento_tabelas_oc3_para_mesh_filtrado[tabela_oc3][coluna_oc3][0]

            else:
                print("Sem correspondência OC3 -> Mesh para tabela {} - coluna {}".format(tabela_oc3, coluna_oc3))
                tabelas_mapeadas[tabela_oc3][coluna_oc3] = "Nan"

    return tabelas_mapeadas

def processar_query(query, resultados_filtrados):
    tabelas_alias_map = extrair_tabelas_aliases(query)
    colunas_usadas = extrair_colunas_usadas(query, resultados_filtrados)

    json_compactados = compactar_json(resultados_filtrados, tabelas_alias_map, colunas_usadas)

    mapeamentos_tabelas_oc3_para_mesh_filtrado = retorna_selecao_de_tabelas_para_usuario(tabelas_alias_map, colunas_usadas, json_compactados)


    tabelas_mapeadas_usuario = registrar_mapeamento_usuario(tabelas_alias_map, colunas_usadas, mapeamentos_tabelas_oc3_para_mesh_filtrado)


    return tabelas_mapeadas_usuario
