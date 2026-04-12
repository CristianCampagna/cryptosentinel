import streamlit as st
from utils.feargreed import (
    get_fear_greed_actual,
    get_fear_greed_historico,
    get_resumen_sentimiento
)
from utils.coingecko import get_datos_globales, get_top_monedas
from utils.alerts   import alerta_fear_greed, mostrar_banner
from utils.charts   import chart_gauge_fear_greed, chart_fear_greed, chart_heatmap_mercado

# ── Encabezado ────────────────────────────────────────────────

st.title("🌡️ Sentimiento del mercado")
st.caption("Fear & Greed Index · Datos globales · Heatmap de variaciones")

# ── Cargar datos ──────────────────────────────────────────────
# Todos los datos se cargan al principio para que los spinners
# aparezcan juntos y no de forma escalonada.

with st.spinner("Cargando datos del mercado..."):
    fg_actual  = get_fear_greed_actual()
    fg_histo   = get_fear_greed_historico(dias=30)
    fg_resumen = get_resumen_sentimiento(dias=30)
    globales   = get_datos_globales()

# ── Banner de alerta (condicional) ───────────────────────────
# Solo aparece si el mercado está en zona extrema.
# En zona normal no muestra nada — no queremos ruido visual.

if fg_actual:
    alerta = alerta_fear_greed(fg_actual.get("valor", 50))
    mostrar_banner(alerta)

# ── Fila 1: KPIs globales ────────────────────────────────────

st.subheader("Estado global del mercado")

if globales:
    k1, k2, k3, k4 = st.columns(4)

    # Market cap total
    cap     = globales.get("market_cap_total", 0)
    cap_str = f"${cap/1e12:.2f}T" if cap > 1e12 else f"${cap/1e9:.1f}B"
    var_24h = globales.get("variacion_24h", 0)
    signo   = "+" if var_24h >= 0 else ""
    k1.metric(
        "Market Cap total",
        cap_str,
        f"{signo}{var_24h:.1f}% 24h"
    )

    # Volumen 24h
    vol     = globales.get("volumen_24h", 0)
    vol_str = f"${vol/1e12:.2f}T" if vol > 1e12 else f"${vol/1e9:.1f}B"
    k2.metric("Volumen 24h", vol_str)

    # Dominancia BTC
    dom_btc = globales.get("dominancia_btc", 0)
    dom_eth = globales.get("dominancia_eth", 0)
    k3.metric("Dominancia BTC", f"{dom_btc:.1f}%")

    # Monedas activas
    num_monedas = globales.get("num_monedas", 0)
    k4.metric("Monedas activas", f"{num_monedas:,}")
else:
    st.warning("No se pudieron cargar los datos globales del mercado.")

st.divider()

# ── Fila 2: Gauge + Resumen 30 días ──────────────────────────

st.subheader("Fear & Greed Index")

col_gauge, col_stats = st.columns([1, 1])

