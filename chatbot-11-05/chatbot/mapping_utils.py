# mapping_utils.py
import os
import json
import re
from logger_config import setup_logger
from config import PATH_CONFIG 

logger = setup_logger()

class MappingManager:
    """Classe centralizada para gerenciar mapeamentos entre sistemas."""
    
    def __init__(self, tipo_conversao="OC3_PARA_DATAMESH"):
        """
        Inicializa o gerenciador de mapeamentos.
        
        Args:
            tipo_conversao: Tipo de conversão ('OC3_PARA_DATAMESH' ou 'SAC_PARA_OC3')
        """
        self.tipo_conversao = tipo_conversao
        self.mapeamentos = []
    
    def descobrir_caminho_mapeamentos(self):
        """Retorna o caminho correto dos mapeamentos com base no tipo de conversão."""
        if self.tipo_conversao == "OC3_PARA_DATAMESH":
            return PATH_CONFIG["MAPEAMENTOS_OC3_DATAMESH"]
        else:  # SAC_PARA_OC3
            return PATH_CONFIG["MAPEAMENTOS_SAC_OC3"]
        
    def carregar_mapeamentos(self, pasta_json=None):
        """
        Carrega mapeamentos de arquivos JSON.
        
        Args:
            pasta_json: Caminho local contendo arquivos JSON
            
        Returns:
            Lista de mapeamentos carregados
        """
        if pasta_json is None:
            pasta_json = self.descobrir_caminho_mapeamentos()
        
        logger.info(f"Carregando mapeamentos de: {pasta_json}")
        mapeamentos = []

        try:
            # Criar o diretório se não existir
            os.makedirs(pasta_json, exist_ok=True)
            
            # Processar arquivos JSON no diretório
            for arquivo in os.listdir(pasta_json):
                if arquivo.endswith(".json"):
                    caminho_json = os.path.join(pasta_json, arquivo)
                    try:
                        with open(caminho_json, "r", encoding="utf-8") as f:
                            dados = json.load(f)
                            if isinstance(dados, list):
                                for item in dados:
                                    if isinstance(item, dict):
                                        mapeamentos.append(item)
                            elif isinstance(dados, dict) and "tabelas" in dados:
                                for item in dados.get("tabelas", []):
                                    if isinstance(item, dict):
                                        mapeamentos.append(item)
                    except Exception as e:
                        logger.error(f"Erro ao processar o arquivo {caminho_json}: {e}")
        except Exception as e:
            logger.error(f"Erro ao acessar diretório {pasta_json}: {e}")

        self.mapeamentos = mapeamentos
        logger.info(f"Total de mapeamentos carregados: {len(mapeamentos)}")
        return mapeamentos
    
    def buscar_por_termos(self, query, elementos_query=None):
        """
        Busca mapeamentos com base nos termos da query.
        
        Args:
            query: Query SQL a ser processada
            elementos_query: Elementos já extraídos da query (opcional)
            
        Returns:
            Lista de mapeamentos correspondentes
        """
        # Importar aqui para evitar importação circular
        from .sql_utils import extrair_elementos_query
        
        # Se não fornecido, extrair elementos da query
        if elementos_query is None:
            elementos_query = extrair_elementos_query(query)
            
        tabelas_query = elementos_query["tabelas"]
        campos_query = elementos_query["campos"]
        
        logger.info(f"Buscando por: Tabelas={tabelas_query}, Campos={campos_query}")
        
        resultados = []
        
        # Determinar os campos de busca com base no tipo de conversão
        if self.tipo_conversao == "OC3_PARA_DATAMESH":
            campo_tabela_origem = "TABELA OC3 LIGHT"
            campo_campo_origem = "CAMPO OC3 LIGHT"
        else:  # SAC_PARA_OC3
            campo_tabela_origem = "TABELA SAC"
            campo_campo_origem = "CAMPO SAC"
        
        # Iterar sobre todos os mapeamentos
        for item in self.mapeamentos:
            # Verificar correspondência de tabela
            tabela_origem = item.get(campo_tabela_origem, "").upper()
            tabela_match = any(
                tabela_origem == tabela_query or 
                tabela_origem in tabela_query or 
                tabela_query in tabela_origem
                for tabela_query in tabelas_query
            )

            # Se não encontrou tabela, continue
            if not tabela_match:
                continue

            # Verificar campos
            campos_match = []
            for campo_query in campos_query:
                # Lista de possíveis campos relacionados
                campo_origem = item.get(campo_campo_origem, "").upper()
                possiveis_campos = [
                    campo_origem,
                    campo_query.replace("ID_", "").upper(),
                    campo_query.replace("_", "").upper()
                ]

                # Verificar se o campo da query corresponde a algum campo do mapeamento
                campo_encontrado = any(
                    campo_query.upper() in campo_possivel or 
                    campo_possivel in campo_query.upper()
                    for campo_possivel in possiveis_campos if campo_possivel
                )

                if campo_encontrado:
                    campos_match.append(campo_query)

            # Se encontrou campos correspondentes, adicionar o item
            if campos_match:
                novo_item = item.copy()
                novo_item["campos_match"] = campos_match
                resultados.append(novo_item)
        
        logger.info(f"Encontrados {len(resultados)} mapeamentos")
        return resultados
    
    def filtrar_mapeamentos(self, mapeamentos_brutos):
        """
        Filtra mapeamentos para incluir apenas itens com campos válidos.
        
        Args:
            mapeamentos_brutos: Lista de mapeamentos a serem filtrados
            
        Returns:
            Lista de mapeamentos filtrados
        """
        # Definir campos com base no tipo de conversão
        if self.tipo_conversao == "OC3_PARA_DATAMESH":
            campos_requeridos = [
                "tipo", "TABELA OC3 LIGHT", "CAMPO OC3 LIGHT", 
                "TABELA DATA MESH", "CAMPO DATA MESH FINAL", "TIPO DE DADO"
            ]
            campos_saida = [
                "tipo", "TABELA OC3 LIGHT", "CAMPO OC3 LIGHT", 
                "TABELA DATA MESH", "CAMPO DATA MESH FINAL", "TIPO DE DADO"
            ]
        else:  # SAC_PARA_OC3
            campos_requeridos = [
                "tipo", "TABELA SAC", "CAMPO SAC", 
                "TABELA OC3", "CAMPO OC3", "TIPO DE DADO"
            ]
            campos_saida = [
                "tipo", "TABELA SAC", "CAMPO SAC", 
                "TABELA OC3", "CAMPO OC3", "TIPO DE DADO"
            ]
        
        resultados_filtrados = []
        
        for item in mapeamentos_brutos:
            # Verificar se todos os campos requeridos existem e não são "nan"
            if all(item.get(campo) != "nan" and item.get(campo) for campo in campos_requeridos):
                novo_item = {campo: item.get(campo, "") for campo in campos_saida}
                # Preservar campos_match se existir
                if "campos_match" in item:
                    novo_item["campos_match"] = item["campos_match"]
                resultados_filtrados.append(novo_item)
        
        return resultados_filtrados
    
    def agrupar_mapeamentos_para_lambda(self, mapeamentos_selecionados):
        """
        Agrupa os mapeamentos no formato adequado para envio à Lambda.
        
        Args:
            mapeamentos_selecionados: Lista de mapeamentos selecionados
            
        Returns:
            Dicionário de mapeamentos agrupados
        """
        mapeamentos_agrupados = {}
        
        # Verificar se temos mapeamentos válidos
        if not mapeamentos_selecionados:
            return mapeamentos_agrupados
        
        for item in mapeamentos_selecionados:
            if not isinstance(item, dict):
                continue
            
            # Definir campos com base no tipo de conversão
            if self.tipo_conversao == "OC3_PARA_DATAMESH":
                tabela_original = item.get("TABELA OC3 LIGHT", "")
                campo_original = item.get("CAMPO OC3 LIGHT", "")
                tabela_destino = item.get("TABELA DATA MESH", "")
                campo_destino = item.get("CAMPO DATA MESH FINAL", "")
                tipo_dado = item.get("TIPO DE DADO", "")
                categoria = item.get("tipo", "cadastro")
                sigla = item.get("sigla", tabela_original[:1].lower())
            else:  # SAC_PARA_OC3
                tabela_original = item.get("TABELA SAC", "")
                campo_original = item.get("CAMPO SAC", "")
                tabela_destino = item.get("TABELA OC3", "")
                campo_destino = item.get("CAMPO OC3", "")
                tipo_dado = item.get("TIPO DE DADO", "")
                categoria = item.get("tipo", "")
                sigla = item.get("sigla", tabela_original[:1].lower())
            
            # Pular se tabela ou campo estiverem vazios
            if not tabela_original or not campo_original:
                continue
                
            # Inicializar a estrutura de nível tabela se não existir
            if tabela_original not in mapeamentos_agrupados:
                mapeamentos_agrupados[tabela_original] = {}
            
            # Adicionar mapeamento de campo
            mapeamentos_agrupados[tabela_original][campo_original] = {
                "tabela_datamesh": tabela_destino,
                "campo_datamesh": campo_destino,
                "tipo_dado": tipo_dado,
                "tipo": categoria,
                "sigla": sigla
            }
        
        return mapeamentos_agrupados
    
    def verificar_multiplas_possibilidades(self, resultados_filtrados):
        """
        Verifica se há múltiplas possibilidades de mapeamento.
        
        Args:
            resultados_filtrados: Lista de mapeamentos encontrados
            
        Returns:
            Tupla (booleano indicando múltiplas possibilidades, 
                  dicionário de tabelas, 
                  dicionário de tabelas com múltiplos destinos)
        """
        # Agrupar mapeamentos por tabela
        tabelas_mapeadas = {}
        
        for item in resultados_filtrados:
            # Verificar se item é um dicionário válido
            if not isinstance(item, dict):
                continue
            
            # Determinar as chaves de tabela baseado no tipo de conversão
            if self.tipo_conversao == "OC3_PARA_DATAMESH":
                tabela_origem = item.get("TABELA OC3 LIGHT", "")
                tabela_destino = item.get("TABELA DATA MESH", "")
                campo_origem = item.get("CAMPO OC3 LIGHT", "")
            else:  # SAC_PARA_OC3
                tabela_origem = item.get("TABELA SAC", "")
                tabela_destino = item.get("TABELA OC3", "")
                campo_origem = item.get("CAMPO SAC", "")
            
            # Ignorar itens sem tabela
            if not tabela_origem:
                continue
            
            # Chave combinada para tabela e destino
            chave_destino = f"{tabela_destino}"
            
            # Inicializar entrada para a tabela se não existir
            if tabela_origem not in tabelas_mapeadas:
                tabelas_mapeadas[tabela_origem] = {
                    "campos": set(),
                    "destinos": set(),
                    "destinos_info": {},
                    "total_mapeamentos": 0,
                    "items": []
                }
            
            # Adicionar campo e destino
            tabelas_mapeadas[tabela_origem]["campos"].add(campo_origem)
            tabelas_mapeadas[tabela_origem]["destinos"].add(chave_destino)
            
            # Adicionar informações do destino
            if chave_destino not in tabelas_mapeadas[tabela_origem]["destinos_info"]:
                tabelas_mapeadas[tabela_origem]["destinos_info"][chave_destino] = {
                    "nome": tabela_destino,
                    "campos": set(),
                    "items": []
                }
            
            tabelas_mapeadas[tabela_origem]["destinos_info"][chave_destino]["campos"].add(campo_origem)
            tabelas_mapeadas[tabela_origem]["destinos_info"][chave_destino]["items"].append(item)
            
            # Incrementar total de mapeamentos
            tabelas_mapeadas[tabela_origem]["total_mapeamentos"] += 1
            
            # Adicionar o item completo
            tabelas_mapeadas[tabela_origem]["items"].append(item)

        # Se temos pelo menos uma tabela, sempre requer seleção
        multiplas_possibilidades = len(tabelas_mapeadas) > 0
        
        # Além disso, registramos explicitamente quais tabelas têm múltiplos destinos
        tabelas_multiplos_destinos = {}
        
        for tabela, dados in tabelas_mapeadas.items():
            if len(dados['destinos']) > 1:
                destinos_list = []
                for i, destino in enumerate(dados['destinos']):
                    nome_destino = dados['destinos_info'][destino]['nome']
                    destinos_list.append((i+1, nome_destino))
                tabelas_multiplos_destinos[tabela] = destinos_list

        return multiplas_possibilidades, tabelas_mapeadas, tabelas_multiplos_destinos