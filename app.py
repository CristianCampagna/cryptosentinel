import streamlit as st
import hmac
from datetime import datetime



# ── Configuración global ──────────────────────────────────────
# DEBE ser la primera instrucción de Streamlit en todo el proyecto.
# Si cualquier página llama a st.set_page_config también, va a romper.

st.set_page_config(
    page_title="CryptoSentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS global ────────────────────────────────────────────────
# Pequeños ajustes visuales que aplican a toda la app.
# Nada estructural — solo pulido visual.

st.markdown("""
<style>
    /* Reducir padding superior de todas las páginas */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1rem;
    }

    /* Métricas — valor más grande y destacado */
    [data-testid="stMetricValue"] {
        font-size: 1.6rem;
        font-weight: 600;
    }

    /* Sidebar — separador más sutil */
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.1);
    }

    /* Links en noticias — sin subrayado por defecto */
    a {
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)


# ── Autenticación ─────────────────────────────────────────────

def _verificar_password(password: str) -> bool:
    """
    Compara la password ingresada con la del secrets.toml
    usando hmac.compare_digest para evitar timing attacks.

    Un timing attack ocurre cuando un atacante mide el tiempo
    que tarda la comparación para deducir cuántos caracteres
    acertó. compare_digest siempre tarda lo mismo sin importar
    cuánto coincida el string.
    """
    password_correcta = st.secrets.get("auth", {}).get("password", "")
    return hmac.compare_digest(password, password_correcta)


def _pantalla_login() -> None:
    # Ocultar sidebar en la pantalla de login
    st.markdown("""
                <style>
                    [data-testid="stSidebar"] { display: none; }
                    [data-testid="collapsedControl"] { display: none; }
                </style>
            """, unsafe_allow_html=True)

        # ... resto del código que ya tenés

    # Centrar el formulario con columnas
    _, col, _ = st.columns([1, 1.2, 1])

    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)

        # Logo y título
        st.markdown(
            """
            <div style='text-align:center; margin-bottom:2rem;'>
                <span style='font-size:3rem;'>🛡️</span>
                <h1 style='margin:0.3rem 0 0.2rem;'>CryptoSentinel</h1>
                <p style='color:#8B949E; margin:0;'>
                    Monitor de sentimiento cripto
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Formulario de login
        with st.form("login", clear_on_submit=True):
            password = st.text_input(
                "Contraseña",
                type="password",
                placeholder="Ingresá tu contraseña"
            )
            submit = st.form_submit_button(
                "Entrar →",
                use_container_width=True,
                type="primary"
            )

        if submit:
            if _verificar_password(password):
                st.session_state.autenticado   = True
                st.session_state.login_hora    = datetime.now()
                st.rerun()
            else:
                st.error("Contraseña incorrecta")


# ── Inicialización del estado global ─────────────────────────

def _init_session_state() -> None:
    """
    Inicializa todas las variables de session_state
    que se comparten entre páginas.

    Centralizar la inicialización acá evita que cada página
    tenga que verificar si la variable existe antes de usarla.
    Solo se ejecuta una vez por sesión — si la variable
    ya existe, no la sobreescribe.
    """

    # Portafolio: dict {coin_id: {simbolo, cantidad, precio_compra}}
    if "portafolio" not in st.session_state:
        st.session_state.portafolio = {}

    # Monedas favoritas para el watchlist
    if "favoritas" not in st.session_state:
        st.session_state.favoritas = ["bitcoin", "ethereum",
                                       "solana", "ripple", "binancecoin"]

    # Umbrales personalizados de alertas
    # Si no están en session_state, alerts.py usa los defaults
    if "umbrales" not in st.session_state:
        st.session_state.umbrales = None

    # Moneda de referencia para precios
    if "moneda_ref" not in st.session_state:
        st.session_state.moneda_ref = "usd"

    # Período default para gráficos
    if "periodo_default" not in st.session_state:
        st.session_state.periodo_default = 30

    # Hora del último login (para mostrar en sidebar)
    if "login_hora" not in st.session_state:
        st.session_state.login_hora = datetime.now()


# ── Sidebar global ────────────────────────────────────────────

def _render_sidebar() -> None:
    """
    Sidebar que aparece en todas las páginas.
    Contiene: branding, estado del mercado resumido,
    configuración rápida y botón de logout.
    """
    with st.sidebar:

        # Branding
        st.markdown(
            """
            <div style='text-align:center; padding: 0.5rem 0 1rem;'>
                <span style='font-size:2rem;'>🛡️</span>
                <h2 style='margin:0.2rem 0 0; font-size:1.3rem;'>
                    CryptoSentinel
                </h2>
                <p style='color:#8B949E; font-size:0.75rem; margin:0;'>
                    Monitor de sentimiento cripto
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.divider()

        # Estado del mercado — cargado de forma lazy
        # (solo si los módulos ya están importados)
        _render_estado_mercado()

        st.divider()

        # Configuración rápida
        st.caption("⚙️ Configuración rápida")

        moneda = st.selectbox(
            "Moneda de referencia",
            ["usd", "eur", "ars"],
            index=["usd", "eur", "ars"].index(
                st.session_state.get("moneda_ref", "usd")
            ),
            label_visibility="collapsed"
        )
        if moneda != st.session_state.moneda_ref:
            st.session_state.moneda_ref = moneda
            st.rerun()

        st.divider()

        # Info de sesión y logout
        hora = st.session_state.login_hora.strftime("%H:%M")
        st.caption(f"🕐 Sesión iniciada a las {hora}")

        if st.button("Cerrar sesión", use_container_width=True):
            # Limpiar solo las claves de autenticación
            # session_state del portafolio se mantiene
            for key in ["autenticado", "login_hora"]:
                st.session_state.pop(key, None)
            st.rerun()


def _render_estado_mercado() -> None:
    """
    Muestra un resumen del estado del mercado en el sidebar.
    Cargado con try/except para que un error de API
    no rompa toda la navegación.
    """
    try:
        from utils.coingecko import get_datos_globales
        from utils.feargreed import get_fear_greed_actual

        globales = get_datos_globales()
        fg       = get_fear_greed_actual()

        if globales and fg:
            st.caption("📊 Estado del mercado")

            # Market cap total
            cap = globales.get("market_cap_total", 0)
            cap_str = (f"${cap/1e12:.2f}T" if cap > 1e12
                       else f"${cap/1e9:.1f}B")

            variacion = globales.get("variacion_24h", 0)
            color_var = "#34C759" if variacion >= 0 else "#FF3B30"
            signo     = "+" if variacion >= 0 else ""

            st.markdown(
                f"""
                <div style='
                    background:#161B22;
                    border-radius:8px;
                    padding:10px 12px;
                    margin-bottom:8px;
                '>
                    <div style='color:#8B949E;font-size:11px;'>
                        Market Cap total
                    </div>
                    <div style='font-size:15px;font-weight:600;'>
                        {cap_str}
                        <span style='color:{color_var};font-size:12px;'>
                            {signo}{variacion:.1f}%
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Fear & Greed
            valor = fg.get("valor", 50)
            label = fg.get("label", "Neutral")
            color = fg.get("color", "#FFCC00")
            emoji = fg.get("emoji", "😐")

            st.markdown(
                f"""
                <div style='
                    background:#161B22;
                    border-radius:8px;
                    padding:10px 12px;
                '>
                    <div style='color:#8B949E;font-size:11px;'>
                        Fear & Greed Index
                    </div>
                    <div style='font-size:15px;font-weight:600;'>
                        <span style='color:{color};'>
                            {emoji} {valor} — {label}
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    except Exception:
        # Si la API falla, el sidebar sigue funcionando
        st.caption("📊 Datos no disponibles")


# ── Punto de entrada principal ────────────────────────────────

def main() -> None:
    """
    Función principal que orquesta toda la app.
    Orden de ejecución en cada re-run:

    1. Verificar autenticación
    2. Si no está autenticado → mostrar login y detener
    3. Si está autenticado → inicializar estado y navegar
    """

    # 1. Verificar autenticación
    if not st.session_state.get("autenticado", False):
        _pantalla_login()
        st.stop()

    # 2. Inicializar estado global (solo la primera vez)
    _init_session_state()

    st.markdown("""
    <style>
        /* Forzar sidebar visible después del login */
        [data-testid="stSidebar"] { display: flex !important; }
    </style>
    """, unsafe_allow_html=True)

    # 3. Definir páginas con st.navigation
    paginas = st.navigation({
        "Mercado": [
            st.Page("pages/sentimiento.py",
                    title="Sentimiento",
                    icon="🌡️"),
            st.Page("pages/noticias.py",
                    title="Noticias",
                    icon="📰"),
            st.Page("pages/precios.py",
                    title="Precios",
                    icon="💰"),
        ],
        "Personal": [
            st.Page("pages/portafolio.py",
                    title="Portafolio",
                    icon="💼"),
        ],
        "Sistema": [
            st.Page("pages/configuracion.py",
                    title="Configuración",
                    icon="⚙️"),
        ]
    })

    # 4. Renderizar sidebar global
    _render_sidebar()

    # 5. Ejecutar la página seleccionada
    paginas.run()


# ── Ejecutar ──────────────────────────────────────────────────

if __name__ == "__main__" or True:
    main()