"""
Aplicación web del proyecto: Análisis de algoritmos en el contexto de la bibliometría.

    streamlit run app.py

Secciones:
  * Corpus: los 20 artículos con título, autores y abstract extraídos del PDF.
  * Req. 1: similitud textual (4 algoritmos clásicos + 2 modelos de IA).
  * Req. 2: agrupamiento jerárquico y dendrogramas.
  * Req. 3: búsqueda de patrones (KMP, Boyer-Moore, Rabin-Karp).
"""
from __future__ import annotations

import html

import altair as alt
import pandas as pd
import streamlit as st

from src.busqueda import benchmark, boyer_moore, kmp, rabin_karp
from src.clustering import jerarquico
from src.clustering.dendrograma import dibujar
from src.clustering.pipeline import REPRESENTACIONES, ejecutar
from src.corpus import cargar_corpus, etiqueta_corta
from src.ordenamiento import no_comparativos as ordenamiento
from src.preprocesamiento.texto import normalizar
from src.similitud import jaccard, levenshtein, needleman_wunsch, tfidf_coseno
from src.similitud.comparador import (ALGORITMOS, CLASICOS, IA, matriz_similitud,
                                      modelo_tfidf, tokens_clasicos, tokens_ia)
from src.similitud.embeddings import cargar_modelo, coseno, euclidiana

st.set_page_config(page_title="Análisis de algoritmos - Bibliometría",
                   page_icon=":material/account_tree:", layout="wide")

ESTILO = """
<style>
[data-testid="stDecoration"] {display: none;}
.block-container {max-width: 1180px; padding-top: 2.5rem;}
.stApp h1, .stApp h2, .stApp h3 {letter-spacing: -0.015em; font-weight: 600;}
.stApp h1 {font-size: 2rem; line-height: 1.2;}
.stApp h2 {font-size: 1.5rem; padding-bottom: .5rem; border-bottom: 1px solid #e3e3df;
           margin-bottom: .6rem;}
.stApp h3 {font-size: 1.1rem; padding-top: 1.4rem;}
.encabezado-sup {font-size: .74rem; text-transform: uppercase; letter-spacing: .12em;
                 color: #6b7075; margin-bottom: .25rem;}
[data-testid="stMetric"] {border: 1px solid #e3e3df; border-radius: 6px;
                          padding: .8rem 1rem; background: #ffffff;}
[data-testid="stMetricLabel"] p {font-size: .8rem; color: #6b7075;}
[data-testid="stMetricValue"] {font-size: 1.6rem; font-weight: 500;}
[data-testid="stSidebar"] {border-right: 1px solid #e3e3df;}
[data-testid="stSidebar"] [role="radiogroup"] label {padding: .25rem 0;}
.marca-lateral {font-weight: 600; font-size: .95rem; margin: .2rem 0 1rem 0;}
.stTabs [data-baseweb="tab-list"] {gap: 1.2rem;}
.stTabs [data-baseweb="tab"] {padding-left: 0; padding-right: 0;}
mark {background: #e6edf3; color: inherit; padding: 0 .15em; border-radius: 2px;}
</style>
"""
st.markdown(ESTILO, unsafe_allow_html=True)

with st.spinner("Cargando corpus..."):
    CORPUS = list(cargar_corpus())
POR_ID = {a["id"]: a for a in CORPUS}
ETIQUETAS = {a["id"]: etiqueta_corta(a, 60) for a in CORPUS}


# --------------------------------------------------------------------------- #
# Utilidades de presentación
# --------------------------------------------------------------------------- #
def tabla_matriz(M, ids, decimales=4):
    df = pd.DataFrame(M, index=[f"[{i}]" for i in ids], columns=[f"[{i}]" for i in ids])
    return df.style.format(f"{{:.{decimales}f}}").background_gradient(cmap="Blues", vmin=0, vmax=1)


