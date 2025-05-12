# utils.py
import random
import re

def responder_com_bedrock(mensagem):
    """Simula respostas do Bedrock para testes da interface"""
    
    # Verifica se a mensagem parece uma query SQL
    if re.search(r'SELECT|FROM|UPDATE|INSERT|DELETE|CREATE|ALTER', mensagem, re.IGNORECASE):
        # Simular resposta para uma query SQL
        return {
            "status": "needs_selection",
            "request_id": f"request-{random.randint(1000, 9999)}",
            "message": "Encontrei múltiplas possibilidades de mapeamento para sua query."
        }
    
    # Para mensagens normais
    respostas = [
        "Entendi! Pode me contar mais?",
        "Ótima pergunta! O que mais você gostaria de saber?",
        "Interessante! Quer explorar outro tópico?",
        "Muito bom! Você quer mais detalhes sobre isso?",
        "Legal! Como posso te ajudar mais?"
    ]
    return random.choice(respostas)

def simular_opcoes_mapeamento():
    """Simula opções de mapeamento para testes"""
    return [
        {
            "id": "map1",
            "tipo": "cadastro",
            "TABELA OC3 LIGHT": "CLIENTE",
            "TABELA DATA MESH": "clientes",
            "CAMPO OC3 LIGHT": "ID_CLIENTE",
            "CAMPO DATA MESH FINAL": "cliente_id"
        },
        {
            "id": "map2",
            "tipo": "hub",
            "TABELA OC3 LIGHT": "PEDIDO",
            "TABELA DATA MESH": "pedidos",
            "CAMPO OC3 LIGHT": "ID_PEDIDO",
            "CAMPO DATA MESH FINAL": "pedido_id"
        },
        {
            "id": "map3",
            "tipo": "cadastro",
            "TABELA OC3 LIGHT": "PRODUTO",
            "TABELA DATA MESH": "produtos",
            "CAMPO OC3 LIGHT": "ID_PRODUTO",
            "CAMPO DATA MESH FINAL": "produto_id"
        }
    ]

def simular_resultado_conversao(query):
    """Simula o resultado de uma conversão para testes"""
    
    # Cria uma query convertida simulada baseada na original
    result_query = "-- Query convertida automaticamente\n"
    
    # Verificar se contém SELECT e FROM
    if "SELECT" in query.upper() and "FROM" in query.upper():
        # Extrai elementos básicos da query
        tables = re.findall(r'FROM\s+(\w+)', query, re.IGNORECASE)
        
        if tables:
            table_name = tables[0]
            if table_name.upper() == "CLIENTE":
                result_query += "SELECT c.cliente_id, c.nome_completo\nFROM spec_clientes AS c\nWHERE c.status_cliente = 'ATIVO'"
            elif table_name.upper() == "PEDIDO":
                result_query += "SELECT p.pedido_id, p.data_criacao, p.valor_total\nFROM hub_pedidos AS p\nWHERE p.cliente_id = 1001"
            else:
                result_query += f"SELECT id\nFROM {'spec_' if table_name.upper() != 'ITEM_PEDIDO' else 'hub_'}{table_name.lower()}\nWHERE status = 'ATIVO'"
        else:
            result_query += "SELECT c.cliente_id, c.nome_completo\nFROM spec_clientes AS c\nWHERE c.status_cliente = 'ATIVO'"
    else:
        result_query += "SELECT c.cliente_id, c.nome_completo\nFROM spec_clientes AS c\nWHERE c.status_cliente = 'ATIVO'"
    
    return {
        "status": "completed",
        "result": result_query
    }