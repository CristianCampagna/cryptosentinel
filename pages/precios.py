import streamlit as st
import pandas as pd
from utils.coingecko import (
    get_top_monedas,
    get_historico,
    get_detalle_moneda,
    get_datos_globales,
)
from utils.alerts  import alerta_precio, mostrar_badge, escanear_mercado
from utils.charts  import (
    chart_precio_historico,
    chart_comparacion,
    chart_dominancia,
)


# ── Encabezado ────────────────────────────────────────────────

st.title("💰 Precios del mercado")
st.caption("Top 50 monedas · Análisis de detalle · Comparación de rendimiento")

# ── Cargar datos base ─────────────────────────────────────────

with st.spinner("Cargando datos del mercado..."):
    globales   = get_datos_globales()
    df_mercado = get_top_monedas(limite=50)

moneda_ref = st.session_state.get("moneda_ref", "usd")

# ── Fila 1: KPIs globales ────────────────────────────────────

if globales:
    k1, k2, k3, k4 = st.columns(4)

    cap     = globales.get("market_cap_total", 0)
    cap_str = f"${cap/1e12:.2f}T" if cap > 1e12 else f"${cap/1e9:.1f}B"
    var_24h = globales.get("variacion_24h", 0)
    signo   = "+" if var_24h >= 0 else ""

    k1.metric("Market Cap total",  cap_str, f"{signo}{var_24h:.1f}%")

    vol     = globales.get("volumen_24h", 0)
    vol_str = f"${vol/1e12:.2f}T" if vol > 1e12 else f"${vol/1e9:.1f}B"
    k2.metric("Volumen 24h", vol_str)

    dom_btc = globales.get("dominancia_btc", 0)
    dom_eth = globales.get("dominancia_eth", 0)
    k3.metric("Dominancia BTC", f"{dom_btc:.1f}%")
    k4.metric("Dominancia ETH", f"{dom_eth:.1f}%")

st.divider()

# ── Fila 2: Donut dominancia + Tabs ──────────────────────────

col_donut, col_tabs = st.columns([1, 2])

with col_donut:
    if globales:
        st.plotly_chart(
            chart_dominancia(
                globales.get("dominancia_btc", 0),
                globales.get("dominancia_eth", 0)
            ),
            use_container_width=True
        )
        st.caption(
            f"Resto del mercado: "
            f"{100 - dom_btc - dom_eth:.1f}%"
        )