def etiquetas_eje(secuencia) -> list[str]:
    """Rótulos únicos para filas/columnas de una matriz de PD: 'ε', '1:t', '2:h'..."""
    return ["ε"] + [f"{i}:{'␣' if x == ' ' else x}" for i, x in enumerate(secuencia, start=1)]


def resaltar(texto: str, posiciones: list[int], m: int, contexto: int = 60) -> list[str]:
    fragmentos = []
    for p in posiciones:
        ini, fin = max(0, p - contexto), min(len(texto), p + m + contexto)
        frag = (html.escape(texto[ini:p]) + "<mark>" + html.escape(texto[p:p + m]) +
                "</mark>" + html.escape(texto[p + m:fin]))
        fragmentos.append(("…" if ini > 0 else "") + frag + ("…" if fin < len(texto) else ""))
    return fragmentos


# --------------------------------------------------------------------------- #
# Páginas
# --------------------------------------------------------------------------- #
def pagina_inicio():
    st.markdown('<p class="encabezado-sup">Corpus</p>', unsafe_allow_html=True)
    st.title("Análisis de algoritmos en el contexto de la bibliometría")
    st.markdown(
        "Universidad del Quindío · Ingeniería de Sistemas y Computación · "
        "Análisis de Algoritmos 2026-2\n\n"
        "Corpus: **20 artículos** sobre inteligencia artificial (generativa) en educación. "
        "Los algoritmos trabajan sobre el **abstract** de cada artículo; el título y los "
        "autores se extrajeron del PDF para cruzar información.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Artículos", len(CORPUS))
    c2.metric("Palabras en abstracts", sum(len(a["abstract"].split()) for a in CORPUS))
    c3.metric("Autores distintos", len({x for a in CORPUS for x in a["autores"]}))

    df = pd.DataFrame([{"ID": a["id"], "Título": a["titulo"],
                        "Autores": ", ".join(a["autores"]),
                        "Palabras": len(a["abstract"].split())} for a in CORPUS])
    st.dataframe(df, hide_index=True, width="stretch")
    with st.expander("Ver los abstracts completos"):
        for a in CORPUS:
            st.markdown(f"**{a['id']}. {a['titulo']}**  \n*{', '.join(a['autores'])}*")
            st.write(a["abstract"])
            st.caption(f"Archivo: {a['archivo']}")
            st.divider()


def pagina_similitud():
    st.header("Requerimiento 1 · Similitud textual")
    st.markdown("Selecciona **dos o más** artículos. Se calculan 4 algoritmos clásicos "
                "(Levenshtein, Needleman-Wunsch, coseno TF-IDF y Jaccard) y 2 modelos de IA "
                "(embeddings preentrenados GloVe y FastText + similitud del coseno).")
    ids = st.multiselect("Artículos", options=list(POR_ID), default=[11, 16],
                         format_func=lambda i: ETIQUETAS[i])
    algs = st.multiselect("Algoritmos", options=list(ALGORITMOS), default=list(ALGORITMOS),
                          format_func=lambda a: ALGORITMOS[a])
    if len(ids) < 2:
        st.info("Elige al menos dos artículos.")
        return
    if len(ids) > 6 and "levenshtein" in algs:
        st.warning("Levenshtein a nivel de carácter es O(n·m): con muchos artículos tarda "
                   "varios segundos por cada par.")

    resumen = []
    barra = st.progress(0.0, text="Calculando similitudes...")
    pestanas = st.tabs([ALGORITMOS[a] for a in algs])
    for paso, (alg, tab) in enumerate(zip(algs, pestanas)):
        barra.progress(paso / max(len(algs), 1), text=f"Calculando {ALGORITMOS[alg]}...")
        with tab:
            with st.spinner(f"Calculando {ALGORITMOS[alg]}...", show_time=True):
                M, detalles = matriz_similitud(ids, alg)
            st.dataframe(tabla_matriz(M, ids), width="stretch")
            st.dataframe(pd.DataFrame(detalles), hide_index=True, width="stretch")
            for d in detalles:
                resumen.append({"Algoritmo": ALGORITMOS[alg], "Par": f"{d['a']}-{d['b']}",
                                "Similitud": d["similitud"],
                                "Tipo": "IA" if alg in IA else "Clásico"})
    barra.empty()
    if resumen:
        st.subheader("Comparación de algoritmos")
        df = pd.DataFrame(resumen)
        st.bar_chart(df.pivot(index="Par", columns="Algoritmo", values="Similitud"),
                     x_label="Par de artículos", y_label="Similitud (sin unidades)", stack=False)
        st.caption("Un valor mayor indica mayor similitud según cada algoritmo. Los métodos "
                   "clásicos usan valores entre 0 y 1; el coseno de embeddings puede variar entre −1 y 1.")

    if len(ids) == 2:
        st.subheader("Paso a paso para el par seleccionado")
        detalle_par(ids[0], ids[1])


