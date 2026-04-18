import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# 1. Configuração de Página (MANTIDO)
st.set_page_config(
    page_title="Taxi Drive", 
    page_icon="🚕", 
    layout="centered"
)

# 2. ESCONDE A COROA E O MENU (MANTIDO)
hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {padding-top: 2rem;}
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)

# --- BANCO DE DADOS (MANTIDO) ---
def init_db():
    conn = sqlite3.connect('dynamic_v4.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS caixa (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, descricao TEXT, valor REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rotas (id INTEGER PRIMARY KEY AUTOINCREMENT, destino TEXT, preco REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS configs (chave TEXT PRIMARY KEY, valor REAL)''')
    defaults = [('extra_fixo', 5.0), ('diaria', 59.0), ('diesel', 2.14), ('consumo', 15.0)]
    for k, v in defaults:
        c.execute("INSERT OR IGNORE INTO configs (chave, valor) VALUES (?, ?)", (k, v))
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect('dynamic_v4.db')

# --- CARREGAR CONFIGURAÇÕES ---
conn = get_db_connection()
cfg = pd.read_sql_query("SELECT * FROM configs", conn).set_index('chave')['valor'].to_dict()
conn.close()

# --- INTERFACE E TRADUÇÃO TOTAL ---
lang_en = st.sidebar.toggle("English Mode")

t = {
    "aba1": "💰 CALCULATOR / ROUTES" if lang_en else "💰 CALCULADORA / ROTAS",
    "aba2": "📊 CASH" if lang_en else "📊 MEU CAIXA",
    "aba3": "⛽ FUEL" if lang_en else "⛽ COMBUSTIVEL",
    "aba4": "⚙️ CONFIG" if lang_en else "⚙️ CONFIG",
    "tabela_precos": "Price List" if lang_en else "Tabela de Preços",
    "sel_destino": "Select Destination" if lang_en else "Selecione o Destino",
    "viagem_perso": "Custom Trip" if lang_en else "Viagem Personalizada",
    "distancia": "Distance (KM)" if lang_en else "Distância (KM)",
    "tempo": "Time (Min)" if lang_en else "Tempo (Min)",
    "tarifa": "Rate" if lang_en else "Tarifa",
    "sugerido": "Suggested Price" if lang_en else "Preço Sugerido",
    "contabilidade": "Accounting" if lang_en else "Contabilidade Pessoal",
    "ver_dia": "Filter date" if lang_en else "Filtrar por data",
    "lançar_diaria": "Log Daily" if lang_en else "Lançar Diária",
    "descricao": "Description" if lang_en else "Descrição",
    "valor_ajuda": "Value (1245 = 12.45)" if lang_en else "Valor (Ex: 1245 para 12.45)",
    "registrar": "Register" if lang_en else "Registrar",
    "saldo_dia": "Balance" if lang_en else "Saldo em",
    "custo_comb": "Fuel Cost" if lang_en else "Custo de combustível",
    "config_app": "Settings" if lang_en else "Configurações do App",
    "add_rota": "Add New Route" if lang_en else "Adicionar Nova Rota",
    "gerenciar_rotas": "Manage Routes" if lang_en else "Gerenciar Rotas Fixas",
    "salvar": "Save" if lang_en else "Salvar",
    "apagar": "Delete" if lang_en else "Deletar"
}

tab_calc, tab_caixa, tab_aceite, tab_config = st.tabs([t["aba1"], t["aba2"], t["aba3"], t["aba4"]])

# --- ABA 1: CALCULADORA ---
with tab_calc:
    st.subheader(t["tabela_precos"])
    conn = get_db_connection()
    df_rotas = pd.read_sql_query("SELECT * FROM rotas ORDER BY destino", conn)
    conn.close()
    if not df_rotas.empty:
        rota_sel = st.selectbox(t["sel_destino"], df_rotas['destino'].tolist())
        p_exibicao = df_rotas[df_rotas['destino'] == rota_sel]['preco'].values[0]
        st.markdown(f"<h1 style='text-align: center; color: #4CAF50;'>€{p_exibicao:.2f}</h1>", unsafe_allow_html=True)

    st.divider()
    st.subheader(t["viagem_perso"])
    col1, col2 = st.columns(2)
    dist_m = col1.number_input(t["distancia"], min_value=0.0)
    tempo_m = col2.number_input(t["tempo"], min_value=0)
    opcoes_tarifa = ["Day (T1)", "Night/Wkd (T2)"] if lang_en else ["Dia (T1)", "Noite-FDS (T2)"]
    tarifa_sel = st.selectbox(t["tarifa"], opcoes_tarifa)
    band = 3.25 if "Day" in tarifa_sel or "Dia" in tarifa_sel else 3.90
    km_rate = 0.67 if "Day" in tarifa_sel or "Dia" in tarifa_sel else 0.80
    time_rate = 16.50 if "Day" in tarifa_sel or "Dia" in tarifa_sel else 19.80
    val_final_calc = band + (dist_m * km_rate) + ((tempo_m / 60) * time_rate) + cfg['extra_fixo']
    st.markdown(f"<h3 style='text-align: center;'>{t['sugerido']}</h3>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='text-align: center; color: #4CAF50;'>€{round(val_final_calc, 0)}</h1>", unsafe_allow_html=True)

