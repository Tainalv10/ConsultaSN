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

def consultar_receita_oficial(cnpj_limpo):
    # Endpoint de consulta direta da Receita Federal
    url = "https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/GAS158/Simples.app/Simples/Exibir"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    payload = {
        "Cnpj": cnpj_limpo
    }
    
    session = requests.Session()
    
    try:
        # Envia a requisição POST diretamente ao portal oficial da Receita
        response = session.post(url, data=payload, headers=headers, timeout=12)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            texto = soup.get_text()
            
            # 1. Extrai Razão Social
            razao_social = "N/A"
            for linha in texto.split('\n'):
                if "Nome Empresarial:" in linha:
                    razao_social = linha.replace("Nome Empresarial:", "").strip()
                    break
            
            # 2. Verifica se é Optante pelo Simples Nacional
            optante_simples = "SIM" if "Optante pelo Simples Nacional desde" in texto else "NÃO"
            
            # 3. Verifica se é MEI / SIMEI
            optante_mei = "SIM" if "Enquadrado no SIMEI desde" in texto else "NÃO"
            
            # 4. REGIME HÍBRIDO: Verifica a tabela de Eventos Futuros (Regime Regular IBS/CBS)
            # Conforme os exemplos: Se constar "Opção pelo regime regular", é Híbrido
            eh_hibrido = "NÃO"
            
            # Procura no texto geral ou analisa as tabelas
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
                    "Simples Nacional": "Inválido",
                    "MEI / SIMEI": "N/A",
                    "Híbrido (IBS/CBS Regular)": "N/A",
                    "Status": "CNPJ Inválido"
                })
            else:
                res = consultar_receita_oficial(cnpj_limpo)
                resultados.append(res)
                
                # Pausa de 2 segundos para evitar bloqueio por requisições rápidas
                if i < total - 1:
                    time.sleep(2)
            
            progresso.progress((i + 1) / total)

        status_texto.success("✅ Consulta finalizada!")
        
        df = pd.DataFrame(resultados)
        st.subheader("📊 Resultados:")
        st.dataframe(df, use_container_width=True)
        
        # Gera o Excel para download
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='CNPJs')
        
        st.download_button(
            label="📥 Baixar Planilha Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name="resultado_cnpjs_hibrido.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
