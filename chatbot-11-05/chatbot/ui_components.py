# ui_components.py - Versão refatorada
# ui_components.py
import streamlit as st
import pandas as pd
import re

# Usar importação relativa com o ponto
from .state_manager import adicionar_mensagem, limpar_historico

def reiniciar_chat():
    """Reinicia o chat limpando o historico e os estados."""
    tipo_conversao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")
    mapping_manager_oc3_datamesh = st.session_state.get("mapping_manager_oc3_datamesh")
    mapping_manager_sac_oc3 = st.session_state.get("mapping_manager_sac_oc3")
    mapeamentos_oc3_datamesh = st.session_state.get("mapeamentos_oc3_datamesh", [])
    mapeamentos_sac_oc3 = st.session_state.get("mapeamentos_sac_oc3", [])

    for key in list(st.session_state.keys()):
        if key not in ["tipo_conversao", "seletor_conversao"]:
            del st.session_state[key]

    st.session_state["tipo_conversao"] = tipo_conversao
    st.session_state["mensagens"] = []
    st.session_state["aguardando_selecao"] = False
    st.session_state["mostrar_selecao"] = False
    st.session_state["esperando_resultado"] = False
    st.session_state["ultima_query"] = ""
    st.session_state["resultado_query"] = None
    st.session_state["tabelas_utilizadas"] = []
    st.session_state["tipo_processamento"] = ""
    st.session_state["resultados_filtrados"] = []
    st.session_state["mapping_manager_oc3_datamesh"] = mapping_manager_oc3_datamesh
    st.session_state["mapping_manager_sac_oc3"] = mapping_manager_sac_oc3
    st.session_state["mapeamentos_oc3_datamesh"] = mapeamentos_oc3_datamesh
    st.session_state["mapeamentos_sac_oc3"] = mapeamentos_sac_oc3

    if tipo_conversao == "OC3_PARA_DATAMESH":
        st.session_state["mapeamentos"] = mapeamentos_oc3_datamesh
        st.session_state["mapping_manager"] = mapping_manager_oc3_datamesh
    else:
        st.session_state["mapeamentos"] = mapeamentos_sac_oc3
        st.session_state["mapping_manager"] = mapping_manager_sac_oc3

    # Resetar progresso
    st.session_state["chat_em_progresso"] = False

    st.rerun()