with col_tabs:
    tab_mercado, tab_detalle, tab_comparar = st.tabs([
        "📊 Mercado",
        "🔍 Detalle",
        "⚖️ Comparar"
    ])

    # ── Tab 1: Tabla de mercado ───────────────────────────────
    with tab_mercado:
        if df_mercado.empty:
            st.warning("No se pudieron cargar los datos del mercado.")
        else:
            # Escáner de alertas activas
            alertas = escanear_mercado(df_mercado)
            if alertas:
                with st.expander(
                    f"⚠️ {len(alertas)} alertas activas en el mercado",
                    expanded=False
                ):
                    for a in alertas[:5]:
                        st.markdown(
                            f"<span style='color:{a['color']}'>"
                            f"{a['icono']} {a['titulo']}"
                            f"</span>",
                            unsafe_allow_html=True
                        )

            # Preparar tabla con badges de variación
            df_tabla = df_mercado[[
                "market_cap_rank", "name", "symbol",
                "current_price", "price_change_pct_24h",
                "price_change_pct_7d", "market_cap", "total_volume"
            ]].copy()

            df_tabla = df_tabla.rename(columns={
                "market_cap_rank":     "#",
                "name":                "Nombre",
                "symbol":              "Ticker",
                "current_price":       "Precio",
                "price_change_pct_24h":"24h %",
                "price_change_pct_7d": "7d %",
                "market_cap":          "Market Cap",
                "total_volume":        "Volumen 24h"
            })

            st.dataframe(
                df_tabla,
                use_container_width=True,
                hide_index=True,
                height=380,
                column_config={
                    "#": st.column_config.NumberColumn(
                        width="small", format="%d"
                    ),
                    "Precio": st.column_config.NumberColumn(
                        format="$%.4f"
                    ),
                    "24h %": st.column_config.NumberColumn(
                        format="%.2f%%"
                    ),
                    "7d %": st.column_config.NumberColumn(
                        format="%.2f%%"
                    ),
                    "Market Cap": st.column_config.NumberColumn(
                        format="$%d"
                    ),
                    "Volumen 24h": st.column_config.NumberColumn(
                        format="$%d"
                    ),
                }
            )

    # ── Tab 2: Detalle de una moneda ──────────────────────────
    with tab_detalle:
        if df_mercado.empty:
            st.warning("No hay datos disponibles.")
        else:
            # Selector de moneda
            opciones = df_mercado["name"].tolist()
            moneda_nombre = st.selectbox(
                "Seleccioná una moneda",
                opciones,
                label_visibility="collapsed"
            )

            # Obtener el id de CoinGecko para la moneda
            coin_id = df_mercado[
                df_mercado["name"] == moneda_nombre
            ]["id"].iloc[0]

            simbolo = df_mercado[
                df_mercado["name"] == moneda_nombre
            ]["symbol"].iloc[0]

            # Selector de período
            periodos = {"7d": 7, "30d": 30, "90d": 90, "1a": 365}
            periodo_label = st.radio(
                "Período",
                list(periodos.keys()),
                horizontal=True,
                label_visibility="collapsed"
            )
            dias = periodos[periodo_label]

            with st.spinner(f"Cargando datos de {moneda_nombre}..."):
                df_hist = get_historico(coin_id, dias=dias)
                detalle = get_detalle_moneda(coin_id)

            # KPIs de la moneda
            if detalle:
                d1, d2, d3 = st.columns(3)

                precio = detalle.get("precio_usd", 0)
                var_24 = detalle.get("variacion_24h", 0) or 0
                signo  = "+" if var_24 >= 0 else ""
                d1.metric(
                    "Precio actual",
                    f"${precio:,.4f}" if precio < 1 else f"${precio:,.2f}",
                    f"{signo}{var_24:.2f}%"
                )

                ath = detalle.get("ath")
                if ath:
                    d2.metric("ATH", f"${ath:,.2f}")

                atl = detalle.get("atl")
                if atl:
                    d3.metric("ATL", f"${atl:,.4f}"
                              if atl < 1 else f"${atl:,.2f}")

                # Supply info
                supply_c = detalle.get("supply_circulante", 0)
                supply_t = detalle.get("supply_total")
                if supply_c:
                    pct_str = ""
                    if supply_t and supply_t > 0:
                        pct = (supply_c / supply_t) * 100
                        pct_str = f" ({pct:.1f}% del total)"
                    st.caption(
                        f"Supply circulante: "
                        f"{supply_c:,.0f} {simbolo.upper()}{pct_str}"
                    )

            # Gráfico histórico
            if not df_hist.empty:
                st.plotly_chart(
                    chart_precio_historico(df_hist, simbolo.upper()),
                    use_container_width=True
                )
            else:
                st.warning("No se pudo cargar el histórico de precios.")

    # ── Tab 3: Comparar monedas ───────────────────────────────
    with tab_comparar:
        if df_mercado.empty:
            st.warning("No hay datos disponibles.")
        else:
            # Multiselect de monedas a comparar
            nombres_disponibles = df_mercado["name"].tolist()
            seleccionadas = st.multiselect(
                "Seleccioná monedas para comparar",
                nombres_disponibles,
                default=nombres_disponibles[:3],
                max_selections=6,
                label_visibility="collapsed"
            )

            # Período de comparación
            per_comp = st.radio(
                "Período de comparación",
                ["7d", "30d", "90d"],
                horizontal=True,
                index=1,
                label_visibility="collapsed"
            )
            dias_comp = {"7d": 7, "30d": 30, "90d": 90}[per_comp]

            if len(seleccionadas) < 2:
                st.info("Seleccioná al menos 2 monedas para comparar.")
            else:
                # Cargar histórico de cada moneda seleccionada
                df_comparacion = {}
                with st.spinner("Cargando datos para comparación..."):
                    for nombre in seleccionadas:
                        cid = df_mercado[
                            df_mercado["name"] == nombre
                        ]["id"].iloc[0]
                        sym = df_mercado[
                            df_mercado["name"] == nombre
                        ]["symbol"].iloc[0].upper()
                        df_h = get_historico(cid, dias=dias_comp)
                        if not df_h.empty:
                            df_comparacion[sym] = df_h

                if df_comparacion:
                    st.plotly_chart(
                        chart_comparacion(df_comparacion),
                        use_container_width=True
                    )

                    # Tabla de rendimiento del período
                    st.markdown("**Rendimiento del período**")
                    rows = []
                    for sym, df_h in df_comparacion.items():
                        inicio  = df_h["precio"].iloc[0]
                        fin     = df_h["precio"].iloc[-1]
                        rend    = ((fin - inicio) / inicio) * 100
                        rows.append({
                            "Moneda":      sym,
                            "Inicio":      f"${inicio:,.2f}",
                            "Fin":         f"${fin:,.2f}",
                            "Rendimiento": round(rend, 2)
                        })

                    df_rend = pd.DataFrame(rows).sort_values(
                        "Rendimiento", ascending=False
                    )
                    st.dataframe(
                        df_rend,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Rendimiento": st.column_config.NumberColumn(
                                format="%.2f%%"
                            )
                        }
                    )
                else:
                    st.warning(
                        "No se pudieron cargar los datos "
                        "para la comparación."
                    )

# ── Footer ────────────────────────────────────────────────────

st.divider()
st.caption(
    "Fuente: CoinGecko API · "
    "Precios con retraso de hasta 5 minutos."
)