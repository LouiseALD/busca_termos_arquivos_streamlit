# query_converter.py
import json
import re
import boto3
from typing import Dict, List, Any, Optional
from logger_config import setup_logger

logger = setup_logger()

class QueryConverter:
    """Classe base para conversão de queries SQL."""
    
    def __init__(self, bedrock_runtime=None):
        """
        Inicializa o conversor de queries.
        
        Args:
            bedrock_runtime: Cliente do Bedrock Runtime (opcional)
        """
        self.bedrock_runtime = bedrock_runtime
    
    def converter_query(self, query, mapeamentos, contexto_adicional=None):
        """
        Método abstrato para conversão de query.
        
        Args:
            query: Query SQL a ser convertida
            mapeamentos: Mapeamentos a serem utilizados na conversão
            contexto_adicional: Contexto adicional (opcional)
            
        Returns:
            Query SQL convertida
        """
        raise NotImplementedError("Subclasses devem implementar este método")

class OC3ParaDataMeshConverter(QueryConverter):
    """Conversor específico para OC3 para DataMesh."""
    
    def converter_query(self, query, mapeamentos, contexto_adicional=None):
        """
        Converte uma query SQL do padrão OC3 para o padrão DataMesh.
        
        Args:
            query: Query SQL no padrão OC3
            mapeamentos: Mapeamentos a serem utilizados na conversão
            contexto_adicional: Contexto adicional (opcional)
            
        Returns:
            Query SQL convertida para DataMesh
        """
        if self.bedrock_runtime:
            return self._converter_com_bedrock(query, mapeamentos, contexto_adicional)
        else:
            return self._converter_simulado(query, mapeamentos)
    
    def _converter_com_bedrock(self, query, mapeamentos, contexto_adicional=None):
        """Converte usando Bedrock."""
        try:
            # Calcular o max_tokens baseado nos mapeamentos
            max_tokens = self._calcular_max_tokens(mapeamentos)
            
            # Preparar o prompt
            prompt = self._criar_prompt(query, mapeamentos, contexto_adicional)
            
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
            
            # Faz a chamada ao modelo
            response = self.bedrock_runtime.invoke_model(
                modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload).encode("utf-8")
            )
            
            # Processa a resposta
            response_body = json.loads(response["body"].read().decode("utf-8"))
            
            # Extrair a query convertida da resposta
            query_convertida = ""
            if "content" in response_body and len(response_body["content"]) > 0:
                query_convertida = response_body["content"][0]["text"]
                
                # Limpar formatação de código se presente
                if query_convertida.startswith("```") and query_convertida.endswith("```"):
                    linhas = query_convertida.split("\n")
                    if len(linhas) > 2:
                        query_convertida = "\n".join(linhas[1:-1])
                
                # Remover qualquer texto adicional antes ou depois da query
                query_convertida = query_convertida.strip()
                
            return query_convertida
            
        except Exception as e:
            logger.error(f"Erro ao converter query OC3 para DataMesh: {e}")
            return f"Erro na conversão: {str(e)}"
    
    def _converter_simulado(self, query, mapeamentos):
        """Simula a conversão sem usar Bedrock."""
        # Converter a query
        query_convertida = query
        
        # Substituir tabelas com prefixos
        for tabela_oc3, campos in mapeamentos.items():
            # Pegar o primeiro campo para determinar o tipo da tabela
            primeiro_campo = next(iter(campos.values()), {})
            tipo = primeiro_campo.get("tipo", "cadastro")
            tabela_datamesh = primeiro_campo.get("tabela_datamesh", "")
            
            if tabela_datamesh:
                prefixo = "spec_" if tipo == "cadastro" else "hub_"
                
                # Usar regex para substituir apenas o nome completo da tabela
                padrao_tabela = r'\b' + re.escape(tabela_oc3) + r'\b'
                query_convertida = re.sub(padrao_tabela, f"{prefixo}{tabela_datamesh}", query_convertida, flags=re.IGNORECASE)
        
        # Substituir nomes de campos
        for tabela_oc3, campos in mapeamentos.items():
            for campo_oc3, info in campos.items():
                campo_datamesh = info.get("campo_datamesh", "")
                if not campo_datamesh:
                    continue
                    
                # Buscar o padrão tabela.campo ou apenas campo
                padrao_campo_com_tabela = r'\b' + re.escape(tabela_oc3) + r'\.' + re.escape(campo_oc3) + r'\b'
                
