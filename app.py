import csv
import io
import math
from datetime import datetime, timedelta
from statistics import pstdev

import pytz
import requests
import streamlit as st

API = "https://api.the-odds-api.com/v4"
AF = "https://v3.football.api-sports.io"
TZ = pytz.timezone("America/Bogota")


# ============================================================ The Odds API
def pedir(ruta, clave, **params):
    """/sports y /events son GRATIS; /odds cuesta mercados x regiones créditos."""
    r = requests.get(f"{API}{ruta}", params={"apiKey": clave, **params}, timeout=25)
    uso = {"restantes": r.headers.get("x-requests-remaining"), "ultimo": r.headers.get("x-requests-last")}
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:160]}")
    return r.json(), uso


@st.cache_data(ttl=6 * 3600)
def ligas_futbol(clave):
    datos, _ = pedir("/sports", clave)  # gratis
    return sorted([(s["key"], s["title"]) for s in datos if s.get("group") == "Soccer" and s.get("active")],
                  key=lambda x: x[1])


def ventana_utc(dia):
    ini = TZ.localize(datetime(dia.year, dia.month, dia.day))
    f = lambda d: d.astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f(ini), f(ini + timedelta(days=1))


@st.cache_data(ttl=900)
def eventos_dia(clave, liga, dia):
    desde, hasta = ventana_utc(dia)
    datos, _ = pedir(f"/sports/{liga}/events", clave, commenceTimeFrom=desde, commenceTimeTo=hasta)  # gratis
    return datos


@st.cache_data(ttl=600)
def cuotas_liga(clave, liga, dia, regiones):
    desde, hasta = ventana_utc(dia)
    return pedir(f"/sports/{liga}/odds", clave, regions=",".join(regiones), markets="h2h", oddsFormat="decimal",
                 commenceTimeFrom=desde, commenceTimeTo=hasta)  # 1 crédito por liga y región


# ============================================================ API-Football (Colombia)
def af(ruta, clave, **params):
    r = requests.get(AF + ruta, headers={"x-apisports-key": clave}, params=params, timeout=25)
    data = r.json()
    if r.status_code != 200 or data.get("errors"):
        raise RuntimeError(f"API-Football: {data.get('errors') or r.status_code}")
    return data


@st.cache_data(ttl=86400)
def ligas_af(clave, pais):
    out = []
    for x in af("/leagues", clave, country=pais, type="league")["response"]:
        temporada = next((s["year"] for s in x.get("seasons", []) if s.get("current")), None)
        if temporada:
            out.append((x["league"]["id"], x["league"]["name"], temporada))
    return out


@st.cache_data(ttl=600)
def eventos_af(clave, liga, temporada, dia, nombre):
    """Convierte partidos + cuotas 'Match Winner' de API-Football al mismo formato que The Odds API."""
    fecha = dia.strftime("%Y-%m-%d")
    fx = af("/fixtures", clave, league=liga, season=temporada, date=fecha, timezone="America/Bogota")["response"]
    info = {f["fixture"]["id"]: f for f in fx}
    if not info:
        return []
    eventos, pagina = {}, 1
    while True:
        d = af("/odds", clave, league=liga, season=temporada, date=fecha, bet=1, page=pagina)
        for item in d["response"]:
            f = info.get(item["fixture"]["id"])
            if not f:
                continue
            h, a = f["teams"]["home"]["name"], f["teams"]["away"]["name"]
            ev = eventos.setdefault(item["fixture"]["id"], {
                "sport_title": nombre, "home_team": h, "away_team": a,
                "commence_time": f["fixture"]["date"], "bookmakers": []})
            for b in item.get("bookmakers", []):
                for bet in b.get("bets", []):
                    if bet.get("id") == 1:
                        nombres = {"Home": h, "Draw": "Draw", "Away": a}
                        ev["bookmakers"].append({"key": b["name"].lower(), "title": b["name"], "markets": [
                            {"key": "h2h", "outcomes": [{"name": nombres.get(v["value"], v["value"]), "price": v["odd"]}
                                                        for v in bet["values"]]}]})
        if pagina >= d.get("paging", {}).get("total", 1):
            break
        pagina += 1
    return list(eventos.values())


# ============================================================ análisis
def quitar_margen(precios, metodo="Shin"):
    """{resultado: cuota} -> {resultado: probabilidad sin margen}. Shin corrige el sesgo de empates/underdogs."""
    inv = {k: 1 / v for k, v in precios.items() if v and v > 1}
    Q = sum(inv.values())
    if not inv or Q <= 0:
        return {}
    if metodo != "Shin" or Q <= 1.0001:
        return {k: v / Q for k, v in inv.items()}

    def p_de(z, q):
        return (math.sqrt(z * z + 4 * (1 - z) * q * q / Q) - z) / (2 * (1 - z))

    lo, hi = 0.0, 0.5
    for _ in range(80):
        mid = (lo + hi) / 2
        if sum(p_de(mid, q) for q in inv.values()) > 1:
            lo = mid
        else:
            hi = mid
    p = {k: p_de((lo + hi) / 2, q) for k, q in inv.items()}
    s = sum(p.values())
    return {k: v / s for k, v in p.items()}


