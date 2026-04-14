import streamlit as st
import pandas as pd
from utils.coingecko import get_top_monedas, get_historico, buscar_moneda
from utils.alerts    import alerta_precio, mostrar_banner, mostrar_lista_alertas
from utils.charts    import chart_portafolio_donut, chart_pnl_barras


def _render_tab_agregar(df_mercado: pd.DataFrame) -> None:
    """
    Renderiza el formulario para agregar una nueva posición.
    Separada en función para poder llamarla tanto cuando
    el portafolio está vacío como desde el tab normal.
    """
    st.markdown("#### Agregar nueva posición")

    # Búsqueda de moneda
    busqueda = st.text_input(
        "Buscar moneda",
        placeholder="Escribí el nombre o ticker (ej: bitcoin, BTC)",
        key="busqueda_moneda"
    )

    # Resultados de búsqueda o top monedas
    if busqueda and len(busqueda) >= 2:
        with st.spinner("Buscando..."):
            resultados = buscar_moneda(busqueda)

        if resultados:
            opciones_busqueda = {
                r["id"]: f"{r['symbol']} — {r['name']}"
                for r in resultados
            }
        else:
            st.warning("No se encontraron monedas con ese nombre.")
            opciones_busqueda = {}
    else:
        # Sin búsqueda: mostrar top 50
        if not df_mercado.empty:
            opciones_busqueda = {
                row["id"]: f"{row['symbol']} — {row['name']}"
                for _, row in df_mercado.head(50).iterrows()
            }
        else:
            opciones_busqueda = {}

    if not opciones_busqueda:
        st.stop()

    with st.form("agregar_posicion", clear_on_submit=True):
        coin_sel = st.selectbox(
            "Moneda",
            list(opciones_busqueda.keys()),
            format_func=lambda x: opciones_busqueda.get(x, x)
        )

        col1, col2 = st.columns(2)
        cantidad = col1.number_input(
            "Cantidad",
            min_value=0.000001,
            value=1.0,
            step=0.01,
            format="%.6f"
        )
        precio_compra = col2.number_input(
            "Precio de compra (USD)",
            min_value=0.000001,
            value=1.0,
            step=0.01,
            format="%.6f"
        )

        costo_estimado = cantidad * precio_compra
        st.caption(f"Costo total estimado: ${costo_estimado:,.2f} USD")

        submitted = st.form_submit_button(
            "Agregar al portafolio",
            use_container_width=True,
            type="primary"
        )

    if submitted and coin_sel:
        simbolo = opciones_busqueda[coin_sel].split(" — ")[0]
        _agregar_posicion(coin_sel, simbolo, cantidad, precio_compra)
        st.toast(
            f"{simbolo} agregado al portafolio",
            icon="✅"
        )
        st.rerun()


# ── Helpers ───────────────────────────────────────────────────

def _calcular_portafolio(df_mercado: pd.DataFrame) -> pd.DataFrame:
    """
    Cruza las posiciones del session_state con los precios
    actuales del mercado y calcula P&L por posición.

    Devuelve DataFrame con una fila por posición y columnas:
    coin_id, simbolo, nombre, cantidad, precio_compra,
    precio_actual, costo_total, valor_actual,
    ganancia, ganancia_pct
    """
    portafolio = st.session_state.portafolio

    if not portafolio:
        return pd.DataFrame()

    # Crear lookup de precios actuales por coin_id
    precios = {}
    nombres = {}
    if not df_mercado.empty:
        for _, row in df_mercado.iterrows():
            precios[row["id"]] = row["current_price"]
            nombres[row["id"]] = row["name"]

    filas = []
    for coin_id, datos in portafolio.items():
        precio_actual = precios.get(coin_id, datos["precio_compra"])
        nombre        = nombres.get(coin_id, coin_id.capitalize())
        costo_total   = datos["cantidad"] * datos["precio_compra"]
        valor_actual  = datos["cantidad"] * precio_actual
        ganancia      = valor_actual - costo_total
        ganancia_pct  = (ganancia / costo_total * 100) if costo_total > 0 else 0

        filas.append({
            "coin_id":       coin_id,
            "simbolo":       datos["simbolo"],
            "nombre":        nombre,
            "cantidad":      datos["cantidad"],
            "precio_compra": datos["precio_compra"],
            "precio_actual": round(precio_actual, 6),
            "costo_total":   round(costo_total, 2),
            "valor_actual":  round(valor_actual, 2),
            "ganancia":      round(ganancia, 2),
            "ganancia_pct":  round(ganancia_pct, 2),
        })

    return pd.DataFrame(filas)


