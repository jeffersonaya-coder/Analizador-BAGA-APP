import streamlit as st
import requests
from datetime import datetime
import pytz
from collections import defaultdict

st.set_page_config(page_title="PICK BAGA DEL DIA", layout="centered")
st.title("🎯 PICK BAGA DEL DÍA")
st.caption("Los partidos de hoy + El mejor pick altamente probable")

api_key = str(st.secrets.get("ODDS_API_KEY", "")).strip() if "ODDS_API_KEY" in st.secrets else ""
if not api_key:
    api_key = st.text_input("ODDS_API_KEY:", type="password").strip()
    if not api_key:
        st.stop()

TODAS_LIGAS = [
    {"key": "soccer_brazil_campeonato", "title": "Brasileirao Serie A", "pais": "Brasil"},
    {"key": "soccer_brazil_serie_b", "title": "Brasileirao Serie B", "pais": "Brasil"},
    {"key": "soccer_brazil_serie_c", "title": "Brasil - Serie C", "pais": "Brasil"},
    {"key": "soccer_colombia_primera_a", "title": "Colombia - Primera A", "pais": "Colombia"},
    {"key": "soccer_colombia_primera_b", "title": "Colombia - Primera B", "pais": "Colombia"},
    {"key": "soccer_chile_primera_division", "title": "Chile - Primera Division", "pais": "Chile"},
    {"key": "soccer_argentina_primera_division", "title": "Argentina - Liga Profesional", "pais": "Argentina"},
    {"key": "soccer_epl", "title": "Premier League", "pais": "Inglaterra"},
    {"key": "soccer_spain_la_liga", "title": "La Liga", "pais": "España"},
    {"key": "soccer_italy_serie_a", "title": "Serie A", "pais": "Italia"},
    {"key": "soccer_germany_bundesliga", "title": "Bundesliga", "pais": "Alemania"},
    {"key": "soccer_mexico_ligamx", "title": "Liga MX", "pais": "Mexico"},
    {"key": "soccer_usa_mls", "title": "MLS", "pais": "USA"},
]

@st.cache_data(ttl=3600)
def get_sports(api_key):
    r = requests.get(f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}&all=true", timeout=15)
    if r.status_code==200:
        return r.json(), r.headers.get('x-requests-remaining','?'), r.headers.get('x-requests-used','?')
    return [], "?", "?"

@st.cache_data(ttl=300)
def get_odds(key, api_key, market):
    url = f"https://api.the-odds-api.com/v4/sports/{key}/odds/?apiKey={api_key}&regions=eu,uk,us&markets={market}&dateFormat=iso"
    r = requests.get(url, timeout=15)
    return r.json() if r.status_code==200 else [], r.status_code, r.headers.get('x-requests-remaining','?')

sports_api, remaining, used = get_sports(api_key)
keys_activas = {s['key'] for s in sports_api if 'soccer' in s['key']}
todas = sports_api + [l for l in TODAS_LIGAS if l['key'] not in keys_activas]
todas = [l for l in todas if 'soccer' in l.get('key','')]

por_pais = defaultdict(list)
for l in todas:
    por_pais[l.get('pais','Otros')].append(l)

# CREDITOS
c1,c2 = st.columns(2)
with c1: st.metric("Creditos restantes", remaining)
with c2: st.metric("Ligas totales", len(todas))

# TODOS LOS PAISES Y LIGAS
st.markdown("### 🌍 Paises y Ligas")
for pais, ligas in sorted(por_pais.items()):
    with st.expander(f"{pais} - {len(ligas)} ligas"):
        for l in ligas:
            activo = "🟢 Partidos hoy" if l['key'] in keys_activas else "⚪"
            st.caption(f"{activo} | {l['title']}")

st.divider()

