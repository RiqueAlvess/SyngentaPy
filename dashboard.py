import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import warnings
import os
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(
    page_title="Dashboard Saúde Ocupacional - Syngenta",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #2E8B57;
        text-align: center;
        margin: 2rem 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: linear-gradient(135deg, #2E8B57, #32CD32);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .metric-number {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    .metric-label {
        font-size: 1rem;
        margin: 0;
        opacity: 0.9;
    }
    .critical-alert {
        background: linear-gradient(45deg, #dc3545, #e74c3c);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 5px solid #c0392b;
    }
    .warning-alert {
        background: linear-gradient(45deg, #f39c12, #e67e22);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 5px solid #d35400;
    }
    .success-alert {
        background: linear-gradient(45deg, #27ae60, #2ecc71);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 5px solid #1e8449;
    }
    .kpi-container {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Carrega dados reais dos arquivos Excel"""
    data = {}
    
    # Mapeamento dos arquivos
    files = {
        'absenteismo': 'data/Absenteísmo 2025.xlsx',
        'absenteismo_doenca': 'data/Absenteísmo por Doença.xlsx',
        'taxa_absenteismo': 'data/Taxa Absenteismo.xlsx',
        'exames_alterados': 'data/Exames Alterados 2025.xlsx',
        'aso_validos': 'data/ASO Válidos.xlsx',
        'perfil_epidemiologico': 'data/Perfil Epidemiológico 2025.xlsx',
        'visitas_medicas': 'data/Visitas Médicas - Dr. Antonio 2025.xlsx',
        'consultas_tecnicas': 'data/Consultas Técnicas.xlsx',
        'controle_documentos': 'data/Controle Documentos.xlsx'
    }
    
    for key, file_path in files.items():
        try:
            if os.path.exists(file_path):
                df = pd.read_excel(file_path)
                
                # Processamento específico de datas
                if key in ['absenteismo', 'absenteismo_doenca', 'taxa_absenteismo']:
                    # Converter datas importantes
                    date_columns = ['Data de Nascimento', 'Data de Criação', 'Data da Ficha', 'Início', 'Fim', 'Retorno']
                    for col in date_columns:
                        if col in df.columns:
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                
                elif key == 'exames_alterados':
                    if 'Data do Exame' in df.columns:
                        df['Data do Exame'] = pd.to_datetime(df['Data do Exame'], errors='coerce')
                
                elif key == 'aso_validos':
                    date_cols = ['Dt.Nascimento', 'Data Último Exame', 'Dt.Demissão', 'Validade']
                    for col in date_cols:
                        if col in df.columns:
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                
                elif key == 'perfil_epidemiologico':
                    date_cols = ['Data de Nascimento', 'Data de Admissão', 'Data de Demissão', 'Data Ficha Clínica']
                    for col in date_cols:
                        if col in df.columns:
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                
                elif key in ['visitas_medicas', 'consultas_tecnicas']:
                    if 'DATA' in df.columns:
                        df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce')
                
                elif key == 'controle_documentos':
                    if 'Vencimento PCMSO ' in df.columns:
                        df['Vencimento PCMSO '] = pd.to_datetime(df['Vencimento PCMSO '], errors='coerce')
                
                data[key] = df
            else:
                st.error(f"Arquivo não encontrado: {file_path}")
                data[key] = pd.DataFrame()
                
        except Exception as e:
            st.error(f"Erro ao carregar {file_path}: {str(e)}")
            data[key] = pd.DataFrame()
    
    return data

def filter_by_date_range(df, date_col, days):
    """Filtra DataFrame por intervalo de dias"""
    if df.empty or date_col not in df.columns:
        return df
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Filtrar apenas registros válidos
    df_filtered = df[df[date_col].notna()].copy()
    mask = (df_filtered[date_col] >= start_date) & (df_filtered[date_col] <= end_date)
    return df_filtered[mask]

def calculate_kpis(data, selected_companies, days_filter):
    """Calcula KPIs principais baseados nos dados reais"""
    kpis = {}
    
    # Dados de absenteísmo
    abs_df = data['absenteismo'] if not data['absenteismo'].empty else data['taxa_absenteismo']
    
    if not abs_df.empty:
        # Filtrar por empresa
        if selected_companies and 'Todas' not in selected_companies:
            abs_df = abs_df[abs_df['Empresa'].isin(selected_companies)]
        
        # Filtrar por período
        abs_df_filtered = filter_by_date_range(abs_df, 'Início', days_filter)
        
        # KPIs de Absenteísmo
        kpis['total_funcionarios'] = abs_df['Funcionário'].nunique() if 'Funcionário' in abs_df.columns else 0
        kpis['total_afastamentos'] = len(abs_df_filtered)
        kpis['dias_perdidos'] = abs_df_filtered['Dias Afastados'].sum() if 'Dias Afastados' in abs_df_filtered.columns else 0
        kpis['media_dias_afastamento'] = abs_df_filtered['Dias Afastados'].mean() if 'Dias Afastados' in abs_df_filtered.columns and len(abs_df_filtered) > 0 else 0
        
        # Taxa de absenteísmo (%)
        if kpis['total_funcionarios'] > 0:
            # Assumindo 22 dias úteis por mês
            dias_uteis_periodo = (days_filter * 22) / 30
            kpis['taxa_absenteismo'] = (kpis['dias_perdidos'] / (kpis['total_funcionarios'] * dias_uteis_periodo)) * 100
        else:
            kpis['taxa_absenteismo'] = 0
    
    # Dados de exames
    exam_df = data['exames_alterados']
    if not exam_df.empty:
        if selected_companies and 'Todas' not in selected_companies:
            exam_df = exam_df[exam_df['Empresa'].isin(selected_companies)]
        
        exam_df_filtered = filter_by_date_range(exam_df, 'Data do Exame', days_filter)
        
        kpis['total_exames'] = len(exam_df_filtered)
        kpis['exames_alterados'] = len(exam_df_filtered[exam_df_filtered['Alterados'] == 'Sim']) if 'Alterados' in exam_df_filtered.columns else 0
        kpis['exames_ocupacionais_alterados'] = len(exam_df_filtered[exam_df_filtered['Alterados Ocupacionais'] == 'Sim']) if 'Alterados Ocupacionais' in exam_df_filtered.columns else 0
        
        # Taxas
        kpis['taxa_exames_alterados'] = (kpis['exames_alterados'] / kpis['total_exames'] * 100) if kpis['total_exames'] > 0 else 0
        kpis['taxa_ocupacionais_alterados'] = (kpis['exames_ocupacionais_alterados'] / kpis['total_exames'] * 100) if kpis['total_exames'] > 0 else 0
    
    # Dados de ASO
    aso_df = data['aso_validos']
    if not aso_df.empty:
        if selected_companies and 'Todas' not in selected_companies:
            aso_df = aso_df[aso_df['Empresa'].isin(selected_companies)]
        
        kpis['total_asos'] = len(aso_df)
        kpis['asos_vencidos'] = len(aso_df[aso_df['Status'] == 'Vencido']) if 'Status' in aso_df.columns else 0
        kpis['asos_pendentes'] = len(aso_df[aso_df['Status'] == 'Pendente']) if 'Status' in aso_df.columns else 0
        
        # Taxa de ASOs vencidos
        kpis['taxa_asos_vencidos'] = (kpis['asos_vencidos'] / kpis['total_asos'] * 100) if kpis['total_asos'] > 0 else 0
    
    return kpis

def generate_health_insights(data, kpis):
    """Gera insights inteligentes de saúde ocupacional"""
    insights = []
    warnings = []
    critical = []
    
    # Análise de Absenteísmo
    if kpis.get('taxa_absenteismo', 0) > 5:
        critical.append(f"🚨 Taxa de absenteísmo crítica: {kpis['taxa_absenteismo']:.1f}% (Meta: <3%)")
    elif kpis.get('taxa_absenteismo', 0) > 3:
        warnings.append(f"⚠️ Taxa de absenteísmo elevada: {kpis['taxa_absenteismo']:.1f}% (Meta: <3%)")
    else:
        insights.append(f"✅ Taxa de absenteísmo controlada: {kpis.get('taxa_absenteismo', 0):.1f}%")
    
    # Análise de duração de afastamentos
    if kpis.get('media_dias_afastamento', 0) > 20:
        critical.append(f"🚨 Duração média de afastamentos crítica: {kpis['media_dias_afastamento']:.1f} dias")
    elif kpis.get('media_dias_afastamento', 0) > 10:
        warnings.append(f"⚠️ Duração média de afastamentos elevada: {kpis['media_dias_afastamento']:.1f} dias")
    
    # Análise de exames alterados
    if kpis.get('taxa_ocupacionais_alterados', 0) > 10:
        critical.append(f"🚨 Taxa de exames ocupacionais alterados: {kpis['taxa_ocupacionais_alterados']:.1f}%")
    elif kpis.get('taxa_ocupacionais_alterados', 0) > 5:
        warnings.append(f"⚠️ Taxa de exames ocupacionais alterados: {kpis['taxa_ocupacionais_alterados']:.1f}%")
    
    # Análise de ASOs
    if kpis.get('taxa_asos_vencidos', 0) > 20:
        critical.append(f"🚨 Taxa de ASOs vencidos crítica: {kpis['taxa_asos_vencidos']:.1f}%")
    elif kpis.get('taxa_asos_vencidos', 0) > 10:
        warnings.append(f"⚠️ Taxa de ASOs vencidos: {kpis['taxa_asos_vencidos']:.1f}%")
    
    # Análise dos principais diagnósticos
    abs_df = data['absenteismo'] if not data['absenteismo'].empty else data['taxa_absenteismo']
    if not abs_df.empty and 'Descrição do Cid Principal' in abs_df.columns:
        top_diagnoses = abs_df['Descrição do Cid Principal'].value_counts().head(3)
        
        # Alertas específicos por tipo de diagnóstico
        mental_health_terms = ['depressivo', 'ansiedade', 'stress', 'psiquiátric']
        musculo_terms = ['coluna', 'lombar', 'cervical', 'articular', 'muscular']
        
        mental_cases = abs_df[abs_df['Descrição do Cid Principal'].str.contains('|'.join(mental_health_terms), case=False, na=False)]
        musculo_cases = abs_df[abs_df['Descrição do Cid Principal'].str.contains('|'.join(musculo_terms), case=False, na=False)]
        
        if len(mental_cases) / len(abs_df) > 0.3:
            warnings.append(f"⚠️ Alto índice de problemas de saúde mental: {len(mental_cases)} casos ({len(mental_cases)/len(abs_df)*100:.1f}%)")
        
        if len(musculo_cases) / len(abs_df) > 0.4:
            warnings.append(f"⚠️ Alto índice de problemas musculoesqueléticos: {len(musculo_cases)} casos ({len(musculo_cases)/len(abs_df)*100:.1f}%)")
    
    return insights, warnings, critical

def main():
    # Header com logo
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("https://www.syngenta.com/themes/custom/themekit/logo.svg", width=200)
        except:
            st.markdown("# 🌱 SYNGENTA")
    
    st.markdown('<h1 class="main-header">Dashboard Saúde Ocupacional</h1>', unsafe_allow_html=True)
    
    # Carregar dados
    with st.spinner('Carregando dados...'):
        data = load_data()
    
    # Verificar se os dados foram carregados
    data_loaded = any(not df.empty for df in data.values())
    
    if not data_loaded:
        st.error("❌ Não foi possível carregar os dados. Verifique se os arquivos estão na pasta 'data'.")
        st.info("Certifique-se de que a pasta 'data' contém os arquivos Excel necessários.")
        return
    
    # Sidebar - Filtros
    st.sidebar.header("🔍 Filtros de Análise")
    
    # Filtro de empresa
    all_companies = set()
    for df_name, df in data.items():
        if not df.empty and 'Empresa' in df.columns:
            all_companies.update(df['Empresa'].dropna().unique())
    
    all_companies = sorted(list(all_companies))
    
    if all_companies:
        selected_companies = st.sidebar.multiselect(
            "Selecione as Empresas:",
            options=['Todas'] + all_companies,
            default=['Todas']
        )
    else:
        selected_companies = ['Todas']
        st.sidebar.warning("Nenhuma empresa encontrada nos dados")
    
    # Filtro de período
    days_filter = st.sidebar.selectbox(
        "Período de Análise:",
        options=[30, 60, 90, 180, 365],
        index=2,  # Default: 90 dias
        format_func=lambda x: f"Últimos {x} dias"
    )
    
    # Calcular KPIs
    kpis = calculate_kpis(data, selected_companies, days_filter)
    
    # Gerar insights
    insights, warnings, critical = generate_health_insights(data, kpis)
    
    # === SEÇÃO DE ALERTAS ===
    st.header("🚨 Alertas e Insights")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if critical:
            for alert in critical:
                st.markdown(f'<div class="critical-alert">{alert}</div>', unsafe_allow_html=True)
    
    with col2:
        if warnings:
            for warning in warnings:
                st.markdown(f'<div class="warning-alert">{warning}</div>', unsafe_allow_html=True)
    
    with col3:
        if insights:
            for insight in insights:
                st.markdown(f'<div class="success-alert">{insight}</div>', unsafe_allow_html=True)
    
    # === SEÇÃO DE KPIs PRINCIPAIS ===
    st.header("📊 KPIs Principais")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-number">{kpis.get('total_funcionarios', 0)}</p>
            <p class="metric-label">Funcionários</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-number">{kpis.get('total_afastamentos', 0)}</p>
            <p class="metric-label">Afastamentos ({days_filter}d)</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-number">{kpis.get('taxa_absenteismo', 0):.1f}%</p>
            <p class="metric-label">Taxa Absenteísmo</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-number">{kpis.get('dias_perdidos', 0)}</p>
            <p class="metric-label">Dias Perdidos</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-number">{kpis.get('asos_vencidos', 0)}</p>
            <p class="metric-label">ASOs Vencidos</p>
        </div>
        """, unsafe_allow_html=True)
    
    # === ANÁLISES DETALHADAS ===
    st.header("📈 Análises Detalhadas")
    
    # Análise de Absenteísmo
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏥 Principais Diagnósticos")
        
        abs_df = data['absenteismo'] if not data['absenteismo'].empty else data['taxa_absenteismo']
        if not abs_df.empty and 'Descrição do Cid Principal' in abs_df.columns:
            # Filtrar por empresa
            if selected_companies and 'Todas' not in selected_companies:
                abs_df = abs_df[abs_df['Empresa'].isin(selected_companies)]
            
            abs_df_filtered = filter_by_date_range(abs_df, 'Início', days_filter)
            
            if not abs_df_filtered.empty:
                diagnoses = abs_df_filtered['Descrição do Cid Principal'].value_counts().head(10)
                
                fig = px.bar(
                    y=diagnoses.index,
                    x=diagnoses.values,
                    orientation='h',
                    title="Top 10 Diagnósticos mais Frequentes",
                    labels={'x': 'Número de Casos', 'y': 'Diagnóstico'}
                )
                fig.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    height=400,
                    template="plotly_white"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum dado de diagnóstico disponível para o período selecionado")
        else:
            st.info("Dados de diagnósticos não disponíveis")
    
    with col2:
        st.subheader("📊 Distribuição por Especialidade Médica")
        
        if not abs_df.empty and 'Especialidade' in abs_df.columns:
            abs_df_filtered = filter_by_date_range(abs_df, 'Início', days_filter)
            
            if not abs_df_filtered.empty:
                especialidades = abs_df_filtered['Especialidade'].value_counts()
                
                fig = px.pie(
                    values=especialidades.values,
                    names=especialidades.index,
                    title="Distribuição por Especialidade"
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum dado de especialidade disponível")
        else:
            st.info("Dados de especialidades não disponíveis")
    
    # Análise Temporal
    st.subheader("📈 Evolução Temporal do Absenteísmo")
    
    if not abs_df.empty and 'Início' in abs_df.columns:
        abs_df_filtered = filter_by_date_range(abs_df, 'Início', days_filter)
        
        if not abs_df_filtered.empty:
            # Agrupar por mês
            abs_df_filtered['Mês'] = abs_df_filtered['Início'].dt.to_period('M')
            monthly_data = abs_df_filtered.groupby('Mês').agg({
                'Funcionário': 'count',
                'Dias Afastados': 'sum'
            }).reset_index()
            monthly_data['Mês'] = monthly_data['Mês'].astype(str)
            
            # Criar subplot com duas métricas
            fig = make_subplots(
                rows=1, cols=2,
                subplot_titles=('Número de Casos por Mês', 'Dias Perdidos por Mês'),
                specs=[[{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            # Gráfico de casos
            fig.add_trace(
                go.Scatter(
                    x=monthly_data['Mês'],
                    y=monthly_data['Funcionário'],
                    mode='lines+markers',
                    name='Casos',
                    line=dict(color='#2E8B57', width=3)
                ),
                row=1, col=1
            )
            
            # Gráfico de dias perdidos
            fig.add_trace(
                go.Bar(
                    x=monthly_data['Mês'],
                    y=monthly_data['Dias Afastados'],
                    name='Dias Perdidos',
                    marker_color='#32CD32'
                ),
                row=1, col=2
            )
            
            fig.update_layout(
                height=400,
                template="plotly_white",
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Análise de Exames
    st.subheader("🔬 Análise de Exames Ocupacionais")
    
    col1, col2 = st.columns(2)
    
    with col1:
        exam_df = data['exames_alterados']
        if not exam_df.empty:
            if selected_companies and 'Todas' not in selected_companies:
                exam_df = exam_df[exam_df['Empresa'].isin(selected_companies)]
            
            exam_df_filtered = filter_by_date_range(exam_df, 'Data do Exame', days_filter)
            
            if not exam_df_filtered.empty:
                # Status dos exames
                fig = go.Figure()
                
                total_exams = len(exam_df_filtered)
                altered = len(exam_df_filtered[exam_df_filtered['Alterados'] == 'Sim'])
                normal = total_exams - altered
                
                fig.add_trace(go.Bar(
                    x=['Normal', 'Alterado'],
                    y=[normal, altered],
                    marker_color=['#2ecc71', '#e74c3c'],
                    text=[f'{normal}<br>({normal/total_exams*100:.1f}%)', 
                          f'{altered}<br>({altered/total_exams*100:.1f}%)'],
                    textposition='inside'
                ))
                
                fig.update_layout(
                    title="Status dos Exames Realizados",
                    yaxis_title="Número de Exames",
                    template="plotly_white",
                    height=300
                )
                
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if not exam_df_filtered.empty and 'Tipo' in exam_df_filtered.columns:
            # Tipos de exame
            exam_types = exam_df_filtered['Tipo'].value_counts()
            
            fig = px.pie(
                values=exam_types.values,
                names=exam_types.index,
                title="Distribuição por Tipo de Exame"
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    # Análise de ASO
    st.subheader("📋 Status dos ASOs")
    
    aso_df = data['aso_validos']
    if not aso_df.empty:
        if selected_companies and 'Todas' not in selected_companies:
            aso_df = aso_df[aso_df['Empresa'].isin(selected_companies)]
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Status dos ASOs
            if 'Status' in aso_df.columns:
                status_counts = aso_df['Status'].value_counts()
                
                colors = {'Válido': '#2ecc71', 'Vencido': '#e74c3c', 'Pendente': '#f39c12'}
                
                fig = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    title="Status dos ASOs",
                    color=status_counts.index,
                    color_discrete_map=colors
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # ASOs por unidade
            if 'Unidade' in aso_df.columns:
                unit_counts = aso_df['Unidade'].value_counts().head(10)
                
                fig = px.bar(
                    x=unit_counts.values,
                    y=unit_counts.index,
                    orientation='h',
                    title="ASOs por Unidade",
                    labels={'x': 'Quantidade', 'y': 'Unidade'}
                )
                fig.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    template="plotly_white"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # Tabelas de dados detalhados
    st.header("📋 Dados Detalhados")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Absenteísmo", "🔬 Exames", "📋 ASO", "🏥 Visitas"])
    
    with tab1:
        if not abs_df.empty:
            abs_display = abs_df[['Empresa', 'Funcionário', 'Início', 'Fim', 'Dias Afastados', 
                                'Descrição do Cid Principal', 'Especialidade']].head(20)
            st.dataframe(abs_display, use_container_width=True)
        else:
            st.info("Dados de absenteísmo não disponíveis")
    
    with tab2:
        if not data['exames_alterados'].empty:
            exam_display = data['exames_alterados'][['Empresa', 'Funcionário', 'Tipo', 'Data do Exame',
                                                   'Alterados', 'Alterados Ocupacionais', 'Parecer do ASO']].head(20)
            st.dataframe(exam_display, use_container_width=True)
        else:
            st.info("Dados de exames não disponíveis")
    
    with tab3:
        if not data['aso_validos'].empty:
            aso_display = data['aso_validos'][['Empresa', 'Nome', 'Unidade', 'Cargo', 
                                             'Data Último Exame', 'Status', 'Validade']].head(20)
            st.dataframe(aso_display, use_container_width=True)
        else:
            st.info("Dados de ASO não disponíveis")
    
    with tab4:
        if not data['visitas_medicas'].empty:
            st.dataframe(data['visitas_medicas'].head(20), use_container_width=True)
        else:
            st.info("Dados de visitas não disponíveis")
    
    # Footer
    st.markdown("---")
    st.markdown("**Dashboard Saúde Ocupacional - Syngenta** | Análise baseada em dados recebidos")

if __name__ == "__main__":
    main()