with col_gauge:
    if fg_actual:
        valor = fg_actual.get("valor", 50)
        color = fg_actual.get("color", "#FFCC00")
        emoji = fg_actual.get("emoji", "😐")
        label = fg_actual.get("label", "Neutral")
        fecha = fg_actual.get("fecha")

        # Gauge visual
        st.plotly_chart(
            chart_gauge_fear_greed(valor, color),
            use_container_width=True
        )

        # Label debajo del gauge
        st.markdown(
            f"""
            <div style='text-align:center; margin-top:-1rem;'>
                <span style='font-size:2rem;'>{emoji}</span>
                <p style='
                    color:{color};
                    font-size:1.2rem;
                    font-weight:600;
                    margin:0.2rem 0 0;
                '>{label}</span>
                <p style='color:#8B949E; font-size:0.8rem; margin:0.2rem 0 0;'>
                    Actualizado: {fecha.strftime('%d/%m/%Y') if fecha else '—'}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.error("No se pudo cargar el Fear & Greed Index.")

with col_stats:
    if fg_resumen:
        st.markdown("#### Resumen — últimos 30 días")

        # Métricas principales
        s1, s2, s3 = st.columns(3)
        s1.metric("Promedio", fg_resumen.get("promedio", "—"))
        s2.metric("Máximo",   fg_resumen.get("maximo",   "—"))
        s3.metric("Mínimo",   fg_resumen.get("minimo",   "—"))

        st.markdown("<br>", unsafe_allow_html=True)

        # Días en cada zona
        dias_fear  = fg_resumen.get("dias_fear",  0)
        dias_greed = fg_resumen.get("dias_greed", 0)
        total_dias = dias_fear + dias_greed

        st.markdown("**Distribución del período**")

        # Barra de progreso visual fear vs greed
        pct_fear = int((dias_fear / total_dias * 100)) if total_dias else 0
        st.markdown(
            f"""
            <div style='margin:0.5rem 0;'>
                <div style='
                    display:flex;
                    border-radius:6px;
                    overflow:hidden;
                    height:24px;
                    font-size:12px;
                    font-weight:600;
                '>
                    <div style='
                        width:{pct_fear}%;
                        background:#FF3B30;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        color:white;
                        min-width:2rem;
                    '>😰 {dias_fear}d</div>
                    <div style='
                        width:{100-pct_fear}%;
                        background:#34C759;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        color:white;
                        min-width:2rem;
                    '>😏 {dias_greed}d</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Tendencia
        tendencia     = fg_resumen.get("tendencia", "estable")
        clasificacion = fg_resumen.get("clasificacion_promedio", "—")

        iconos_tendencia = {
            "mejorando":  ("📈", "#34C759"),
            "empeorando": ("📉", "#FF3B30"),
            "estable":    ("➡️", "#8B949E"),
        }
        icono_t, color_t = iconos_tendencia.get(
            tendencia, ("➡️", "#8B949E")
        )

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.markdown(
            f"""
            <div style='
                background:#161B22;
                border-radius:8px;
                padding:10px 12px;
            '>
                <div style='color:#8B949E;font-size:11px;'>
                    Tendencia del período
                </div>
                <div style='
                    font-size:15px;
                    font-weight:600;
                    color:{color_t};
                '>
                    {icono_t} {tendencia.capitalize()}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        c2.markdown(
            f"""
            <div style='
                background:#161B22;
                border-radius:8px;
                padding:10px 12px;
            '>
                <div style='color:#8B949E;font-size:11px;'>
                    Clasificación promedio
                </div>
                <div style='font-size:15px;font-weight:600;'>
                    {clasificacion}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.warning("No se pudo cargar el resumen estadístico.")

st.divider()

# ── Fila 3: Histórico Fear & Greed ───────────────────────────

st.subheader("Histórico Fear & Greed — 30 días")

# Selector de período encima del gráfico
col_per, _ = st.columns([1, 4])
dias_opciones = {"7 días": 7, "15 días": 15, "30 días": 30}
periodo_label = col_per.selectbox(
    "Período",
    list(dias_opciones.keys()),
    index=2,
    label_visibility="collapsed"
)
dias_sel = dias_opciones[periodo_label]

# Si el período cambió necesitamos recargar
if dias_sel != 30:
    fg_histo = get_fear_greed_historico(dias=dias_sel)

if not fg_histo.empty:
    st.plotly_chart(
        chart_fear_greed(fg_histo),
        use_container_width=True
    )
else:
    st.warning("No se pudo cargar el histórico.")

st.divider()

# ── Fila 4: Heatmap del mercado ───────────────────────────────

st.subheader("Heatmap del mercado — Top 50")
st.caption("Tamaño = market cap · Color = variación de precio")

# Selector de período del heatmap
col_h1, col_h2, _ = st.columns([1, 1, 4])
periodo_heat = col_h1.radio(
    "Variación",
    ["24h", "7d"],
    horizontal=True,
    label_visibility="collapsed"
)

with st.spinner("Cargando datos del mercado..."):
    df_mercado = get_top_monedas(limite=50)

if not df_mercado.empty:
    columna = ("price_change_pct_24h" if periodo_heat == "24h"
               else "price_change_pct_7d")
    st.plotly_chart(
        chart_heatmap_mercado(df_mercado, columna=columna),
        use_container_width=True
    )
else:
    st.warning("No se pudieron cargar los datos del mercado.")

# ── Footer ────────────────────────────────────────────────────

st.divider()
st.caption(
    "Fuentes: Alternative.me Fear & Greed Index · CoinGecko API · "
    "Datos con retraso de hasta 15 minutos."
)