import re
import streamlit as st
import feedparser
import requests
import pandas as pd
from datetime  import datetime
from dateutil  import parser as dateparser

# ── Fuentes RSS configuradas ──────────────────────────────────

RSS_FEEDS = {
    "CoinDesk":         "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph":    "https://cointelegraph.com/rss",
    "Decrypt":          "https://decrypt.co/feed",
    "Bitcoin Magazine": "https://bitcoinmagazine.com/feed",
}

COINGECKO_NEWS_URL = "https://api.coingecko.com/api/v3/news"

KEYWORDS_MONEDAS = {
    "BTC":   ["bitcoin", "btc"],
    "ETH":   ["ethereum", "eth", "ether"],
    "XRP":   ["xrp", "ripple"],
    "BNB":   ["bnb", "binance"],
    "SOL":   ["solana", "sol"],
    "ADA":   ["cardano", "ada"],
    "DOGE":  ["dogecoin", "doge"],
    "DOT":   ["polkadot", "dot"],
    "MATIC": ["polygon", "matic"],
    "AVAX":  ["avalanche", "avax"],
}


# ── Helpers internos ──────────────────────────────────────────

def _limpiar_html(texto: str) -> str:
    """
    Elimina tags HTML y decodifica entidades HTML comunes.
    Se aplica a título y descripción de cada noticia
    antes de guardarla — así el resto de la app recibe
    texto limpio sin tener que preocuparse por esto.
    """
    if not texto:
        return ""
    # Eliminar tags HTML
    texto = re.sub(r"<[^>]+>", "", texto)
    # Decodificar entidades HTML
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
    # Limpiar espacios extras
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _parsear_fecha(fecha_str: str) -> datetime:
    """
    Convierte cualquier formato de fecha string a datetime.
    Si falla devuelve la fecha actual.
    """
    if not fecha_str:
        return datetime.now()
    try:
        return dateparser.parse(str(fecha_str), ignoretz=True)
    except Exception:
        return datetime.now()


def _detectar_monedas(texto: str) -> list[str]:
    """
    Busca menciones de criptomonedas en un texto.
    Devuelve lista de símbolos encontrados.
    """
    if not texto:
        return []
    texto_lower = texto.lower()
    encontradas = []
    for simbolo, keywords in KEYWORDS_MONEDAS.items():
        if any(kw in texto_lower for kw in keywords):
            encontradas.append(simbolo)
    return encontradas


def _normalizar(titulo: str, url: str, fecha: datetime,
                fuente: str, descripcion: str = "") -> dict:
    """
    Estructura estándar para cualquier noticia.
    Aplica limpieza de HTML a título y descripción.
    """
    titulo_limpio      = _limpiar_html(titulo)
    descripcion_limpia = _limpiar_html(descripcion)
    texto_completo     = f"{titulo_limpio} {descripcion_limpia}"

    return {
        "titulo":      titulo_limpio or "Sin título",
        "url":         url or "",
        "fecha":       fecha,
        "fuente":      fuente,
        "descripcion": descripcion_limpia[:300],
        "monedas":     _detectar_monedas(texto_completo),
        "tipo":        "rss" if fuente in RSS_FEEDS else "coingecko",
    }


# ── Función 1: Noticias desde RSS feeds ───────────────────────

@st.cache_data(ttl=900)
def get_noticias_rss(max_por_fuente: int = 15) -> list[dict]:
    """
    Lee todos los feeds RSS y devuelve lista unificada
    de noticias normalizadas y con HTML limpiado.
    """
    noticias = []

    for nombre, url in RSS_FEEDS.items():
        try:
            response = requests.get(
                url,
                timeout=8,
                headers={"User-Agent": "CryptoSentinel/1.0"}
            )
            feed    = feedparser.parse(response.content)
            entradas = feed.entries[:max_por_fuente]

            for entry in entradas:
                titulo      = entry.get("title", "")
                url_noticia = entry.get("link", "")

                # Parsear fecha
                fecha_raw = (entry.get("published", "")
                             or entry.get("updated", ""))
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    fecha = datetime(*entry.published_parsed[:6])
                else:
                    fecha = _parsear_fecha(fecha_raw)

                # Obtener descripción y limpiar HTML
                descripcion = ""
                if entry.get("summary"):
                    descripcion = entry.summary
                elif entry.get("content"):
                    descripcion = entry.content[0].get("value", "")

                noticia = _normalizar(
                    titulo, url_noticia, fecha, nombre, descripcion
                )
                noticias.append(noticia)

        except requests.exceptions.Timeout:
            continue
        except Exception:
            continue

    return noticias


