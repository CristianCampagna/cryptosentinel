import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from utils.alerts import color_variacion

def _hex_a_rgba(hex_color: str, opacidad: float = 0.1) -> str:
    """
    Convierte un color hex a string rgba válido para Plotly.
    Ejemplo: "#FF3B30", 0.1 → "rgba(255,59,48,0.1)"
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{opacidad})"

# ── Tema base para todos los gráficos ────────────────────────
# Centralizar el tema evita inconsistencias visuales entre páginas.
# Si querés cambiar la fuente o el color de fondo,
# lo cambiás acá y se aplica a toda la app.

TEMA = {
    "bg":           "#0E1117",   # fondo del gráfico (mismo que la app)
    "bg_paper":     "#161B22",   # fondo del área de plot
    "grid":         "#21262D",   # color de la grilla
    "texto":        "#FAFAFA",   # color del texto
    "texto_muted":  "#8B949E",   # color del texto secundario
    "naranja":      "#F7931A",   # color primario Bitcoin
    "verde":        "#34C759",
    "rojo":         "#FF3B30",
    "amarillo":     "#FFCC00",
    "cyan":         "#00C7BE",
}

COLORES_SECUENCIA = [
    "#F7931A", "#00C7BE", "#34C759",
    "#FF9500", "#FF3B30", "#BF5AF2",
    "#64D2FF", "#FFD60A", "#FF375F",
]

def _aplicar_tema(fig: go.Figure, titulo: str = "",
                  altura: int = 400) -> go.Figure:
    """
    Aplica el tema oscuro estándar a cualquier figura de Plotly.
    Se llama al final de cada función de gráfico antes de devolver.

    Parámetros:
    - fig:    figura de Plotly a estilizar
    - titulo: título del gráfico (vacío = sin título)
    - altura: altura en píxeles
    """
    fig.update_layout(
        title=dict(
            text=titulo,
            font=dict(color=TEMA["texto"], size=15),
            x=0
        ),
        height=altura,
        paper_bgcolor=TEMA["bg"],
        plot_bgcolor=TEMA["bg_paper"],
        font=dict(color=TEMA["texto"], size=12),
        margin=dict(l=0, r=0, t=40 if titulo else 10, b=0),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=TEMA["grid"],
            font=dict(color=TEMA["texto_muted"])
        ),
        xaxis=dict(
            gridcolor=TEMA["grid"],
            zerolinecolor=TEMA["grid"],
            tickfont=dict(color=TEMA["texto_muted"]),
        ),
        yaxis=dict(
            gridcolor=TEMA["grid"],
            zerolinecolor=TEMA["grid"],
            tickfont=dict(color=TEMA["texto_muted"]),
        ),
        hovermode="x unified",
    )
    return fig


# ── Gráfico 1: Precio histórico de una moneda ─────────────────

def chart_precio_historico(df: pd.DataFrame, simbolo: str,
                           color: str = None) -> go.Figure:
    """
    Línea de precio histórico con área rellena debajo.
    El color del área y la línea se adapta a si el período
    es positivo (verde) o negativo (rojo).

    Parámetros:
    - df:      DataFrame con columnas "fecha" y "precio"
    - simbolo: ticker de la moneda para el título
    - color:   color hex forzado (None = auto según rendimiento)
    """
    if df.empty:
        return go.Figure()

    # Determinar color según rendimiento del período
    if color is None:
        variacion = ((df["precio"].iloc[-1] - df["precio"].iloc[0])
                     / df["precio"].iloc[0]) * 100
        color = TEMA["verde"] if variacion >= 0 else TEMA["rojo"]

    fig = go.Figure()

    # Área rellena con opacidad baja
    fig.add_trace(go.Scatter(
        x=df["fecha"],
        y=df["precio"],
        fill="tozeroy",
        fillcolor=_hex_a_rgba(color, 0.1),
        line=dict(color=color, width=2),
        name=simbolo,
        hovertemplate="<b>%{x|%d %b %Y}</b><br>$%{y:,.2f}<extra></extra>"
    ))

    fig = _aplicar_tema(fig, f"{simbolo} — Precio histórico")
    fig.update_layout(showlegend=False)
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")

    return fig


# ── Gráfico 2: Comparación de múltiples monedas ───────────────

def chart_comparacion(df_precios: dict[str, pd.DataFrame]) -> go.Figure:
    """
    Compara múltiples monedas normalizadas a base 100.
    Normalizar permite comparar movimientos relativos
    sin importar el precio absoluto de cada moneda.

    Parámetros:
    - df_precios: dict {simbolo: DataFrame con columnas fecha/precio}
    """
    fig = go.Figure()

    for i, (simbolo, df) in enumerate(df_precios.items()):
        if df.empty:
            continue

        # Normalizar a base 100
        base   = df["precio"].iloc[0]
        valores = (df["precio"] / base) * 100

        color = COLORES_SECUENCIA[i % len(COLORES_SECUENCIA)]

        fig.add_trace(go.Scatter(
            x=df["fecha"],
            y=valores,
            name=simbolo,
            line=dict(color=color, width=2),
            hovertemplate=(
                f"<b>{simbolo}</b><br>"
                "%{x|%d %b}<br>"
                "Base 100: %{y:.1f}<extra></extra>"
            )
        ))

    fig = _aplicar_tema(fig, "Comparación de rendimiento (base 100)", altura=420)
    fig.add_hline(y=100, line_dash="dash",
                  line_color=TEMA["texto_muted"],
                  annotation_text="Base",
                  annotation_font_color=TEMA["texto_muted"])
    fig.update_yaxes(ticksuffix="")

    return fig


# ── Gráfico 3: Fear & Greed histórico ────────────────────────

def chart_fear_greed(df: pd.DataFrame) -> go.Figure:
    """
    Gráfico de área del Fear & Greed histórico con zonas
    coloreadas según el nivel de sentimiento.

    El color de la línea y el área cambia dinámicamente
    según el valor — no es un color fijo.

    Parámetros:
    - df: DataFrame de get_fear_greed_historico()
          con columnas fecha, valor, color
    """
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    # Línea principal
    fig.add_trace(go.Scatter(
        x=df["fecha"],
        y=df["valor"],
        mode="lines",
        line=dict(color=TEMA["naranja"], width=2),
        fill="tozeroy",
        fillcolor="rgba(247,147,26,0.1)",
        name="Fear & Greed",
        hovertemplate=(
            "<b>%{x|%d %b %Y}</b><br>"
            "Índice: %{y}<extra></extra>"
        )
    ))

    # Líneas de referencia para cada zona
    zonas = [
        (25,  TEMA["rojo"],    "Miedo extremo"),
        (50,  TEMA["amarillo"],"Neutral"),
        (75,  TEMA["verde"],   "Codicia extrema"),
    ]
    for y_val, color, label in zonas:
        fig.add_hline(
            y=y_val,
            line_dash="dot",
            line_color=color,
            line_width=1,
            annotation_text=label,
            annotation_position="right",
            annotation_font_color=color,
            annotation_font_size=11,
        )

    fig = _aplicar_tema(fig, "Fear & Greed Index — Histórico", altura=380)
    fig.update_yaxes(range=[0, 100], ticksuffix="")
    fig.update_layout(showlegend=False)

    return fig


# ── Gráfico 4: Gauge del Fear & Greed actual ─────────────────

def chart_gauge_fear_greed(valor: int, color: str) -> go.Figure:
    """
    Indicador tipo velocímetro para el valor actual
    del Fear & Greed Index. Impacto visual inmediato.

    Parámetros:
    - valor: número entre 0 y 100
    - color: hex del color según la zona actual
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        domain={"x": [0, 1], "y": [0, 1]},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickcolor": TEMA["texto_muted"],
                "tickfont":  {"color": TEMA["texto_muted"]},
            },
            "bar":  {"color": color, "thickness": 0.3},
            "bgcolor": TEMA["bg_paper"],
            "bordercolor": TEMA["grid"],
            "steps": [
                {"range": [0,  25], "color": "rgba(255,59,48,0.15)"},
                {"range": [25, 50], "color": "rgba(255,149,0,0.10)"},
                {"range": [50, 75], "color": "rgba(52,199,89,0.10)"},
                {"range": [75,100], "color": "rgba(0,199,190,0.15)"},
            ],
            "threshold": {
                "line":      {"color": color, "width": 3},
                "thickness": 0.8,
                "value":     valor,
            },
        },
        number={"font": {"color": color, "size": 48}},
    ))

    fig.update_layout(
        height=280,
        paper_bgcolor=TEMA["bg"],
        margin=dict(l=20, r=20, t=20, b=10),
        font=dict(color=TEMA["texto"]),
    )

    return fig