# --- ABA 2: MEU CAIXA ---
with tab_caixa:
    st.subheader(t["contabilidade"])
    data_sel = st.date_input(t["ver_dia"], datetime.now().date(), format="DD/MM/YYYY")
    data_str = data_sel.strftime("%Y-%m-%d")

    if st.button(f"{t['lançar_diaria']} (€{cfg['diaria']})"):
        conn = get_db_connection()
        conn.execute("INSERT INTO caixa (data, descricao, valor) VALUES (?, ?, ?)", 
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Custo Diária", -cfg['diaria']))
        conn.commit()
        conn.close()
        st.rerun()

    with st.form("add_caixa", clear_on_submit=True):
        f_desc = st.text_input(t["descricao"])
        f_val = st.text_input(t["valor_ajuda"])
        if st.form_submit_button(t["registrar"]):
            if f_val:
                v_conv = float(f_val) / 100
                conn = get_db_connection()
                conn.execute("INSERT INTO caixa (data, descricao, valor) VALUES (?, ?, ?)", 
                            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f_desc, v_conv))
                conn.commit()
                conn.close()
                st.rerun()

    conn = get_db_connection()
    df_c = pd.read_sql_query(f"SELECT * FROM caixa WHERE data LIKE '{data_str}%' ORDER BY id DESC", conn)
    conn.close()
    st.metric(f"{t['saldo_dia']} {data_sel.strftime('%d/%m/%Y')}", f"€{df_c['valor'].sum():.2f}")
    for i, row in df_c.iterrows():
        c1, c2, c3 = st.columns([2, 1, 0.5])
        hora = row['data'][11:16] if len(row['data']) > 10 else "--:--"
        c1.write(f"**{row['descricao']}**")
        c1.caption(f"🕒 {hora}")
        cor = "green" if row['valor'] > 0 else "red"
        c2.write(f":{cor}[€{row['valor']:.2f}]")
        if c3.button("🗑️", key=f"del_{row['id']}"):
            conn = get_db_connection()
            conn.execute("DELETE FROM caixa WHERE id=?", (row['id'],))
            conn.commit()
            conn.close()
            st.rerun()
        st.divider()

# --- ABA 3: COMBUSTÍVEL ---
with tab_aceite:
    st.subheader(t["custo_comb"])
    dist_a = st.number_input(t["distancia"], min_value=0.0, step=0.1)
    p_dies = st.number_input("Diesel (€)", value=cfg['diesel'], step=0.01)
    c_car = st.number_input("Consumo (KM/L)", value=cfg['consumo'], step=0.1)
    if c_car > 0:
        st.header(f"Total: €{(dist_a * (p_dies / c_car)):.2f}")

# --- ABA 4: CONFIG ---
with tab_config:
    st.subheader(t["config_app"])
    with st.form("cfg_f"):
        ne = st.number_input("Extra (€)", value=cfg['extra_fixo'])
        nd = st.number_input("Daily (€)", value=cfg['diaria'])
        ng = st.number_input("Diesel (€)", value=cfg['diesel'])
        nc = st.number_input("Consumo (KM/L)", value=cfg['consumo'])
        if st.form_submit_button(t["salvar"]):
            conn = get_db_connection()
            for k, v in [('extra_fixo', ne), ('diaria', nd), ('diesel', ng), ('consumo', nc)]:
                conn.execute("UPDATE configs SET valor = ? WHERE chave = ?", (v, k))
            conn.commit()
            conn.close()
            st.rerun()

    st.divider()
    st.subheader(t["add_rota"])
    with st.form("add_r"):
        rd = st.text_input("Destination" if lang_en else "Destino")
        rp = st.number_input("Price" if lang_en else "Preço", min_value=0.0)
        if st.form_submit_button(t["registrar"]):
            if rd:
                conn = get_db_connection()
                conn.execute("INSERT INTO rotas (destino, preco) VALUES (?, ?)", (rd, rp))
                conn.commit()
                conn.close()
                st.rerun()

    st.subheader(t["gerenciar_rotas"])
    df_r = pd.read_sql_query("SELECT * FROM rotas ORDER BY destino", get_db_connection())
    for i, r in df_r.iterrows():
        with st.expander(f"{r['destino']} - €{r['preco']:.2f}"):
            ndest = st.text_input("Name", value=r['destino'], key=f"rd{r['id']}")
            nprec = st.number_input("Value", value=r['preco'], key=f"rp{r['id']}")
            ca, cb = st.columns(2)
            if ca.button(t["salvar"], key=f"sv{r['id']}"):
                conn = get_db_connection()
                conn.execute("UPDATE rotas SET destino=?, preco=? WHERE id=?", (ndest, nprec, r['id']))
                conn.commit()
                conn.close()
                st.rerun()
            if cb.button(t["apagar"], key=f"ap{r['id']}"):
                conn = get_db_connection()
                conn.execute("DELETE FROM rotas WHERE id=?", (r['id'],))
                conn.commit()
                conn.close()
                st.rerun()