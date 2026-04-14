import streamlit as st
from utils.alerts import UMBRALES_DEFAULT


# ── Encabezado ────────────────────────────────────────────────

st.title("⚙️ Configuración")
st.caption("Preferencias personales · Umbrales de alertas · Gestión del sistema")

# ── Tabs de configuración ─────────────────────────────────────

tab_preferencias, tab_alertas, tab_sistema = st.tabs([
    "🎯 Preferencias",
    "🔔 Alertas",
    "🛠️ Sistema"
])


# ── Tab 1: Preferencias ───────────────────────────────────────

with tab_preferencias:
    st.markdown("#### Moneda de referencia")
    st.caption("Afecta los precios mostrados en toda la app.")

    moneda_actual = st.session_state.get("moneda_ref", "usd")
    moneda_nueva  = st.radio(
        "Moneda",
        ["usd", "eur", "ars"],
        index=["usd", "eur", "ars"].index(moneda_actual),
        horizontal=True,
        format_func=lambda x: {
            "usd": "🇺🇸 USD — Dólar",
            "eur": "🇪🇺 EUR — Euro",
            "ars": "🇦🇷 ARS — Peso argentino"
        }[x],
        label_visibility="collapsed"
    )

    if moneda_nueva != moneda_actual:
        st.session_state.moneda_ref = moneda_nueva
        st.toast(f"Moneda cambiada a {moneda_nueva.upper()}", icon="💱")
        st.rerun()

    st.divider()

    # Período default para gráficos
    st.markdown("#### Período default para gráficos")
    st.caption("Se usa como valor inicial en las páginas de Precios y Sentimiento.")

    periodo_actual = st.session_state.get("periodo_default", 30)
    periodo_nuevo  = st.select_slider(
        "Período",
        options=[7, 14, 30, 60, 90, 180, 365],
        value=periodo_actual,
        format_func=lambda x: {
            7:   "7 días",
            14:  "14 días",
            30:  "30 días",
            60:  "60 días",
            90:  "90 días",
            180: "6 meses",
            365: "1 año"
        }[x],
        label_visibility="collapsed"
    )

    if periodo_nuevo != periodo_actual:
        st.session_state.periodo_default = periodo_nuevo
        st.toast(f"Período default: {periodo_nuevo} días", icon="📅")

    st.divider()

    # Monedas favoritas
    st.markdown("#### Monedas favoritas")
    st.caption(
        "Estas monedas aparecen preseleccionadas "
        "en los comparadores y filtros."
    )

    MONEDAS_DISPONIBLES = {
        "bitcoin":       "BTC — Bitcoin",
        "ethereum":      "ETH — Ethereum",
        "solana":        "SOL — Solana",
        "ripple":        "XRP — XRP",
        "binancecoin":   "BNB — BNB",
        "cardano":       "ADA — Cardano",
        "dogecoin":      "DOGE — Dogecoin",
        "avalanche-2":   "AVAX — Avalanche",
        "polkadot":      "DOT — Polkadot",
        "chainlink":     "LINK — Chainlink",
        "litecoin":      "LTC — Litecoin",
        "uniswap":       "UNI — Uniswap",
        "stellar":       "XLM — Stellar",
        "tron":          "TRX — TRON",
    }

    favoritas_actual = st.session_state.get("favoritas", [
        "bitcoin", "ethereum", "solana", "ripple", "binancecoin"
    ])

    favoritas_nuevas = st.multiselect(
        "Monedas favoritas",
        options=list(MONEDAS_DISPONIBLES.keys()),
        default=[f for f in favoritas_actual
                 if f in MONEDAS_DISPONIBLES],
        format_func=lambda x: MONEDAS_DISPONIBLES.get(x, x),
        label_visibility="collapsed"
    )

    if st.button("Guardar favoritas", use_container_width=True):
        if favoritas_nuevas:
            st.session_state.favoritas = favoritas_nuevas
            st.toast(
                f"{len(favoritas_nuevas)} monedas guardadas como favoritas",
                icon="⭐"
            )
        else:
            st.error("Seleccioná al menos una moneda.")


# ── Tab 2: Umbrales de alertas ────────────────────────────────