def _agregar_posicion(coin_id: str, simbolo: str,
                      cantidad: float, precio_compra: float) -> None:
    """Agrega o actualiza una posición en el portafolio."""
    st.session_state.portafolio[coin_id] = {
        "simbolo":       simbolo.upper(),
        "cantidad":      cantidad,
        "precio_compra": precio_compra,
    }


def _eliminar_posicion(coin_id: str) -> None:
    """Elimina una posición del portafolio."""
    if coin_id in st.session_state.portafolio:
        del st.session_state.portafolio[coin_id]


# ── Encabezado ────────────────────────────────────────────────

st.title("💼 Mi portafolio")
st.caption("Seguimiento de posiciones · P&L en tiempo real · Alertas")

# ── Cargar datos ──────────────────────────────────────────────

with st.spinner("Actualizando precios..."):
    df_mercado = get_top_monedas(limite=100)

df_port = _calcular_portafolio(df_mercado)

# ── Portafolio vacío ──────────────────────────────────────────

if df_port.empty:
    st.info(
        "Tu portafolio está vacío. "
        "Agregá tu primera posición en la pestaña **Agregar**."
    )
    # Mostrar igual la pestaña de agregar
    _, tab_agregar, _ = st.tabs(
        ["📋 Posiciones", "➕ Agregar", "🔔 Alertas"]
    )
    with tab_agregar:
        _render_tab_agregar(df_mercado)
    st.stop()

# ── Fila 1: KPIs ─────────────────────────────────────────────

total_invertido  = df_port["costo_total"].sum()
total_actual     = df_port["valor_actual"].sum()
ganancia_total   = total_actual - total_invertido
ganancia_total_pct = (
    (ganancia_total / total_invertido * 100)
    if total_invertido > 0 else 0
)

k1, k2, k3, k4 = st.columns(4)

k1.metric("Total invertido",   f"${total_invertido:,.2f}")
k2.metric("Valor actual",      f"${total_actual:,.2f}")

color_pnl = "#34C759" if ganancia_total >= 0 else "#FF3B30"
signo     = "+" if ganancia_total >= 0 else ""
k3.metric(
    "P&L total",
    f"${ganancia_total:+,.2f}",
    f"{signo}{ganancia_total_pct:.2f}%"
)

# Mejor posición
mejor = df_port.loc[df_port["ganancia_pct"].idxmax()]
k4.metric(
    "Mejor posición",
    mejor["simbolo"],
    f"{mejor['ganancia_pct']:+.1f}%"
)

st.divider()

# ── Fila 2: Donut + Barras P&L ───────────────────────────────

col_donut, col_barras = st.columns([1, 2])

with col_donut:
    st.plotly_chart(
        chart_portafolio_donut(df_port),
        use_container_width=True
    )

with col_barras:
    st.plotly_chart(
        chart_pnl_barras(df_port),
        use_container_width=True
    )

st.divider()

# ── Tabs ──────────────────────────────────────────────────────

tab_pos, tab_agregar, tab_alertas = st.tabs([
    "📋 Posiciones",
    "➕ Agregar",
    "🔔 Alertas"
])

# ── Tab 1: Posiciones ─────────────────────────────────────────

