#!/usr/bin/env python3
"""
Script para converter planilhas Excel para arquivos JSON

Este script lê todas as abas de planilhas Excel em uma pasta,
identifica as tabelas em cada aba e gera um arquivo JSON para cada aba.
"""

import os
import re
import json
import pandas as pd
from openpyxl import load_workbook


def sanitize_filename(name):
    """Sanitiza o nome do arquivo para evitar caracteres inválidos."""
    return re.sub(r'[^a-z0-9]', '_', name.lower())


def identify_tables(data):
    """
    Identifica tabelas em uma matriz de dados.
    
    Esta função busca por tabelas em dados de planilha, onde uma tabela é identificada por:
    1. Uma linha com o nome da tabela
    2. Seguida por uma linha com a descrição da tabela
    3. Seguida por uma linha com os cabeçalhos das colunas (pode incluir 'Campo' ou outros)
    4. Seguida por linhas de dados dos campos
    
    Args:
        data (list): Uma lista de listas representando as linhas e colunas dos dados.
        
    Returns:
        list: Uma lista de dicionários representando as tabelas encontradas.
    """
    tables = []
    current_table = None
    is_in_table = False
    header_row = None
    
    i = 0
    while i < len(data):
        row = data[i]
        first_cell = row[0].strip() if row and isinstance(row[0], str) else ''
        
        # Verifica se é uma linha vazia
        is_empty_row = all(not cell or (isinstance(cell, str) and cell.strip() == '') for cell in row)
        
        # Se for uma linha vazia e estiver em uma tabela, finaliza a tabela atual
        if is_empty_row and is_in_table:
            if current_table and current_table.get('campos', []):
                tables.append(current_table)
            current_table = None
            is_in_table = False
            header_row = None
            i += 1
            continue
        
        # Se for uma linha vazia, pula
        if is_empty_row:
            i += 1
            continue
        
        # Verifica se é o início de uma nova tabela (analisando o padrão da tabela)
        # Uma tabela é identificada pelo nome da tabela seguido de uma descrição e headers
        if not is_in_table and first_cell and len(first_cell) > 0 and i+2 < len(data):
            # Verifica se próximas linhas seguem o padrão de uma tabela
            next_row = data[i+1] if i+1 < len(data) else []
            header_candidate = data[i+2] if i+2 < len(data) else []
            
            # Verifica se a próxima linha tem descrição e a linha seguinte tem cabeçalhos
            if (next_row and any(cell for cell in next_row) and 
                header_candidate and len([c for c in header_candidate if c]) >= 2):
                # Considera que encontramos uma tabela se:
                # 1. A primeira linha tem conteúdo (nome da tabela)
                # 2. A segunda linha tem algum conteúdo (descrição)
                # 3. A terceira linha tem pelo menos 2 células com conteúdo (possíveis cabeçalhos)
                is_in_table = True
                current_table = {
                    "tipo": "conversaotal",  # Valor mockado conforme requisito
                    "tabela": first_cell,
                    "descritivoTabela": next_row[0] if next_row and next_row[0] else "Sem descrição",
                    "campos": []
                }
                
                # Avança para a linha de descrição
                i += 1
                
                # A próxima linha não vazia deve ser o cabeçalho
                j = i + 1
                while j < len(data):
                    if not all(not cell or (isinstance(cell, str) and cell.strip() == '') for cell in data[j]):
                        header_row = data[j]
                        i = j  # Avança para a linha de cabeçalho
                        break
                    j += 1
                i += 1
                continue
        
        # Se estiver em uma tabela e tiver cabeçalho, processa os campos
        if is_in_table and header_row and current_table:
            # Verifica se a linha atual é um campo da tabela (não é índice nem bytes por linha)
            if first_cell and not (first_cell.startswith('ip_') or 
                                  first_cell.startswith('idx_') or 
                                  first_cell.startswith('pk_') or 
                                  first_cell.startswith('fk_') or 
                                  'bytes por linha' in first_cell):
                campo = {}
                
                # Mapeia as colunas para as propriedades do campo
                for col_index, header in enumerate(header_row):
                    if header and col_index < len(row):
                        header_key = header.strip().lower() if isinstance(header, str) else ''
                        value = row[col_index]
                        value = value.strip() if isinstance(value, str) else value
                        value = str(value) if value is not None else '-'
                        
                        # Mapeamento padrão de cabeçalhos conhecidos
                        if header_key == 'campo':
                            campo['campo'] = value
                        elif header_key == 'tipo':
                            campo['tipoCampo'] = value
                        elif header_key == 'tam':
                            campo['tam'] = value
                        elif header_key == 'nulo':
                            campo['nulo'] = value
                        elif header_key == 'base':
                            campo['base'] = value
                        elif header_key == 'tabela_origem':
                            campo['tabelaOrigem'] = value
                        elif header_key == 'campo_origem':
                            campo['campoOrigem'] = value
                        elif header_key == 'descricao':
                            campo['descricao'] = value
                        elif header_key == 'ambiente':
                            campo['ambiente'] = value
                        elif header_key == 'data':
                            campo['data'] = value
                        elif header_key == 'responsavel':
                            campo['responsavel'] = value
                        elif header_key == 'bytes':
                            campo['bytes'] = value
                        else:
                            # Para colunas não mapeadas, adiciona com seu nome original (limpo)
                            if header_key:
                                # Substitui espaços por underscores e remove caracteres especiais para chaves JSON válidas
                                clean_key = re.sub(r'[^a-z0-9_]', '', header_key.replace(' ', '_'))
                                if clean_key:  # Se ainda tiver algum caractere após a limpeza
                                    campo[clean_key] = value
                
                # Adiciona o campo à tabela somente se tiver pelo menos um valor válido
                if campo and any(v for k, v in campo.items() if v != '-'):
                    current_table['campos'].append(campo)
            
            # Verifica se a linha é um índice (pode começar com ip_, idx_, pk_, fk_, etc)
            elif (first_cell.startswith('ip_') or 
                  first_cell.startswith('idx_') or 
                  first_cell.startswith('pk_') or 
                  first_cell.startswith('fk_')):
                if 'indices' not in current_table:
                    current_table['indices'] = []
                
                # Obtém o nome do índice
                indice = {
                    "nome": first_cell,
                    "campos": []
                }
                
                # Obtém os campos do índice na próxima linha
                if i + 1 < len(data):
                    next_row = data[i + 1]
                    if next_row and next_row[0]:
                        # Tenta extrair os campos do índice
                        campos_indice = re.sub(r'["\'"]', '', str(next_row[0]))  # Remove aspas
                        campos_indice = [c.strip() for c in campos_indice.split(',') if c.strip()]  # Divide por vírgula
                        
                        indice['campos'] = campos_indice
                        i += 1  # Avança para a linha dos campos do índice
                
                current_table['indices'].append(indice)
            
            # Verifica se é uma linha de bytes por linha ou tamanho total
            elif 'bytes por linha' in first_cell or 'tamanho total' in first_cell.lower():
                # Tenta extrair o número (bytes por linha ou tamanho total)
                bytes_match = re.search(r'(bytes por linha|tamanho total)\s*(\d+)', first_cell, re.I)
                if bytes_match:
                    if 'bytes por linha' in first_cell.lower():
                        current_table['bytesPorLinha'] = bytes_match.group(2)
                    else:
                        current_table['tamanhoTotal'] = bytes_match.group(2)
        
        i += 1
    
    # Adiciona a última tabela se existir
    if current_table and current_table.get('campos', []):
        tables.append(current_table)
    
    return tables


