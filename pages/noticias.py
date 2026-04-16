import re
import streamlit as st
import pandas as pd
from collections import Counter
from utils.noticias import (
    get_feed_completo,
    filtrar_por_moneda,
    filtrar_por_fuente
)
from utils.coingecko import get_trending


# ── Helper de limpieza ────────────────────────────────────────

def _limpiar_texto(texto: str) -> str:
    if not texto:
        return ""
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = texto.replace("&amp;",   "&")
    texto = texto.replace("&lt;",    "<")
    texto = texto.replace("&gt;",    ">")
    texto = texto.replace("&quot;",  '"')
    texto = texto.replace("&#39;",   "'")
    texto = texto.replace("&nbsp;",  " ")
    texto = texto.replace("&#8216;", "'")
    texto = texto.replace("&#8217;", "'")
    texto = texto.replace("&#8220;", '"')
    texto = texto.replace("&#8221;", '"')
    texto = texto.replace("&#8230;", "...")
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


# ── Función de renderizado de cards ──────────────────────────

def _render_noticia_card(noticia: dict) -> None:
    """
    Renderiza una noticia usando componentes nativos de Streamlit.
    Evita completamente el problema de HTML en el contenido.
    """
    titulo      = _limpiar_texto(noticia.get("titulo", "Sin título"))
    url         = noticia.get("url", "")
    fuente      = noticia.get("fuente", "—")
    hace        = noticia.get("hace", "—")
    descripcion = _limpiar_texto(noticia.get("descripcion", ""))
    monedas     = noticia.get("monedas", [])

    with st.container(border=True):
        # Titular con link
        if url:
            st.markdown(f"**[{titulo}]({url})**")
        else:
            st.markdown(f"**{titulo}**")

        # Fuente y tiempo
        st.caption(f"📡 {fuente}  ·  🕐 {hace}")

        # Descripción
        if descripcion:
            desc_corta = descripcion[:180]
            puntos     = "..." if len(descripcion) > 180 else ""
            st.caption(f"{desc_corta}{puntos}")

        # Badges de monedas como texto simple
        if monedas:
            badges = "  ".join([f"`{m}`" for m in monedas[:4]])
            st.markdown(badges)


# ── Encabezado ────────────────────────────────────────────────

st.title("📰 Noticias del mercado")
st.caption("Feed en tiempo real · CoinDesk · Cointelegraph · Decrypt · Bitcoin Magazine")

# ── Cargar datos ──────────────────────────────────────────────

with st.spinner("Cargando noticias..."):
    df_feed  = get_feed_completo(max_noticias=100)
    trending = get_trending()

if df_feed.empty:
    st.error("No se pudieron cargar las noticias. Verificá tu conexión.")
    st.stop()

# ── Barra de filtros ──────────────────────────────────────────

col_buscar, col_moneda, col_fuente, col_orden = st.columns([3, 2, 2, 2])

busqueda = col_buscar.text_input(
    "Buscar",
    placeholder="🔍 Buscar en titulares...",
    label_visibility="collapsed"
)

todas_monedas = ["Todas"] + sorted({
    m for monedas in df_feed["monedas"]
    for m in monedas
})
moneda_sel = col_moneda.selectbox(
    "Moneda",
    todas_monedas,
    label_visibility="collapsed"
)

fuentes_disponibles = sorted(df_feed["fuente"].unique().tolist())
fuentes_sel = col_fuente.multiselect(
    "Fuente",
    fuentes_disponibles,
    default=fuentes_disponibles,
    label_visibility="collapsed"
)

orden_sel = col_orden.selectbox(
    "Orden",
    ["Más recientes", "Más antiguas"],
    label_visibility="collapsed"
)

# ── Aplicar filtros ───────────────────────────────────────────

df_filtrado = df_feed.copy()

if busqueda:
    mask = (
        df_filtrado["titulo"].str.contains(busqueda, case=False, na=False) |
        df_filtrado["descripcion"].str.contains(busqueda, case=False, na=False)
    )
    df_filtrado = df_filtrado[mask]

