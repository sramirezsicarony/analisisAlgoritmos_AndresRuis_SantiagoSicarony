"""Pruebas de los algoritmos: casos conocidos, comparación contra fuerza bruta y
(si está instalada) comparación contra SciPy en el clustering."""
import random

import pytest

from src.busqueda import boyer_moore, kmp, rabin_karp
from src.clustering import jerarquico, metricas
from src.corpus import cargar_corpus
from src.preprocesamiento.texto import preprocesar, s_stemmer
from src.similitud import jaccard, levenshtein, needleman_wunsch, tfidf_coseno


# ---------------------------------------------------------------- corpus
def test_corpus_tiene_20_articulos_completos():
    corpus = cargar_corpus()
    assert len(corpus) == 20
    for a in corpus:
        assert a["titulo"] and a["autores"] and len(a["abstract"]) > 500


# ---------------------------------------------------------------- preprocesamiento
def test_stemmer():
    assert s_stemmer("studies") == "study"
    assert s_stemmer("assessments") == "assessment"
    assert s_stemmer("analysis") == "analysis"


def test_preprocesar_quita_stopwords():
    assert preprocesar("The use of AI in the classroom") == ["use", "ai", "classroom"]


# ---------------------------------------------------------------- Levenshtein / NW
@pytest.mark.parametrize("a,b,d", [("kitten", "sitting", 3), ("", "abc", 3),
                                   ("flaw", "lawn", 2), ("algoritmo", "algoritmo", 0)])
def test_levenshtein_casos_clasicos(a, b, d):
    assert levenshtein.distancia(a, b) == d
    assert levenshtein.matriz_completa(a, b)[-1][-1] == d


def test_levenshtein_operaciones_reconstruyen_distancia():
    ops = levenshtein.operaciones("kitten", "sitting")
    assert sum(1 for o in ops if o[0] != "=") == 3


def test_needleman_wunsch():
    r = needleman_wunsch.alinear(list("GATTACA"), list("GCATGCU"), guardar_matriz=True)
    assert r.puntaje == 0                      # ejemplo clásico (match 1, mismatch -1, gap -1)
    assert len(r.alineado_a) == len(r.alineado_b)
    assert needleman_wunsch.alinear(["a", "b"], ["a", "b"]).identidad == 1.0


# ---------------------------------------------------------------- TF-IDF / Jaccard
def test_coseno_y_jaccard():
    m = tfidf_coseno.ModeloTFIDF([["ai", "education"], ["ai", "health"], ["music"]])
    v = m.vector(["ai", "education"])
    assert tfidf_coseno.coseno(v, v) == pytest.approx(1.0)
    assert tfidf_coseno.coseno(v, m.vector(["music"])) == 0.0
    assert jaccard.coeficiente({"a", "b", "c"}, {"b", "c", "d"}) == pytest.approx(0.5)


def test_tfidf_igual_a_sklearn():
    sk = pytest.importorskip("sklearn.feature_extraction.text")
    docs = [preprocesar(a["abstract"]) for a in cargar_corpus()]
    m = tfidf_coseno.ModeloTFIDF(docs)
    vec = sk.TfidfVectorizer(analyzer=lambda x: x, norm=None, sublinear_tf=False)
    X = vec.fit_transform(docs)
    idf_sk = dict(zip(vec.get_feature_names_out(), vec.idf_))
    for t in list(m.idf)[:200]:
        assert m.idf[t] == pytest.approx(idf_sk[t])


# ---------------------------------------------------------------- búsqueda
def fuerza_bruta(t, p):
    return [i for i in range(len(t) - len(p) + 1) if t[i:i + len(p)] == p]


def test_busqueda_aleatoria_contra_fuerza_bruta():
    random.seed(7)
    for _ in range(2000):
        t = "".join(random.choice("abc") for _ in range(random.randint(0, 60)))
        p = "".join(random.choice("abc") for _ in range(random.randint(1, 5)))
        esperado = fuerza_bruta(t, p)
        assert kmp.buscar(t, p).posiciones == esperado
        assert boyer_moore.buscar(t, p).posiciones == esperado
        assert boyer_moore.buscar(t, p, usar_sufijo_bueno=False).posiciones == esperado
        assert rabin_karp.buscar(t, p, q=13).posiciones == esperado


def test_tablas_auxiliares():
    assert kmp.tabla_fallo("ababaca") == [0, 0, 1, 2, 3, 0, 1]
    assert boyer_moore.tabla_caracter_malo("assessment")["s"] == 5
    r = rabin_karp.buscar("abracadabra", "abra", q=101, trazar=True)
    assert r.posiciones == [0, 7]


def test_rabin_karp_detecta_colisiones_con_q_pequeno():
    texto = " ".join(a["abstract"].lower() for a in cargar_corpus())
    r = rabin_karp.buscar(texto, "learning", q=11)
    assert r.extra["colisiones"] > 0
    assert r.posiciones == fuerza_bruta(texto, "learning")


# ---------------------------------------------------------------- clustering
@pytest.mark.parametrize("criterio", ["single", "complete", "average", "ward"])
def test_clustering_igual_a_scipy(criterio):
    np = pytest.importorskip("numpy")
    hierarchy = pytest.importorskip("scipy.cluster.hierarchy")
    distance = pytest.importorskip("scipy.spatial.distance")
    random.seed(3)
    pts = [(random.random(), random.random()) for _ in range(15)]
    D = [[((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for b in pts] for a in pts]
    fus = jerarquico.aglomerativo(D, criterio)
    Z = hierarchy.linkage(distance.squareform(np.array(D), checks=False), method=criterio)
    assert sorted(f.distancia for f in fus) == pytest.approx(sorted(Z[:, 2]))
    ccc_sp = hierarchy.cophenet(Z, distance.squareform(np.array(D), checks=False))[0]
    assert metricas.correlacion_cofenetica(D, fus) == pytest.approx(ccc_sp)


def test_corte_y_silueta():
    D = [[0, 1, 9, 9], [1, 0, 9, 9], [9, 9, 0, 1], [9, 9, 1, 0]]
    fus = jerarquico.aglomerativo(D, "average")
    etiquetas = jerarquico.cortar(fus, 4, 2)
    assert etiquetas[0] == etiquetas[1] != etiquetas[2] == etiquetas[3]
    assert metricas.silueta(D, etiquetas)[0] == pytest.approx(8 / 9)


# ---------------------------------------------------------------- Seguimiento 1
def test_ordenamientos_no_comparativos():
    from src.ordenamiento import no_comparativos as o
    random.seed(5)
    pares = [(f"t{i}", random.randint(1, 120)) for i in range(500)]
    esperado = sorted(pares, key=lambda x: x[1])          # sorted es estable
    assert o.counting_sort(pares) == esperado
    assert o.radix_sort(pares) == esperado
    assert [f for _, f in o.bucket_sort(pares)] == [f for _, f in esperado]
    reales = o.frecuencias_corpus()
    assert o.ranking(o.counting_sort(reales), 1)[0][0] == "ai"
