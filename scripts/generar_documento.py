"""
Genera el documento técnico (docs/Documento_Tecnico.docx) con los casos de
estudio calculados en vivo por las implementaciones del proyecto, junto con las
figuras (docs/figuras/) y las tablas de resultados (docs/resultados/).

    python scripts/generar_documento.py

Todos los números del documento salen de ejecutar el código: si se cambia un
algoritmo o el corpus, basta con volver a correr este script.
"""
from __future__ import annotations

import csv
import math
import platform
import sys
from datetime import date
from itertools import combinations
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from docx import Document  # noqa: E402
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

from src.busqueda import benchmark, boyer_moore, kmp, rabin_karp  # noqa: E402
from src.clustering import jerarquico  # noqa: E402
from src.clustering.dendrograma import dibujar  # noqa: E402
from src.clustering.pipeline import REPRESENTACIONES, ejecutar  # noqa: E402
from src.corpus import articulo_por_id, cargar_corpus, etiqueta_corta  # noqa: E402
from src.ordenamiento import no_comparativos as ordenamiento  # noqa: E402
from src.preprocesamiento.texto import normalizar, preprocesar  # noqa: E402
from src.similitud import jaccard, levenshtein, needleman_wunsch, tfidf_coseno  # noqa: E402
from src.similitud.comparador import (ALGORITMOS, modelo_tfidf, similitud_par,  # noqa: E402
                                      tokens_clasicos, tokens_ia)
from src.similitud.embeddings import cargar_modelo, coseno, euclidiana  # noqa: E402

DOCS = RAIZ / "docs"
FIG = DOCS / "figuras"
RES = DOCS / "resultados"
FIG.mkdir(parents=True, exist_ok=True)
RES.mkdir(parents=True, exist_ok=True)

# Caso de estudio
ID_A, ID_B = 11, 16
PATRON = "assessment"
CORPUS = list(cargar_corpus())
ART_A, ART_B = articulo_por_id(ID_A), articulo_por_id(ID_B)


# =========================================================================== #
# Utilidades de python-docx
# =========================================================================== #
doc = Document()
estilo = doc.styles["Normal"]
estilo.font.name = "Calibri"
estilo.font.size = Pt(11)
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.3)
    s.top_margin = s.bottom_margin = Cm(2.2)


def h(texto: str, nivel: int = 1):
    return doc.add_heading(texto, level=nivel)


def p(texto: str = "", negrita: bool = False, cursiva: bool = False, tam: int | None = None,
      centrado: bool = False):
    par = doc.add_paragraph()
    _runs(par, texto, negrita, cursiva, tam)
    if centrado:
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return par


def _runs(par, texto, negrita=False, cursiva=False, tam=None):
    """Permite **negrita** dentro del texto."""
    partes = texto.split("**")
    for i, parte in enumerate(partes):
        if not parte:
            continue
        r = par.add_run(parte)
        r.bold = negrita or (i % 2 == 1)
        r.italic = cursiva
        if tam:
            r.font.size = Pt(tam)


def viñeta(texto: str):
    par = doc.add_paragraph(style="List Bullet")
    _runs(par, texto)
    return par


def ecuacion(texto: str):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = par.add_run(texto)
    r.font.name = "Cambria Math"
    r.italic = True
    r.font.size = Pt(11)
    return par


def codigo(texto: str):
    par = doc.add_paragraph()
    par.paragraph_format.left_indent = Cm(0.5)
    lineas = texto.split("\n")
    r = par.add_run(lineas[0])
    for linea in lineas[1:]:
        r.add_break()
        r.add_text(linea)
    r.font.name = "Consolas"
    r.font.size = Pt(8.5)
    sombra = OxmlElement("w:shd")
    sombra.set(qn("w:val"), "clear")
    sombra.set(qn("w:fill"), "F3F4F6")
    par._p.get_or_add_pPr().append(sombra)
    return par


def tabla(encabezados: list[str], filas: list[list], tam: float = 8.5, anchos=None):
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, e in enumerate(encabezados):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(str(e))
        r.bold = True
        r.font.size = Pt(tam)
    for fila in filas:
        celdas = t.add_row().cells
        for i, v in enumerate(fila):
            if isinstance(v, float):
                v = f"{v:.4f}"
            celdas[i].text = ""
            r = celdas[i].paragraphs[0].add_run(str(v))
            r.font.size = Pt(tam)
    if anchos:
        for fila in t.rows:
            for i, w in enumerate(anchos):
                fila.cells[i].width = Cm(w)
    doc.add_paragraph()
    return t


def figura(ruta: Path, ancho_cm: float = 15.5, pie: str = ""):
    doc.add_picture(str(ruta), width=Cm(ancho_cm))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if pie:
        par = p(pie, cursiva=True, tam=9, centrado=True)
        par.runs[0].font.color.rgb = RGBColor(0x47, 0x55, 0x69)


def guardar_csv(nombre: str, filas: list[dict]):
    if not filas:
        return
    with open(RES / nombre, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)


def mostrar(c) -> str:
    return "␣" if c == " " else c


# =========================================================================== #
# Figura de arquitectura
# =========================================================================== #
def figura_arquitectura() -> Path:
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.axis("off")

    def caja(x, y, w, hh, texto, color):
        ax.add_patch(plt.Rectangle((x, y), w, hh, facecolor=color, edgecolor="#1e293b",
                                   lw=1.2, zorder=2))
        ax.text(x + w / 2, y + hh / 2, texto, ha="center", va="center", fontsize=8.6, zorder=3)

    def flecha(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", lw=1.3, color="#334155"))

    ax.set_xlim(0, 11)
    ax.set_ylim(0, 6.2)
    ax.text(0.1, 5.95, "Capa de datos", fontsize=9, color="#64748b")
    caja(0.2, 4.8, 2.2, 0.9, "20 artículos PDF\n(articulos/)", "#fde68a")
    caja(3.0, 4.8, 2.6, 0.9, "Extracción\nsrc/extraccion\n(pdfplumber + heurísticas)", "#fef3c7")
    caja(6.2, 4.8, 2.2, 0.9, "data/corpus.json\ntítulo · autores · abstract", "#fde68a")
    caja(8.9, 4.8, 1.9, 0.9, "data/embeddings\nGloVe · FastText", "#fde68a")
    flecha(2.4, 5.25, 3.0, 5.25)
    flecha(5.6, 5.25, 6.2, 5.25)

    ax.text(0.1, 4.45, "Capa de lógica (algoritmos implementados desde cero)", fontsize=9,
            color="#64748b")
    caja(0.2, 3.3, 10.6, 0.9, "Preprocesamiento (src/preprocesamiento): normalización · tokenización · "
         "stopwords · S-stemmer", "#dbeafe")
    caja(0.2, 1.75, 3.4, 1.3, "Req. 1 · src/similitud\nLevenshtein · Needleman-Wunsch\n"
         "Coseno TF-IDF · Jaccard\nGloVe · FastText (IA)", "#bfdbfe")
    caja(3.8, 1.75, 3.4, 1.3, "Req. 2 · src/clustering\nSingle · Complete · Average (· Ward)\n"
         "Lance-Williams · cofenética · silueta\nDendrograma propio", "#bfdbfe")
    caja(7.4, 1.75, 3.4, 1.3, "Req. 3 · src/busqueda\nKMP · Boyer-Moore · Rabin-Karp\n"
         "trazas paso a paso\nbenchmark", "#bfdbfe")
    flecha(7.3, 4.8, 5.5, 4.2)
    flecha(9.85, 4.8, 2.0, 3.05)
    for x in (1.9, 5.5, 9.1):
        flecha(x, 3.3, x, 3.05)

    ax.text(0.1, 1.45, "Capa de presentación", fontsize=9, color="#64748b")
    caja(0.2, 0.3, 5.1, 0.95, "Aplicación web Streamlit (app.py)\nCorpus · Req. 1 · Req. 2 · Req. 3",
         "#bbf7d0")
    caja(5.7, 0.3, 5.1, 0.95, "scripts/generar_documento.py\nDocumento técnico · figuras · CSV",
         "#bbf7d0")
    for x in (1.9, 5.5, 9.1):
        flecha(x, 1.75, x if x < 5 else (4 if x < 9 else 8.2), 1.25)
    ruta = FIG / "arquitectura.png"
    fig.tight_layout()
    fig.savefig(ruta, dpi=160)
    plt.close(fig)
    return ruta


# =========================================================================== #
# Cálculos
# =========================================================================== #
print("Calculando similitud de los 190 pares para los 6 algoritmos (Levenshtein tarda ~1 min)...")
pares = list(combinations([a["id"] for a in CORPUS], 2))
textos = {a["id"]: a["abstract"] for a in CORPUS}
sim_global: dict[str, list[float]] = {alg: [] for alg in ALGORITMOS}
filas_csv = []
for a, b in pares:
    fila = {"a": a, "b": b}
    for alg in ALGORITMOS:
        v = similitud_par(alg, textos[a], textos[b])["similitud"]
        sim_global[alg].append(v)
        fila[alg] = round(v, 6)
    filas_csv.append(fila)
guardar_csv("similitud_190_pares.csv", filas_csv)


def pearson(x, y):
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy)


def rangos(x):
    orden = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    for pos, i in enumerate(orden):
        r[i] = pos + 1
    return r


def spearman(x, y):
    return pearson(rangos(x), rangos(y))


print("Clustering...")
res_cluster = {(c, rep): ejecutar(c, rep) for rep in REPRESENTACIONES
               for c in ("single", "complete", "average", "ward")}
etiquetas_cortas = [etiqueta_corta(a, 52) for a in CORPUS]
for rep in REPRESENTACIONES:
    for c in ("single", "complete", "average"):
        r = res_cluster[(c, rep)]
        fig = dibujar(r["fusiones"], etiquetas_cortas,
                      f"{jerarquico.CRITERIOS[c]} · {REPRESENTACIONES[rep]}", r["etiquetas"])
        fig.savefig(FIG / f"dendrograma_{rep}_{c}.png", dpi=140)
        plt.close(fig)

print("Benchmark de búsqueda...")
bench_n = benchmark.experimento_tamano_texto(repeticiones=5)
bench_m = benchmark.experimento_tamano_patron(repeticiones=5)
bench_w = benchmark.experimento_peor_caso(repeticiones=3)
guardar_csv("benchmark_tamano_texto.csv", bench_n)
guardar_csv("benchmark_tamano_patron.csv", bench_m)
guardar_csv("benchmark_peor_caso.csv", bench_w)