# ── Gráfico 5: Heatmap de variaciones del mercado ────────────

def chart_heatmap_mercado(df: pd.DataFrame,
                          columna: str = "price_change_pct_24h") -> go.Figure:
    """
    Heatmap de variaciones del mercado — muestra el mercado
    completo de un vistazo con colores rojo/verde.

    Parámetros:
    - df:      DataFrame de get_top_monedas()
    - columna: qué variación mostrar (24h o 7d)
    """
    if df.empty:
        return go.Figure()

    df_plot = df.copy().dropna(subset=[columna])

    # Escalar el tamaño de cada celda por market cap
    # (monedas más grandes ocupan más espacio visual)
    df_plot["size"] = (
        df_plot["market_cap"]
        .fillna(0)
        .apply(lambda x: max(x, 1))
    )

    fig = px.treemap(
        df_plot,
        path=["symbol"],
        values="size",
        color=columna,
        color_continuous_scale=[
            [0.0,  "#FF3B30"],   # rojo fuerte  (caída > umbral)
            [0.35, "#FF9500"],   # naranja      (caída leve)
            [0.5,  "#1C1C1E"],   # gris oscuro  (neutro)
            [0.65, "#34C759"],   # verde        (suba leve)
            [1.0,  "#00C7BE"],   # cyan         (suba fuerte)
        ],
        color_continuous_midpoint=0,
        custom_data=[columna, "current_price", "market_cap"],
    )

    fig.update_traces(
        texttemplate=(
            "<b>%{label}</b><br>"
            "%{customdata[0]:.1f}%"
        ),
        textfont=dict(color="white", size=13),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Variación: %{customdata[0]:.2f}%<br>"
            "Precio: $%{customdata[1]:,.2f}<br>"
            "Market Cap: $%{customdata[2]:,.0f}"
            "<extra></extra>"
        )
    )

    etiqueta = "24h" if "24h" in columna else "7d"
    fig = _aplicar_tema(fig,
                        f"Heatmap del mercado — variación {etiqueta}",
                        altura=480)
    fig.update_layout(coloraxis_showscale=False)

    return fig


