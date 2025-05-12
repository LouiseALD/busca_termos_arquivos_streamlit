# mapeamento_loader.py
import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class MapeamentoLoader:
    """
    Classe centralizada para carregar e gerenciar arquivos de mapeamento.
    Simplifica o processo de busca e carregamento de arquivos JSON.
    """

    def __init__(self, base_path: str = "mapeamentos-de-para"):
        """
        Inicializa o carregador de mapeamentos.
        
        Args:
            base_path: Caminho base para os diretórios de mapeamentos
        """
        self.base_path = base_path
        self.cache = {}
        
        # Caminhos para os diferentes tipos de mapeamentos
        self.caminhos = {
            "OC3_PARA_DATAMESH": os.path.join(base_path, "mapeamentos-oc3-datamesh"),
            "SAC_PARA_OC3": os.path.join(base_path, "mapeamentos-sac-oc3")
        }
        
        # Verificar diretórios
        self._criar_diretorios()
    
    def _criar_diretorios(self):
        """Verifica se os diretórios de mapeamentos existem e reporta erros."""
        # Verificar diretório base
        if not os.path.exists(self.base_path):
            logger.error(f"Diretório base não encontrado: {self.base_path}")
            return False
            
        # Verificar subdiretórios para cada tipo de conversão
        for tipo, caminho in self.caminhos.items():
            if not os.path.exists(caminho):
                logger.error(f"Diretório de mapeamento '{tipo}' não encontrado: {caminho}")
                return False
        
        # Se chegou até aqui, todos os diretórios existem
        logger.info("Todos os diretórios de mapeamento foram encontrados")
        return True
    
    def carregar_mapeamentos(self, tipo_conversao: str) -> List[Dict[str, Any]]:
        """
        Carrega todos os mapeamentos para um tipo de conversão específico.
        
        Args:
            tipo_conversao: Tipo de conversão ('OC3_PARA_DATAMESH' ou 'SAC_PARA_OC3')
            
        Returns:
            Lista de mapeamentos carregados
        """
        # Usar cache se disponível
        if tipo_conversao in self.cache:
            return self.cache[tipo_conversao]
        
        # Obter o caminho correto
        caminho = self.caminhos.get(tipo_conversao)
        if not caminho:
            logger.error(f"Tipo de conversão desconhecido: {tipo_conversao}")
            return []
        
        # Verificar se o diretório existe
        if not os.path.exists(caminho):
            logger.error(f"Diretório de mapeamentos não encontrado: {caminho}")
            return []
        
        mapeamentos = []
        arquivos_processados = 0
        arquivos_json = []
        logger.info(f"Iniciando busca em: {caminho}")

        # Buscar todos os arquivos JSON no diretório e subdiretórios
        for root, dirs, files in os.walk(caminho):
            logger.info(f"Verificando diretório: {root}")
            logger.info(f"Subdiretórios: {dirs}")
            logger.info(f"Arquivos: {files}")
            
            for file in files:
                if file.endswith(".json"):
                    arquivo_path = os.path.join(root, file)
                    logger.info(f"Arquivo JSON encontrado: {arquivo_path}")
                    arquivos_json.append(arquivo_path)

        if not arquivos_json:
            logger.warning(f"Nenhum arquivo JSON encontrado no diretório: {caminho}")
            return []
            
        # Processar cada arquivo JSON encontrado
        for arquivo_path in arquivos_json:
            try:
                logger.info(f"Tentando processar arquivo: {arquivo_path}")
                with open(arquivo_path, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    logger.info(f"Arquivo carregado com sucesso: {arquivo_path}")
                    
                    # Processar diferentes formatos de arquivo
                    if isinstance(dados, list):
                        logger.info(f"Formato de lista direta em: {arquivo_path}")
                        # Formato de lista direta
                        for item in dados:
                            if isinstance(item, dict):
                                mapeamentos.append(item)
                    elif isinstance(dados, dict) and "tabelas" in dados:
                        logger.info(f"Formato com chave 'tabelas' em: {arquivo_path}")
                        # Formato com chave "tabelas"
                        for item in dados["tabelas"]:
                            if isinstance(item, dict):
                                mapeamentos.append(item)
                    else:
                        logger.warning(f"Formato de arquivo desconhecido: {arquivo_path}")
                        logger.warning(f"Tipo de dados: {type(dados)}")
                        logger.warning(f"Chaves disponíveis (se for dict): {dados.keys() if isinstance(dados, dict) else 'N/A'}")
                    
                    arquivos_processados += 1
            except Exception as e:
                logger.error(f"Erro ao processar arquivo {arquivo_path}: {e}")
        
        logger.info(f"Carregados {len(mapeamentos)} mapeamentos de {arquivos_processados} arquivos para {tipo_conversao}")
        
        # Armazenar no cache
        self.cache[tipo_conversao] = mapeamentos
        
        return mapeamentos
    
    def buscar_por_tabela_campo(self, tipo_conversao: str, tabela: str, campo: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Busca mapeamentos por tabela e opcionalmente por campo.
        
        Args:
            tipo_conversao: Tipo de conversão
            tabela: Nome da tabela a ser buscada
            campo: Nome do campo a ser buscado (opcional)
            
        Returns:
            Lista de mapeamentos encontrados
        """
        # Carregar mapeamentos (ou usar cache)
        mapeamentos = self.carregar_mapeamentos(tipo_conversao)
        resultados = []
        
        # Determinar os nomes dos campos com base no tipo de conversão
        if tipo_conversao == "OC3_PARA_DATAMESH":
            campo_tabela = "TABELA OC3 LIGHT"
            campo_campo = "CAMPO OC3 LIGHT"
        else:  # SAC_PARA_OC3
            campo_tabela = "TABELA SAC"
            campo_campo = "CAMPO SAC"
        
        # Buscar por tabela e campo
        tabela = tabela.upper()
        for item in mapeamentos:
            tabela_item = item.get(campo_tabela, "").upper()
            
            # Verificar correspondência de tabela
            if tabela in tabela_item or tabela_item in tabela:
                # Se um campo específico foi solicitado
                if campo:
                    campo = campo.upper()
                    campo_item = item.get(campo_campo, "").upper()
                    if campo in campo_item or campo_item in campo:
                        resultados.append(item)
                else:
                    # Adicionar todos os mapeamentos da tabela
                    resultados.append(item)
        
        return resultados
    
    def buscar_por_query(self, tipo_conversao: str, query: str) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
        """
        Extrai tabelas e campos de uma query SQL e busca mapeamentos correspondentes.
        
        Args:
            tipo_conversao: Tipo de conversão
            query: Query SQL a ser analisada
            
        Returns:
            Tupla (mapeamentos encontrados, elementos extraídos da query)
        """
        # Extrair tabelas e campos da query
        import re
        
        # Buscar tabelas (após FROM ou JOIN)
        tabelas = re.findall(r'(?:FROM|JOIN)\s+(\w+)', query, re.IGNORECASE)
        tabelas = [tabela.upper() for tabela in tabelas]
        
        # Buscar campos no SELECT
        campos_match = re.findall(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
        campos = []
        
        if campos_match:
            # Dividir por vírgula, considerando funções
            campos_raw = re.findall(r'([^,]+(?:\([^)]*\)[^,]*)?)', campos_match[0])
            for campo_raw in campos_raw:
                # Extrair apenas o nome do campo, removendo aliases e funções
                campo_limpo = re.sub(r'.*?\.([a-zA-Z0-9_]+)(?:\s+AS\s+.*)?', r'\1', campo_raw.strip())
                if not re.match(r'^[A-Za-z0-9_]+\(', campo_limpo):  # Ignorar funções
                    campos.append(campo_limpo.upper())
        
        # Buscar campos em outras partes da query (WHERE, JOIN, etc.)
        outros_campos = re.findall(r'\b(?:WHERE|AND|OR|ON)\s+([a-zA-Z0-9_.]+)', query, re.IGNORECASE)
        for campo in outros_campos:
            if '.' in campo:  # Formato tabela.campo
                campo_nome = campo.split('.')[-1].upper()
                if campo_nome not in campos:
                    campos.append(campo_nome)
        
        # Remover palavras reservadas
        palavras_reservadas = {"SELECT", "FROM", "WHERE", "AND", "OR", "JOIN", "ON", "GROUP", "BY", "ORDER"}
        campos = [campo for campo in campos if campo not in palavras_reservadas]
        
        elementos_query = {
            "tabelas": tabelas,
            "campos": campos
        }
        
        # Buscar mapeamentos para cada tabela e campo
        resultados = []
        for tabela in tabelas:
            for campo in campos:
                mapeamentos_encontrados = self.buscar_por_tabela_campo(tipo_conversao, tabela, campo)
                for item in mapeamentos_encontrados:
                    if item not in resultados:
                        resultados.append(item)
        
        return resultados, elementos_query
    
    def filtrar_mapeamentos(self, tipo_conversao: str, mapeamentos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtra e formata mapeamentos para uso na conversão.
        
        Args:
            tipo_conversao: Tipo de conversão
            mapeamentos: Lista de mapeamentos a serem filtrados
            
        Returns:
            Lista de mapeamentos filtrados
        """
        if not mapeamentos:
            return []
        
        # Definir campos relevantes com base no tipo de conversão
        if tipo_conversao == "OC3_PARA_DATAMESH":
            campos_obrigatorios = [
                "TABELA OC3 LIGHT", "CAMPO OC3 LIGHT", 
                "TABELA DATA MESH", "CAMPO DATA MESH FINAL"
            ]
            campos_saida = [
                "tipo", "TABELA OC3 LIGHT", "CAMPO OC3 LIGHT", 
                "TABELA DATA MESH", "CAMPO DATA MESH FINAL", "TIPO DE DADO"
            ]
        else:  # SAC_PARA_OC3
            campos_obrigatorios = [
                "TABELA SAC", "CAMPO SAC", 
                "TABELA OC3", "CAMPO OC3"
            ]
            campos_saida = [
                "tipo", "TABELA SAC", "CAMPO SAC", 
                "TABELA OC3", "CAMPO OC3", "TIPO DE DADO"
            ]
        
        # Filtrar mapeamentos
        mapeamentos_filtrados = []
        for item in mapeamentos:
            # Verificar se todos os campos obrigatórios existem
            if all(item.get(campo) for campo in campos_obrigatorios):
                # Criar novo item com os campos de saída
                novo_item = {campo: item.get(campo, "") for campo in campos_saida}
                mapeamentos_filtrados.append(novo_item)
        
        return mapeamentos_filtrados
    
    def agrupar_mapeamentos(self, tipo_conversao: str, mapeamentos: List[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Agrupa mapeamentos por tabela e campo para facilitar a conversão.
        
        Args:
            tipo_conversao: Tipo de conversão
            mapeamentos: Lista de mapeamentos a serem agrupados
            
        Returns:
            Dicionário agrupado por tabela e campo
        """
        if not mapeamentos:
            return {}
        
        # Definir campos com base no tipo de conversão
        if tipo_conversao == "OC3_PARA_DATAMESH":
            campo_tabela_origem = "TABELA OC3 LIGHT"
            campo_campo_origem = "CAMPO OC3 LIGHT"
            campo_tabela_destino = "TABELA DATA MESH"
            campo_campo_destino = "CAMPO DATA MESH FINAL"
        else:  # SAC_PARA_OC3
            campo_tabela_origem = "TABELA SAC"
            campo_campo_origem = "CAMPO SAC"
            campo_tabela_destino = "TABELA OC3"
            campo_campo_destino = "CAMPO OC3"
        
        mapeamentos_agrupados = {}
        
        for item in mapeamentos:
            tabela_origem = item.get(campo_tabela_origem)
            campo_origem = item.get(campo_campo_origem)
            
            if not tabela_origem or not campo_origem:
                continue
            
            # Inicializar estrutura para tabela
            if tabela_origem not in mapeamentos_agrupados:
                mapeamentos_agrupados[tabela_origem] = {}
            
            # Adicionar mapeamento para o campo
            mapeamentos_agrupados[tabela_origem][campo_origem] = {
                "tabela_destino": item.get(campo_tabela_destino, ""),
                "campo_destino": item.get(campo_campo_destino, ""),
                "tipo_dado": item.get("TIPO DE DADO", ""),
                "tipo": item.get("tipo", "cadastro"),
                "sigla": tabela_origem[:1].lower()
            }
        
        return mapeamentos_agrupados