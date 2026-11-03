"""
Knuth-Morris-Pratt (1977).

Preprocesamiento: función de fallo (tabla LPS, "longest proper prefix which is
also suffix"):  π[q] = longitud del prefijo propio más largo de P[0..q] que
también es sufijo de P[0..q].  Se calcula en O(m).

Búsqueda: se recorre el texto una sola vez; cuando hay un desajuste después de
haber casado q caracteres, el patrón se desplaza para que el prefijo P[0..π[q-1]]
quede alineado, sin retroceder en el texto.  O(n).

Total: O(n + m) en tiempo (peor caso incluido) y O(m) de espacio extra.
Número de comparaciones de la búsqueda ≤ 2n.
"""
from __future__ import annotations

import time

from src.busqueda.resultado import ResultadoBusqueda


def tabla_fallo(patron: str, contador: list[int] | None = None) -> list[int]:
    m = len(patron)
    pi = [0] * m
    k = 0
    for q in range(1, m):
        while k > 0 and patron[k] != patron[q]:
            if contador is not None:
                contador[0] += 1
            k = pi[k - 1]
        if contador is not None:
            contador[0] += 1
        if patron[k] == patron[q]:
            k += 1
        pi[q] = k
    return pi


def buscar(texto: str, patron: str, trazar: bool = False) -> ResultadoBusqueda:
    n, m = len(texto), len(patron)
    t0 = time.perf_counter()
    pi = tabla_fallo(patron) if m else []
    t1 = time.perf_counter()

    posiciones: list[int] = []
    pasos: list[dict] = []
    comparaciones = 0
    q = 0                                  # caracteres casados hasta ahora
    if m and m <= n:
        for i in range(n):
            while q > 0 and patron[q] != texto[i]:
                comparaciones += 1
                if trazar:
                    pasos.append({"i": i, "q": q, "alineacion": i - q, "accion": "fallo",
                                  "detalle": f"T[{i}]='{texto[i]}' ≠ P[{q}]='{patron[q]}' → q = π[{q - 1}] = {pi[q - 1]}"})
                q = pi[q - 1]
            comparaciones += 1
            if patron[q] == texto[i]:
                q += 1
                if trazar:
                    pasos.append({"i": i, "q": q, "alineacion": i - q + 1, "accion": "coincide",
                                  "detalle": f"T[{i}]='{texto[i]}' = P[{q - 1}] → q = {q}"})
            elif trazar:
                pasos.append({"i": i, "q": q, "alineacion": i, "accion": "avanza",
                              "detalle": f"T[{i}]='{texto[i]}' ≠ P[0]='{patron[0]}' → avanzar"})
            if q == m:
                posiciones.append(i - m + 1)
                if trazar:
                    pasos.append({"i": i, "q": q, "alineacion": i - m + 1, "accion": "ocurrencia",
                                  "detalle": f"¡Ocurrencia en {i - m + 1}! q = π[{m - 1}] = {pi[m - 1]}"})
                q = pi[q - 1]
    t2 = time.perf_counter()
    return ResultadoBusqueda("KMP", patron, posiciones, comparaciones, t1 - t0, t2 - t1,
                             pasos, {"tabla_fallo": pi})