def detalle_par(id_a: int, id_b: int):
    A, B = POR_ID[id_a]["abstract"], POR_ID[id_b]["abstract"]
    t1, t2, t3, t4, t5 = st.tabs(["Levenshtein", "Needleman-Wunsch", "Coseno TF-IDF",
                                  "Jaccard", "Embeddings (IA)"])
    with t1:
        st.latex(r"D[i][j]=\min\{D[i-1][j]+1,\;D[i][j-1]+1,\;D[i-1][j-1]+[a_i\neq b_j]\}")
        k = st.slider("Caracteres iniciales a mostrar", 5, 40, 14, key="lev_k")
        a, b = normalizar(A)[:k], normalizar(B)[:k]
        D = levenshtein.matriz_completa(a, b)
        df = pd.DataFrame(D, index=etiquetas_eje(a), columns=etiquetas_eje(b))
        st.dataframe(df, width="stretch")
        ops = levenshtein.operaciones(a, b, D)
        st.code(" ".join(o[0] for o in ops) + f"\n\nDistancia = {D[-1][-1]} · "
                f"similitud = 1 - {D[-1][-1]}/{max(len(a), len(b))} = "
                f"{levenshtein.similitud(a, b):.4f}")
    with t2:
        st.latex(r"F[i][j]=\max\{F[i-1][j-1]+s(a_i,b_j),\;F[i-1][j]+g,\;F[i][j-1]+g\}")
        k = st.slider("Palabras iniciales a mostrar", 3, 25, 8, key="nw_k")
        ta, tb = tokens_clasicos(A)[:k], tokens_clasicos(B)[:k]
        r = needleman_wunsch.alinear(ta, tb, guardar_matriz=True)
        st.dataframe(pd.DataFrame(r.matriz, index=etiquetas_eje(ta), columns=etiquetas_eje(tb)),
                     width="stretch")
        st.dataframe(pd.DataFrame([r.alineado_a, r.alineado_b], index=["A", "B"],
                                  columns=[str(i) for i in range(1, len(r.alineado_a) + 1)]),
                     width="stretch")
        st.write(f"Puntaje = {r.puntaje}; coincidencias = {r.coincidencias}; "
                 f"identidad = {r.identidad:.4f}")
        with st.spinner("Alineando los abstracts completos..."):
            rc = needleman_wunsch.alinear(tokens_clasicos(A), tokens_clasicos(B))
        st.info(f"Abstracts completos: puntaje {rc.puntaje}, {rc.coincidencias} coincidencias, "
                f"{rc.sustituciones} sustituciones, {rc.huecos} huecos → identidad "
                f"{rc.identidad:.4f}")
    with t3:
        st.latex(r"w_{t,d}=tf_{t,d}\cdot\left(\ln\frac{1+N}{1+df_t}+1\right),\quad "
                 r"\cos\theta=\frac{\sum_t w_{t,A}w_{t,B}}{\|A\|\|B\|}")
        det = tfidf_coseno.detalle(modelo_tfidf(), tokens_clasicos(A), tokens_clasicos(B))
        df = pd.DataFrame(det["filas"]).sort_values("w_A*w_B", ascending=False)
        st.dataframe(df, hide_index=True, width="stretch", height=300)
        st.write(f"Σ w_A·w_B = {det['producto_punto']:.6f};  ‖A‖ = {det['norma_A']:.6f};  "
                 f"‖B‖ = {det['norma_B']:.6f}")
        st.success(f"cos θ = {det['coseno']:.4f}  →  θ = {det['angulo']:.2f}°")
    with t4:
        st.latex(r"J(A,B)=\frac{|A\cap B|}{|A\cup B|}")
        det = jaccard.detalle(set(tokens_clasicos(A)), set(tokens_clasicos(B)))
        st.write(f"|A| = {det['A']}, |B| = {det['B']}, |A∩B| = {det['n_interseccion']}, "
                 f"|A∪B| = {det['n_union']} → J = {det['jaccard']:.4f}")
        st.write("Intersección:", ", ".join(det["interseccion"]))
    with t5:
        for nombre in ("glove100", "fasttext300"):
            with st.spinner("Cargando modelo de embeddings..."):
                m = cargar_modelo(nombre)
            u, usa, oova = m.vector_documento(tokens_ia(A))
            v, usb, oovb = m.vector_documento(tokens_ia(B))
            st.markdown(f"**{m.descripcion}**: A usa {len(usa)} palabras ({len(oova)} fuera "
                        f"de vocabulario), B usa {len(usb)} ({len(oovb)} fuera de vocabulario).")
            st.write(f"Primeras 6 componentes de v(A): {[round(x, 4) for x in u[:6]]}")
            st.write(f"cos = {coseno(u, v):.4f} · distancia euclidiana = {euclidiana(u, v):.4f}")


