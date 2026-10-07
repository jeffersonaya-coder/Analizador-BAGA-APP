import streamlit as st
import requests
from datetime import datetime
import pytz
from collections import defaultdict

st.set_page_config(page_title="Analizador BAGA V9 País", page_icon="🌎", layout="centered")
st.title("🌎 Analizador BAGA V9 por País")
st.subheader("Analiza lo que HAY HOY, no lo que adivinamos")
st.caption("Paso 1: Ver qué ligas hay hoy | Paso 2: Analizar picks")

api_key = str(st.secrets.get("ODDS_API_KEY", "")).strip()
if not api_key:
    api_key = st.text_input("Ingresa tu Odds API Key:", type="password").strip()

@st.cache_data(ttl=3600)
def get_ligas_activas_hoy(api_key):
    # Esta es la clave: le pregunta a la API qué deportes existen y cuáles están activos HOY
    url = f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            sports = r.json()
            # Filtrar solo soccer activos
            activos = [s for s in sports if s.get('group') == 'Soccer' and s.get('active') == True]
            return activos, r.headers.get('x-requests-remaining', '?')
        else:
            return [], "?"
    except:
        return [], "?"

if api_key:
    with st.spinner("Consultando a la API qué ligas hay ACTIVAS HOY en el mundo... (1 crédito)"):
        ligas_activas, remaining = get_ligas_activas_hoy(api_key)

    if ligas_activas:
        st.success(f"¡Hay {len(ligas_activas)} ligas de fútbol activas HOY en el mundo! Créditos restantes: {remaining}")

        # Agrupar por país
        por_pais = defaultdict(list)
        for liga in ligas_activas:
            title = liga['title']
            # Intentar sacar país del título
            pais = "Internacional"
            if "Brazil" in title or "Brasileiro" in title: pais = "🇧🇷 Brasil"
            elif "Colombia" in title: pais = "🇨🇴 Colombia"
            elif "Chile" in title: pais = "🇨🇱 Chile"
            elif "USA" in title or "MLS" in title or "USL" in title: pais = "🇺🇸 USA"
            elif "England" in title or "EPL" in title or "EFL" in title: pais = "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra"
            elif "Spain" in title or "La Liga" in title: pais = "🇪🇸 España"
            elif "Germany" in title or "Bundesliga" in title: pais = "🇩🇪 Alemania"
            elif "France" in title or "Ligue 1" in title: pais = "🇫🇷 Francia"
            elif "Italy" in title or "Serie A" in title: pais = "🇮🇹 Italia"
            elif "China" in title: pais = "🇨🇳 China"
            elif "Mexico" in title: pais = "🇲🇽 México"
            elif "Denmark" in title: pais = "🇩🇰 Dinamarca"
            elif "World Cup" in title or "Euro" in title or "Nations" in title or "Friendly" in title: pais = "🌍 Internacional / Eliminatorias"
            else: pais = "🌎 Otros Países"

            por_pais[pais].append(liga)

        st.markdown("### 📋 1. Ligas ACTIVAS HOY por país (detectadas ahora mismo)")
        for pais, ligas in por_pais.items():
            with st.expander(f"{pais} - {len(ligas)} ligas activas hoy"):
                for l in ligas:
                    st.caption(f"✅ {l['title']} | key: `{l['key']}` | {l['description']}")

        # --- SELECTOR POR PAÍS ---
        st.markdown("### 🎯 2. Elige por país qué analizar hoy")
        paises_disponibles = list(por_pais.keys())
        paises_sel = st.multiselect("Elige países (ej: Colombia, Brasil, Chile para hoy 07.10)", options=paises_disponibles, default=["🇨🇴 Colombia", "🇧🇷 Brasil", "🇨🇱 Chile", "🇺🇸 USA", "🌍 Internacional / Eliminatorias"] if "🇨🇴 Colombia" in paises_disponibles else paises_disponibles[:3])

        # Construir lista final de ligas según países elegidos
        ligas_finales = []
        for pais in paises_sel:
            ligas_finales.extend(por_pais[pais])

        # Mostrar checkboxes de ligas finales
        if ligas_finales:
            opciones = {f"{l['title']} ({l['key']})": l['key'] for l in ligas_finales}
            ligas_elegidas_nombres = st.multiselect(f"3. Elige ligas exactas de esos países ({len(ligas_finales)} disponibles hoy)", options=list(opciones.keys()), default=list(opciones.keys())[:6])
            LIGAS_OBJETIVO_KEYS = [opciones[n] for n in ligas_elegidas_nombres]
            LIGAS_OBJETIVO_NOMBRES = {opciones[n]: n for n in ligas_elegidas_nombres}

            st.info(f"Vas a consultar {len(LIGAS_OBJETIVO_KEYS)} ligas = {len(LIGAS_OBJETIVO_KEYS)} créditos")

            col1, col2, col3 = st.columns(3)
            with col1:
                cuota_min = st.number_input("Cuota min", value=1.50, step=0.05)
            with col2:
                cuota_max = st.number_input("Cuota max", value=1.70, step=0.05)
            with col3:
                mercados_sel = st.multiselect("Mercados", ["h2h", "btts", "totals"], default=["h2h", "btts", "totals"])

            if st.button("🚀 OBTENER PICKS DE LO QUE HAY HOY", use_container_width=True, type="primary"):
                picks = []
                total_analizados = 0
                tz_local = pytz.timezone('America/Bogota')
                for sport_key in LIGAS_OBJETIVO_KEYS:
                    markets_str = ",".join(mercados_sel) if mercados_sel else "h2h"
                    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=eu,uk&markets={markets_str}&dateFormat=iso"
                    try:
                        r = requests.get(url, timeout=20)
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
                                            if key == 'h2h':
                                                pick_text = f"Gana {out.get('name')}"
                                            elif key == 'btts' and out.get('name') == 'Yes':
                                                pick_text = "Ambos Anotan: SI"
                                            elif key == 'totals' and 'Over' in str(out.get('name','')) and out.get('point') == 1.5:
                                                pick_text = "Over 1.5 Goles"
                                            if pick_text:
                                                picks.append({'liga': LIGAS_OBJETIVO_NOMBRES[sport_key], 'partido': vs, 'fecha_dt': fecha_dt, 'pick': pick_text, 'cuota': price, 'bookmaker': bm.get('title')})
                    except:
                        continue

                if picks:
                    st.success(f"¡BAGA! {len(picks)} picks en {total_analizados} partidos reales de HOY")
                    for p in sorted(picks, key=lambda x: x['fecha_dt']):
                        st.markdown(f"**⏰ {p['fecha_dt'].strftime('%d/%m %H:%M')} | {p['liga']}**")
                        st.markdown(f"{p['partido']} -> **{p['pick']} @ {p['cuota']}**")
                        st.divider()
                else:
                    st.warning(f"0 picks @ {cuota_min}-{cuota_max}. Pero sí había {total_analizados} partidos hoy. Baja la cuota min a 1.20 para verlos.")
    else:
        st.error("No se pudo obtener ligas activas. Revise API Key o créditos")
else:
    st.warning("Ingrese API Key")
