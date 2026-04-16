import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Dynamic Drive Pro", page_icon="🚕")

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('dynamic_v4.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS caixa (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, descricao TEXT, valor REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rotas (id INTEGER PRIMARY KEY AUTOINCREMENT, destino TEXT, preco REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS configs (chave TEXT PRIMARY KEY, valor REAL)''')
    
    # Inserir Configs Iniciais
    # 'extra_fixo' agora é em Euros, não mais %
    defaults = [('extra_fixo', 5.0), ('diaria', 59.0), ('diesel', 2.14), ('consumo', 15.0)]
    for k, v in defaults:
        c.execute("INSERT OR IGNORE INTO configs (chave, valor) VALUES (?, ?)", (k, v))
    
    # Inserir Suas Rotas Predefinidas
    c.execute("SELECT COUNT(*) FROM rotas")
    if c.fetchone()[0] == 0:
        pre_rotas = [
            ('Rossio', 20.0), ('Praça do Comércio', 20.0), ('Lx Factory', 18.0),
            ('Chiado/Bairro Alto', 20.0), ('Castelo S. Jorge', 22.0), ('TimeOut Market', 20.0),
            ('Colombo', 22.0), ('Mosteiro', 15.0), ('Hippotrip Docas', 15.0), ('Terminal Cruzeiros', 22.0)
        ]
        c.executemany("INSERT INTO rotas (destino, preco) VALUES (?, ?)", pre_rotas)
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect('dynamic_v4.db')

# --- CARREGAR CONFIGURAÇÕES ---
conn = get_db_connection()
cfg = pd.read_sql_query("SELECT * FROM configs", conn).set_index('chave')['valor'].to_dict()
conn.close()

# --- INTERFACE ---
st.title("🚕 Taxi Drive")
lang_en = st.sidebar.toggle("English Mode")

tab_calc, tab_caixa, tab_aceite, tab_config = st.tabs([
    "💰 CALCULATOR / ROUTES", 
    "📊 MEU CAIXA", 
    "⛽ COMBUSTIVEL", 
    "⚙️ CONFIG"
])

# --- ABA 1: CALCULADORA E ROTAS (CLIENTE) ---
with tab_calc:
    st.subheader("Price List / Tabela de Preços" if lang_en else "Tabela de Preços")
    
    conn = get_db_connection()
    df_rotas = pd.read_sql_query("SELECT * FROM rotas ORDER BY destino", conn)
    conn.close()
    
    if not df_rotas.empty:
        rota_sel = st.selectbox("Select Destination / Selecione o Destino", df_rotas['destino'].tolist())
        p_exibicao = df_rotas[df_rotas['destino'] == rota_sel]['preco'].values[0]
        st.markdown(f"<h1 style='text-align: center; color: #4CAF50; font-size: 60px;'>€{p_exibicao:.2f}</h1>", unsafe_allow_html=True)

    st.divider()
    
    st.subheader("Custom Trip / Viagem Personalizada" if lang_en else "Viagem Personalizada")
    col1, col2 = st.columns(2)
    dist_m = col1.number_input("Distance (KM)" if lang_en else "Distância (KM)", min_value=0.0)
    tempo_m = col2.number_input("Time (Min)" if lang_en else "Tempo (Min)", min_value=0)
    
    tarifa = st.selectbox("Rate / Tarifa", ["Day / Dia (Tarifa 1)", "Night-Weekend / Noite-FDS (Tarifa 2)"])
    band = 3.25 if "Day" in tarifa or "Dia" in tarifa else 3.90
    km_rate = 0.67 if "Day" in tarifa or "Dia" in tarifa else 0.80
    time_rate = 16.50 if "Day" in tarifa or "Dia" in tarifa else 19.80
    
    # Cálculo Oficial + ADICIONAL EM VALOR FIXO (€)
    val_oficial = band + (dist_m * km_rate) + ((tempo_m / 60) * time_rate)
    val_final_calc = val_oficial + cfg['extra_fixo']
    
    label_sugerido = "Suggested Price" if lang_en else "Preço Sugerido"
    st.markdown(f"<h3 style='text-align: center; margin-top: 20px;'>{label_sugerido}</h3>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='text-align: center; color: #4CAF50; font-size: 60px;'>€{round(val_final_calc, 0)}</h1>", unsafe_allow_html=True)

