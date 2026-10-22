import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import io

# Configuração da página
st.set_page_config(page_title="Consulta Simples Nacional - Híbrido", page_icon="🏢", layout="wide")

st.title("🏢 Consulta de CNPJs - Simples Nacional e Regime Híbrido (IBS/CBS)")
st.write("Insira os CNPJs (um por linha) para verificar o enquadramento no Simples Nacional, MEI e Regime Híbrido (IBS/CBS).")

texto_cnpjs = st.text_area(
    "CNPJs para consulta:",
    height=150,
    placeholder="03.294.984/0001-59\n33.000.167/0001-01"
)

def consultar_receita(cnpj_limpo):
    url = f"https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/GAS158/Simples.app/Simples/Exibir/{cnpj_limpo}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            texto_pagina = soup.get_text()
            
            # 1. Verifica Simples Nacional
            optante_simples = "SIM" if "Optante pelo Simples Nacional desde" in texto_pagina else "NÃO"
            
            # 2. Verifica MEI / SIMEI
            optante_mei = "SIM" if "Enquadrado no SIMEI desde" in texto_pagina else "NÃO"
            
            # 3. Verifica se é HÍBRIDO (Eventos Futuros no Regime Regular IBS/CBS)
            # Se constar "Opção pelo regime regular" dentro da tabela de eventos futuros
            eh_hibrido = "NÃO"
            if "Opção pelo regime regular" in texto_pagina or "Eventos Futuros (Regime Regular IBS/CBS)" in texto_pagina:
                # Busca se há opção explícita cadastrada nos eventos futuros
                if "Opção pelo regime regular" in texto_pagina:
                    eh_hibrido = "SIM (Híbrido)"
            
            # Extrai Razão Social se disponível
            razao_social = "Não identificada"
            for linha in texto_pagina.split('\n'):
                if "Nome Empresarial:" in linha:
                    razao_social = linha.replace("Nome Empresarial:", "").strip()
                    break

            return {
                "CNPJ": cnpj_limpo,
                "Razão Social": razao_social,
                "Simples Nacional": optante_simples,
                "MEI / SIMEI": optante_mei,
                "Híbrido (IBS/CBS Regular)": eh_hibrido,
                "Status": "Sucesso"
            }
        else:
            return {
                "CNPJ": cnpj_limpo,
                "Razão Social": "N/A",
                "Simples Nacional": "Erro",
                "MEI / SIMEI": "Erro",
                "Híbrido (IBS/CBS Regular)": "Erro",
                "Status": f"HTTP {response.status_code}"
            }
    except Exception as e:
        return {
            "CNPJ": cnpj_limpo,
            "Razão Social": "N/A",
            "Simples Nacional": "Erro",
            "MEI / SIMEI": "Erro",
            "Híbrido (IBS/CBS Regular)": "Erro",
            "Status": "Falha na conexão"
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
                    "Simples Nacional": "Invalido",
                    "MEI / SIMEI": "N/A",
                    "Híbrido (IBS/CBS Regular)": "N/A",
                    "Status": "CNPJ Inválido"
                })
            else:
                res = consultar_receita(cnpj_limpo)
                resultados.append(res)
                
                # Pequena pausa para evitar bloqueio do servidor
                if i < total - 1:
                    time.sleep(2)
            
            progresso.progress((i + 1) / total)

        status_texto.success("✅ Consulta finalizada!")
        
        df = pd.DataFrame(resultados)
        st.subheader("📊 Resultados:")
        st.dataframe(df, use_container_width=True)
        
        # Gera arquivo Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='CNPJs')
