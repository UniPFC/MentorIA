import argparse
import os
import re
import sys

import pandas as pd


def analyze_and_clean(file_path, clean_loose_letters=False):
    if not os.path.exists(file_path):
        print(f"Erro: Arquivo '{file_path}' não encontrado.")
        sys.exit(1)

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Erro ao ler arquivo: {e}")
        sys.exit(1)

    cols = df.columns
    q_col = cols[0]
    a_col = cols[1] if len(cols) > 1 else cols[0]

    bad_rows = []

    # Cleaning counts
    cleaned_loose_letters = 0

    # Iterar copiando dados caso vá limpar
    for idx, row in df.iterrows():
        answer_text = str(row[a_col])
        question_text = str(row[q_col])

        issues = []

        # 1. "não disponível"
        if (
            "não disponível" in answer_text.lower()
            or "não disponível" in question_text.lower()
        ):
            issues.append("Contém 'não disponível'")

        # 2. "(cid:"
        if "(cid:" in answer_text.lower() or "(cid:" in question_text.lower():
            issues.append("Contém caracteres (cid:...)")

        # 3. Letra solta no final da resposta
        if re.search(r"\s[A-Ea-e]\.?\s*$", answer_text):
            issues.append("Letra de alternativa solta no final da resposta")
            if clean_loose_letters:
                # Efetuar a limpeza
                new_answer = re.sub(r"\s+[A-Ea-e]\.?\s*$", "", answer_text)
                df.at[idx, a_col] = new_answer
                cleaned_loose_letters += 1

        if issues:
            bad_rows.append(
                {
                    "Linha": idx + 2,
                    "Problemas": ", ".join(issues),
                    "Pergunta (trecho)": question_text[:80].replace("\n", " ") + "..."
                    if len(question_text) > 80
                    else question_text.replace("\n", " "),
                    "Resposta (trecho)": answer_text[:120].replace("\n", " ") + "..."
                    if len(answer_text) > 120
                    else answer_text.replace("\n", " "),
                }
            )

    # Save cleaned file if requested
    if clean_loose_letters and cleaned_loose_letters > 0:
        out_path = file_path
        try:
            df.to_excel(out_path, index=False)
            print(f"[*] Limpeza concluída. {cleaned_loose_letters} linhas corrigidas.")
            print(f"[*] Arquivo original sobrescrito com as correções: {out_path}\n")
        except Exception as e:
            print(f"Erro ao salvar arquivo corrigido: {e}")

    # Generate Markdown Report
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(script_dir, "relatorio_planilha.md")
    with open(report_path, "w", encoding="utf-8") as f:
        rel_path = os.path.relpath(file_path)
        f.write("# Relatório de Análise da Planilha\n\n")
        f.write(f"**Arquivo Analisado:** `{rel_path}`\n\n")
        f.write(f"**Total de Linhas:** `{len(df)}`\n\n")
        f.write(f"**Linhas com Problemas Encontradas:** `{len(bad_rows)}`\n\n")

        if clean_loose_letters:
            f.write(
                f"**Limpeza Automática:** Foram corrigidas `{cleaned_loose_letters}` alternativas soltas.\n\n"
            )

        if bad_rows:
            f.write("## Linhas Identificadas\n\n")
            f.write(
                "| Planilha Linha | Problemas | Pergunta (Trecho) | Resposta (Trecho) |\n"
            )
            f.write("|---|---|---|---|\n")
            for br in bad_rows:
                q = br["Pergunta (trecho)"].replace("|", "\\|")
                a = br["Resposta (trecho)"].replace("|", "\\|")
                f.write(f"| {br['Linha']} | {br['Problemas']} | {q} | {a} |\n")
        else:
            f.write("Nenhum problema encontrado nas linhas.\n")

    print(f"[*] Análise concluída. {len(bad_rows)} linhas com problemas encontradas.")
    print(f"[*] Relatório detalhado gerado em: {report_path}")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_excel = os.path.join(
        script_dir, "ENEM --- Conhecimento do ENEM de 2020 à 2025.xlsx"
    )

    parser = argparse.ArgumentParser(
        description="Analisa e opcionalmente limpa planilhas de perguntas/respostas do MentorIA."
    )
    parser.add_argument(
        "file_path",
        nargs="?",
        default=default_excel,
        help="Caminho para o arquivo .xlsx",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Ativar limpeza automática das alternativas soltas no final das respostas",
    )

    args = parser.parse_args()

    analyze_and_clean(args.file_path, args.clean)
