# Assistente de Conversão de Consultas SQL

## Visão Geral

O Assistente de Conversão de Consultas SQL é uma aplicação baseada em Streamlit projetada para ajudar desenvolvedores e profissionais de dados a converter consultas SQL entre diferentes sistemas de banco de dados. A ferramenta suporta dois modos principais de conversão:

1. Conversão de OC3 para DataMesh (Athena)
2. Conversão de SAC para OC3

### Recursos Principais

- Conversão automática de consultas SQL
- Mapeamento inteligente de tabelas e colunas
- Interface de usuário interativa
- Tratamento robusto de erros
- Conversão com suporte de IA usando Amazon Bedrock

## Arquitetura do Sistema

### Componentes Principais

1. **Interface de Usuário (`ui.py`)**: 
   - Gerencia o layout do aplicativo Streamlit
   - Fornece abas interativas para conversão SQL e busca de campos
   - Trata interações e navegação do usuário

2. **Processamento de Consultas (`query_processing.py`)**: 
   - Valida e processa consultas SQL de entrada
   - Identifica possibilidades de mapeamento
   - Coordena o fluxo de trabalho de conversão

3. **Gerenciamento de Mapeamentos (`mapping_utils.py`)**: 
   - Carrega e gerencia configurações de mapeamento
   - Busca e filtra mapeamentos com base no conteúdo da consulta
   - Suporta diferentes tipos de conversão

4. **Utilitários de Conversão (`converters/`)**: 
   - Trata a lógica de conversão para diferentes mapeamentos de sistemas
   - Fornece estratégias de conversão com simulação e IA

5. **Integração com AWS**: 
   - Usa AWS Bedrock para conversão avançada de consultas
   - Suporta processamento baseado em funções Lambda

## Instalação e Configuração

### Pré-requisitos

- Python 3.8+
- Streamlit
- Conta AWS com acesso ao Bedrock
- Pacotes Python necessários (listados no `requirements.txt`)

### Configuração do Ambiente

1. Clonar o repositório
   ```bash
   git clone https://github.com/seu-usuario/assistente-conversao-sql.git
   cd assistente-conversao-sql
   ```

2. Criar ambiente virtual
   ```bash
   python -m venv venv
   source venv/bin/activate  # No Windows, use `venv\Scripts\activate`
   ```

3. Instalar dependências
   ```bash
   pip install -r requirements.txt
   ```

4. Configurar Credenciais AWS
   - Definir variáveis de ambiente ou usar configuração AWS CLI
   ```bash
   export AWS_ACCESS_KEY_ID=sua_chave_de_acesso
   export AWS_SECRET_ACCESS_KEY=sua_chave_secreta
   export AWS_SESSION_TOKEN=seu_token_de_sessao  # Se aplicável
   ```

5. Executar a aplicação
   ```bash
   streamlit run app.py
   ```

## Guia de Uso

### Modos de Conversão

1. **OC3 para DataMesh (Athena)**
   - Converter consultas do sistema OC3 para SQL compatível com Athena
   - Mapear automaticamente nomes de tabelas e colunas
   - Ajustar sintaxe para Presto SQL

2. **SAC para OC3**
   - Converter consultas do sistema SAC para o sistema OC3
   - Tratar transformações de nomes de tabelas e colunas
   - Preservar a lógica original da consulta

### Fluxo de Trabalho

1. Selecionar o modo de conversão
2. Inserir a consulta SQL
3. Revisar sugestões de mapeamento
4. Confirmar ou selecionar mapeamentos manualmente
5. Obter a consulta convertida

## Configuração de Mapeamento

Os mapeamentos são armazenados em arquivos JSON dentro do diretório `mapeamentos-de-para/`:
- `mapeamentos-oc3-datamesh/`: Mapeamentos de OC3 para DataMesh
- `mapeamentos-sac-oc3/`: Mapeamentos de SAC para OC3

### Exemplo de Estrutura de Mapeamento JSON

```json
[
  {
    "TABELA OC3 LIGHT": "CLIENTE",
    "CAMPO OC3 LIGHT": "ID_CLIENTE",
    "TABELA DATA MESH": "clientes",
    "CAMPO DATA MESH FINAL": "cliente_id",
    "tipo": "cadastro"
  }
]
```

## Recursos Avançados

- Correspondência inteligente de campos
- Múltiplas possibilidades de mapeamento
- Seleção de mapeamento manual e automática
- Tratamento detalhado de erros

## Registro de Logs

A aplicação usa um registrador personalizado (`logger_config.py`) para:
- Rastrear eventos da aplicação
- Registrar erros
- Monitorar processos de conversão

## Segurança e Desempenho

- Usa credenciais AWS baseadas em ambiente
- Implementa chamadas de API do Bedrock baseadas em token
- Otimiza operações de mapeamento com cache

## Solução de Problemas

- Verifique se as credenciais AWS estão configuradas corretamente
- Verifique se os arquivos JSON de mapeamento estão formatados corretamente
- Confirme a conectividade de rede com os serviços AWS

## Licença

[Especifique a licença do seu projeto]

## Contato

[Suas informações de contato ou canais de suporte]