def grafica_bench(filas, eje, valor, titulo, archivo, ylabel):
    fig, ax = plt.subplots(figsize=(7.5, 4))
    for alg in ("KMP", "Boyer-Moore", "Rabin-Karp"):
        xs = [f[eje] for f in filas if f["algoritmo"] == alg]
        ys = [f[valor] for f in filas if f["algoritmo"] == alg]
        ax.plot(xs, ys, marker="o", label=alg)
    ax.set_xlabel("n (caracteres del texto)" if eje == "n" else "m (longitud del patrón)")
    ax.set_ylabel(ylabel)
    ax.set_title(titulo, fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / archivo, dpi=150)
    plt.close(fig)


grafica_bench(bench_n, "n", "busqueda_ms", "Tiempo de búsqueda vs n (patrón 'assessment')",
              "bench_n_tiempo.png", "tiempo de búsqueda (ms)")
grafica_bench(bench_m, "m", "busqueda_ms", "Tiempo de búsqueda vs m (texto de 113 099 caracteres)",
              "bench_m_tiempo.png", "tiempo de búsqueda (ms)")
grafica_bench(bench_m, "m", "comparaciones", "Comparaciones de caracteres vs m",
              "bench_m_comparaciones.png", "comparaciones")
grafica_bench(bench_m, "m", "preproceso_ms", "Tiempo de preprocesamiento vs m",
              "bench_m_preproceso.png", "preprocesamiento (ms)")

ruta_arq = figura_arquitectura()

# =========================================================================== #
# DOCUMENTO
# =========================================================================== #
print("Escribiendo el documento...")
p("Universidad del Quindío", negrita=True, tam=14, centrado=True)
p("Programa de Ingeniería de Sistemas y Computación", tam=12, centrado=True)
p("Análisis de Algoritmos · 2026-2", tam=12, centrado=True)
doc.add_paragraph()
p("Análisis de algoritmos en el contexto de la bibliometría", negrita=True, tam=20, centrado=True)
p("Documento técnico de diseño, arquitectura y análisis algorítmico", tam=13, centrado=True)
doc.add_paragraph()
p("Estudiante: ______________________________", centrado=True)
p("Docente: Sergio Augusto Cardona Torres", centrado=True)
p(f"Fecha: {date.today().strftime('%d/%m/%Y')}", centrado=True)
doc.add_page_break()

# ----------------------------------------------------------------- Contenido
h("Contenido", 1)
for linea in ["1. Introducción y alcance", "2. Arquitectura y diseño de la solución",
              "3. Fuente de datos: extracción y preprocesamiento",
              "4. Requerimiento 1: similitud textual (clásicos e IA)",
              "5. Requerimiento 2: agrupamiento jerárquico",
              "6. Requerimiento 3: búsqueda de patrones",
              "7. Seguimiento 1: ranking de términos con ordenamiento no comparativo",
              "8. Requerimiento 4: despliegue, pruebas y uso de la aplicación",
              "9. Declaración del uso de inteligencia artificial generativa", "10. Referencias"]:
    p(linea)
doc.add_page_break()

# ----------------------------------------------------------------- 1
h("1. Introducción y alcance", 1)
p("El proyecto implementa y analiza algoritmos clásicos y modelos de inteligencia artificial "
  "sobre un corpus controlado de 20 artículos científicos acerca de la inteligencia artificial "
  "(generativa) en educación, suministrados por el docente en formato PDF. El procesamiento se "
  "concentra en el **abstract** de cada artículo; el título y los autores se extraen como "
  "metadatos para identificar y cruzar la información en la aplicación.")
p("Los requerimientos funcionales abordados son:")
viñeta("**Req. 1:** similitud textual entre dos o más abstracts con 4 algoritmos clásicos "
       "(Levenshtein, Needleman-Wunsch, coseno sobre TF-IDF y Jaccard) y 2 modelos de IA basados en "
       "embeddings preentrenados (GloVe y FastText).")
viñeta("**Req. 2:** agrupamiento jerárquico aglomerativo con tres criterios (single, complete y "
       "average linkage; se agrega Ward como referencia), dendrogramas y evaluación interna "
       "(correlación cofenética y coeficiente de silueta).")
viñeta("**Req. 3:** búsqueda exacta de patrones con Knuth-Morris-Pratt, Boyer-Moore y Rabin-Karp, "
       "con trazas paso a paso y contraste entre la complejidad teórica y el rendimiento medido.")
viñeta("**Req. 4:** aplicación web desplegable (Streamlit) y esta documentación técnica.")
p("**Restricción de implementación.** Ningún algoritmo solicitado usa funciones de alto nivel "
  "que lo resuelvan directamente: no se usan find(), index(), re.search() para la búsqueda, ni "
  "scipy/sklearn para la similitud o el clustering. Todos se escriben con listas, diccionarios, "
  "conjuntos y ciclos explícitos. SciPy y scikit-learn aparecen únicamente en las pruebas "
  "automáticas, como oráculo para verificar que los resultados propios son correctos.")
p("**Notación de análisis.** Siguiendo el material del curso, el tiempo de ejecución T(n) se "
  "estima contando operaciones elementales (asignaciones, comparaciones, operaciones aritméticas, "
  "accesos a estructuras) y se resume en notación asintótica O, considerando mejor y peor caso.")

# ----------------------------------------------------------------- 2
h("2. Arquitectura y diseño de la solución", 1)
p("La solución sigue una arquitectura en tres capas: datos, lógica algorítmica y presentación. "
  "Cada requerimiento es un paquete independiente de Python que solo depende de la capa de "
  "datos y del módulo de preprocesamiento, lo que permite probar cada algoritmo por separado.")
figura(ruta_arq, 16, "Figura 1. Arquitectura de la solución.")
tabla(["Módulo", "Responsabilidad"], [
    ["src/extraccion/extractor_pdf.py", "Lee la primera página de cada PDF con pdfplumber; detecta título "
     "(mayor tamaño de fuente), autores (líneas bajo el título) y abstract (columna bajo el encabezado "
     "'Abstract' hasta 'Keywords' / 'Introduction')."],
    ["src/corpus.py", "Carga data/corpus.json (20 artículos)."],
    ["src/preprocesamiento/texto.py", "Normalización, tokenización, stopwords y S-stemmer."],
    ["src/similitud/*.py", "Levenshtein, Needleman-Wunsch, TF-IDF + coseno, Jaccard, embeddings."],
    ["src/similitud/comparador.py", "Fachada del Req. 1: matrices de similitud para N artículos."],
    ["src/clustering/*.py", "Aglomerativo (Lance-Williams), métricas internas, dendrograma, pipeline."],
    ["src/busqueda/*.py", "KMP, Boyer-Moore, Rabin-Karp con trazas; benchmark."],
    ["app.py", "Interfaz web Streamlit con una sección por requerimiento."],
    ["scripts/", "construir_corpus.py, construir_embeddings.py, generar_documento.py."],
    ["tests/", "Pruebas con pytest (casos clásicos, fuerza bruta y comparación con SciPy/sklearn)."],
], anchos=[5.5, 11])
p("**Flujo de datos.** (1) scripts/construir_corpus.py extrae los metadatos de los 20 PDF y genera "
  "data/corpus.json. (2) scripts/construir_embeddings.py descarga una vez los modelos preentrenados "
  "y guarda solo los vectores de las palabras del corpus (≈1 100 palabras) en data/embeddings/, "
  "lo que permite ejecutar la aplicación sin conexión. (3) La aplicación y el generador de este "
  "documento consumen esos datos e invocan los algoritmos.")
p("**Decisiones de diseño.**")
viñeta("Los algoritmos devuelven estructuras de resultado con contadores (comparaciones, tiempo de "
       "preprocesamiento y de búsqueda) y, opcionalmente, una traza de pasos, para hacer visible su "
       "comportamiento interno sin cambiar el algoritmo.")
viñeta("Los vectores TF-IDF se representan como diccionarios dispersos {término: peso}: un abstract "
       "tiene ~90 términos distintos frente a ~1 000 del vocabulario, así que el producto punto solo "
       "recorre términos presentes.")
viñeta("El clustering recibe una matriz de distancias, de modo que la misma implementación sirve "
       "para TF-IDF y para los embeddings de IA.")

# ----------------------------------------------------------------- 3
h("3. Fuente de datos: extracción y preprocesamiento", 1)
p("La extracción es automática para los 20 artículos (el archivo data/correcciones.json permite "
  "corregir manualmente un campo y queda registrado en el corpus, pero no fue necesario usarlo). "
  "Las 20 maquetaciones provienen de 6 editoriales distintas (Elsevier, BMC/Springer Open, Springer, "
  "Emerald, Wiley y MDPI), por lo que el extractor usa la posición de cada palabra para separar las "
  "columnas laterales (palabras clave, afiliaciones, citación) del abstract. También resuelve "
  "ligaduras tipográficas (ﬁ, ﬂ), acentos combinados (Gašević) y cortes de palabra con guion al "
  "final de línea, decidiendo con el vocabulario del propio documento si el guion era parte de la "
  "palabra (AI-driven) o un corte (practi-tioners → practitioners).")
tabla(["ID", "Título", "Autores", "Palabras"],
      [[a["id"], a["titulo"], ", ".join(a["autores"]), len(a["abstract"].split())] for a in CORPUS],
      tam=7.5, anchos=[1, 8.5, 5.5, 1.5])
p("**Preprocesamiento.** Se aplica la siguiente cadena: (1) minúsculas y eliminación de todo carácter "
  "que no sea letra o dígito; (2) tokenización por espacios; (3) eliminación de números y de "
  f"stopwords del inglés; (4) S-stemmer de Harman (1991), que solo reduce plurales regulares. Por "
  f"ejemplo, el abstract {ID_A} pasa de {len(ART_A['abstract'].split())} palabras a "
  f"{len(tokens_clasicos(ART_A['abstract']))} tokens. Levenshtein trabaja sobre el texto normalizado "
  "(nivel carácter); Needleman-Wunsch, TF-IDF, Jaccard y clustering sobre los tokens; los modelos de "
  "IA usan los tokens sin stemming, porque sus vocabularios contienen las formas originales.")
p(f"Tokens iniciales del abstract {ID_A}: " + ", ".join(tokens_clasicos(ART_A["abstract"])[:18]) + " …")

