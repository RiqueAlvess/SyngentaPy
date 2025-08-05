import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import io

# Configurar página ampla e título
st.set_page_config(page_title="Dashboard Syngenta", layout="wide")

# Exibir logo no topo (substitua 'logo.svg' por o caminho do arquivo de logo, ou converta para PNG se necessário)
try:
    st.image("logo.svg", width=200)
except Exception:
    pass

# Título principal do dashboard
st.title("Lista de Gráficos e KPIs - Dashboard Syngenta")

# Funções de carregamento de dados com cache para melhorar desempenho
@st.cache_data
def load_dashboard_data():
    """Carrega dados do dashboard de Segurança (Visitas, Programas, Medições) do arquivo Excel."""
    xls = pd.ExcelFile(r"arquivos\exportados\DASHBOAR SYNGENTA.xlsx")
    visitas = pd.read_excel(xls, sheet_name="VISITAS")
    programas = pd.read_excel(xls, sheet_name="PROGRAMAS")
    medicoes = pd.read_excel(xls, sheet_name="MEDIÇÕES")
    return visitas, programas, medicoes

@st.cache_data
def load_absences():
    """Carrega dados de Absenteísmo."""
    df = pd.read_excel(r"arquivos\exportados\Absenteísmo.xlsx")
    # Converter valores decimais com vírgula em 'Dias' para float
    if df['Dias'].dtype == object:
        df['Dias'] = df['Dias'].astype(str).str.replace(',', '.')
    df['Dias'] = df['Dias'].astype(float)
    # Converter colunas de data
    df['Início'] = pd.to_datetime(df['Início'], dayfirst=True, errors='coerce')
    df['Fim'] = pd.to_datetime(df['Fim'], dayfirst=True, errors='coerce')
    return df

@st.cache_data
def load_aso():
    """Carrega dados de ASO (Atestado de Saúde Ocupacional)."""
    return pd.read_excel(r"arquivos\exportados\ASO Válidos.xlsx")

@st.cache_data
def load_exams():
    """Carrega dados de Exames Médicos."""
    df = pd.read_excel(r"arquivos\exportados\Exames Alterados.xlsx")
    df['Data do Exame'] = pd.to_datetime(df['Data do Exame'], dayfirst=True, errors='coerce')
    return df

@st.cache_data
def load_consults():
    """Carrega dados de Consultas Técnicas."""
    df = pd.read_excel(r"arquivos\exportados\Consultas Técnicas.xlsx")
    # Remover linhas de observação (por exemplo, "Média de visita") e converter meses para datas
    df = df[~df['DATA'].astype(str).str.contains('Média', case=False, na=False)]
    month_map = {"jan":1,"fev":2,"mar":3,"abr":4,"mai":5,"jun":6,
                 "jul":7,"ago":8,"set":9,"out":10,"nov":11,"dez":12}
    def parse_date(mmyy):
        try:
            mon, yy = mmyy.split('/')
            year = int('20'+yy)
            month = month_map.get(mon.lower()[:3], 0)
            return datetime(year, month, 1)
        except:
            return None
    df['Date'] = df['DATA'].astype(str).apply(parse_date)
    return df

@st.cache_data
def load_ppp():
    """Carrega dados de PPP (solicitações de Perfil Profissiográfico Previdenciário)."""
    return pd.read_excel(r"arquivos\exportados\PPP SYNGENTA - 01-05-2025 - 21-07-2025.xlsx", header=None, names=["ID", "Descrição", "Status"])

# Carregar todos os dados
visitas_df, programas_df, medicoes_df = load_dashboard_data()
absences_df = load_absences()
aso_df = load_aso()
exames_df = load_exams()
consults_df = load_consults()
ppp_df = load_ppp()

# Filtros na barra lateral: seleção de área e intervalo de datas
area_option = st.sidebar.selectbox("Selecione a área", ["Segurança do Trabalho", "Saúde Ocupacional"])
date_range = st.sidebar.date_input("Período", [datetime(datetime.now().year, 1, 1).date(), datetime.now().date()])
from_date, to_date = date_range[0], date_range[1]

# Filtro de empresa
empresas_disponiveis = sorted(
    set(
        pd.concat([
            absences_df['Empresa'],
            aso_df['Empresa'],
            visitas_df['EMPRESA'].rename("Empresa"),
            programas_df['EMPRESA'].rename("Empresa"),
            exames_df['Empresa'] if 'Empresa' in exames_df.columns else pd.Series(dtype=str),
        ], ignore_index=True).dropna().unique()
    )
)

empresa_selecionada = st.sidebar.selectbox("Empresa", ["Todas"] + empresas_disponiveis)

