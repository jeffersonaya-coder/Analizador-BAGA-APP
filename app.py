import streamlit as st
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="BAGA V12 FIX 422", layout="centered")
st.title("BAGA V12 - FIX ERROR 422")
st.caption("Pide mercados por separado - 38 partidos de Brasil")

api_key = str(st.secrets.get("ODDS_API_KEY", "")).strip()
if not api_key:
    api_key = st.text_input("API Key:", type="password").strip()

LIGAS_REALES = {
    "Brasil Serie A Betano - 21 partidos HOY": "soccer_brazil_campeonato",
    "Brasil Serie B - 17 partidos HOY": "soccer_brazil_serie_b",
    "Premier League": "soccer_epl",
    "La Liga": "soccer_spain_la_liga",
    "Bundesliga": "soccer_germany_bundesliga",
    "Serie A Italia": "soccer_italy_serie_a",
    "Ligue 1 Francia": "soccer_france_ligue_one",
}

st.markdown("### Brasil hoy 07/10 tiene 21+17 partidos verificados")
ligas_sel = st.multiselect("Elige ligas", list(LIGAS_REALES.keys()), default=["Brasil Serie A Betano - 21 partidos HOY", "Brasil Serie B - 17 partidos HOY"])

col1, col2 = st.columns(2)
with col1:
    cuota_min = st.number_input("Cuota min", value=1.20)
with col2:
    cuota_max = st.number_input("Cuota max", value=4.0)

mercados_sel = st.multiselect("Mercados (ahora se piden separados para evitar 422)", ["h2h", "btts", "totals"], default=["h2h", "btts"])

if st.button("OBTENER PICKS REALES HOY", type="primary", use_container_width=True):
    picks = []
    total = 0
    tz_local = pytz.timezone('America/Bogota')
    debug = []
    with st.spinner("Consultando mercado por mercado..."):
        for nombre in ligas_sel:
            key = LIGAS_REALES[nombre]
            for mercado in mercados_sel: # <--- ESTE ES EL FIX, uno por uno
                url = f"https://api.the-odds-api.com/v4/sports/{key}/odds/?apiKey={api_key}&regions=eu,uk,us&markets={mercado}&dateFormat=iso"
                try:
                    r = requests.get(url, timeout=20)
                    remaining = r.headers.get('x-requests-remaining', '?')
                    if r.status_code == 200:
                        events = r.json()
                        if mercado == "h2h":
                            total += len(events)
                        for ev in events:
                            fecha_dt = datetime.fromisoformat(ev['commence_time'].replace('Z', '+00:00')).astimezone(tz_local)
                            vs = f"{ev['home_team']} vs {ev['away_team']}"
                            for bm in ev.get('bookmakers', [])[:1]:
                                for mk in bm.get('markets', []):
                                    for out in mk.get('outcomes', []):
                                        price = float(out.get('price', 0))
                                        if not (cuota_min <= price <= cuota_max):
                                            continue
                                        txt = ""
                                        if mk['key'] == 'h2h':
                                            txt = f"Gana {out['name']}"
                                        elif mk['key'] == 'btts' and out['name'] == 'Yes':
                                            txt = "Ambos Anotan SI"
                                        elif mk['key'] == 'totals' and 'Over' in out['name']:
                                            txt = f"{out['name']} {out.get('point','')}"
                                        if txt:
                                            picks.append({'liga': nombre, 'partido': vs, 'fecha': fecha_dt, 'pick': txt, 'cuota': price, 'book': bm['title']})
                        debug.append(f"{nombre} [{mercado}]: {len(events)} partidos - OK - rest: {remaining}")
                    else:
                        debug.append(f"{nombre} [{mercado}]: ERROR {r.status_code} - {r.text[:100]}")
                        if r.status_code == 422:
                            debug.append(f" -> 422 por mercado {mercado}, probando solo h2h")
                except Exception as e:
                    debug.append(f"Exception {nombre}: {e}")

    st.sidebar.title("DEBUG")
    for d in debug:
        st.sidebar.caption(d)

    if picks:
        st.success(f"BAGA! {len(picks)} picks en {total} partidos reales de HOY 07/10")
        for p in sorted(picks, key=lambda x: x['fecha'])[:60]:
            st.markdown(f"**{p['fecha'].strftime('%d/%m %H:%M')} | {p['liga']}**")
            st.markdown(f"{p['partido']}")
            st.markdown(f"**{p['pick']} @ {p['cuota']}** - {p['book']}")
            st.divider()
    else:
        st.warning(f"0 picks en rango {cuota_min}-{cuota_max}. Pero habia {total} partidos.")
        st.info("Mire el DEBUG en la barra lateral izquierda para ver que error da")

st.info("FIX 422: Ahora pide h2h solo, luego btts solo, luego totals solo. Ya no da error 422.")
