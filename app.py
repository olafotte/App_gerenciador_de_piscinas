import json
from pathlib import Path

import streamlit as st
import pandas as pd
import database as db
import plotly.express as px

# Inicializa o banco de dados
db.init_db()

TEXTS_FILE = Path(__file__).resolve().parent / "pool_tips.json"
if TEXTS_FILE.exists():
    with open(TEXTS_FILE, "r", encoding="utf-8") as f:
        pool_texts = json.load(f)
else:
    pool_texts = {}

def converter_alcalinidade_gotas_para_ppm(gotas):
    return gotas * 10

def converter_dureza_gotas_para_ppm(gotas):
    return gotas * 10

def converter_salinidade_gotas_para_ppm(gotas):
    # Conforme foto: 1 gota = 125 ppm
    return gotas * 125

def converter_salinidade_ppm_para_g_l(ppm):
    # Conforme foto: cada gota (125 ppm) = 0,125 g/L
    return ppm / 1000

def calcular_dosagem_bicarbonato(alcalinidade_ppm, volume_m3):
    """
    Calcula a quantidade de bicarbonato de sódio baseada em uma relação linear:
    0 ppm -> 180g/1000L
    120 ppm -> 0g/1000L
    Fórmula: g = (-1.5 * ppm + 180) * volume
    """
    if alcalinidade_ppm >= 120:
        return 0.0
    
    gramas_por_m3 = (-1.5 * alcalinidade_ppm) + 180
    total_gramas = gramas_por_m3 * volume_m3
    return total_gramas

def avaliar_status(valor, minimo, maximo):
    largura = maximo - minimo
    limite_inferior = minimo + largura * 0.01
    limite_superior = maximo - largura * 0.01

    if minimo <= valor <= maximo:
        if valor <= limite_inferior or valor >= limite_superior:
            return "🟡 Limite"
        return "✅ Dentro"

    if minimo - largura * 0.01 <= valor < minimo:
        return "🟡 Limite"
    if maximo < valor <= maximo + largura * 0.01:
        return "🟡 Limite"

    if valor < minimo:
        return "🔻 Abaixo"
    return "🔺 Acima"


def avaliar_pool_status(latest_row, textos, volume_m3):
    mensagens = []
    recomendacoes = []

    if latest_row["pH"] < 7.2:
        mensagens.append((textos["summary"]["ph_low"], False))
        recomendacoes.extend(textos["recommendations"]["ph_low"])
    elif latest_row["pH"] > 7.6:
        mensagens.append((textos["summary"]["ph_high"], False))
        recomendacoes.extend(textos["recommendations"]["ph_high"])
    else:
        mensagens.append((textos["summary"]["ph_ok"], True))

    salinity_ok = 2500 <= latest_row["Salinidade"] <= 4500

    if latest_row["Cloro"] < 1.0:
        mensagens.append((textos["summary"]["cloro_low"], False))
        recomendacoes.extend(textos["recommendations"]["cloro_low"])
        if salinity_ok:
            mensagens.append((textos["summary"]["generator_ready"], True))
            recomendacoes.extend(textos["recommendations"]["generator_low_chlorine"])
        else:
            mensagens.append((textos["summary"]["generator_saline_issue"], False))
            recomendacoes.extend(textos["recommendations"]["generator_salinity_low"])
    elif latest_row["Cloro"] > 3.0:
        mensagens.append((textos["summary"]["cloro_high"], False))
        recomendacoes.extend(textos["recommendations"]["cloro_high"])
    else:
        mensagens.append((textos["summary"]["cloro_ok"], True))
        if salinity_ok:
            recomendacoes.extend(textos["recommendations"]["generator_ok"])

    # Alcalinidade com Cálculo de Bicarbonato
    alcalinidade_ppm = converter_alcalinidade_gotas_para_ppm(latest_row["Alcalinidade"])
    if alcalinidade_ppm < 80:
        mensagens.append((textos["summary"]["alcalinidade_low"], False))
        # Adiciona a recomendação específica de bicarbonato
        gramas = calcular_dosagem_bicarbonato(alcalinidade_ppm, volume_m3)
        if gramas > 0:
            recomendacoes.append(f"Adicionar **{gramas/1000:.2f} kg** de Bicarbonato de Sódio para elevar a alcalinidade.")
        recomendacoes.extend(textos["recommendations"]["alcalinidade_low"])
    elif alcalinidade_ppm > 120:
        mensagens.append((textos["summary"]["alcalinidade_high"], False))
        recomendacoes.extend(textos["recommendations"]["alcalinidade_high"])
    else:
        mensagens.append((textos["summary"]["alcalinidade_ok"], True))
        
    dureza_ppm = converter_dureza_gotas_para_ppm(latest_row["Dureza"])
    if dureza_ppm < 150:
        mensagens.append((textos["summary"]["dureza_low"], False))
        recomendacoes.extend(textos["recommendations"]["dureza_low"])
    elif dureza_ppm > 350:
        mensagens.append((textos["summary"]["dureza_high"], False))
        recomendacoes.extend(textos["recommendations"]["dureza_high"])
    else:
        mensagens.append((textos["summary"]["dureza_ok"], True))

    salinidade_ppm = converter_salinidade_gotas_para_ppm(latest_row["Salinidade"])
    if salinidade_ppm < 2500:
        mensagens.append((textos["summary"]["salinidade_low"], False))
        recomendacoes.extend(textos["recommendations"]["salinidade_low"])
    elif salinidade_ppm > 4500:
        mensagens.append((textos["summary"]["salinidade_high"], False))
        recomendacoes.extend(textos["recommendations"]["salinidade_high"])
    else:
        mensagens.append((textos["summary"]["salinidade_ok"], True))

    return mensagens, recomendacoes


