"""
Distancia de edición de Levenshtein (programación dinámica, tabulación bottom-up).

D[i][j] = número mínimo de operaciones (inserción, eliminación, sustitución)
para transformar los primeros i símbolos de A en los primeros j símbolos de B.

    D[i][0] = i,  D[0][j] = j
    D[i][j] = min( D[i-1][j] + 1,                 # eliminación
                   D[i][j-1] + 1,                 # inserción
                   D[i-1][j-1] + (A[i] != B[j]) ) # sustitución / coincidencia

Similitud normalizada:  sim(A, B) = 1 - D[n][m] / max(n, m)   en [0, 1]

Complejidad: tiempo O(n·m); espacio O(n·m) con la matriz completa, u O(min(n, m))
guardando solo dos filas (función `distancia`).

Las funciones aceptan cadenas (nivel carácter) o listas de tokens (nivel palabra).
"""
from __future__ import annotations

from typing import Sequence


def distancia(a: Sequence, b: Sequence) -> int:
    """Distancia de Levenshtein con espacio lineal (dos filas)."""
    if len(a) < len(b):          # la fila se construye sobre la secuencia más corta
        a, b = b, a
    m = len(b)
    anterior = list(range(m + 1))
    for i in range(1, len(a) + 1):
        actual = [i] + [0] * m
        ai = a[i - 1]
        for j in range(1, m + 1):
            costo = 0 if ai == b[j - 1] else 1
            eliminar = anterior[j] + 1
            insertar = actual[j - 1] + 1
            sustituir = anterior[j - 1] + costo
            mejor = eliminar
            if insertar < mejor:
                mejor = insertar
            if sustituir < mejor:
                mejor = sustituir
            actual[j] = mejor
        anterior = actual
    return anterior[m]


def similitud(a: Sequence, b: Sequence) -> float:
    if len(a) == 0 and len(b) == 0:
        return 1.0
    return 1.0 - distancia(a, b) / max(len(a), len(b))


def matriz_completa(a: Sequence, b: Sequence) -> list[list[int]]:
    """Matriz D completa de (n+1) x (m+1); se usa para la traza paso a paso."""
    n, m = len(a), len(b)
    D = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        D[i][0] = i
    for j in range(m + 1):
        D[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            costo = 0 if a[i - 1] == b[j - 1] else 1
            D[i][j] = min(D[i - 1][j] + 1, D[i][j - 1] + 1, D[i - 1][j - 1] + costo)
    return D


def operaciones(a: Sequence, b: Sequence, D: list[list[int]] | None = None) -> list[tuple]:
    """Reconstruye (backtracking) la secuencia de operaciones de edición óptima.

    Devuelve tuplas (operacion, i, j, simbolo_a, simbolo_b) con operacion en
    {'=', 'S', 'E', 'I'}: coincidencia, sustitución, eliminación, inserción.
    """
    if D is None:
        D = matriz_completa(a, b)
    i, j = len(a), len(b)
    ops = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i - 1] == b[j - 1] and D[i][j] == D[i - 1][j - 1]:
            ops.append(("=", i, j, a[i - 1], b[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and j > 0 and D[i][j] == D[i - 1][j - 1] + 1:
            ops.append(("S", i, j, a[i - 1], b[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and D[i][j] == D[i - 1][j] + 1:
            ops.append(("E", i, j, a[i - 1], None))
            i -= 1
        else:
            ops.append(("I", i, j, None, b[j - 1]))
            j -= 1
    ops.reverse()
    return ops
