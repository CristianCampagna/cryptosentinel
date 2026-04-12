import streamlit as st
import feedparser
import requests
import pandas as pd
from datetime  import datetime
from dateutil  import parser as dateparser

# ── Fuentes RSS configuradas ──────────────────────────────────

RSS_FEEDS = {
    "CoinDesk":        "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph":   "https://cointelegraph.com/rss",
    "Decrypt":         "https://decrypt.co/feed",
    "Bitcoin Magazine":"https://bitcoinmagazine.com/feed",
}

COINGECKO_NEWS_URL = "https://api.coingecko.com/api/v3/news"

# Palabras clave para detectar qué monedas menciona una noticia
KEYWORDS_MONEDAS = {
    "BTC":  ["bitcoin", "btc"],
    "ETH":  ["ethereum", "eth", "ether"],
    "XRP":  ["xrp", "ripple"],
    "BNB":  ["bnb", "binance"],
    "SOL":  ["solana", "sol"],
    "ADA":  ["cardano", "ada"],
    "DOGE": ["dogecoin", "doge"],
    "DOT":  ["polkadot", "dot"],
    "MATIC":["polygon", "matic"],
    "AVAX": ["avalanche", "avax"],
}


# ── Función interna: parsear fecha robusta ────────────────────

def _parsear_fecha(fecha_str: str) -> datetime:
    """
    Convierte cualquier formato de fecha string a datetime.

    Los feeds RSS usan formatos distintos según el sitio:
    - "Mon, 12 Apr 2026 14:30:00 +0000"  (RFC 822)
    - "2026-04-12T14:30:00Z"              (ISO 8601)
    - "2026-04-12 14:30:00"               (formato simple)

    dateutil.parser.parse maneja todos estos casos automáticamente.
    Si falla, devuelve la fecha actual para no romper el ordenamiento.
    """
    if not fecha_str:
        return datetime.now()
    try:
        return dateparser.parse(str(fecha_str), ignoretz=True)
    except Exception:
        return datetime.now()


# ── Función interna: detectar monedas en texto ────────────────

def _detectar_monedas(texto: str) -> list[str]:
    """
    Busca menciones de criptomonedas en un texto.
    Devuelve lista de símbolos encontrados (ej: ["BTC", "ETH"]).
    Útil para filtrar noticias por moneda en la UI.
    """
    if not texto:
        return []

    texto_lower = texto.lower()
    encontradas = []

    for simbolo, keywords in KEYWORDS_MONEDAS.items():
        if any(kw in texto_lower for kw in keywords):
            encontradas.append(simbolo)

    return encontradas


# ── Función interna: normalizar noticia ───────────────────────

def _normalizar(titulo: str, url: str, fecha: datetime,
                fuente: str, descripcion: str = "") -> dict:
    """
    Estructura estándar para cualquier noticia,
    independientemente de su fuente original.

    Todos los campos siempre están presentes — nunca None —
    para que la UI no tenga que hacer comprobaciones.
    """
    texto_completo = f"{titulo} {descripcion}"

    return {
        "titulo":      titulo.strip() if titulo else "Sin título",
        "url":         url or "",
        "fecha":       fecha,
        "fuente":      fuente,
        "descripcion": descripcion.strip()[:300] if descripcion else "",
        "monedas":     _detectar_monedas(texto_completo),
        "tipo":        "rss" if fuente in RSS_FEEDS else "coingecko",
    }


# ── Función 1: Noticias desde RSS feeds ───────────────────────

@st.cache_data(ttl=900)  # refresca cada 15 minutos
def get_noticias_rss(max_por_fuente: int = 15) -> list[dict]:
    """
    Lee todos los feeds RSS configurados y devuelve
    una lista unificada de noticias normalizadas.

    Parámetros:
    - max_por_fuente: cuántos artículos traer por cada feed

    Si un feed falla, lo saltea silenciosamente y continúa
    con los demás — el usuario siempre ve algo.
    """
    noticias = []

    for nombre, url in RSS_FEEDS.items():
        try:
            # feedparser maneja el request internamente
            # timeout no está soportado nativamente,
            # usamos requests para tener control del timeout
            response = requests.get(url, timeout=8,
                                    headers={"User-Agent": "CryptoSentinel/1.0"})
            feed = feedparser.parse(response.content)

            entradas = feed.entries[:max_por_fuente]

            for entry in entradas:
                titulo     = entry.get("title", "")
                url_noticia = entry.get("link", "")

                # Fecha: feedparser la devuelve como struct_time o string
                fecha_raw = entry.get("published", "") or entry.get("updated", "")
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    import time
                    fecha = datetime(*entry.published_parsed[:6])
                else:
                    fecha = _parsear_fecha(fecha_raw)

                # Descripción: puede estar en summary o content
                descripcion = ""
                if entry.get("summary"):
                    descripcion = entry.summary
                elif entry.get("content"):
                    descripcion = entry.content[0].get("value", "")

                # Limpiar tags HTML básicos de la descripción
                import re
                descripcion = re.sub(r"<[^>]+>", "", descripcion)

                noticia = _normalizar(titulo, url_noticia, fecha,
                                      nombre, descripcion)
                noticias.append(noticia)

        except requests.exceptions.Timeout:
            # Feed lento — lo saltamos silenciosamente
            continue
        except Exception:
            # Cualquier otro error — seguimos con el próximo feed
            continue

    return noticias