st.set_page_config(page_title="Gerenciador de Piscinas", layout="centered")

# Gerenciamento de Estado da Sessão
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'pool_id' not in st.session_state:
    st.session_state['pool_id'] = None
if 'pool_name' not in st.session_state:
    st.session_state['pool_name'] = ""
if 'pool_volume' not in st.session_state:
    st.session_state['pool_volume'] = 0.0

def login_screen():
    st.title("🔐 Login")
    aba1, aba2 = st.tabs(["Login", "Cadastrar"])
    
    with aba1:
        with st.form("login_form"):
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar")
            if submitted:
                user_id = db.verify_user(username, password)
                if user_id:
                    st.session_state['user_id'] = user_id
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

    with aba2:
        with st.form("register_form"):
            new_username = st.text_input("Novo Usuário")
            new_password = st.text_input("Nova Senha", type="password")
            confirm_password = st.text_input("Confirmar Senha", type="password")
            registered = st.form_submit_button("Cadastrar")
            if registered:
                if new_password != confirm_password:
                    st.error("As senhas não coincidem.")
                elif not new_username or not new_password:
                    st.error("Preencha todos os campos.")
                else:
                    user_id = db.create_user(new_username, new_password)
                    if user_id:
                        st.success("Usuário criado com sucesso! Faça login para continuar.")
                    else:
                        st.error("Nome de usuário já existe.")

