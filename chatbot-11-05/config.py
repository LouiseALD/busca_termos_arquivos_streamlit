# config.py
"""
Arquivo de configuração central para o aplicativo.
Aqui são definidas todas as configurações que podem precisar ser ajustadas.
"""

# Configuração de caminhos de mapeamentos
BASE_PATH = "/app/src/mapeamentos-de-para"  # Mude apenas esta linha para alterar todos os caminhos
PATH_CONFIG = {
    "MAPEAMENTOS_BASE": BASE_PATH,
    "MAPEAMENTOS_OC3_DATAMESH": f"{BASE_PATH}/mapeamentos-oc3-datamesh",
    "MAPEAMENTOS_SAC_OC3": f"{BASE_PATH}/mapeamentos-sac-oc3"
}

# Configurações do Bedrock
BEDROCK_CONFIG = {
    "MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0",
    "REGION_NAME": "us-east-1",
    "MAX_TOKENS_BASE": 500,
    "MAX_TOKENS_MAX": 2500
}

# Interface do usuário
UI_CONFIG = {
    "TITULO_APP": "Assistente De Conversão SQL",
    "TEMA_COR_PRIMARIA": "#ffd966",
    "TEMA_COR_SECUNDARIA": "#e8f0fe"
}