# Determinar o prefixo da tabela
                tipo = info.get("tipo", "cadastro")
                tabela_datamesh = info.get("tabela_datamesh", "")
                prefixo = "spec_" if tipo == "cadastro" else "hub_"
                
                # Substituir tabela.campo
                query_convertida = re.sub(
                    padrao_campo_com_tabela, 
                    f"{prefixo}{tabela_datamesh}.{campo_datamesh}", 
                    query_convertida, 
                    flags=re.IGNORECASE
                )
                
                # Substituir campo isolado (se não for palavra reservada)
                # Isto é mais arriscado pois pode substituir palavras incorretamente
                if campo_oc3 not in ["SELECT", "FROM", "WHERE", "AND", "OR", "JOIN", "ON", "GROUP", "BY", "ORDER"]:
                    padrao_campo = r'\b' + re.escape(campo_oc3) + r'\b'
                    query_convertida = re.sub(padrao_campo, campo_datamesh, query_convertida, flags=re.IGNORECASE)
        
        # Substituir funções e sintaxe específicas
        query_convertida = query_convertida.replace("GETDATE()", "current_date")
        query_convertida = re.sub(r'TOP\s+(\d+)', r'LIMIT \1', query_convertida, flags=re.IGNORECASE)
        query_convertida = re.sub(r'ISNULL\(([^,]+),\s*([^)]+)\)', r'COALESCE(\1, \2)', query_convertida, flags=re.IGNORECASE)
        
        # Converter concatenação com + para função concat()
        query_convertida = re.sub(r'(\w+)\s*\+\s*(\w+)', r'concat(\1, \2)', query_convertida)
        
        # Adicionar comentário explicativo
        query_convertida = f"-- Query convertida de OC3 para DataMesh (Presto SQL / Athena)\n{query_convertida}"
        
        return query_convertida
    
    def _criar_prompt(self, query, mapeamentos, contexto_adicional=None):
        """Cria o prompt para o Bedrock."""
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
        {json.dumps(mapeamentos, indent=2)}
        
        Retorne apenas a query convertida em Presto SQL, sem explicações ou comentários adicionais.
        """
        
        return prompt
    
    def _calcular_max_tokens(self, mapeamentos):
        """Calcula o número máximo de tokens baseado nos mapeamentos."""
        # Base de tokens
        base_tokens = 500
        
        # Calcular tokens adicionais baseado nos mapeamentos
        tokens_por_mapeamento = 0
        
        for tabela, campos in mapeamentos.items():
            # Tokens base por tabela
            tokens_por_mapeamento += 50
            
            # Tokens por campos
            tokens_por_mapeamento += len(campos) * 30
        
        # Limitar tokens máximos
        max_tokens = min(base_tokens + tokens_por_mapeamento, 2500)
        
        return max_tokens

class SACParaOC3Converter(QueryConverter):
    """Conversor específico para SAC para OC3."""
    
    def converter_query(self, query, mapeamentos, contexto_adicional=None):
        """
        Converte uma query SQL do padrão SAC para o padrão OC3.
        
        Args:
            query: Query SQL no padrão SAC
            mapeamentos: Mapeamentos a serem utilizados na conversão
            contexto_adicional: Contexto adicional (opcional)
            
        Returns:
            Query SQL convertida para OC3
        """
        if self.bedrock_runtime:
            return self._converter_com_bedrock(query, mapeamentos, contexto_adicional)
        else:
            return self._converter_simulado(query, mapeamentos)
    
    def _converter_com_bedrock(self, query, mapeamentos, contexto_adicional=None):
        """Converte usando Bedrock."""
        try:
            # Calcular o max_tokens baseado nos mapeamentos
            max_tokens = self._calcular_max_tokens(mapeamentos)
            
            # Preparar o prompt
            prompt = self._criar_prompt(query, mapeamentos, contexto_adicional)
            
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
            
            # Faz a chamada ao modelo
            response = self.bedrock_runtime.invoke_model(
                modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload).encode("utf-8")
            )
            
            # Processa a resposta
            response_body = json.loads(response["body"].read().decode("utf-8"))
            
            # Extrair a query convertida da resposta
            query_convertida = ""
            if "content" in response_body and len(response_body["content"]) > 0:
                query_convertida = response_body["content"][0]["text"]
                
                # Limpar formatação de código se presente
                if query_convertida.startswith("```") and query_convertida.endswith("```"):
                    linhas = query_convertida.split("\n")
                    if len(linhas) > 2:
                        query_convertida = "\n".join(linhas[1:-1])
                
                # Remover qualquer texto adicional antes ou depois da query
                query_convertida = query_convertida.strip()
                
            return query_convertida
            
        except Exception as e:
            logger.error(f"Erro ao converter query SAC para OC3: {e}")
            return f"Erro na conversão: {str(e)}"
    
    def _converter_simulado(self, query, mapeamentos):
        """Simula a conversão sem usar Bedrock."""
        # Converter a query
        query_convertida = query
        
        # Substituir tabelas
        for tabela_sac, campos in mapeamentos.items():
            # Pegar o primeiro campo para determinar a tabela OC3
            primeiro_campo = next(iter(campos.values()), {})
            tabela_oc3 = primeiro_campo.get("tabela_datamesh", "")  # A chave ainda é tabela_datamesh no dicionário
            
            if tabela_oc3:
                # Usar regex para substituir apenas o nome completo da tabela
                padrao_tabela = r'\b' + re.escape(tabela_sac) + r'\b'
                query_convertida = re.sub(padrao_tabela, tabela_oc3, query_convertida, flags=re.IGNORECASE)
        
        # Substituir nomes de campos
        for tabela_sac, campos in mapeamentos.items():
            for campo_sac, info in campos.items():
                campo_oc3 = info.get("campo_datamesh", "")  # A chave ainda é campo_datamesh no dicionário
                if not campo_oc3:
                    continue
                    
                # Pegar tabela OC3
                tabela_oc3 = info.get("tabela_datamesh", "")
                
                # Buscar o padrão tabela.campo ou apenas campo
                padrao_campo_com_tabela = r'\b' + re.escape(tabela_sac) + r'\.' + re.escape(campo_sac) + r'\b'
                
                # Substituir tabela.campo
                query_convertida = re.sub(padrao_campo_com_tabela, f"{tabela_oc3}.{campo_oc3}", query_convertida, flags=re.IGNORECASE)
                
                # Substituir campo isolado (se não for palavra reservada)
                if campo_sac not in ["select", "from", "where", "and", "or", "join", "on", "group", "by", "order"]:
                    padrao_campo = r'\b' + re.escape(campo_sac) + r'\b'
                    query_convertida = re.sub(padrao_campo, campo_oc3, query_convertida, flags=re.IGNORECASE)
        
        # Remover prefixo tb_ de tabelas que não estão nos mapeamentos
        query_convertida = re.sub(r'\b(tb_\w+)\b', lambda m: m.group(1).replace('tb_', '').upper(), query_convertida, flags=re.IGNORECASE)
        
        # Adicionar comentário explicativo
        query_convertida = f"-- Query convertida de SAC para OC3\n{query_convertida}"
        
        return query_convertida
    
    def _criar_prompt(self, query, mapeamentos, contexto_adicional=None):
        """Cria o prompt para o Bedrock."""
        prompt = """
        Você é um assistente especializado em conversão de queries SQL.
        
        Instruções:
        1. Converter a query do SAC (SQL Server) para OC3 (SQL)
        2. Substituir nomes de tabelas e colunas conforme o mapeamento fornecido
        3. Para tabelas SAC com prefixo 'tb_', remover este prefixo na OC3 e colocar em maiúsculas
        4. NÃO modificar os prefixos dos campos (como dt_, cd_, vl_, etc) a menos que estejam especificamente listados no mapeamento
        5. Não adicione nada além da query convertida à sua resposta
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
        
        Query original (SAC):
        {query}
        
        Mapeamentos a serem aplicados:
        {json.dumps(mapeamentos, indent=2)}
        
        Retorne apenas a query convertida em OC3, sem explicações ou comentários adicionais.
        """
        
        return prompt
    
    def _calcular_max_tokens(self, mapeamentos):
        """Calcula o número máximo de tokens baseado nos mapeamentos."""
        # Base de tokens
        base_tokens = 500
        
        # Calcular tokens adicionais baseado nos mapeamentos
        tokens_por_mapeamento = 0
        
        for tabela, campos in mapeamentos.items():
            # Tokens base por tabela
            tokens_por_mapeamento += 50
            
            # Tokens por campos
            tokens_por_mapeamento += len(campos) * 30
        
        # Limitar tokens máximos
        max_tokens = min(base_tokens + tokens_por_mapeamento, 2500)
        
        return max_tokens

def criar_conversor(tipo_conversao, bedrock_runtime=None):
    """
    Factory para criar o conversor apropriado.
    
    Args:
        tipo_conversao: Tipo de conversão ('OC3_PARA_DATAMESH' ou 'SAC_PARA_OC3')
        bedrock_runtime: Cliente do Bedrock Runtime (opcional)
        
    Returns:
        Instância do conversor apropriado
    """
    if tipo_conversao == "OC3_PARA_DATAMESH":
        return OC3ParaDataMeshConverter(bedrock_runtime)
    elif tipo_conversao == "SAC_PARA_OC3":
        return SACParaOC3Converter(bedrock_runtime)
    else:
        raise ValueError(f"Tipo de conversão não suportado: {tipo_conversao}")