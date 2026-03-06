# --- 7. INDICADORES (DASHBOARD DE PERFORMANCE E AGING) ---
if menu == "📊 INDICADORES":
    df_v = carregar_vagas()
    df_c = pd.read_sql("SELECT * FROM candidatos", engine)
    
    if not df_v.empty and not df_c.empty:
        # Preparação de Datas
        hoje = pd.Timestamp(datetime.now().date())
        df_v['data_abertura'] = pd.to_datetime(df_v['data_abertura'])
        
        # 1. MÉTRICAS EXECUTIVAS (CARDS)
        st.markdown("### 📈 Visão Geral")
        c1, c2, c3, c4 = st.columns(4)
        
        vagas_abertas = df_v[df_v['status_vaga'] == 'Aberta']
        avg_aging = int(vagas_abertas['data_abertura'].apply(lambda x: (hoje - x).days).mean()) if not vagas_abertas.empty else 0
        
        c1.metric("📌 VAGAS ABERTAS", len(vagas_abertas))
        c2.metric("⏱️ AGING MÉDIO", f"{avg_aging} dias")
        c3.metric("👥 CANDIDATOS ATIVOS", len(df_c[df_c['status_geral'] != 'Finalizada']))
        c4.metric("✅ CONTRATAÇÕES", len(df_c[df_c['status_geral'] == 'Finalizada']))
        
        st.divider()

        # 2. DASHBOARD DE TEMPO POR ETAPA (LEAD TIME)
        st.subheader("⏳ Performance: Dias por Etapa")
        
        # Cruzamento de dados para calcular intervalos
        df_c['entrevista_rh'] = pd.to_datetime(df_c['entrevista_rh'])
        df_c['entrevista_gestor'] = pd.to_datetime(df_c['entrevista_gestor'])
        df_c['entrevista_cultura'] = pd.to_datetime(df_c['entrevista_cultura'])
        
        df_dash = df_c.merge(df_v[['nome_vaga', 'data_abertura']], left_on='vaga_vinculada', right_on='nome_vaga')
        
        # Cálculos de intervalos (diferença entre etapas)
        df_dash['Abertura -> RH'] = (df_dash['entrevista_rh'] - df_dash['data_abertura']).dt.days
        df_dash['RH -> Gestor'] = (df_dash['entrevista_gestor'] - df_dash['entrevista_rh']).dt.days
        df_dash['Gestor -> Cultura'] = (df_dash['entrevista_cultura'] - df_dash['entrevista_gestor']).dt.days
        
        # Ajuste de valores nulos/negativos para 0 (limpeza de dados)
        etapas_cols = ['Abertura -> RH', 'RH -> Gestor', 'Gestor -> Cultura']
        for col in etapas_cols:
            df_dash[col] = df_dash[col].apply(lambda x: x if x > 0 else 0)

        # Gráfico de Barras Empilhadas (Horizontal para facilitar leitura de nomes)
        fig_lead = px.bar(
            df_dash, 
            y="candidato", 
            x=etapas_cols,
            orientation='h',
            title="Tempo acumulado por candidato (dias)",
            color_discrete_sequence=["#8DF768", "#4CAF50", "#1B5E20"], # Gradiente de Verde Etus
            barmode="stack"
        )
        
        fig_lead.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)', 
            font_color="white",
            legend_title="Etapas do Processo"
        )
        st.plotly_chart(fig_lead, use_container_width=True)

        # 3. AGING INDIVIDUAL DAS VAGAS
        st.divider()
        col_inf1, col_inf2 = st.columns(2)
        
        with col_inf1:
            st.subheader("🏢 Aging por Vaga")
            vagas_abertas['dias'] = vagas_abertas['data_abertura'].apply(lambda x: (hoje - x).days)
            fig_vagas = px.bar(vagas_abertas, x='dias', y='nome_vaga', orientation='h', 
                               color='dias', color_continuous_scale='Greens')
            st.plotly_chart(fig_vagas, use_container_width=True)

        with col_inf2:
            st.subheader("📊 Distribuição do Funil")
            fig_pie = px.pie(df_c, names='status_geral', hole=0.5, 
                             color_discrete_sequence=px.colors.sequential.Greens_r)
            st.plotly_chart(fig_pie, use_container_width=True)
            
    else:
        st.info("💡 Para visualizar o Dashboard, certifique-se de que existem Vagas cadastradas e Candidatos com datas preenchidas.")
