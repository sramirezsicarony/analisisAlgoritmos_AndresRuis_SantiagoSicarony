"""
Fachada del Requerimiento 1: calcula los 6 algoritmos de similitud para dos o
más abstracts y arma la matriz de similitud por algoritmo.
"""
from __future__ import annotations

import time
from functools import lru_cache
from itertools import combinations

from src.corpus import cargar_corpus
from src.preprocesamiento.texto import normalizar, preprocesar
from src.similitud import jaccard, levenshtein, needleman_wunsch, tfidf_coseno
from src.similitud.embeddings import cargar_modelo, coseno, euclidiana

ALGORITMOS = {
    "levenshtein": "Levenshtein (caracteres)",
    "needleman_wunsch": "Needleman-Wunsch (palabras)",
    "tfidf_coseno": "Coseno TF-IDF",
    "jaccard": "Jaccard (términos)",
    "glove": "IA: GloVe 100d + coseno",
    "fasttext": "IA: FastText 300d + coseno",
}
CLASICOS = ["levenshtein", "needleman_wunsch", "tfidf_coseno", "jaccard"]
IA = ["glove", "fasttext"]


# Representaciones de cada abstract (se calculan una vez) ---------------------
def texto_normalizado(abstract: str) -> str:
    return normalizar(abstract)


def tokens_clasicos(abstract: str) -> list[str]:
    return preprocesar(abstract, quitar_stopwords=True, stemming=True)


def tokens_ia(abstract: str) -> list[str]:
    return preprocesar(abstract, quitar_stopwords=True, stemming=False)


@lru_cache(maxsize=1)
def modelo_tfidf() -> tfidf_coseno.ModeloTFIDF:
    return tfidf_coseno.ModeloTFIDF([tokens_clasicos(a["abstract"]) for a in cargar_corpus()])


def similitud_par(algoritmo: str, abs_a: str, abs_b: str) -> dict:
    """Similitud en [0,1] entre dos abstracts más información del cálculo."""
    t0 = time.perf_counter()
    info: dict = {}
    if algoritmo == "levenshtein":
        a, b = texto_normalizado(abs_a), texto_normalizado(abs_b)
        d = levenshtein.distancia(a, b)
        sim = 1 - d / max(len(a), len(b))
        info = {"distancia": d, "n": len(a), "m": len(b)}
    elif algoritmo == "needleman_wunsch":
        r = needleman_wunsch.alinear(tokens_clasicos(abs_a), tokens_clasicos(abs_b))
        sim = r.identidad
        info = {"puntaje": r.puntaje, "coincidencias": r.coincidencias,
                "sustituciones": r.sustituciones, "huecos": r.huecos,
                "puntaje_normalizado": r.puntaje_normalizado}
    elif algoritmo == "tfidf_coseno":
        m = modelo_tfidf()
        va, vb = m.vector(tokens_clasicos(abs_a)), m.vector(tokens_clasicos(abs_b))
        sim = tfidf_coseno.coseno(va, vb)
        info = {"angulo_grados": tfidf_coseno.angulo_grados(sim)}
    elif algoritmo == "jaccard":
        A, B = jaccard.conjunto(tokens_clasicos(abs_a)), jaccard.conjunto(tokens_clasicos(abs_b))
        sim = jaccard.coeficiente(A, B)
        inter = len(jaccard.interseccion(A, B))
        info = {"interseccion": inter, "union": len(A) + len(B) - inter}
    elif algoritmo in ("glove", "fasttext"):
        modelo = cargar_modelo("glove100" if algoritmo == "glove" else "fasttext300")
        u, _, oov_a = modelo.vector_documento(tokens_ia(abs_a))
        v, _, oov_b = modelo.vector_documento(tokens_ia(abs_b))
        sim = coseno(u, v)
        info = {"euclidiana": euclidiana(u, v), "fuera_vocabulario": len(oov_a) + len(oov_b)}
    else:
        raise ValueError(algoritmo)
    info["tiempo_ms"] = (time.perf_counter() - t0) * 1000
    return {"similitud": sim, **info}


def matriz_similitud(ids: list[int], algoritmo: str) -> tuple[list[list[float]], list[dict]]:
    """Matriz simétrica de similitud entre los artículos indicados."""
    corpus = {a["id"]: a for a in cargar_corpus()}
    n = len(ids)
    M = [[1.0] * n for _ in range(n)]
    detalles = []
    for i, j in combinations(range(n), 2):
        r = similitud_par(algoritmo, corpus[ids[i]]["abstract"], corpus[ids[j]]["abstract"])
        M[i][j] = M[j][i] = r["similitud"]
        detalles.append({"a": ids[i], "b": ids[j], **r})
    return M, detalles