# --- ABA 2: MEU CAIXA ---
with tab_caixa:
    st.subheader("Contabilidade Pessoal")
    
    if st.button("Lançar Diária de Hoje (€" + str(cfg['diaria']) + ")"):
        conn = get_db_connection()
        conn.execute("INSERT INTO caixa (data, descricao, valor) VALUES (?, ?, ?)", 
                    (datetime.now().strftime("%Y-%m-%d"), "Custo Diária", -cfg['diaria']))
        conn.commit()
        conn.close()
        st.rerun()

    with st.form("add_caixa"):
        desc = st.text_input("Descrição")
        val = st.number_input("Valor (€)", format="%.2f", help="Negativo para gastos")
        if st.form_submit_button("Registrar"):
            conn = get_db_connection()
            conn.execute("INSERT INTO caixa (data, descricao, valor) VALUES (?, ?, ?)", 
                        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), desc, val))
            conn.commit()
            conn.close()
            st.rerun()

    df_caixa = pd.read_sql_query(f"SELECT descricao, valor FROM caixa WHERE data LIKE '{datetime.now().strftime('%Y-%m-%d')}%'", get_db_connection())
    st.metric("Saldo Real Hoje", f"€{df_caixa['valor'].sum():.2f}")
    st.table(df_caixa)
    
    if st.button("LIMPAR CAIXA (HOJE)"):
        conn = get_db_connection()
        conn.execute("DELETE FROM caixa WHERE data LIKE ?", (datetime.now().strftime("%Y-%m-%d") + "%",))
        conn.commit()
        conn.close()
        st.rerun()

# --- ABA 3: ACEITE ---
with tab_aceite:
    st.subheader("Custo de combustível")
    dist_a = st.number_input("KM totais", min_value=0.1, key="a_km")
    tempo_a = st.number_input("Tempo total (min)", min_value=1, key="a_min")
    
    custo_d = dist_a * (cfg['diesel'] / cfg['consumo'])
    min_aceite = custo_d + ((tempo_a / 60) * 20)
    
    st.header(f"Custo combustível: €{custo_d:.2f}")

# --- ABA 4: CONFIG ---
with tab_config:
    st.subheader("Configurações do App")
    with st.form("cfg_form"):
        new_extra = st.number_input("Adicional Fixo na Calculadora (€)", value=cfg['extra_fixo'])
        new_diaria = st.number_input("Valor da Diária (€)", value=cfg['diaria'])
        new_diesel = st.number_input("Preço do Gasóleo (€)", value=cfg['diesel'])
        if st.form_submit_button("Salvar Tudo"):
            conn = get_db_connection()
            conn.execute("UPDATE configs SET valor = ? WHERE chave = 'extra_fixo'", (new_extra,))
            conn.execute("UPDATE configs SET valor = ? WHERE chave = 'diaria'", (new_diaria,))
            conn.execute("UPDATE configs SET valor = ? WHERE chave = 'diesel'", (new_diesel,))
            conn.commit()
            conn.close()
            st.rerun()
            
    st.divider()
    
    # --- NOVA FUNÇÃO: CADASTRAR NOVA ROTA ---
    st.subheader("➕ Adicionar Nova Rota")
    with st.form("form_nova_rota"):
        c_dest, c_prec = st.columns([2, 1])
        n_dest = c_dest.text_input("Nome do Destino (Ex: Aeroporto)")
        n_prec = c_prec.number_input("Preço Fixo (€)", min_value=0.0, step=1.0)
        
        if st.form_submit_button("CADASTRAR ROTA"):
            if n_dest: # Só salva se tiver nome
                conn = get_db_connection()
                conn.execute("INSERT INTO rotas (destino, preco) VALUES (?, ?)", (n_dest, n_prec))
                conn.commit()
                conn.close()
                st.success(f"Rota para {n_dest} adicionada!")
                st.rerun()
            else:
                st.error("Por favor, digite o nome do destino.")

    st.divider()
    
    # --- GERENCIAR EXISTENTES ---
    st.subheader("Gerenciar Rotas Fixas")
    df_edit = pd.read_sql_query("SELECT * FROM rotas", get_db_connection())
    for i, r in df_edit.iterrows():
        with st.expander(f"Editar: {r['destino']}"):
            n_name = st.text_input("Destino", value=r['destino'], key=f"n{r['id']}")
            n_price = st.number_input("Preço", value=r['preco'], key=f"p{r['id']}")
            c1, c2 = st.columns(2)
            if c1.button("Salvar", key=f"up{r['id']}"):
                conn = get_db_connection()
                conn.execute("UPDATE rotas SET destino=?, preco=? WHERE id=?", (n_name, n_price, r['id']))
                conn.commit()
                conn.close()
                st.rerun()
            if c2.button("Deletar", key=f"del{r['id']}"):
                conn = get_db_connection()
                conn.execute("DELETE FROM rotas WHERE id=?", (r['id'],))
                conn.commit()
                conn.close()
                st.rerun()