"""
Ranking de términos con algoritmos de ordenamiento NO basados en comparaciones
(Seguimiento 1 del proyecto).

Las implementaciones de Counting Sort, Radix Sort y Bucket Sort provienen del
Seguimiento 1 (seguimiento.py) y se integran aquí sin cambios en su lógica.
Ordenan pares (término, frecuencia) por frecuencia, de forma ascendente; el
ranking se obtiene recorriendo el resultado de atrás hacia adelante.

Diferencias respecto al Seguimiento 1:
  * La entrada sale del corpus validado (data/corpus.json) en lugar de extraer
    el abstract con expresiones regulares sobre el texto plano del PDF.
  * El preprocesamiento usa src/preprocesamiento con las mismas reglas del
    seguimiento: minúsculas, guiones como separadores, sin números, sin stopwords,
    sin stemming y descartando palabras de 1-2 letras excepto "ai".

Complejidades (n = términos distintos, k = frecuencia máxima, d = dígitos de k):
    Counting Sort  O(n + k)            estable
    Radix Sort     O(d·(n + b)), b=10  estable (cada pasada reparte en cubetas)
    Bucket Sort    O(n) promedio, O(n²) peor caso (inserción dentro de cada cubeta)
"""
from __future__ import annotations

import statistics
import time

from src.corpus import cargar_corpus
from src.preprocesamiento.texto import preprocesar


# --------------------------------------------------------------------------- #
# Entrada: frecuencias de términos
# --------------------------------------------------------------------------- #
def tokens_seguimiento(abstract: str) -> list[str]:
    return preprocesar(abstract, quitar_stopwords=True, stemming=False, longitud_minima=3,
                       quitar_numeros=True, excepciones=("ai",))


def frecuencias_corpus(ids: list[int] | None = None) -> list[tuple[str, int]]:
    """Lista de pares (término, frecuencia) contada con una tabla hash."""
    frecuencias: dict[str, int] = {}
    for art in cargar_corpus():
        if ids is not None and art["id"] not in ids:
            continue
        for t in tokens_seguimiento(art["abstract"]):
            frecuencias[t] = frecuencias.get(t, 0) + 1
    return list(frecuencias.items())


def caracterizacion() -> list[dict]:
    filas = []
    for art in cargar_corpus():
        tokens = tokens_seguimiento(art["abstract"])
        filas.append({"id": art["id"], "titulo": art["titulo"],
                      "palabras": len(art["abstract"].split()),
                      "tokens": len(tokens), "unicos": len(set(tokens))})
    return filas


# --------------------------------------------------------------------------- #
# Algoritmos (Seguimiento 1)
# --------------------------------------------------------------------------- #
def counting_sort(pares):
    if not pares:
        return []
    k = max(f for _, f in pares)
    conteo = [0] * (k + 1)
    for _, f in pares:
        conteo[f] += 1
    for i in range(1, k + 1):
        conteo[i] += conteo[i - 1]
    salida = [None] * len(pares)
    for i in range(len(pares) - 1, -1, -1):
        f = pares[i][1]
        conteo[f] -= 1
        salida[conteo[f]] = pares[i]
    return salida


def radix_sort(pares, base=10):
    if not pares:
        return []
    arr = list(pares)
    maximo = max(f for _, f in arr)
    exp = 1
    while maximo // exp > 0:
        cubetas = [[] for _ in range(base)]
        for par in arr:
            digito = (par[1] // exp) % base
            cubetas[digito].append(par)
        arr = [par for cubeta in cubetas for par in cubeta]
        exp *= base
    return arr


def bucket_sort(pares, n_cubetas=None):
    if not pares:
        return []
    n = len(pares)
    if n_cubetas is None:
        n_cubetas = n
    maximo = max(f for _, f in pares)
    minimo = min(f for _, f in pares)
    rango = (maximo - minimo) or 1
    cubetas = [[] for _ in range(n_cubetas)]
    for par in pares:
        idx = int((par[1] - minimo) * (n_cubetas - 1) / rango)
        cubetas[idx].append(par)
    salida = []
    for cubeta in cubetas:
        for i in range(1, len(cubeta)):
            actual = cubeta[i]
            j = i - 1
            while j >= 0 and cubeta[j][1] > actual[1]:
                cubeta[j + 1] = cubeta[j]
                j -= 1
            cubeta[j + 1] = actual
        salida.extend(cubeta)
    return salida


ALGORITMOS = {"Counting Sort": counting_sort, "Radix Sort": radix_sort,
              "Bucket Sort": bucket_sort}


def ranking(orden_ascendente, top: int = 15) -> list[tuple[str, int]]:
    return list(reversed(orden_ascendente))[:top]


# --------------------------------------------------------------------------- #
# Medición (misma metodología del Seguimiento 1)
# --------------------------------------------------------------------------- #
def medir(funcion, pares, repeticiones: int = 1000) -> dict:
    """Promedio, mínimo y máximo (ms) de 'repeticiones' ejecuciones; cada una
    recibe una copia nueva de la lista y se descarta una ejecución de calentamiento."""
    funcion(list(pares))
    tiempos = []
    resultado = None
    for _ in range(repeticiones):
        copia = list(pares)
        t0 = time.perf_counter()
        resultado = funcion(copia)
        tiempos.append((time.perf_counter() - t0) * 1000)
    return {"resultado": resultado, "promedio_ms": statistics.fmean(tiempos),
            "min_ms": min(tiempos), "max_ms": max(tiempos), "total_s": sum(tiempos) / 1000}


def experimento_documentos(tamanos=(5, 10, 15, 20), repeticiones: int = 1000) -> list[dict]:
    filas = []
    ids = [a["id"] for a in cargar_corpus()]
    for t in tamanos:
        pares = frecuencias_corpus(ids[:t])
        for nombre, f in ALGORITMOS.items():
            m = medir(f, pares, repeticiones)
            filas.append({"documentos": t, "n": len(pares), "k": max(x for _, x in pares),
                          "algoritmo": nombre, "promedio_ms": m["promedio_ms"],
                          "min_ms": m["min_ms"], "max_ms": m["max_ms"]})
    return filas


def distribucion_cubetas(pares, n_cubetas=None) -> list[int]:
    """Tamaño de cada cubeta de Bucket Sort (para ver el efecto de la ley de Zipf)."""
    n = len(pares)
    n_cubetas = n_cubetas or n
    maximo = max(f for _, f in pares)
    minimo = min(f for _, f in pares)
    rango = (maximo - minimo) or 1
    tamanos = [0] * n_cubetas
    for _, f in pares:
        tamanos[int((f - minimo) * (n_cubetas - 1) / rango)] += 1
    return tamanos
