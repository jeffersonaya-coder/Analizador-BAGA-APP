import streamlit as st
import requests
from datetime import datetime
import pytz
from collections import defaultdict

st.set_page_config(page_title="BAGA V17 FINAL", layout="centered")
st.title("🎯 BAGA V17 FINAL - PARTIDO INTERESANTE")
st.caption("Idea Master: Paises > Ligas > 1 Partido > 1 Pick BAGA - 4 creditos/dia")

# API KEY - Se lee de secrets o caja de texto
api_key = str(st.secrets.get("ODDS_API_KEY", "")).strip() if "ODDS_API_KEY" in st.secrets else ""
if not api_key:
    api_key = st.text_input("Pega tu ODDS_API_KEY aqui:", type="password").strip()
    if not api_key:
        st.warning("Pega tu API Key para continuar")
        st.stop()

# Ligas manuales para que Colombia siempre aparezca
LIGAS_MANUALES = [
    {"key": "soccer_brazil_campeonato", "title": "Brasil - Serie A (21 partidos hoy verificado)", "pais": "Brasil", "group": "Soccer"},
    {"key": "soccer_brazil_serie_b", "title": "Brasil - Serie B (17 partidos hoy verificado)", "pais": "Brasil", "group": "Soccer"},
    {"key": "soccer_colombia_primera_a", "title": "Colombia - Primera A", "pais": "Colombia", "group": "Soccer"},
    {"key": "soccer_colombia_primera_b", "title": "Colombia - Primera B", "pais": "Colombia", "group": "Soccer"},
    {"key": "soccer_chile_primera_division", "title": "Chile - Primera Division", "pais": "Chile", "group": "Soccer"},
    {"key": "soccer_epl", "title": "Inglaterra - Premier League", "pais": "Inglaterra", "group": "Soccer"},
    {"key": "soccer_spain_la_liga", "title": "España - La Liga", "pais": "España", "group": "Soccer"},
]

@st.cache_data(ttl=3600)
def get_sports(api_key):
    try:
        r = requests.get(f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}", timeout=15)
        if r.status_code == 200:
            return r.json(), r.headers.get('x-requests-remaining', '?'), r.headers.get('x-requests-used', '?')
    except:
        pass
    return [], "?", "?"

# Cargar ligas
with st.spinner("Cargando paises (1 credito)..."):
    ligas_api, remaining, used = get_sports(api_key)
    todas_ligas = ligas_api + LIGAS_MANUALES

por_pais = defaultdict(list)
for l in todas_ligas:
    if l.get('group')!= 'Soccer':
        continue
    pais = l.get('pais', 'Otros Paises')
    por_pais[pais].append(l)

# Mostrar creditos
col1, col2 = st.columns(2)
with col1:
    st.metric("Creditos restantes", remaining)
with col2:
    st.metric("Creditos usados", used)

# ZONA 1: PAISES
st.markdown("### 1. 🌍 Zona de Paises (0 creditos)")
paises_lista = sorted(list(por_pais.keys()))
# Poner Colombia y Brasil primero
orden = ["Colombia", "Brasil", "Chile", "Inglaterra", "España"] + [p for p in paises_lista if p not in ["Colombia", "Brasil", "Chile", "Inglaterra", "España"]]
paises_ordenados = [p for p in orden if p in por_pais]
pais_sel = st.selectbox("Elige PAIS", options=paises_ordenados, index=1 if "Brasil" in paises_ordenados else 0)

# ZONA 2: LIGAS
st.markdown(f"### 2. 🏆 Zona de Ligas - {pais_sel} (0 creditos)")
ligas_del_pais = por_pais.get(pais_sel, [])
opciones_liga = {f"{l['title']}": l for l in ligas_del_pais}
if not opciones_liga:
    st.error("No hay ligas en este pais")
    st.stop()

liga_nombre = st.selectbox("Elige LIGA", options=list(opciones_liga.keys()))
liga_obj = opciones_liga[liga_nombre]

st.info(f"Seleccionado: {pais_sel} > {liga_obj['title']} | Hasta aqui solo 1 credito gastado")