# ELEGIR
st.markdown("### Elige liga para ver partidos de hoy")
paises_disp = sorted(list(por_pais.keys()))
pais_sel = st.selectbox("Pais", paises_disp, index=paises_disp.index("Brasil") if "Brasil" in paises_disp else 0)
ligas_pais = por_pais.get(pais_sel, [])
opciones = {f"{l['title']}": l for l in ligas_pais}
liga_sel = st.selectbox(f"Ligas de {pais_sel}", list(opciones.keys()))
liga_obj = opciones[liga_sel]

if st.button(f"VER PARTIDOS DE HOY - {liga_obj['title']}", type="primary", use_container_width=True):
    partidos_raw, status, rem = get_odds(liga_obj['key'], api_key, "h2h")
    st.caption(f"Creditos restantes: {rem} | Partidos: {len(partidos_raw)}")
    if status!=200:
        st.error("Sin cuotas hoy, prueba Brasileirao Serie A/B")
        st.stop()

    tz_local = pytz.timezone('America/Bogota')
    hoy = []
    for ev in partidos_raw:
        dt = datetime.fromisoformat(ev['commence_time'].replace('Z', '+00:00')).astimezone(tz_local)
        if dt.date()!= datetime.now(tz_local).date(): continue
        cuota_l = cuota_e = cuota_v = "?"
        fav = ""; fav_c = 99; book_fav = ""
        for bm in ev.get('bookmakers', [])[:1]:
            for mk in bm.get('markets', []):
                for out in mk.get('outcomes', []):
                    if out['name']==ev['home_team']:
                        cuota_l = out['price']
                        if out['price'] < fav_c:
                            fav_c = out['price']; fav = ev['home_team']; book_fav = bm['title']
                    elif out['name']==ev['away_team']:
                        cuota_v = out['price']
                        if out['price'] < fav_c:
                            fav_c = out['price']; fav = ev['away_team']; book_fav = bm['title']
                    elif out['name']=='Draw':
                        cuota_e = out['price']
        hoy.append({'partido': f"{ev['home_team']} vs {ev['away_team']}", 'hora': dt.strftime("%H:%M"), 'local': cuota_l, 'empate': cuota_e, 'visita': cuota_v, 'fav': fav, 'fav_cuota': fav_c, 'book': book_fav, 'id': ev['id'], 'key': liga_obj['key'], 'dt': dt})

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
    st.markdown(f"**Favorito: {mas['fav']} @{mas['fav_cuota']}**")

    totales,_,_ = get_odds(mas['key'], api_key, "totals")
    btts,_,rem3 = get_odds(mas['key'], api_key, "btts")
    st.caption(f"Creditos restantes: {rem3} | Gasto total: 3 creditos")

    picks=[]
    for ev in totales+btts:
        if ev['id']!=mas['id']: continue
        for bm in ev.get('bookmakers', [])[:1]:
            for mk in bm.get('markets', []):
                for out in mk.get('outcomes', []):
                    price=float(out.get('price',0))
                    if mk['key']=='totals' and out['name']=='Over' and out.get('point')==1.5 and 1.40<=price<=1.95:
                        picks.append({'pick': f"Over 1.5 Goles @ {price}", 'cuota': price, 'logica': f"Favorito {mas['fav']} @{mas['fav_cuota']} muy superior, habra minimo 2 goles", 'book': bm['title']})
                    if mk['key']=='btts' and out['name']=='No' and 1.50<=price<=2.10:
                        picks.append({'pick': f"Ambos NO anotan @ {price}", 'cuota': price, 'logica': "Favorito domina, rival no marca", 'book': bm['title']})

    if picks:
        mejor = sorted(picks, key=lambda x: abs(x['cuota']-1.70))[0]
        st.success("PICK MAS LOGICO Y ALTAMENTE PROBABLE:")
        st.markdown(f"### 👉 {mejor['pick']}")
        st.markdown(f"**Logica BAGA:** {mejor['logica']}")
        st.markdown(f"**Book:** {mejor['book']}")
        st.balloons()
    else:
        st.info(f"Pick seguro: Gana {mas['fav']} @{mas['fav_cuota']}")

st.caption("PICK BAGA DEL DIA - V22 - Partidos del dia + Mejor pick")