# ----------------------------------------------------------------- 4
doc.add_page_break()
h("4. Requerimiento 1: similitud textual", 1)
p(f"**Caso de estudio.** Se seleccionaron los abstracts de los artículos {ID_A} y {ID_B}, ambos "
  "sobre el impacto de la IA generativa en la evaluación (assessment) en educación superior, por lo "
  "que se espera una similitud temática alta aunque estén redactados de forma distinta:")
viñeta(f"**A = [{ID_A}]** {ART_A['titulo']} ({', '.join(ART_A['autores'])}).")
viñeta(f"**B = [{ID_B}]** {ART_B['titulo']} ({', '.join(ART_B['autores'])}).")
A_txt, B_txt = ART_A["abstract"], ART_B["abstract"]
A_norm, B_norm = normalizar(A_txt), normalizar(B_txt)
A_tok, B_tok = tokens_clasicos(A_txt), tokens_clasicos(B_txt)

# ---- 4.1 Levenshtein
h("4.1 Distancia de edición de Levenshtein (programación dinámica)", 2)
p("La distancia de Levenshtein es el número mínimo de inserciones, eliminaciones y sustituciones "
  "de un carácter necesarias para transformar una cadena en otra. Se resuelve con programación "
  "dinámica por tabulación (bottom-up): cada celda D[i][j] guarda la solución del subproblema "
  "'primeros i caracteres de A contra primeros j caracteres de B'.")
ecuacion("D[i][0] = i ;  D[0][j] = j")
ecuacion("D[i][j] = mín{ D[i−1][j] + 1 ,  D[i][j−1] + 1 ,  D[i−1][j−1] + [aᵢ ≠ bⱼ] }")
ecuacion("sim(A,B) = 1 − D[n][m] / máx(n, m)")
codigo("""for i in range(1, n + 1):                  # n iteraciones
    for j in range(1, m + 1):              # m iteraciones por cada i
        costo = 0 if a[i-1] == b[j-1] else 1
        D[i][j] = min(D[i-1][j] + 1, D[i][j-1] + 1, D[i-1][j-1] + costo)""")
p("**Tiempo de ejecución.** La inicialización de la primera fila y columna cuesta (n+1)+(m+1) "
  "asignaciones. El cuerpo del ciclo interno realiza un número constante c de operaciones "
  "elementales (1 comparación, 3 sumas, 6 accesos, 1 mínimo de tres, 2 asignaciones ≈ 13) y se "
  "ejecuta n·m veces; las comparaciones de control de los ciclos aportan (n+1) + n(m+1). Así, "
  "T(n,m) = c₁·n·m + c₂·n + c₃·m + c₄ con c₁ ≈ 15 ⇒ **O(n·m)** en mejor, peor y caso promedio (la tabla siempre "
  "se llena completa). El espacio es O(n·m) con la matriz o O(mín(n,m)) guardando solo dos filas, "
  "que es la versión usada para los abstracts completos.")
k = 12
a_dem, b_dem = A_norm[:k], B_norm[:k]
D = levenshtein.matriz_completa(a_dem, b_dem)
p(f"**Demostración paso a paso.** Por legibilidad la matriz se muestra para los primeros {k} "
  f"caracteres normalizados de cada abstract: A = \"{a_dem}\" y B = \"{b_dem}\".")
tabla(["", "ε"] + [mostrar(c) for c in b_dem],
      [["ε"] + D[0]] + [[mostrar(a_dem[i - 1])] + D[i] for i in range(1, k + 1)], tam=7.5)
celdas = [(1, 1), (1, 3), (2, 2), (3, 4)]
for (i, j) in celdas:
    costo = 0 if a_dem[i - 1] == b_dem[j - 1] else 1
    p(f"• D[{i}][{j}] ('{mostrar(a_dem[i - 1])}' vs '{mostrar(b_dem[j - 1])}'): "
      f"mín(D[{i - 1}][{j}]+1 = {D[i - 1][j] + 1}, D[{i}][{j - 1}]+1 = {D[i][j - 1] + 1}, "
      f"D[{i - 1}][{j - 1}]+{costo} = {D[i - 1][j - 1] + costo}) = {D[i][j]}", tam=10)
ops = levenshtein.operaciones(a_dem, b_dem, D)
p("Camino óptimo reconstruido (= coincide, S sustitución, E eliminación, I inserción): " +
  " ".join(f"{o[0]}" for o in ops) + f". Distancia del fragmento = {D[k][k]}.")
d_full = levenshtein.distancia(A_norm, B_norm)
sim_lev = 1 - d_full / max(len(A_norm), len(B_norm))
p(f"**Resultado sobre los abstracts completos:** n = {len(A_norm)}, m = {len(B_norm)} caracteres, "
  f"la matriz tiene {(len(A_norm) + 1) * (len(B_norm) + 1):,} celdas; D[n][m] = {d_full} y "
  f"sim = 1 − {d_full}/{max(len(A_norm), len(B_norm))} = **{sim_lev:.4f}**.")

# ---- 4.2 Needleman-Wunsch
h("4.2 Alineamiento global de Needleman-Wunsch (programación dinámica)", 2)
p("Needleman-Wunsch (1970) busca el alineamiento global de máximo puntaje entre dos secuencias "
  "(aquí, secuencias de palabras). Se usa match = +1, mismatch = −1 y hueco g = −1. A diferencia "
  "de Levenshtein, además del valor óptimo se reconstruye el alineamiento recorriendo la matriz "
  "desde F[n][m] hasta F[0][0] (traceback).")
ecuacion("F[i][0] = i·g ;  F[0][j] = j·g")
ecuacion("F[i][j] = máx{ F[i−1][j−1] + s(aᵢ,bⱼ) ,  F[i−1][j] + g ,  F[i][j−1] + g }")
ecuacion("identidad = coincidencias / longitud del alineamiento")
p("**Complejidad.** Llenado de la matriz: T(n,m) = c·n·m + O(n+m) ⇒ O(n·m). Traceback: O(n+m). "
  "Espacio O(n·m), porque el traceback necesita la matriz de direcciones.")
k = 7
ta, tb = A_tok[:k], B_tok[:k]
r = needleman_wunsch.alinear(ta, tb, guardar_matriz=True)
p(f"**Demostración paso a paso** con las primeras {k} palabras preprocesadas: "
  f"A = {ta}; B = {tb}.")
tabla(["", "ε"] + tb, [["ε"] + r.matriz[0]] + [[ta[i - 1]] + r.matriz[i] for i in range(1, k + 1)],
      tam=7)
i, j = 2, 3
p(f"Ejemplo de celda F[{i}][{j}] ('{ta[i - 1]}' vs '{tb[j - 1]}'): máx(F[{i - 1}][{j - 1}] + "
  f"s = {r.matriz[i - 1][j - 1]} + {1 if ta[i - 1] == tb[j - 1] else -1}, F[{i - 1}][{j}] − 1 = "
  f"{r.matriz[i - 1][j] - 1}, F[{i}][{j - 1}] − 1 = {r.matriz[i][j - 1] - 1}) = {r.matriz[i][j]}.",
  tam=10)
tabla(["A"] + r.alineado_a, [["B"] + r.alineado_b], tam=7)
p(f"Puntaje F[{k}][{k}] = {r.puntaje}; coincidencias = {r.coincidencias}; identidad = "
  f"{r.identidad:.4f}.")
rc = needleman_wunsch.alinear(A_tok, B_tok)
p(f"**Resultado sobre los abstracts completos** ({len(A_tok)} y {len(B_tok)} tokens): puntaje "
  f"{rc.puntaje}, {rc.coincidencias} coincidencias, {rc.sustituciones} sustituciones, {rc.huecos} "
  f"huecos; identidad = **{rc.identidad:.4f}** (puntaje normalizado {rc.puntaje_normalizado:.4f}).")

# ---- 4.3 TF-IDF
h("4.3 Similitud del coseno con TF-IDF (modelo de espacio vectorial)", 2)
p("Cada abstract se representa como un vector con un peso por término. TF mide cuán frecuente es "
  "el término en el documento e IDF penaliza los términos comunes a muchos documentos del corpus "
  "(N = 20). La similitud es el coseno del ángulo entre los dos vectores.")
ecuacion("tf(t,d) = f(t,d) / |d|      idf(t) = ln((1+N)/(1+df(t))) + 1      w(t,d) = tf·idf")
ecuacion("cos θ = Σₜ w(t,A)·w(t,B) / ( √Σₜ w(t,A)² · √Σₜ w(t,B)² )")
p("**Complejidad.** Construir el modelo recorre todos los tokens del corpus una vez: O(T). El "
  "vector de un documento es O(|d|). El producto punto recorre el diccionario más pequeño y consulta "
  "el otro en O(1) promedio: O(mín(|A|,|B|)), y cada norma O(|A|). Con vectores densos de tamaño V "
  "(vocabulario) sería O(V).")
det = tfidf_coseno.detalle(modelo_tfidf(), A_tok, B_tok)
comunes = sorted([f for f in det["filas"] if f["w_A*w_B"] > 0], key=lambda f: -f["w_A*w_B"])
p(f"**Demostración paso a paso.** |A| = {det['n_tokens_A']} tokens, |B| = {det['n_tokens_B']} tokens. "
  f"Hay {len(comunes)} términos compartidos (solo ellos aportan al producto punto). Ejemplo para "
  f"el término '{comunes[0]['termino']}': f(A) = {comunes[0]['f_A']}, tf(A) = {comunes[0]['f_A']}/"
  f"{det['n_tokens_A']} = {comunes[0]['tf_A']:.4f}; aparece en df = {comunes[0]['df']} abstracts, "
  f"idf = ln(21/{1 + comunes[0]['df']}) + 1 = {comunes[0]['idf']:.4f}; w(A) = "
  f"{comunes[0]['tf_A']:.4f} × {comunes[0]['idf']:.4f} = {comunes[0]['w_A']:.4f}.")
tabla(["término", "f_A", "f_B", "df", "idf", "w_A", "w_B", "w_A·w_B"],
      [[f["termino"], f["f_A"], f["f_B"], f["df"], f["idf"], f["w_A"], f["w_B"],
        f"{f['w_A*w_B']:.6f}"] for f in comunes], tam=7.5)
p(f"Producto punto Σ w_A·w_B = {det['producto_punto']:.6f}; ‖A‖ = {det['norma_A']:.6f}; "
  f"‖B‖ = {det['norma_B']:.6f}.")
p(f"cos θ = {det['producto_punto']:.6f} / ({det['norma_A']:.6f} × {det['norma_B']:.6f}) = "
  f"**{det['coseno']:.4f}**  ⇒  θ = arccos({det['coseno']:.4f}) = **{det['angulo']:.2f}°**.")

