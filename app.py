import streamlit as st
import requests
from datetime import datetime
import pytz
from collections import defaultdict

st.set_page_config(page_title="BAGA V10 DEBUG", layout="centered")
st.title("BAGA V10 - DEBUG ULTRA")
st.caption("Esta version le dice EXACTAMENTE que devuelve la API")

api_key = str(st.secrets.get("ODDS_API_KEY", "")).strip()
if not api_key:
    api_key = st.text_input("API Key:", type="password").strip()

if api_key:
    # Probamos ligas que SI deberian tener hoy segun usted
    LIGAS_A_PROBAR = {
        "Primera B Colombia": "soccer_colombia_primera_b",
        "Serie A Brasil": "soccer_brazil_campeonato",
        "Serie B Brasil": "soccer_brazil_serie_b",
        "Copa Chile": "soccer_chile_cup",
        "China League One": "soccer_china_league_one",
        "USL League One": "soccer_usa_usl_league_one",
        "EPL (prueba control)": "soccer_epl"
    }

    cuota_min = st.number_input("Cuota min", value=1.20)
    cuota_max = st.number_input("Cuota max", value=3.0)
    mercados = st.multiselect("Mercados", ["h2h", "btts", "totals"], default=["h2h"])

    if st.button("PROBAR CON DEBUG", type="primary", use_container_width=True):
        tz_local = pytz.timezone('America/Bogota')
        for nombre, key in LIGAS_A_PROBAR.items():
            st.divider()
            st.markdown(f"### Probando: {nombre} -> `{key}`")
            # Probamos con TODAS las regiones, no solo eu,uk
            for region in ["eu,uk,us", "eu,uk", "us", "uk"]:
                url = f"https://api.the-odds-api.com/v4/sports/{key}/odds/?apiKey={api_key}&regions={region}&markets={','.join(mercados)}&dateFormat=iso"
                try:
                    r = requests.get(url, timeout=15)
                    remaining = r.headers.get('x-requests-remaining', '?')
                    used = r.headers.get('x-requests-used', '?')
                    st.write(f"Region {region} -> Status: {r.status_code} | Restantes: {remaining} | Usados: {used}")
                    if r.status_code == 200:
                        data = r.json()
                        st.write(f"Partidos encontrados: {len(data)}")
                        if len(data) > 0:
                            for ev in data[:2]: # muestra 2
                                dt = datetime.fromisoformat(ev['commence_time'].replace('Z', '+00:00')).astimezone(tz_local)
                                st.success(f"{ev['home_team']} vs {ev['away_team']} - {dt.strftime('%d/%m %H:%M')} - bookies: {len(ev.get('bookmakers',[]))}")
                            break
                        else:
                            st.warning("Vacio en esta region")
                    elif r.status_code == 401:
                        st.error(f"401 - API Key mala o sin creditos: {r.text[:200]}")
                        break
                    elif r.status_code == 422:
                        st.error(f"422 - Key invalida para esta liga: {r.text[:200]}")
                    else:
                        st.error(f"Error {r.status_code}: {r.text[:200]}")
                except Exception as e:
                    st.error(f"Exception: {e}")

        st.markdown("---")
        st.info("Si TODAS le dan 0 partidos, su API Key no tiene partidos de hoy o se acabaron los creditos. Mande foto de este debug.")
else:
    st.warning("Ponga API Key")
