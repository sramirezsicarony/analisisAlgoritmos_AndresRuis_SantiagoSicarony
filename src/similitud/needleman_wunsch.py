"""
Alineamiento global de Needleman-Wunsch (programación dinámica).

F[i][j] = mejor puntaje de alinear A[1..i] con B[1..j]

    F[i][0] = i·g,   F[0][j] = j·g
    F[i][j] = max( F[i-1][j-1] + s(A[i], B[j]),   # diagonal: match / mismatch
                   F[i-1][j]   + g,               # hueco en B
                   F[i][j-1]   + g )              # hueco en A

con s(x, y) = match si x == y, mismatch si no, y g = penalización por hueco.
El alineamiento se recupera recorriendo la matriz desde F[n][m] hasta F[0][0].

Medidas de similitud que se reportan:
  * identidad = coincidencias / longitud del alineamiento          en [0, 1]
  * puntaje normalizado = (F[n][m] - minimo) / (maximo - minimo)    en [0, 1]
    donde maximo = match·min(n,m) + g·|n-m|  y  minimo = g·(n+m)
    (peor caso: ninguna coincidencia y todo alineado contra huecos).

Complejidad: O(n·m) en tiempo y espacio (se necesita la matriz para el traceback).
Se aplica por defecto a nivel de palabras (tokens del abstract).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class ResultadoNW:
    puntaje: int
    alineado_a: list
    alineado_b: list
    coincidencias: int
    sustituciones: int
    huecos: int
    identidad: float
    puntaje_normalizado: float
    matriz: list[list[int]] | None = None


def alinear(a: Sequence, b: Sequence, match: int = 1, mismatch: int = -1,
            gap: int = -1, guardar_matriz: bool = False) -> ResultadoNW:
    n, m = len(a), len(b)
    F = [[0] * (m + 1) for _ in range(n + 1)]
    # P guarda de dónde vino cada celda: 'D' diagonal, 'U' arriba, 'L' izquierda
    P = [[""] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        F[i][0] = i * gap
        P[i][0] = "U"
    for j in range(1, m + 1):
        F[0][j] = j * gap
        P[0][j] = "L"
    for i in range(1, n + 1):
        ai = a[i - 1]
        for j in range(1, m + 1):
            diag = F[i - 1][j - 1] + (match if ai == b[j - 1] else mismatch)
            arriba = F[i - 1][j] + gap
            izq = F[i][j - 1] + gap
            if diag >= arriba and diag >= izq:
                F[i][j], P[i][j] = diag, "D"
            elif arriba >= izq:
                F[i][j], P[i][j] = arriba, "U"
            else:
                F[i][j], P[i][j] = izq, "L"

    # traceback
    al_a, al_b = [], []
    i, j = n, m
    coinc = sust = huecos = 0
    while i > 0 or j > 0:
        mov = P[i][j]
        if mov == "D":
            al_a.append(a[i - 1]); al_b.append(b[j - 1])
            if a[i - 1] == b[j - 1]:
                coinc += 1
            else:
                sust += 1
            i, j = i - 1, j - 1
        elif mov == "U":
            al_a.append(a[i - 1]); al_b.append("-")
            huecos += 1
            i -= 1
        else:
            al_a.append("-"); al_b.append(b[j - 1])
            huecos += 1
            j -= 1
    al_a.reverse(); al_b.reverse()

    longitud = len(al_a)
    identidad = coinc / longitud if longitud else 1.0
    maximo = match * min(n, m) + gap * abs(n - m)
    # el peor puntaje óptimo posible: emparejar todo como mismatch (si sale más
    # barato que dos huecos) o alinear todo contra huecos
    if mismatch >= 2 * gap:
        minimo = mismatch * min(n, m) + gap * abs(n - m)
    else:
        minimo = gap * (n + m)
    rango = maximo - minimo
    normalizado = (F[n][m] - minimo) / rango if rango else 1.0
    return ResultadoNW(F[n][m], al_a, al_b, coinc, sust, huecos, identidad,
                       normalizado, F if guardar_matriz else None)


def similitud(a: Sequence, b: Sequence, **kw) -> float:
    """Similitud = identidad del alineamiento global."""
    return alinear(a, b, **kw).identidad
