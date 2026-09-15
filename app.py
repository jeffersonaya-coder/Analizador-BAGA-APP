import streamlit as st
import requests
from datetime import datetime
import pytz

# Configuración de la página
st.set_page_config(page_title="Analizador BAGA", page_icon="⚽", layout="centered")

st.title("⚽ Analizador BAGA")
st.subheader("Picks de Alta Efectividad (@1.50 - @1.70)")

# 1. Autenticación con API Key desde Secrets o manual
api_key = st.secrets.get("ODDS_API_KEY", "")

if not api_key:
    api_key = st.text_input("Ingresa tu Odds API Key:", type="password")

if st.button("🚀 OBTENER PICKS DEL DÍA"):
    if not api_key:
        st.error("Por favor, ingresa una API Key válida.")
    else:
        with st.spinner("Consultando partidos y procesando cuotas..."):
            try:
                # Consulta a The Odds API
                url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?apiKey={api_key}&regions=eu,us,uk&markets=h2h,totals&dateFormat=iso"
                response = requests.get(url)
                
                if response.status_code != 200:
                    st.error(f"Error en la API ({response.status_code}). Verifica tu clave o cuota de uso.")
                else:
                    events = response.json()
                    picks_aprobados = []
                    total_analizados = len(events)
                    
                    tz_local = pytz.timezone('America/Bogota')

                    for event in events:
                        liga = event.get('sport_title', 'Otras Ligas')
                        home_team = event.get('home_team')
                        away_team = event.get('away_team')
                        commence_time_str = event.get('commence_time')
                        
                        # Conversión de fecha y hora a zona horaria local
                        fecha_dt = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
                        fecha_local = fecha_dt.astimezone(tz_local)
                        
                        bookmakers = event.get('bookmakers', [])
                        if not bookmakers:
                            continue
                            
                        bm = bookmakers[0]
                        bm_name = bm.get('title', 'Casa principal')
                        
                        for market in bm.get('markets', []):
                            # Filtro BAGA para victorias simples
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

                    # --- SECCIÓN DE RESULTADOS MEJORADA ---
                    if picks_aprobados:
                        st.success(f"¡Análisis completo! {len(picks_aprobados)} partidos aprobados de {total_analizados} analizados.")
                        
                        # Ordenar por fecha y hora cronológica
                        picks_aprobados = sorted(picks_aprobados, key=lambda x: x['fecha_dt'])

                        # Agrupar por Liga
                        ligas_dict = {}
                        for pick in picks_aprobados:
                            lg = pick['liga']
                            if lg not in ligas_dict:
                                ligas_dict[lg] = []
                            ligas_dict[lg].append(pick)

                        # Mostrar agrupado por desplegable de Liga
                        for liga, partidos in ligas_dict.items():
                            with st.expander(f"🏆 {liga} ({len(partidos)} partidos)"):
                                for p in partidos:
                                    hora_str = p['fecha_dt'].strftime("%d/%m - %H:%M")
                                    st.markdown(f"**⏰ {hora_str} | {p['local']} vs {p['visitante']}**")
                                    st.write(f"📌 **Pick:** {p['pick_nombre']} @ **{p['cuota']}**")
                                    st.write(f"📊 **Casa:** {p['bookmaker']}")
                                    st.divider()
                    else:
                        st.warning("No se encontraron partidos que cumplan los criterios BAGA (@1.50 - @1.70) para hoy.")
                        
            except Exception as e:
                st.error(f"Ocurrió un error inesperado al procesar los datos: {e}")
