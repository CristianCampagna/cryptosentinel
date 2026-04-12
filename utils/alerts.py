import streamlit as st
import pandas as pd
from datetime import datetime

# ── Umbrales configurables ────────────────────────────────────
# Todos los valores están centralizados acá.
# Si el usuario los personaliza desde Configuración,
# se guardan en session_state y sobreescriben estos defaults.

UMBRALES_DEFAULT = {
    # Fear & Greed
    "fg_miedo_extremo":   25,   # por debajo de este valor → alerta roja
    "fg_codicia_extrema": 75,   # por encima de este valor → alerta cyan

    # Variación de precio en 24h (%)
    "precio_caida_fuerte":  -5.0,   # caída fuerte → badge rojo
    "precio_caida_leve":    -2.0,   # caída leve   → badge naranja
    "precio_suba_fuerte":    5.0,   # suba fuerte  → badge verde brillante
    "precio_suba_leve":      2.0,   # suba leve    → badge verde

    # Volumen (multiplicador sobre el promedio)
    "volumen_alto": 2.0,   # volumen > 2x el promedio → alerta de actividad
}

# ── Definición de niveles de alerta ──────────────────────────

NIVELES = {
    "critico":  {"color": "#FF3B30", "bg": "#2D0A08", "icono": "🚨"},
    "peligro":  {"color": "#FF9500", "bg": "#2D1800", "icono": "⚠️"},
    "neutro":   {"color": "#FFCC00", "bg": "#2D2500", "icono": "ℹ️"},
    "positivo": {"color": "#34C759", "bg": "#0A2D13", "icono": "✅"},
    "euforia":  {"color": "#00C7BE", "bg": "#002D2B", "icono": "🚀"},
}


# ── Función helper: obtener umbrales activos ──────────────────

def _get_umbrales() -> dict:
    umbrales = st.session_state.get("umbrales", None)
    # Si es None o no es un dict válido, usar los defaults
    if not umbrales or not isinstance(umbrales, dict):
        return UMBRALES_DEFAULT
    return umbrales


# ── Bloque 1: Alertas de Fear & Greed ────────────────────────

def alerta_fear_greed(valor: int) -> dict | None:
    """
    Evalúa el valor actual del Fear & Greed Index
    y devuelve una alerta si está en zona extrema.

    Devuelve None si el valor está en zona normal (25-75).
    Devuelve un dict con nivel, titulo, mensaje y estilo
    si está en zona de alerta.
    """
    u = _get_umbrales()

    if valor <= u["fg_miedo_extremo"]:
        return {
            "nivel":   "critico",
            "titulo":  f"😱 Miedo Extremo — {valor}/100",
            "mensaje": (
                f"El mercado está en pánico. Históricamente, valores "
                f"por debajo de {u['fg_miedo_extremo']} han precedido "
                f"rebotes técnicos. Procedé con cautela."
            ),
            **NIVELES["critico"]
        }

    if valor >= u["fg_codicia_extrema"]:
        return {
            "nivel":   "euforia",
            "titulo":  f"🤑 Codicia Extrema — {valor}/100",
            "mensaje": (
                f"El mercado está en euforia. Valores por encima de "
                f"{u['fg_codicia_extrema']} suelen preceder correcciones. "
                f"Considerá tomar ganancias."
            ),
            **NIVELES["euforia"]
        }

    return None


# ── Bloque 2: Alertas de precio por moneda ───────────────────

def alerta_precio(simbolo: str, variacion_pct: float) -> dict | None:
    """
    Evalúa la variación de precio de una moneda en 24h
    y devuelve una alerta según la magnitud del movimiento.

    Parámetros:
    - simbolo:       ticker de la moneda (ej: "BTC")
    - variacion_pct: variación en % (ej: -6.5 para -6.5%)

    Devuelve None si el movimiento es normal (dentro del rango leve).
    """
    u = _get_umbrales()

    if variacion_pct <= u["precio_caida_fuerte"]:
        return {
            "nivel":   "critico",
            "titulo":  f"📉 {simbolo} cayó {variacion_pct:.1f}% en 24h",
            "mensaje": (
                f"{simbolo} registra una caída fuerte. "
                f"Revisá niveles de soporte y tu exposición."
            ),
            **NIVELES["critico"]
        }

    if variacion_pct <= u["precio_caida_leve"]:
        return {
            "nivel":   "peligro",
            "titulo":  f"📉 {simbolo} bajó {variacion_pct:.1f}% en 24h",
            "mensaje": f"{simbolo} muestra presión vendedora moderada.",
            **NIVELES["peligro"]
        }

    if variacion_pct >= u["precio_suba_fuerte"]:
        return {
            "nivel":   "euforia",
            "titulo":  f"📈 {simbolo} subió {variacion_pct:.1f}% en 24h",
            "mensaje": (
                f"{simbolo} registra una suba fuerte. "
                f"Momentum positivo — atento a posible sobrecompra."
            ),
            **NIVELES["euforia"]
        }

    if variacion_pct >= u["precio_suba_leve"]:
        return {
            "nivel":   "positivo",
            "titulo":  f"📈 {simbolo} subió {variacion_pct:.1f}% en 24h",
            "mensaje": f"{simbolo} muestra momentum comprador.",
            **NIVELES["positivo"]
        }

    return None


# ── Bloque 3: Alertas de volumen ─────────────────────────────

