"""
Boyer-Moore (1977) con las dos heurísticas.

El patrón se compara de DERECHA a IZQUIERDA. Ante un desajuste en P[j] con el
carácter c = T[s + j], el desplazamiento es el máximo de:

1) Carácter malo:  ult[c] = última posición de c en P (o -1 si no aparece).
     desplazamiento_cm = max(1, j - ult[c])

2) Sufijo bueno (versión fuerte): si ya casaron los caracteres P[j+1..m-1]
   (sufijo bueno u), se desplaza hasta la siguiente aparición de u en P precedida
   por un carácter distinto de P[j], o hasta el prefijo más largo de P que es
   sufijo de u.  Tabla bs[j+1] precalculada en O(m) con la técnica de "bordes".

Tras una ocurrencia completa se desplaza bs[0] (periodo del patrón).

Preprocesamiento: O(m + σ) (σ = tamaño del alfabeto usado).
Búsqueda: O(n/m) en el mejor caso (sublineal), O(n·m) en el peor caso con solo
la regla del carácter malo; con el sufijo bueno fuerte el peor caso para hallar
la primera ocurrencia es O(n + m) (Cole, 1994).
"""
from __future__ import annotations

import time

from src.busqueda.resultado import ResultadoBusqueda


def tabla_caracter_malo(patron: str) -> dict[str, int]:
    ult: dict[str, int] = {}
    for i in range(len(patron)):
        ult[patron[i]] = i              # se sobrescribe: queda la última aparición
    return ult


def tabla_sufijo_bueno(patron: str) -> tuple[list[int], list[int]]:
    """Devuelve (desplazamiento, borde) de tamaño m+1.

    desplazamiento[j] = cuánto mover el patrón si el desajuste ocurre en j-1
    (es decir, si P[j..m-1] ya casó). borde[i] = inicio del borde más ancho de
    P[i..m-1].
    """
    m = len(patron)
    desp = [0] * (m + 1)
    borde = [0] * (m + 1)
    # caso 1: el sufijo bueno aparece en otra parte del patrón
    i, j = m, m + 1
    borde[i] = j
    while i > 0:
        while j <= m and patron[i - 1] != patron[j - 1]:
            if desp[j] == 0:
                desp[j] = j - i
            j = borde[j]
        i -= 1
        j -= 1
        borde[i] = j
    # caso 2: solo un prefijo del patrón coincide con parte del sufijo bueno
    j = borde[0]
    for i in range(m + 1):
        if desp[i] == 0:
            desp[i] = j
        if i == j:
            j = borde[j]
    return desp, borde


def buscar(texto: str, patron: str, trazar: bool = False,
           usar_sufijo_bueno: bool = True) -> ResultadoBusqueda:
    n, m = len(texto), len(patron)
    t0 = time.perf_counter()
    ult = tabla_caracter_malo(patron)
    desp, borde = tabla_sufijo_bueno(patron) if m else ([], [])
    t1 = time.perf_counter()

    posiciones: list[int] = []
    pasos: list[dict] = []
    comparaciones = 0
    s = 0                                    # alineación del patrón sobre el texto
    while m and s <= n - m:
        j = m - 1
        while j >= 0:
            comparaciones += 1
            if patron[j] != texto[s + j]:
                break
            j -= 1
        if j < 0:
            posiciones.append(s)
            d = desp[0] if usar_sufijo_bueno else 1
            if trazar:
                pasos.append({"s": s, "j": -1, "accion": "ocurrencia", "desplazamiento": d,
                              "detalle": f"Patrón completo en s={s}; desplazar bs[0]={d}"})
            s += d
        else:
            c = texto[s + j]
            d_cm = j - ult.get(c, -1)
            d_sb = desp[j + 1] if usar_sufijo_bueno else 0
            d = max(1, d_cm, d_sb)
            if trazar:
                pasos.append({"s": s, "j": j, "accion": "desajuste", "caracter": c,
                              "cm": d_cm, "sb": d_sb, "desplazamiento": d,
                              "detalle": (f"P[{j}]='{patron[j]}' ≠ T[{s + j}]='{c}'; "
                                          f"carácter malo: {j} - ult['{c}']({ult.get(c, -1)}) = {d_cm}; "
                                          f"sufijo bueno: bs[{j + 1}] = {d_sb}; desplazar {d}")})
            s += d
    t2 = time.perf_counter()
    return ResultadoBusqueda("Boyer-Moore", patron, posiciones, comparaciones, t1 - t0, t2 - t1,
                             pasos, {"caracter_malo": ult, "sufijo_bueno": desp, "borde": borde})