def exibir_historico_chat():
    """Exibe o histórico do chat."""
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

    for msg in st.session_state.get("mensagens", []):
        # Pular o resultado final que será mostrado separadamente
        if msg.get("is_result", False):
            continue
            
        if msg["role"] == "assistant":
            if msg.get("is_html", False):
                # Mensagem HTML - renderizar diretamente
                st.markdown(f"""
                <div class='msg-container' style="margin-bottom: 15px;">
                    <div class='message-box bot-msg'>
                        {msg['text']}
                    </div>
                    <div style="width:40%;"></div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Mensagem normal - escapar caracteres
                st.markdown(f"""
                <div class='msg-container' style="margin-bottom: 15px;">
                    <div class='message-box bot-msg'>
                        {msg['text']}
                    </div>
                    <div style="width:40%;"></div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='msg-container' style="margin-bottom: 15px;">
                <div style="width:40%;"></div>
                <div class='message-box user-msg'>
                    {msg['text']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

def exibir_mensagem_usuario(mensagem):
    """Exibe a mensagem do usuário imediatamente."""
    st.markdown(f"""
    <div class='msg-container'>
        <div style="width:40%;"></div>
        <div class='message-box user-msg'>
            {mensagem} <span class='icon'></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def exibir_mensagem_bot(mensagem):
    """Exibe uma mensagem do assistente, dividindo mensagens específicas em partes."""
    # Dividir a mensagem em linhas
    linhas = mensagem.split('\n')
    
    # Verificar se a mensagem tem o formato específico de múltiplas tabelas
    if (len(linhas) >= 4 and 
        "Analisando sua query SQL" in linhas[0] and 
        "Foi encontrado para a tabela" in linhas[1] and 
        "Foi encontrado para a tabela" in linhas[2] and 
        "Por favor" in linhas[3]):
        
        # Primeira mensagem inicial
        st.markdown(f"""
        <div class='msg-container'>
            <div class='message-box bot-msg'>
                <span class='icon'></span> {linhas[0]}
            </div>
            <div style="width:40%;"></div>
        </div>
        """, unsafe_allow_html=True)
        
        # Primeira tabela
        st.markdown(f"""
        <div class='msg-container'>
            <div class='message-box bot-msg'>
                <span class='icon'></span> {linhas[1]}
            </div>
            <div style="width:40%;"></div>
        </div>
        """, unsafe_allow_html=True)
        
        # Segunda tabela
        st.markdown(f"""
        <div class='msg-container'>
            <div class='message-box bot-msg'>
                <span class='icon'></span> {linhas[2]}
            </div>
            <div style="width:40%;"></div>
        </div>
        """, unsafe_allow_html=True)
        
        # Mensagem final
        st.markdown(f"""
        <div class='msg-container'>
            <div class='message-box bot-msg'>
                <span class='icon'></span> {linhas[3]}
            </div>
            <div style="width:40%;"></div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Para mensagens normais, apenas renderizar o texto
        st.markdown(f"""
        <div class='msg-container'>
            <div class='message-box bot-msg'>
                <span class='icon'></span> {mensagem}
            </div>
            <div style="width:40%;"></div>
        </div>
        """, unsafe_allow_html=True)

def exibir_erro(mensagem):
    """Exibe uma mensagem de erro do assistente."""
    st.markdown("""
    <div class='msg-container'>
        <div class='message-box bot-msg'>
            <span class='icon'></span> ⚠️ {}
        </div>
        <div style="width:40%;"></div>
    </div>
    """.format(mensagem), 
    unsafe_allow_html=True)

def exibir_resultado():
    """Exibe o resultado da conversão da query."""
    # Verificar se há um resultado para exibir
    result = st.session_state.get("resultado_query")
    if not result:
        return
    
    # Definir o texto a ser exibido
    tipo_conversao = result.get("tipo_conversao", st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH"))
    
    # Define o texto amigável para o tipo de conversão
    if tipo_conversao == "OC3_PARA_DATAMESH":
        tipo_conversao_texto = "OC3 para DataMesh (Athena)"
    elif tipo_conversao == "SAC_PARA_OC3":
        tipo_conversao_texto = "SAC para OC3"
    else:
        tipo_conversao_texto = tipo_conversao
    
    # Título do resultado
    st.markdown(f"### Resultado da Conversão ({tipo_conversao_texto})")
    
    # Mostrar query original
    with st.expander("Query Original", expanded=True):
        st.code(result.get("original", ""), language="sql")
    
    # Mostrar query convertida
    with st.expander("Query Convertida", expanded=True):
        st.code(result.get("convertida", ""), language="sql")
        
        # Adicionar botão para copiar o resultado
        if st.button("📋 Copiar Query Convertida"):
            # Usar JavaScript para copiar para a área de transferência
            st.write("Query copiada para a área de transferência!")
            st.markdown(f"""
            <script>
                navigator.clipboard.writeText(`{result.get("convertida", "")}`)
                    .then(() => console.log('Texto copiado!'))
                    .catch(err => console.error('Erro ao copiar texto:', err));
            </script>
            """, unsafe_allow_html=True)
    
    # Exibir tabelas utilizadas na conversão
    if st.session_state.get("tabelas_utilizadas"):
        st.markdown("#### Tabelas utilizadas na conversão:")
        
        # Preparar dados para o formato de tabela do Streamlit
        table_data = []
        
        if tipo_conversao == "OC3_PARA_DATAMESH":
            for tabela in st.session_state["tabelas_utilizadas"]:
                if isinstance(tabela, dict):
                    table_data.append({
                        "Tipo": tabela.get("tipo", ""),
                        "Tabela OC3": tabela.get("TABELA OC3 LIGHT", ""),
                        "Tabela DataMesh": tabela.get("TABELA DATA MESH", "")
                    })
        elif tipo_conversao == "SAC_PARA_OC3":
            for tabela in st.session_state["tabelas_utilizadas"]:
                if isinstance(tabela, dict):
                    table_data.append({
                        "Tipo": tabela.get("tipo", ""),
                        "Tabela SAC": tabela.get("TABELA SAC", ""),
                        "Tabela OC3": tabela.get("TABELA OC3", ""),
                        "Descrição": tabela.get("DESCRITIVO", "")
                    })
        
        # Exibir a tabela usando o componente nativo
        if table_data:
            st.table(table_data)
        
        # Adicionar informação sobre o modo de processamento
        st.markdown(f"**Modo de processamento:** {st.session_state.get('tipo_processamento', '')}")
        st.markdown(f"**Tipo de conversão:** {tipo_conversao_texto}")
    
    # Adicionar botão para novo chat
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Iniciar Nova Conversão", use_container_width=True, type="primary"):
            reiniciar_chat()

def mostrar_opcoes_selecao():
    """Mostra as opções de seleção (automática ou manual)."""
    # Verificar se estamos aguardando seleção
    if not st.session_state.get("aguardando_selecao", False):
        return
        
    # Contar o número de tabelas distintas encontradas
    resultados_filtrados = st.session_state.get("resultados_filtrados", [])
    
    # Determinar o tipo de mapeamento
    tipo_conversao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")
    
    # Contar tabelas distintas
    tabelas_distintas = set()
    for item in resultados_filtrados:
        if isinstance(item, dict):
            if tipo_conversao == "OC3_PARA_DATAMESH" and "TABELA OC3 LIGHT" in item:
                tabela = item.get("TABELA OC3 LIGHT", "")
                tabelas_distintas.add(tabela)
            elif tipo_conversao == "SAC_PARA_OC3" and "TABELA SAC" in item:
                tabela = item.get("TABELA SAC", "")
                tabelas_distintas.add(tabela)
    
    # Criar mensagem personalizada com base nas tabelas encontradas
    if len(tabelas_distintas) > 1:
        tabelas_str = ", ".join(tabelas_distintas)
        mensagem = f"Encontrei {len(tabelas_distintas)} tabelas ({tabelas_str}) com mapeamentos. Como deseja proceder?"
    else:
        mensagem = f"Encontrei {len(resultados_filtrados)} mapeamentos possíveis. Como deseja proceder?"
    
    st.markdown(f"""
    <div class='msg-container'>
        <div class='message-box bot-msg'>
            <span class='icon'></span> {mensagem}
        </div>
        <div style="width:40%;"></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Opções para o usuário com colunas mais próximas e melhor alinhamento
    col1, spacer, col2 = st.columns([1, 0.1, 1])
    with col1:
        if st.button("1️⃣ Processar automaticamente", use_container_width=True):
            st.session_state["aguardando_selecao"] = False
            st.session_state["esperando_resultado"] = True
            st.session_state["tipo_processamento"] = "Processamento automático"
            
            # Uso da primeira opção de mapeamento encontrada
            if st.session_state.get("resultados_filtrados"):
                st.session_state["tabelas_utilizadas"] = [st.session_state["resultados_filtrados"][0]]
            
            # Adicionar mensagem de processamento
            adicionar_mensagem(
                "assistant", 
                "Processando sua query automaticamente com o primeiro mapeamento encontrado..."
            )
            
            # Iniciar processamento
            from .query_processing import processar_conversao
            processar_conversao()
    
    with col2:
        if st.button("2️⃣ Selecionar tabelas manualmente", use_container_width=True):
            st.session_state["mostrar_selecao"] = True
            st.rerun()

def mostrar_selecao_manual():
    """Mostra a interface para seleção manual de tabelas com apenas uma opção permitida por tabela e visualização dos dados."""
    if not st.session_state.get("mostrar_selecao", False):
        return

    st.write("### Selecione os mapeamentos desejados:")

    resultados_filtrados = st.session_state.get("resultados_filtrados", [])
    info_mapeamentos = st.session_state.get("info_mapeamentos", {})
    tabelas_multiplos_destinos = st.session_state.get("tabelas_multiplos_destinos", {})
    tipo_conversao = st.session_state.get("tipo_conversao", "OC3_PARA_DATAMESH")

    selected_mappings_por_tabela = {}

    if info_mapeamentos:
        for tabela_origem, dados in info_mapeamentos.items():
            tem_multiplos_destinos = tabela_origem in tabelas_multiplos_destinos

            with st.expander(f"Tabela de origem: {tabela_origem}", expanded=True):
                if tem_multiplos_destinos:
                    st.warning(f"**Atenção:** Foram encontrados {len(dados['destinos'])} possíveis mapeamentos para a tabela '{tabela_origem}'.")

                    tabela_dados = []
                    opcoes = []
                    opcoes_dict = {}

                    for i, destino in enumerate(dados["destinos"], 1):
                        mapeamentos = dados["destinos_info"][destino]["items"]
                        item_representativo = mapeamentos[0]

                        for item in mapeamentos:
                            if tipo_conversao == "OC3_PARA_DATAMESH":
                                tabela_dados.append({
                                    "Opção": i,
                                    "Tabela OC3": tabela_origem,
                                    "Campo OC3": item.get("CAMPO OC3 LIGHT", ""),
                                    "Tabela DataMesh": item.get("TABELA DATA MESH", ""),
                                    "Campo DataMesh": item.get("CAMPO DATA MESH FINAL", ""),
                                    "Tipo": item.get("tipo", "")
                                })
                            else:
                                tabela_dados.append({
                                    "Opção": i,
                                    "Tabela SAC": tabela_origem,
                                    "Campo SAC": item.get("CAMPO SAC", ""),
                                    "Tabela OC3": item.get("TABELA OC3", ""),
                                    "Campo OC3": item.get("CAMPO OC3", ""),
                                    "Tipo": item.get("tipo", ""),
                                    "Descrição": item.get("DESCRITIVO", "")
                                })

                        # Montar label
                        if tipo_conversao == "OC3_PARA_DATAMESH":
                            campos = ", ".join([item.get("CAMPO OC3 LIGHT", "") for item in mapeamentos[:3]])
                            label = f"Opção {i}: {tabela_origem} → {item_representativo.get('TABELA DATA MESH', '')} (Campos: {campos}, Tipo: {item_representativo.get('tipo', '')})"
                        else:
                            campos = ", ".join([item.get("CAMPO SAC", "") for item in mapeamentos[:3]])
                            label = f"Opção {i}: {tabela_origem} → {item_representativo.get('TABELA OC3', '')} (Campos: {campos}, Tipo: {item_representativo.get('tipo', '')})"
                            if item_representativo.get("DESCRITIVO"):
                                label += f" - {item_representativo.get('DESCRITIVO')}"

                        opcoes.append(label)
                        opcoes_dict[label] = mapeamentos

                    if tabela_dados:
                        st.dataframe(pd.DataFrame(tabela_dados))

                    escolha = st.radio(
                        "Escolha uma das opções de mapeamento:",
                        options=opcoes,
                        key=f"radio_{tabela_origem}"
                    )

                    if escolha:
                        selected_mappings_por_tabela[tabela_origem] = opcoes_dict[escolha]

                else:
                    destino = next(iter(dados["destinos"]))
                    mapeamentos = dados["destinos_info"][destino]["items"]
                    item_representativo = mapeamentos[0]

                    if tipo_conversao == "OC3_PARA_DATAMESH":
                        tabela_destino = item_representativo.get("TABELA DATA MESH", "")
                        tipo_registro = item_representativo.get("tipo", "")
                        campos = ", ".join([item.get("CAMPO OC3 LIGHT", "") for item in mapeamentos[:3]])
                        label = f"Opção única: {tabela_origem} → {tabela_destino} (Campos: {campos}, Tipo: {tipo_registro})"
                    else:
                        tabela_destino = item_representativo.get("TABELA OC3", "")
                        tipo_registro = item_representativo.get("tipo", "")
                        descricao = item_representativo.get("DESCRITIVO", "")
                        campos = ", ".join([item.get("CAMPO SAC", "") for item in mapeamentos[:3]])
                        label = f"Opção única: {tabela_origem} → {tabela_destino} (Campos: {campos}, Tipo: {tipo_registro})"
                        if descricao:
                            label += f" - {descricao}"

                    st.markdown(f"✅ {label}")
                    selected_mappings_por_tabela[tabela_origem] = mapeamentos

    else:
        st.warning("Nenhum mapeamento encontrado para esta query.")

    if st.button("Confirmar seleção", type="primary"):
        selected_mappings = []
        for mapeamentos in selected_mappings_por_tabela.values():
            selected_mappings.extend(mapeamentos)

        if selected_mappings:
            st.session_state["aguardando_selecao"] = False
            st.session_state["mostrar_selecao"] = False
            st.session_state["esperando_resultado"] = True
            st.session_state["tipo_processamento"] = "Seleção manual de tabelas"
            st.session_state["tabelas_utilizadas"] = selected_mappings

            adicionar_mensagem("assistant", "Processando com os mapeamentos selecionados...")

            from .query_processing import processar_conversao
            processar_conversao()
        else:
            st.error("Por favor, selecione pelo menos uma opção por tabela.")

def bloquear_interacoes():
    """Impede que o usuário interaja com certas partes da interface durante o processamento."""
    if st.session_state.get("chat_em_progresso", False):
        st.warning("⚠️ A busca de campos está desativada enquanto o chat estiver em andamento. Clique em 'Iniciar Nova Conversão' para recomeçar.")
        
        # Cria uma aparência desabilitada visualmente
        st.markdown("""
            <style>
                .element-container:has(.campo-busca) {
                    opacity: 0.5;
                    pointer-events: none;
                }
            </style>
        """, unsafe_allow_html=True)