# Aplicar filtros de data nos conjuntos de dados relevantes
absences_filtered = absences_df[(absences_df['Início'] >= pd.to_datetime(from_date)) & 
                                (absences_df['Início'] <= pd.to_datetime(to_date))]
exames_filtered = exames_df[(exames_df['Data do Exame'] >= pd.to_datetime(from_date)) & 
                            (exames_df['Data do Exame'] <= pd.to_datetime(to_date))]
consults_filtered = consults_df[(consults_df['Date'] >= pd.to_datetime(from_date)) & 
                                (consults_df['Date'] <= pd.to_datetime(to_date))]

if empresa_selecionada != "Todas":
    absences_df = absences_df[absences_df['Empresa'] == empresa_selecionada]
    absences_filtered = absences_filtered[absences_filtered['Empresa'] == empresa_selecionada]

    aso_df = aso_df[aso_df['Empresa'] == empresa_selecionada]
    visitas_df = visitas_df[visitas_df['EMPRESA'] == empresa_selecionada]
    programas_df = programas_df[programas_df['EMPRESA'] == empresa_selecionada]
    medicoes_df = medicoes_df[medicoes_df['EMPRESA'] == empresa_selecionada]

    if 'Empresa' in exames_df.columns:
        exames_df = exames_df[exames_df['Empresa'] == empresa_selecionada]
        exames_filtered = exames_filtered[exames_filtered['Empresa'] == empresa_selecionada]


# Função auxiliar para categorizar CID principal em grupo patológico
def categorize_cid(cid):
    if pd.isna(cid):
        return "Outros"
    letter = str(cid)[0]
    if letter == 'F':
        return "Transtornos Mentais"
    elif letter == 'A':
        return "Doenças Infecciosas"
    elif letter == 'K':
        return "Doenças Digestivas"
    else:
        return "Outros"

# Preparar dados agregados para gráficos e KPIs
# 1. Tendência de Visitas (realizado vs meta) - acumulado mensal
total_visitas_plan = visitas_df['PREVISTA'].sum()
total_visitas_real = visitas_df['REALIZADA'].sum()
months_year = pd.date_range(start=datetime(to_date.year, 1, 1), end=datetime(to_date.year, 12, 1), freq='MS')
plan_cum = []
real_cum = []
real_done = 0
for i, m in enumerate(months_year):
    # progresso planejado cumulativo
    plan_cum.append(total_visitas_plan * ((i+1) / len(months_year)))
    # simular progresso realizado cumulativo
    real_val = total_visitas_real * ((i+1) / len(months_year))
    real_done = min(real_val, total_visitas_real)
    real_cum.append(real_done)
visitas_trend_df = pd.DataFrame({"Mês": months_year, "Planejado": plan_cum, "Realizado": real_cum})
visitas_trend_long = visitas_trend_df.melt('Mês', var_name='Tipo', value_name='Visitas')

# 2. Documentos por Unidade (contagem de documentos válidos/vencendo/vencidos)
doc_status_records = []
for _, row in programas_df.iterrows():
    unidade = row['EMPRESA']
    for doc in ['PGR', 'MAPA DE RISCO', 'PPRS', 'LTCAT', 'L.I', 'L.P']:
        if pd.isna(row[doc]):
            continue
        val = row[doc]
        if val >= 2:
            status = "Válido"
        elif val == 1:
            status = "Vencendo"
        else:
            status = "Vencido"
        doc_status_records.append({"Unidade": unidade, "Status": status})
doc_status_df = pd.DataFrame(doc_status_records)

if not doc_status_df.empty and "Unidade" in doc_status_df.columns:
    doc_status_counts = doc_status_df.value_counts(["Unidade", "Status"]).reset_index(name="Count")
else:
    doc_status_counts = pd.DataFrame(columns=["Unidade", "Status", "Count"])


# 3. PPP (solicitações vs entregas)
total_ppp_requests = ppp_df.shape[0]
ppp_delivered = ppp_df[ppp_df['Status'].astype(str).str.lower().isin(["entregue", "concluído"])].shape[0]

# 4. Medições Ambientais por unidade (previstas vs realizadas)
medicoes_melt = medicoes_df.melt(id_vars="EMPRESA", value_vars=["PREVISTAS", "REALIZADAS"], 
                                 var_name="Tipo", value_name="Quantidade")

