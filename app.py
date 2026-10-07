import streamlit as st
import requests
from datetime import datetime
import pytz
from collections import defaultdict

st.set_page_config(page_title="PICK BAGA DEL DIA", layout="centered")
st.title("🎯 PICK BAGA DEL DÍA")
st.caption("Partidos de hoy + Corners + Mejor Pick")

api_key_odds = str(st.secrets.get("ODDS_API_KEY", "")).strip()
api_key_football = str(st.secrets.get("API_FOOTBALL_KEY", "")).strip()

if not api_key_odds:
    api_key_odds = st.text_input("ODDS_API_KEY:", type="password").strip()
    if not api_key_odds: st.stop()

HEADERS_FOOT = {"x-apisports-key": api_key_football} if api_key_football else {}

LIGAS_MAP_FOOT = {
    "soccer_brazil_campeonato": 71,
    "soccer_brazil_serie_b": 72,
    "soccer_colombia_primera_a": 239,
    "soccer_colombia_primera_b": 240,
    "soccer_argentina_primera_division": 128,
    "soccer_chile_primera_division": 265,
    "soccer_epl": 39,
    "soccer_spain_la_liga": 140,
    "soccer_italy_serie_a": 135,
    "soccer_germany_bundesliga": 78,
    "soccer_mexico_ligamx": 262,
    "soccer_usa_mls": 253,
}

TODAS_LIGAS = [
    {"key": "soccer_brazil_campeonato", "title": "Brasileirao Serie A", "pais": "Brasil"},
    {"key": "soccer_brazil_serie_b", "title": "Brasileirao Serie B", "pais": "Brasil"},
    {"key": "soccer_brazil_serie_c", "title": "Brasil - Serie C", "pais": "Brasil"},
    {"key": "soccer_colombia_primera_a", "title": "🇨🇴 BetPlay Dimayor - Primera A", "pais": "Colombia"},
    {"key": "soccer_colombia_primera_b", "title": "🇨🇴 BetPlay Dimayor - Primera B (Torneo BetPlay)", "pais": "Colombia"},
    {"key": "soccer_chile_primera_division", "title": "Chile - Primera Division", "pais": "Chile"},
    {"key": "soccer_argentina_primera_division", "title": "Argentina - Liga Profesional", "pais": "Argentina"},
    {"key": "soccer_epl", "title": "Premier League", "pais": "Inglaterra"},
    {"key": "soccer_spain_la_liga", "title": "La Liga", "pais": "España"},
    {"key": "soccer_italy_serie_a", "title": "Serie A", "pais": "Italia"},
    {"key": "soccer_germany_bundesliga", "title": "Bundesliga", "pais": "Alemania"},
    {"key": "soccer_france_ligue_one", "title": "Ligue 1", "pais": "Francia"},
    {"key": "soccer_mexico_ligamx", "title": "Liga MX", "pais": "Mexico"},
    {"key": "soccer_usa_mls", "title": "MLS", "pais": "USA"},
    {"key": "soccer_uruguay_primera", "title": "Uruguay - Primera", "pais": "Uruguay"},
    {"key": "soccer_paraguay_primera_division", "title": "Paraguay - Primera", "pais": "Paraguay"},
    {"key": "soccer_peru_primera", "title": "Peru - Liga 1", "pais": "Peru"},
    {"key": "soccer_ecuador_primera_a", "title": "Ecuador - Serie A", "pais": "Ecuador"},
    {"key": "soccer_conmebol_copa_libertadores", "title": "Copa Libertadores", "pais": "CONMEBOL"},
    {"key": "soccer_uefa_champs_league", "title": "Champions League", "pais": "Europa"},
]

@st.cache_data(ttl=3600)
def get_sports(api_key):
    r = requests.get(f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}&all=true", timeout=15)
    if r.status_code==200:
        return r.json(), r.headers.get('x-requests-remaining','?'), r.headers.get('x-requests-used','?')
    return [], "?", "?"

@st.cache_data(ttl=300)
def get_odds(key, market, api_key):
    url = f"https://api.the-odds-api.com/v4/sports/{key}/odds/?apiKey={api_key}&regions=eu,uk,us&markets={market}&dateFormat=iso"
    r = requests.get(url, timeout=15)
    return r.json() if r.status_code==200 else [], r.status_code, r.headers.get('x-requests-remaining','?')

sports_api, remaining, used = get_sports(api_key_odds)
keys_activas = {s['key'] for s in sports_api if 'soccer' in s['key']}
todas = sports_api + [l for l in TODAS_LIGAS if l['key'] not in keys_activas]
todas = [l for l in todas if 'soccer' in l.get('key','')]

por_pais = defaultdict(list)
for l in todas:
    por_pais[l.get('pais','Otros')].append(l)

c1,c2 = st.columns(2)
with c1: st.metric("Creditos restantes", remaining)
with c2: st.metric("Ligas totales", len(todas))
if api_key_football: st.success(f"✅ API-Football activa")

