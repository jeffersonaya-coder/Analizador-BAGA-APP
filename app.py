import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Analizador BAGA V4", page_icon="⚽", layout="centered")

st.title("⚽ Analizador BAGA V4")
st.subheader("Saver Edition - 500 Créditos")
st.caption("Optimizado para no quemar la API Key - Octubre 2026")

# --- LÓGICA INTELIGENTE DE LIGAS SEGÚN FECHA ---
def get_ligas_del_dia():
    hoy = datetime.now()
    dia = hoy.day
    mes = hoy.month
    weekday = hoy.weekday()

    # Fecha FIFA Nations League: 1-6 Octubre y 12-16 Noviembre
    if (mes == 10 and dia <= 6) or (mes == 11 and 12 <= dia <= 16):
        return {
            "UEFA Nations League": "soccer_uefa_nations_league",
            "Premier League": "soccer_epl",
            "La Liga": "soccer_spain_la_liga"
        }
    # Fin de semana: Más volumen con Sudamérica
    elif weekday >= 5:
        return {
            "Premier League": "soccer_epl",
            "La Liga": "soccer_spain_la_liga",
            "Serie A": "soccer_italy_serie_a",
            "Brasileirao": "soccer_brazil_campeonato",
            "Liga Argentina": "soccer_argentina_primera_division"
        }
    # Entre semana
    else:
        return {
            "Premier League": "soccer_epl",
            "La Liga": "soccer_spain_la_liga",
            "Serie A": "soccer_italy_serie_a"
        }

LIGAS_OBJETIVO = get_ligas_del_dia()

# --- API KEY ---
api_key = str(st.secrets.get("ODDS_API_KEY", "")).strip()
if not api_key:
    api_key = st.text_input("Ingresa tu Odds API Key:", type="password").strip()

# --- UI DE FILTROS ---
st.info(f"📅 Hoy {datetime.now().strftime('%d/%m/%Y')} | Analizando: {', '.join(LIGAS_OBJETIVO.keys())} | Costo: {len(LIGAS_OBJETIVO)} créditos")

col1, col2, col3 = st.columns(3)
with col1:
    cuota_min = st.number_input("Cuota min", value=1.50, step=0.05)
with col2:
    cuota_max = st.number_input("Cuota max", value=1.70, step=0.05)
with col3:
    mercados_sel = st.multiselect("Mercados", ["h2h", "btts", "totals"], default=["h2h", "btts", "totals"])

# --- BOTÓN PRINCIPAL ---
if st.button("🚀 OBTENER PICKS BAGA", use_container_width=True):
    if not api_key:
        st.error("Falta API Key Master")
        st.stop()
    
    picks = []
    total_analizados = 0
    tz_local = pytz.timezone('America/Bogota')
    
    now_utc = datetime.now(pytz.utc)
    tomorrow_utc = now_utc + timedelta(hours=24)
    
    with st.spinner(f"Consultando {len(LIGAS_OBJETIVO)} ligas (solo 24h)..."):
        for nombre_liga, sport_key in LIGAS_OBJETIVO.items():
            markets_str = ",".join(mercados_sel) if mercados_sel else "h2h"
           url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=eu,uk&markets={markets_str}&dateFormat=iso"
            try:
                r = requests.get(url, timeout=20)
                remaining = r.headers.get('x-requests-remaining', '?')
                used = r.headers.get('x-requests-used', '?')
                
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
                                    icono = ""
                                    if key == 'h2h':
                                        pick_text = f"Gana {out.get('name')}"
                                        icono = "🏆"
                                    elif key == 'btts' and out.get('name') == 'Yes':
                                        pick_text = "Ambos Anotan: SI"
                                        icono = "⚽"
                                    elif key == 'totals' and 'Over' in str(out.get('name','')) and out.get('point') == 1.5:
                                        pick_text = "Over 1.5 Goles"
                                        icono = "📈"
                                    
                                    if pick_text:
                                        picks.append({
                                            'liga': event.get('sport_title', nombre_liga),
                                            'partido': vs,
                                            'fecha_dt': fecha_dt,
                                            'pick': pick_text,
                                            'cuota': price,
                                            'bookmaker': bm.get('title'),
                                            'mercado': key.upper(),
                                            'icono': icono
                                        })
                
                elif r.status_code == 401:
                    st.error("❌ 401: Se acabaron los 500 créditos o Key inválida")
                    st.stop()
                elif r.status_code == 422:
                    continue
                    
            except Exception as e:
                st.warning(f"Error en {nombre_liga}: {e}")
                continue
        
        # Mostrar créditos al final
        st.sidebar.success(f"Créditos restantes: {remaining} / Usados: {used}")

    # --- RESULTADOS ---
    if picks:
        picks = sorted(picks, key=lambda x: x['fecha_dt'])
        st.success(f"¡BAGA! {len(picks)} picks encontrados en {total_analizados} partidos.")
        
        ligas_dict = {}
        for p in picks:
            ligas_dict.setdefault(p['liga'], []).append(p)
        
        for liga, lista in ligas_dict.items():
            with st.expander(f"🏆 {liga} ({len(lista)} picks)", expanded=True):
                for p in lista:
                    hora = p['fecha_dt'].strftime("%d/%m %H:%M")
                    st.markdown(f"**⏰ {hora} | {p['partido']}**")
                    st.markdown(f"{p['icono']} **{p['mercado']}: {p['pick']} @ {p['cuota']}**")
                    st.caption(f"📊 {p['bookmaker']}")
                    st.divider()
    else:
        st.warning(f"No hay picks @ {cuota_min}-{cuota_max} para las próximas 24h. Analizados: {total_analizados} partidos.")
        st.info("Tip: Si es Lunes/Martes hay pocos partidos, intente mañana o baje a 1.40-1.80")