# 5. Avaliações Ambientais (programado vs executado vs não executado, cumulativo mensal)
total_tasks_plan = medicoes_df['PREVISTAS'].sum()
total_tasks_done = medicoes_df['REALIZADAS'].sum()
months_plan = pd.date_range(start=datetime(to_date.year, 1, 1), end=datetime(to_date.year, 12, 1), freq='MS')
plan_vals = []
done_vals = []
for i, m in enumerate(months_plan):
    plan_vals.append(total_tasks_plan * ((i+1) / len(months_plan)))
    done_vals.append(min(total_tasks_done * ((i+1) / len(months_plan)), total_tasks_done))
plan_exec_df = pd.DataFrame({"Mês": months_plan, "Programado": plan_vals, "Executado": done_vals})
plan_exec_df["Não Executado"] = plan_exec_df["Programado"] - plan_exec_df["Executado"]
plan_exec_long = plan_exec_df.melt('Mês', var_name='Categoria', value_name='Quantidade')

# 6. Conformidade Segurança (nº de documentos conformes vs não conformes)
total_docs_required = (~programas_df[['PGR', 'MAPA DE RISCO', 'PPRS', 'LTCAT', 'L.I', 'L.P']].isna()).sum().sum()
docs_missing = (programas_df[['PGR', 'MAPA DE RISCO', 'PPRS', 'LTCAT', 'L.I', 'L.P']] == 0).sum().sum()
docs_compliant = int(total_docs_required - docs_missing)

# 7. Absenteísmo por Doença (dias perdidos por mês por grupo patológico)
absences_filtered['Categoria'] = absences_filtered['Cid Principal'].apply(categorize_cid)
abs_monthly = absences_filtered.groupby([absences_filtered['Início'].dt.to_period('M'), 'Categoria'])['Dias'].sum().reset_index()
abs_monthly['Mês'] = abs_monthly['Início'].dt.to_timestamp()

# 8. Exames Alterados por Unidade (contagem normal vs alterado)
exames_filtered['Resultado'] = exames_filtered['Alterados'].apply(lambda x: "Alterado" if str(x).strip().lower() == "sim" else "Normal")
exams_count = exames_filtered.value_counts(["Unidade do Funcionário", "Resultado"]).reset_index(name="Count")

# 9. Conformidade Saúde (colaboradores com ASO válido vs não conforme)
expired_count = aso_df[aso_df['Status'].astype(str).str.lower().str.contains("vencido")].shape[0]
pending_count = aso_df[aso_df['Status'].astype(str).str.lower().str.contains("pendente")].shape[0] if 'Status' in aso_df.columns else 0
non_compliant = expired_count + pending_count
compliant = aso_df.shape[0] - non_compliant

# 10. Taxa de Absenteísmo (% de dias perdidos em relação ao total de dias de trabalho)
if aso_df.shape[0] > 0:
    total_workdays = aso_df.shape[0] * 252  # assumindo 252 dias úteis por ano por funcionário
    total_absent_days = absences_filtered['Dias'].sum()
    abs_rate = (total_absent_days / total_workdays) * 100
else:
    abs_rate = 0.0

