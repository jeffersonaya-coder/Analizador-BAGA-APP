import csv
import io
from datetime import datetime, timedelta
from statistics import pstdev

import pytz
import requests
import streamlit as st

API = "https://api.the-odds-api.com/v4"
TZ = pytz.timezone("America/Bogota")


# ---------------------------------------------------------------- API
def pedir(ruta, clave, **params):
    """The Odds API. /sports y /events son GRATIS; /odds cuesta mercados x regiones créditos."""
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
    fin = ini + timedelta(days=1)
    f = lambda d: d.astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f(ini), f(fin)


@st.cache_data(ttl=900)
def eventos_dia(clave, liga, dia):
    desde, hasta = ventana_utc(dia)
    datos, _ = pedir(f"/sports/{liga}/events", clave, commenceTimeFrom=desde, commenceTimeTo=hasta)  # gratis
    return datos


@st.cache_data(ttl=600)
def cuotas_liga(clave, liga, dia):
    desde, hasta = ventana_utc(dia)
    return pedir(f"/sports/{liga}/odds", clave, regions="eu", markets="h2h", oddsFormat="decimal",
                 commenceTimeFrom=desde, commenceTimeTo=hasta)  # 1 crédito por liga


# ---------------------------------------------------------------- análisis
def quitar_margen(precios):
    """{resultado: cuota} -> {resultado: probabilidad sin margen de la casa}"""
    inv = {k: 1 / v for k, v in precios.items() if v and v > 1}
    total = sum(inv.values())
    return {k: v / total for k, v in inv.items()} if total else {}


def analizar_evento(ev, min_casas=4, tz=None):
    """Compara TODAS las casas (no solo la primera): probabilidad justa, mejor cuota y valor."""
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
    probs = {t: quitar_margen(p) for t, (_, p) in libros.items()}
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
        casa, (_, precios) = max(libros.items(), key=lambda kv: kv[1][1].get(n, 0))
        mejor, pj = precios[n], ref[n]
        if pj <= 0:
            continue
        filas.append({
            "hora": hora, "liga": ev.get("sport_title", ""), "local": ev.get("home_team"), "visitante": ev.get("away_team"),
            "pick": "Empate" if n.lower() == "draw" else f"Gana {n}",
            "mejor_cuota": round(mejor, 2), "casa": casa,
            "prob_justa": round(pj, 3), "cuota_justa": round(1 / pj, 2), "valor": round(mejor * pj - 1, 3),
            "n_casas": len(libros), "referencia": ref_nombre,
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


# ---------------------------------------------------------------- interfaz
def main():
    st.set_page_config(page_title="Analizador BAGA", page_icon="⚽", layout="centered")
    st.title("⚽ Analizador BAGA")
    st.caption("Datos de The Odds API (no es OddsPortal). Buscar ligas y partidos es GRATIS; solo traer cuotas gasta créditos.")

    try:
        clave = str(st.secrets.get("ODDS_API_KEY", "")).strip()
    except Exception:
        clave = ""
    clave = clave or st.text_input("Odds API Key:", type="password").strip()
    if not clave:
        st.stop()

    try:
        ligas = ligas_futbol(clave)
    except Exception as e:
        st.error(f"No pude leer las ligas (revisa la clave): {e}")
        st.stop()
    nombres = dict(ligas)

    dia = st.date_input("Día", value=datetime.now(TZ).date())
    elegidas = st.multiselect("Ligas", list(nombres), format_func=nombres.get)
    c1, c2 = st.columns(2)
    rmin, rmax = c1.slider("Rango de la mejor cuota", 1.01, 10.0, (1.50, 1.70), 0.01)
    min_casas = c2.number_input("Mínimo de casas", 2, 30, 4)
    solo_valor = st.checkbox("Solo con valor positivo (mejor cuota > cuota justa)", False)

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
        st.session_state.pop("filas", None)

    hoy = st.session_state.get("hoy")
    if hoy is not None:
        if not hoy:
            st.warning("Ninguna de las ligas elegidas tiene partidos ese día. No se gastó ningún crédito.")
        else:
            st.info("Partidos encontrados: " + ", ".join(f"{nombres.get(k, k)} ({n})" for k, n in hoy.items()))
            if st.button(f"2️⃣ Traer cuotas (costará {len(hoy)} créditos)"):
                filas, uso = [], {}
                for lg in hoy:
                    try:
                        datos, uso = cuotas_liga(clave, lg, dia)
                    except Exception as e:
                        st.error(f"{nombres.get(lg, lg)}: {e}")
                        continue
                    for ev in datos:
                        filas += analizar_evento(ev, int(min_casas), TZ)
                st.session_state["filas"], st.session_state["uso"] = filas, uso

    if "uso" in st.session_state and st.session_state["uso"].get("restantes"):
        st.metric("Créditos restantes", st.session_state["uso"]["restantes"])

    filas = st.session_state.get("filas")
    if filas is None:
        return
    sel = [f for f in filas if rmin <= f["mejor_cuota"] <= rmax and (not solo_valor or f["valor"] > 0)]
    orden = st.radio("Ordenar por", ["Hora", "Valor"], horizontal=True)
    sel.sort(key=lambda f: (f["hora"] or datetime.max.replace(tzinfo=TZ)) if orden == "Hora" else -f["valor"])
    st.success(f"{len(sel)} picks de {len(filas)} resultados analizados.")
    for liga in sorted({f["liga"] for f in sel}):
        with st.expander(f"🏆 {liga}", expanded=True):
            for f in [x for x in sel if x["liga"] == liga]:
                h = f["hora"].strftime("%d/%m %H:%M") if f["hora"] else "?"
                st.markdown(f"**⏰ {h} | {f['local']} vs {f['visitante']}**")
                st.write(f"📌 {f['pick']} @ **{f['mejor_cuota']}** ({f['casa']}) · cuota justa {f['cuota_justa']} "
                         f"· valor {f['valor']:+.1%} · {f['n_casas']} casas · ref: {f['referencia']}")
                st.divider()
    st.download_button("📥 Descargar picks (CSV)", a_csv(sel), file_name="picks_baga.csv", mime="text/csv")
    st.caption("Valor positivo = la mejor cuota paga más de lo que implica la probabilidad justa del mercado. "
               "No garantiza acierto: guarda el CSV y compara con los resultados para saber si funciona.")


if __name__ == "__main__":
    main()
