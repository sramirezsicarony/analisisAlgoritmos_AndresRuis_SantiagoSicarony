"""
Construye los "mini-modelos" de embeddings que usa la aplicación.

    python scripts/construir_embeddings.py [--modelos carpeta]

Los modelos preentrenados completos pesan mucho (FastText ~1 GB comprimido),
pero el corpus solo usa unos pocos miles de palabras. Este script:
  1. Descarga (una sola vez) los vectores preentrenados publicados por el
     proyecto gensim-data en GitHub:
       - GloVe  (glove-wiki-gigaword-100): Wikipedia 2014 + Gigaword 5, 100 dim.
       - FastText (fasttext-wiki-news-subwords-300): Wikipedia 2017 + UMBC +
         statmt.org news, 300 dim, entrenado con información de subpalabras.
  2. Recorre el archivo línea a línea y guarda SOLO los vectores de las palabras
     que aparecen en los 20 abstracts, en data/embeddings/<modelo>.npz.

Así la aplicación funciona sin conexión y arranca en segundos. Los vectores
guardados son idénticos a los del modelo original (no se reentrena nada).
"""
from __future__ import annotations

import argparse
import gzip
import sys
import urllib.request
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.corpus import cargar_corpus  # noqa: E402
from src.preprocesamiento.texto import preprocesar  # noqa: E402

BASE = "https://github.com/RaRe-Technologies/gensim-data/releases/download"
MODELOS = {
    "glove100": f"{BASE}/glove-wiki-gigaword-100/glove-wiki-gigaword-100.gz",
    "fasttext300": f"{BASE}/fasttext-wiki-news-subwords-300/fasttext-wiki-news-subwords-300.gz",
}


def vocabulario_corpus() -> set[str]:
    vocab = set()
    for art in cargar_corpus():
        for t in preprocesar(art["abstract"], quitar_stopwords=False, stemming=False,
                             longitud_minima=1, quitar_numeros=False):
            vocab.add(t)
    return vocab


def descargar(url: str, destino: Path) -> None:
    if destino.exists():
        print(f"  ya existe {destino.name}")
        return
    print(f"  descargando {url} ...")
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(destino)


def extraer(archivo: Path, vocab: set[str]) -> tuple[list[str], np.ndarray]:
    palabras, vectores = [], []
    encontradas: dict[str, int] = {}
    with gzip.open(archivo, "rt", encoding="utf-8", errors="ignore") as f:
        primera = f.readline().split()
        if len(primera) != 2:            # archivo sin cabecera "n_palabras dim"
            f.seek(0)
        for linea in f:
            partes = linea.rstrip().split(" ")
            palabra = partes[0]
            clave = palabra.lower()
            if clave not in vocab:
                continue
            # prioridad a la forma en minúscula si el modelo distingue mayúsculas
            if clave in encontradas and palabra != clave:
                continue
            vec = [float(x) for x in partes[1:]]
            if clave in encontradas:
                vectores[encontradas[clave]] = vec
            else:
                encontradas[clave] = len(palabras)
                palabras.append(clave)
                vectores.append(vec)
    return palabras, np.asarray(vectores, dtype=np.float32)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelos", default=str(Path.home() / ".cache" / "modelos_embeddings"),
                    help="carpeta donde se guardan los modelos completos descargados")
    args = ap.parse_args()
    carpeta = Path(args.modelos)
    vocab = vocabulario_corpus()
    print(f"Vocabulario del corpus: {len(vocab)} palabras")
    for nombre, url in MODELOS.items():
        print(f"[{nombre}]")
        archivo = carpeta / f"{nombre}.gz"
        descargar(url, archivo)
        palabras, matriz = extraer(archivo, vocab)
        destino = RAIZ / "data" / "embeddings" / f"{nombre}.npz"
        np.savez_compressed(destino, palabras=np.array(palabras), vectores=matriz)
        print(f"  {len(palabras)}/{len(vocab)} palabras con vector -> {destino}")


if __name__ == "__main__":
    main()
