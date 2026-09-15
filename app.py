import streamlit as st
import requests
from datetime import datetime
import pytz

# Configuración de la página en móvil
st.set_page_config(page_title="Analizador BAGA", page_icon="⚽", layout="centered")

st.title("⚽ Analizador BAGA")
st.subheader("Picks de Alta Efectividad (@1.50 - @1.70)")

# Entrada para la API Key
api_key = st.text_input("Ingresa tu Odds API Key:", type="password")

def convertir_hora_local(fecha_utc_str):
    try:
        fecha_utc = datetime.fromisoformat(fecha_utc_str.replace("Z", "+00:00"))
        zona_local = pytz.timezone('America/Bogota')
        fecha_local = fecha_utc.astimezone(zona_local)
        return fecha_local.strftime("%d/%m/%Y - %I:%M %p")
    except Exception:
        return fecha_utc_str

def evaluar_partido(equipo_favorito, cuota_ha, cuota_over, prob_baga):
    if prob_baga < 0.70:
        return {"aprobado": False}

    if cuota_ha and (1.50 <= cuota_ha <= 1.70):
        return {
            "aprobado": True,
            "caso": "FAVORITO SÓLIDO (Alta Efectividad)",
            "pick_conservador": f"Gana {equipo_favorito}",
            "cuota_estimada": f"@{cuota_ha:.2f}",
            "estrategia_betano": f"Victoria Directa de {equipo_favorito} o Apuesta Sin Empate"
        }

    if cuota_over and (1.50 <= cuota_over <= 1.70):
        return {
            "aprobado": True,
            "caso": "PARTIDO DE GOLES (Alta Efectividad)",
            "pick_conservador": "Over 2.5 Goles",
            "cuota_estimada": f"@{cuota_over:.2f}",
            "estrategia_betano": "Over 2.5 Goles / Over 0.5 Goles 1er Tiempo"
        }

    return {"aprobado": False}

LIGAS = [
    ("Brasil Serie A", "soccer_brazil_campeonato"),
    ("Brasil Serie B", "soccer_brazil_serie_b"),
    ("Alemania Bundesliga", "soccer_germany_bundesliga"),
    ("Arabia Saudí Pro League", "soccer_saudi_pro_league"),
    ("Argentina Liga Profesional", "soccer_argentina_primera_division"),
    ("Chile Primera División", "soccer_chile_campeonato"),
    ("Colombia Primera A", "soccer_colombia_primer_a"),
    ("España LaLiga EA Sports", "soccer_spain_la_liga"),
    ("EE.UU. MLS", "soccer_usa_mls"),
    ("Francia Ligue 1", "soccer_france_ligue_one"),
    ("Inglaterra Premier League", "soccer_epl"),
    ("Inglaterra Championship", "soccer_efl_champ"),
    ("Inglaterra EFL Cup", "soccer_england_efl_cup"),
    ("Italia Serie A", "soccer_italy_serie_a"),
    ("México Liga MX", "soccer_mexico_ligamx"),
    ("Noruega Eliteserien", "soccer_norway_eliteserien"),
    ("Países Bajos Eredivisie", "soccer_netherlands_eredivisie"),
    ("Portugal Liga Portugal", "soccer_portugal_primeira_liga"),
    ("Suecia Allsvenskan", "soccer_sweden_allsvenskan"),
    ("Suecia Superettan", "soccer_sweden_superettan"),
    ("Turquía Super Lig", "soccer_turkey_super_league"),
    ("Dinamarca Superliga", "soccer_denmark_superliga"),
    ("Copa Libertadores", "soccer_conmebol_copa_libertadores"),
    ("Copa Sudamericana", "soccer_conmebol_copa_sudamericana"),
    ("Grecia Cup", "soccer_greece_cup")
]

if st.button("🚀 OBTENER PICKS DEL DÍA", use_container_width=True):
    if not api_key:
        st.error("Por favor ingresa tu API Key para continuar.")
    else:
        with st.spinner("Realizando barrido de ligas..."):
            total_partidos = 0
            aprobados = []

            for nombre_liga, key_liga in LIGAS:
                url = f"https://api.the-odds-api.com/v4/sports/{key_liga}/odds/?apiKey={api_key}&regions=eu&markets=h2h,totals"
                respuesta = requests.get(url)

                if respuesta.status_code != 200:
                    continue

                datos = respuesta.json()
                if not datos:
                    continue

                for partido in datos:
                    total_partidos += 1
                    local = partido['home_team']
                    visitante = partido['away_team']
                    fecha_raw = partido.get('commence_time', '')
                    fecha_fmt = convertir_hora_local(fecha_raw) if fecha_raw else "Fecha N/A"

                    cuota_ha = None
                    equipo_favorito = ""
                    cuota_over = None

                    if partido.get('bookmakers'):
                        bm = partido['bookmakers'][0]
                        for m in bm.get('markets', []):
                            if m['key'] == 'h2h':
                                for out in m['outcomes']:
                                    if cuota_ha is None or out['price'] < cuota_ha:
                                        cuota_ha = out['price']
                                        equipo_favorito = out['name']
                            if m['key'] == 'totals':
                                for out in m['outcomes']:
                                    if out.get('name') == 'Over' and out.get('point') == 2.5:
                                        cuota_over = out['price']

                    res = evaluar_partido(equipo_favorito, cuota_ha, cuota_over, 0.75)

                    if res["aprobado"]:
                        aprobados.append({
                            "liga": nombre_liga,
                            "partido": f"{local} vs {visitante}",
                            "fecha": fecha_fmt,
                            "caso": res["caso"],
                            "pick": res["pick_conservador"],
                            "cuota": res["cuota_estimada"],
                            "betano": res["estrategia_betano"]
                        })

            st.success(f"¡Análisis completo! {len(aprobados)} partidos aprobados de {total_partidos} analizados.")

            for p in aprobados:
                with st.expander(f"📌 [{p['liga']}] {p['partido']}"):
                    st.write(f"⏰ **Programado:** {p['fecha']}")
                    st.write(f"📊 **Clasificación:** {p['caso']}")
                    st.write(f"🎯 **Pick Sugerido:** {p['pick']} ({p['cuota']})")
                    st.info(f"💡 **Enfoque Betano:** {p['betano']}")