def process_excel(file_path, output_dir):
    """
    Processa um arquivo Excel e cria arquivos JSON para cada aba.
    
    Args:
        file_path (str): Caminho para o arquivo Excel.
        output_dir (str): Diretório onde os arquivos JSON serão salvos.
    """
    print(f"Processando arquivo: {file_path}")
    
    # Carrega o workbook
    workbook = load_workbook(file_path, read_only=True, data_only=True)
    
    # Obtém a lista de todas as abas
    sheet_names = workbook.sheetnames
    print(f"Encontradas {len(sheet_names)} abas no arquivo Excel.")
    
    # Processa cada aba
    for sheet_name in sheet_names:
        print(f"Processando aba: {sheet_name}")
        
        # Obtém a planilha
        sheet = workbook[sheet_name]
        
        # Converter a planilha para uma lista de listas (matriz)
        data = []
        for row in sheet.rows:
            data_row = []
            for cell in row:
                data_row.append(cell.value)
            data.append(data_row)
        
        # Identifica as tabelas na aba
        tables = identify_tables(data)
        
        # Se não encontrou tabelas, tenta um método alternativo
        if not tables and data:
            print(f"  Usando método alternativo para identificar tabelas na aba {sheet_name}...")
            # Procura por possíveis cabeçalhos de tabela (linhas com múltiplas células não vazias)
            for i, row in enumerate(data):
                if i+1 < len(data) and sum(1 for cell in row if cell) >= 3:
                    # Considera esta linha como cabeçalho se tiver 3+ células com conteúdo
                    header_row = row
                    
                    # Extrai linhas que parecem ser dados (até encontrar linha vazia)
                    campos = []
                    j = i + 1
                    while j < len(data) and any(cell for cell in data[j]):
                        campo = {}
                        for col_index, header in enumerate(header_row):
                            if header and col_index < len(data[j]):
                                header_key = str(header).strip().lower() if header else ''
                                value = data[j][col_index]
                                value = str(value).strip() if value is not None else '-'
                                
                                # Sanitiza nome da chave
                                clean_key = re.sub(r'[^a-z0-9_]', '', header_key.replace(' ', '_'))
                                if clean_key:
                                    campo[clean_key] = value
                        
                        if campo and any(v for k, v in campo.items() if v != '-'):
                            campos.append(campo)
                        j += 1
                    
                    if campos:
                        tables.append({
                            "tipo": "conversaotal",
                            "tabela": f"tabela_{len(tables)+1}",
                            "descritivoTabela": f"Tabela encontrada na aba {sheet_name}",
                            "campos": campos
                        })
                        # Pula para depois dos dados processados
                        i = j
        
        print(f"Encontradas {len(tables)} tabelas na aba {sheet_name}.")
        
        # Cria o JSON para a aba
        sheet_json = {
            "aba": sheet_name,
            "tabelas": tables
        }
        
        # Salva o JSON da aba
        output_file = os.path.join(output_dir, f"{sanitize_filename(sheet_name)}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sheet_json, f, ensure_ascii=False, indent=2)
        print(f"Arquivo salvo: {output_file}")


def main():
    """Função principal que processa todos os arquivos Excel em uma pasta e gera os arquivos JSON."""
    import argparse
    
    # Configura o parser de argumentos
    parser = argparse.ArgumentParser(description='Converte tabelas de arquivos Excel para JSON.')
    parser.add_argument('--input-dir', '-i', default='mapeamentos_sac', 
                        help='Pasta contendo os arquivos Excel (.xlsx) (padrão: mapeamentos_sac)')
    parser.add_argument('--output-dir', '-o', default='output', 
                        help='Diretório onde serão salvos os arquivos JSON (padrão: output)')
    
    # Parse dos argumentos
    args = parser.parse_args()
    
    # Validações básicas
    if not os.path.exists(args.input_dir):
        print(f"Erro: A pasta {args.input_dir} não existe.")
        return
    
    if not os.path.isdir(args.input_dir):
        print(f"Erro: {args.input_dir} não é uma pasta.")
        return
    
    # Garante que o diretório de saída existe
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Lista todos os arquivos Excel na pasta
    excel_files = []
    for file in os.listdir(args.input_dir):
        if file.lower().endswith('.xlsx') and not file.startswith('~$'):  # Ignora arquivos temporários
            excel_files.append(os.path.join(args.input_dir, file))
    
    if not excel_files:
        print(f"Nenhum arquivo Excel (.xlsx) encontrado na pasta {args.input_dir}.")
        return
    
    print(f"Encontrados {len(excel_files)} arquivos Excel para processar.")
    
    # Processa cada arquivo Excel
    for excel_file in excel_files:
        try:
            print(f"\nProcessando arquivo: {excel_file}")
            process_excel(excel_file, args.output_dir)
        except Exception as e:
            print(f"Erro ao processar o arquivo {excel_file}: {e}")
    
    print("\nProcessamento concluído!")


if __name__ == "__main__":
    main()