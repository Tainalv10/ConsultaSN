import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io

# Configuração da página do site
st.set_page_config(page_title="Consulta CNPJ - Regime Híbrido", page_icon="🏢", layout="wide")

st.title("🏢 Verificador de CNPJ - Simples Nacional & Regime Híbrido")
st.write("Verifique em lote se as empresas pertencem ao Simples Nacional, MEI ou ao **Regime Híbrido (IBS/CBS)**.")

# Abas para alternar entre os modos
aba_automatica, aba_manual = st.tabs(["🚀 Consulta Automática (Lote)", "📋 Leitor de Texto / HTML (100% Garantido)"])

def extrair_dados_html(html_ou_texto, cnpj_identificador=""):
    soup = BeautifulSoup(html_ou_texto, 'html.parser')
    texto = soup.get_text()
    
    # Extrai Razão Social
    razao_social = "Não identificada"
    for linha in texto.split('\n'):
        if "Nome Empresarial:" in linha:
            razao_social = linha.replace("Nome Empresarial:", "").strip()
            break
            
    # Extrai CNPJ da página se disponível
    cnpj_encontrado = cnpj_identificador
    for linha in texto.split('\n'):
        if "CNPJ:" in linha:
            cnpj_encontrado = linha.replace("CNPJ:", "").strip()
            break

    # Situação Simples e MEI
    optante_simples = "SIM" if "Optante pelo Simples Nacional desde" in texto else ("NÃO" if "Não optante pelo Simples Nacional" in texto else "Não informado")
    optante_mei = "SIM" if "Enquadrado no SIMEI desde" in texto else ("NÃO" if "NÃO enquadrado no SIMEI" in texto else "Não informado")
    
    # REGIME HÍBRIDO: Verifica a opção pelo regime regular no bloco de IBS/CBS
    eh_hibrido = "NÃO"
    if "Opção pelo regime regular" in texto:
        eh_hibrido = "SIM (Híbrido)"
    elif "Não Existem" in texto and "Eventos Futuros (Regime Regular IBS/CBS)" in texto:
        eh_hibrido = "NÃO"

    return {
        "CNPJ": cnpj_encontrado,
        "Razão Social": razao_social,
        "Simples Nacional": optante_simples,
        "MEI / SIMEI": optante_mei,
        "Híbrido (IBS/CBS Regular)": eh_hibrido
    }

# --- ABA 1: CONSULTA AUTOMÁTICA VIA REQUISIÇÃO ---
with aba_automatica:
    st.subheader("Insira a lista de CNPJs")
    texto_cnpjs = st.text_area(
        "CNPJs (um por linha):",
        height=120,
        placeholder="03.294.984/0001-59\n02.760.464/0001-21"
    )
    
    if st.button("🔍 Consultar Lote", type="primary"):
        cnpjs = [linha.strip() for linha in texto_cnpjs.split("\n") if linha.strip()]
        if not cnpjs:
            st.warning("Por favor, digite ao menos um CNPJ.")
        else:
            resultados = []
            progresso = st.progress(0)
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            
            for i, cnpj in enumerate(cnpjs):
                cnpj_limpo = ''.join(filter(str.isdigit, str(cnpj)))
                url = f"https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/GAS158/Simples.app/Simples/Exibir"
                
                try:
                    resp = requests.post(url, data={"Cnpj": cnpj_limpo}, headers=headers, timeout=8)
                    if resp.status_code == 200 and "Situação Atual" in resp.text:
                        dados = extrair_dados_html(resp.text, cnpj_limpo)
                        dados["Status"] = "Sucesso"
                        resultados.append(dados)
                    else:
                        resultados.append({
                            "CNPJ": cnpj_limpo,
                            "Razão Social": "N/A",
                            "Simples Nacional": "N/A",
                            "MEI / SIMEI": "N/A",
                            "Híbrido (IBS/CBS Regular)": "Bloqueado pela Receita",
                            "Status": "Use a Aba 'Leitor de Texto'"
                        })
                except Exception:
                    resultados.append({
                        "CNPJ": cnpj_limpo,
                        "Razão Social": "N/A",
                        "Simples Nacional": "Erro",
                        "MEI / SIMEI": "Erro",
                        "Híbrido (IBS/CBS Regular)": "Erro de Conexão",
                        "Status": "Use a Aba 'Leitor de Texto'"
                    })
                
                progresso.progress((i + 1) / len(cnpjs))

            df = pd.DataFrame(resultados)
            st.dataframe(df, use_container_width=True)
            
            # Exportar Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Resultados')
            
            st.download_button("📥 Baixar Excel (.xlsx)", data=buffer.getvalue(), file_name="resultado_cnpjs.xlsx")

# --- ABA 2: LEITOR DE TEXTO/HTML (GARANTIDO SEM ERROS) ---
with aba_manual:
    st.subheader("Análise Direta de Conteúdo (Sem Bloqueios)")
    st.markdown("""
    **Como usar:**
    1. Abra o site da Receita Federal: [Portal Simples Nacional](https://www8.receita.fazenda.gov.br/simplesnacional/aplicacoes.aspx?id=21)
    2. Pesquise o CNPJ desejado.
    3. Selecione todo o texto da página (Ctrl+A), copie (Ctrl+C) e cole no campo abaixo:
    """)
    
    conteudo_colado = st.text_area("Cole o texto ou HTML da consulta da Receita aqui:", height=200)
    
    if st.button("📊 Processar Conteúdo Colado"):
        if not conteudo_colado.strip():
            st.warning("Por favor, cole o texto da página da Receita.")
        else:
            res = extrair_dados_html(conteudo_colado)
            df_manual = pd.DataFrame([res])
            
            st.success("✅ Leitura realizada com sucesso!")
            st.dataframe(df_manual, use_container_width=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_manual.to_excel(writer, index=False, sheet_name='Resultado')
            
            st.download_button("📥 Baixar Resultado em Excel (.xlsx)", data=buffer.getvalue(), file_name="resultado_manual.xlsx")
