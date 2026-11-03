"""
Crea una COPIA del documento técnico con un anexo de guía de estudio:
qué se hizo en cada parte del proyecto, cómo funciona y por qué se tomó cada
decisión, más preguntas probables de sustentación con su respuesta.

    python scripts/generar_guia.py

Entrada:  docs/Documento_Tecnico.docx           (no se modifica)
Salida:   docs/Documento_Tecnico_con_Guia.docx
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from docx import Document  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt  # noqa: E402

from src.clustering.pipeline import ejecutar  # noqa: E402
from src.corpus import articulo_por_id  # noqa: E402
from src.ordenamiento import no_comparativos as ordenamiento  # noqa: E402
from src.similitud.comparador import ALGORITMOS, similitud_par  # noqa: E402

ORIGEN = RAIZ / "docs" / "Documento_Tecnico.docx"
DESTINO = RAIZ / "docs" / "Documento_Tecnico_con_Guia.docx"

shutil.copyfile(ORIGEN, DESTINO)
doc = Document(DESTINO)


def h(t, n=1):
    doc.add_heading(t, level=n)


def p(t, cursiva=False):
    par = doc.add_paragraph()
    partes = t.split("**")
    for i, x in enumerate(partes):
        if x:
            r = par.add_run(x)
            r.bold = i % 2 == 1
            r.italic = cursiva
    return par


def v(t):
    par = doc.add_paragraph(style="List Bullet")
    partes = t.split("**")
    for i, x in enumerate(partes):
        if x:
            par.add_run(x).bold = i % 2 == 1


def pregunta(q, a):
    par = doc.add_paragraph()
    r = par.add_run("P: " + q)
    r.bold = True
    par2 = doc.add_paragraph()
    par2.paragraph_format.left_indent = Cm(0.6)
    partes = ("R: " + a).split("**")
    for i, x in enumerate(partes):
        if x:
            par2.add_run(x).bold = i % 2 == 1


def codigo(t):
    par = doc.add_paragraph()
    par.paragraph_format.left_indent = Cm(0.5)
    lineas = t.split("\n")
    r = par.add_run(lineas[0])
    for l in lineas[1:]:
        r.add_break()
        r.add_text(l)
    r.font.name = "Consolas"
    r.font.size = Pt(8.5)
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:fill"), "F3F4F6")
    par._p.get_or_add_pPr().append(sh)


# Números reales para citar en la guía
A, B = articulo_por_id(11)["abstract"], articulo_por_id(16)["abstract"]
sim = {k: similitud_par(k, A, B)["similitud"] for k in ALGORITMOS}
clu = {c: ejecutar(c, "tfidf") for c in ("single", "complete", "average")}
pares = ordenamiento.frecuencias_corpus()

doc.add_page_break()
t = doc.add_heading("Anexo A. Guía de estudio y sustentación", 0)
t.alignment = WD_ALIGN_PARAGRAPH.LEFT
p("Este anexo explica, parte por parte, qué hace el proyecto, cómo funciona por dentro y por qué "
  "se tomó cada decisión. Está pensado para estudiar antes de la sustentación: cada sección "
  "termina con preguntas que el docente podría hacer y una respuesta corta. Las referencias a "
  "archivos indican dónde está el código de cada parte (por ejemplo src/busqueda/kmp.py).",
  cursiva=True)

# ------------------------------------------------------------------ A.1
h("A.1 Visión general: qué pide el enunciado y cómo se respondió", 1)
p("El enunciado pide procesar los abstracts de 20 artículos con cuatro requerimientos. La tabla "
  "resume la respuesta del proyecto:")
for x in [
    "**Req. 1, similitud textual:** 4 algoritmos clásicos (Levenshtein, Needleman-Wunsch, coseno "
    "TF-IDF, Jaccard) y 2 de IA (embeddings GloVe y FastText). La app permite elegir 2 o más "
    "artículos y calcula una matriz de similitud por algoritmo.",
    "**Req. 2, clustering jerárquico:** Single, Complete y Average linkage escritos desde cero, "
    "dendrograma propio y dos métricas internas (correlación cofenética y silueta).",
    "**Req. 3, búsqueda de patrones:** KMP, Boyer-Moore y Rabin-Karp sin usar find(), index() ni "
    "expresiones regulares, con trazas de sus tablas y un benchmark.",
    "**Req. 4, despliegue y documentación:** aplicación Streamlit, pruebas automáticas, README, "
    "Dockerfile y el documento técnico.",
    "**Seguimiento 1:** Counting, Radix y Bucket Sort (tu código del seguimiento) para el ranking "
    "de términos, integrado como sección de la app y capítulo 7 del documento.",
]:
    v(x)
p("**Regla transversal del enunciado:** no se permiten funciones de alto nivel que implementen "
  "directamente los algoritmos. Por eso todos se escribieron con listas, diccionarios, conjuntos y "
  "ciclos. SciPy y scikit-learn solo aparecen en tests/, como 'oráculo' para comprobar que los "
  "resultados propios son correctos. Esta distinción es importante defenderla: usar una librería "
  "para VERIFICAR no es lo mismo que usarla para RESOLVER.")
p("**Por qué Python + Streamlit:** el enunciado fija Python. Streamlit permite construir la "
  "interfaz web con el mismo lenguaje, sin HTML ni JavaScript, y se despliega gratis en Streamlit "
  "Community Cloud. Así el esfuerzo se concentra en los algoritmos, que es lo que se evalúa.")

h("A.1.1 Recorrido por las carpetas", 2)
codigo("""app.py                     -> interfaz (una función por sección)
src/extraccion/            -> leer PDF y sacar título, autores, abstract
src/preprocesamiento/      -> limpiar texto (minúsculas, tokens, stopwords, stemming)
src/similitud/             -> Req. 1 (un archivo por algoritmo + comparador.py)
src/clustering/            -> Req. 2 (jerarquico.py, metricas.py, dendrograma.py, pipeline.py)
src/busqueda/              -> Req. 3 (kmp.py, boyer_moore.py, rabin_karp.py, benchmark.py)
src/ordenamiento/          -> Seguimiento 1 (no_comparativos.py)
scripts/                   -> construir_corpus, construir_embeddings, generar_documento
tests/test_algoritmos.py   -> 20 pruebas
data/corpus.json           -> los 20 artículos ya extraídos""")
p("**Por qué esta organización:** cada requerimiento es un paquete independiente que solo depende "
  "de los datos y del preprocesamiento. Esto permite probar cada algoritmo por separado y explicar "
  "uno sin tener que explicar los demás. La app solo 'orquesta': llama a las funciones y muestra "
  "resultados; no contiene lógica algorítmica.")

# ------------------------------------------------------------------ A.2
h("A.2 Extracción de los PDF (src/extraccion/extractor_pdf.py)", 1)
p("**Qué hace:** abre la primera página de cada PDF con pdfplumber, que entrega cada palabra con "
  "su posición (x, y) y su tamaño de letra. Con eso aplica tres heurísticas:")
v("**Título:** el bloque de palabras con la letra más grande, descartando la cabecera con el "
  "nombre de la revista (que en Elsevier es aún más grande que el título).")
v("**Autores:** las líneas justo debajo del título. Se quitan los superíndices de afiliación "
  "(a, b, 1, 2, *) porque tienen letra más pequeña, y se separa por comas, 'and', '|' o '·'.")
v("**Abstract:** se busca el encabezado ('Abstract', 'A B S T R A C T') y se toman las palabras "
  "que están debajo y alineadas con su columna, con el tamaño de letra del cuerpo del abstract, "
  "hasta un terminador ('Keywords', '1. Introduction', 'Citation:'...).")
p("**Por qué por posición y no por texto plano:** los 20 artículos vienen de 6 editoriales "
  "(Elsevier, BMC, Springer, Emerald, Wiley, MDPI) con maquetaciones distintas. En Elsevier las "
  "palabras clave están en una columna a la izquierda del abstract; en BMC y Wiley hay una columna "
  "lateral con afiliaciones; en Emerald hay notas al margen con fechas. Si se lee el texto plano "
  "(como hacía el seguimiento con pypdf), esas columnas se mezclan con el abstract. Usar la "
  "coordenada x permite quedarse solo con la columna correcta.")
p("**Detalles resueltos (buenos para mencionar):**")
v("**Ligaduras:** en algunos PDF 'fi' es un solo glifo dibujado aparte ('Arti ﬁ cial'); se "
  "vuelven a unir cuando los tres trozos están pegados en x.")
v("**Cortes con guion al final de línea:** 'practi-' + 'tioners' debe quedar 'practitioners', "
  "pero 'AI-' + 'driven' debe quedar 'AI-driven'. Se decide mirando si la palabra unida aparece "
  "en el resto del documento (vocabulario del propio PDF).")
v("**Acentos sueltos:** 'Gaševic ́' se recompone como 'Gašević' (normalización Unicode NFC).")
p("**Resultado:** los 20 artículos se extraen automáticamente y bien. data/correcciones.json "
  "existe para corregir a mano un campo si alguna vez falla, y queda registrado en el corpus, pero "
  "no hizo falta usarlo. El script scripts/construir_corpus.py corre la extracción y guarda "
  "data/corpus.json; la app usa ese JSON para no releer los PDF cada vez.")
pregunta("¿Por qué no usar simplemente una expresión regular entre 'Abstract' y 'Keywords'?",
         "Porque el texto plano mezcla columnas. En el seguimiento eso produjo un abstract de 12 "
         "palabras (artículo de Human-centred learning analytics) y otro de 1 197 palabras "
         "(AI technologies for education, que no tiene encabezado 'Introduction'). Con la "
         "posición de cada palabra se separan las columnas.")
pregunta("¿Cómo sabes que la extracción es correcta?",
         "Revisé los 20 abstracts contra los PDF, la app los muestra completos en la sección "
         "Corpus, y una prueba automática verifica que los 20 tengan título, autores y un "
         "abstract de más de 500 caracteres.")

# ------------------------------------------------------------------ A.3
h("A.3 Preprocesamiento (src/preprocesamiento/texto.py)", 1)
p("Pasos, en orden: (1) minúsculas y reemplazo por espacio de todo lo que no sea letra o dígito; "
  "(2) tokenización recorriendo el texto carácter a carácter; (3) quitar números y stopwords "
  "(lista basada en la de NLTK, escrita dentro del archivo); (4) S-stemmer de Harman, que solo "
  "quita plurales regulares: studies→study, assessments→assessment, analysis se queda igual.")
p("**Por qué cada paso:**")
v("Minúsculas: 'Learning' y 'learning' deben contar como el mismo término.")
v("Stopwords: 'the', 'of', 'and' aparecen en todos los textos; si no se quitan, todos los "
  "abstracts se parecen entre sí y la similitud pierde sentido.")
v("Stemming ligero y no Porter: Porter recorta mucho ('education'→'educ', 'university'→'univers') "
  "y produce raíces difíciles de leer en las tablas del documento. El S-stemmer solo une singular "
  "y plural, que es el caso más frecuente, y deja términos legibles.")
v("La lista de stopwords está escrita en el código para no depender de descargar NLTK al "
  "instalar (el seguimiento sí la descargaba).")
p("**Qué representación usa cada algoritmo, y por qué:**")
v("**Levenshtein:** texto normalizado completo, a nivel de carácter, porque así se define la "
  "distancia de edición clásica.")
v("**Needleman-Wunsch, TF-IDF, Jaccard, clustering:** tokens sin stopwords y con stemming, "
  "porque comparan palabras con contenido.")
v("**GloVe y FastText:** tokens sin stemming, porque el vocabulario de esos modelos tiene las "
  "palabras completas ('assessments' existe, 'assessm' no).")
v("**Seguimiento 1:** las mismas reglas de tu seguimiento: sin stemming, palabras de 3 o más "
  "letras y se conserva 'ai'.")

# ------------------------------------------------------------------ A.4
h("A.4 Requerimiento 1: similitud textual", 1)
p("**Caso de estudio elegido:** artículos 11 (Xia et al., IA generativa y evaluación en educación "
  "superior) y 16 (Lye y Lim, IA generativa y rediseño de la evaluación en educación terciaria). "
  "**Por qué:** tratan el mismo tema con estilos distintos (uno es una revisión de alcance, el otro "
  "un ensayo conceptual). Eso hace visible la diferencia entre los algoritmos que miden la forma "
  "del texto y los que miden el contenido.")
p("Resultados del caso (sim. en [0,1]): " + "; ".join(
    f"{ALGORITMOS[k]} = {sim[k]:.4f}" for k in ALGORITMOS) + ".")

h("A.4.1 Levenshtein (src/similitud/levenshtein.py)", 2)
p("**Idea:** número mínimo de inserciones, eliminaciones y sustituciones de caracteres para "
  "convertir A en B. **Programación dinámica:** la celda D[i][j] resuelve el subproblema 'primeros "
  "i caracteres de A contra primeros j de B' a partir de tres celdas ya calculadas (arriba, "
  "izquierda, diagonal). Es tabulación bottom-up, como en las diapositivas del curso.")
p("**Similitud:** 1 − D[n][m] / máx(n, m). Se divide por la longitud mayor porque es la máxima "
  "distancia posible, así el resultado queda entre 0 y 1.")
p("**Decisión de implementación:** hay dos versiones. matriz_completa() guarda toda la tabla para "
  "mostrarla paso a paso; distancia() solo guarda dos filas (O(mín(n,m)) de memoria), porque para "
  "dos abstracts completos la tabla tiene ~1,4 millones de celdas y no hace falta guardarla para "
  "obtener el número final. operaciones() reconstruye el camino (=, S, E, I) recorriendo la tabla "
  "desde la esquina.")
p("**Complejidad:** O(n·m) siempre (la tabla se llena completa en mejor y peor caso).")
pregunta("¿Por qué Levenshtein da ~0,30 incluso entre abstracts que no tienen nada que ver?",
         "Porque compara letras: en inglés las letras frecuentes (e, a, t, espacio) coinciden por "
         "azar. En el corpus todos los pares están entre ~0,23 y ~0,32. Sirve para detectar "
         "copia o variantes de una misma frase, no para similitud temática.")
pregunta("¿Qué tiene de programación dinámica?",
         "Subestructura óptima (la mejor edición de prefijos largos se arma con la de prefijos "
         "más cortos) y subproblemas superpuestos (la misma celda la usan tres celdas vecinas). "
         "Se guarda cada resultado en la tabla para no recalcularlo; la versión recursiva sin "
         "tabla sería exponencial.")

h("A.4.2 Needleman-Wunsch (src/similitud/needleman_wunsch.py)", 2)
p("**Idea:** alineamiento global de dos secuencias, de biología computacional. Puntajes: "
  "coincidencia +1, diferencia −1, hueco −1. F[i][j] es el mejor puntaje de alinear los prefijos.")
p("**Diferencia con Levenshtein:** Levenshtein minimiza un costo; NW maximiza un puntaje y además "
  "devuelve el alineamiento (qué palabra queda frente a cuál). Para eso se guarda una matriz de "
  "direcciones P ('D' diagonal, 'U' arriba, 'L' izquierda) y se recorre desde F[n][m] (traceback).")
p("**Por qué a nivel de palabras:** a nivel de carácter sería casi igual que Levenshtein. A nivel "
  "de palabras muestra otra cosa: si los dos textos presentan los conceptos en el mismo orden. "
  "Además reduce la tabla de ~10⁶ a ~10⁴ celdas.")
p("**Similitud reportada:** identidad = coincidencias / longitud del alineamiento. También se "
  "calcula el puntaje normalizado entre el peor y el mejor puntaje posibles.")

h("A.4.3 Coseno con TF-IDF (src/similitud/tfidf_coseno.py)", 2)
p("**Idea:** cada abstract es un vector con un peso por término. tf = frecuencia del término / "
  "tokens del documento. idf = ln((1+N)/(1+df)) + 1, donde df es en cuántos abstracts aparece. "
  "La similitud es el coseno del ángulo entre los vectores.")
p("**Por qué IDF:** 'artificial' e 'intelligence' están en los 20 abstracts (idf = 1, el mínimo); "
  "'integrity' solo en 2 (idf ≈ 2,95). Sin IDF, las palabras comunes del dominio dominarían y "
  "todos los abstracts se parecerían. **Por qué el IDF suavizado** (+1 arriba y abajo, +1 al "
  "final): evita dividir por cero y que un término presente en todos los documentos pese 0; es la "
  "misma fórmula de scikit-learn, y una prueba lo verifica contra sklearn.")
p("**Por qué el coseno y no la distancia euclidiana:** el coseno mide la dirección, no la "
  "longitud: un abstract largo y uno corto sobre lo mismo dan un ángulo pequeño.")
p("**Decisión de implementación:** vectores como diccionarios {término: peso}. Un abstract tiene "
  "~90 términos de ~1 000 del vocabulario; el producto punto solo recorre el diccionario más "
  "pequeño y consulta el otro en O(1). Por eso cuesta O(mín(|A|,|B|)) y no O(V).")
p(f"**Lectura del caso:** cos = {sim['tfidf_coseno']:.4f} (ángulo ≈ 76°). Es de los valores más "
  "altos del corpus: el par queda 9.º de 190. La palabra 'assessment' (8 veces en A, 6 en B) "
  "aporta casi la mitad del producto punto.")

h("A.4.4 Jaccard (src/similitud/jaccard.py)", 2)
p("**Idea:** |A ∩ B| / |A ∪ B| sobre los conjuntos de términos distintos. Ignora cuántas veces "
  "aparece cada término y no tiene pesos.")
p("**Para qué se incluye:** es el modelo de conjuntos más simple y sirve de contraste con TF-IDF. "
  f"En el caso da {sim['jaccard']:.4f} (14 términos comunes de 130) y deja el par en la posición "
  "78 de 190, porque coincidir en 'assessment' vale lo mismo que coincidir en 'provide'.")

h("A.4.5 Modelos de IA: GloVe y FastText (src/similitud/embeddings.py)", 2)
p("**Qué es un embedding:** un vector denso (100 o 300 números) aprendido de miles de millones de "
  "palabras, donde palabras usadas en contextos parecidos quedan cerca ('cheating' cerca de "
  "'plagiarism'). **GloVe** se entrena factorizando la matriz de co-ocurrencias; **FastText** "
  "(evolución de Word2Vec) representa cada palabra con n-gramas de caracteres, por lo que maneja "
  "mejor variantes morfológicas.")
p("**Cómo se usa:** el vector del abstract es el promedio de los vectores de sus palabras (mean "
  "pooling) y se compara con el coseno. También se reporta la distancia euclidiana.")
p("**Por qué estos dos modelos:** el enunciado los sugiere (Word2Vec/FastText), son preentrenados "
  "(no hay que entrenar nada), funcionan sin GPU y sin claves de API, y dan dos enfoques distintos "
  "(co-ocurrencia global vs. subpalabras).")
p("**Decisión de diseño importante:** los modelos completos pesan ~1,2 GB. "
  "scripts/construir_embeddings.py los descarga una vez y guarda solo los vectores de las ~1 100 "
  "palabras del corpus en data/embeddings/ (~1,6 MB). Los vectores son exactamente los del modelo "
  "original; así la app arranca en segundos y funciona sin internet.")
p(f"**Lectura del caso:** GloVe {sim['glove']:.4f} y FastText {sim['fasttext']:.4f}. Parecen muy "
  "altos, pero todos los pares del corpus dan entre ~0,91 y ~0,98: al promediar palabras de un "
  "mismo dominio, todos los vectores apuntan a una zona parecida (anisotropía). Lo informativo es "
  "el ranking, no el valor. Y en el ranking estos modelos ponen el par 11-16 abajo (178 y 150 de "
  "190) porque el promedio queda dominado por el estilo del texto (revisión sistemática vs. "
  "ensayo) más que por el tema.")
pregunta("Entonces, ¿la IA es peor que TF-IDF?",
         "Para este caso concreto, TF-IDF ordena mejor. Pero los embeddings capturan algo que los "
         "clásicos no: sinónimos ('higher' vs 'tertiary', 'cheating' vs 'integrity'). La "
         "limitación está en el mean pooling, que ignora orden y énfasis. Un modelo contextual "
         "tipo Sentence-BERT mejoraría, a cambio de una red neuronal de cientos de MB.")
pregunta("¿Por qué los valores de los clásicos y de la IA están en escalas tan distintas?",
         "Porque miden cosas distintas: los clásicos cuentan coincidencias exactas (casi siempre "
         "pocas), los embeddings comparan direcciones en un espacio donde todo el dominio está "
         "junto. Por eso el documento compara posiciones en el ranking de los 190 pares y la "
         "correlación de Spearman entre algoritmos, no los valores absolutos.")

# ------------------------------------------------------------------ A.5
h("A.5 Requerimiento 2: clustering jerárquico", 1)
p("**Pipeline:** abstract → tokens → vector TF-IDF → matriz de distancias 20×20 con "
  "d = 1 − coseno → algoritmo aglomerativo → dendrograma → métricas. **Por qué 1 − coseno:** "
  "convierte la similitud (1 = idéntico) en distancia (0 = idéntico), que es lo que necesita el "
  "clustering. La app también deja usar GloVe o FastText como representación.")
p("**Algoritmo (src/clustering/jerarquico.py):** cada abstract empieza solo; en cada paso se busca "
  "el par de grupos más cercano, se fusionan y se recalcula la distancia del grupo nuevo a los "
  "demás. Tras 19 fusiones queda un único grupo; el registro de fusiones es el árbol.")
p("**La fórmula de Lance-Williams** permite escribir los tres criterios con una sola función:")
v("**Single:** distancia = la MÍNIMA entre miembros. Une por el vecino más cercano; tiende a "
  "encadenar (los abstracts se van pegando de a uno a un grupo grande).")
v("**Complete:** distancia = la MÁXIMA entre miembros. Grupos compactos, pero exagera distancias.")
v("**Average (UPGMA):** PROMEDIO de todas las distancias entre miembros, ponderado por tamaño. "
  "Punto medio entre los dos anteriores.")
v("**Ward** se incluye como referencia extra (minimiza el aumento de varianza).")
p("**Por qué Lance-Williams y no recalcular desde los puntos:** permite actualizar la distancia "
  "del grupo nuevo en O(1) a partir de las distancias que ya se tienen, sin volver a recorrer los "
  "miembros. **Complejidad:** buscar el mínimo cuesta O(k²) con k grupos activos y se hace n−1 "
  "veces: O(n³). Con n = 20 son 1 330 comparaciones, nada para un computador.")
p("**Dendrograma (src/clustering/dendrograma.py):** se dibuja con matplotlib a partir de las "
  "fusiones propias (no se usa scipy.dendrogram). El orden de las hojas sale de un recorrido en "
  "profundidad del árbol y cada fusión es una 'U' a la altura de su distancia.")
p("**Evaluación:**")
v("**Correlación cofenética (CCC):** compara la distancia original entre cada par con la altura "
  "donde el árbol los une. Si el árbol respeta las distancias, la correlación es alta. Evalúa el "
  "árbol completo, por eso es la métrica principal para comparar criterios.")
v("**Silueta:** evalúa un corte del árbol en k grupos: qué tan cerca está cada abstract de su "
  "grupo frente al grupo vecino. Se prueba k = 2…8 y se elige el mejor k ≥ 3, porque con k = 2 "
  "el corte suele dejar un solo abstract atípico aparte, algo poco informativo.")
p(f"**Resultado:** CCC Single = {clu['single']['ccc']:.4f}, Complete = "
  f"{clu['complete']['ccc']:.4f}, Average = {clu['average']['ccc']:.4f}. **Average es el más "
  "coherente**, también con GloVe y FastText. Razón: la altura de cada fusión es un promedio de "
  "distancias reales, no un extremo, y por eso el árbol las reproduce mejor. Se forman grupos con "
  "sentido: evaluación con IA generativa (11, 16, 17) y revisiones bibliométricas generales de "
  "AIEd (2, 5, 6, 9, 12, 20).")
pregunta("La silueta con TF-IDF es muy baja (< 0,1). ¿Está mal el clustering?",
         "No. Los 20 abstracts son del mismo dominio y comparten mucho vocabulario, así que no hay "
         "grupos muy separados. La silueta mide separación de la partición; la CCC mide fidelidad "
         "del árbol. Con embeddings la silueta sube (~0,3) porque las distancias se reparten de "
         "otra forma.")
pregunta("¿Cómo sabes que tu clustering está bien implementado?",
         "Las pruebas comparan las alturas de fusión y la CCC con scipy.cluster.hierarchy para "
         "los cuatro criterios, y coinciden exactamente. SciPy solo se usa en las pruebas.")

# ------------------------------------------------------------------ A.6
h("A.6 Requerimiento 3: búsqueda de patrones", 1)
p("Caso del documento: patrón 'assessment' (m = 10) en un párrafo de 264 caracteres del "
  "abstract 11, que lo contiene 2 veces (posiciones 83 y 233). En la app se busca en los 20 "
  "abstracts y se muestran las ocurrencias resaltadas.")
p("**Fuerza bruta, para comparar:** probar cada posición y comparar hasta m caracteres: O(n·m). "
  "Los tres algoritmos mejoran esto con un preprocesamiento del patrón.")
h("A.6.1 KMP (src/busqueda/kmp.py)", 2)
p("**Idea clave:** nunca retroceder en el texto. La tabla π (función de fallo) dice, para cada "
  "prefijo del patrón, cuál es su borde más largo (prefijo que también es sufijo). Si se casaron q "
  "caracteres y falla el siguiente, el patrón salta a π[q−1] sin volver a leer el texto.")
p("**En el caso:** π de 'assessment' es toda ceros, porque la 'a' solo está al inicio: ningún "
  "prefijo es también sufijo. Si te preguntan un ejemplo con bordes: 'ababaca' → π = "
  "[0,0,1,2,3,0,1].")
p("**Complejidad:** O(m) para π y O(n) para buscar (como mucho 2n comparaciones). Total Θ(n+m) "
  "garantizado, sin importar el alfabeto ni el texto.")
h("A.6.2 Boyer-Moore (src/busqueda/boyer_moore.py)", 2)
p("**Idea clave:** comparar el patrón de DERECHA a IZQUIERDA y saltar lo más posible. Dos reglas; "
  "se aplica el mayor salto:")
v("**Carácter malo:** si el carácter del texto que falló no está en el patrón, se salta el patrón "
  "completo. Tabla: última posición de cada letra en el patrón (en 'assessment': s→5, e→7, t→9).")
v("**Sufijo bueno:** si ya casó un sufijo del patrón, se desplaza hasta la próxima aparición de "
  "ese sufijo (o del prefijo más largo que coincida con él).")
p("**En el caso:** 30 alineaciones de 255 posibles y 50 comparaciones (KMP hizo 279), porque casi "
  "siempre la letra del texto no está en 'assessment' y salta 10.")
p("**Por qué implementar las dos reglas:** solo con carácter malo, el peor caso es O(n·m). El "
  "benchmark lo demuestra: con texto 'aaaa…' y patrón 'baaa…a', BM sin sufijo bueno hace 399 620 "
  "comparaciones y con sufijo bueno 20 000.")
h("A.6.3 Rabin-Karp (src/busqueda/rabin_karp.py)", 2)
p("**Idea clave:** convertir cada ventana de m caracteres en un número (hash) en base 256 módulo "
  "un primo q, y comparar números en lugar de cadenas. El hash de la ventana siguiente se calcula "
  "en O(1) quitando el carácter que sale y agregando el que entra (rolling hash). Si el hash "
  "coincide, se verifica carácter a carácter, porque dos cadenas distintas pueden tener el mismo "
  "hash (colisión).")
p("**Por qué q = 37 en el documento y 1 000 000 007 en la app:** con un primo pequeño aparecen "
  "colisiones (5 en el caso), lo que permite mostrarlas; con un primo grande casi nunca ocurren "
  "(probabilidad ≈ 1/q por ventana).")
p("**Complejidad:** O(n+m) esperado; O(n·m) en el peor caso, si muchas ventanas colisionan.")
h("A.6.4 Qué mostró el benchmark", 2)
v("El preprocesamiento de los tres es despreciable (microsegundos) frente a la búsqueda "
  "(milisegundos), porque m es mucho menor que n.")
v("Los tres crecen linealmente con n, como dice la teoría.")
v("Boyer-Moore es el más rápido y mejora cuando el patrón es más largo (saltos más grandes): "
  "comportamiento sublineal O(n/m).")
v("Rabin-Karp hace muy pocas comparaciones de caracteres, pero es el más LENTO en tiempo real: "
  "cada ventana requiere multiplicación, resta, suma y módulo. Las constantes que esconde la "
  "notación O sí importan en la práctica.")
pregunta("Si Rabin-Karp es el más lento, ¿para qué sirve?",
         "Para buscar muchos patrones a la vez (se compara un hash contra un conjunto de hashes) "
         "y para detectar plagio por huellas digitales. Para un solo patrón, Boyer-Moore gana.")
pregunta("¿Por qué no usar str.find()?",
         "Lo prohíbe el enunciado y además esconde el algoritmo. Las tres implementaciones se "
         "comprobaron contra una búsqueda por fuerza bruta en 2 000 textos aleatorios.")

# ------------------------------------------------------------------ A.7
h("A.7 Seguimiento 1: ordenamiento no comparativo", 1)
p("**Qué se conservó:** tus funciones counting_sort, radix_sort y bucket_sort quedaron igual en "
  "src/ordenamiento/no_comparativos.py, y también la metodología de medición (1 000 repeticiones, "
  "copia nueva de la lista en cada una, una ejecución de calentamiento, 5/10/15/20 documentos).")
p("**Qué cambió y por qué:** la entrada. El seguimiento extraía el abstract con expresiones "
  "regulares sobre el texto de pypdf, y eso falló en dos artículos (12 y 1 197 palabras). Ahora "
  "se usa el corpus validado y las mismas reglas de limpieza. Por eso n bajó de 1 180 a "
  f"{len(pares)} términos distintos y k de 98 a {max(f for _, f in pares)}. La lista de stopwords "
  "es la del preprocesamiento del proyecto, para no depender de descargar NLTK.")
p("**Por qué estos algoritmos pueden bajar de n log n:** no comparan elementos entre sí, usan el "
  "valor de la frecuencia como posición. Counting es O(n+k), Radix O(d·(n+10)) con d = 2 dígitos, "
  "Bucket O(n) promedio. Bucket es el más lento porque las frecuencias siguen la ley de Zipf: "
  "la mayoría de términos aparece una vez y cae en la primera cubeta, mientras se crean cientos de "
  "cubetas casi vacías.")
pregunta("¿Por qué ahora Radix a veces sale más rápido que Counting, al revés que en el informe?",
         "Porque la diferencia es muy pequeña (decenas de microsegundos) y está dentro de la "
         "variación entre ejecuciones y equipos. Con k tan pequeño ambos son lineales con "
         "constantes parecidas. Lo estable es que Bucket Sort es el más lento.")

# ------------------------------------------------------------------ A.8
h("A.8 Aplicación, pruebas y despliegue", 1)
p("**app.py:** una función por sección (pagina_inicio, pagina_similitud, pagina_clustering, "
  "pagina_busqueda, pagina_seguimiento) y un menú lateral que elige cuál ejecutar. Cada página "
  "llama a los módulos de src/ y muestra tablas, gráficas y las trazas paso a paso.")
p("**Pruebas (tests/test_algoritmos.py, 20 en total):** casos clásicos con respuesta conocida "
  "(kitten/sitting = 3; GATTACA/GCATGCU = 0), comparación contra fuerza bruta con miles de textos "
  "aleatorios para los tres algoritmos de búsqueda, comparación con SciPy (clustering) y "
  "scikit-learn (IDF), y comprobación de los ordenamientos contra sorted(). Se ejecutan con "
  "python -m pytest.")
p("**Por qué probar contra librerías si no se pueden usar:** el enunciado prohíbe usarlas para "
  "resolver, no para verificar. Si la implementación propia da lo mismo que una librería "
  "reconocida, es evidencia fuerte de que es correcta.")
p("**Documento técnico (scripts/generar_documento.py):** todos los números, tablas y figuras del "
  "documento se calculan ejecutando el código. Si cambias un algoritmo y vuelves a correr el "
  "script, el documento se actualiza solo.")
p("**Despliegue:** local con streamlit run app.py; en internet con Streamlit Community Cloud "
  "(necesita el proyecto en GitHub) o con el Dockerfile en cualquier servicio de contenedores.")

# ------------------------------------------------------------------ A.9
h("A.9 Tabla resumen de complejidades (para memorizar)", 1)
filas = [
    ("Levenshtein", "O(n·m)", "O(mín(n,m)) con 2 filas", "Programación dinámica"),
    ("Needleman-Wunsch", "O(n·m)", "O(n·m)", "Programación dinámica + traceback"),
    ("Coseno TF-IDF", "O(T) modelo; O(mín(|A|,|B|)) por par", "O(V)", "Espacio vectorial"),
    ("Jaccard", "O(|A|+|B|)", "O(|A|+|B|)", "Conjuntos / tabla hash"),
    ("Embeddings (promedio + coseno)", "O(k·dim)", "O(dim)", "Modelo preentrenado"),
    ("Clustering aglomerativo", "O(n³)", "O(n²)", "Voraz + Lance-Williams"),
    ("KMP", "Θ(m) + Θ(n)", "O(m)", "Función de fallo"),
    ("Boyer-Moore", "O(m+σ) + O(n/m)…O(n·m)", "O(m+σ)", "Heurísticas de salto"),
    ("Rabin-Karp", "Θ(m) + O(n+m) esperado, O(n·m) peor", "O(1)", "Hash rodante"),
    ("Counting Sort", "O(n+k)", "O(n+k)", "Conteo"),
    ("Radix Sort", "O(d·(n+b))", "O(n+b)", "Dígito por dígito, estable"),
    ("Bucket Sort", "O(n) promedio, O(n²) peor", "O(n+m)", "Cubetas + inserción"),
]
t = doc.add_table(rows=1, cols=4)
t.style = "Light Grid Accent 1"
for i, e in enumerate(["Algoritmo", "Tiempo", "Espacio", "Técnica"]):
    t.rows[0].cells[i].text = e
for f in filas:
    c = t.add_row().cells
    for i, x in enumerate(f):
        c[i].text = x
for fila in t.rows:
    for c in fila.cells:
        for par in c.paragraphs:
            for r in par.runs:
                r.font.size = Pt(8.5)

h("A.10 Cómo hacer una demostración en vivo", 1)
for x in [
    "Abrir la app (.venv\\Scripts\\python -m streamlit run app.py) y mostrar la sección Corpus: "
    "los 20 artículos con título, autores y abstract.",
    "Req. 1: elegir 11 y 16, mostrar la matriz de cada algoritmo y, abajo, el paso a paso "
    "(matriz de Levenshtein, tabla TF-IDF, intersección de Jaccard). Luego agregar un tercer "
    "artículo para mostrar la selección de 2 o más.",
    "Req. 2: dejar TF-IDF y los tres criterios; señalar la tabla de CCC (Average gana) y el "
    "dendrograma con sus grupos de colores.",
    "Req. 3: buscar 'assessment', abrir las ocurrencias resaltadas, mostrar la tabla π, las tablas "
    "de Boyer-Moore y las colisiones de Rabin-Karp con q = 37; ejecutar el benchmark.",
    "Seguimiento 1: mostrar el ranking idéntico en los tres algoritmos y la distribución de "
    "cubetas (ley de Zipf).",
    "Terminar con python -m pytest para mostrar las 20 pruebas en verde.",
]:
    doc.add_paragraph(x, style="List Number")

doc.save(DESTINO)
print(f"Guía guardada en {DESTINO}")
