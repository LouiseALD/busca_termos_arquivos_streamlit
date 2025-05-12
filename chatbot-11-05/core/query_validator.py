import os
import sys
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
    print("Função validar query chamada")

    # 1. Verificação sintática
    try:
        parsed_query = sqlparse.parse(query)
        if not parsed_query:
            return {"status": "Erro", "mensagem": "A query está vazia ou mal formatada."}
    except Exception as e:
        return {"status": "Erro", "mensagem": f"Erro ao analisar a query: {e}"}

    # 2. Verificar palavras-chave reservadas não escapadas
    tokens = set(re.findall(r"\b[A-Za-z_]+\b", query.upper()))
    print("Tokens encontrados:", tokens)
    invalid_tokens = [token for token in tokens if token in SQL_RESERVED_KEYWORDS and f"`{token}`" not in query]
    invalid_tokens = [token for token in invalid_tokens if token not in VALID_CONTEXTUAL_KEYWORDS]
    print("Tokens inválidos:", invalid_tokens)

    if invalid_tokens:
        return {"status": "Erro", "mensagem": f"Palavras-chave reservadas precisam ser escapadas com acentos graves: {invalid_tokens}"}

    # 3. Validar estrutura básica
    if not re.search(r"SELECT\s", query, re.IGNORECASE):
        return {"status": "Erro", "mensagem": "Query inválida: falta a cláusula SELECT"}
    if not re.search(r"FROM\s", query, re.IGNORECASE):
        return {"status": "Erro", "mensagem": "Query inválida: falta a cláusula FROM"}

    # 4. Validar tabelas e colunas
    tabelas = re.findall(r"(?:FROM|JOIN)\s+(\S+)", query, re.IGNORECASE)
    colunas = re.findall(r"SELECT\s+(.*?)\s+FROM", query, re.IGNORECASE | re.DOTALL)
    print("Tabelas encontradas:", tabelas)
    print("Colunas encontradas antes do split:", colunas)

    if colunas:
        # Ajuste para lidar com colunas complexas e funções
        colunas = [col.strip() for col in re.split(r",\s*(?![^(]*\))", colunas[0]) if col.strip()]
        print("Colunas encontradas após o split:", colunas)

    if not tabelas:
        return {"status": "Erro", "mensagem": "Nenhuma tabela encontrada na Query"}
    if not colunas:
        return {"status": "Erro", "mensagem": "Nenhuma coluna encontrada na Query"}

    # Se passou por todas as validações
    return {"status": "Sucesso", "mensagem": "A query é válida"}

def lambda_handler(event, _context):
    """Função Lambda para processar a query"""
    query = sys.stdin.read()  # Lê a query da entrada padrão
    if not query:
        return {"error": "Nenhuma query informada"}

    resultado_sql = validar_query(query)
    print(resultado_sql)
    return resultado_sql

# Chamada da função Lambda
if __name__ == "__main__":
    lambda_handler(None, None)