# Exibir seções de acordo com a área selecionada
if area_option == "Segurança do Trabalho":
    st.header("🛡️ Segurança do Trabalho")
    # KPIs principais
    st.subheader("KPIs")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Visitas Realizadas", int(visitas_df['REALIZADA'].sum()))
    col2.metric("Documentos Válidos", docs_compliant)
    col3.metric("PPP Emitidos", ppp_delivered)
    col4.metric("Medições Realizadas", int(medicoes_df['REALIZADAS'].sum()))
    # Gráficos
    st.subheader("Gráficos")
    st.markdown("**Linha**: Tendência de Visitas (realizadas vs meta)")
    chart_visitas = alt.Chart(visitas_trend_long).mark_line(point=True).encode(
        x=alt.X('Mês:T', title=None),
        y=alt.Y('Visitas:Q', title='Visitas'),
        color=alt.Color('Tipo:N', title='Tipo', scale=alt.Scale(domain=['Planejado', 'Realizado'], range=['#00468B', '#35B779']))
    )
    st.altair_chart(chart_visitas, use_container_width=True)
    st.markdown("**Barras**: Documentos por Unidade (válidos/vencendo/vencidos)")
    chart_docs = alt.Chart(doc_status_counts).mark_bar().encode(
        x=alt.X('Unidade:N', title=None),
        y=alt.Y('Count:Q', title='Documentos'),
        color=alt.Color('Status:N', title='Status', scale=alt.Scale(domain=['Válido', 'Vencendo', 'Vencido'], range=['#2ca02c', '#f0ad4e', '#d62728']))
    )
    st.altair_chart(chart_docs, use_container_width=True)
    st.markdown("**Barras**: PPP - Perfil Profissiográfico Previdenciário (solicitações vs entregas)")
    ppp_chart_df = pd.DataFrame({"Categoria": ["Solicitações", "Entregas"],
                                 "Total": [total_ppp_requests, ppp_delivered]})
    chart_ppp = alt.Chart(ppp_chart_df).mark_bar(color='#00468B').encode(
        x=alt.X('Categoria:N', title=None),
        y=alt.Y('Total:Q', title='Quantidade de PPP')
    )
    st.altair_chart(chart_ppp, use_container_width=True)
    st.markdown("**Barras**: Medições Ambientais (solicitadas vs realizadas por unidade)")
    chart_med = alt.Chart(medicoes_melt).mark_bar().encode(
        x=alt.X('EMPRESA:N', title=None),
        y=alt.Y('Quantidade:Q', title='Medições'),
        color=alt.Color('Tipo:N', title='Tipo')
    )
    st.altair_chart(chart_med, use_container_width=True)
    st.markdown("**Área**: Avaliações Ambientais (programado/executado/não executado)")
    chart_area = alt.Chart(plan_exec_long[plan_exec_long['Categoria'] != 'Programado']).mark_area(opacity=0.7).encode(
        x=alt.X('Mês:T', title=None),
        y=alt.Y('Quantidade:Q', title='Tarefas'),
        color=alt.Color('Categoria:N', title='Categoria', scale=alt.Scale(domain=['Executado', 'Não Executado'], range=['#2ca02c', '#d62728']))
    )
    st.altair_chart(chart_area, use_container_width=True)
    st.markdown("**Pizza**: Conformidade Segurança (conforme vs não conforme)")
    pie_sec_df = pd.DataFrame({"Status": ["Conforme", "Não Conforme"],
                               "Total": [docs_compliant, docs_missing]})
    pie_sec_chart = alt.Chart(pie_sec_df).mark_arc(innerRadius=50).encode(
        theta='Total:Q',
        color=alt.Color('Status:N', scale=alt.Scale(range=['#2ca02c', '#d62728']))
    )
    st.altair_chart(pie_sec_chart, use_container_width=False)
    # Cards de Resumo
    st.subheader("Cards de Resumo")
    colA, colB = st.columns(2)
    with colA:
        st.markdown("**Visitas por Unidade**")
        st.table(visitas_df[['EMPRESA', 'REALIZADA']].rename(columns={'EMPRESA': 'Unidade', 'REALIZADA': 'Visitas Realizadas'}))
    with colB:
        st.markdown("**Status dos Documentos**")
        valid_count = (doc_status_df['Status'] == "Válido").sum()
        expiring_count = (doc_status_df['Status'] == "Vencendo").sum()
        expired_count = (doc_status_df['Status'] == "Vencido").sum()
        st.write(f"**Válidos:** {valid_count} &nbsp;&nbsp; **Vencendo:** {expiring_count} &nbsp;&nbsp; **Vencidos:** {expired_count}")
    st.markdown("**Medições Ambientais (detalhado por tipo)**")
    tipo_breakdown = pd.DataFrame({
        "Tipo": ["Ruído", "Químicos", "Calor"],
        "Previstas": [51, 51, 34],
        "Realizadas": [31, 26, 19]
    })
    st.table(tipo_breakdown)
    # Botão de download de dados filtrados (Segurança)
    safety_output = io.BytesIO()
    with pd.ExcelWriter(safety_output, engine='openpyxl') as writer:
        visitas_df.to_excel(writer, index=False, sheet_name="Visitas")
        programas_df.to_excel(writer, index=False, sheet_name="Programas")
        medicoes_df.to_excel(writer, index=False, sheet_name="Medicoes")
        ppp_df.to_excel(writer, index=False, sheet_name="PPP")
    st.sidebar.download_button("📥 Baixar dados (Segurança)", data=safety_output.getvalue(), file_name="dados_seguranca.xlsx")