with tab_pos:
    st.markdown("#### Detalle de posiciones")

    # Tabla de posiciones con formato
    df_tabla = df_port[[
        "simbolo", "nombre", "cantidad",
        "precio_compra", "precio_actual",
        "costo_total", "valor_actual",
        "ganancia", "ganancia_pct"
    ]].copy()

    df_tabla = df_tabla.rename(columns={
        "simbolo":       "Ticker",
        "nombre":        "Nombre",
        "cantidad":      "Cantidad",
        "precio_compra": "Compra",
        "precio_actual": "Actual",
        "costo_total":   "Invertido",
        "valor_actual":  "Valor",
        "ganancia":      "P&L (USD)",
        "ganancia_pct":  "P&L (%)",
    })

    st.dataframe(
        df_tabla,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Compra":    st.column_config.NumberColumn(format="$%.4f"),
            "Actual":    st.column_config.NumberColumn(format="$%.4f"),
            "Invertido": st.column_config.NumberColumn(format="$%.2f"),
            "Valor":     st.column_config.NumberColumn(format="$%.2f"),
            "P&L (USD)": st.column_config.NumberColumn(format="$%.2f"),
            "P&L (%)":   st.column_config.NumberColumn(format="%.2f%%"),
        }
    )

    # Eliminar posición
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Eliminar posición")

    col_sel, col_btn = st.columns([3, 1])
    opciones = ["— Seleccioná —"] + df_port["coin_id"].tolist()
    labels   = {
        row["coin_id"]: f"{row['simbolo']} — {row['nombre']}"
        for _, row in df_port.iterrows()
    }
    labels["— Seleccioná —"] = "— Seleccioná —"

    coin_borrar = col_sel.selectbox(
        "Posición a eliminar",
        opciones,
        format_func=lambda x: labels.get(x, x),
        label_visibility="collapsed"
    )

    if col_btn.button(
        "Eliminar",
        type="primary",
        use_container_width=True,
        disabled=coin_borrar == "— Seleccioná —"
    ):
        nombre_borrado = labels.get(coin_borrar, coin_borrar)
        _eliminar_posicion(coin_borrar)
        st.toast(f"{nombre_borrado} eliminado del portafolio", icon="🗑️")
        st.rerun()

# ── Tab 2: Agregar posición ───────────────────────────────────

with tab_agregar:
    _render_tab_agregar(df_mercado)

# ── Tab 3: Alertas del portafolio ─────────────────────────────

with tab_alertas:
    st.markdown("#### Alertas activas en tu portafolio")

    if df_mercado.empty:
        st.warning("No se pudieron cargar los precios actuales.")
    else:
        # Buscar variaciones de las monedas del portafolio
        alertas_port = []
        for _, row in df_port.iterrows():
            coin_id = row["coin_id"]
            simbolo = row["simbolo"]

            # Buscar variación 24h en df_mercado
            match = df_mercado[df_mercado["id"] == coin_id]
            if not match.empty:
                var_24h = match.iloc[0].get("price_change_pct_24h", 0) or 0
                alerta  = alerta_precio(simbolo, var_24h)
                if alerta:
                    alertas_port.append(alerta)

        mostrar_lista_alertas(alertas_port)

        # Resumen de variaciones de todas las posiciones
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Variaciones de tus posiciones (24h)")

        for _, row in df_port.iterrows():
            coin_id = row["coin_id"]
            simbolo = row["simbolo"]
            match   = df_mercado[df_mercado["id"] == coin_id]

            if not match.empty:
                var_24h = match.iloc[0].get("price_change_pct_24h", 0) or 0
                signo   = "+" if var_24h >= 0 else ""
                color   = "#34C759" if var_24h >= 0 else "#FF3B30"

                st.markdown(
                    f"""
                    <div style='
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                        padding:8px 0;
                        border-bottom:1px solid #21262D;
                    '>
                        <span style='font-weight:600;'>{simbolo}</span>
                        <span style='color:{color};font-weight:600;'>
                            {signo}{var_24h:.2f}%
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

# ── Footer ────────────────────────────────────────────────────

st.divider()
st.caption(
    "Precios actualizados cada 5 minutos · "
    "Los datos del portafolio se guardan en la sesión actual."
)


