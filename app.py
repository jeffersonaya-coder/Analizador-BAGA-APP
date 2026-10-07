import streamlit as st
import requests
from datetime import datetime
import pytz
from collections import defaultdict

st.set_page_config(page_title="BAGA V18 TODAS LIGAS", layout="centered")
st.title("🌍 BAGA V18 - TODAS LAS LIGAS DE FUTBOL")
st.caption("Lista completa Odds API 2026 - Incluye Brasileirao A, B, C")

api_key = str(st.secrets.get("ODDS_API_KEY", "")).strip() if "ODDS_API_KEY" in st.secrets else ""
if not api_key:
    api_key = st.text_input("ODDS_API_KEY:", type="password").strip()
    if not api_key:
        st.stop()

# LISTA COMPLETA OFICIAL ODDS API - FUTBOL 2026
# Fuente: api.the-odds-api.com/v4/sports?all=true
TODAS_LIGAS_FUTBOL = [
    # BRASIL - Todas
    {"key": "soccer_brazil_campeonato", "title": "Brasil - Serie A Betano", "pais": "Brasil"},
    {"key": "soccer_brazil_serie_b", "title": "Brasil - Serie B (HOY 17 partidos)", "pais": "Brasil"},
    {"key": "soccer_brazil_serie_c", "title": "Brasil - Serie C", "pais": "Brasil"},
    {"key": "soccer_brazil_cup", "title": "Brasil - Copa do Brasil", "pais": "Brasil"},

    # COLOMBIA - Todas
    {"key": "soccer_colombia_primera_a", "title": "Colombia - Primera A", "pais": "Colombia"},
    {"key": "soccer_colombia_primera_b", "title": "Colombia - Primera B", "pais": "Colombia"},

    # CHILE
    {"key": "soccer_chile_primera_division", "title": "Chile - Primera Division", "pais": "Chile"},
    {"key": "soccer_chile_primera_b", "title": "Chile - Primera B", "pais": "Chile"},
    {"key": "soccer_chile_cup", "title": "Chile - Copa Chile", "pais": "Chile"},

    # ARGENTINA
    {"key": "soccer_argentina_primera_division", "title": "Argentina - Liga Profesional", "pais": "Argentina"},

    # ECUADOR, PERU, URUGUAY, PARAGUAY
    {"key": "soccer_conmebol_copa_libertadores", "title": "CONMEBOL - Libertadores", "pais": "Internacional"},
    {"key": "soccer_conmebol_copa_sudamericana", "title": "CONMEBOL - Sudamericana", "pais": "Internacional"},
    {"key": "soccer_epl", "title": "Inglaterra - Premier League", "pais": "Inglaterra"},
    {"key": "soccer_efl_champ", "title": "Inglaterra - Championship", "pais": "Inglaterra"},
    {"key": "soccer_england_league1", "title": "Inglaterra - League One", "pais": "Inglaterra"},
    {"key": "soccer_england_league2", "title": "Inglaterra - League Two", "pais": "Inglaterra"},
    {"key": "soccer_fa_cup", "title": "Inglaterra - FA Cup", "pais": "Inglaterra"},
    {"key": "soccer_spain_la_liga", "title": "España - La Liga", "pais": "España"},
    {"key": "soccer_spain_segunda_division", "title": "España - La Liga 2", "pais": "España"},
    {"key": "soccer_italy_serie_a", "title": "Italia - Serie A", "pais": "Italia"},
    {"key": "soccer_italy_serie_b", "title": "Italia - Serie B", "pais": "Italia"},
    {"key": "soccer_germany_bundesliga", "title": "Alemania - Bundesliga", "pais": "Alemania"},
    {"key": "soccer_germany_bundesliga2", "title": "Alemania - Bundesliga 2", "pais": "Alemania"},
    {"key": "soccer_france_ligue_one", "title": "Francia - Ligue 1", "pais": "Francia"},
    {"key": "soccer_france_ligue_two", "title": "Francia - Ligue 2", "pais": "Francia"},
    {"key": "soccer_usa_mls", "title": "USA - MLS", "pais": "USA"},
    {"key": "soccer_usa_usl_championship", "title": "USA - USL Championship", "pais": "USA"},
    {"key": "soccer_mexico_ligamx", "title": "Mexico - Liga MX", "pais": "Mexico"},
    {"key": "soccer_portugal_primeira_liga", "title": "Portugal - Primeira Liga", "pais": "Portugal"},
    {"key": "soccer_netherlands_eredivisie", "title": "Holanda - Eredivisie", "pais": "Holanda"},
    {"key": "soccer_japan_j_league", "title": "Japon - J League", "pais": "Japon"},
    {"key": "soccer_china_superleague", "title": "China - Super League", "pais": "China"},
    {"key": "soccer_australia_aleague", "title": "Australia - A-League", "pais": "Australia"},
    {"key": "soccer_uefa_champs_league", "title": "UEFA - Champions League", "pais": "Internacional"},
    {"key": "soccer_uefa_europa_league", "title": "UEFA - Europa League", "pais": "Internacional"},
    {"key": "soccer_uefa_europa_conference_league", "title": "UEFA - Conference League", "pais": "Internacional"},
]

