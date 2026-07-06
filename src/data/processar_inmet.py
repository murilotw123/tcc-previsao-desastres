"""
Processa arquivos CSV do INMET:
- Extrai os 8 campos do cabeçalho (REGIAO, UF, ESTACAO, etc.)
- Transforma cada campo em uma coluna nas linhas de dados
- Concatena todos os arquivos em um único CSV limpo

Uso:
    python3 processar_inmet.py <pasta_com_csvs> [pasta_saida]

Exemplo:
    python3 processar_inmet.py ~/Downloads/INMET ~/Downloads/INMET_processado
"""

import sys
import os
import glob
import pandas as pd

HEADER_FIELDS = [
    "REGIAO",
    "UF",
    "ESTACAO",
    "CODIGO (WMO)",
    "LATITUDE",
    "LONGITUDE",
    "ALTITUDE",
    "DATA DE FUNDACAO",
]


def parse_metadata(filepath):
    """Lê as primeiras 8 linhas e retorna um dict com os metadados."""
    meta = {}
    with open(filepath, encoding="latin-1") as f:
        for _ in range(8):
            line = f.readline()
            # Suporta ; ou , como separador
            sep = ";" if ";" in line else ","
            parts = line.strip().split(sep)
            if len(parts) >= 2:
                key = parts[0].strip().rstrip(":")
                value = parts[1].strip()
                meta[key] = value
    return meta


def find_data_start(filepath):
    """Encontra a linha onde começa o cabeçalho de dados (após os metadados)."""
    with open(filepath, encoding="latin-1") as f:
        for i, line in enumerate(f):
            # A linha de cabeçalho dos dados contém "Data" ou "Hora UTC"
            if "Data" in line and ("Hora" in line or "UTC" in line or "PRECIPITA" in line):
                return i
    return 8  # fallback: pula as 8 linhas de metadados


def process_file(filepath):
    """Processa um único arquivo CSV do INMET e retorna um DataFrame."""
    print(f"  Processando: {os.path.basename(filepath)}")

    meta = parse_metadata(filepath)
    header_row = find_data_start(filepath)

    # Detecta separador
    with open(filepath, encoding="latin-1") as f:
        for _ in range(header_row):
            f.readline()
        sample = f.readline()
    sep = ";" if sample.count(";") > sample.count(",") else ","

    try:
        df = pd.read_csv(
            filepath,
            skiprows=header_row,
            sep=sep,
            encoding="latin-1",
            dtype=str,
            on_bad_lines="skip",
        )
    except Exception as e:
        print(f"    ERRO ao ler {filepath}: {e}")
        return None

    # Remove linhas totalmente vazias
    df = df.dropna(how="all")

    # Adiciona os metadados como colunas no início
    for field in reversed(HEADER_FIELDS):
        value = meta.get(field, "")
        df.insert(0, field, value)

    return df


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 processar_inmet.py <pasta_com_csvs> [pasta_saida]")
        sys.exit(1)

    input_folder = os.path.expanduser(sys.argv[1])
    output_folder = os.path.expanduser(sys.argv[2]) if len(sys.argv) > 2 else input_folder

    os.makedirs(output_folder, exist_ok=True)

    # Busca todos os CSVs na pasta (e subpastas)
    pattern_upper = os.path.join(input_folder, "**", "*.CSV")
    pattern_lower = os.path.join(input_folder, "**", "*.csv")
    files = glob.glob(pattern_upper, recursive=True) + glob.glob(pattern_lower, recursive=True)
    files = list(set(files))  # remove duplicatas

    if not files:
        print(f"Nenhum arquivo CSV encontrado em: {input_folder}")
        sys.exit(1)

    print(f"\nEncontrados {len(files)} arquivo(s) CSV.\n")

    all_dfs = []
    for filepath in sorted(files):
        df = process_file(filepath)
        if df is not None:
            all_dfs.append(df)

    if not all_dfs:
        print("Nenhum arquivo processado com sucesso.")
        sys.exit(1)

    # Salva arquivo único com todos os dados
    output_file = os.path.join(output_folder, "INMET_consolidado.csv")
    combined = pd.concat(all_dfs, ignore_index=True)
    combined.to_csv(output_file, index=False, encoding="utf-8-sig", sep=";")

    print(f"\nConcluido!")
    print(f"  Arquivos processados : {len(all_dfs)}")
    print(f"  Total de linhas      : {len(combined):,}")
    print(f"  Arquivo salvo em     : {output_file}")


if __name__ == "__main__":
    main()
