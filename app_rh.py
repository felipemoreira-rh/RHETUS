# --- 6. ABA: INDICADORES (CORRIGIDO) ---
if menu == "📊 INDICADORES":
    df_v = carregar_vagas()
    df_c = carregar_candidatos()
    
    if not df_v.empty:
        # Garantir que as colunas são datetime
        df_v['data_abertura'] = pd.to_datetime(df_v['data_abertura'], errors='coerce')
        df_v['data_fechamento'] = pd.to_datetime(df_v['data_fechamento'], errors='coerce')
        
        # 1. TIME-TO-HIRE (Vagas Finalizadas)
        df_fechadas = df_v[df_v['status_vaga'] == 'Finalizada'].copy()
        
        # Proteção contra valores nulos nas datas
        df_fechadas = df_fechadas.dropna(subset=['data_abertura', 'data_fechamento'])
        
        if not df_fechadas.empty:
            df_fechadas['time_to_hire'] = (df_fechadas['data_fechamento'] - df_fechadas['data_abertura']).dt.days
            # Usamos mean() com proteção para não retornar NaN
            media_calculada = df_fechadas['time_to_hire'].mean()
            avg_tth = int(media_calculada) if pd.notnull(media_calculada) else 0
        else:
            avg_tth = 0

        # 2. MÉTRICAS TOPO
        c1, c2, c3 = st.columns(3)
        v_abertas = len(df_v[df_v['status_vaga'] == 'Aberta'])
        c1.metric("📌 VAGAS ATIVAS", v_abertas)
        c2.metric("⏱️ TIME-TO-HIRE MÉDIO", f"{avg_tth} dias")
        
        cands_ativos = len(df_c[~df_c['status_geral'].isin(['Finalizada', 'Perda'])]) if not df_c.empty else 0
        c3.metric("👥 CANDIDATOS ATIVOS", cands_ativos)
