# config.py
"""
Arquivo de configuração central para o Assistente de Conversão SQL.
Todas as configurações do aplicativo são definidas aqui para fácil manutenção.
"""

# Configurações de caminhos para mapeamentos
PATH_CONFIG = {
    "MAPEAMENTOS_BASE": "mapeamentos-de-para",
    "MAPEAMENTOS_OC3_DATAMESH": "mapeamentos-de-para/mapeamentos-oc3-datamesh",
    "MAPEAMENTOS_SAC_OC3": "mapeamentos-de-para/mapeamentos-sac-oc3"
}

# Configurações do Bedrock
BEDROCK_CONFIG = {
    "MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0",  # ID do modelo Claude no Bedrock
    "REGION_NAME": "us-east-1",                   # Região AWS do Bedrock
    "MAX_TOKENS_BASE": 500,                       # Tokens base para respostas
    "MAX_TOKENS_MAX": 2500                       # Máximo de tokens para respostas
}

# Configurações da interface do usuário
UI_CONFIG = {
    "TITULO_APP": "Assistente De Conversão SQL",
    "TEMA_COR_PRIMARIA": "#ffd966",               # Cor primária para temas
    "TEMA_COR_SECUNDARIA": "#e8f0fe"              # Cor secundária para temas
}

# Configurações de logging
LOGGING_CONFIG = {
    "LEVEL": "INFO",                               # Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    "FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Formato das mensagens de log
    "LOG_FILE": "assistente_sql.log"               # Nome do arquivo de log (opcional)
}


# Configurações gerais do aplicativo
APP_CONFIG = {
    "VERSAO": "1.0.0",
    "MOSTRAR_VERSAO": True,
    "MODO_DEBUG": False,
    "TEMPO_CACHE": 3600  # Tempo em segundos para manter os mapeamentos em cache
}