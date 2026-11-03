"""
Construye data/corpus.json a partir de los PDF de la carpeta articulos/.

    python scripts/construir_corpus.py

1. Extrae automáticamente título, autores y abstract de cada PDF.
2. Aplica las correcciones manuales de data/correcciones.json (si las hay),
   dejando registro en el campo "fuente" de cada artículo.
3. Guarda el resultado en data/corpus.json, que es lo que usa la aplicación.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.extraccion.extractor_pdf import extraer_corpus  # noqa: E402


def main() -> None:
    articulos = extraer_corpus(RAIZ / "articulos")
    ruta_corr = RAIZ / "data" / "correcciones.json"
    correcciones = json.loads(ruta_corr.read_text(encoding="utf-8")) if ruta_corr.exists() else {}

    salida = []
    for art in articulos:
        datos = art.a_dict()
        for campo, valor in correcciones.get(str(art.id), {}).items():
            if campo.startswith("_"):
                continue
            datos[campo] = valor
            datos["fuente"][campo] = "correccion_manual"
        salida.append(datos)
        estado = "OK" if datos["abstract"] and datos["titulo"] and datos["autores"] else "REVISAR"
        print(f"[{estado}] {art.id:>2}. {datos['titulo'][:70]}  ({len(datos['abstract'])} car.)")

    destino = RAIZ / "data" / "corpus.json"
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nCorpus guardado en {destino} ({len(salida)} artículos)")


if __name__ == "__main__":
    main()