# ── Gráfico 6: Dominancia BTC/ETH ────────────────────────────

def chart_dominancia(dominancia_btc: float,
                     dominancia_eth: float) -> go.Figure:
    """
    Donut chart de dominancia del mercado.
    Muestra la distribución BTC / ETH / Resto.

    Parámetros:
    - dominancia_btc: porcentaje de BTC (ej: 56.9)
    - dominancia_eth: porcentaje de ETH (ej: 12.3)
    """
    resto = max(0, 100 - dominancia_btc - dominancia_eth)

    fig = go.Figure(go.Pie(
        labels=["Bitcoin", "Ethereum", "Resto"],
        values=[dominancia_btc, dominancia_eth, resto],
        hole=0.55,
        marker=dict(
            colors=[TEMA["naranja"], TEMA["cyan"], TEMA["grid"]],
            line=dict(color=TEMA["bg"], width=2)
        ),
        textfont=dict(color="white"),
        hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>"
    ))

    fig.update_layout(
        height=300,
        paper_bgcolor=TEMA["bg"],
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(
            font=dict(color=TEMA["texto_muted"]),
            bgcolor="rgba(0,0,0,0)"
        ),
        annotations=[dict(
            text=f"BTC<br>{dominancia_btc:.1f}%",
            x=0.5, y=0.5,
            font=dict(color=TEMA["naranja"], size=16),
            showarrow=False
        )]
    )

    return fig


# ── Gráfico 7: Portafolio — distribución ─────────────────────

def chart_portafolio_donut(df: pd.DataFrame) -> go.Figure:
    """
    Donut chart de distribución del portafolio por valor actual.

    Parámetros:
    - df: DataFrame con columnas "simbolo" y "valor_actual"
    """
    if df.empty:
        return go.Figure()

    fig = go.Figure(go.Pie(
        labels=df["simbolo"],
        values=df["valor_actual"],
        hole=0.5,
        marker=dict(
            colors=COLORES_SECUENCIA[:len(df)],
            line=dict(color=TEMA["bg"], width=2)
        ),
        textfont=dict(color="white"),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "$%{value:,.2f}<br>"
            "%{percent}<extra></extra>"
        )
    ))

    total = df["valor_actual"].sum()
    fig.update_layout(
        height=320,
        paper_bgcolor=TEMA["bg"],
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(
            font=dict(color=TEMA["texto_muted"]),
            bgcolor="rgba(0,0,0,0)"
        ),
        annotations=[dict(
            text=f"Total<br>${total:,.0f}",
            x=0.5, y=0.5,
            font=dict(color=TEMA["texto"], size=14),
            showarrow=False
        )]
    )

    return fig


# ── Gráfico 8: P&L del portafolio ────────────────────────────

def chart_pnl_barras(df: pd.DataFrame) -> go.Figure:
    """
    Barras horizontales de ganancia/pérdida por posición.
    Verde para ganancia, rojo para pérdida.
    Facilita identificar de un vistazo qué posiciones
    están funcionando y cuáles no.

    Parámetros:
    - df: DataFrame con columnas "simbolo" y "ganancia_pct"
    """
    if df.empty:
        return go.Figure()

    df_sorted = df.sort_values("ganancia_pct", ascending=True)
    colores   = [
        TEMA["verde"] if v >= 0 else TEMA["rojo"]
        for v in df_sorted["ganancia_pct"]
    ]

    fig = go.Figure(go.Bar(
        x=df_sorted["ganancia_pct"],
        y=df_sorted["simbolo"],
        orientation="h",
        marker=dict(color=colores),
        text=[f"{v:+.1f}%" for v in df_sorted["ganancia_pct"]],
        textposition="outside",
        textfont=dict(color=TEMA["texto"]),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "P&L: %{x:+.2f}%<extra></extra>"
        )
    ))

    fig = _aplicar_tema(fig, "Rendimiento por posición (%)", altura=350)
    fig.add_vline(x=0, line_color=TEMA["texto_muted"],
                  line_width=1, line_dash="dash")
    fig.update_xaxes(ticksuffix="%")

    return fig