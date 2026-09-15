import streamlit as st
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="Analizador BAGA", page_icon="⚽", layout="centered")

st.title("⚽ Analizador BAGA")
st.subheader("Picks de Alta Efectividad (@1.50 - @1.70)")

# 1. Obtener clave de Secrets o Input de manera limpia
api_key = st.secrets.get("ODDS_API_KEY", "").strip()

if not api_key:
    api_key = st.text_input("Ingresa tu Odds API Key:", type="password").strip()

if st.button("🚀 OBTENER PICKS DEL DÍA"):
    if not api_key:
        st.error("Por favor, ingresa una API Key válida.")
    else:
        with st.spinner("Consultando partidos..."):
            try:
                # Consulta a todo el fútbol mundial
                url = "https://api.the-odds-api.com/v4/sports/soccer/odds/"
                    'apiKey': api_key,
                    'regions': 'eu',
                    'markets': 'h2h',
                    'dateFormat': 'iso'
                }
                
                response = requests.get(url, params=params)
                
                if response.status_code == 401:
                    # Diagnóstico visual de la clave enviada
                    masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "Corta"
                    st.error(f"Error 401: La API rechazó la clave enviada ({masked_key}). Verifica el texto exacto en Secrets.")
                elif response.status_code != 200:
                    st.error(f"Error en la API ({response.status_code}): {response.text}")
                else:
                    events = response.json()
                    picks_aprobados = []
                    tz_local = pytz.timezone('America/Bogota')

                    for event in events:
                        liga = event.get('sport_title', 'Otras Ligas')
                        home_team = event.get('home_team')
                        away_team = event.get('away_team')
                        commence_time_str = event.get('commence_time')
                        
                        fecha_dt = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
                        fecha_local = fecha_dt.astimezone(tz_local)
                        
                        for bm in event.get('bookmakers', []):
                            bm_name = bm.get('title', 'Casa')
                            for market in bm.get('markets', []):
                                if market.get('key') == 'h2h':
                                    for outcome in market.get('outcomes', []):
                                        price = outcome.get('price', 0.0)
                                        name = outcome.get('name')
                                        if 1.50 <= price <= 1.70:
                                            picks_aprobados.append({
                                                'liga': liga,
                                                'local': home_team,
                                                'visitante': away_team,
                                                'fecha_dt': fecha_local,
                                                'pick_nombre': f"Victoria de {name}",
                                                'cuota': price,
                                                'bookmaker': bm_name
                                            })

                    if picks_aprobados:
                        st.success(f"¡Análisis completo! {len(picks_aprobados)} partidos aprobados.")
                        picks_aprobados = sorted(picks_aprobados, key=lambda x: x['fecha_dt'])
                        
                        ligas_dict = {}
                        for pick in picks_aprobados:
                            lg = pick['liga']
                            if lg not in ligas_dict:
                                ligas_dict[lg] = []
                            ligas_dict[lg].append(pick)

                        for liga, partidos in ligas_dict.items():
                            with st.expander(f"🏆 {liga} ({len(partidos)} partidos)"):
                                for p in partidos:
                                    hora_str = p['fecha_dt'].strftime("%d/%m - %H:%M")
                                    st.markdown(f"**⏰ {hora_str} | {p['local']} vs {p['visitante']}**")
                                    st.write(f"📌 **Pick:** {p['pick_nombre']} @ **{p['cuota']}**")
                                    st.write(f"📊 **Casa:** {p['bookmaker']}")
                                    st.divider()
                    else:
                        st.warning("No se encontraron partidos en el rango @1.50 - @1.70.")
                        
            except Exception as e:
                st.error(f"Error inesperado: {e}")
