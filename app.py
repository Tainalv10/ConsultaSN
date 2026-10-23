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

def consultar_receita_simples(cnpj_limpo):
    # Sessão HTTP para manter cookies
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www8.receita.fazenda.gov.br/simplesnacional/aplicacoes.aspx?id=21"
    }
    
    try:
        # Passo 1: Acessar a página inicial para capturar cookies e sessão
        init_url = "https://www8.receita.fazenda.gov.br/simplesnacional/aplicacoes.aspx?id=21"
        session.get(init_url, headers=headers, timeout=10)
        
        # Passo 2: Fazer a consulta do CNPJ
        post_url = "https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/GAS158/Simples.app/Simples/Exibir"
        payload = {"Cnpj": cnpj_limpo}
        
        response = session.post(post_url, data=payload, headers=headers, timeout=12)
        
        if response.status_code == 200 and "Situação Atual" in response.text:
            soup = BeautifulSoup(response.text, 'html.parser')
            texto = soup.get_text()
            
            # Razão Social
            razao_social = "N/A"
            for linha in texto.split('\n'):
                if "Nome Empresarial:" in linha:
                    razao_social = linha.replace("Nome Empresarial:", "").strip()
                    break
            
            # Simples Nacional e MEI
            optante_simples = "SIM" if "Optante pelo Simples Nacional desde" in texto else "NÃO"
            optante_mei = "SIM" if "Enquadrado no SIMEI desde" in texto else "NÃO"
            
            # Checagem de HÍBRIDO (Eventos Futuros - Regime Regular IBS/CBS)
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
            # Contingência via API se a Receita solicitar Captcha ou bloquear
            return consultar_via_api_fallback(cnpj_limpo)
            
    except Exception:
        return consultar_via_api_fallback(cnpj_limpo
