import streamlit as st
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="BAGA V11 FINAL", layout="centered")
st.title("BAGA V11 FINAL - Solo ligas reales")
st.caption("07.10.2026 - 38 partidos de Brasil encontrados")

api_key = str(st.secrets.get("ODDS_API_KEY", "")).strip()
if not api_key:
    api_key = st.text_input("API Key:", type="password").strip()

# ESTAS SON LAS UNICAS QUE SI EXISTEN Y DAN 200 HOY - VERIFICADO CON SUS FOTOS
LIGAS_REALES_VERIFICADAS = {
    "Brasil Serie A Betano - 21 partidos HOY": "soccer_brazil_campeonato",
    "Brasil Serie B - 17 partidos HOY": "soccer_brazil_serie_b",
    # Estas son las que Odds API si tiene del resto del mundo
    "Premier League Inglaterra": "soccer_epl",
    "Bundesliga Alemania": "soccer_germany_bundesliga",
    "La Liga Espana": "soccer_spain_la_liga",
    "Serie A Italia": "soccer_italy_serie_a",
    "Ligue 1 Francia": "soccer_france_ligue_one",
    "Eredivisie Holanda": "soccer_netherlands_eredivisie",
    "MLS USA": "soccer_usa_mls",
    "Championship Inglaterra": "soccer_efl_champ",
}

st.markdown("### Hoy 07/10 hay 38 partidos de Brasil (verificado en sus fotos)")
ligas_sel = st.multiselect("Elige ligas que SI existen", list(LIGAS_REALES_VERIFICADAS.keys()), default=["Brasil Serie A Betano - 21 partidos HOY", "Brasil Serie B - 17 partidos HOY"])

col1, col2 = st.columns(2)
with col1:
    cuota_min = st.number_input("Cuota min", value=1.50)
with col2:
    cuota_max = st.number_input("Cuota max", value=2.20)

mercados = st.multiselect("Mercados", ["h2h", "btts", "totals"], default=["h2h", "btts", "totals"])

if st.button("OBTENER PICKS REALES DE HOY", type="primary", use_container_width=True):
    if not api_key:
        st.error("Falta API Key")
        st.stop()
    picks = []
    tz_local = pytz.timezone('America/Bogota')
    total = 0
    with st.spinner("Buscando en ligas verificadas..."):
        for nombre in ligas_sel:
            key = LIGAS_REALES_VERIFICADAS[nombre]
            url = f"https://api.the-odds-api.com/v4/sports/{key}/odds/?apiKey={api_key}&regions=eu,uk,us&markets={','.join(mercados)}&dateFormat=iso&oddsFormat=decimal"
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                events = r.json()
                total += len(events)
                for ev in events:
                    fecha_dt = datetime.fromisoformat(ev['commence_time'].replace('Z', '+00:00')).astimezone(tz_local)
                    # Solo hoy y mañana
                    if (fecha_dt.date() - datetime.now(tz_local).date()).days > 1:
                        continue
                    vs = f"{ev['home_team']} vs {ev['away_team']}"
                    for bm in ev.get('bookmakers', [])[:2]:
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
                                    txt = f"{out['name']} {out.get('point','')} Goles"
                                if txt:
                                    picks.append({'liga': nombre, 'partido': vs, 'fecha': fecha_dt, 'pick': txt, 'cuota': price, 'book': bm['title']})
            else:
                st.error(f"{nombre} error {r.status_code}")

    if picks:
        st.success(f"BAGA! {len(picks)} picks en {total} partidos de HOY")
        for p in sorted(picks, key=lambda x: x['fecha'])[:50]:
            st.markdown(f"**{p['fecha'].strftime('%d/%m %H:%M')} | {p['liga']}**")
            st.markdown(f"{p['partido']}")
            st.markdown(f"**{p['pick']} @ {p['cuota']}** - {p['book']}")
            st.divider()
    else:
        st.warning(f"0 picks en rango {cuota_min}-{cuota_max} pero si habia {total} partidos. Suba cuota max a 3.0")

st.info("NOTA: Primera B Colombia NO existe en The Odds API. Si quiere Colombia, necesitamos cambiar a API-Football (otra API gratis). Pero con Brasil hoy tiene 38 partidos para sacar picks.")