# ---- 4.4 Jaccard
h("4.4 Coeficiente de Jaccard (modelo de conjuntos)", 2)
ecuacion("J(A,B) = |A ∩ B| / |A ∪ B| = |A ∩ B| / (|A| + |B| − |A ∩ B|)")
p("Cada abstract se representa como el conjunto de sus términos (sin repeticiones ni pesos). "
  "**Complejidad:** construir los conjuntos O(|A|+|B|); la intersección recorre el conjunto menor "
  "con búsquedas O(1) en tabla hash: O(mín(|A|,|B|)) en promedio.")
dj = jaccard.detalle(set(A_tok), set(B_tok))
p(f"|A| = {dj['A']} términos distintos, |B| = {dj['B']}, |A ∩ B| = {dj['n_interseccion']}, "
  f"|A ∪ B| = {dj['A']} + {dj['B']} − {dj['n_interseccion']} = {dj['n_union']}.")
p("A ∩ B = {" + ", ".join(dj["interseccion"]) + "}")
p(f"J(A,B) = {dj['n_interseccion']}/{dj['n_union']} = **{dj['jaccard']:.4f}**.")

# ---- 4.5 Embeddings
h("4.5 Modelos de IA: embeddings preentrenados GloVe y FastText", 2)
p("Los dos modelos de IA representan cada palabra como un vector denso aprendido de grandes "
  "corpus, de modo que palabras que aparecen en contextos parecidos quedan cerca en el espacio "
  "vectorial (hipótesis distribucional). Se usan modelos preentrenados, sin reentrenarlos:")
viñeta("**GloVe (glove-wiki-gigaword-100)**, Pennington, Socher y Manning (2014): factoriza la "
       "matriz global de co-ocurrencias palabra-palabra de Wikipedia 2014 + Gigaword 5 (6 000 "
       "millones de tokens). 400 000 palabras, 100 dimensiones.")
viñeta("**FastText (fasttext-wiki-news-subwords-300)**, Bojanowski et al. (2017) y Mikolov et al. "
       "(2018): modelo skip-gram/CBOW que representa cada palabra como suma de n-gramas de "
       "caracteres; entrenado con Wikipedia 2017, UMBC y noticias (16 000 millones de tokens). "
       "1 millón de palabras, 300 dimensiones.")
p("Ambos se obtienen del repositorio público gensim-data. Para no exigir la descarga completa "
  "(≈1,1 GB) cada vez, scripts/construir_embeddings.py guarda solo los vectores de las ≈1 100 "
  "palabras del corpus; los valores son idénticos a los originales.")
p("**Vector del abstract (mean pooling)** y medidas:")
ecuacion("v(d) = (1/k) Σᵢ e(wᵢ)      cos(u,v) = u·v / (‖u‖‖v‖)      dₑ(u,v) = √Σ(uᵢ − vᵢ)²")
p("**Complejidad.** Buscar cada palabra en la tabla hash es O(1); el promedio cuesta O(k·dim) y el "
  "coseno O(dim). Para dos abstracts de ~100 palabras y dim = 300 son unas 60 000 operaciones, muy "
  "por debajo de Levenshtein (más de 10⁶ celdas). El costo real está en el entrenamiento del "
  "modelo, que ya viene hecho (preentrenado).")
filas_ia = []
for nombre in ("glove100", "fasttext300"):
    m = cargar_modelo(nombre)
    u, usa, oova = m.vector_documento(tokens_ia(A_txt))
    v, usb, oovb = m.vector_documento(tokens_ia(B_txt))
    pp = sum(u[i] * v[i] for i in range(m.dimension))
    filas_ia.append((m, u, v, usa, usb, oova, oovb, pp))
    p(f"**{m.descripcion}.** A: {len(usa)} palabras con vector (fuera de vocabulario: "
      f"{oova if oova else 'ninguna'}); B: {len(usb)} palabras (fuera de vocabulario: "
      f"{oovb if oovb else 'ninguna'}).")
    p("Primeras 5 componentes: v(A) = [" + ", ".join(f"{x:.4f}" for x in u[:5]) + ", …]; v(B) = [" +
      ", ".join(f"{x:.4f}" for x in v[:5]) + ", …].", tam=10)
    parcial = sum(u[i] * v[i] for i in range(5))
    p(f"Producto punto: las 5 primeras componentes aportan " +
      " + ".join(f"({u[i]:.4f}·{v[i]:.4f})" for i in range(3)) + f" + … = {parcial:.4f}; "
      f"sumando las {m.dimension} componentes, u·v = {pp:.4f}; ‖u‖ = {math.sqrt(sum(x * x for x in u)):.4f}, "
      f"‖v‖ = {math.sqrt(sum(x * x for x in v)):.4f}.", tam=10)
    p(f"cos = **{coseno(u, v):.4f}**; distancia euclidiana = {euclidiana(u, v):.4f}.")

# ---- 4.6 Análisis crítico
h("4.6 Análisis crítico: clásicos frente a IA", 2)
caso = {alg: similitud_par(alg, A_txt, B_txt)["similitud"] for alg in ALGORITMOS}
tabla(["Algoritmo", "Tipo", f"sim([{ID_A}],[{ID_B}])", "Media en 190 pares", "Mín", "Máx",
       "Posición del par (de 190)"],
      [[ALGORITMOS[a], "IA" if a in ("glove", "fasttext") else "Clásico", caso[a],
        sum(sim_global[a]) / len(sim_global[a]), min(sim_global[a]), max(sim_global[a]),
        1 + sum(1 for x in sim_global[a] if x > caso[a])] for a in ALGORITMOS], tam=8)
p("La tabla anterior compara el caso de estudio con la distribución de las 190 parejas posibles "
  "del corpus (resultados completos en docs/resultados/similitud_190_pares.csv). La columna "
  "'posición' indica el lugar que ocupa el par en el ranking de cada algoritmo (1 = el más "
  "parecido), lo que permite comparar algoritmos con escalas distintas.")
nombres = list(ALGORITMOS)
tabla(["Spearman"] + [ALGORITMOS[a].split(" ")[0] if not a in ("glove", "fasttext") else a
                      for a in nombres],
      [[ALGORITMOS[a].split(" ")[0] if a not in ("glove", "fasttext") else a] +
       [f"{spearman(sim_global[a], sim_global[b]):.3f}" for b in nombres] for a in nombres], tam=8)
p("Observaciones:")
rank = {a: 1 + sum(1 for x in sim_global[a] if x > caso[a]) for a in ALGORITMOS}
viñeta(f"**Escala.** Los métodos léxicos dan valores bajos (Jaccard {caso['jaccard']:.3f}, "
       f"Needleman-Wunsch {caso['needleman_wunsch']:.3f}, coseno TF-IDF {caso['tfidf_coseno']:.3f}), "
       f"mientras que los embeddings dan valores muy altos (GloVe {caso['glove']:.3f}, FastText "
       f"{caso['fasttext']:.3f}). Esto no significa que la IA 'acierte más': el promedio de vectores "
       "de palabras de un mismo dominio (educación, IA, evaluación) concentra todos los abstracts en "
       "una región estrecha del espacio (anisotropía), por lo que el coseno rara vez baja de "
       f"{min(sim_global['glove']):.2f}. Lo informativo es el **orden relativo**, no el valor absoluto.")
top_glove = sorted(zip(pares, sim_global["glove"]), key=lambda x: -x[1])[:3]
viñeta(f"**Ranking y desacuerdo entre enfoques.** El par ({ID_A},{ID_B}) ocupa la posición "
       f"{rank['tfidf_coseno']} de 190 con TF-IDF y {rank['needleman_wunsch']} con Needleman-Wunsch, "
       "es decir, entre los pares más parecidos del corpus, lo que coincide con la lectura humana: "
       "ambos tratan cómo la IA generativa obliga a rediseñar la evaluación en educación superior. "
       f"En cambio, Jaccard lo ubica en la posición {rank['jaccard']}, GloVe en la {rank['glove']} y "
       f"FastText en la {rank['fasttext']}. Jaccard da el mismo peso a todos los términos, de modo "
       "que coincidir en 'assessment' o 'integrity' vale lo mismo que coincidir en 'provide'; TF-IDF "
       "corrige eso con el IDF y por eso el término 'assessment' (8 y 6 apariciones) domina su "
       "producto punto. El promedio de embeddings, por su parte, está dominado por las palabras "
       "frecuentes y generales del abstract: el artículo 11 es una revisión de alcance con "
       "vocabulario metodológico (scoping review, PRISMA, articles, screening) y el 16 es un ensayo "
       "conceptual (plagiarism, cheating, hallucination, policing). Los pares que GloVe considera más "
       "parecidos son revisiones sistemáticas entre sí (p. ej. " +
       ", ".join(f"{a}-{b}" for (a, b), _ in top_glove) + "), es decir, los embeddings promediados "
       "capturan sobre todo el tipo de documento y su registro, más que el tema específico.")
viñeta(f"**Distancia de edición.** Levenshtein (posición {rank['levenshtein']}) y Needleman-Wunsch "
       f"(posición {rank['needleman_wunsch']}) miden el orden de los símbolos, no el tema: dos "
       "abstracts sobre el mismo asunto escritos con distinta estructura obtienen valores parecidos "
       "a los de un par sin relación. Además, para textos en lenguaje natural Levenshtein queda "
       f"acotado en la práctica a ≈{min(sim_global['levenshtein']):.2f}–"
       f"{max(sim_global['levenshtein']):.2f} porque letras frecuentes (e, a, t, espacio) coinciden "
       "por azar. Son adecuados para detectar copia literal o variantes cercanas de una misma "
       "frase, no para similitud temática.")
viñeta("**Sinonimia y morfología.** TF-IDF y Jaccard solo cuentan coincidencias exactas de "
       "términos: 'higher education' frente a 'tertiary education' o 'cheating' frente a "
       "'integrity' no suman. Los embeddings sí capturan esa cercanía semántica, y FastText además "
       "comparte información entre formas de una misma palabra gracias a los n-gramas de caracteres.")
viñeta("**Costo computacional.** Levenshtein a nivel carácter es el más costoso (O(n·m), más de un "
       "millón de celdas por par); Needleman-Wunsch a nivel palabra reduce el tamaño a ~10⁴ celdas. "
       "TF-IDF y Jaccard son casi lineales y los embeddings, una vez cargado el modelo, también.")
