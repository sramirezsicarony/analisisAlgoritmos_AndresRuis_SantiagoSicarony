"""
Fachada del Requerimiento 2:
abstract -> preprocesamiento -> vectores -> matriz de distancias -> clustering
-> dendrograma -> evaluación interna.
"""
from __future__ import annotations

from functools import lru_cache

from src.clustering import jerarquico, metricas
from src.corpus import cargar_corpus
from src.preprocesamiento.texto import preprocesar
from src.similitud import tfidf_coseno
from src.similitud.embeddings import cargar_modelo, coseno, euclidiana

REPRESENTACIONES = {
    "tfidf": "TF-IDF + distancia coseno (1 - cos)",
    "glove": "GloVe 100d (promedio) + distancia coseno",
    "fasttext": "FastText 300d (promedio) + distancia coseno",
}


@lru_cache(maxsize=8)
def matriz_distancias(representacion: str = "tfidf") -> tuple[tuple[float, ...], ...]:
    corpus = cargar_corpus()
    n = len(corpus)
    if representacion == "tfidf":
        docs = [preprocesar(a["abstract"]) for a in corpus]
        modelo = tfidf_coseno.ModeloTFIDF(docs)
        vectores = [modelo.vector(d) for d in docs]
        sim = tfidf_coseno.coseno
    else:
        modelo = cargar_modelo("glove100" if representacion == "glove" else "fasttext300")
        vectores = [modelo.vector_documento(preprocesar(a["abstract"], stemming=False))[0]
                    for a in corpus]
        sim = coseno
    D = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = max(0.0, 1.0 - sim(vectores[i], vectores[j]))
            D[i][j] = D[j][i] = d
    return tuple(tuple(f) for f in D)


def ejecutar(criterio: str, representacion: str = "tfidf", k_max: int = 8) -> dict:
    D = [list(f) for f in matriz_distancias(representacion)]
    n = len(D)
    fusiones = jerarquico.aglomerativo(D, criterio)
    ccc = metricas.correlacion_cofenetica(D, fusiones)
    siluetas = {}
    for k in range(2, k_max + 1):
        etiquetas = jerarquico.cortar(fusiones, n, k)
        siluetas[k] = metricas.silueta(D, etiquetas)[0]
    # k = 2 suele separar un solo abstract atípico del resto; para que el corte
    # sea informativo se elige el mejor k entre 3 y k_max
    candidatos = {k: v for k, v in siluetas.items() if k >= 3} or siluetas
    mejor_k = max(candidatos, key=candidatos.get)
    return {"criterio": criterio, "representacion": representacion, "D": D,
            "fusiones": fusiones, "ccc": ccc, "siluetas": siluetas,
            "mejor_k": mejor_k, "etiquetas": jerarquico.cortar(fusiones, n, mejor_k)}
