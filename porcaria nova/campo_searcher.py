# campo_searcher.py
import streamlit as st
import pandas as pd
import os
import json
import re
import logging
from typing import List, Dict, Any, Optional, Set

logger = logging.getLogger(__name__)

class CampoSearcher:
    """
    Classe para buscar campos nos arquivos de mapeamento de forma simplificada.
    """
    
    def __init__(self, base_path: str = "mapeamentos-de-para"):
        """
        Inicializa o buscador de campos.
        
        Args:
            base_path: Caminho base para os diretórios de mapeamentos
        """
        self.base_path = base_path
        self.caminhos = {
            "OC3_PARA_DATAMESH": os.path.join(base_path, "mapeamentos-oc3-datamesh"),
            "SAC_PARA_OC3": os.path.join(base_path, "mapeamentos-sac-oc3")
        }
    
    def buscar_arquivos_json(self, tipo_conversao: str) -> List[Dict[str, Any]]:
        """
        Busca todos os arquivos JSON no diretório de mapeamentos.
        
        Args:
            tipo_conversao: Tipo de conversão ('OC3_PARA_DATAMESH' ou 'SAC_PARA_OC3')
            
        Returns:
            Lista de dados de arquivos JSON
        """
        arquivos_json = []
        caminho_base = self.caminhos.get(tipo_conversao, "")
        
        if not caminho_base or not os.path.exists(caminho_base):
            logger.warning(f"Diretório não encontrado: {caminho_base}")
            return arquivos_json
        
        for root, _, files in os.walk(caminho_base):
            for file in files:
                if file.endswith(".json"):
                    caminho_completo = os.path.join(root, file)
                    try:
                        with open(caminho_completo, 'r', encoding='utf-8') as f:
                            dados = json.load(f)
                            
                            # Determinar o tipo de arquivo
                            if isinstance(dados, list):
                                tipo = "Mapeamento Lista"
                            elif isinstance(dados, dict) and "tabelas" in dados:
                                tipo = "Mapeamento Tabelas"
                                dados = dados.get("tabelas", [])
                            else:
                                tipo = "Outro Formato"
                            
                            arquivos_json.append({
                                "nome_arquivo": file,
                                "caminho": caminho_completo,
                                "tipo": tipo,
                                "dados": dados
                            })
                    except Exception as e:
                        logger.error(f"Erro ao processar arquivo {file}: {e}")
        
        logger.info(f"Encontrados {len(arquivos_json)} arquivos JSON para {tipo_conversao}")
        return arquivos_json
    
    def obter_campos_unicos(self, arquivos_json: List[Dict[str, Any]], tipo_conversao: str) -> List[str]:
        """
        Obtém uma lista de todos os campos únicos encontrados nos arquivos JSON.
        
        Args:
            arquivos_json: Lista de dicionários com dados de arquivos JSON
            tipo_conversao: Tipo de conversão ('OC3_PARA_DATAMESH' ou 'SAC_PARA_OC3')
            
        Returns:
            Lista ordenada de nomes de campos únicos
        """
        campos_unicos = set()
        for arquivo in arquivos_json:
            for item in arquivo["dados"]:
                if not isinstance(item, dict):
                    continue
                    
                # Adicionar todos os campos disponíveis no item
                campos_unicos.update(item.keys())
                
                # Para o formato de mapeamento SAC-OC3, verificar campos aninhados
                if tipo_conversao == "SAC_PARA_OC3" and "campos" in item and isinstance(item["campos"], list):
                    for campo in item["campos"]:
                        if isinstance(campo, dict):
                            campos_unicos.update(campo.keys())
        
        # Remover campos de metadados e campos que não são relevantes para a busca
        campos_para_remover = {"detalhes_match", "arquivo_origem", "tipo_arquivo", "campos"}
        
        # Remover campos vazios ou inválidos
        campos_filtrados = {campo for campo in campos_unicos - campos_para_remover if campo and isinstance(campo, str)}
        
        return sorted(list(campos_filtrados))
    
    def busca_abrangente(self, query: str, arquivos_json: List[Dict[str, Any]], tipo_conversao: str, filtro_campos: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Realiza uma busca abrangente em todos os campos dos mapeamentos.
        
        Args:
            query: Termo de busca
            arquivos_json: Lista de dicionários com dados de arquivos JSON
            tipo_conversao: Tipo de conversão ('OC3_PARA_DATAMESH' ou 'SAC_PARA_OC3')
            filtro_campos: Lista de campos para filtrar a busca (opcional)
            
        Returns:
            Lista de resultados encontrados
        """
        resultados = []
        query = query.upper()  # Normalizar para comparação
        
        # Garantir que filtro_campos seja uma lista, mesmo que vazia
        filtro_campos = filtro_campos or []
        
        for arquivo in arquivos_json:
            for item in arquivo["dados"]:
                if not isinstance(item, dict):
                    continue
                
                # Flags para rastrear se houve match
                match_encontrado = False
                detalhes_match = {}
                
                # Verificar se estamos lidando com o formato SAC_PARA_OC3 com campos aninhados
                if tipo_conversao == "SAC_PARA_OC3" and "campos" in item and isinstance(item["campos"], list):
                    # Para cada campo de "campos" na estrutura SAC_PARA_OC3
                    for campo in item["campos"]:
                        if not isinstance(campo, dict):
                            continue
                            
                        campo_match = False
                        campo_detalhes = {}
                        
                        # Verificar cada chave dentro do objeto campo
                        for chave, valor in campo.items():
                            # Verificar se o campo está no filtro (se houver)
                            if filtro_campos and len(filtro_campos) > 0 and chave not in filtro_campos:
                                continue
                                
                            # Converter valor para string para comparação
                            valor_str = str(valor).upper()
                            
                            # Verificar se a query está contida no valor
                            if query in valor_str:
                                campo_match = True
                                campo_detalhes[chave] = valor
                        
                        # Se houver match em algum campo aninhado, incluir o item pai
                        if campo_match:
                            match_encontrado = True
                            # Incluir informações do campo específico que deu match
                            detalhes_match.update(campo_detalhes)
                            
                            # Também incluir o campo específico que deu match
                            if "campo_match" not in detalhes_match:
                                detalhes_match["campo_match"] = []
                            detalhes_match["campo_match"].append(campo)
                
                # Verificação normal dos campos no nível superior do item
                for chave, valor in item.items():
                    # Pular o campo "campos" que já foi processado
                    if chave == "campos" and tipo_conversao == "SAC_PARA_OC3":
                        continue
                        
                    # Verificar se o campo está no filtro (se houver)
                    if filtro_campos and len(filtro_campos) > 0 and chave not in filtro_campos:
                        continue
                    
                    # Converter valor para string para comparação
                    valor_str = str(valor).upper()
                    
                    # Verificar se a query está contida no valor
                    if query in valor_str:
                        match_encontrado = True
                        detalhes_match[chave] = valor
                
                # Adicionar o resultado se encontrou correspondência
                if match_encontrado:
                    # Clonar o item inteiro para preservar todos os campos
                    resultado = item.copy()
                    resultado["detalhes_match"] = detalhes_match
                    resultado["arquivo_origem"] = arquivo["nome_arquivo"]
                    resultado["tipo_arquivo"] = arquivo["tipo"]
                    resultados.append(resultado)
        
        return resultados
    
    def mostrar_interface_busca(self):
        """
        Exibe a interface de busca por campos no Streamlit.
        """
        st.title("Busca por Campos")
        st.write("""
        Esta ferramenta permite buscar em todos os campos dos mapeamentos JSON.
        Digite o termo que deseja pesquisar.
        """)
        
        # Determinar o tipo de conversão atual (da sessão ou padrão)
        tipo_conversao_padrao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")
        
        # Opções para seleção direta do tipo de conversão
        tipo_conversao_opcoes = {
            "OC3_PARA_DATAMESH": "OC3 para DataMesh (Athena)",
            "SAC_PARA_OC3": "SAC para OC3"
        }
        
        # Interface para seleção do tipo de conversão
        tipo_conversao = st.selectbox(
            "Selecione o tipo de conversão para busca:",
            options=list(tipo_conversao_opcoes.keys()),
            format_func=lambda x: tipo_conversao_opcoes[x],
            index=list(tipo_conversao_opcoes.keys()).index(tipo_conversao_padrao),
            key="busca_tipo_conversao"
        )
        
        # Determinar sistema de origem e destino com base no tipo de conversão
        if tipo_conversao == "OC3_PARA_DATAMESH":
            sistema_origem = "OC3"
            sistema_destino = "DataMesh"
        else:  # SAC_PARA_OC3
            sistema_origem = "SAC"
            sistema_destino = "OC3"
        
        # Mostrar informação do modo atual com mais destaque
        st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:10px; border-radius:5px; margin:10px 0;">
            <h3 style="margin:0; color:#262730;">Modo: {sistema_origem} para {sistema_destino}</h3>
            <p style="margin:5px 0 0 0; font-size:0.9em;">Este modo permite buscar nos mapeamentos de {sistema_origem} para {sistema_destino}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Verificar se o diretório de mapeamentos existe
        caminho_mapeamentos = self.caminhos.get(tipo_conversao)
        if not os.path.exists(caminho_mapeamentos):
            st.error(f"❌ Diretório de mapeamentos não encontrado: {caminho_mapeamentos}")
            st.warning("Por favor, certifique-se de que o diretório existe antes de continuar.")
            return
            
        # Verificar se existem arquivos JSON no caminho
        arquivos_json = [f for f in os.listdir(caminho_mapeamentos) if f.endswith('.json')]
        if not arquivos_json:
            st.warning(f"⚠️ Nenhum arquivo JSON encontrado no diretório: {caminho_mapeamentos}")
            st.info("Adicione arquivos JSON de mapeamento ao diretório para usar esta funcionalidade.")
            return
            
        # Adicionar uma seção explicativa com informações detalhadas sobre as opções de busca
        with st.expander("ℹ️ Ajuda - Como usar a busca de campos"):
            st.markdown("""
            ### Como usar a busca de campos
            
            Esta ferramenta permite buscar termos específicos em todos os mapeamentos disponíveis. Aqui está como usar cada opção:
            
            #### Tipo de conversão
            - Selecione **OC3 para DataMesh** para buscar nos mapeamentos de OC3 para DataMesh/Athena
            - Selecione **SAC para OC3** para buscar nos mapeamentos de SAC para OC3
            
            #### Tipo de correspondência 
            - **Contém**: Busca valores que contenham o termo em qualquer posição
              - Exemplo: buscar "prod" encontrará "produto", "produção", etc.
            - **Correspondência exata**: Busca apenas valores exatamente iguais ao termo
              - Exemplo: buscar "produto" encontrará somente "produto"
            
            #### Filtrar campos específicos
            - **Ativado**: Permite selecionar em quais campos você deseja buscar
            - **Desativado**: Busca em todos os campos disponíveis
            
            #### Resultados
            Os resultados mostram todos os mapeamentos que correspondem aos critérios de busca.
            Use o expandidor "Ver detalhes completos" para ver todas as informações sobre cada mapeamento.
            """)
        
        # Carregar todos os arquivos JSON
        with st.spinner(f"Carregando arquivos JSON para {tipo_conversao}..."):
            arquivos_json = self.buscar_arquivos_json(tipo_conversao)
            st.write(f"Total de arquivos JSON encontrados: {len(arquivos_json)}")
            
            # Mostrar contagem por tipo de arquivo
            if arquivos_json:
                tipos_arquivos = {}
                for arquivo in arquivos_json:
                    tipo = arquivo["tipo"]
                    if tipo not in tipos_arquivos:
                        tipos_arquivos[tipo] = 0
                    tipos_arquivos[tipo] += 1
                    
                st.write("Tipos de arquivos encontrados:")
                for tipo, contagem in tipos_arquivos.items():
                    st.write(f"- {tipo}: {contagem} arquivo(s)")
        
        # Obter campos únicos para filtragem
        campos_unicos = self.obter_campos_unicos(arquivos_json, tipo_conversao)
        
        # Interface para busca e filtros
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Opções para o tipo de busca com descrição
            match_type = st.radio(
                "Tipo de correspondência:",
                ["Contém", "Correspondência exata"],
                index=0,
                horizontal=True,
                help="'Contém': Encontra resultados onde o termo buscado está contido em qualquer parte do valor. 'Correspondência exata': Encontra apenas resultados que correspondem exatamente ao termo buscado."
            )
            
            # Adicionar texto explicativo abaixo da opção
            if match_type == "Contém":
                st.caption("Busca valores que contenham o termo em qualquer posição (Ex: buscar 'prod' encontrará 'produto', 'produção', etc)")
            else:
                st.caption("Busca apenas valores exatamente iguais ao termo (Ex: buscar 'produto' encontrará somente 'produto')")
        
        with col2:
            # Mostrar tipo de conversão atual
            st.markdown(f"**Origem**: {sistema_origem}")
            st.markdown(f"**Destino**: {sistema_destino}")
        
        with col3:
            # Opção de filtro de campos com explicação
            filtrar_campos = st.checkbox(
                "Filtrar campos específicos", 
                value=True,
                help="Ative para selecionar em quais campos você deseja buscar. Desative para buscar em todos os campos."
            )
            if filtrar_campos:
                st.caption("Permite buscar apenas em campos específicos")
            else:
                st.caption("Busca em todos os campos disponíveis")
        
        # Campo de pesquisa com tooltip explicativo
        query = st.text_input(
            "Digite o termo de busca:", 
            placeholder=f"Ex: PRODUTO, cliente, INT, etc.",
            help="Digite o termo que deseja buscar nos mapeamentos. Pode ser um nome de tabela, campo, tipo de dado, etc."
        )
        
        # Seleção de campos para filtro (se habilitado)
        filtro_campos_selecionados = []
        if filtrar_campos:
            # Selecionar campos específicos para exibição de acordo com o tipo de conversão
            if tipo_conversao == "OC3_PARA_DATAMESH":
                campos_sugeridos = [
                    "TABELA OC3 LIGHT", "CAMPO OC3 LIGHT", 
                    "TABELA DATA MESH", "CAMPO DATA MESH FINAL", 
                    "TIPO DE DADO", "tipo"
                ]
            else:  # SAC_PARA_OC3
                campos_sugeridos = [
                    "tabela", "campo", "tipoCampo", 
                    "descricao", "campoOrigem", "tabelaOrigem"
                ]
            
            # Filtrar os campos sugeridos que realmente existem nos dados
            campos_sugeridos_existentes = [campo for campo in campos_sugeridos if campo in campos_unicos]
            
            # Interface para seleção de campos com explicações
            opcao_exibicao = st.radio(
                "Exibir campos:",
                ["Campos comuns", "Todos os campos disponíveis"],
                index=0,
                horizontal=True,
                help="'Campos comuns': Exibe apenas os campos mais relevantes para este tipo de conversão. 'Todos os campos disponíveis': Exibe todos os campos encontrados nos mapeamentos."
            )
            
            # Adicionar texto explicativo
            if opcao_exibicao == "Campos comuns":
                st.caption(f"Mostra apenas os campos mais usados para o modo {sistema_origem} para {sistema_destino}")
            else:
                st.caption("Mostra todos os campos disponíveis nos mapeamentos")
            
            if opcao_exibicao == "Campos comuns" and campos_sugeridos_existentes:
                filtro_campos_selecionados = st.multiselect(
                    "Selecione os campos para busca:",
                    options=campos_unicos,
                    default=campos_sugeridos_existentes
                )
            else:
                filtro_campos_selecionados = st.multiselect(
                    "Selecione os campos para busca:",
                    options=campos_unicos,
                    default=[]
                )
            
            # Mensagem de orientação
            if not filtro_campos_selecionados:
                st.warning("Nenhum campo selecionado. A busca será realizada em todos os campos.")
        
        # Botão de busca
        search_clicked = st.button("Buscar", type="primary", use_container_width=True)
        
        # Processar busca quando o botão for clicado e query for preenchida
        if search_clicked and query:
            with st.spinner("Buscando correspondências..."):
                if not arquivos_json:
                    st.error(f"Não foi possível encontrar arquivos JSON para o tipo de conversão {tipo_conversao}.")
                    return
                
                # Buscar resultados
                resultados = self.busca_abrangente(
                    query, 
                    arquivos_json, 
                    tipo_conversao, 
                    filtro_campos=filtro_campos_selecionados if filtrar_campos else None
                )
                
                # Filtrar para correspondência exata se necessário
                if match_type == "Correspondência exata":
                    query_upper = query.upper()
                    resultados = [r for r in resultados if 
                                any(query_upper == str(valor).upper() for valor in r["detalhes_match"].values())]
                
                # Exibir resultados
                if resultados:
                    st.success(f"Foram encontradas {len(resultados)} correspondências para '{query}'")
                    
                    # Preparar todas as colunas disponíveis
                    todas_colunas = set()
                    for r in resultados:
                        todas_colunas.update(r.keys())
                    
                    # Remover chaves não desejadas
                    colunas_para_remover = {"detalhes_match", "arquivo_origem", "tipo_arquivo"}
                    colunas_ordenadas = sorted(
                        [col for col in todas_colunas if col not in colunas_para_remover], 
                        key=lambda x: x.lower()
                    )
                    
                    # Formatar os resultados para exibição na tabela
                    dados_tabela = []
                    for r in resultados:
                        linha = {}
                        for col in colunas_ordenadas:
                            # Usar 'nan' se o campo não existir
                            linha[col] = r.get(col, 'nan')
                        dados_tabela.append(linha)
                    
                    # Para o modo SAC_PARA_OC3, processar campos aninhados para apresentação
                    if tipo_conversao == "SAC_PARA_OC3":
                        # Processar resultados que tenham campos aninhados
                        dados_processados = []
                        for r in resultados:
                            if "campo_match" in r.get("detalhes_match", {}):
                                # Para cada campo aninhado que deu match
                                for campo in r["detalhes_match"]["campo_match"]:
                                    item_processado = {
                                        "tipo": r.get("tipo", ""),
                                        "tabela": r.get("tabela", ""),
                                        "descritivoTabela": r.get("descritivoTabela", "")
                                    }
                                    # Adicionar os detalhes do campo
                                    item_processado.update(campo)
                                    dados_processados.append(item_processado)
                            else:
                                # Para resultados normais, adicionar diretamente
                                dados_processados.append(r)
                                
                        # Se encontrou campos aninhados, substituir os dados da tabela
                        if dados_processados:
                            dados_tabela = []
                            for r in dados_processados:
                                linha = {}
                                for col in colunas_ordenadas:
                                    linha[col] = r.get(col, 'nan')
                                dados_tabela.append(linha)
                    
                    # Exibir dados em um dataframe para melhor visualização
                    df = pd.DataFrame(dados_tabela)
                    
                    # Destacar colunas específicas para cada tipo de conversão
                    if tipo_conversao == "OC3_PARA_DATAMESH":
                        colunas_importantes = ["tipo", "TABELA OC3 LIGHT", "CAMPO OC3 LIGHT", "TABELA DATA MESH", "CAMPO DATA MESH FINAL", "TIPO DE DADO"]
                    else:  # SAC_PARA_OC3
                        colunas_importantes = ["tipo", "tabela", "campo", "descricao", "tipoCampo", "tabelaOrigem", "campoOrigem", "descritivoTabela"]
                    
                    # Reordenar o DataFrame para mostrar as colunas importantes primeiro
                    colunas_df = [col for col in colunas_importantes if col in df.columns]
                    colunas_df += [col for col in df.columns if col not in colunas_importantes and col not in colunas_df]
                    
                    # Exibir o DataFrame com as colunas reorganizadas
                    if colunas_df:
                        # Verificar se há colunas válidas antes de filtrar
                        colunas_validas = [col for col in colunas_df if col in df.columns]
                        if colunas_validas:
                            st.dataframe(df[colunas_validas], use_container_width=True)
                        else:
                            st.dataframe(df, use_container_width=True)
                    else:
                        st.dataframe(df, use_container_width=True)
                    
                    # Informações dos arquivos em um expander separado
                    with st.expander("Arquivos de origem"):
                        arquivos_encontrados = []
                        for r in resultados:
                            arquivo_info = {
                                "Nome do Arquivo": r["arquivo_origem"],
                                "Tipo de Arquivo": r["tipo_arquivo"]
                            }
                            if arquivo_info not in arquivos_encontrados:
                                arquivos_encontrados.append(arquivo_info)
                        
                        st.table(arquivos_encontrados)
                    
                    # Opção para expandir detalhes completos
                    with st.expander("Ver detalhes completos"):
                        for i, r in enumerate(resultados, 1):
                            st.markdown(f"### Mapeamento {i}")
                            st.json(r)
                else:
                    st.warning(f"Nenhuma correspondência encontrada para '{query}'.")
                    
        elif search_clicked and not query:
            st.warning("Por favor, digite um termo para buscar.")