if moneda_sel != "Todas":
    df_filtrado = filtrar_por_moneda(df_filtrado, moneda_sel)

if fuentes_sel:
    df_filtrado = filtrar_por_fuente(df_filtrado, fuentes_sel)

if orden_sel == "Más antiguas":
    df_filtrado = df_filtrado.sort_values("fecha", ascending=True)

# ── KPIs del feed ─────────────────────────────────────────────

st.divider()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Noticias encontradas", len(df_filtrado))
k2.metric("Fuentes activas",      len(df_filtrado["fuente"].unique()))

noticias_btc = sum(
    1 for monedas in df_filtrado["monedas"] if "BTC" in monedas
)
k3.metric("Mencionan BTC", noticias_btc)

if not df_filtrado.empty:
    k4.metric("Última noticia", df_filtrado.iloc[0]["hace"])

st.divider()

# ── Layout principal ──────────────────────────────────────────

col_feed, col_lateral = st.columns([3, 1])

# ── Feed de noticias ──────────────────────────────────────────

with col_feed:
    if df_filtrado.empty:
        st.info("No se encontraron noticias con los filtros seleccionados.")
    else:
        NOTICIAS_POR_PAGINA = 10
        total_paginas = max(1, -(-len(df_filtrado) // NOTICIAS_POR_PAGINA))

        if "pagina_noticias" not in st.session_state:
            st.session_state.pagina_noticias = 1

        clave_filtros = f"{busqueda}{moneda_sel}{str(fuentes_sel)}{orden_sel}"
        if st.session_state.get("filtros_anteriores") != clave_filtros:
            st.session_state.pagina_noticias    = 1
            st.session_state.filtros_anteriores = clave_filtros

        pagina_actual = st.session_state.pagina_noticias
        inicio        = (pagina_actual - 1) * NOTICIAS_POR_PAGINA
        fin           = inicio + NOTICIAS_POR_PAGINA
        df_pagina     = df_filtrado.iloc[inicio:fin]

        for _, noticia in df_pagina.iterrows():
            _render_noticia_card(noticia)

        st.markdown("<br>", unsafe_allow_html=True)
        p1, p2, p3 = st.columns([1, 2, 1])

        if p1.button("← Anterior",
                     disabled=pagina_actual <= 1,
                     use_container_width=True):
            st.session_state.pagina_noticias -= 1
            st.rerun()

        p2.markdown(
            f"<p style='text-align:center;color:#8B949E;margin:0.5rem 0;'>"
            f"Página {pagina_actual} de {total_paginas}</p>",
            unsafe_allow_html=True
        )

        if p3.button("Siguiente →",
                     disabled=pagina_actual >= total_paginas,
                     use_container_width=True):
            st.session_state.pagina_noticias += 1
            st.rerun()

# ── Panel lateral ─────────────────────────────────────────────

with col_lateral:

    if trending:
        st.markdown("#### 🔥 Trending")
        for coin in trending[:7]:
            rank   = coin.get("rank", "—")
            symbol = coin.get("symbol", "")
            name   = coin.get("name", "")
            st.caption(f"#{rank}  **{symbol}** {name}")
        st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("#### 📡 Fuentes")
    conteo_fuentes = df_feed["fuente"].value_counts()
    for fuente, count in conteo_fuentes.items():
        st.caption(f"{fuente} — {count} noticias")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("#### 🏷️ Más mencionadas")
    todas_menciones = [
        m for monedas in df_feed["monedas"]
        for m in monedas
    ]
    if todas_menciones:
        conteo_monedas = Counter(todas_menciones).most_common(8)
        for simbolo, count in conteo_monedas:
            st.caption(f"**{simbolo}** — {count} noticias")
    else:
        st.caption("Sin datos de menciones")

# ── Footer ────────────────────────────────────────────────────

st.divider()
st.caption(
    "Fuentes: CoinDesk · Cointelegraph · Decrypt · Bitcoin Magazine · "
    "Actualización cada 15 minutos."
)