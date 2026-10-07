import streamlit as st
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="Analizador BAGA V7 PRO", page_icon="⚽", layout="centered")
st.title("⚽ Analizador BAGA V7 PRO")
st.subheader("Elige ligas - Ahorra créditos")
st.caption("Usted elige: 1 liga = 1 crédito | 15 ligas = 15 créditos")

# --- DICCIONARIO COMPLETO DE TODAS LAS LIGAS ---
TODAS_LAS_LIGAS = {
    "Premier League": "soccer_epl",
    "Bundesliga": "soccer_germany_bundesliga",
    "La Liga": "soccer_spain_la_liga",
    "Ligue 1 Francia": "soccer_france_ligue_one",
    "Serie A": "soccer_italy_serie_a",
    "Eredivisie Holanda": "soccer_netherlands_eredivisie",
    "Liga Portugal": "soccer_portugal_primeira_liga",
    "Liga Bélgica": "soccer_belgium_first_div",
    "Superliga Dinamarca": "soccer_denmark_superliga",
    "Championship Inglaterra": "soccer_efl_champ",
    "Brasileirao": "soccer_brazil_campeonato",
    "Liga MX": "soccer_mexico_ligamx",
    "MLS USA": "soccer_usa_mls",
    "Primera A Colombia": "soccer_colombia_primera_a",
    "Primera B Colombia": "soccer_colombia_primera_b",
    "Eliminatorias Sudamérica": "soccer_conmebol_world_cup_qualifiers",
    "Eliminatorias UEFA": "soccer_uefa_euro_qualification",
    "Nations League": "soccer_uefa_nations_league",
}

api_key = str(st.secrets.get("ODDS_API_KEY", "")).strip()
if not api_key:
    api_key = st.text_input("Ingresa tu Odds API Key:", type="password").strip()

# --- SELECTOR INTELIGENTE DE LIGAS ---
st.markdown("### 📋 1. Elige las ligas de HOY")

hoy = datetime.now()
# Pre-selección automática
if hoy.day <= 9 and hoy.month == 10:
    default_ligas = ["Eliminatorias Sudamérica", "Primera A Colombia", "Primera B Colombia"]
else:
    default_ligas = ["Primera A Colombia", "Primera B Colombia", "Bundesliga", "Ligue 1 Francia", "Championship Inglaterra", "Superliga Dinamarca"]

ligas_seleccionadas = st.multiselect(
    f"Selecciona ligas (Cada liga = 1 crédito. Hoy es {hoy.strftime('%d/%m/%Y')})",
    options=list(TODAS_LAS_LIGAS.keys()),
    default=default_ligas
)

st.markdown("### 🎯 2. Elige cuota y mercados")
col1, col2, col3 = st.columns(3)
with col1:
    cuota_min = st.number_input("Cuota min", value=1.50, step=0.05)
with col2:
    cuota_max = st.number_input("Cuota max", value=1.70, step=0.05)
with col3:
    mercados_sel = st.multiselect("Mercados", ["h2h", "btts", "totals"], default=["h2h", "btts", "totals"])

if ligas_seleccionadas:
    st.info(f"✅ Consultarás {len(ligas_seleccionadas)} ligas = {len(ligas_seleccionadas)} créditos | {', '.join(ligas_seleccionadas)}")
else:
    st.warning("Selecciona al menos 1 liga Master")

if st.button("🚀 OBTENER PICKS BAGA", use_container_width=True, type="primary"):
    if not api_key:
        st.error("Falta API Key Master")
        st.stop()
    if not ligas_seleccionadas:
        st.error("Elige al menos 1 liga")
        st.stop()

    picks = []
    total_analizados = 0
    tz_local = pytz.timezone('America/Bogota')
    remaining = "?"

    LIGAS_OBJETIVO = {nombre: TODAS_LAS_LIGAS[nombre] for nombre in ligas_seleccionadas}

    with st.spinner(f"Consultando {len(LIGAS_OBJETIVO)} ligas..."):
        for nombre_liga, sport_key in LIGAS_OBJETIVO.items():
            markets_str = ",".join(mercados_sel) if mercados_sel else "h2h"
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=eu,uk&markets={markets_str}&dateFormat=iso"
            try:
                r = requests.get(url, timeout=20)
                remaining = r.headers.get('x-requests-remaining', '?')
                if r.status_code == 200:
                    events = r.json()
                    total_analizados += len(events)
                    for event in events:
                        fecha_dt = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00')).astimezone(tz_local)
                        vs = f"{event.get('home_team')} vs {event.get('away_team')}"
                        for bm in event.get('bookmakers', [])[:1]:
                            for market in bm.get('markets', []):
                                key = market.get('key')
                                for out in market.get('outcomes', []):
                                    price = float(out.get('price', 0))
                                    if not (cuota_min <= price <= cuota_max):
                                        continue
                                    pick_text = ""
                                    icono = "🏆"
                                    if key == 'h2h':
                                        pick_text = f"Gana {out.get('name')}"
                                        icono = "🏆"
                                    elif key == 'btts' and out.get('name') == 'Yes':
                                        pick_text = "Ambos Anotan: SI"
                                        icono = "⚽"
                                    elif key == 'totals' and 'Over' in str(out.get('name','')) and out.get('point') == 1.5:
                                        pick_text = "Over 1.5 Goles"
                                        icono = "📈"
                                    if pick_text:
                                        picks.append({'liga': nombre_liga, 'partido': vs, 'fecha_dt': fecha_dt, 'pick': pick_text, 'cuota': price, 'bookmaker': bm.get('title'), 'mercado': key.upper(), 'icono': icono})
                elif r.status_code == 401:
                    st.error("❌ 401: Se acabaron los 500 créditos Master")
                    st.stop()
                elif r.status_code in [404, 422]:
                    continue
            except Exception as e:
                continue
        st.sidebar.success(f"Créditos restantes: {remaining}")

    if picks:
        picks = sorted(picks, key=lambda x: x['fecha_dt'])
        st.success(f"¡BAGA! {len(picks)} picks encontrados en {total_analizados} partidos.")
        for liga_nombre in ligas_seleccionadas:
            lista = [p for p in picks if p['liga'] == liga_nombre]
            if lista:
                with st.expander(f"🏆 {liga_nombre} ({len(lista)} picks)", expanded=True):
                    for p in lista:
                        st.markdown(f"**⏰ {p['fecha_dt'].strftime('%d/%m %H:%M')} | {p['partido']}**")
                        st.markdown(f"{p['icono']} **{p['mercado']}: {p['pick']} @ {p['cuota']}**")
                        st.caption(f"📊 {p['bookmaker']}")
                        st.divider()
            else:
                with st.expander(f"🏆 {liga_nombre} (0 picks)", expanded=False):
                    st.caption("No hubo picks en ese rango de cuota hoy")
    else:
        st.warning(f"0 picks @ {cuota_min}-{cuota_max}. Analizados: {total_analizados} partidos hoy.")
        if total_analizados == 0:
            st.error("Si dice 0 partidos es Fecha FIFA o esa liga no juega hoy. Pruebe solo con Primera A y B de Colombia para hoy 07.10")
