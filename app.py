import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

# ─────────────────────────────────────────────
# SAYFA AYARI
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="BIST Sinyal Paneli",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');

:root {
    --bg: #0a0e1a;
    --surface: #111827;
    --surface2: #1a2235;
    --border: #1e2d45;
    --accent: #00d4ff;
    --accent2: #7c3aed;
    --green: #00e676;
    --red: #ff3d57;
    --yellow: #ffd600;
    --text: #e2e8f0;
    --muted: #64748b;
}

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: var(--bg);
    color: var(--text);
}

.stApp { background-color: var(--bg); }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}

/* Metric cards */
.metric-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 8px;
}
.metric-label {
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-family: 'Space Mono', monospace;
}
.metric-value {
    font-size: 22px;
    font-weight: 800;
    margin-top: 4px;
}

/* Signal badge */
.badge-al   { background:#00e67622; color:#00e676; border:1px solid #00e676; padding:3px 12px; border-radius:20px; font-weight:700; font-size:13px; }
.badge-sat  { background:#ff3d5722; color:#ff3d57; border:1px solid #ff3d57; padding:3px 12px; border-radius:20px; font-weight:700; font-size:13px; }
.badge-tut  { background:#ffd60022; color:#ffd600; border:1px solid #ffd600; padding:3px 12px; border-radius:20px; font-weight:700; font-size:13px; }

/* Score bar */
.score-bar-bg { background:var(--border); border-radius:4px; height:8px; width:100%; margin-top:6px; }
.score-bar-fill { height:8px; border-radius:4px; transition:width .3s; }

/* Table */
.dataframe { font-family: 'Space Mono', monospace !important; font-size: 13px !important; }

/* Fav star */
.fav-btn { cursor:pointer; font-size:20px; }

/* Header */
.page-header {
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -1px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
}
.page-sub { color: var(--muted); font-size: 13px; margin-bottom: 24px; font-family:'Space Mono',monospace; }

/* Stop loss chip */
.sl-chip {
    background: #ff3d5711;
    border: 1px solid #ff3d5744;
    color: #ff3d57;
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 12px;
    font-family:'Space Mono',monospace;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HİSSE LİSTESİ
# ─────────────────────────────────────────────
BIST100 = [
    "AGHOL","AGROT","AHGAZ","AKBNK","AKSA","AKSEN","ALARK","ALFAS","ALTNY","ANSGR",
    "AEFES","ANHYT","ARCLK","ARDYZ","ASELS","ASTOR","AVPGY","BTCIM","BSOKE","BERA",
    "BIMAS","BRSAN","BRYAT","CCOLA","CWENE","CANTE","CLEBI","CIMSA","DOHOL","DOAS",
    "EFORC","ECILC","EKGYO","ENJSA","ENERY","ENKAI","EREGL","EUPWR","FROTO","GSRAY",
    "GESAN","GOLTS","GRTHO","GUBRF","SAHOL","HEKTS","IEYHO","ISMEN","KRDMD","KARSN",
    "KTLEV","KCHOL","KONTR","KONYA","KOZAL","KOZAA","LMKDC","MAGEN","MAVI","MIATK",
    "MGROS","MPARK","OBAMS","ODAS","OTKAR","OYAKC","PASEU","PGSUS","PETKM","RALYH",
    "REEDR","RYGYO","SASA","SELEC","SMRTG","SKBNK","SOKM","TABGD","TAVHL","TKFEN",
    "TOASO","TCELL","TUPRS","THYAO","GARAN","HALKB","ISCTR","TSKB","TURSG","SISE",
    "VAKBN","TTKOM","VESTL","YKBNK","CVKMD","ZOREN","PRKAB","EGEEN","TTRAK","YEOTK"
]
EK = ["AKFYE","ASGR","ORGE","HTTBT","SDTTR","OYYAT","NETCAD","VBTYZ","EGEGY","RYSAS","TGSAS","ATATP","KCAER","A1CAP"]
ALL_TICKERS = sorted(list(set(BIST100 + EK)))

# ─────────────────────────────────────────────
# FAVORİ YÖNETİMİ (session state)
# ─────────────────────────────────────────────
if "favorites" not in st.session_state:
    st.session_state.favorites = set()

def toggle_fav(ticker):
    if ticker in st.session_state.favorites:
        st.session_state.favorites.discard(ticker)
    else:
        st.session_state.favorites.add(ticker)

# ─────────────────────────────────────────────
# VERİ ÇEKİMİ
# ─────────────────────────────────────────────
@st.cache_data(ttl=900)
def get_data(ticker: str, period: str = "6mo") -> pd.DataFrame:
    try:
        df = yf.download(f"{ticker}.IS", period=period, interval="1d", progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = df[["Open","High","Low","Close","Volume"]].dropna()
        return df
    except Exception:
        return pd.DataFrame()

# ─────────────────────────────────────────────
# İNDİKATÖRLER
# ─────────────────────────────────────────────
def calc_cmf(df: pd.DataFrame, length: int = 21) -> pd.Series:
    clv = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / (df["High"] - df["Low"] + 1e-9)
    mfv = clv * df["Volume"]
    cmf = mfv.rolling(length).sum() / df["Volume"].rolling(length).sum()
    return cmf

def calc_smi(df: pd.DataFrame, k_len: int = 14, d_len: int = 3, ema_len: int = 3) -> tuple:
    ll = df["Low"].rolling(k_len).min()
    hh = df["High"].rolling(k_len).max()
    mid = (hh + ll) / 2
    diff = df["Close"] - mid
    range_ = (hh - ll) / 2 + 1e-9

    def ema(s, n): return s.ewm(span=n, adjust=False).mean()

    d1 = ema(ema(diff, d_len), d_len)
    r1 = ema(ema(range_, d_len), d_len)
    smi = 100 * d1 / r1
    signal = ema(smi, ema_len)
    return smi, signal

def calc_atr(df: pd.DataFrame, length: int = 21) -> pd.Series:
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"]  - df["Close"].shift()).abs()
    ], axis=1).max(axis=1)
    # RMA (Wilder's smoothing)
    atr = tr.ewm(alpha=1/length, adjust=False).mean()
    return atr

def calc_heikin_ashi(df: pd.DataFrame, ema_len: int = 10, smooth_len: int = 14) -> pd.DataFrame:
    o = df["Open"].ewm(span=ema_len, adjust=False).mean()
    c = df["Close"].ewm(span=ema_len, adjust=False).mean()
    h = df["High"].ewm(span=ema_len, adjust=False).mean()
    l = df["Low"].ewm(span=ema_len, adjust=False).mean()

    ha_close = (o + h + l + c) / 4
    ha_open = pd.Series(index=df.index, dtype=float)
    ha_open.iloc[0] = (o.iloc[0] + c.iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2

    o2 = ha_open.ewm(span=smooth_len, adjust=False).mean()
    c2 = ha_close.ewm(span=smooth_len, adjust=False).mean()
    is_green = c2 >= o2
    return pd.DataFrame({"ha_open": o2, "ha_close": c2, "is_green": is_green}, index=df.index)

def compute_signals(df: pd.DataFrame) -> dict:
    if len(df) < 30:
        return None

    cmf    = calc_cmf(df, 21)
    smi, sig = calc_smi(df, 14, 3, 3)
    atr    = calc_atr(df, 21)
    ha     = calc_heikin_ashi(df, 10, 14)

    last_close = df["Close"].iloc[-1]
    last_atr   = atr.iloc[-1]
    last_cmf   = cmf.iloc[-1]
    last_smi   = smi.iloc[-1]
    prev_smi   = smi.iloc[-2]
    last_ha_green = ha["is_green"].iloc[-1]

    # CMF puanı (33)
    cmf_score = 33 if last_cmf >= 0 else 0

    # SMI puanı (33):
    #   1) SMI -40'ı yukarı keser  VEYA
    #   2) SMI, Signal EMA'yı güçlü yukarı keser (önceki barda SMI <= Signal, şimdi SMI > Signal ve fark > 1)
    prev_sig   = sig.iloc[-2]
    last_sig   = sig.iloc[-1]
    smi_cross_oversold  = (prev_smi <= -40) and (last_smi > -40)
    smi_cross_signal    = (prev_smi <= prev_sig) and (last_smi > last_sig) and ((last_smi - last_sig) > 1)
    smi_score = 33 if (smi_cross_oversold or smi_cross_signal) else 0

    # HA puanı (33)
    ha_score = 33 if last_ha_green else 0

    # ATR puanı (1) — herkese bedava
    atr_score = 1

    total_score = cmf_score + smi_score + ha_score + atr_score

    # Karar
    if total_score >= 75:
        signal = "AL"
    elif total_score >= 33:
        signal = "TUT"
    else:
        signal = "SAT"

    # Stop Loss (sadece AL sinyalinde anlamlı)
    stop_loss = last_close - (last_atr * 2)

    return {
        "close":       float(last_close),
        "cmf":         float(last_cmf),
        "smi":         float(last_smi),
        "ha_green":    bool(last_ha_green),
        "atr":         float(last_atr),
        "cmf_score":   cmf_score,
        "smi_score":   smi_score,
        "ha_score":    ha_score,
        "atr_score":   atr_score,
        "total_score": total_score,
        "signal":      signal,
        "stop_loss":   float(stop_loss),
        "cmf_series":  cmf,
        "smi_series":  smi,
        "sig_series":  sig,
        "atr_series":  atr,
        "ha_df":       ha,
    }

# ─────────────────────────────────────────────
# PANEL: TÜM HİSSELER TABLOSU
# ─────────────────────────────────────────────
def render_table(tickers, only_favs=False):
    rows = []
    prog = st.progress(0, text="Veriler çekiliyor…")
    for i, t in enumerate(tickers):
        prog.progress((i+1)/len(tickers), text=f"{t} işleniyor…")
        df = get_data(t)
        if df.empty:
            continue
        s = compute_signals(df)
        if s is None:
            continue
        if only_favs and t not in st.session_state.favorites:
            continue
        rows.append({
            "⭐":      "⭐" if t in st.session_state.favorites else "☆",
            "Hisse":   t,
            "Fiyat":   round(s["close"], 2),
            "Skor":    s["total_score"],
            "Sinyal":  s["signal"],
            "CMF":     round(s["cmf"], 4),
            "SMI":     round(s["smi"], 2),
            "HA":      "🟢" if s["ha_green"] else "🔴",
            "Stop Loss": round(s["stop_loss"], 2),
        })
    prog.empty()
    if not rows:
        st.info("Gösterilecek hisse bulunamadı.")
        return

    df_table = pd.DataFrame(rows)

    # Renk haritası
    def color_signal(val):
        if val == "AL":  return "color: #00e676; font-weight:700"
        if val == "SAT": return "color: #ff3d57; font-weight:700"
        return "color: #ffd600; font-weight:700"

    def color_score(val):
        if val >= 75: return "color:#00e676"
        if val >= 25: return "color:#ffd600"
        return "color:#ff3d57"

    styled = df_table.style \
        .applymap(color_signal, subset=["Sinyal"]) \
        .applymap(color_score,  subset=["Skor"]) \
        .set_properties(**{"font-family": "Space Mono, monospace", "font-size": "13px"})

    st.dataframe(styled, use_container_width=True, height=600)

    # Hisse seç → detay
    st.markdown("---")
    selected = st.selectbox("Hisse detayını aç:", ["—"] + [r["Hisse"] for r in rows])
    if selected != "—":
        render_detail(selected)

# ─────────────────────────────────────────────
# PANEL: HİSSE DETAY
# ─────────────────────────────────────────────
def render_detail(ticker: str):
    df = get_data(ticker)
    if df.empty:
        st.error("Veri alınamadı.")
        return
    s = compute_signals(df)
    if s is None:
        st.error("Yeterli veri yok.")
        return

    is_fav = ticker in st.session_state.favorites
    fav_label = "⭐ Favoriden Çıkar" if is_fav else "☆ Favorilere Ekle"

    col1, col2, col3, col4 = st.columns([3,1,1,1])
    with col1:
        st.markdown(f"<div class='page-header'>{ticker}.IS</div>", unsafe_allow_html=True)
        sig = s["signal"]
        badge = f"<span class='badge-{sig.lower()}'>{sig}</span>"
        st.markdown(f"Skor: **{s['total_score']}/75** &nbsp; {badge}", unsafe_allow_html=True)
    with col2:
        if st.button(fav_label, key=f"fav_{ticker}"):
            toggle_fav(ticker)
            st.rerun()
    with col3:
        st.metric("Kapanış", f"{s['close']:.2f} ₺")
    with col4:
        st.metric("ATR", f"{s['atr']:.2f}")

    # Stop loss chip
    if s["signal"] == "AL":
        st.markdown(f"🛑 Stop Loss: <span class='sl-chip'>{s['stop_loss']:.2f} ₺</span>  &nbsp;(Fiyat − ATR×2)", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── GRAFIK ──────────────────────────────
    ha_df  = s["ha_df"]
    cmf_s  = s["cmf_series"]
    smi_s  = s["smi_series"]
    sig_s  = s["sig_series"]
    atr_s  = s["atr_series"]
    sl_s   = df["Close"] - atr_s * 2

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        row_heights=[0.45, 0.2, 0.2, 0.15],
        vertical_spacing=0.03,
        subplot_titles=["Smoothed Heiken Ashi + Stop Loss", "CMF (21)", "SMI (14,3,3)", "ATR (21, RMA)"]
    )

    # ── Heiken Ashi mumları ──
    colors = ["#00e676" if g else "#ff3d57" for g in ha_df["is_green"]]
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=ha_df["ha_open"],
        high=ha_df[["ha_open","ha_close"]].max(axis=1),
        low=ha_df[["ha_open","ha_close"]].min(axis=1),
        close=ha_df["ha_close"],
        increasing_line_color="#00e676",
        decreasing_line_color="#ff3d57",
        name="SHA",
    ), row=1, col=1)

    # Stop loss çizgisi
    fig.add_trace(go.Scatter(
        x=df.index, y=sl_s,
        line=dict(color="#ff3d57", width=1, dash="dot"),
        name="Stop Loss",
    ), row=1, col=1)

    # ── CMF ──
    cmf_colors = ["#00e676" if v >= 0 else "#ff3d57" for v in cmf_s]
    fig.add_trace(go.Bar(x=df.index, y=cmf_s, marker_color=cmf_colors, name="CMF"), row=2, col=1)
    fig.add_hline(y=0, line_color="#ffffff44", row=2, col=1)

    # ── SMI ──
    fig.add_trace(go.Scatter(x=df.index, y=smi_s, line=dict(color="#00d4ff", width=1.5), name="SMI"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=sig_s, line=dict(color="#ffd600", width=1, dash="dot"), name="SMI Signal"), row=3, col=1)
    fig.add_hline(y=40,  line_color="#ff3d5766", row=3, col=1)
    fig.add_hline(y=-40, line_color="#00e67666", row=3, col=1)
    fig.add_hline(y=0,   line_color="#ffffff33", row=3, col=1)

    # ── ATR ──
    fig.add_trace(go.Scatter(x=df.index, y=atr_s, line=dict(color="#7c3aed", width=1.5), name="ATR"), row=4, col=1)

    fig.update_layout(
        height=820,
        paper_bgcolor="#0a0e1a",
        plot_bgcolor="#111827",
        font=dict(family="Space Mono, monospace", color="#e2e8f0", size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    for i in range(1, 5):
        fig.update_xaxes(gridcolor="#1e2d45", row=i, col=1)
        fig.update_yaxes(gridcolor="#1e2d45", row=i, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # ── Skor kartları ──
    st.markdown("### İndikatör Skorları")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _score_card("CMF", s["cmf_score"], 33, f"{s['cmf']:.4f}", "≥0 → 33 puan")
    with c2:
        _score_card("SMI", s["smi_score"], 33, f"{s['smi']:.2f}", "-40↑ veya EMA güçlü ↑ → 33")
    with c3:
        _score_card("Heiken Ashi", s["ha_score"], 33, "🟢 Yeşil" if s["ha_green"] else "🔴 Kırmızı", "Yeşil mum → 33 puan")
    with c4:
        _score_card("ATR", s["atr_score"], 1, f"{s['atr']:.2f} ₺", "Herkese 1 puan 🎁")


def _score_card(name, score, max_score, value, hint):
    pct = int(score / max_score * 100) if max_score else 0
    color = "#00e676" if score == max_score else "#ff3d57"
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>{name}</div>
        <div class='metric-value' style='color:{color}'>{score}<span style='font-size:14px;color:#64748b'>/{max_score}</span></div>
        <div style='font-size:12px;color:#94a3b8;margin:4px 0'>{value}</div>
        <div class='score-bar-bg'><div class='score-bar-fill' style='width:{pct}%;background:{color}'></div></div>
        <div style='font-size:10px;color:#475569;margin-top:4px;font-family:Space Mono'>{hint}</div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='font-size:22px;font-weight:800;color:#00d4ff;margin-bottom:4px'>📊 BIST Sinyal</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:11px;color:#64748b;font-family:Space Mono;margin-bottom:20px'>Günlük · yfinance</div>", unsafe_allow_html=True)

    page = st.radio("Sayfa", ["📋 Tüm Hisseler", "⭐ Favorilerim", "🔍 Hisse Ara"])
    st.markdown("---")

    if page == "📋 Tüm Hisseler":
        signal_filter = st.multiselect("Sinyal Filtresi", ["AL","TUT","SAT"], default=["AL","TUT","SAT"])
        show_only_bist = st.checkbox("Sadece BIST 100", value=False)
    elif page == "⭐ Favorilerim":
        st.markdown(f"**{len(st.session_state.favorites)}** hisse favorilendi")
    else:
        search_ticker = st.selectbox("Hisse Seç", ALL_TICKERS)

    st.markdown("---")
    if st.button("🔄 Önbelleği Temizle"):
        st.cache_data.clear()
        st.rerun()

# ─────────────────────────────────────────────
# ANA ALAN
# ─────────────────────────────────────────────
if page == "📋 Tüm Hisseler":
    st.markdown("<div class='page-header'>BIST Sinyal Paneli</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>CMF · SMI · Heiken Ashi · ATR Stop Loss — Günlük</div>", unsafe_allow_html=True)
    tickers = BIST100 if show_only_bist else ALL_TICKERS
    render_table(tickers)

elif page == "⭐ Favorilerim":
    st.markdown("<div class='page-header'>Favorilerim</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Takip ettiğin hisseler</div>", unsafe_allow_html=True)
    if not st.session_state.favorites:
        st.info("Henüz favori hisse eklemedin. Tüm Hisseler tablosundan ⭐ ile ekleyebilirsin.")
    else:
        render_table(list(st.session_state.favorites), only_favs=False)

else:  # Hisse Ara
    st.markdown(f"<div class='page-header'>{search_ticker}</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Hisse detay görünümü</div>", unsafe_allow_html=True)
    render_detail(search_ticker)
