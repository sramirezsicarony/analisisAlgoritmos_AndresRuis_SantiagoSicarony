"""
Rabin-Karp (1987): búsqueda por huella digital (hash rodante).

Cada cadena de longitud m se interpreta como un número en base d:
    h(S) = ( S[0]·d^(m-1) + S[1]·d^(m-2) + ... + S[m-1] ) mod q
calculado con el método de Horner.  La ventana se "rueda" en O(1):
    h(T[s+1..s+m]) = ( d·( h(T[s..s+m-1]) - T[s]·h ) + T[s+m] ) mod q,
    con h = d^(m-1) mod q.

Si h(ventana) == h(P) se verifica carácter a carácter (para descartar
colisiones o "falsos positivos": hashes iguales con cadenas distintas).

Preprocesamiento: O(m).  Búsqueda: O(n + m) esperado; O(n·m) en el peor caso
(todas las ventanas colisionan).  Con q grande (primo cercano a 10^9) las
colisiones son muy raras; con q pequeño (p. ej. 101) se observan con facilidad,
lo cual es útil para la demostración.
"""
from __future__ import annotations

import time

from src.busqueda.resultado import ResultadoBusqueda

BASE = 256
PRIMO_GRANDE = 1_000_000_007


def hash_horner(cadena: str, d: int = BASE, q: int = PRIMO_GRANDE,
                pasos: list | None = None) -> int:
    h = 0
    for c in cadena:
        nuevo = (d * h + ord(c)) % q
        if pasos is not None:
            pasos.append(f"({d}·{h} + ord('{c}')={ord(c)}) mod {q} = {nuevo}")
        h = nuevo
    return h


def buscar(texto: str, patron: str, q: int = PRIMO_GRANDE, d: int = BASE,
           trazar: bool = False) -> ResultadoBusqueda:
    n, m = len(texto), len(patron)
    t0 = time.perf_counter()
    if m == 0 or m > n:
        return ResultadoBusqueda("Rabin-Karp", patron, [], 0, 0.0, 0.0)
    h = 1
    for _ in range(m - 1):
        h = (h * d) % q                           # d^(m-1) mod q
    pasos_hash_p: list[str] = [] if trazar else None
    hp = hash_horner(patron, d, q, pasos_hash_p)
    t1 = time.perf_counter()

    posiciones: list[int] = []
    pasos: list[dict] = []
    comparaciones = 0
    colisiones = 0
    verificaciones = 0
    ht = 0
    for i in range(m):
        ht = (d * ht + ord(texto[i])) % q
    for s in range(n - m + 1):
        coincide_hash = ht == hp
        es_ocurrencia = False
        if coincide_hash:
            verificaciones += 1
            j = 0
            while j < m:
                comparaciones += 1
                if texto[s + j] != patron[j]:
                    break
                j += 1
            if j == m:
                posiciones.append(s)
                es_ocurrencia = True
            else:
                colisiones += 1
        if trazar:
            pasos.append({"s": s, "ventana": texto[s:s + m], "hash": ht,
                          "accion": "ocurrencia" if es_ocurrencia else
                                    ("colision" if coincide_hash else "distinto")})
        if s < n - m:
            ht = (d * (ht - ord(texto[s]) * h) + ord(texto[s + m])) % q
    t2 = time.perf_counter()
    return ResultadoBusqueda("Rabin-Karp", patron, posiciones, comparaciones, t1 - t0, t2 - t1,
                             pasos, {"hash_patron": hp, "q": q, "d": d, "h": h,
                                     "colisiones": colisiones, "verificaciones": verificaciones,
                                     "pasos_hash_patron": pasos_hash_p or []})