if st.button(f"🔍 BUSCAR EL PARTIDO MAS INTERESANTE DE HOY", type="primary", use_container_width=True):
    tz_local = pytz.timezone('America/Bogota')
    partidos_hoy = []

    with st.spinner(f"Credito 2/4: Analizando {liga_obj['title']}..."):
        url = f"https://api.the-odds-api.com/v4/sports/{liga_obj['key']}/odds/?apiKey={api_key}&regions=eu,uk,us&markets=h2h&dateFormat=iso"
        r = requests.get(url, timeout=15)
        remaining2 = r.headers.get('x-requests-remaining', '?')

        if r.status_code!= 200:
            st.error(f"Esta liga hoy no tiene cuotas (Error {r.status_code}). Prueba con Brasil Serie A que hoy si tiene 21 partidos verificados por ti.")
            st.caption(f"Creditos restantes: {remaining2}")
            st.stop()

        for ev in r.json():
            fecha_dt = datetime.fromisoformat(ev['commence_time'].replace('Z', '+00:00')).astimezone(tz_local)
            if fecha_dt.date()!= datetime.now(tz_local).date():
                continue
            for bm in ev.get('bookmakers', [])[:1]:
                for mk in bm.get('markets', []):
                    precios = [(float(o['price']), o['name']) for o in mk.get('outcomes', []) if o['name']!= 'Draw']
                    if precios:
                        precios.sort()
                        fav_cuota, fav_name = precios[0]
                        if len(precios) > 1:
                            partidos_hoy.append({
                                'id': ev['id'], 'partido': f"{ev['home_team']} vs {ev['away_team']}",
                                'fecha': fecha_dt, 'favorito': fav_name, 'cuota_fav': fav_cuota,
                                'diff': precios[1][0] - fav_cuota, 'sport_key': liga_obj['key'],
                                'home': ev['home_team'], 'away': ev['away_team']
                            })

    st.caption(f"Credito 2 gastado. Restantes: {remaining2} | {len(partidos_hoy)} partidos encontrados hoy")

    if not partidos_hoy:
        st.warning("Hoy no hay partidos en esta liga. Elige Brasil Serie A que tiene 21 hoy.")
        st.stop()

    partidos_hoy.sort(key=lambda x: x['cuota_fav'])
    mas_interesante = partidos_hoy[0]

    st.success(f"PARTIDO MAS INTERESANTE DEL DIA:")
    st.markdown(f"## {mas_interesante['partido']}")
    st.markdown(f"**{mas_interesante['fecha'].strftime('%d/%m %H:%M')} - {liga_obj['title']}**")
    st.markdown(f"**Favorito: {mas_interesante['favorito']} @ {mas_interesante['cuota_fav']}** - Diferencia: {mas_interesante['diff']:.2f}")
    st.divider()

    st.markdown(f"### 🧠 Filtro BAGA aplicado a este unico partido")
    picks_baga = []

    for idx, mercado in enumerate(['totals', 'btts'], start=3):
        with st.spinner(f"Credito {idx}/4: Buscando {mercado}..."):
            url = f"https://api.the-odds-api.com/v4/sports/{mas_interesante['sport_key']}/odds/?apiKey={api_key}&regions=eu,uk,us&markets={mercado}&dateFormat=iso"
            try:
                r = requests.get(url, timeout=15)
                rem = r.headers.get('x-requests-remaining', '?')
                st.caption(f"Credito {idx} gastado. Restantes: {rem}")
                if r.status_code == 200:
                    for ev in r.json():
                        if ev['id']!= mas_interesante['id']:
                            continue
                        for bm in ev.get('bookmakers', [])[:1]:
                            for mk in bm.get('markets', []):
                                for out in mk.get('outcomes', []):
                                    price = float(out.get('price', 0))
                                    if not (1.40 <= price <= 2.10):
                                        continue
                                    pick_text = ""
                                    logica = ""
                                    if mk['key'] == 'totals' and out['name'] == 'Over' and out.get('point') == 1.5:
                                        pick_text = "Over 1.5 Goles"
                                        logica = f"Favorito {mas_interesante['favorito']} @{mas_interesante['cuota_fav']} muy fuerte, habra minimo 2 goles"
                                    elif mk['key'] == 'btts' and out['name'] == 'No':
                                        pick_text = "Ambos NO anotan"
                                        logica = f"Favorito superior, rival no marca. Cuota fav {mas_interesante['cuota_fav']} indica dominio"
                                    if pick_text:
                                        if mas_interesante['partido'] not in [p['partido'] for p in picks_baga]:
                                            picks_baga.append({
                                                'partido': mas_interesante['partido'], 'liga': liga_obj['title'],
                                                'fecha': mas_interesante['fecha'], 'favorito': f"{mas_interesante['favorito']} @{mas_interesante['cuota_fav']}",
                                                'pick': pick_text, 'cuota': price, 'logica': logica, 'book': bm['title']
                                            })
            except:
                continue

    if picks_baga:
        mejor = sorted(picks_baga, key=lambda x: abs(x['cuota'] - 1.65))[0]
        st.markdown(f"## ✅ PICK BAGA MAS LOGICO Y ALTAMENTE PROBABLE")
        st.markdown(f"**Partido:** {mejor['partido']}")
        st.markdown(f"**Liga:** {mejor['liga']}")
        st.markdown(f"**Favorito detectado:** {mejor['favorito']}")
        st.markdown(f"### 👉 **{mejor['pick']} @ {mejor['cuota']}**")
        st.markdown(f"**Logica BAGA:** {mejor['logica']}")
        st.markdown(f"**Book:** {mejor['book']}")
        st.balloons()
        st.success(f"GASTO TOTAL: 4 CREDITOS. Te quedan {rem} creditos. Antes gastabas 80!")
    else:
        st.warning("Este partido no tiene Over/BTTS en esta API. Pick seguro:")
        st.markdown(f"**Gana {mas_interesante['favorito']} @ {mas_interesante['cuota_fav']}** - 1X2 directo")

st.caption("V17 FINAL - Copiar y pegar completo - 4 creditos/dia - Zona paises + Zona ligas + Filtro BAGA")