def pagina_clustering():
    st.header("Requerimiento 2 · Agrupamiento jerárquico")
    st.markdown("Pipeline: abstract → preprocesamiento → vectores → matriz de distancias → "
                "clustering aglomerativo (implementado desde cero) → dendrograma → evaluación.")
    rep = st.selectbox("Representación", list(REPRESENTACIONES),
                       format_func=lambda r: REPRESENTACIONES[r])
    criterios = st.multiselect("Criterios de enlace", list(jerarquico.CRITERIOS),
                               default=["single", "complete", "average"],
                               format_func=lambda c: jerarquico.CRITERIOS[c])
    etiquetas = [etiqueta_corta(a, 55) for a in CORPUS]
    resultados = {}
    if criterios:
        barra = st.progress(0.0, text="Agrupando...")
        for paso, c in enumerate(criterios):
            barra.progress(paso / len(criterios),
                           text=f"Agrupando con {jerarquico.CRITERIOS[c]}...")
            resultados[c] = ejecutar(c, rep)
        barra.empty()
    if not resultados:
        return
    filas = []
    for c, r in resultados.items():
        filas.append({"Criterio": jerarquico.CRITERIOS[c], "Correlación cofenética": r["ccc"],
                      "k elegido (silueta)": r["mejor_k"],
                      "Silueta en k elegido": r["siluetas"][r["mejor_k"]],
                      **{f"Silueta k={k}": v for k, v in r["siluetas"].items()}})
    df = pd.DataFrame(filas)
    st.subheader("Evaluación interna")
    st.dataframe(df.style.format(precision=4), hide_index=True, width="stretch")
    mejor = max(resultados.values(), key=lambda r: r["ccc"])
    st.success(f"Mayor correlación cofenética: **{jerarquico.CRITERIOS[mejor['criterio']]}** "
               f"(CCC = {mejor['ccc']:.4f}).")
    for c, r in resultados.items():
        st.subheader(jerarquico.CRITERIOS[c])
        with st.spinner("Dibujando dendrograma..."):
            fig = dibujar(r["fusiones"], etiquetas,
                          f"{jerarquico.CRITERIOS[c]} · {REPRESENTACIONES[rep]}", r["etiquetas"])
        st.pyplot(fig)
        with st.expander("Fusiones paso a paso y grupos"):
            st.dataframe(pd.DataFrame([vars(f) for f in r["fusiones"]]), hide_index=True)
            grupos: dict[int, list[str]] = {}
            for i, g in enumerate(r["etiquetas"]):
                grupos.setdefault(g, []).append(etiquetas[i])
            for g, miembros in grupos.items():
                st.markdown(f"**Grupo {g + 1}**: " + "; ".join(miembros))