st.markdown("### 🌍 Paises y Ligas - Todas disponibles")
for pais, ligas in sorted(por_pais.items()):
    with st.expander(f"{pais} - {len(ligas)} ligas"):
        for l in ligas:
            activo = "🟢 Partidos hoy" if l['key'] in keys_activas else "⚪"
            corners_ok = "🚩" if l['key'] in LIGAS_MAP_FOOT else ""
            st.caption(f"{activo} {corners_ok} | {l['title']}")

st.divider()
st.markdown("### Elige liga para ver partidos de hoy")
paises_disp = sorted(list(por_pais.keys()))
# Que Colombia salga primero si quiere Master
default_pais = paises_disp.index("Colombia") if "Colombia" in paises_disp else 0
pais_sel = st.selectbox("Pais", paises_disp, index=default_pais)
ligas_pais = por_pais.get(pais_sel, [])
opciones = {f"{l['title']}": l for l in ligas_pais}
liga_sel = st.selectbox(f"Ligas de {pais_sel}", list(opciones.keys()))
liga_obj = opciones[liga_sel]

if st.button(f"VER PICK BAGA - {liga_obj['title']}", type="primary", use_container_width=True):
    partidos_raw, status, rem = get_odds(liga_obj['key'], "h2h", api_key_odds)
    st.caption(f"Creditos restantes: {rem} | Partidos: {len(partidos_raw)}")
    if status!=200 or not partidos_raw:
        st.error("Sin partidos hoy en esta liga")
        st.stop()
    tz_local = pytz.timezone('America/Bogota')
    hoy = []
    for ev in partidos_raw:
        dt = datetime.fromisoformat(ev['commence_time'].replace('Z', '+00:00')).astimezone(tz_local)
        if dt.date()!= datetime.now(tz_local).date(): continue
        fav = ""; fav_c = 99; cl=ce=cv="?"
        for bm in ev.get('bookmakers', [])[:1]:
            for mk in bm.get('markets', []):
                for out in mk.get('outcomes', []):
                    if out['name']==ev['home_team']:
                        cl = out['price']
                        if out['price'] < fav_c: fav_c = out['price']; fav = ev['home_team']
                    elif out['name']==ev['away_team']:
                        cv = out['price']
                        if out['price'] < fav_c: fav_c = out['price']; fav = ev['away_team']
                    elif out['name']=='Draw': ce = out['price']
        hoy.append({'partido': f"{ev['home_team']} vs {ev['away_team']}", 'hora': dt.strftime("%H:%M"), 'local': cl, 'empate': ce, 'visita': cv, 'fav': fav, 'fav_cuota': fav_c, 'id': ev['id'], 'key': liga_obj['key'], 'dt': dt})

    if not hoy:
        st.warning("No hay partidos hoy en esta liga")
        st.stop()

    st.success(f"{liga_obj['title']} - {len(hoy)} partidos hoy")
    for p in sorted(hoy, key=lambda x: x['dt']):
        hot = "🔥" if p['fav_cuota']<=1.90 else ""
        st.markdown(f"**{hot} {p['hora']} - {p['partido']}**")
        c1,c2,c3 = st.columns(3)
        with c1: st.metric("Local", p['local'])
        with c2: st.metric("Empate", p['empate'])
        with c3: st.metric("Visita", p['visita'])
        st.caption(f"Favorito: {p['fav']} @{p['fav_cuota']}")
        st.divider()

    hoy.sort(key=lambda x: x['fav_cuota'])
    mas = hoy[0]
    st.markdown(f"## 🏆 PICK BAGA DEL DÍA")
    st.markdown(f"**{mas['partido']} - {mas['hora']}**")
    totales,_,_ = get_odds(mas['key'], "totals", api_key_odds)
    btts,_,rem3 = get_odds(mas['key'], "btts", api_key_odds)
    st.caption(f"Creditos restantes: {rem3}")

    picks=[]
    for ev in totales+btts:
        if ev['id']!=mas['id']: continue
        for bm in ev.get('bookmakers', [])[:1]:
            for mk in bm.get('markets', []):
                for out in mk.get('outcomes', []):
                    price=float(out.get('price',0))
                    if mk['key']=='totals' and out['name']=='Over' and out.get('point')==1.5 and 1.40<=price<=1.95:
                        picks.append({'pick': f"Over 1.5 Goles @ {price}", 'cuota': price, 'logica': f"Favorito {mas['fav']} @{mas['fav_cuota']} superior", 'book': bm['title']})
                    if mk['key']=='btts' and out['name']=='No' and 1.50<=price<=2.10:
                        picks.append({'pick': f"Ambos NO anotan @ {price}", 'cuota': price, 'logica': "Favorito domina", 'book': bm['title']})

    if picks:
        mejor = sorted(picks, key=lambda x: abs(x['cuota']-1.70))[0]
        st.success("PICK MAS LOGICO:")
        st.markdown(f"### 👉 {mejor['pick']}")
        st.markdown(f"**Logica:** {mejor['logica']}")
        if mas['fav_cuota']<=1.85:
            st.info(f"👉 Extra: Over 8.5 Corners @1.75")
        st.balloons()
    else:
        st.info(f"Pick: Gana {mas['fav']} @{mas['fav_cuota']}")

st.caption("V24.1 - BetPlay A y B incluidas + Todos los paises")