def pool_selection_screen():
    st.title("🌊 Seleção de Piscina")
    st.write("Selecione uma piscina para administrar ou crie uma nova.")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Sair da Conta"):
            st.session_state['user_id'] = None
            st.rerun()

    st.subheader("Suas Piscinas")
    pools = db.get_pools(st.session_state['user_id'])
    
    if pools:
        for p in pools:
            with st.container():
                c1, c2, c3 = st.columns([5, 1, 1])
                with c1:
                    st.write(f"**{p['name']}** (Volume: {p['volume']} m³)")
                with c2:
                    if st.button("Acessar", key=f"acessar_{p['id']}"):
                        st.session_state['pool_id'] = p['id']
                        st.session_state['pool_name'] = p['name']
                        st.session_state['pool_volume'] = p['volume']
                        st.rerun()
                with c3:
                    if st.button("Excluir", key=f"excluir_{p['id']}", type="secondary"):
                        st.session_state[f"confirm_delete_{p['id']}"] = True
                
                if st.session_state.get(f"confirm_delete_{p['id']}"):
                    if st.button(f"⚠️ Confirmar exclusão de {p['name']}?", key=f"real_del_{p['id']}", type="primary"):
                        db.deletar_piscina(p['id'])
                        st.success("Piscina removida.")
                        st.rerun()
    else:
        st.info("Você ainda não possui piscinas cadastradas.")
        
    st.divider()
    st.subheader("Cadastrar Nova Piscina")
    with st.form("new_pool_form"):
        pool_name = st.text_input("Nome da Piscina (ex: Piscina Casa, Piscina Clube)")
        pool_volume = st.number_input("Volume (m³ / mil litros)", min_value=1.0, value=40.0, step=1.0)
        submitted = st.form_submit_button("Cadastrar Piscina")
        if submitted:
            if not pool_name:
                st.error("Por favor, insira o nome da piscina.")
            else:
                db.create_pool(st.session_state['user_id'], pool_name, pool_volume)
                st.success("Piscina cadastrada com sucesso!")
                st.rerun()