def alerta_volumen(simbolo: str, volumen_actual: float,
                   volumen_promedio: float) -> dict | None:
    """
    Detecta volumen inusualmente alto comparado con el promedio.
    Volumen alto + movimiento de precio = señal relevante.

    Parámetros:
    - simbolo:           ticker de la moneda
    - volumen_actual:    volumen de las últimas 24h
    - volumen_promedio:  volumen promedio de referencia
    """
    if volumen_promedio <= 0:
        return None

    u          = _get_umbrales()
    ratio      = volumen_actual / volumen_promedio

    if ratio >= u["volumen_alto"]:
        return {
            "nivel":   "neutro",
            "titulo":  f"📊 Volumen inusual en {simbolo}",
            "mensaje": (
                f"El volumen de {simbolo} es "
                f"{ratio:.1f}x el promedio habitual. "
                f"Mayor actividad de traders institucionales o retailers."
            ),
            **NIVELES["neutro"]
        }

    return None


# ── Bloque 4: Escaneo masivo del mercado ─────────────────────

def escanear_mercado(df_monedas: pd.DataFrame) -> list[dict]:
    """
    Recibe el DataFrame de get_top_monedas() y evalúa
    todas las monedas en busca de alertas activas.

    Devuelve lista de alertas ordenadas por severidad:
    critico → peligro → euforia → neutro → positivo

    Uso típico:
        df = get_top_monedas(50)
        alertas = escanear_mercado(df)
        mostrar_alertas(alertas)
    """
    if df_monedas.empty:
        return []

    alertas = []

    for _, row in df_monedas.iterrows():
        simbolo    = row.get("symbol", "")
        variacion  = row.get("price_change_pct_24h", 0) or 0

        alerta = alerta_precio(simbolo, variacion)
        if alerta:
            alertas.append(alerta)

    # Ordenar por severidad
    orden = {"critico": 0, "peligro": 1, "euforia": 2,
             "neutro": 3, "positivo": 4}
    alertas.sort(key=lambda a: orden.get(a["nivel"], 99))

    return alertas


# ── Bloque 5: Funciones de renderizado UI ────────────────────
# Estas funciones generan HTML/markdown de Streamlit.
# Las páginas las llaman directamente sin preocuparse
# por los colores o estilos.

def mostrar_banner(alerta: dict) -> None:
    """
    Muestra un banner destacado en la parte superior de la página.
    Ideal para alertas críticas de Fear & Greed.
    """
    if not alerta:
        return

    color = alerta.get("color", "#FFCC00")
    bg    = alerta.get("bg",    "#2D2500")
    icono = alerta.get("icono", "ℹ️")

    st.markdown(
        f"""
        <div style="
            background-color: {bg};
            border-left: 4px solid {color};
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 16px;
        ">
            <span style="color:{color}; font-weight:600; font-size:15px;">
                {alerta['titulo']}
            </span><br>
            <span style="color:#AAAAAA; font-size:13px;">
                {alerta['mensaje']}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )


def mostrar_badge(variacion_pct: float) -> str:
    """
    Devuelve un string con HTML de un badge de color
    según la variación porcentual.

    Uso: st.markdown(mostrar_badge(-6.5), unsafe_allow_html=True)

    Ejemplos visuales:
    -6.5% → badge rojo    🔴 -6.5%
    -2.1% → badge naranja 🟠 -2.1%
     0.3% → badge gris    ⚪  +0.3%
     2.5% → badge verde   🟢 +2.5%
     7.1% → badge cyan    🔵 +7.1%
    """
    u = _get_umbrales()

    if variacion_pct <= u["precio_caida_fuerte"]:
        color, bg = "#FF3B30", "#2D0A08"
    elif variacion_pct <= u["precio_caida_leve"]:
        color, bg = "#FF9500", "#2D1800"
    elif variacion_pct >= u["precio_suba_fuerte"]:
        color, bg = "#00C7BE", "#002D2B"
    elif variacion_pct >= u["precio_suba_leve"]:
        color, bg = "#34C759", "#0A2D13"
    else:
        color, bg = "#8E8E93", "#1C1C1E"

    signo = "+" if variacion_pct > 0 else ""

    return (
        f'<span style="'
        f'background:{bg};color:{color};'
        f'padding:2px 8px;border-radius:4px;'
        f'font-size:13px;font-weight:600;'
        f'">{signo}{variacion_pct:.2f}%</span>'
    )


def mostrar_lista_alertas(alertas: list[dict]) -> None:
    """
    Renderiza una lista de alertas como banners apilados.
    Si no hay alertas, muestra un mensaje positivo.
    """
    if not alertas:
        st.success("✅ Sin alertas activas — mercado en rangos normales")
        return

    for alerta in alertas:
        mostrar_banner(alerta)


def color_variacion(variacion_pct: float) -> str:
    """
    Devuelve solo el color hex según la variación.
    Útil para colorear texto o elementos SVG en charts.py.
    """
    u = _get_umbrales()

    if variacion_pct   <= u["precio_caida_fuerte"]: return "#FF3B30"
    elif variacion_pct <= u["precio_caida_leve"]:   return "#FF9500"
    elif variacion_pct >= u["precio_suba_fuerte"]:  return "#00C7BE"
    elif variacion_pct >= u["precio_suba_leve"]:    return "#34C759"
    else:                                            return "#8E8E93"