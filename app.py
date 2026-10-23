import streamlit as st
import pandas as pd
import requests
import time
import io

# Configuração da página
st.set_page_config(page_title="Consulta Simples Nacional - Híbrido", page_icon="🏢", layout="wide")

st.title("🏢 Consulta de CNPJs - Simples Nacional e Regime Híbrido (IBS/CBS)")
st.write("Insira os CNPJs abaixo (um por linha) para verificar o enquadramento fiscal.")

texto_cnpjs = st.text_area(
    "CNPJs para consulta:",
    height=150,
    placeholder="02.760.464/0001-21\n03.294.984/0001-59"
)

def consultar_cnpj(cnpj_limpo):
    # 1. Consulta via BrasilAPI (Rápida e sem erros 404)
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            dados = response.json()
            
            razao_social = dados.get("razao_social", "N/A")
            opcao_simples = dados.get("opcao_pelo_simples")
            opcao_mei = dados.get("opcao_pelo_mei")
            
            simples_str = "SIM" if opcao_simples is True else ("NÃO" if opcao_simples is False else "Não informado")
            mei_str = "SIM" if opcao_mei is True else ("NÃO" if opcao_mei is False else "Não informado")
            
            # 2. Verificação do Regime Híbrido (IBS/CBS)
            # Empresas optantes pelo Simples que possuem opção declarada para o recolhimento regular do IBS/CBS
            hibrido_str = "NÃO"
            
            # Tenta buscar os dados adicionais de eventos futuros na API complementar do CNPJ.ws
            try:
                url_ws = f"https://publica.cnpj.ws/cnpj/{cnpj_limpo}"
                resp_ws = requests.get(url_ws, timeout=8)
                if resp_ws.status_code == 200:
                    dados_ws = resp_ws.json()
                    simples_data = dados_ws.get("simples") or {}
                    
                    # Checa presença de eventos futuros do regime regular IBS/CBS
                    eventos = simples_data.get("eventos_futuros") or []
                    for evento in eventos:
                        if "IBS" in str(evento) or "CBS" in str(evento) or "regular" in str(evento).lower():
                            hibrido_str = "SIM (Híbrido)"
                            break
            except Exception:
                pass
                
            return {
                "CNPJ": cnpj_limpo,
                "Razão Social": razao_social,
                "Simples Nacional": simples_str,
                "MEI / SIMEI": mei_str,
                "Híbrido (IBS/CBS Regular)": hibrido_str,
                "Status": "Sucesso"
            }
            
        elif response.status_code == 404:
            return {
                "CNPJ": cnpj_limpo,
                "Razão Social": "N/A",
                "Simples Nacional": "N/A",
                "MEI / SIMEI": "N/A",
                "Híbrido (IBS/CBS Regular)": "N/A",
                "Status": "CNPJ Não Encontrado"
            }
        else:
            return {
                "CNPJ": cnpj_limpo,
                "Razão Social": "N/A",
                "Simples Nacional": "Erro",
                "MEI / SIMEI": "Erro",
                "Híbrido (IBS/CBS Regular)": "Erro",
                "Status": f"Erro HTTP {response.status_code}"
            }
            
    except Exception as e:
        return {
            "CNPJ": cnpj_limpo,
            "Razão Social": "N/A",
            "Simples Nacional": "Erro",
            "MEI / SIMEI": "Erro",
            "Híbrido (IBS/CBS Regular)": "Erro",
            "Status": "Falha na Conexão"
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
                res = consultar_cnpj(cnpj_limpo)
                resultados.append(res)
                
                # Pausa leve de 1 segundo para estabilidade
                if i < total - 1:
                    time.sleep(1)
            
            progresso.progress((i + 1) / total)

        status_texto.success("✅ Consulta finalizada!")
        
        df = pd.DataFrame(resultados)
        st.subheader("📊 Resultados:")
        st.dataframe(df, use_container_width=True)
        
        # Cria a planilha Excel para download
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='CNPJs')
        
        st.download_button(
            label="📥 Baixar Planilha Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name="resultado_cnpjs_hibrido.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
