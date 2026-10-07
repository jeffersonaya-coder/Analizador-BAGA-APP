import streamlit as st
import requests
from datetime import datetime
import pytz
from collections import defaultdict

st.set_page_config(page_title="BAGA V19 WPLAY", layout="centered")
st.title("🎯 BAGA V19 - LISTA COMPLETA COMO WPLAY")
st.caption("Como su foto 2 - Todos los partidos de la liga hoy")

api_key = str(st.secrets.get("ODDS_API_KEY", "")).strip() if "ODDS_API_KEY" in st.secrets else ""
if not api_key:
    api_key = st.text_input("API Key:", type="password").strip()
    if not api_key:
        st.stop()

LIGAS_BRASIL = [
    {"key": "soccer_brazil_campeonato", "title": "Brasileirao Serie A Betano", "pais": "Brasil"},
    {"key": "soccer_brazil_serie_b", "title": "Brasileirao Serie B", "pais": "Brasil"},
]

@st.cache_data(ttl=300)
def get_partidos(key, api_key):
    url = f"https://api.the-odds-api.com/v4/sports/{key}/odds/?apiKey={api_key}&regions=eu,uk,us&markets=h2h&dateFormat=iso"
    r = requests.get(url, timeout=15)
    return r.json() if r.status_code==200 else [], r.status_code, r.headers.get('x-requests-remaining','?')

st.markdown("### 1. Elige liga")
pais = st.selectbox("Pais", ["Brasil", "Colombia", "Chile"])
if pais == "Brasil":
    opciones = {f"{l['title']}": l for l in LIGAS_BRASIL}
else:
    opciones = {"Colombia Primera A": {"key": "soccer_colombia_primera_a", "title": "Colombia Primera A"}}

liga_nombre = st.selectbox(f"Ligas de {pais}", list(opciones.keys()))
liga_obj = opciones[liga_nombre]

if st.button(f"VER TODOS LOS PARTIDOS DE HOY - {liga_obj['title']}", type="primary", use_container_width=True):
    partidos, status, remaining = get_partidos(liga_obj['key'], api_key)
    st.caption(f"Creditos restantes: {remaining} | Status: {status} | Partidos API: {len(partidos)}")

    if status!=200:
        st.error(f"La liga {liga_obj['title']} hoy no tiene cuotas en Odds API. Use Brasil Serie A/B que si tienen (foto 2)")
        st.stop()

    tz_local = pytz.timezone('America/Bogota')
    hoy = []
    for ev in partidos:
        dt = datetime.fromisoformat(ev['commence_time'].replace('Z', '+00:00')).astimezone(tz_local)
        if dt.date()!= datetime.now(tz_local).date():
            continue
        # Sacar cuotas 1X2
        cuota_local = cuota_empate = cuota_visita = "?"
        fav = ""
        fav_cuota = 99
        for bm in ev.get('bookmakers', [])[:1]:
            for mk in bm.get('markets', []):
                for out in mk.get('outcomes', []):
                    if out['name'] == ev['home_team']:
                        cuota_local = out['price']
                        if cuota_local < fav_cuota:
                            fav_cuota = cuota_local
                            fav = ev['home_team']
                    elif out['name'] == ev['away_team']:
                        cuota_visita = out['price']
                        if cuota_visita < fav_cuota:
                            fav_cuota = cuota_visita
                            fav = ev['away_team']
                    elif out['name'] == 'Draw':
                        cuota_empate = out['price']
        hoy.append({
            'partido': f"{ev['home_team']} vs {ev['away_team']}",
            'hora': dt.strftime("%H:%M"),
            'local': cuota_local,
            'empate': cuota_empate,
            'visita': cuota_visita,
            'fav': fav,
            'fav_cuota': fav_cuota,
            'id': ev['id'],
            'key': liga_obj['key']
        })

    # Mostrar como Wplay - lista completa
    st.success(f"{liga_obj['title']} - Hoy {len(hoy)} partidos")
    st.markdown(f"### {liga_obj['title']} - BRASIL - Hoy")

    for p in sorted(hoy, key=lambda x: x['hora']):
        # Marcar el mas interesante
        es_interesante = "🔥" if p['fav_cuota'] <= 1.90 else ""
        st.markdown(f"**{es_interesante} {p['hora']} - {p['partido']}**")
        cols = st.columns(3)
        with cols[0]:
            st.metric("Local", p['local'])
        with cols[1]:
            st.metric("Empate", p['empate'])
        with cols[2]:
            st.metric("Visita", p['visita'])
        st.caption(f"Favorito: {p['fav']} @{p['fav_cuota']} - ID: {p['id'][:8]}")
        st.divider()

    # Ahora el pick BAGA del mas interesante
    if hoy:
        hoy.sort(key=lambda x: x['fav_cuota'])
        mas = hoy[0]
        st.markdown(f"## 🎯 PARTIDO MAS INTERESANTE (su idea)")
        st.markdown(f"**{mas['partido']} - Fav {mas['fav']} @{mas['fav_cuota']}**")
        st.markdown(f"Este es el que en Wplay paga {mas['fav_cuota']} - Le aplicamos filtro BAGA:")

        # Buscar Over 1.5 de ese partido
        url = f"https://api.the-odds-api.com/v4/sports/{mas['key']}/odds/?apiKey={api_key}&regions=eu,uk,us&markets=totals,btts&dateFormat=iso"
        r = requests.get(url, timeout=15)
        picks = []
        if r.status_code==200:
            for ev in r.json():
                if ev['id']!= mas['id']: continue
                for bm in ev.get('bookmakers', [])[:1]:
                    for mk in bm.get('markets', []):
                        for out in mk.get('outcomes', []):
                            price = float(out.get('price',0))
                            if mk['key']=='totals' and out['name']=='Over' and out.get('point')==1.5 and 1.40 <= price <= 1.90:
                                picks.append(f"Over 1.5 Goles @ {price} - {bm['title']}")
                            if mk['key']=='btts' and out['name']=='No' and 1.50 <= price <= 2.10:
                                picks.append(f"Ambos NO @ {price} - {bm['title']}")

        if picks:
            st.success(f"PICK BAGA para {mas['partido']}:")
            for pk in picks[:3]:
                st.markdown(f"👉 **{pk}**")
        else:
            st.info(f"Pick seguro: Gana {mas['fav']} @{mas['fav_cuota']}")

st.caption("V19 - Lista como Wplay + Pick BAGA del mas interesante - Ya incluye Serie B")
