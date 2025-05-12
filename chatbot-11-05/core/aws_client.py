import json
from logger_config import setup_logger
logger = setup_logger()
from typing import List, Dict
import time

def calcular_max_tokens(json_mappings: List[Dict]) -> int:
    """Calcula o número máximo de tokens baseado nos mapeamentos JSON fornecidos.

    :param json_mappings: Lista de dicionários contendo mapeamentos JSON.
    :return: Número máximo de tokens calculado.
    """
    num_items = sum(len(item) for item in json_mappings)
    base_tokens = 500
    dynamic_tokens = num_items * 10
    max_tokens = min(2500, base_tokens + dynamic_tokens)
    return max_tokens

def converter_query_oc3_para_datamesh(bedrock_runtime, query: str, json_mappings: List[Dict], contexto_adicional: str = None) -> str:
    """Converte uma query SQL do padrão OC3 para o padrão Datamesh usando os mapeamentos JSON.

    :param bedrock_runtime: Cliente do Bedrock Runtime
    :param query: Query SQL no padrão OC3.
    :param json_mappings: Lista de dicionários contendo mapeamentos JSON.
    :param contexto_adicional: Mensagem original completa do usuário (opcional).
    :return: Query SQL convertida para o padrão Datamesh.
    """
    try:
        # Atualiza o payload para usar o novo prompt e a query fornecida
        prompt = """
        Você é um assistente especializado em conversão de queries SQL.
        
        Instruções:
        1. Converter a query de T-SQL (SQL Server) para Presto SQL (Amazon Athena)
        2. Substituir nomes de tabelas e colunas conforme o mapeamento fornecido
        3. Para tabelas do tipo "cadastro", adicionar o prefixo "spec_"
        4. Para tabelas do tipo "hub", adicionar o prefixo "hub_"
        5. Se não existir mapeamento para uma tabela ou coluna, mantenha o original
        6. NÃO modifique os prefixos originais dos campos (como ID_, DATA_, etc) a menos que estejam explicitamente mapeados
        7. Ajustar sintaxe específica como:
           - GETDATE() -> current_date
           - DATEADD -> usar intervalo padrão do Presto
           - Concatenação com + -> função concat()
           - ISNULL -> COALESCE
           - TOP N -> LIMIT N
        8. Não adicione nada além da query convertida à sua resposta
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
        
        Query original (T-SQL):
        {query}
        
        Mapeamentos a serem aplicados:
        {json.dumps(json_mappings, indent=2)}
        
        Retorne apenas a query convertida em Presto SQL, sem explicações ou comentários adicionais.
        """

        # Calcula o max_tokens baseado nos mapeamentos
        max_tokens = calcular_max_tokens(json_mappings)

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

        start_time = time.time()

        # Faz a chamada ao modelo
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",  # Certifique-se de usar o ID correto do modelo
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload).encode("utf-8")
        )

        end_time = time.time()
        response_time = end_time - start_time
        print(f"Tempo de resposta da API do bedrock: {response_time:.2f} segundos")

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
        print("Erro ao processar a query com Bedrock:")
        print(e)
        return f"Erro ao processar a query: {str(e)}"