viñeta("**Limitaciones de los modelos de IA usados.** El mean pooling ignora el orden de las "
       "palabras y la negación; los modelos estáticos asignan un único vector por palabra (no "
       "distinguen sentidos). Modelos contextuales tipo Sentence-BERT darían representaciones más "
       "discriminativas, a cambio de requerir redes neuronales de cientos de MB y GPU/CPU potente.")

# ----------------------------------------------------------------- 5
doc.add_page_break()
h("5. Requerimiento 2: agrupamiento jerárquico", 1)
p("**Pipeline.** abstract → preprocesamiento (sección 3) → vector TF-IDF de cada abstract → matriz "
  "de distancias D(i,j) = 1 − cos(i,j) de 20 × 20 → clustering aglomerativo → dendrograma → "
  "evaluación interna. Como representación alternativa se usan también los vectores de GloVe y "
  "FastText (Req. 1), con la misma distancia coseno.")
h("5.1 Algoritmo aglomerativo y criterios de enlace", 2)
p("Cada abstract empieza como un clúster. En cada uno de los n − 1 pasos se fusiona el par de "
  "clústeres más cercano y se actualiza la distancia del nuevo clúster r = p ∪ q a los demás con la "
  "fórmula de Lance-Williams:")
ecuacion("d(r,k) = αₚ·d(p,k) + α_q·d(q,k) + β·d(p,q) + γ·|d(p,k) − d(q,k)|")
tabla(["Criterio", "αₚ", "α_q", "β", "γ", "Equivale a"], [
    ["Single", "1/2", "1/2", "0", "−1/2", "mín(d(p,k), d(q,k)): vecino más cercano"],
    ["Complete", "1/2", "1/2", "0", "+1/2", "máx(d(p,k), d(q,k)): vecino más lejano"],
    ["Average (UPGMA)", "nₚ/(nₚ+n_q)", "n_q/(nₚ+n_q)", "0", "0", "promedio de todas las distancias entre pares"],
    ["Ward (referencia)", "(nₚ+nₖ)/N", "(n_q+nₖ)/N", "−nₖ/N", "0", "mínimo aumento de varianza"],
], tam=8)
codigo("""para paso = 1 .. n-1:
    (p, q) <- par activo con menor dist[p][q]        # recorre O(k²) pares, k = clústeres activos
    registrar fusión (p, q, dist[p][q], tamaño)
    para cada clúster activo k distinto de p, q:     # O(k)
        dist[r][k] <- LanceWilliams(dist[p][k], dist[q][k], dist[p][q], tamaños)
    eliminar p y q; activar r""")
p("**Tiempo de ejecución.** En el paso con k clústeres activos, la búsqueda del mínimo hace "
  "k(k−1)/2 comparaciones y la actualización O(k). Sumando para k = n, n−1, …, 2: "
  "T(n) = Σₖ k(k−1)/2 + O(k) = (n³ − n)/6 + O(n²) ⇒ **O(n³)** en tiempo y **O(n²)** en espacio. "
  f"Para n = 20 son {sum(k * (k - 1) // 2 for k in range(2, 21))} comparaciones en la búsqueda "
  "de mínimos. (Con una cola de prioridad se podría bajar a O(n² log n), innecesario para n = 20.) "
  "La matriz de distancias previa cuesta O(n²·V) con V términos por vector.")
p("**Validación.** Las alturas de fusión y la correlación cofenética de la implementación propia "
  "coinciden con scipy.cluster.hierarchy.linkage para los cuatro criterios (ver tests/).")
r_avg = res_cluster[("average", "tfidf")]
p("Primeras fusiones del criterio average sobre TF-IDF (los ids ≥ 20 son clústeres internos):")
tabla(["Paso", "Clúster a", "Clúster b", "Distancia", "Tamaño", "Nuevo id"],
      [[f.paso, f.a if f.a >= 20 else f"[{CORPUS[f.a]['id']}]",
        f.b if f.b >= 20 else f"[{CORPUS[f.b]['id']}]", f.distancia, f.tamano, f.nuevo]
       for f in r_avg["fusiones"][:8]], tam=8)

h("5.2 Dendrogramas", 2)
for c in ("single", "complete", "average"):
    figura(FIG / f"dendrograma_tfidf_{c}.png", 15.5,
           f"Dendrograma {jerarquico.CRITERIOS[c]} sobre TF-IDF (colores: corte en k = "
           f"{res_cluster[(c, 'tfidf')]['mejor_k']} grupos, elegido por silueta).")

h("5.3 Evaluación interna y elección del mejor algoritmo", 2)
p("Al no existir etiquetas reales de los grupos, la coherencia se evalúa con métricas internas:")
viñeta("**Coeficiente de correlación cofenética (CCC)**, Sokal y Rohlf (1962): correlación de "
       "Pearson entre la distancia original d(i,j) y la distancia cofenética c(i,j) (altura del "
       "dendrograma donde i y j se unen por primera vez). Mide qué tan fielmente el árbol completo "
       "conserva las distancias; 1 es perfecto. Se calcula sobre los 190 pares: O(n²).")
viñeta("**Coeficiente de silueta**, Rousseeuw (1987), para el corte del árbol en k grupos: "
       "s(i) = (b(i) − a(i)) / máx(a(i), b(i)), donde a(i) es la distancia media de i a su propio "
       "grupo y b(i) la menor distancia media a otro grupo. Rango [−1, 1]; mide compacidad y "
       "separación de la partición. O(n²) por cada k.")
filas = []
for rep in REPRESENTACIONES:
    for c in ("single", "complete", "average", "ward"):
        r = res_cluster[(c, rep)]
        filas.append([REPRESENTACIONES[rep].split(" +")[0].split(" (")[0], jerarquico.CRITERIOS[c].split(" (")[0],
                      r["ccc"], r["siluetas"][2], r["siluetas"][3], r["siluetas"][4], r["siluetas"][5],
                      r["mejor_k"]])
tabla(["Repr.", "Criterio", "CCC", "Sil k=2", "Sil k=3", "Sil k=4", "Sil k=5", "k*"], filas, tam=8)
guardar_csv("clustering_metricas.csv", [dict(zip(["representacion", "criterio", "ccc", "sil2", "sil3",
                                                    "sil4", "sil5", "k_mejor"], f)) for f in filas])
mejor = max((res_cluster[(c, "tfidf")] for c in ("single", "complete", "average")),
            key=lambda r: r["ccc"])
p(f"**Conclusión.** Con la representación TF-IDF, el criterio con mayor correlación cofenética es "
  f"**{jerarquico.CRITERIOS[mejor['criterio']]}** (CCC = {mejor['ccc']:.4f}), y se mantiene como "
  "el mejor también con GloVe y FastText. Es el resultado esperado: el enlace promedio usa todas "
  "las distancias entre miembros, de modo que la altura de cada fusión es un promedio de las "
  "distancias reales (no un extremo), y por eso el árbol las reproduce mejor. Single linkage "
  "produce el efecto de encadenamiento (los abstracts se van añadiendo de a uno a un único grupo "
  "grande), visible en su dendrograma; complete linkage obtiene grupos más compactos pero distorsiona "
  "más las distancias (menor CCC).")
p("Los valores de silueta con TF-IDF son bajos (< 0,1): los 20 abstracts pertenecen a un mismo "
  "dominio (IA en educación) y comparten gran parte del vocabulario, por lo que no forman grupos "
  "muy separados. Con embeddings la silueta es mayor porque las distancias se distribuyen de forma "
  "más contrastada. Aun así, average linkage identifica grupos temáticos interpretables, por ejemplo "
  "los artículos de evaluación con IA generativa (11, 16, 17) y las revisiones bibliométricas "
  "generales de AIEd (2, 5, 6, 9, 12, 20).")
figura(FIG / "dendrograma_glove_average.png", 15.5,
       "Dendrograma average linkage sobre embeddings GloVe (representación de IA).")

# ----------------------------------------------------------------- 6
doc.add_page_break()
h("6. Requerimiento 3: búsqueda de patrones (coincidencia exacta)", 1)
texto_completo = ART_A["abstract"]
ini = texto_completo.find("Existing")
fin = texto_completo.find("We used the PRISMA")
T = texto_completo[ini:fin].strip().lower()
P = PATRON
p(f"**Caso de estudio.** Patrón P = \"{P}\" (m = {len(P)}) y texto T tomado del abstract [{ID_A}] "
  f"(en minúsculas, n = {len(T)}):")
codigo(T)
p("En la aplicación, la búsqueda se ejecuta sobre los 20 abstracts y muestra cada ocurrencia en "
  "contexto. Las tres implementaciones se verificaron contra una búsqueda por fuerza bruta en 2 000 "
  "casos aleatorios (tests/).")

# ---- KMP
h("6.1 Knuth-Morris-Pratt (KMP)", 2)
p("KMP evita retroceder en el texto: cuando ocurre un desajuste después de casar q caracteres, usa "
  "la función de fallo π para saber cuál es el prefijo más largo del patrón que sigue casando, y "
  "continúa desde ahí.")
ecuacion("π[q] = máx{ k < q+1 : P[0..k−1] es sufijo de P[0..q] }")
pi = kmp.tabla_fallo(P)
tabla(["q"] + [str(i) for i in range(len(P))],
      [["P[q]"] + list(P), ["π[q]"] + [str(x) for x in pi]], tam=8)
p("Cálculo de la tabla: π[0] = 0 por definición. Para q = 1 ('as') el único prefijo propio es "
  "'a' y el sufijo correspondiente es 's' ⇒ π[1] = 0; para q = 2 ('ass') los prefijos 'a', 'as' "
  "no coinciden con los sufijos 's', 'ss' ⇒ 0; y así sucesivamente: todo prefijo propio de "
  "'assessment' empieza por 'a', y la 'a' solo aparece en la posición 0, de modo que ningún prefijo "
  "es también sufijo y **π es toda ceros**. En consecuencia, cada vez que hay un desajuste el patrón "
  "vuelve a P[0], pero el índice i del texto nunca retrocede; en un patrón con bordes (p. ej. "
  "'ababaca', π = [0,0,1,2,3,0,1]) KMP sí aprovecharía las coincidencias parciales.")
rk = kmp.buscar(T, P, trazar=True)
importantes = [s for s in rk.pasos if s["accion"] in ("fallo", "ocurrencia") or s["q"] >= 3][:30]
tabla(["i", "T[i]", "q", "acción", "detalle"],
      [[s["i"], mostrar(T[s["i"]]), s["q"], s["accion"], s["detalle"]] for s in importantes], tam=7.5)
