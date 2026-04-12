import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# ── Configuración base ────────────────────────────────────────

BASE_URL = "https://api.coingecko.com/api/v3"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "CryptoSentinel/1.0"  # buena práctica identificarse
}

# ── Función de request centralizada ──────────────────────────

def _get(endpoint: str, params: dict = None) -> dict | list | None:
    """
    Función interna que centraliza todos los requests a CoinGecko.

    Ventajas de tener una sola función de request:
    - El manejo de errores se escribe una sola vez
    - Si CoinGecko cambia la URL base, se cambia en un solo lugar
    - Fácil agregar headers de autenticación en el futuro

    Devuelve el JSON parseado, o None si hubo algún error.
    """
    url = f"{BASE_URL}/{endpoint}"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            params=params,
            timeout=10  # si no responde en 10 segundos, falla limpio
        )

        # Manejar rate limiting — CoinGecko devuelve 429 si hacés
        # más de 30 requests por minuto en el plan gratuito
        if response.status_code == 429:
            st.warning("⏳ Límite de CoinGecko alcanzado. Esperá un momento y recargá.")
            return None

        # Cualquier otro error HTTP (404, 500, etc.)
        response.raise_for_status()

        return response.json()

    except requests.exceptions.Timeout:
        st.error("⏱️ CoinGecko no respondió a tiempo. Intentá de nuevo.")
        return None

    except requests.exceptions.ConnectionError:
        st.error("🔌 Sin conexión a internet o CoinGecko no disponible.")
        return None

    except requests.exceptions.HTTPError as e:
        st.error(f"❌ Error en la API de CoinGecko: {e}")
        return None

    except Exception as e:
        st.error(f"❌ Error inesperado: {e}")
        return None


# ── Función 1: Top monedas del mercado ────────────────────────

@st.cache_data(ttl=300)  # refresca cada 5 minutos
def get_top_monedas(limite: int = 50, moneda: str = "usd") -> pd.DataFrame:
    """
    Devuelve las top N monedas ordenadas por market cap.

    Cada fila del DataFrame tiene:
    - id:                  identificador interno de CoinGecko (ej: "bitcoin")
    - symbol:              ticker en mayúsculas (ej: "BTC")
    - name:                nombre completo (ej: "Bitcoin")
    - current_price:       precio actual en USD
    - market_cap:          capitalización de mercado
    - market_cap_rank:     ranking por market cap
    - total_volume:        volumen de las últimas 24 horas
    - price_change_24h:    variación absoluta en las últimas 24 horas
    - price_change_pct_24h: variación porcentual en las últimas 24 horas
    - price_change_pct_7d: variación porcentual en los últimos 7 días
    - image:               URL del ícono de la moneda

    Parámetros:
    - limite:  cuántas monedas traer (máximo 250 por request)
    - moneda:  moneda de referencia para los precios ("usd", "eur", "ars")
    """
    data = _get("coins/markets", params={
        "vs_currency":           moneda,
        "order":                 "market_cap_desc",
        "per_page":              limite,
        "page":                  1,
        "sparkline":             False,
        "price_change_percentage": "24h,7d"
    })

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    # Renombrar columnas a nombres más limpios
    df = df.rename(columns={
        "price_change_percentage_24h":              "price_change_pct_24h",
        "price_change_percentage_7d_in_currency":   "price_change_pct_7d",
    })

    # Quedarse solo con las columnas que vamos a usar
    columnas = [
        "id", "symbol", "name", "image", "current_price",
        "market_cap", "market_cap_rank", "total_volume",
        "price_change_24h", "price_change_pct_24h", "price_change_pct_7d"
    ]
    columnas_existentes = [c for c in columnas if c in df.columns]
    df = df[columnas_existentes]

    # Convertir símbolo a mayúsculas
    df["symbol"] = df["symbol"].str.upper()

    return df


# ── Función 2: Histórico de precios ───────────────────────────