# ── Función 2: Noticias desde CoinGecko ───────────────────────

@st.cache_data(ttl=900)
def get_noticias_coingecko() -> list[dict]:
    """
    Trae noticias desde CoinGecko.
    Devuelve lista vacía si el endpoint no está disponible.
    """
    try:
        response = requests.get(
            COINGECKO_NEWS_URL,
            headers={
                "Accept":     "application/json",
                "User-Agent": "CryptoSentinel/1.0"
            },
            timeout=10
        )
        response.raise_for_status()
        data  = response.json()
        items = data.get("data", [])

        noticias = []
        for item in items:
            fecha   = _parsear_fecha(item.get("created_at", ""))
            noticia = _normalizar(
                titulo      = item.get("title", ""),
                url         = item.get("url", ""),
                fecha       = fecha,
                fuente      = item.get("news_site", "CoinGecko"),
                descripcion = item.get("description", "")
            )
            noticia["tipo"] = "coingecko"
            noticias.append(noticia)

        return noticias

    except Exception:
        return []


# ── Función 3: Feed combinado ─────────────────────────────────

@st.cache_data(ttl=900)
def get_feed_completo(max_noticias: int = 100) -> pd.DataFrame:
    """
    Combina RSS + CoinGecko en un DataFrame ordenado
    por fecha descendente con deduplicación.
    """
    rss       = get_noticias_rss()
    coingecko = get_noticias_coingecko()
    todas     = rss + coingecko

    if not todas:
        return pd.DataFrame()

    df = pd.DataFrame(todas)

    # Deduplicar por título
    df["titulo_key"] = df["titulo"].str[:60].str.lower().str.strip()
    df = df.drop_duplicates(subset="titulo_key").drop(columns="titulo_key")

    # Ordenar por fecha descendente
    df = df.sort_values("fecha", ascending=False).reset_index(drop=True)
    df = df.head(max_noticias)

    # Agregar tiempo relativo
    df["hace"] = df["fecha"].apply(_hace_cuanto)

    return df


# ── Función 4: Filtrar por moneda ─────────────────────────────

def filtrar_por_moneda(df: pd.DataFrame, simbolo: str) -> pd.DataFrame:
    if df.empty or not simbolo:
        return df
    return df[df["monedas"].apply(lambda m: simbolo in m)]


# ── Función 5: Filtrar por fuente ─────────────────────────────

def filtrar_por_fuente(df: pd.DataFrame,
                       fuentes: list[str]) -> pd.DataFrame:
    if df.empty or not fuentes:
        return df
    return df[df["fuente"].isin(fuentes)]


# ── Helper: tiempo relativo ───────────────────────────────────

def _hace_cuanto(fecha: datetime) -> str:
    if not isinstance(fecha, datetime):
        return "—"
    ahora      = datetime.now()
    diferencia = ahora - fecha
    segundos   = int(diferencia.total_seconds())
    minutos    = segundos // 60
    horas      = minutos  // 60
    dias       = horas    // 24
    semanas    = dias     // 7

    if segundos < 60:
        return "hace un momento"
    elif minutos < 60:
        return f"hace {minutos} minuto{'s' if minutos > 1 else ''}"
    elif horas < 24:
        return f"hace {horas} hora{'s' if horas > 1 else ''}"
    elif dias < 7:
        return f"hace {dias} día{'s' if dias > 1 else ''}"
    else:
        return f"hace {semanas} semana{'s' if semanas > 1 else ''}"