with tab_alertas:
    st.markdown("#### Umbrales de alertas de precio")
    st.caption(
        "Definí a partir de qué variación porcentual "
        "se activa cada nivel de alerta."
    )

    # Cargar umbrales actuales
    umbrales_actuales = st.session_state.get("umbrales") or UMBRALES_DEFAULT

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Alertas de caída 📉**")

        caida_fuerte = st.number_input(
            "Caída fuerte (crítico 🔴)",
            min_value=-50.0,
            max_value=-0.1,
            value=float(umbrales_actuales["precio_caida_fuerte"]),
            step=0.5,
            format="%.1f",
            help="Variación negativa que activa alerta crítica"
        )

        caida_leve = st.number_input(
            "Caída leve (peligro 🟠)",
            min_value=-50.0,
            max_value=-0.1,
            value=float(umbrales_actuales["precio_caida_leve"]),
            step=0.5,
            format="%.1f",
            help="Variación negativa que activa alerta de peligro"
        )

    with col2:
        st.markdown("**Alertas de suba 📈**")

        suba_fuerte = st.number_input(
            "Suba fuerte (euforia 🔵)",
            min_value=0.1,
            max_value=100.0,
            value=float(umbrales_actuales["precio_suba_fuerte"]),
            step=0.5,
            format="%.1f",
            help="Variación positiva que activa alerta de euforia"
        )

        suba_leve = st.number_input(
            "Suba leve (positivo 🟢)",
            min_value=0.1,
            max_value=100.0,
            value=float(umbrales_actuales["precio_suba_leve"]),
            step=0.5,
            format="%.1f",
            help="Variación positiva que activa alerta positiva"
        )

    st.divider()

    st.markdown("#### Umbrales Fear & Greed")
    st.caption(
        "Valores extremos del índice que activan "
        "el banner de alerta en la página de Sentimiento."
    )

    col3, col4 = st.columns(2)

    fg_miedo = col3.slider(
        "Miedo extremo — umbral máximo 😱",
        min_value=5,
        max_value=40,
        value=int(umbrales_actuales["fg_miedo_extremo"]),
        help="Por debajo de este valor → banner rojo"
    )

    fg_codicia = col4.slider(
        "Codicia extrema — umbral mínimo 🤑",
        min_value=60,
        max_value=95,
        value=int(umbrales_actuales["fg_codicia_extrema"]),
        help="Por encima de este valor → banner cyan"
    )

    st.divider()

    # Vista previa de los umbrales
    with st.expander("Vista previa de las alertas configuradas"):
        st.markdown(
            f"""
            | Variación | Nivel | Color |
            |---|---|---|
            | ≤ `{caida_fuerte:.1f}%` | 🔴 Crítico | Caída fuerte |
            | ≤ `{caida_leve:.1f}%`   | 🟠 Peligro | Caída leve |
            | `{caida_leve:.1f}%` a `{suba_leve:.1f}%` | ⚪ Normal | Sin alerta |
            | ≥ `{suba_leve:.1f}%`    | 🟢 Positivo | Suba leve |
            | ≥ `{suba_fuerte:.1f}%`  | 🔵 Euforia | Suba fuerte |

            **Fear & Greed:**
            - Miedo extremo: índice ≤ `{fg_miedo}`
            - Codicia extrema: índice ≥ `{fg_codicia}`
            """
        )

    col_guardar, col_reset = st.columns(2)

    if col_guardar.button(
        "Guardar umbrales",
        use_container_width=True,
        type="primary"
    ):
        # Validar que los umbrales tienen sentido
        if caida_fuerte >= caida_leve:
            st.error(
                "La caída fuerte debe ser menor que la caída leve. "
                f"({caida_fuerte} debe ser < {caida_leve})"
            )
        elif suba_leve >= suba_fuerte:
            st.error(
                "La suba leve debe ser menor que la suba fuerte. "
                f"({suba_leve} debe ser < {suba_fuerte})"
            )
        else:
            st.session_state.umbrales = {
                "fg_miedo_extremo":    fg_miedo,
                "fg_codicia_extrema":  fg_codicia,
                "precio_caida_fuerte": caida_fuerte,
                "precio_caida_leve":   caida_leve,
                "precio_suba_fuerte":  suba_fuerte,
                "precio_suba_leve":    suba_leve,
                "volumen_alto":        umbrales_actuales["volumen_alto"],
            }
            st.toast("Umbrales guardados correctamente", icon="✅")
            st.rerun()

    if col_reset.button(
        "Restaurar defaults",
        use_container_width=True
    ):
        st.session_state.umbrales = None
        st.toast("Umbrales restaurados a valores default", icon="🔄")
        st.rerun()