def casas_de(ev):
    return {b.get("title") or b.get("key") for b in ev.get("bookmakers", [])}


def analizar_evento(ev, min_casas=4, tz=None, metodo="Shin", usables=None):
    """La referencia usa TODAS las casas; la mejor cuota solo las casas donde puedes apostar."""
    libros = {}
    for b in ev.get("bookmakers", []):
        for m in b.get("markets", []):
            if m.get("key") == "h2h":
                p = {o["name"]: float(o["price"]) for o in m.get("outcomes", []) if o.get("price")}
                if len(p) >= 2:
                    libros[b.get("title") or b.get("key")] = (b.get("key"), p)
    if len(libros) < min_casas:
        return []
    nombres = set.intersection(*[set(p) for _, p in libros.values()])
    if len(nombres) < 2:
        return []
    probs = {t: quitar_margen(p, metodo) for t, (_, p) in libros.items()}
    pin = [t for t, (k, _) in libros.items() if k == "pinnacle"]
    if pin:
        ref, ref_nombre = {n: probs[pin[0]].get(n, 0) for n in nombres}, "Pinnacle"
    else:
        ref = {n: sum(probs[t].get(n, 0) for t in libros) / len(libros) for n in nombres}
        ref_nombre = f"consenso de {len(libros)} casas"
    hora = None
    if ev.get("commence_time"):
        hora = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
        hora = hora.astimezone(tz) if tz else hora
    filas = []
    for n in sorted(nombres):
        cand = sorted([(t, p[n]) for t, (_, p) in libros.items() if n in p and (not usables or t in usables)],
                      key=lambda x: -x[1])
        pj = ref[n]
        if not cand or pj <= 0:
            continue
        casa, mejor = cand[0]
        segunda = cand[1][1] if len(cand) > 1 else None
        filas.append({
            "hora": hora, "liga": ev.get("sport_title", ""), "local": ev.get("home_team"), "visitante": ev.get("away_team"),
            "pick": "Empate" if n.lower() == "draw" else f"Gana {n}",
            "mejor_cuota": round(mejor, 2), "casa": casa, "segunda_cuota": round(segunda, 2) if segunda else "",
            "aislada": bool(segunda and mejor / segunda - 1 > 0.03),
            "prob_justa": round(pj, 3), "cuota_justa": round(1 / pj, 2), "valor": round(mejor * pj - 1, 3),
            "n_casas": len(libros), "referencia": ref_nombre, "metodo": metodo,
            "dispersion": round(pstdev([probs[t].get(n, 0) for t in libros]), 3),
        })
    return filas


def a_csv(filas):
    if not filas:
        return b""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(filas[0].keys()) + ["consultado"])
    w.writeheader()
    ahora = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    for f in filas:
        w.writerow({**f, "hora": f["hora"].strftime("%Y-%m-%d %H:%M") if f["hora"] else "", "consultado": ahora})
    return buf.getvalue().encode("utf-8")


