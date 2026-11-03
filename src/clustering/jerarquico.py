"""
Agrupamiento jerárquico aglomerativo implementado desde cero.

Entrada: matriz de distancias D (n x n, simétrica, diagonal 0).
Algoritmo:
  1. Cada abstract empieza como un clúster.
  2. Repetir n-1 veces:
       a) buscar el par de clústeres activos (p, q) con menor distancia;
       b) fusionarlos en un clúster nuevo r = p ∪ q y registrar la fusión;
       c) actualizar la distancia de r a cada clúster k con la fórmula de
          Lance-Williams del criterio elegido:
             d(r,k) = αp·d(p,k) + αq·d(q,k) + β·d(p,q) + γ·|d(p,k) - d(q,k)|

     criterio   αp             αq             β      γ
     single     1/2            1/2            0     -1/2   -> min(d(p,k), d(q,k))
     complete   1/2            1/2            0     +1/2   -> max(d(p,k), d(q,k))
     average    np/(np+nq)     nq/(np+nq)     0      0     -> promedio de todos los pares (UPGMA)
     ward       (np+nk)/N      (nq+nk)/N     -nk/N   0     N = np+nq+nk (sobre distancias euclidianas)

Complejidad: la búsqueda del mínimo recorre la matriz O(n²) y se hace n-1 veces,
así que T(n) = O(n³) en tiempo y O(n²) en espacio. Con n = 20 abstracts son
unas 2 660 comparaciones en la búsqueda de mínimos (Σ_{k=2..20} k(k-1)/2).

La salida usa el formato de "matriz de enlace" de la literatura (y de SciPy):
cada fila [id_a, id_b, distancia, tamaño]; los clústeres nuevos reciben los
identificadores n, n+1, ..., 2n-2.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

CRITERIOS = {
    "single": "Single linkage (enlace simple / vecino más cercano)",
    "complete": "Complete linkage (enlace completo / vecino más lejano)",
    "average": "Average linkage (UPGMA, enlace promedio)",
    "ward": "Ward (mínima varianza)",
}


@dataclass
class Fusion:
    paso: int
    a: int
    b: int
    distancia: float
    tamano: int
    nuevo: int


def lance_williams(criterio: str, d_pk: float, d_qk: float, d_pq: float,
                   n_p: int, n_q: int, n_k: int) -> float:
    if criterio == "single":
        return 0.5 * d_pk + 0.5 * d_qk - 0.5 * abs(d_pk - d_qk)
    if criterio == "complete":
        return 0.5 * d_pk + 0.5 * d_qk + 0.5 * abs(d_pk - d_qk)
    if criterio == "average":
        return (n_p * d_pk + n_q * d_qk) / (n_p + n_q)
    if criterio == "ward":
        total = n_p + n_q + n_k
        valor = ((n_p + n_k) * d_pk ** 2 + (n_q + n_k) * d_qk ** 2 - n_k * d_pq ** 2) / total
        return math.sqrt(max(valor, 0.0))
    raise ValueError(f"Criterio desconocido: {criterio}")


def aglomerativo(D: list[list[float]], criterio: str = "average") -> list[Fusion]:
    n = len(D)
    # copia de trabajo: distancias entre clústeres activos indexadas por id
    dist: dict[int, dict[int, float]] = {i: {j: D[i][j] for j in range(n) if j != i} for i in range(n)}
    tamano = {i: 1 for i in range(n)}
    activos = list(range(n))
    fusiones: list[Fusion] = []
    siguiente = n
    for paso in range(1, n):
        # a) par más cercano (recorrido explícito de la matriz triangular)
        mejor = math.inf
        p = q = -1
        for x in range(len(activos)):
            for y in range(x + 1, len(activos)):
                i, j = activos[x], activos[y]
                d = dist[i][j]
                if d < mejor:
                    mejor, p, q = d, i, j
        # b) fusión
        r = siguiente
        siguiente += 1
        tamano[r] = tamano[p] + tamano[q]
        fusiones.append(Fusion(paso, p, q, mejor, tamano[r], r))
        # c) actualización de Lance-Williams
        dist[r] = {}
        for k in activos:
            if k in (p, q):
                continue
            d_rk = lance_williams(criterio, dist[p][k], dist[q][k], mejor,
                                  tamano[p], tamano[q], tamano[k])
            dist[r][k] = d_rk
            dist[k][r] = d_rk
            del dist[k][p], dist[k][q]
        del dist[p], dist[q]
        activos = [k for k in activos if k not in (p, q)] + [r]
    return fusiones


def matriz_enlace(fusiones: list[Fusion]) -> list[list[float]]:
    return [[f.a, f.b, f.distancia, f.tamano] for f in fusiones]


def miembros(fusiones: list[Fusion], n: int) -> dict[int, list[int]]:
    """Hojas (abstracts) que contiene cada clúster (hojas e internos)."""
    grupos = {i: [i] for i in range(n)}
    for f in fusiones:
        grupos[f.nuevo] = grupos[f.a] + grupos[f.b]
    return grupos


def cortar(fusiones: list[Fusion], n: int, k: int) -> list[int]:
    """Etiqueta de clúster (0..k-1) de cada hoja al cortar el árbol en k grupos:
    se aplican solo las primeras n-k fusiones."""
    padre = list(range(2 * n - 1))

    def raiz(x: int) -> int:
        while padre[x] != x:
            x = padre[x]
        return x

    for f in fusiones[: n - k]:
        padre[f.a] = f.nuevo
        padre[f.b] = f.nuevo
    raices: dict[int, int] = {}
    etiquetas = []
    for i in range(n):
        rz = raiz(i)
        if rz not in raices:
            raices[rz] = len(raices)
        etiquetas.append(raices[rz])
    return etiquetas
