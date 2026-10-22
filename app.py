import streamlit as st
import requests
import pandas as pd
import time
import io

# Configuração da página do site
st.set_page_config(page_title="Consulta Simples Nacional", page_icon="🏢", layout="wide")

st.title("🏢 Consulta de CNPJs - Simples Nacional")
st.write("Digite os CNPJs abaixo (um por linha) para verificar se são optantes do Simples Nacional ou MEI.")

# Campo onde o usuário vai colar os CNPJs
texto_cnpjs = st.text_area(
    "CNPJs para consulta:",
    height=150,
    placeholder="00.000.000/0001-91\n33.000.167/0001-01\n06.160.084/0001-23"
)

# Botão para iniciar a busca
if st.button("🚀 Iniciar Consulta", type="primary"):
    # Separa a lista de CNPJs linha por linha
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
                    "Simples Nacional": "CNPJ Inválido",
                    "MEI / SIMEI": "N/A"
                })
            else:
                url = f"https://publica.cnpj.ws/cnpj/{cnpj_limpo}"
                try:
                    resp = requests.get(url, timeout=10)
                    if resp.status_code == 200:
                        dados = resp.json()
                        simples = dados.get("simples") or {}
                        
                        opt_simples = simples.get("optante")
                        opt_mei = simples.get("simples")
                        
                        resultados.append({
                            "CNPJ": cnpj_limpo,
                            "Razão Social": dados.get("razao_social", "N/A"),
                            "Simples Nacional": "SIM" if opt_simples else ("NÃO" if opt_simples is False else "Não informado"),
                            "MEI / SIMEI": "SIM" if opt_mei else ("NÃO" if opt_mei is False else "Não informado")
                        })
                    else:
                        resultados.append({
                            "CNPJ": cnpj_limpo,
                            "Razão Social": "N/A",
                            "Simples Nacional": "Não encontrado / Limite excedido",
                            "MEI / SIMEI": "N/A"
                        })
                except Exception:
                    resultados.append({
                        "CNPJ": cnpj_limpo,
                        "Razão Social": "N/A",
                        "Simples Nacional": "Erro na conexão",
                        "MEI / SIMEI": "N/A"
                    })
                
                # Aguarda para respeitar o limite gratuito da API
                if i < total - 1:
                    time.sleep(20)
            
            # Atualiza a barra de progresso no site
            progresso.progress((i + 1) / total)

        status_texto.success("✅ Consulta finalizada com sucesso!")
        
        # Mostra a tabela com os resultados
        df = pd.DataFrame(resultados)
        st.subheader("📊 Resultados:")
        st.dataframe(df, use_container_width=True)
        
        # Cria o arquivo Excel para o usuário baixar
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='CNPJs')
        
        st.download_button(
            label="📥 Baixar Planilha em Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name="resultado_cnpjs.xlsx",
            mime="application/vnd.openxml