@st.cache_data(ttl=300)
def get_historico(coin_id: str, dias: int = 30, moneda: str = "usd") -> pd.DataFrame:
    """
    Devuelve el histórico de precios de una moneda.

    CoinGecko ajusta automáticamente la granularidad:
    - 1 día:        datos cada 5 minutos
    - 2-90 días:    datos cada hora
    - 91+ días:     datos diarios

    Devuelve un DataFrame con columnas:
    - fecha:  datetime con timezone UTC
    - precio: precio de cierre en la moneda elegida

    Parámetros:
    - coin_id: identificador de CoinGecko (ej: "bitcoin", "ethereum")
    - dias:    cantidad de días hacia atrás (1, 7, 30, 90, 365)
    - moneda:  moneda de referencia
    """
    data = _get(f"coins/{coin_id}/market_chart", params={
        "vs_currency": moneda,
        "days":        dias,
        "interval":    "daily" if dias > 90 else ""
    })

    if not data or "prices" not in data:
        return pd.DataFrame()

    # CoinGecko devuelve listas de [timestamp_ms, valor]
    df = pd.DataFrame(data["prices"], columns=["timestamp", "precio"])

    # Convertir timestamp de milisegundos a datetime
    df["fecha"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df[["fecha", "precio"]].copy()

    return df


# ── Función 3: Detalle de una moneda ─────────────────────────

@st.cache_data(ttl=600)  # detalle cambia menos seguido, 10 minutos
def get_detalle_moneda(coin_id: str) -> dict:
    """
    Devuelve información detallada de una moneda específica.

    Incluye descripción, links, ATH, ATL, supply y más.
    Útil para la página de análisis y el portafolio.
    """
    data = _get(f"coins/{coin_id}", params={
        "localization":   False,  # no traer traducciones (más liviano)
        "tickers":        False,  # no traer exchanges
        "market_data":    True,
        "community_data": False,
        "developer_data": False
    })

    if not data:
        return {}

    # Extraer solo lo que necesitamos para no cargar todo el objeto
    market = data.get("market_data", {})

    return {
        "id":               data.get("id"),
        "symbol":           data.get("symbol", "").upper(),
        "name":             data.get("name"),
        "descripcion":      data.get("description", {}).get("en", ""),
        "imagen":           data.get("image", {}).get("large"),
        "sitio_web":        data.get("links", {}).get("homepage", [""])[0],
        "precio_usd":       market.get("current_price", {}).get("usd"),
        "market_cap_usd":   market.get("market_cap", {}).get("usd"),
        "ath":              market.get("ath", {}).get("usd"),
        "ath_fecha":        market.get("ath_date", {}).get("usd"),
        "atl":              market.get("atl", {}).get("usd"),
        "supply_total":     market.get("total_supply"),
        "supply_circulante":market.get("circulating_supply"),
        "variacion_24h":    market.get("price_change_percentage_24h"),
        "variacion_7d":     market.get("price_change_percentage_7d"),
        "variacion_30d":    market.get("price_change_percentage_30d"),
    }


# ── Función 4: Datos globales del mercado ────────────────────

@st.cache_data(ttl=300)
def get_datos_globales() -> dict:
    """
    Devuelve métricas globales del mercado cripto:
    - market_cap_total:    capitalización total en USD
    - volumen_24h:         volumen total de las últimas 24 horas
    - dominancia_btc:      porcentaje del mercado que es Bitcoin
    - dominancia_eth:      porcentaje del mercado que es Ethereum
    - variacion_24h:       variación del market cap total en 24 horas
    - num_monedas:         cantidad de criptomonedas activas

    Útil para el header global y la página de Sentimiento.
    """
    data = _get("global")

    if not data or "data" not in data:
        return {}

    d = data["data"]

    return {
        "market_cap_total": d.get("total_market_cap", {}).get("usd", 0),
        "volumen_24h":      d.get("total_volume", {}).get("usd", 0),
        "dominancia_btc":   d.get("market_cap_percentage", {}).get("btc", 0),
        "dominancia_eth":   d.get("market_cap_percentage", {}).get("eth", 0),
        "variacion_24h":    d.get("market_cap_change_percentage_24h_usd", 0),
        "num_monedas":      d.get("active_cryptocurrencies", 0),
    }


# ── Función 5: Monedas trending ───────────────────────────────

@st.cache_data(ttl=1800)  # trending cambia lento, 30 minutos
def get_trending() -> list[dict]:
    """
    Devuelve las 7 monedas más buscadas en CoinGecko
    en las últimas 24 horas.

    Cada elemento de la lista tiene:
    - id:     identificador de CoinGecko
    - name:   nombre completo
    - symbol: ticker en mayúsculas
    - rank:   posición en el ranking de trending
    - imagen: URL del ícono
    """
    data = _get("search/trending")

    if not data or "coins" not in data:
        return []

    trending = []
    for item in data["coins"]:
        coin = item.get("item", {})
        trending.append({
            "id":     coin.get("id"),
            "name":   coin.get("name"),
            "symbol": coin.get("symbol", "").upper(),
            "rank":   coin.get("market_cap_rank"),
            "imagen": coin.get("small"),  # ícono pequeño 24x24
        })

    return trending


# ── Función 6: Buscar moneda por nombre o símbolo ────────────

@st.cache_data(ttl=3600)  # la lista de monedas cambia muy poco, 1 hora
def buscar_moneda(query: str) -> list[dict]:
    """
    Busca monedas por nombre o símbolo.
    Útil para el buscador en la página de Portafolio.

    Devuelve lista de coincidencias con id, name y symbol.
    """
    data = _get("search", params={"query": query})

    if not data or "coins" not in data:
        return []

    return [
        {
            "id":     c.get("id"),
            "name":   c.get("name"),
            "symbol": c.get("symbol", "").upper(),
        }
        for c in data["coins"][:10]  # máximo 10 resultados
    ]