# ── Función 2: Noticias desde CoinGecko ───────────────────────

@st.cache_data(ttl=900)
def get_noticias_coingecko() -> list[dict]:
    """
    Trae noticias desde el endpoint de CoinGecko.
    Complementa los RSS con noticias directamente
    asociadas al ecosistema cripto.
    """
    try:
        response = requests.get(
            COINGECKO_NEWS_URL,
            headers={"Accept": "application/json",
                     "User-Agent": "CryptoSentinel/1.0"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        # CoinGecko devuelve {"data": [...]}
        items = data.get("data", [])

        noticias = []
        for item in items:
            fecha = _parsear_fecha(item.get("created_at", ""))

            noticia = _normalizar(
                titulo      = item.get("title", ""),
                url         = item.get("url", ""),
                fecha       = fecha,
                fuente      = item.get("news_site", "CoinGecko"),
                descripcion = item.get("description", "")
            )
            # Sobrescribir tipo para identificar origen
            noticia["tipo"] = "coingecko"
            noticias.append(noticia)

        return noticias

    except Exception:
        # Si CoinGecko falla, devolvemos lista vacía
        # Los RSS siguen funcionando igual
        return []


# ── Función 3: Feed combinado y unificado ─────────────────────

@st.cache_data(ttl=900)
def get_feed_completo(max_noticias: int = 100) -> pd.DataFrame:
    """
    Combina RSS + CoinGecko en un único DataFrame ordenado
    por fecha descendente (más reciente primero).

    Incluye deduplicación básica por título para evitar
    que la misma noticia aparezca dos veces de distintas fuentes.

    Columnas del DataFrame:
    - titulo:      texto del titular
    - url:         link al artículo completo
    - fecha:       datetime de publicación
    - fuente:      nombre del medio (CoinDesk, Cointelegraph, etc.)
    - descripcion: resumen corto (máx 300 chars)
    - monedas:     lista de símbolos mencionados (["BTC", "ETH"])
    - tipo:        "rss" o "coingecko"
    - hace:        string legible de hace cuánto (ej: "hace 2 horas")
    """
    # Obtener de ambas fuentes en paralelo conceptual
    # (secuencial en la práctica, ambas están cacheadas)
    rss       = get_noticias_rss()
    coingecko = get_noticias_coingecko()

    todas = rss + coingecko

    if not todas:
        return pd.DataFrame()

    df = pd.DataFrame(todas)

    # Deduplicar por título (primeras 60 chars para ser flexible)
    df["titulo_key"] = df["titulo"].str[:60].str.lower().str.strip()
    df = df.drop_duplicates(subset="titulo_key").drop(columns="titulo_key")

    # Ordenar por fecha descendente
    df = df.sort_values("fecha", ascending=False).reset_index(drop=True)

    # Limitar cantidad total
    df = df.head(max_noticias)

    # Agregar columna "hace cuánto" para la UI
    df["hace"] = df["fecha"].apply(_hace_cuanto)

    return df


# ── Función 4: Filtrar por moneda ─────────────────────────────

def filtrar_por_moneda(df: pd.DataFrame, simbolo: str) -> pd.DataFrame:
    """
    Filtra el feed por moneda específica.
    Útil para mostrar noticias relevantes en la página
    de detalle de una moneda.

    Parámetros:
    - df:      DataFrame del feed completo
    - simbolo: ticker en mayúsculas (ej: "BTC")
    """
    if df.empty or not simbolo:
        return df

    return df[df["monedas"].apply(lambda monedas: simbolo in monedas)]


# ── Función 5: Filtrar por fuente ─────────────────────────────

def filtrar_por_fuente(df: pd.DataFrame, fuentes: list[str]) -> pd.DataFrame:
    """
    Filtra el feed para mostrar solo las fuentes seleccionadas.

    Parámetros:
    - df:      DataFrame del feed completo
    - fuentes: lista de nombres de fuentes (ej: ["CoinDesk", "Decrypt"])
    """
    if df.empty or not fuentes:
        return df

    return df[df["fuente"].isin(fuentes)]


# ── Helper: tiempo relativo ───────────────────────────────────

def _hace_cuanto(fecha: datetime) -> str:
    """
    Convierte un datetime a string legible de tiempo relativo.

    Ejemplos:
    - "hace 5 minutos"
    - "hace 2 horas"
    - "hace 3 días"
    - "hace 2 semanas"
    """
    if not isinstance(fecha, datetime):
        return "—"

    ahora     = datetime.now()
    diferencia = ahora - fecha

    segundos  = int(diferencia.total_seconds())
    minutos   = segundos // 60
    horas     = minutos  // 60
    dias      = horas    // 24
    semanas   = dias     // 7

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