def pagina_busqueda():
    st.header("Requerimiento 3 · Búsqueda de patrones (coincidencia exacta)")
    patron = st.text_input("Patrón de búsqueda", value="assessment")
    c1, c2 = st.columns(2)
    ignorar_mayus = c1.checkbox("Ignorar mayúsculas/minúsculas", value=True)
    q = c2.number_input("Módulo primo q de Rabin-Karp", min_value=3, value=rabin_karp.PRIMO_GRANDE)
    if not patron:
        return
    p = patron.lower() if ignorar_mayus else patron
    algs = {"KMP": kmp.buscar, "Boyer-Moore": boyer_moore.buscar,
            "Rabin-Karp": lambda t, pt: rabin_karp.buscar(t, pt, q=int(q))}
    totales = {n: {"ocurrencias": 0, "comparaciones": 0, "preproceso_ms": 0.0, "busqueda_ms": 0.0}
               for n in algs}
    hallazgos = []
    barra = st.progress(0.0, text="Buscando en los abstracts...")
    for idx, art in enumerate(CORPUS):
        barra.progress(idx / len(CORPUS), text=f"Buscando en el artículo {art['id']}...")
        texto = art["abstract"].lower() if ignorar_mayus else art["abstract"]
        posiciones = None
        for nombre, f in algs.items():
            r = f(texto, p)
            t = totales[nombre]
            t["ocurrencias"] += len(r.posiciones)
            t["comparaciones"] += r.comparaciones
            t["preproceso_ms"] += r.tiempo_preproceso_s * 1000
            t["busqueda_ms"] += r.tiempo_busqueda_s * 1000
            posiciones = r.posiciones
        if posiciones:
            hallazgos.append((art, posiciones))
    barra.empty()
    st.subheader("Rendimiento sobre los 20 abstracts")
    st.dataframe(pd.DataFrame([{"Algoritmo": n, **v} for n, v in totales.items()])
                 .style.format(precision=4), hide_index=True, width="stretch")
    st.subheader(f"Ocurrencias: {sum(len(x[1]) for x in hallazgos)} en {len(hallazgos)} artículos")
    for art, pos in hallazgos:
        with st.expander(f"{ETIQUETAS[art['id']]} · {len(pos)} ocurrencia(s) en {pos}"):
            for frag in resaltar(art["abstract"], pos, len(p)):
                st.markdown(frag, unsafe_allow_html=True)

    st.subheader("Traza paso a paso")
    id_t = st.selectbox("Abstract para la traza", list(POR_ID), format_func=lambda i: ETIQUETAS[i],
                        index=10)
    largo = st.slider("Caracteres del abstract a usar", 40, 600, 160)
    texto = POR_ID[id_t]["abstract"][:largo]
    texto = texto.lower() if ignorar_mayus else texto
    st.code(texto)
    t1, t2, t3 = st.tabs(["KMP", "Boyer-Moore", "Rabin-Karp"])
    with t1:
        r = kmp.buscar(texto, p, trazar=True)
        st.write("Tabla de fallo π:")
        st.dataframe(pd.DataFrame([list(p), r.extra["tabla_fallo"]], index=["P[q]", "π[q]"],
                                  columns=[str(i) for i in range(len(p))]).astype(str))
        st.dataframe(pd.DataFrame(r.pasos), hide_index=True, width="stretch", height=300)
        st.write(f"Ocurrencias: {r.posiciones} · comparaciones: {r.comparaciones}")
    with t2:
        r = boyer_moore.buscar(texto, p, trazar=True)
        st.write("Tabla de carácter malo (última aparición):")
        st.dataframe(pd.DataFrame([{("␣" if k == " " else k): v
                                    for k, v in r.extra["caracter_malo"].items()}]))
        st.write("Tabla de sufijo bueno bs[j] (j = 0..m):")
        st.dataframe(pd.DataFrame([r.extra["sufijo_bueno"]]))
        st.dataframe(pd.DataFrame(r.pasos), hide_index=True, width="stretch", height=300)
        st.write(f"Ocurrencias: {r.posiciones} · comparaciones: {r.comparaciones} · "
                 f"alineaciones probadas: {len(r.pasos)}")
    with t3:
        q_demo = st.number_input("q para la traza (un primo pequeño muestra colisiones)",
                                 min_value=3, value=37)
        r = rabin_karp.buscar(texto, p, q=int(q_demo), trazar=True)
        st.write(f"h = d^(m-1) mod q = {r.extra.get('h')} · hash(P) = {r.extra.get('hash_patron')}")
        st.code("\n".join(r.extra.get("pasos_hash_patron", [])))
        st.dataframe(pd.DataFrame(r.pasos), hide_index=True, width="stretch", height=300)
        st.write(f"Ocurrencias: {r.posiciones} · verificaciones: {r.extra.get('verificaciones')} · "
                 f"colisiones (falsos positivos): {r.extra.get('colisiones')}")

    st.subheader("Benchmark: teoría vs. rendimiento observado")
    if st.button("Ejecutar experimentos"):
        barra = st.progress(0.0, text="Midiendo tiempo vs. tamaño del texto (1/3)...")
        with st.spinner("Ejecutando experimentos...", show_time=True):
            df_n = pd.DataFrame(benchmark.experimento_tamano_texto())
            barra.progress(1 / 3, text="Midiendo tiempo vs. tamaño del patrón (2/3)...")
            df_m = pd.DataFrame(benchmark.experimento_tamano_patron())
            barra.progress(2 / 3, text="Midiendo el peor caso (3/3)...")
            df_w = pd.DataFrame(benchmark.experimento_peor_caso())
        barra.empty()
        st.markdown("**Tiempo de búsqueda vs. tamaño del texto n** (patrón 'assessment')")
        st.line_chart(df_n.pivot(index="n", columns="algoritmo", values="busqueda_ms"))
        st.markdown("**Tiempo de búsqueda vs. tamaño del patrón m**")
        st.line_chart(df_m.pivot(index="m", columns="algoritmo", values="busqueda_ms"))
        st.dataframe(df_m, hide_index=True, width="stretch")
        st.markdown("**Peor caso** (texto a^n, patrón b·a^(m-1))")
        st.dataframe(df_w, hide_index=True, width="stretch")