# ============================================================ interfaz
def main():
    st.set_page_config(page_title="Analizador BAGA", page_icon="⚽", layout="centered")
    st.title("⚽ Analizador BAGA")
    st.caption("Datos de The Odds API (no es OddsPortal). Buscar ligas y partidos es GRATIS; solo traer cuotas gasta créditos.")

    def secreto(n):
        try:
            return str(st.secrets.get(n, "")).strip()
        except Exception:
            return ""

    clave = secreto("ODDS_API_KEY") or st.text_input("Odds API Key:", type="password").strip()
    if not clave:
        st.stop()
    try:
        ligas = ligas_futbol(clave)
    except Exception as e:
        st.error(f"No pude leer las ligas (revisa la clave): {e}")
        st.stop()
    nombres = dict(ligas)

    dia = st.date_input("Día", value=datetime.now(TZ).date())
    buscar = st.text_input("Buscar liga o país (ej. Colombia, Bundesliga)").strip().lower()
    opciones = [k for k, t in ligas if buscar in t.lower() or buscar in k.lower()]
    if buscar and not opciones:
        st.warning(f"The Odds API no lista ninguna liga con «{buscar}». Para Colombia usa la sección de API-Football más abajo.")
    elegidas = st.multiselect("Ligas", opciones, format_func=nombres.get)
    regiones = st.multiselect("Regiones de casas (cada una cuesta 1 crédito por liga)", ["eu", "uk", "us", "au"], default=["eu"])

    if "crudos" not in st.session_state:
        st.session_state["crudos"] = {}
    if st.button("1️⃣ Buscar partidos del día (gratis)"):
        hoy = {}
        for lg in elegidas:
            try:
                ev = eventos_dia(clave, lg, dia)
            except Exception as e:
                st.warning(f"{nombres.get(lg, lg)}: {e}")
                continue
            if ev:
                hoy[lg] = len(ev)
        st.session_state["hoy"] = hoy
    hoy = st.session_state.get("hoy")
    if hoy is not None:
        if not hoy:
            st.warning("Ninguna de las ligas elegidas tiene partidos ese día. No se gastó ningún crédito.")
        else:
            costo = len(hoy) * max(1, len(regiones))
            st.info("Partidos encontrados: " + ", ".join(f"{nombres.get(k, k)} ({n})" for k, n in hoy.items()))
            if st.button(f"2️⃣ Traer cuotas (costará {costo} créditos)"):
                uso = {}
                for lg in hoy:
                    try:
                        datos, uso = cuotas_liga(clave, lg, dia, tuple(regiones or ["eu"]))
                        st.session_state["crudos"][lg] = datos
                    except Exception as e:
                        st.error(f"{nombres.get(lg, lg)}: {e}")
                st.session_state["uso"] = uso

    with st.expander("🇨🇴 Colombia: Liga BetPlay Primera A y B (API-Football)"):
        ck = secreto("API_FOOTBALL_KEY") or st.text_input("API-Football Key:", type="password").strip()
        if ck:
            try:
                col = ligas_af(ck, "Colombia")
                sel = st.multiselect("Ligas de Colombia", col, format_func=lambda x: f"{x[1]} ({x[2]})")
                if st.button("Traer partidos y cuotas de Colombia (gasta consultas de API-Football, no créditos de Odds API)"):
                    for lid, nom, temp in sel:
                        st.session_state["crudos"][f"af_{lid}"] = eventos_af(ck, lid, temp, dia, nom)
                    st.success("Listo: se agregaron a la lista de abajo.")
            except Exception as e:
                st.error(str(e))

    crudos = st.session_state["crudos"]
    if not crudos:
        return
    st.divider()
    todas = sorted({c for evs in crudos.values() for ev in evs for c in casas_de(ev)})
    c1, c2 = st.columns(2)
    metodo = c1.selectbox("Cómo quitar el margen", ["Shin", "Proporcional"])
    min_casas = c2.number_input("Mínimo de casas", 2, 30, 4)
    usables = st.multiselect("Casas donde SÍ puedo apostar (vacío = todas)", todas)
    rmin, rmax = st.slider("Rango de la mejor cuota", 1.01, 10.0, (1.01, 10.0), 0.01)
    vmin = st.slider("Valor mínimo (%)", -5.0, 10.0, 2.0, 0.5) / 100
    filas = []
    for evs in crudos.values():
        for ev in evs:
            filas += analizar_evento(ev, int(min_casas), TZ, metodo, set(usables))
    sel = [f for f in filas if rmin <= f["mejor_cuota"] <= rmax and f["valor"] >= vmin]
    orden = st.radio("Ordenar por", ["Hora", "Valor"], horizontal=True)
    sel.sort(key=lambda f: (f["hora"] or datetime.max.replace(tzinfo=TZ)) if orden == "Hora" else -f["valor"])
    if st.session_state.get("uso", {}).get("restantes"):
        st.metric("Créditos restantes (Odds API)", st.session_state["uso"]["restantes"])
    st.success(f"{len(sel)} picks de {len(filas)} resultados analizados.")
    for liga in sorted({f["liga"] for f in sel}):
        with st.expander(f"🏆 {liga}", expanded=True):
            for f in [x for x in sel if x["liga"] == liga]:
                h = f["hora"].strftime("%d/%m %H:%M") if f["hora"] else "?"
                st.markdown(f"**⏰ {h} | {f['local']} vs {f['visitante']}**")
                st.write(f"📌 {f['pick']} @ **{f['mejor_cuota']}** ({f['casa']}) · cuota justa {f['cuota_justa']} "
                         f"· valor {f['valor']:+.1%} · {f['n_casas']} casas · ref: {f['referencia']}")
                if f["aislada"]:
                    st.warning(f"⚠ Solo {f['casa']} paga así: la siguiente casa paga {f['segunda_cuota']}. Puede ser una cuota desactualizada.")
                st.divider()
    st.download_button("📥 Descargar picks (CSV)", a_csv(sel), file_name="picks_baga.csv", mime="text/csv")
    st.caption("Valor positivo = la mejor cuota paga más de lo que implica la probabilidad justa. No garantiza acierto: "
               "guarda el CSV y compara con los resultados y con la cuota de cierre de Pinnacle.")


if __name__ == "__main__":
    main()
