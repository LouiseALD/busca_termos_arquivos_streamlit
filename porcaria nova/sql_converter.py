# sql_converter.py
import re
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class SQLConverter:
    """
    Classe para converter queries SQL entre diferentes sistemas,
    usando mapeamentos de tabelas e campos.
    """
    
    def __init__(self, bedrock_client=None):
        """
        Inicializa o conversor.
        
        Args:
            bedrock_client: Cliente do Bedrock para conversão assistida por IA (opcional)
        """
        self.bedrock_client = bedrock_client
    
    def converter_query(self, 
                        query: str, 
                        mapeamentos_agrupados: Dict[str, Dict[str, Dict[str, Any]]], 
                        tipo_conversao: str,
                        contexto_adicional: Optional[str] = None) -> str:
        """
        Converte uma query SQL usando os mapeamentos fornecidos.
        
        Args:
            query: Query SQL a ser convertida
            mapeamentos_agrupados: Mapeamentos agrupados por tabela e campo
            tipo_conversao: Tipo de conversão ('OC3_PARA_DATAMESH' ou 'SAC_PARA_OC3')
            contexto_adicional: Contexto adicional para a conversão (opcional)
            
        Returns:
            Query SQL convertida
        """
        if self.bedrock_client and self._verificar_bedrock_disponivel():
            # Usar IA para fazer a conversão
            return self._converter_com_bedrock(query, mapeamentos_agrupados, tipo_conversao, contexto_adicional)
        else:
            # Usar conversão baseada em regras (fallback)
            return self._converter_com_regras(query, mapeamentos_agrupados, tipo_conversao)
    
    def _verificar_bedrock_disponivel(self) -> bool:
        """Verifica se o cliente Bedrock está disponível e funcionando."""
        if not self.bedrock_client:
            return False
            
        try:
            # Testar com uma chamada simples
            self.bedrock_client.get_model_invoke_settings(modelId="anthropic.claude-3-sonnet-20240229-v1:0")
            return True
        except Exception as e:
            logger.warning(f"Bedrock não disponível: {e}")
            return False
    
    def _converter_com_bedrock(self, 
                              query: str, 
                              mapeamentos_agrupados: Dict[str, Dict[str, Dict[str, Any]]], 
                              tipo_conversao: str,
                              contexto_adicional: Optional[str] = None) -> str:
        """
        Converte a query usando o modelo Bedrock Claude.
        
        Args:
            query: Query SQL a ser convertida
            mapeamentos_agrupados: Mapeamentos agrupados por tabela e campo
            tipo_conversao: Tipo de conversão
            contexto_adicional: Contexto adicional (opcional)
            
        Returns:
            Query SQL convertida
        """
        try:
            # Calcular o max_tokens baseado na complexidade dos mapeamentos
            max_tokens = self._calcular_max_tokens(mapeamentos_agrupados)
            
            # Criar prompt apropriado para o tipo de conversão
            prompt = self._criar_prompt(query, mapeamentos_agrupados, tipo_conversao, contexto_adicional)
            
            # Preparar payload para a chamada ao Bedrock
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
            
            # Fazer a chamada ao modelo
            response = self.bedrock_client.invoke_model(
                modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload).encode("utf-8")
            )
            
            # Processar a resposta
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
            logger.error(f"Erro ao converter query com Bedrock: {e}")
            # Em caso de erro, fallback para conversão baseada em regras
            return self._converter_com_regras(query, mapeamentos_agrupados, tipo_conversao)
    
    def _criar_prompt(self, 
                     query: str, 
                     mapeamentos_agrupados: Dict[str, Dict[str, Dict[str, Any]]], 
                     tipo_conversao: str,
                     contexto_adicional: Optional[str] = None) -> str:
        """
        Cria o prompt para o modelo Bedrock.
        
        Args:
            query: Query SQL a ser convertida
            mapeamentos_agrupados: Mapeamentos agrupados por tabela e campo
            tipo_conversao: Tipo de conversão
            contexto_adicional: Contexto adicional (opcional)
            
        Returns:
            Prompt formatado para o modelo
        """
        if tipo_conversao == "OC3_PARA_DATAMESH":
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
        else:  # SAC_PARA_OC3
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
            
            Query original:
            {query}
            
            Mapeamentos a serem aplicados:
            {json.dumps(mapeamentos_agrupados, indent=2)}
            
            Retorne apenas a query convertida, sem explicações ou comentários adicionais.
            """
        
        return prompt
    
    def _calcular_max_tokens(self, mapeamentos_agrupados: Dict[str, Dict[str, Dict[str, Any]]]) -> int:
        """
        Calcula o número máximo de tokens baseado na complexidade dos mapeamentos.
        
        Args:
            mapeamentos_agrupados: Mapeamentos agrupados por tabela e campo
            
        Returns:
            Número máximo de tokens
        """
        # Base de tokens
        base_tokens = 500
        
        # Calcular tokens adicionais baseado nos mapeamentos
        tokens_por_mapeamento = 0
        
        for tabela, campos in mapeamentos_agrupados.items():
            # Tokens base por tabela
            tokens_por_mapeamento += 50
            
            # Tokens por campos
            tokens_por_mapeamento += len(campos) * 30
        
        # Limitar tokens máximos
        max_tokens = min(base_tokens + tokens_por_mapeamento, 2500)
        
        return max_tokens
    
    def _converter_com_regras(self, 
                             query: str, 
                             mapeamentos_agrupados: Dict[str, Dict[str, Dict[str, Any]]], 
                             tipo_conversao: str) -> str:
        """
        Converte a query usando regras baseadas nos mapeamentos.
        
        Args:
            query: Query SQL a ser convertida
            mapeamentos_agrupados: Mapeamentos agrupados por tabela e campo
            tipo_conversao: Tipo de conversão
            
        Returns:
            Query SQL convertida
        """
        # Clonar a query original
        query_convertida = query
        
        if tipo_conversao == "OC3_PARA_DATAMESH":
            # Converter de OC3 para DataMesh
            
            # Substituir tabelas com prefixos
            for tabela_oc3, campos in mapeamentos_agrupados.items():
                # Pegar o primeiro campo para determinar o tipo da tabela
                primeiro_campo = next(iter(campos.values()), {})
                tipo = primeiro_campo.get("tipo", "cadastro")
                tabela_datamesh = primeiro_campo.get("tabela_destino", "")
                
                if tabela_datamesh:
                    prefixo = "spec_" if tipo == "cadastro" else "hub_"
                    
                    # Usar regex para substituir apenas o nome completo da tabela
                    padrao_tabela = r'\b' + re.escape(tabela_oc3) + r'\b'
                    query_convertida = re.sub(padrao_tabela, f"{prefixo}{tabela_datamesh}", query_convertida, flags=re.IGNORECASE)
            
            # Substituir nomes de campos
            for tabela_oc3, campos in mapeamentos_agrupados.items():
                for campo_oc3, info in campos.items():
                    campo_datamesh = info.get("campo_destino", "")
                    if not campo_datamesh:
                        continue
                        
                    # Buscar o padrão tabela.campo ou apenas campo
                    padrao_campo_com_tabela = r'\b' + re.escape(tabela_oc3) + r'\.' + re.escape(campo_oc3) + r'\b'
                    
                    # Determinar o prefixo da tabela
                    tipo = info.get("tipo", "cadastro")
                    tabela_datamesh = info.get("tabela_destino", "")
                    prefixo = "spec_" if tipo == "cadastro" else "hub_"
                    
                    # Substituir tabela.campo
                    query_convertida = re.sub(
                        padrao_campo_com_tabela, 
                        f"{prefixo}{tabela_datamesh}.{campo_datamesh}", 
                        query_convertida, 
                        flags=re.IGNORECASE
                    )
                    
                    # Substituir campo isolado (se não for palavra reservada)
                    palavras_reservadas = ["SELECT", "FROM", "WHERE", "AND", "OR", "JOIN", "ON", "GROUP", "BY", "ORDER"]
                    if campo_oc3.upper() not in palavras_reservadas:
                        padrao_campo = r'\b' + re.escape(campo_oc3) + r'\b'
                        query_convertida = re.sub(padrao_campo, campo_datamesh, query_convertida, flags=re.IGNORECASE)
            
            # Substituir funções e sintaxe específicas
            query_convertida = query_convertida.replace("GETDATE()", "current_date")
            query_convertida = re.sub(r'TOP\s+(\d+)', r'LIMIT \1', query_convertida, flags=re.IGNORECASE)
            query_convertida = re.sub(r'ISNULL\(([^,]+),\s*([^)]+)\)', r'COALESCE(\1, \2)', query_convertida, flags=re.IGNORECASE)
            query_convertida = re.sub(r'(\w+)\s*\+\s*(\w+)', r'concat(\1, \2)', query_convertida)
            
            # Adicionar comentário explicativo
            query_convertida = f"-- Query convertida de OC3 para DataMesh (Presto SQL / Athena)\n{query_convertida}"
            
        else:  # SAC_PARA_OC3
            # Converter de SAC para OC3
            
            # Substituir tabelas
            for tabela_sac, campos in mapeamentos_agrupados.items():
                # Pegar o primeiro campo para determinar a tabela OC3
                primeiro_campo = next(iter(campos.values()), {})
                tabela_oc3 = primeiro_campo.get("tabela_destino", "")
                
                if tabela_oc3:
                    # Usar regex para substituir apenas o nome completo da tabela
                    padrao_tabela = r'\b' + re.escape(tabela_sac) + r'\b'
                    query_convertida = re.sub(padrao_tabela, tabela_oc3, query_convertida, flags=re.IGNORECASE)
            
            # Substituir nomes de campos
            for tabela_sac, campos in mapeamentos_agrupados.items():
                for campo_sac, info in campos.items():
                    campo_oc3 = info.get("campo_destino", "")
                    if not campo_oc3:
                        continue
                        
                    # Pegar tabela OC3
                    tabela_oc3 = info.get("tabela_destino", "")
                    
                    # Buscar o padrão tabela.campo ou apenas campo
                    padrao_campo_com_tabela = r'\b' + re.escape(tabela_sac) + r'\.' + re.escape(campo_sac) + r'\b'
                    
                    # Substituir tabela.campo
                    query_convertida = re.sub(padrao_campo_com_tabela, f"{tabela_oc3}.{campo_oc3}", query_convertida, flags=re.IGNORECASE)
                    
                    # Substituir campo isolado (se não for palavra reservada)
                    palavras_reservadas = ["select", "from", "where", "and", "or", "join", "on", "group", "by", "order"]
                    if campo_sac.lower() not in palavras_reservadas:
                        padrao_campo = r'\b' + re.escape(campo_sac) + r'\b'
                        query_convertida = re.sub(padrao_campo, campo_oc3, query_convertida, flags=re.IGNORECASE)
            
            # Remover prefixo tb_ de tabelas que não estão nos mapeamentos
            query_convertida = re.sub(r'\b(tb_\w+)\b', lambda m: m.group(1).replace('tb_', '').upper(), query_convertida, flags=re.IGNORECASE)
            
            # Adicionar comentário explicativo
            query_convertida = f"-- Query convertida de SAC para OC3\n{query_convertida}"
            
        return query_convertida