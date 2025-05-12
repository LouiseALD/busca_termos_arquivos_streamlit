# check_config.py
import os

# Verificar se o arquivo config.py existe
try:
    from config import S3_CONFIG, PATH_CONFIG
    print("✅ Arquivo config.py encontrado!")
    
    # Verificar configurações S3
    print("\nConfiguração S3 atual:")
    print(f"BUCKET_NAME: {S3_CONFIG.get('BUCKET_NAME', 'não definido')}")
    print(f"REGION_NAME: {S3_CONFIG.get('REGION_NAME', 'não definido')}")
    print(f"PREFIX_OC3_DATAMESH: {S3_CONFIG.get('PREFIX_OC3_DATAMESH', 'não definido')}")
    print(f"PREFIX_SAC_OC3: {S3_CONFIG.get('PREFIX_SAC_OC3', 'não definido')}")
    print(f"USAR_S3: {S3_CONFIG.get('USAR_S3', 'não definido')}")
    
    if not S3_CONFIG.get("USAR_S3", False):
        print("\n⚠️ AVISO: O uso do S3 está DESABILITADO no arquivo config.py!")
        print("Para habilitar, edite config.py e defina S3_CONFIG['USAR_S3'] = True")
    
except ImportError:
    print("❌ Arquivo config.py não encontrado!")
    
# Verificar variáveis de ambiente AWS
access_key = os.environ.get("AWS_ACCESS_KEY_ID")
secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
session_token = os.environ.get("AWS_SESSION_TOKEN")

print("\nVariáveis de ambiente AWS:")
print(f"AWS_ACCESS_KEY_ID: {'✅ Configurado' if access_key else '❌ Não configurado'}")
print(f"AWS_SECRET_ACCESS_KEY: {'✅ Configurado' if secret_key else '❌ Não configurado'}")
print(f"AWS_SESSION_TOKEN: {'✅ Configurado' if session_token else '⚠️ Não configurado (opcional)'}")

if not access_key or not secret_key:
    print("\n⚠️ AVISO: Credenciais AWS não configuradas corretamente!")
    print("Configure as variáveis de ambiente AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY")