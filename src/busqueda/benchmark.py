"""
Experimentos de rendimiento del Requerimiento 3: se mide por separado el tiempo
de preprocesamiento y el de búsqueda de cada algoritmo, y el número de
comparaciones de caracteres, variando el tamaño del texto (n) y del patrón (m).
"""
from __future__ import annotations

import statistics

from src.busqueda import boyer_moore, kmp, rabin_karp
from src.corpus import cargar_corpus

ALGORITMOS = {
    "KMP": kmp.buscar,
    "Boyer-Moore": boyer_moore.buscar,
    "Rabin-Karp": rabin_karp.buscar,
}


def texto_corpus(minusculas: bool = True) -> str:
    texto = " ".join(a["abstract"] for a in cargar_corpus())
    return texto.lower() if minusculas else texto


def medir(texto: str, patron: str, repeticiones: int = 5) -> list[dict]:
    filas = []
    for nombre, f in ALGORITMOS.items():
        pre, bus = [], []
        r = None
        for _ in range(repeticiones):
            r = f(texto, patron)
            pre.append(r.tiempo_preproceso_s)
            bus.append(r.tiempo_busqueda_s)
        filas.append({
            "algoritmo": nombre, "n": len(texto), "m": len(patron), "patron": patron,
            "ocurrencias": len(r.posiciones), "comparaciones": r.comparaciones,
            "preproceso_ms": statistics.median(pre) * 1000,
            "busqueda_ms": statistics.median(bus) * 1000,
        })
    return filas


def experimento_tamano_texto(patron: str = "assessment", factores=(1, 2, 4, 8, 16),
                             repeticiones: int = 3) -> list[dict]:
    base = texto_corpus()
    filas = []
    for f in factores:
        filas += medir(" ".join([base] * f), patron, repeticiones)
    return filas


def experimento_tamano_patron(patrones=None, repeticiones: int = 5) -> list[dict]:
    texto = " ".join([texto_corpus()] * 4)
    if patrones is None:
        patrones = ["ai", "data", "learning", "assessment", "higher education",
                    "artificial intelligence", "artificial intelligence in education",
                    "generative artificial intelligence in higher education"]
    filas = []
    for p in patrones:
        filas += medir(texto, p, repeticiones)
    return filas


def experimento_peor_caso(n: int = 20000, m: int = 20, repeticiones: int = 3) -> list[dict]:
    """Texto 'aaaa...a' y patrón 'baa...a'.

    Cada alineación casa m-1 caracteres (de derecha a izquierda) antes de fallar
    en P[0]. Con solo la regla del carácter malo Boyer-Moore desplaza 1 posición
    y hace ~n·m comparaciones (peor caso O(n·m)); con el sufijo bueno el
    desplazamiento es m y vuelve a ser lineal. KMP es lineal siempre.
    """
    texto, patron = "a" * n, "b" + "a" * (m - 1)
    filas = medir(texto, patron, repeticiones)
    pre, bus = [], []
    r = None
    for _ in range(repeticiones):
        r = boyer_moore.buscar(texto, patron, usar_sufijo_bueno=False)
        pre.append(r.tiempo_preproceso_s)
        bus.append(r.tiempo_busqueda_s)
    filas.append({"algoritmo": "Boyer-Moore (solo carácter malo)", "n": n, "m": m,
                  "patron": patron, "ocurrencias": len(r.posiciones),
                  "comparaciones": r.comparaciones,
                  "preproceso_ms": statistics.median(pre) * 1000,
                  "busqueda_ms": statistics.median(bus) * 1000})
    return filas