def pagina_seguimiento():
    st.header("Seguimiento 1 · Ranking de términos con ordenamiento no comparativo")
    st.markdown("Frecuencia de cada término en los 20 abstracts (minúsculas, sin números, sin "
                "stopwords, sin stemming, palabras de 3+ letras y 'ai'), ordenada con **Counting "
                "Sort**, **Radix Sort** y **Bucket Sort** (implementaciones del Seguimiento 1).")
    c1, c2, c3 = st.columns(3)
    top = c1.slider("Términos del ranking", 5, 50, 15)
    reps = c2.select_slider("Repeticiones por medición", [10, 100, 500, 1000], value=100)
    docs = c3.select_slider("Documentos usados", [5, 10, 15, 20], value=20)
    ids = [a["id"] for a in CORPUS][:docs]
    with st.spinner("Contando frecuencias..."):
        pares = ordenamiento.frecuencias_corpus(ids)
    k = max(f for _, f in pares)
    st.write(f"n = **{len(pares)}** términos distintos · k = **{k}** (frecuencia máxima)")
    medidas = {}
    barra = st.progress(0.0, text="Midiendo algoritmos de ordenamiento...")
    for paso, (n, f) in enumerate(ordenamiento.ALGORITMOS.items()):
        barra.progress(paso / len(ordenamiento.ALGORITMOS), text=f"Midiendo {n} ({reps} repeticiones)...")
        medidas[n] = ordenamiento.medir(f, pares, reps)
    barra.empty()
    base = [f for _, f in medidas["Counting Sort"]["resultado"]]
    st.dataframe(pd.DataFrame([{
        "Algoritmo": n, "Promedio (ms)": m["promedio_ms"], "Mínimo (ms)": m["min_ms"],
        "Máximo (ms)": m["max_ms"],
        "Mismo orden de frecuencias que Counting": [f for _, f in m["resultado"]] == base}
        for n, m in medidas.items()]).style.format(precision=4), hide_index=True, width="stretch")
    rankings = {n: ordenamiento.ranking(m["resultado"], top) for n, m in medidas.items()}
    df = pd.DataFrame({"Posición": range(1, top + 1),
                       **{n: [t for t, _ in r] for n, r in rankings.items()},
                       "Frecuencia": [f for _, f in rankings["Counting Sort"]]})
    c1, c2 = st.columns([1, 1])
    c1.dataframe(df, hide_index=True, width="stretch")
    grafica = (alt.Chart(df.rename(columns={"Counting Sort": "Término"}))
               .mark_bar().encode(
                   x=alt.X("Frecuencia:Q", title="Frecuencia (n.º de apariciones)"),
                   y=alt.Y("Término:N", title="Término del abstract", sort="-x")))
    c2.altair_chart(grafica, width="stretch")
    c2.caption("La frecuencia cuenta las apariciones de cada término en los abstracts de los "
               "documentos seleccionados.")
    st.caption("Los empates pueden aparecer en distinto orden entre algoritmos (Bucket Sort "
               "conserva el orden de inserción dentro de cada cubeta); la secuencia de "
               "frecuencias es idéntica.")
    with st.expander("Distribución de las frecuencias en las cubetas de Bucket Sort (ley de Zipf)"):
        tam = ordenamiento.distribucion_cubetas(pares)
        no_vacias = [(i, t) for i, t in enumerate(tam) if t]
        st.write(f"{len(tam)} cubetas, {len(no_vacias)} no vacías; la primera recibe "
                 f"{tam[0]} de {len(pares)} términos ({100 * tam[0] / len(pares):.1f} %).")
        st.bar_chart(pd.DataFrame(no_vacias, columns=["cubeta", "términos"]).set_index("cubeta"),
                     x_label="Índice de cubeta", y_label="Cantidad de términos distintos")
        st.caption("Cada barra cuenta los términos distintos asignados a una cubeta según su "
                   "frecuencia. Solo se muestran las cubetas no vacías.")
    with st.expander("Caracterización del corpus"):
        st.dataframe(pd.DataFrame(ordenamiento.caracterizacion()), hide_index=True, width="stretch")


PAGINAS = {
    "Corpus": pagina_inicio,
    "Req. 1 · Similitud": pagina_similitud,
    "Req. 2 · Clustering": pagina_clustering,
    "Req. 3 · Búsqueda de patrones": pagina_busqueda,
    "Seguimiento 1 · Ordenamiento": pagina_seguimiento,
}

with st.sidebar:
    st.markdown('<p class="marca-lateral">Navegación</p>', unsafe_allow_html=True)
    eleccion = st.radio("Sección", list(PAGINAS), label_visibility="collapsed")
    st.caption("Algoritmos implementados desde cero en Python. "
               "Ver docs/Documento_Tecnico.docx para el análisis completo.")
PAGINAS[eleccion]()