# ── Tab 3: Sistema ────────────────────────────────────────────

with tab_sistema:
    st.markdown("#### Caché de datos")
    st.caption(
        "Los datos se cachean para reducir llamadas a las APIs. "
        "Limpiá el caché si ves datos desactualizados."
    )

    # Estado del caché
    col1, col2 = st.columns(2)

    col1.markdown(
        """
        <div style='
            background:#161B22;
            border-radius:8px;
            padding:12px 16px;
        '>
            <div style='color:#8B949E;font-size:12px;'>
                CoinGecko API
            </div>
            <div style='font-weight:600;margin-top:4px;'>
                TTL: 5 minutos
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    col2.markdown(
        """
        <div style='
            background:#161B22;
            border-radius:8px;
            padding:12px 16px;
        '>
            <div style='color:#8B949E;font-size:12px;'>
                Fear & Greed Index
            </div>
            <div style='font-weight:600;margin-top:4px;'>
                TTL: 60 minutos
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    col3, col4 = st.columns(2)

    if col3.button(
        "🗑️ Limpiar caché de precios",
        use_container_width=True
    ):
        from utils.coingecko import (
            get_top_monedas, get_historico,
            get_datos_globales, get_trending,
            get_detalle_moneda, buscar_moneda
        )
        get_top_monedas.clear()
        get_historico.clear()
        get_datos_globales.clear()
        get_trending.clear()
        get_detalle_moneda.clear()
        buscar_moneda.clear()
        st.toast("Caché de precios limpiado", icon="🗑️")

    if col4.button(
        "🗑️ Limpiar caché de noticias",
        use_container_width=True
    ):
        from utils.noticias import get_feed_completo, get_noticias_rss
        from utils.feargreed import (
            get_fear_greed_actual,
            get_fear_greed_historico,
            get_resumen_sentimiento
        )
        get_feed_completo.clear()
        get_noticias_rss.clear()
        get_fear_greed_actual.clear()
        get_fear_greed_historico.clear()
        get_resumen_sentimiento.clear()
        st.toast("Caché de noticias y Fear & Greed limpiado", icon="🗑️")

    if st.button(
        "🗑️ Limpiar TODO el caché",
        use_container_width=True,
        type="primary"
    ):
        st.cache_data.clear()
        st.toast("Todo el caché limpiado — próxima carga será más lenta", icon="🔄")

    st.divider()

    # Estado de la sesión
    st.markdown("#### Estado de la sesión")

    col_a, col_b, col_c = st.columns(3)
    col_a.metric(
        "Posiciones en portafolio",
        len(st.session_state.get("portafolio", {}))
    )
    col_b.metric(
        "Monedas favoritas",
        len(st.session_state.get("favoritas", []))
    )
    col_c.metric(
        "Umbrales",
        "Personalizados" if st.session_state.get("umbrales") else "Default"
    )

    with st.expander("Ver session_state completo"):
        estado_visible = {
            "moneda_ref":      st.session_state.get("moneda_ref"),
            "periodo_default": st.session_state.get("periodo_default"),
            "favoritas":       st.session_state.get("favoritas"),
            "portafolio":      st.session_state.get("portafolio"),
            "umbrales":        st.session_state.get("umbrales"),
        }
        st.json(estado_visible)

    st.divider()

    # Cerrar sesión
    st.markdown("#### Sesión")
    if st.button(
        "Cerrar sesión",
        use_container_width=True
    ):
        for key in ["autenticado", "login_hora"]:
            st.session_state.pop(key, None)
        st.rerun()