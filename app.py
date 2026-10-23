import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import time
import io
import subprocess
import os

# Instala os navegadores do Playwright se não estiverem instalados no servidor
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    subprocess.run(["playwright", "install", "chromium"])
    from playwright.sync_api import sync_playwright

# Configuração da página
st.set_page_config(page_title="Consulta Simples Nacional - Híbrido", page_icon="🏢", layout="wide")

st.title("🏢 Consulta de CNPJs - Simples Nacional e Regime Híbrido (IBS/CBS)")
st.write("Insira os CNPJs abaixo (um por linha) para verificar o enquadramento fiscal e regime Híbrido.")

texto_cnpjs = st.text_area(
    "CNPJs para consulta:",
    height=150,
    placeholder="02.760.464/0001-21\n03.294.984/0001-59"
)

def consultar_com_navegador(cnpj_limpo):
    url = "https://www8.receita.fazenda.gov.br/simplesnacional/aplicacoes.aspx?id=21"
    
    with sync_playwright() as p:
        # Abre o navegador em modo invisível (headless)
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page()
        
        try:
            page.goto(url, wait_until="networkidle", timeout=25000)
            
            # Preenche o campo do CNPJ
            page.fill("input[name*='Cnpj']", cnpj_limpo)
            
            # Clica no botão de consulta
            page.click("button[type='submit'], input[type='submit']")
            page.wait_for_load_state("networkidle", timeout=25000)
            
            # Obtém o conteúdo HTML completo retornado pela Receita
            html = page.content()
            browser.close()
            
            soup = BeautifulSoup(html, 'html.parser')
            texto = soup.get_text()
            
            # 1. Razão Social
            razao_social = "N/A"
            for linha in texto.split('\n'):
                if "Nome Empresarial:" in linha:
                    razao_social = linha.replace("Nome Empresarial:", "").strip()
                    break
            
            # 2. Simples Nacional
            optante_simples = "SIM" if "Optante pelo Simples Nacional desde" in texto else "NÃO"
            
            # 3. MEI / SIMEI
            optante_mei = "SIM" if "Enquadrado no SIMEI desde" in texto else "NÃO"
            
            # 4. REGIME HÍBRIDO (Eventos Futuros IBS/CBS)
            eh_hibrido = "NÃO"
            if "Opção pelo regime regular" in texto:
                eh_hibrido = "SIM (Híbrido)"
            
            return {
                "CNPJ": cnpj_limpo,
                "Razão Social": razao_social,
                "Simples Nacional": optante_simples,
                "MEI / SIMEI": optante_mei,
                "Híbrido (IBS/CBS Regular)": eh_hibrido,
                "Status": "Sucesso"
            }
            
        except Exception as e:
            browser.close()
            return {
                "CNPJ": cnpj_limpo,
                "Razão Social": "N/A",
                "Simples Nacional": "Erro",
                "MEI / SIMEI": "Erro",
                "Híbrido (IBS/CBS Regular)": "Erro na Consulta",
                "Status": f"Falha ao carregar página oficial"
            }

if st.button("🚀 Iniciar Consulta", type="primary"):
    cnpjs = [linha.strip() for linha in texto_cnpjs.split("\n") if linha.strip()]
    
    if not cnpjs:
        st.warning("Por favor, digite ao menos um CNPJ.")
    else:
        resultados = []
        progresso = st.progress(0)
        status_texto = st.empty()
        
        total = len(cnpjs)
        
        for i, cnpj in enumerate(cnpjs):
            cnpj_limpo = ''.join(filter(str.isdigit, str(cnpj)))
            status_texto.text(f"Consultando {i+1} de {total}: CNPJ {cnpj_limpo}...")
            
            if len(cnpj_limpo) != 14:
                resultados.append({
                    "CNPJ": cnpj,
                    "Razão Social": "N/A",
                    "Simples Nacional": "Inválido",
                    "MEI / SIMEI": "N/A",
                    "Híbrido (IBS/CBS Regular)": "N/A",
                    "Status": "CNPJ Inválido"
                })
            else:
                res = consultar_com_navegador(cnpj_limpo)
                resultados.append(res)
                
                if i < total - 1:
                    time.sleep(2)
            
            progresso.progress((i + 1) / total)

        status_texto.success("✅ Consulta finalizada!")
        
        df = pd.DataFrame(resultados)
        st.subheader("📊 Resultados:")
        st.dataframe(df, use_container_width=True)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='CNPJs')
        
        st.download_button(
            label="📥 Baixar Planilha Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name="resultado_cnpjs_hibrido.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