def main_app():
    # Sidebar para Configurações Gerais
    st.sidebar.header("⚙️ Configurações Gerais")
    st.sidebar.write(f"**Piscina Atual:** {st.session_state['pool_name']}")

    volume_piscina = st.session_state['pool_volume']
    st.sidebar.write(f"**Volume Configurado:** {volume_piscina} m³")
    
    if st.sidebar.button("Trocar de Piscina"):
        st.session_state['pool_id'] = None
        st.rerun()
        
    if st.sidebar.button("Sair da Conta"):
        st.session_state['user_id'] = None
        st.session_state['pool_id'] = None
        st.rerun()


    st.title(f"🏊‍♂️ {st.session_state['pool_name']}")
    st.subheader("Registro de Parâmetros")
    # Formulário de Entrada

    with st.form("form_medicao"):
        col1, col2 = st.columns(2)
        with col1:
            responsavel = st.selectbox("Responsável", ["Olaf", "Zelador", "Outro"])
            ph = st.number_input("pH", min_value=6.0, max_value=9.0, value=7.4, step=0.1)
            cloro = st.number_input("Cloro (ppm)", min_value=0.0, max_value=10.0, value=2.0, step=0.5)
            generator_level = st.slider("Nível do Gerador (%)", 0, 100, 0, step=20)

        with col2:
            alcalinidade = st.number_input("Alcalinidade (gotas)", min_value=0, step=1)
            dureza = st.number_input("Dureza Cálcica (gotas)", min_value=0, step=1)
            salinidade = st.number_input("Salinidade (gotas)", min_value=0, step=1)
            
        if st.form_submit_button("Salvar Medição"):
            db.salvar_medicao(st.session_state['pool_id'], responsavel, ph, cloro, generator_level, alcalinidade, dureza, salinidade)
            st.success("Medição registrada com sucesso!")
            st.rerun()

    # Exibição do Histórico
    st.divider()
    st.subheader("Histórico Recente")
    historico = db.ler_historico(st.session_state['pool_id'])

    if historico:
        df = pd.DataFrame(historico, columns=["ID", "Data/Hora", "Responsável", "pH", "Cloro", "Nível Gerador", "Alcalinidade", "Dureza", "Salinidade"])
        df["Data/Hora"] = pd.to_datetime(df["Data/Hora"])
        df = df.sort_values("Data/Hora")
        st.dataframe(df, hide_index=True)

        latest_values = df.iloc[-1]
        alcalinidade_ppm = converter_alcalinidade_gotas_para_ppm(latest_values["Alcalinidade"])
        dureza_ppm = converter_dureza_gotas_para_ppm(latest_values["Dureza"])
        salinidade_ppm = converter_salinidade_gotas_para_ppm(latest_values["Salinidade"])
        salinidade_g_l = converter_salinidade_ppm_para_g_l(salinidade_ppm)

        st.divider()
        st.subheader("Valores Convertidos e Faixas Ideais")

        status_ph = avaliar_status(latest_values["pH"], 7.2, 7.6)
        status_cloro = avaliar_status(latest_values["Cloro"], 1.0, 3.0)
        status_alcalinidade = avaliar_status(alcalinidade_ppm, 80, 120)
        status_dureza = avaliar_status(dureza_ppm, 200, 400)
        status_salinidade = avaliar_status(salinidade_ppm, 2500, 4500)

        conversoes = pd.DataFrame([
            {
                "Parâmetro": "pH",
                "Conversão": "Leitura Direta",
                "Valor Convertido": f"{latest_values['pH']:.1f}",
                "Unidade": "pH",
                "Faixa Ideal": "7.2 a 7.6",
                "Status": status_ph,
            },
            {
                "Parâmetro": "Cloro",
                "Conversão": "Leitura Direta",
                "Valor Convertido": f"{latest_values['Cloro']:.1f}",
                "Unidade": "ppm",
                "Faixa Ideal": "1.0 a 3.0",
                "Status": status_cloro,
            },
            {
                "Parâmetro": "Alcalinidade",
                "Conversão": "1 gota = 10 ppm",
                "Valor Convertido": f"{alcalinidade_ppm}",
                "Unidade": "ppm",
                "Faixa Ideal": "80 a 120",
                "Status": status_alcalinidade,
            },
            {
                "Parâmetro": "Dureza Cálcica",
                "Conversão": "1 gota = 10 ppm",
                "Valor Convertido": f"{dureza_ppm}",
                "Unidade": "ppm",
                "Faixa Ideal": "200 a 400",
                "Status": status_dureza,
            },
            {
                "Parâmetro": "Salinidade",
                "Conversão": "1 gota = 125 ppm",
                "Valor Convertido": f"{salinidade_ppm} ppm ({salinidade_g_l:.2f} g/L)",
                "Unidade": "ppm (g/L)",
                "Faixa Ideal": "2500 a 4500 (2.5 a 4.5)",
                "Status": status_salinidade,
            },
        ])

        st.table(conversoes)

        st.markdown("**O que cada parâmetro significa:**")
        st.markdown(
            "- **pH**: mede a acidez ou alcalinidade da água; valores ideais mantêm a água confortável e o cloro eficaz.\n"
            "- **Cloro**: nível de desinfecção ativo em ppm; protege contra germes, algas e bactérias.\n"
            "- **Alcalinidade**: capacidade da água de resistir a mudanças de pH; ajuda a manter o pH estável.\n"
            "- **Dureza**: concentração de cálcio na água; valores corretos evitam corrosão ou incrustações.\n"
            "- **Salinidade**: quantidade de sal na água; necessária para o gerador de cloro salino operar corretamente."
        )

        st.caption("As conversões de gotas em ppm/g/L são aproximadas e servem para facilitar a interpretação dos resultados.")

        if pool_texts:
            st.divider()
            st.subheader("Condição Atual da Piscina")
            latest = df.iloc[-1]
            # Passando o volume configurado para a função de avaliação
            mensagens, recomendacoes = avaliar_pool_status(latest, pool_texts, volume_piscina)
            for mensagem, is_ok in mensagens:
                if is_ok:
                    st.success(mensagem)
                else:
                    st.warning(mensagem)
            if recomendacoes:
                st.markdown("**Recomendações:**")
                for recomendacao in recomendacoes:
                    st.write(f"- {recomendacao}")

        st.divider()
        st.subheader("Gráficos de Tendência")

        fig_tendencia = px.line(
            df,
            x="Data/Hora",
            y=["pH", "Cloro"],
            markers=True,
            title="pH e Cloro ao Longo do Tempo",
            labels={"value": "Valor", "variable": "Parâmetro"},
        )
        st.plotly_chart(fig_tendencia, width="stretch")

        fig_quimica = px.line(
            df,
            x="Data/Hora",
            y=["Alcalinidade", "Dureza", "Salinidade"],
            markers=True,
            title="Alcalinidade, Dureza e Salinidade ao Longo do Tempo",
            labels={"value": "Valor", "variable": "Parâmetro"},
        )
        st.plotly_chart(fig_quimica, width="stretch")

        df_melted = df.melt(
            id_vars=["Data/Hora"],
            value_vars=["pH", "Cloro", "Alcalinidade", "Dureza", "Salinidade"],
            var_name="Parâmetro",
            value_name="Valor",
        )
        fig_barras = px.bar(
            df_melted,
            x="Data/Hora",
            y="Valor",
            color="Parâmetro",
            title="Valores por Medição",
            barmode="group",
        )
        st.plotly_chart(fig_barras, width="stretch")

        st.divider()
        st.subheader("Gerenciar Registros")
        
        opcoes = ["Editar Registro", "Deletar Registro"]
        acao = st.radio("Selecione a ação:", opcoes, horizontal=True)

        record_ids = df["ID"].tolist()
        if record_ids:
            id_selecionado = st.selectbox("Selecione o ID do registro:", record_ids)
            
            registro_selecionado = df[df["ID"] == id_selecionado].iloc[0]

            if acao == "Deletar Registro":
                if st.button("🗑️ Confirmar Exclusão"):
                    db.deletar_medicao(int(id_selecionado))
                    st.success(f"Registro {id_selecionado} deletado com sucesso!")
                    st.rerun()

            elif acao == "Editar Registro":
                with st.form("editar_form"):
                    novo_data_hora = st.text_input("Data e Hora (YYYY-MM-DD HH:MM:SS)", value=str(registro_selecionado["Data/Hora"]))
                    novo_responsavel = st.text_input("Nome do Responsável pela medição", value=str(registro_selecionado["Responsável"]))

                    
                    col1, col2 = st.columns(2)
                    with col1:
                        novo_ph = st.number_input("pH", min_value=0.0, max_value=14.0, step=0.1, value=float(registro_selecionado["pH"]))
                        novo_cloro = st.number_input("Cloro (ppm)", min_value=0.0, step=0.1, value=float(registro_selecionado["Cloro"]))
                        generator_options = [0, 20, 40, 60, 80, 100]
                        current_generator_level = int(registro_selecionado.get("Nível Gerador", 0) or 0)
                        default_index = generator_options.index(current_generator_level) if current_generator_level in generator_options else 0
                        novo_generator_level = st.selectbox(
                        "Nível de geração de cloro (% de geração)",
                        generator_options,
                        index=default_index,
                        )
                    
                    with col2:
                        nova_alcalinidade = st.number_input("Alcalinidade (gotas)", min_value=0, step=1, value=int(registro_selecionado["Alcalinidade"]))
                        nova_dureza = st.number_input("Dureza (gotas)", min_value=0, step=1, value=int(registro_selecionado["Dureza"]))
                        nova_salinidade = st.number_input("Salinidade (gotas)", min_value=0, step=1, value=int(registro_selecionado["Salinidade"]))

                    btn_atualizar = st.form_submit_button("💾 Atualizar Medição")

                    if btn_atualizar:
                        db.atualizar_medicao(
                            int(id_selecionado),
                            novo_data_hora,
                            novo_responsavel,
                            novo_ph,
                            novo_cloro,
                            novo_generator_level,
                            nova_alcalinidade,                        
                            nova_dureza,
                            nova_salinidade                        
                        )
                        st.success(f"Registro {id_selecionado} atualizado com sucesso!")
                        st.rerun()
    else:
        st.info("Nenhum registro encontrado no histórico desta piscina.")

if st.session_state['user_id'] is None:
    login_screen()
elif st.session_state['pool_id'] is None:
    pool_selection_screen()
else:
    main_app()
