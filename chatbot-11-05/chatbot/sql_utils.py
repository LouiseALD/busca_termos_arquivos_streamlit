# sql_utils.py
import re
import sqlparse

# Conjunto de palavras-chave reservadas comuns em SQL
SQL_RESERVED_KEYWORDS = {
    "ALL", "ALTER", "AND", "AS", "BETWEEN", "BY", "CASE", "CAST", "CREATE", "CROSS", "DELETE", "DISTINCT", "DROP",
    "ELSE", "END", "EXISTS", "FALSE", "FOR", "FROM", "FULL", "GROUP", "HAVING", "IN", "INNER", "INSERT", "INTERSECT",
    "IS", "JOIN", "LEFT", "LIKE", "LIMIT", "NOT", "NULL", "ON", "ORDER", "OUTER", "RIGHT", "SELECT",
    "SET", "TABLE", "THEN", "TRUE", "UNION", "UPDATE", "USING", "VALUES", "WHERE", "WITH"
}

# Palavras-chave que são válidas em contexto sem precisar de escape
VALID_CONTEXTUAL_KEYWORDS = {
    "SELECT", "FROM", "WHERE", "AND", "JOIN", "ON", "AS", "BETWEEN", "GROUP", "BY",
    "WITH", "HAVING", "ORDER", "INNER", "LEFT", "RIGHT", "OUTER", "CROSS", "IN", "NOT", 
    "LIKE", "IS", "NULL", "DESC", "ASC", "LIMIT", "UNION", "ALL", "DISTINCT", "CASE", 
    "WHEN", "THEN", "ELSE", "END", "EXISTS"
}

def validar_query(query):
    """Valida uma query SQL de forma genérica."""
    # 1. Verificação sintática
    try:
        parsed_query = sqlparse.parse(query)
        if not parsed_query:
            return {"status": "Erro", "mensagem": "A query está vazia ou mal formatada."}
    except Exception as e:
        return {"status": "Erro", "mensagem": f"Erro ao analisar a query: {e}"}

    # 2. Verificar estrutura básica
    if not re.search(r"SELECT\s", query, re.IGNORECASE):
        return {"status": "Erro", "mensagem": "Query inválida: falta a cláusula SELECT"}
    if not re.search(r"FROM\s", query, re.IGNORECASE):
        return {"status": "Erro", "mensagem": "Query inválida: falta a cláusula FROM"}

    # Se passou por todas as validações
    return {"status": "Sucesso", "mensagem": "A query é válida"}

def validar_query_simplificada(query):
    """Versão simplificada da validação para contornar problemas com LIKE."""
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

def extrair_elementos_query(query):
    """
    Extrai tabelas e campos de uma query SQL.
    
    Args:
        query: Query SQL a ser analisada
        
    Returns:
        Dicionário com tabelas e campos extraídos
    """
    # Extrair tabelas usando regex mais abrangente
    tabela_match = re.findall(r'(?:FROM|JOIN)\s+(\w+)', query, re.IGNORECASE)
    tabelas = [tabela.upper() for tabela in tabela_match if tabela]

    # Extrair campos
    campos_match = re.findall(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
    campos = []
    
    if campos_match:
        campos_str = campos_match[0]
        # Dividir por vírgula, respeitando parênteses
        campos_raw = re.findall(r'([^,]+(?:\([^)]*\)[^,]*)?)', campos_str)
        
        for campo_raw in campos_raw:
            # Extrair o nome do campo, removendo aliases e referências de tabela
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
    
    # Filtrar palavras reservadas
    palavras_reservadas = {"SELECT", "FROM", "WHERE", "JOIN", "ON", "AND", "OR", "GROUP", "ORDER", "BY", "HAVING", "AS", "IS", "NOT", "NULL", "LIKE", "BETWEEN", "IN", "DESC", "ASC"}
    campos_filtrados = [campo for campo in campos if campo.upper() not in palavras_reservadas]
    
    return {
        "tabelas": tabelas,
        "campos": campos_filtrados
    }

def extrair_tabelas_aliases(query):
    """Extrai tabelas e seus aliases de uma query SQL."""
    padrao_tabela_alias = re.findall(r"FROM\s+(\w+)(?:\s+AS)?(?:\s+(\w+))?|JOIN\s+(\w+)(?:\s+AS)?(?:\s+(\w+))?", query, re.IGNORECASE)
    tabela_alias_dict = {}

    for match in padrao_tabela_alias:
        # Formato: (FROM_tabela, FROM_alias, JOIN_tabela, JOIN_alias)
        tabela_real = match[0] if match[0] else match[2]
        alias = match[1] if match[1] else match[3]
        
        if tabela_real:
            if alias:
                tabela_alias_dict[alias] = tabela_real
            else:
                # Se não tem alias, usa a própria tabela como chave
                tabela_alias_dict[tabela_real] = tabela_real

    return tabela_alias_dict

def extrair_colunas_usadas(query):
    """Extrai colunas usadas em uma query SQL."""
    colunas_usadas = {}

    # Extrair colunas com prefixo de tabela/alias
    matches = re.findall(r"(\w+)\.(\w+)", query)
    matches = [(a.upper(), b.upper()) for (a, b) in matches]

    for alias, coluna in matches:
        if alias not in colunas_usadas:
            colunas_usadas[alias] = set()
        colunas_usadas[alias].add(coluna)

    # Extrair colunas sem prefixo
    colunas_isoladas = re.findall(r"SELECT\s+(.*?)\s+FROM", query, re.IGNORECASE | re.DOTALL)
    if colunas_isoladas:
        # Dividir por vírgula, respeitando parênteses
        campos_raw = re.findall(r'([^,]+(?:\([^)]*\)[^,]*)?)', colunas_isoladas[0])
        
        for campo_raw in campos_raw:
            # Ignorar se tem um alias de tabela (já foi capturado acima)
            if '.' not in campo_raw:
                # Extrair o nome do campo, removendo AS e funções
                campo_limpo = re.sub(r'([a-zA-Z0-9_]+)(?:\s+AS\s+[a-zA-Z0-9_]+)?', r'\1', campo_raw.strip())
                # Ignorar funções
                if not re.match(r'^[A-Za-z0-9_]+\(', campo_limpo):
                    if "sem_alias" not in colunas_usadas:
                        colunas_usadas["sem_alias"] = set()
                    colunas_usadas["sem_alias"].add(campo_limpo.upper())

    return colunas_usadas