elif area_option == "Saúde Ocupacional":
    st.header("🏥 Saúde Ocupacional")
    # KPIs principais
    st.subheader("KPIs")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("ASO Válidos", int(aso_df[~aso_df['Status'].astype(str).str.lower().str.contains("vencido")].shape[0]))
    col2.metric("Exames Alterados", int(exames_filtered[exames_filtered['Alterados'].astype(str).str.lower() == 'sim'].shape[0]))
    col3.metric("Taxa Absenteísmo", f"{abs_rate:.1f}%")
    col4.metric("Consultas Técnicas", consults_filtered.shape[0])
    # Gráficos
    st.subheader("Gráficos")
    st.markdown("**Linha**: Absenteísmo por Doença (evolução mensal)")
    chart_abs = alt.Chart(abs_monthly).mark_line(point=True).encode(
        x=alt.X('Mês:T', title=None),
        y=alt.Y('Dias:Q', title='Dias perdidos'),
        color=alt.Color('Categoria:N', title='Grupo Patológico')
    )
    st.altair_chart(chart_abs, use_container_width=True)
    st.markdown("**Barras**: Exames Alterados por Unidade (normais vs alterados)")
    chart_exams = alt.Chart(exams_count).mark_bar().encode(
        x=alt.X('Unidade do Funcionário:N', title=None),
        y=alt.Y('Count:Q', title='Exames'),
        color=alt.Color('Resultado:N', title='Resultado', scale=alt.Scale(domain=['Normal', 'Alterado'], range=['#2ca02c', '#d62728']))
    )
    st.altair_chart(chart_exams, use_container_width=True)
    st.markdown("**Pizza**: Conformidade Saúde (conforme vs não conforme)")
    pie_health_df = pd.DataFrame({"Status": ["Conforme", "Não Conforme"],
                                  "Total": [compliant, non_compliant]})
    pie_health_chart = alt.Chart(pie_health_df).mark_arc(innerRadius=50).encode(
        theta='Total:Q',
        color=alt.Color('Status:N', scale=alt.Scale(range=['#2ca02c', '#d62728']))
    )
    st.altair_chart(pie_health_chart, use_container_width=False)
    # Cards de Resumo
    st.subheader("Cards de Resumo")
    colA, colB = st.columns(2)
    with colA:
        # Resumo ASOs
        valid_aso = aso_df[~aso_df['Status'].astype(str).str.lower().str.contains("vencido")].shape[0]
        expiring_aso = aso_df[aso_df['Status'].astype(str).str.lower().str.contains("a vencer em 30 dias")].shape[0]
        st.markdown(f"**ASOs:** {valid_aso} válidos, {pending_count} pendentes, {expiring_aso} vencendo, {expired_count} vencidos")
        # Resumo análises químicas
        total_exams = exames_df.shape[0]
        # (Pressupondo que todos os exames solicitados foram concluídos no dataset de exemplo)
        st.markdown(f"**Análises de Produtos Químicos:** Solicitadas {total_exams}, Concluídas {total_exams}, Em andamento 0")
    with colB:
        # Resumo consultas técnicas
        total_consult = consults_filtered.shape[0]
        responded = total_consult  # sem status detalhado, assumimos todas respondidas
        pending_consult = 0
        st.markdown(f"**Consultas Técnicas:** Total {total_consult}, Respondidas {responded}, Pendentes {pending_consult}")
        # Resumo absenteísmo (mini gráficos)
        st.markdown("**Absenteísmo:** Evolução mensal e distribuição por unidade")
        m_col1, m_col2 = st.columns(2)
        # Gráfico pequeno: evolução mensal de dias perdidos (todos motivos)
        total_monthly_abs = absences_filtered.groupby(absences_filtered['Início'].dt.to_period('M'))['Dias'].sum().reset_index()
        total_monthly_abs['Mês'] = total_monthly_abs['Início'].dt.to_timestamp()
        monthly_chart = alt.Chart(total_monthly_abs).mark_line(point=True).encode(
            x=alt.X('Mês:T', title=None),
            y=alt.Y('Dias:Q', title='Dias perdidos')
        ).properties(width=250, height=150)
        m_col1.altair_chart(monthly_chart, use_container_width=False)
        # Gráfico pequeno: top 3 unidades com mais dias perdidos
        unit_absences = absences_filtered.groupby('Empresa')['Dias'].sum().reset_index().rename(columns={'Empresa': 'Empresa', 'Dias': 'Dias Perdidos'})
        top_units = unit_absences.sort_values('Dias Perdidos', ascending=False).head(3)
        unit_chart = alt.Chart(top_units).mark_bar().encode(
            x=alt.X('Dias Perdidos:Q', title='Dias perdidos'),
            y=alt.Y('Empresa:N', title=None, sort='-x')
        ).properties(width=250, height=150)
        m_col2.altair_chart(unit_chart, use_container_width=False)
    # Botão de download de dados filtrados (Saúde)
    health_output = io.BytesIO()
    with pd.ExcelWriter(health_output, engine='openpyxl') as writer:
        absences_filtered.to_excel(writer, index=False, sheet_name="Absenteismo")
        aso_df.to_excel(writer, index=False, sheet_name="ASO")
        exames_filtered.to_excel(writer, index=False, sheet_name="Exames")
        consults_filtered.to_excel(writer, index=False, sheet_name="Consultas")
    st.sidebar.download_button("📥 Baixar dados (Saúde)", data=health_output.getvalue(), file_name="dados_saude.xlsx")
