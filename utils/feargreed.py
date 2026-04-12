import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# ── Configuración ─────────────────────────────────────────────

BASE_URL = "https://api.alternative.me/fng/"

# Mapeo de clasificaciones a español y colores
CLASIFICACIONES = {
    "Extreme Fear":  {"label": "Miedo extremo",  "color": "#FF3B30", "emoji": "😱"},
    "Fear":          {"label": "Miedo",           "color": "#FF9500", "emoji": "😰"},
    "Neutral":       {"label": "Neutral",         "color": "#FFCC00", "emoji": "😐"},
    "Greed":         {"label": "Codicia",         "color": "#34C759", "emoji": "😏"},
    "Extreme Greed": {"label": "Codicia extrema", "color": "#00C7BE", "emoji": "🤑"},
}


# ── Función interna de request ────────────────────────────────

def _get(limit: int) -> dict | None:
    """
    Request centralizado a Alternative.me.
    Igual patrón que coingecko.py para consistencia.
    """
    try:
        response = requests.get(
            BASE_URL,
            params={"limit": limit, "format": "json"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout:
        st.error("⏱️ Alternative.me no respondió a tiempo.")
        return None

    except requests.exceptions.ConnectionError:
        st.error("🔌 Sin conexión a Alternative.me.")
        return None

    except requests.exceptions.HTTPError as e:
        st.error(f"❌ Error en Fear & Greed API: {e}")
        return None

    except Exception as e:
        st.error(f"❌ Error inesperado: {e}")
        return None


# ── Función 1: Valor actual ───────────────────────────────────

@st.cache_data(ttl=3600)  # el índice se actualiza una vez por día
def get_fear_greed_actual() -> dict:
    """
    Devuelve el valor actual del Fear & Greed Index.

    Estructura del dict devuelto:
    - valor:          número entre 0 y 100
    - clasificacion:  string en inglés (ej: "Extreme Fear")
    - label:          string en español (ej: "Miedo extremo")
    - color:          hex del color asociado a la zona
    - emoji:          emoji representativo
    - fecha:          datetime del último update
    - siguiente_update: string con tiempo hasta próxima actualización
    """
    data = _get(limit=1)

    if not data or "data" not in data or not data["data"]:
        return {}

    item = data["data"][0]
    clasificacion = item.get("value_classification", "Neutral")
    info = CLASIFICACIONES.get(clasificacion, CLASIFICACIONES["Neutral"])

    return {
        "valor":            int(item.get("value", 50)),
        "clasificacion":    clasificacion,
        "label":            info["label"],
        "color":            info["color"],
        "emoji":            info["emoji"],
        "fecha":            datetime.fromtimestamp(int(item.get("timestamp", 0))),
        "siguiente_update": data.get("metadata", {}).get("next_update", "—"),
    }


# ── Función 2: Historial ──────────────────────────────────────

@st.cache_data(ttl=3600)
def get_fear_greed_historico(dias: int = 30) -> pd.DataFrame:
    """
    Devuelve el historial del índice para los últimos N días.

    Devuelve un DataFrame con columnas:
    - fecha:          datetime del registro
    - valor:          número entre 0 y 100
    - clasificacion:  string en inglés
    - label:          string en español
    - color:          hex del color de la zona
    - emoji:          emoji representativo
    - zona:           número de zona (1=Extreme Fear ... 5=Extreme Greed)
                      útil para colorear gráficos por zona

    Parámetros:
    - dias: cuántos días hacia atrás traer (máximo ~900)
    """
    data = _get(limit=dias)

    if not data or "data" not in data:
        return pd.DataFrame()

    filas = []
    for item in data["data"]:
        clasificacion = item.get("value_classification", "Neutral")
        info = CLASIFICACIONES.get(clasificacion, CLASIFICACIONES["Neutral"])
        valor = int(item.get("value", 50))

        filas.append({
            "fecha":         datetime.fromtimestamp(int(item.get("timestamp", 0))),
            "valor":         valor,
            "clasificacion": clasificacion,
            "label":         info["label"],
            "color":         info["color"],
            "emoji":         info["emoji"],
            "zona":          _valor_a_zona(valor),
        })

    df = pd.DataFrame(filas)
    df = df.sort_values("fecha").reset_index(drop=True)

    return df


# ── Función 3: Resumen estadístico ────────────────────────────

@st.cache_data(ttl=3600)
def get_resumen_sentimiento(dias: int = 30) -> dict:
    """
    Devuelve estadísticas del sentimiento en los últimos N días.
    Útil para mostrar en la página de Sentimiento como KPIs.

    Devuelve:
    - promedio:        valor promedio del período
    - maximo:          valor más alto
    - minimo:          valor más bajo
    - dias_fear:       días en zona Fear o Extreme Fear
    - dias_greed:      días en zona Greed o Extreme Greed
    - tendencia:       "mejorando", "empeorando" o "estable"
                       comparando la primera y segunda mitad del período
    - clasificacion_promedio: clasificación del valor promedio
    """
    df = get_fear_greed_historico(dias)

    if df.empty:
        return {}

    promedio = df["valor"].mean()
    mitad    = len(df) // 2

    # Comparar primera mitad vs segunda mitad para detectar tendencia
    primera_mitad  = df.iloc[:mitad]["valor"].mean()
    segunda_mitad  = df.iloc[mitad:]["valor"].mean()
    diferencia     = segunda_mitad - primera_mitad

    if diferencia > 3:
        tendencia = "mejorando"
    elif diferencia < -3:
        tendencia = "empeorando"
    else:
        tendencia = "estable"

    # Clasificar el promedio usando los mismos rangos
    clasificacion_promedio = _valor_a_clasificacion(round(promedio))

    return {
        "promedio":               round(promedio, 1),
        "maximo":                 int(df["valor"].max()),
        "minimo":                 int(df["valor"].min()),
        "dias_fear":              int((df["valor"] < 50).sum()),
        "dias_greed":             int((df["valor"] >= 50).sum()),
        "tendencia":              tendencia,
        "clasificacion_promedio": clasificacion_promedio,
    }


# ── Helpers internos ──────────────────────────────────────────

def _valor_a_zona(valor: int) -> int:
    """
    Convierte un valor 0-100 a número de zona:
    1 = Extreme Fear, 2 = Fear, 3 = Neutral,
    4 = Greed, 5 = Extreme Greed
    """
    if valor < 25:   return 1
    if valor < 50:   return 2
    if valor < 55:   return 3
    if valor < 75:   return 4
    return 5

def _valor_a_clasificacion(valor: int) -> str:
    """Convierte un valor numérico a su clasificación en inglés."""
    if valor < 25:   return "Extreme Fear"
    if valor < 50:   return "Fear"
    if valor < 55:   return "Neutral"
    if valor < 75:   return "Greed"
    return "Extreme Greed"

def get_color(valor: int) -> str:
    """
    Función pública para obtener el color hex de cualquier valor.
    La usan charts.py y alerts.py para colorear elementos.
    """
    clasificacion = _valor_a_clasificacion(valor)
    return CLASIFICACIONES.get(clasificacion, {}).get("color", "#FFCC00")

def get_emoji(valor: int) -> str:
    """Función pública para obtener el emoji de cualquier valor."""
    clasificacion = _valor_a_clasificacion(valor)
    return CLASIFICACIONES.get(clasificacion, {}).get("emoji", "😐")