@st.cache_data(ttl=3600)
def get_active_sports(api_key):
    try:
        r = requests.get(f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}&all=true", timeout=15)
        if r.status_code == 200:
            return r.json(), r.headers.get('x-requests-remaining', '?')
    except:
        pass
    return [], "?"

with st.spinner("Cargando todas las ligas activas HOY..."):
    activas_api, remaining = get_active_sports(api_key)
    # Merge: activas de API + manuales completas
    keys_activas = {s['key'] for s in activas_api if 'soccer' in s['key']}
    # Añadir todas las manuales aunque no esten activas hoy para que siempre aparezcan
    todas = activas_api + [l for l in TODAS_LIGAS_FUTBOL if l['key'] not in keys_activas]
    # Filtrar solo soccer
    todas = [l for l in todas if 'soccer' in l.get('key','')]

por_pais = defaultdict(list)
for l in todas:
    pais = l.get('pais', 'Otros')
    if 'pais' not in l:
        # Detectar pais por titulo si no tiene
        t = l.get('title','')
        if 'Brazil' in t or 'Brasil' in t: pais = 'Brasil'
        elif 'Colombia' in t: pais = 'Colombia'
        elif 'Chile' in t: pais = 'Chile'
        elif 'EPL' in t or 'England' in t or 'EFL' in t: pais = 'Inglaterra'
        elif 'Spain' in t or 'La Liga' in t: pais = 'España'
        elif 'Italy' in t: pais = 'Italia'
        elif 'Germany' in t: pais = 'Alemania'
        else: pais = 'Otros'
    por_pais[pais].append(l)

st.success(f"{len(todas)} ligas de futbol totales. Creditos restantes: {remaining}")
st.markdown("### 1. 🌍 Zona Paises - TODAS")
for pais, ligas in por_pais.items():
    with st.expander(f"{pais} - {len(ligas)} ligas"):
        for l in ligas:
            activo = "🟢 HOY" if l['key'] in keys_activas else "⚪"
            st.caption(f"{activo} {l['title']} | {l['key']}")

st.markdown("### 2. Elige pais y liga para filtro BAGA")
paises = sorted(list(por_pais.keys()))
pais_sel = st.selectbox("Pais", options=paises, index=paises.index("Brasil") if "Brasil" in paises else 0)

ligas_pais = por_pais.get(pais_sel, [])
opciones = {f"{l['title']}": l for l in ligas_pais}
liga_sel = st.selectbox(f"Ligas de {pais_sel}", options=list(opciones.keys()))
liga_obj = opciones[liga_sel]

if st.button("BUSCAR PARTIDO MAS INTERESANTE", type="primary", use_container_width=True):
    tz_local = pytz.timezone('America/Bogota')
    url = f"https://api.the-odds-api.com/v4/sports/{liga_obj['key']}/odds/?apiKey={api_key}&regions=eu,uk,us&markets=h2h&dateFormat=iso"
    r = requests.get(url, timeout=15)
    if r.status_code!= 200:
        st.error(f"Hoy {liga_obj['title']} no tiene cuotas (la API la desactivo). Prueba Brasil Serie A y Serie B que si tienen partidos hoy.")
        st.stop()
    partidos = []
    for ev in r.json():
        dt = datetime.fromisoformat(ev['commence_time'].replace('Z', '+00:00')).astimezone(tz_local)
        if dt.date()!= datetime.now(tz_local).date(): continue
        for bm in ev.get('bookmakers', [])[:1]:
            for mk in bm.get('markets', []):
                precios = [(float(o['price']), o['name']) for o in mk.get('outcomes', []) if o['name']!= 'Draw']
                if precios:
                    precios.sort()
                    partidos.append({'partido': f"{ev['home_team']} vs {ev['away_team']}", 'fav': precios[0][1], 'cuota': precios[0][0], 'id': ev['id'], 'fecha': dt, 'key': liga_obj['key']})
    if partidos:
        partidos.sort(key=lambda x: x['cuota'])
        st.success(f"Partido mas interesante: {partidos[0]['partido']} - Fav {partidos[0]['fav']} @{partidos[0]['cuota']}")
        st.balloons()
    else:
        st.warning("No hay partidos hoy en esa liga")
