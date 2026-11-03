"""
Dibujo del dendrograma a partir de la lista de fusiones (sin usar
scipy.cluster.hierarchy.dendrogram): se calcula el orden de las hojas con un
recorrido en profundidad del árbol y cada fusión se dibuja como una "U" entre
las posiciones de sus dos hijos, a la altura de la distancia de fusión.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.clustering.jerarquico import Fusion  # noqa: E402

COLORES = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2",
           "#ca8a04", "#db2777", "#4b5563", "#65a30d"]


def orden_hojas(fusiones: list[Fusion], n: int) -> list[int]:
    hijos = {f.nuevo: (f.a, f.b) for f in fusiones}
    raiz = fusiones[-1].nuevo if fusiones else 0
    orden, pila = [], [raiz]
    while pila:                                 # DFS iterativo
        nodo = pila.pop()
        if nodo < n:
            orden.append(nodo)
        else:
            a, b = hijos[nodo]
            pila.append(b)
            pila.append(a)
    return orden


def dibujar(fusiones: list[Fusion], etiquetas: list[str], titulo: str = "",
            grupos: list[int] | None = None, ax=None):
    n = len(etiquetas)
    orden = orden_hojas(fusiones, n)
    pos = {hoja: i for i, hoja in enumerate(orden)}   # posición vertical de cada nodo
    altura = {i: 0.0 for i in range(n)}
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 0.42 * n + 1.5))
    else:
        fig = ax.figure

    # color de cada nodo: el de su grupo si todos sus miembros están en el mismo
    color_nodo = {}
    miembros = {i: [i] for i in range(n)}
    for i in range(n):
        color_nodo[i] = COLORES[grupos[i] % len(COLORES)] if grupos else "#334155"
    for f in fusiones:
        miembros[f.nuevo] = miembros[f.a] + miembros[f.b]
        if grupos and len({grupos[m] for m in miembros[f.nuevo]}) == 1:
            color_nodo[f.nuevo] = COLORES[grupos[miembros[f.nuevo][0]] % len(COLORES)]
        else:
            color_nodo[f.nuevo] = "#334155"

    for f in fusiones:
        ya, yb = pos[f.a], pos[f.b]
        xa, xb, x = altura[f.a], altura[f.b], f.distancia
        c = color_nodo[f.nuevo]
        ax.plot([xa, x], [ya, ya], color=c, lw=1.6)
        ax.plot([xb, x], [yb, yb], color=c, lw=1.6)
        ax.plot([x, x], [ya, yb], color=c, lw=1.6)
        pos[f.nuevo] = (ya + yb) / 2
        altura[f.nuevo] = x

    ax.set_yticks(range(n))
    ax.set_yticklabels([etiquetas[h] for h in orden], fontsize=8)
    ax.set_ylim(-0.7, n - 0.3)
    ax.invert_yaxis()
    ax.set_xlabel("Distancia de fusión")
    ax.set_title(titulo, fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    return fig
