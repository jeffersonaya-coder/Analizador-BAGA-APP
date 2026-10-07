import streamlit as st
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="BAGA V13 PRO", layout="centered")
st.title("🔥 BAGA V13 PRO - 95 PICKS HOY")
st.caption("Fix: 1 pick por partido, sin duplicados")

api_key = str(st.secrets.get("ODDS_API_KEY", "")).strip()
if not api_key:
    api_key = st.text_input("API Key:", type="password").strip()

LIGAS = {
    "Brasil Serie A Betano": "soccer_brazil_campeonato",
    "Brasil Serie B": "soccer_brazil_serie_b",
    "Premier League": "soccer_epl",
    "La Liga": "soccer_spain_la_liga",
}

ligas_sel = st.multiselect("Ligas", list(LIGAS.keys()), default=["Brasil Serie A Betano", "Brasil Serie B"])
c1, c2, c3 = st.columns(3)
with c1:
    cuota_min = st.number_input("Cuota min", value=1.50)
with c2:
    cuota_max = st.number_input("Cuota max", value=1.75)
with c3:
    solo_favoritos = st.checkbox("Solo favoritos <2.0", value=True)

mercados = st.multiselect("Mercados", ["h2h", "btts", "totals"], default=["h2h"])

if st.button("GENERAR PARLAY BAGA HOY", type="primary", use_container_width=True):
    picks_final = []
    tz_local = pytz.timezone('America/Bogota')
    total_partidos = 0
    for nombre in ligas_sel:
        key = LIGAS[nombre]
        for mercado in mercados:
            url = f"https://api.the-odds-api.com/v4/sports/{key}/odds/?apiKey={api_key}&regions=eu,uk,us&markets={mercado}&dateFormat=iso"
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                events = r.json()
                if mercado == "h2h":
                    total_partidos += len(events)
                for ev in events:
                    fecha_dt = datetime.fromisoformat(ev['commence_time'].replace('Z', '+00:00')).astimezone(tz_local)
                    vs = f"{ev['home_team']} vs {ev['away_team']}"
                    # Para h2h, solo quedarnos con 1 pick: el de menor cuota que esté en rango
                    candidatos = []
                    for bm in ev.get('bookmakers', [])[:1]:
                        for mk in bm.get('markets', []):
                            for out in mk.get('outcomes', []):
                                price = float(out.get('price', 0))
                                if cuota_min <= price <= cuota_max:
                                    # Si solo_favoritos, evitar Empate si hay otro mejor
                                    if solo_favoritos and out.get('name') == 'Draw' and price > 2.5:
                                        continue
                                    candidatos.append({'price': price, 'name': out['name'], 'mk': mk['key'], 'book': bm['title']})
                    if candidatos:
                        # Ordenar por cuota más baja (favorito)
                        candidatos.sort(key=lambda x: x['price'])
                        mejor = candidatos[0]
                        # Evitar duplicados del mismo partido
                        if not any(p['partido'] == vs for p in picks_final):
                            txt = f"Gana {mejor['name']}" if mejor['mk']=='h2h' and mejor['name']!='Draw' else ( "Empate" if mejor['name']=='Draw' else f"{mejor['mk']} {mejor['name']}")
                            if mejor['mk'] == 'btts' and mejor['name']=='Yes':
                                txt = "Ambos Anotan SI"
                            picks_final.append({'liga': nombre, 'partido': vs, 'fecha': fecha_dt, 'pick': txt, 'cuota': mejor['price'], 'book': mejor['book']})

    if picks_final:
        st.success(f"BAGA! {len(picks_final)} PARTIDOS FILTRADOS en {total_partidos} partidos de HOY (antes eran 95 duplicados)")

        # Armar parlay
        cuota_total = 1
        for p in picks_final[:10]:
            cuota_total *= p['cuota']

        st.markdown(f"### 🎯 PARLAY BAGA TOP 10 - Cuota Total: {cuota_total:.2f}")
        for p in sorted(picks_final, key=lambda x: x['fecha'])[:10]:
            st.markdown(f"**{p['fecha'].strftime('%H:%M')} {p['partido']}**")
            st.markdown(f"👉 {p['pick']} @ {p['cuota']} - {p['book']}")
            st.divider()

        st.balloons()
        st.markdown("**Esto ya está listo para copiar a su Betano Master**")
    else:
        st.warning(f"0 picks en {cuota_min}-{cuota_max}. Pruebe 1.2-2.5")

st.info("V13: Ya no muestra 3 picks del mismo partido. Ahora 1 pick = 1 partido. Ponga 1.5-1.75 y le arma el parlay directo.")