p(f"Ocurrencias en {rk.posiciones}. Comparaciones de caracteres: {rk.comparaciones} (cota 2n = "
  f"{2 * len(T)}). La tabla muestra los pasos con coincidencias parciales de 3 o más caracteres, "
  "fallos con retroceso del patrón y ocurrencias; la traza completa está en la aplicación.")
p("**Complejidad.** Preprocesamiento: el ciclo de la tabla de fallo avanza q de 1 a m−1 y la "
  "variable k solo puede disminuir tantas veces como aumentó ⇒ T(m) ≤ 2m ⇒ **O(m)**. Búsqueda: "
  "i avanza n veces y q disminuye a lo sumo tantas veces como aumentó ⇒ ≤ 2n comparaciones ⇒ "
  "**O(n)**. Total **Θ(n + m)** en el peor caso, independientemente del alfabeto; espacio O(m).")

# ---- BM
h("6.2 Boyer-Moore", 2)
p("Boyer-Moore compara el patrón de derecha a izquierda y, ante un desajuste, salta usando dos "
  "heurísticas precalculadas; el salto aplicado es el máximo de ambas.")
ult = boyer_moore.tabla_caracter_malo(P)
desp, borde = boyer_moore.tabla_sufijo_bueno(P)
p("**Regla del carácter malo:** ult[c] = última posición de c en P (−1 si no aparece). Si el "
  "desajuste ocurre en P[j] frente al carácter c del texto, se desplaza j − ult[c] (mínimo 1).")
tabla(["c"] + [mostrar(c) for c in ult] + ["otro"], [["ult[c]"] + [str(v) for v in ult.values()] + ["−1"]],
      tam=8)
p("**Regla del sufijo bueno (versión fuerte):** si ya casó el sufijo u = P[j+1..m−1], se desplaza "
  "hasta la siguiente aparición de u precedida por un carácter distinto, o hasta el prefijo más "
  "largo de P que sea sufijo de u. bs[j] indica el desplazamiento cuando el desajuste se produce en "
  "j−1 (bs[m] corresponde a no haber casado nada; bs[0] se usa tras una ocurrencia completa).")
tabla(["j"] + [str(i) for i in range(len(P) + 1)], [["bs[j]"] + [str(x) for x in desp],
                                                     ["borde[j]"] + [str(x) for x in borde]], tam=8)
rb = boyer_moore.buscar(T, P, trazar=True)
p("**Iteraciones sobre el texto** (s = alineación del patrón; j = posición del desajuste):")
tabla(["#", "s", "j", "c = T[s+j]", "carácter malo", "sufijo bueno", "desplazamiento"],
      [[k + 1, st["s"], st["j"], mostrar(st.get("caracter", "")) if st["j"] >= 0 else "—",
        st.get("cm", "—"), st.get("sb", "—"), st["desplazamiento"]] for k, st in enumerate(rb.pasos)],
      tam=7.5)


def figura_bm(pasos, texto, patron, archivo, max_filas=12):
    filas = pasos[:max_filas]
    fig, ax = plt.subplots(figsize=(13, 0.42 * (len(filas) + 2)))
    ax.axis("off")
    ventana = min(len(texto), max(st["s"] for st in filas) + len(patron) + 2)
    for x in range(ventana):
        ax.text(x, len(filas) + 0.6, mostrar(texto[x]), ha="center", fontsize=7, family="monospace")
    for fila, st in enumerate(filas):
        y = len(filas) - fila - 0.4
        for jj, ch in enumerate(patron):
            color = "#16a34a"
            if st["j"] >= 0 and jj == st["j"]:
                color = "#dc2626"
            elif st["j"] >= 0 and jj < st["j"]:
                color = "#94a3b8"
            ax.text(st["s"] + jj, y, ch, ha="center", fontsize=7, family="monospace", color=color)
        ax.text(-1.5, y, f"s={st['s']}", ha="right", fontsize=7)
        ax.text(st["s"] + len(patron) + 0.5, y, f"→ +{st['desplazamiento']}", fontsize=7, color="#2563eb")
    ax.set_xlim(-6, ventana + 6)
    ax.set_ylim(-0.5, len(filas) + 1.2)
    ax.set_title("Boyer-Moore: alineaciones (rojo = desajuste, verde = coincidencia comparada, "
                 "gris = no comparado)", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / archivo, dpi=170)
    plt.close(fig)


figura_bm(rb.pasos, T, P, "boyer_moore_iteraciones.png")
figura(FIG / "boyer_moore_iteraciones.png", 16.5,
       "Figura: primeras alineaciones de Boyer-Moore sobre el texto del caso de estudio.")
p(f"Ocurrencias en {rb.posiciones}. Alineaciones probadas: {len(rb.pasos)} (la fuerza bruta "
  f"probaría {len(T) - len(P) + 1}); comparaciones de caracteres: {rb.comparaciones} frente a "
  f"{rk.comparaciones} de KMP. La mayoría de desplazamientos son de m = {len(P)} posiciones porque "
  "el carácter del texto no aparece en 'assessment'.")
p("**Complejidad.** Preprocesamiento: carácter malo O(m + σ) y sufijo bueno O(m) ⇒ O(m + σ). "
  "Búsqueda: mejor caso **O(n/m)** (sublineal: cada alineación descarta m caracteres con una sola "
  "comparación); peor caso **O(n·m)** con solo carácter malo (p. ej. T = aⁿ, P = b·a^(m−1)) y "
  "**O(n + m)** con la regla del sufijo bueno fuerte (Cole, 1994) para hallar ocurrencias no "
  "periódicas. Espacio O(m + σ).")

# ---- RK
h("6.3 Rabin-Karp", 2)
p("Rabin-Karp compara huellas numéricas (hash) en lugar de caracteres: la ventana de m caracteres "
  "se interpreta como un número en base d = 256 módulo un primo q, y el hash de la siguiente "
  "ventana se obtiene en O(1) (rolling hash). Solo cuando los hashes coinciden se verifica "
  "carácter a carácter, para descartar colisiones (falsos positivos).")
ecuacion("h(S) = (S[0]·d^(m−1) + … + S[m−1]) mod q   (método de Horner)")
ecuacion("h(Tₛ₊₁) = ( d·(h(Tₛ) − T[s]·dᵐ⁻¹) + T[s+m] ) mod q")
q_demo = 37
rr = rabin_karp.buscar(T, P, q=q_demo, trazar=True)
p(f"Con un primo pequeño, q = {q_demo}, para hacer visibles las colisiones: "
  f"dᵐ⁻¹ mod q = 256⁹ mod {q_demo} = {rr.extra['h']}. Cálculo iterativo del hash del patrón (Horner):")
codigo("\n".join(rr.extra["pasos_hash_patron"]))
p(f"hash(P) = {rr.extra['hash_patron']}. Primeras ventanas del texto y sus hashes:")
primeras = rr.pasos[:6]
tabla(["s", "ventana", "hash", "resultado"], [[st["s"], st["ventana"], st["hash"], st["accion"]]
                                             for st in primeras], tam=8)
s0 = rr.pasos[0]
s1 = rr.pasos[1]
p(f"Ejemplo de rolling hash de s = 0 a s = 1: (256·({s0['hash']} − ord('{T[0]}')={ord(T[0])}·"
  f"{rr.extra['h']}) + ord('{T[len(P)]}')={ord(T[len(P)])}) mod {q_demo} = {s1['hash']}.", tam=10)
marcados = [st for st in rr.pasos if st["accion"] != "distinto"]
tabla(["s", "ventana", "hash", "resultado"], [[st["s"], st["ventana"], st["hash"], st["accion"]]
                                             for st in marcados], tam=8)
p(f"Con q = {q_demo} hubo {rr.extra['verificaciones']} ventanas con hash igual al del patrón: "
  f"{len(rr.posiciones)} ocurrencias reales y **{rr.extra['colisiones']} colisiones** (ventanas "
  "distintas con el mismo hash, que la verificación descarta). Con q = 1 000 000 007 (valor por "
  f"defecto) el número de colisiones es {rabin_karp.buscar(T, P).extra['colisiones']}: la "
  "probabilidad de colisión por ventana es ≈ 1/q.")
p("**Complejidad.** Preprocesamiento: hash del patrón y de dᵐ⁻¹, **O(m)**. Búsqueda: n − m + 1 "
  "actualizaciones O(1) del hash + O(m) por cada verificación ⇒ **O(n + m)** esperado y **O(n·m)** "
  "en el peor caso (todas las ventanas colisionan, p. ej. q muy pequeño o texto adversario). "
  "Espacio O(1) adicional.")

# ---- análisis comparativo
h("6.4 Análisis crítico: complejidad teórica frente a rendimiento observado", 2)
tabla(["Algoritmo", "Preprocesamiento", "Búsqueda (mejor)", "Búsqueda (peor)", "Espacio"], [
    ["KMP", "Θ(m)", "Θ(n)", "Θ(n)", "O(m)"],
    ["Boyer-Moore", "O(m + σ)", "O(n/m)", "O(n·m) (solo c. malo) / O(n+m) (c. malo + s. bueno)", "O(m + σ)"],
    ["Rabin-Karp", "Θ(m)", "O(n + m)", "O(n·m)", "O(1)"],
], tam=8)
p(f"**Montaje experimental.** Python {platform.python_version()} en {platform.system()}; cada "
  "medición es la mediana de 5 ejecuciones; el texto es la concatenación de los 20 abstracts en "
  "minúsculas (28 274 caracteres), repetida para variar n. El tiempo de preprocesamiento y el de "
  "búsqueda se miden por separado dentro de cada algoritmo con time.perf_counter.")
figura(FIG / "bench_n_tiempo.png", 13, "Tiempo de búsqueda al crecer n (patrón 'assessment').")
tabla(["Algoritmo", "n", "Preproceso (ms)", "Búsqueda (ms)", "Comparaciones"],
      [[f["algoritmo"], f["n"], f"{f['preproceso_ms']:.4f}", f"{f['busqueda_ms']:.3f}",
        f["comparaciones"]] for f in bench_n], tam=8)
figura(FIG / "bench_m_tiempo.png", 13, "Tiempo de búsqueda al crecer la longitud del patrón m.")
figura(FIG / "bench_m_comparaciones.png", 13, "Comparaciones de caracteres al crecer m.")
tabla(["Algoritmo", "m", "patrón", "ocurr.", "Preproceso (ms)", "Búsqueda (ms)", "Comparaciones"],
      [[f["algoritmo"], f["m"], f["patron"], f["ocurrencias"], f"{f['preproceso_ms']:.4f}",
        f"{f['busqueda_ms']:.3f}", f["comparaciones"]] for f in bench_m], tam=7.5)
