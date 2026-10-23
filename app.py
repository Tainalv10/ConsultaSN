import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import io

# Configuração da página
st.set_page_config(page_title="Consulta Simples Nacional - Híbrido", page_icon="🏢", layout="wide")

st.title("🏢 Consulta de CNPJs - Simples Nacional e Regime Híbrido (IBS/CBS)")
st.write("Insira os CNPJs abaixo (um por linha) para verificar a situação no Simples Nacional e Regime Híbrido.")

texto_cnpjs = st.text_area(
    "CNPJs para consulta:",
    height=150,
    placeholder="02.760.464/0001-21\n03.294.984/0001-59"
)

def consultar_via_api_fallback(cnpj_limpo):
    try:
        url = f"https://publica.cnpj.ws/cnpj/{cnpj_limpo}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            dados = resp.json()
            simples = dados.get("simples") or {}
            opt_s = simples.get("optante")
            opt_m = simples.get("simples")
            
            return {
                "CNPJ": cnpj_limpo,
                "Razão Social": dados.get("razao_social", "N/A"),
                "Simples Nacional": "SIM" if opt_s else "NÃO",
                "MEI / SIMEI": "SIM" if opt_m else "NÃO",
                "Híbrido (IBS/CBS Regular)": "Verificar Manualmente",
                "Status": "Sucesso (Via API)"
            }
    except Exception:
        pass
        
    return {
        "CNPJ": cnpj_limpo,
        "Razão Social": "N/A",
        "Simples Nacional": "Erro",
        "MEI / SIMEI": "Erro",
        "Híbrido (IBS/CBS Regular)": "Erro",
        "Status": "Falha na requisição"
    }

def consultar_receita_simples(cnpj_limpo):
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www8.receita.fazenda.gov.br/simplesnacional/aplicacoes.aspx?id=21"
    }
    
    try:
        init_url = "https://www8.receita.fazenda.gov.br/simplesnacional/aplicacoes.aspx?id=21"
        session.get(init_url, headers=headers, timeout=10)
        
        post_url = "https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/GAS158/Simples.app/Simples/Exibir"
        payload = {"Cnpj": cnpj_limpo}
        
        response = session.post(post_url, data=payload, headers=headers, timeout=12)
        
        if response.status_code == 200 and "Situação Atual" in response.text:
            soup = BeautifulSoup(response.text, 'html.parser')
            texto = soup.get_text()
            
            razao_social = "N/A"
            for linha in texto.split('\n'):
                if "Nome Empresarial:" in linha:
                    razao_social = linha.replace("Nome Empresarial:", "").strip()
                    break
            
            optante_simples = "SIM" if "Optante pelo Simples Nacional desde" in texto else "NÃO"
            optante_mei = "SIM" if "Enquadrado no SIMEI desde" in texto else "NÃO"
            
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
        else:
            return consultar_via_api_fallback(cnpj_limpo)
            
    except Exception:
        return consultar_via_api_fallback(cnpj_limpo)

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
                res = consultar_receita_simples(cnpj_limpo)
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
