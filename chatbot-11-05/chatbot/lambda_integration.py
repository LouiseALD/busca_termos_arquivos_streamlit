# chatbot/lambda_integration.py
import json
from typing import Dict, List, Any, Optional
import boto3
import os

from logger_config import setup_logger
logger = setup_logger()

class LambdaInvoker:
    """
    Classe responsável por invocar funções Lambda para integração com Bedrock.
    """
    
    def __init__(self, region="us-east-1"):
        """
        Inicializa o invocador Lambda com credenciais AWS.
        
        Args:
            region: Região AWS para o Lambda (padrão: us-east-1)
        """
        try:
            # Configurar o cliente Lambda usando boto3
            self.lambda_client = boto3.client(
                'lambda',
                region_name=region,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                aws_session_token=os.getenv("AWS_SESSION_TOKEN")
            )
            self.is_available = True
        except Exception as e:
            logger.error(f"Não foi possível configurar o cliente Lambda: {e}")
            self.is_available = False
    
def invocar_lambda_bedrock(self, function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoca uma função Lambda para processamento com Bedrock.
    
    Args:
        function_name: Nome da função Lambda a ser invocada
        payload: Dicionário contendo dados para a função Lambda
            
    Returns:
        Resposta da função Lambda
    """
    if not self.is_available:
        return {
            "status": "error",
            "error": "Cliente Lambda não disponível",
            "message": "Usando modo de simulação para converter a query."
        }
    
    try:
        print("Preparando payload para Lambda...")
        # Garantir que o payload esteja no formato adequado
        if "mapeamentos" in payload and isinstance(payload["mapeamentos"], list):
            print("Payload contém lista de mapeamentos. Convertendo para formato agrupado...")
            from chatbot.converters.conversion_utils import agrupar_mapeamentos_para_lambda
            payload["mapeamentos"] = agrupar_mapeamentos_para_lambda(payload["mapeamentos"])
            print("Conversão para formato agrupado concluída.")
            
        # Serializar o payload para JSON
        payload_json = json.dumps(payload)
        print(f"Payload serializado. Tamanho: {len(payload_json)} bytes")
        
        print(f"Invocando Lambda function: {function_name}")
        # Invocar a função Lambda
        response = self.lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',  # Síncrono
            Payload=payload_json.encode('utf-8')
        )
        
        print("Resposta recebida da Lambda. Processando...")
        # Processar a resposta
        payload_response = json.loads(response['Payload'].read().decode('utf-8'))
        
        # Verificar por erros na resposta
        if 'FunctionError' in response:
            print(f"Erro detectado na resposta Lambda: {response.get('FunctionError')}")
            return {
                "status": "error",
                "error": "Erro na função Lambda",
                "message": str(payload_response)
            }
        
        print("Resposta Lambda processada com sucesso.")
        return payload_response
            
    except Exception as e:
        print(f"Erro ao invocar Lambda: {e}")
        import traceback
        print(traceback.format_exc())
        return {
            "status": "error",
            "error": str(e),
            "message": "Não foi possível processar a requisição Lambda."
        }


# Função auxiliar para verificar status da conexão com AWS
def verificar_lambda_disponivel() -> bool:
    """
    Verifica se a integração com Lambda está disponível.
    
    Returns:
        Booleano indicando se a integração está disponível
    """
    try:
        invoker = LambdaInvoker()
        return invoker.is_available
    except Exception as e:
        logger.error(f"Erro ao verificar disponibilidade do Lambda: {e}")
        return False