tabla(["Peor caso (T = aⁿ, P = b·a^(m−1))", "n", "m", "Comparaciones", "Búsqueda (ms)"],
      [[f["algoritmo"], f["n"], f["m"], f["comparaciones"], f"{f['busqueda_ms']:.3f}"] for f in bench_w],
      tam=8)
bm_n = [f for f in bench_n if f["algoritmo"] == "Boyer-Moore"]
kmp_n = [f for f in bench_n if f["algoritmo"] == "KMP"]
p("**Discusión.**")
viñeta("**Preprocesamiento vs. búsqueda.** El preprocesamiento de los tres algoritmos es "
       "despreciable frente a la búsqueda (microsegundos frente a milisegundos), porque m ≪ n: "
       "construir π, las tablas de Boyer-Moore o el hash del patrón cuesta O(m) con m ≤ 54, mientras "
       "que la búsqueda recorre decenas de miles de caracteres. Solo con muchos patrones cortos "
       "sobre textos pequeños el preprocesamiento tendría peso relativo (p. ej. σ en Boyer-Moore).")
viñeta(f"**Linealidad en n.** Los tres crecen linealmente con n, como predice la teoría: al pasar "
       f"de n = {kmp_n[0]['n']:,} a n = {kmp_n[-1]['n']:,} (×{kmp_n[-1]['n'] // kmp_n[0]['n']}) el "
       f"tiempo de KMP pasa de {kmp_n[0]['busqueda_ms']:.2f} a {kmp_n[-1]['busqueda_ms']:.2f} ms y el "
       f"de Boyer-Moore de {bm_n[0]['busqueda_ms']:.2f} a {bm_n[-1]['busqueda_ms']:.2f} ms.")
viñeta("**Efecto de m.** KMP hace ≈ n comparaciones sin importar m (Θ(n)). Boyer-Moore reduce sus "
       "comparaciones y su tiempo a medida que m crece, reflejando el comportamiento sublineal "
       "O(n/m): con el patrón de 54 caracteres compara menos de un 8 % de los caracteres del texto. "
       "Para patrones muy cortos ('ai', m = 2) los saltos son pequeños y la ventaja desaparece.")
viñeta("**Rabin-Karp** hace muy pocas comparaciones de caracteres (solo verifica ventanas con hash "
       "igual), pero es el más lento en tiempo real: cada una de las n − m + 1 ventanas requiere "
       "una multiplicación, una resta, una suma y un módulo con enteros grandes. Las constantes "
       "ocultas por la notación O importan: en la práctica Θ(n) operaciones aritméticas cuestan "
       "más que Θ(n) comparaciones de caracteres. Su ventaja real es buscar muchos patrones a la "
       "vez (comparando un hash contra un conjunto) o detectar plagio por huellas.")
bmw = {f["algoritmo"]: f for f in bench_w}
viñeta(f"**Peor caso.** Con T = aⁿ y P = b·a^(m−1), Boyer-Moore con solo la regla del carácter "
       f"malo hace {bmw['Boyer-Moore (solo carácter malo)']['comparaciones']:,} comparaciones "
       f"(≈ n·m), mientras que con la regla del sufijo bueno hace "
       f"{bmw['Boyer-Moore']['comparaciones']:,} y KMP {bmw['KMP']['comparaciones']:,} (≈ n). Esto "
       "confirma empíricamente el O(n·m) teórico y justifica implementar ambas heurísticas.")
viñeta("**Conclusión.** Para buscar un patrón en lenguaje natural (alfabeto amplio, m moderado) "
       "Boyer-Moore es el más rápido; KMP ofrece la garantía lineal más estable y no depende del "
       "alfabeto; Rabin-Karp es conceptualmente útil para búsqueda múltiple pero el más lento en "
       "Python para un solo patrón.")

# ----------------------------------------------------------------- 7 (Seguimiento 1)
doc.add_page_break()
h("7. Seguimiento 1: ranking de términos con ordenamiento no comparativo", 1)
pares_seg = ordenamiento.frecuencias_corpus()
k_seg = max(f for _, f in pares_seg)
p("El Seguimiento 1 del curso construyó un ranking de los términos más frecuentes de los abstracts "
  "con tres algoritmos de ordenamiento que no comparan elementos: Counting Sort, Radix Sort y "
  "Bucket Sort. Por indicación del docente hace parte del proyecto, de modo que se integró al "
  "código (src/ordenamiento/no_comparativos.py), a la aplicación (sección 'Seguimiento 1') y a este "
  "documento. Las implementaciones de los tres algoritmos se conservan tal como se entregaron en el "
  "seguimiento; lo que cambia es la entrada.")
h("7.1 Cambios respecto al informe del seguimiento", 2)
p("En el seguimiento el abstract se extraía con expresiones regulares sobre el texto plano que "
  "entrega pypdf (desde la palabra 'Abstract' hasta 'Keywords' o 'Introduction'). Con las 6 "
  "maquetaciones del corpus ese método falla en algunos artículos: en el informe, 'Human-centred "
  "learning analytics and AI in education' aparece con solo 12 palabras (el abstract real tiene "
  "226) y 'AI technologies for education' con 1 197 palabras (el texto siguió hasta la "
  "introducción porque ese artículo no tiene encabezado 'Introduction'; el abstract real tiene "
  "160). Esos errores inflaban el tamaño de la entrada (n = 1 180 términos, k = 98).")
p("En el proyecto el ranking usa el corpus validado de la sección 3 y las mismas reglas de "
  "limpieza del seguimiento: minúsculas, guiones como separadores, sin números, sin stopwords, "
  "sin stemming y descartando palabras de una o dos letras excepto 'ai'. La lista de stopwords es "
  "la del módulo de preprocesamiento (basada en la de NLTK), lo que evita depender de la descarga "
  f"de NLTK. Con la extracción corregida la entrada queda en **n = {len(pares_seg)} términos "
  f"distintos** y **k = {k_seg}**.")
car = ordenamiento.caracterizacion()
tabla(["ID", "Palabras del abstract", "Tokens tras preprocesamiento", "Términos únicos"],
      [[c["id"], c["palabras"], c["tokens"], c["unicos"]] for c in car] +
      [["Total", sum(c["palabras"] for c in car), sum(c["tokens"] for c in car), len(pares_seg)]],
      tam=8)
h("7.2 Algoritmos y complejidad", 2)
tabla(["Algoritmo", "Tiempo", "Espacio extra", "Estable", "Idea"], [
    ["Counting Sort", "Θ(n + k)", "O(n + k)", "Sí", "Contar cuántos términos tienen cada frecuencia, acumular "
     "y colocar cada par en su posición recorriendo la entrada de atrás hacia adelante."],
    ["Radix Sort (base 10)", "Θ(d·(n + 10)), d = dígitos de k", "O(n + 10)", "Sí", "Distribuir por "
     "unidades, decenas, ... en 10 cubetas por pasada; la estabilidad conserva el trabajo previo."],
    ["Bucket Sort", "O(n) promedio, O(n²) peor", "O(n + m)", "Sí (inserción estable)", "Repartir en m = n "
     "cubetas según la frecuencia y ordenar cada cubeta por inserción."],
], tam=8)
p(f"Para Counting Sort, con n = {len(pares_seg)} y k = {k_seg}: el conteo hace n incrementos, la "
  f"acumulación k sumas y la colocación n asignaciones, T(n,k) ≈ 2n + k + c, del orden de "
  f"{2 * len(pares_seg) + k_seg} operaciones dominantes. Radix hace d = {len(str(k_seg))} pasadas "
  "de n repartos cada una. Ninguno de los tres compara pares de elementos, por eso pueden romper "
  "la cota Ω(n log n) de los ordenamientos por comparación.")
tam_cub = ordenamiento.distribucion_cubetas(pares_seg)
p(f"**Efecto de la ley de Zipf en Bucket Sort.** Con m = n = {len(tam_cub)} cubetas, solo "
  f"{sum(1 for t in tam_cub if t)} quedan ocupadas y la primera recibe {tam_cub[0]} términos "
  f"({100 * tam_cub[0] / len(pares_seg):.1f} %): la mayoría de las palabras aparece una sola vez. "
  "Como esa cubeta contiene términos con la misma frecuencia, la inserción no desplaza nada y no "
  "llega al peor caso cuadrático, pero el algoritmo paga el costo de crear y recorrer n cubetas "
  "casi vacías.")
h("7.3 Resultados", 2)
print("Seguimiento: midiendo ordenamientos (1000 repeticiones)...")
med = {n: ordenamiento.medir(f, pares_seg, 1000) for n, f in ordenamiento.ALGORITMOS.items()}
base_f = [f for _, f in med["Counting Sort"]["resultado"]]
tabla(["Algoritmo", "Promedio (ms)", "Mínimo (ms)", "Máximo (ms)", "Misma secuencia de frecuencias"],
      [[n, f"{m['promedio_ms']:.4f}", f"{m['min_ms']:.4f}", f"{m['max_ms']:.4f}",
        "Sí" if [f for _, f in m["resultado"]] == base_f else "No"] for n, m in med.items()], tam=8.5)
exp_docs = ordenamiento.experimento_documentos(repeticiones=1000)
guardar_csv("seguimiento_tiempos_por_documentos.csv", exp_docs)
fig, ax = plt.subplots(figsize=(7.5, 4))
for alg in ordenamiento.ALGORITMOS:
    xs = [f["n"] for f in exp_docs if f["algoritmo"] == alg]
    ys = [f["promedio_ms"] for f in exp_docs if f["algoritmo"] == alg]
    ax.plot(xs, ys, marker="o", label=alg)
for f in exp_docs:
    if f["algoritmo"] == "Counting Sort":
        ax.annotate(f"{f['documentos']} docs", (f["n"], f["promedio_ms"]), fontsize=7,
                    textcoords="offset points", xytext=(0, -12))
ax.set_xlabel("n (términos distintos)")
ax.set_ylabel("tiempo promedio (ms)")
ax.set_title("Tiempo de ordenamiento vs n (5, 10, 15 y 20 documentos)", fontsize=10)
ax.grid(alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig(FIG / "seguimiento_tiempos.png", dpi=150)
plt.close(fig)
tabla(["Documentos", "n", "k", "Algoritmo", "Promedio (ms)"],
      [[f["documentos"], f["n"], f["k"], f["algoritmo"], f"{f['promedio_ms']:.4f}"] for f in exp_docs],
      tam=8)
figura(FIG / "seguimiento_tiempos.png", 13, "Crecimiento del tiempo de ordenamiento con el tamaño de la entrada.")
top15 = {n: ordenamiento.ranking(m["resultado"], 15) for n, m in med.items()}
tabla(["Posición", "Counting Sort", "Radix Sort", "Bucket Sort", "Frecuencia"],
      [[i + 1, top15["Counting Sort"][i][0], top15["Radix Sort"][i][0], top15["Bucket Sort"][i][0],
        top15["Counting Sort"][i][1]] for i in range(15)], tam=8.5)
fig, ax = plt.subplots(figsize=(7.5, 4.2))
terminos = [t for t, _ in top15["Counting Sort"]][::-1]
ax.barh(terminos, [f for _, f in top15["Counting Sort"]][::-1], color="#2563eb")
ax.set_xlabel("frecuencia en los 20 abstracts")
ax.set_title("Los 15 términos más frecuentes", fontsize=10)
fig.tight_layout()
fig.savefig(FIG / "seguimiento_top15.png", dpi=150)
plt.close(fig)
figura(FIG / "seguimiento_top15.png", 12, "Ranking de los 15 términos más frecuentes del corpus.")
orden_t = sorted(med, key=lambda n: med[n]["promedio_ms"])
c_ms, r_ms, b_ms = (med[n]["promedio_ms"] for n in ("Counting Sort", "Radix Sort", "Bucket Sort"))
p(f"**Discusión.** Bucket Sort es el más lento ({b_ms:.4f} ms, ≈{b_ms / min(c_ms, r_ms):.1f} veces "
  f"el más rápido), como anticipaba la hipótesis del seguimiento: crea n listas, reparte y "
  f"concatena, un costo constante alto en Python. Counting Sort ({c_ms:.4f} ms) y Radix Sort "
  f"({r_ms:.4f} ms) quedan muy cerca (diferencia de {abs(c_ms - r_ms) / min(c_ms, r_ms) * 100:.0f} %), "
  "y su orden relativo puede invertirse entre ejecuciones y equipos (en el informe del seguimiento "
  "Counting fue 1,1 % más rápido). Es coherente con la teoría: Counting hace dos recorridos de n "
  f"y uno de k = {k_seg}, mientras que Radix hace d = {len(str(k_seg))} pasadas de n con solo 10 "
  "cubetas; con k tan pequeño ambos son lineales con constantes parecidas. Los tres crecen de forma "
  "aproximadamente lineal con n. Los términos dominantes (ai, education, research, learning, aied, "
  "review, assessment) describen bien el dominio del corpus: revisiones de literatura sobre IA en "
  "educación y su impacto en la evaluación.")

# ----------------------------------------------------------------- 8
doc.add_page_break()
h("8. Requerimiento 4: despliegue, pruebas y uso de la aplicación", 1)
p("**Ejecución local.** Requiere Python 3.10 o superior:")
codigo("""python -m venv .venv
.venv\\Scripts\\activate            (Windows)   |   source .venv/bin/activate   (Linux/Mac)
pip install -r requirements.txt
streamlit run app.py               # abre http://localhost:8501""")
p("**Despliegue en la nube (Streamlit Community Cloud).** 1) Subir la carpeta del proyecto a un "
  "repositorio de GitHub (incluye data/corpus.json y data/embeddings/, por lo que no se necesita "
  "descargar modelos en el servidor). 2) En share.streamlit.io elegir 'New app', el repositorio, la "
  "rama y el archivo app.py. 3) La plataforma instala requirements.txt y publica la aplicación en "
  "una URL pública. También se incluye un Dockerfile para desplegar en cualquier servicio que "
  "ejecute contenedores (Render, Railway, Azure, etc.).")
p("**Regenerar los datos y este documento.**")
codigo("""python scripts/construir_corpus.py        # PDF -> data/corpus.json
python scripts/construir_embeddings.py    # descarga GloVe/FastText (una vez) -> data/embeddings/
python scripts/generar_documento.py       # -> docs/Documento_Tecnico.docx, figuras y CSV""")
p("**Pruebas automáticas** (python -m pytest): casos clásicos con resultado conocido "
  "(kitten/sitting = 3, GATTACA/GCATGCU = 0, π('ababaca')), comparación de KMP, Boyer-Moore (con y "
  "sin sufijo bueno) y Rabin-Karp contra fuerza bruta en 2 000 textos aleatorios, verificación del "
  "IDF contra scikit-learn y del clustering y la correlación cofenética contra SciPy para los "
  "cuatro criterios, y verificación de que el corpus tiene los 20 artículos completos.")
p("**Secciones de la aplicación.** Corpus (tabla de los 20 artículos con título, autores y "
  "abstract); Req. 1 (selección dinámica de 2 o más artículos, matriz de similitud por algoritmo, "
  "gráfica comparativa y paso a paso del par); Req. 2 (elección de representación y criterios, "
  "dendrogramas, métricas y grupos); Req. 3 (búsqueda en los 20 abstracts con contexto resaltado, "
  "trazas de los tres algoritmos con sus tablas, colisiones de Rabin-Karp y benchmark).")

# ----------------------------------------------------------------- 8
h("9. Declaración del uso de inteligencia artificial generativa", 1)
p("En cumplimiento del enunciado, se declara el uso de herramientas de IA generativa como apoyo "
  "al desarrollo del proyecto:")
tabla(["Aspecto", "Declaración"], [
    ["Herramienta", "Claude (Anthropic), asistente de IA generativa, usado mediante Claude Code."],
    ["Uso", "Apoyo en la escritura del código Python (extractor de PDF, implementación de los "
            "algoritmos de los requerimientos 1 a 3, aplicación Streamlit, pruebas) y en la redacción "
            "y maquetación de este documento técnico. Los algoritmos de ordenamiento del Seguimiento 1 "
            "provienen del trabajo entregado en ese seguimiento (cuyo informe incluye su propio anexo "
            "de prompts)."],
    ["Lo que no reemplaza", "El diseño algorítmico y el análisis formal deben ser comprendidos, "
                            "revisados y sustentados por el estudiante. Cada algoritmo fue verificado "
                            "con pruebas automáticas contra casos conocidos, fuerza bruta y bibliotecas "
                            "de referencia; los resultados numéricos del documento provienen de "
                            "ejecutar el código, no de la herramienta de IA."],
    ["Modelos de IA dentro de la solución", "GloVe y FastText (embeddings preentrenados, Req. 1 y "
                                            "como representación alternativa en el Req. 2). No se "
                                            "usan APIs externas en tiempo de ejecución."],
    ["Responsabilidad", "El estudiante revisó el código, ejecutó la aplicación y las pruebas, y es "
                        "responsable del contenido entregado. [Completar con los aspectos que "
                        "indique el documento del docente sobre uso de IA.]"],
], tam=8.5, anchos=[4, 12.5])

# ----------------------------------------------------------------- 9
h("10. Referencias", 1)
for ref in [
    "Bojanowski, P., Grave, E., Joulin, A., & Mikolov, T. (2017). Enriching word vectors with subword "
    "information. Transactions of the ACL, 5, 135-146.",
    "Boyer, R. S., & Moore, J. S. (1977). A fast string searching algorithm. Communications of the "
    "ACM, 20(10), 762-772.",
    "Cardona Torres, S. A. Material del curso Análisis de Algoritmos (fundamentos, complejidad "
    "computacional, algoritmos recursivos, ordenamiento y búsqueda, programación dinámica, "
    "estructuras de datos). Universidad del Quindío.",
    "Cole, R. (1994). Tight bounds on the complexity of the Boyer-Moore string matching algorithm. "
    "SIAM Journal on Computing, 23(5), 1075-1091.",
    "Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2022). Introduction to Algorithms "
    "(4th ed.). MIT Press.",
    "Harman, D. (1991). How effective is suffixing? Journal of the American Society for Information "
    "Science, 42(1), 7-15.",
    "Jaccard, P. (1912). The distribution of the flora in the alpine zone. New Phytologist, 11(2), 37-50.",
    "Karp, R. M., & Rabin, M. O. (1987). Efficient randomized pattern-matching algorithms. IBM "
    "Journal of Research and Development, 31(2), 249-260.",
    "Knuth, D. E., Morris, J. H., & Pratt, V. R. (1977). Fast pattern matching in strings. SIAM "
    "Journal on Computing, 6(2), 323-350.",
    "Lance, G. N., & Williams, W. T. (1967). A general theory of classificatory sorting strategies: "
    "1. Hierarchical systems. The Computer Journal, 9(4), 373-380.",
    "Levenshtein, V. I. (1966). Binary codes capable of correcting deletions, insertions and "
    "reversals. Soviet Physics Doklady, 10(8), 707-710.",
    "Manning, C. D., Raghavan, P., & Schütze, H. (2008). Introduction to Information Retrieval. "
    "Cambridge University Press.",
    "Mikolov, T., Grave, E., Bojanowski, P., Puhrsch, C., & Joulin, A. (2018). Advances in "
    "pre-training distributed word representations. LREC 2018.",
    "Needleman, S. B., & Wunsch, C. D. (1970). A general method applicable to the search for "
    "similarities in the amino acid sequence of two proteins. Journal of Molecular Biology, 48(3), 443-453.",
    "Pennington, J., Socher, R., & Manning, C. D. (2014). GloVe: Global vectors for word "
    "representation. EMNLP 2014, 1532-1543.",
    "Rousseeuw, P. J. (1987). Silhouettes: a graphical aid to the interpretation and validation of "
    "cluster analysis. Journal of Computational and Applied Mathematics, 20, 53-65.",
    "Salton, G., & Buckley, C. (1988). Term-weighting approaches in automatic text retrieval. "
    "Information Processing & Management, 24(5), 513-523.",
    "Sokal, R. R., & Rohlf, F. J. (1962). The comparison of dendrograms by objective methods. "
    "Taxon, 11(2), 33-40.",
]:
    par = doc.add_paragraph(ref)
    par.paragraph_format.left_indent = Cm(0.8)
    par.paragraph_format.first_line_indent = Cm(-0.8)
    par.runs[0].font.size = Pt(9.5)

destino = DOCS / "Documento_Tecnico.docx"
doc.save(destino)
print(f"Documento guardado en {destino}")
