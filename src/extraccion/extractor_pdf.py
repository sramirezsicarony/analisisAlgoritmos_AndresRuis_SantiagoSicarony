"""
Extracción de metadatos (título, autores) y abstract desde los PDF del corpus.

La extracción usa la posición (x, y) y el tamaño de fuente de cada palabra en la
primera página, que entrega pdfplumber. Así se pueden separar las columnas
laterales (palabras clave, afiliaciones, citación) del cuerpo del abstract.

Heurísticas principales:
  * Título: el bloque de palabras con mayor tamaño de fuente (descartando la
    cabecera con el nombre de la revista).
  * Autores: las líneas inmediatamente debajo del título.
  * Abstract: las palabras que están debajo del encabezado "Abstract" /
    "A B S T R A C T", alineadas con su columna, hasta encontrar un terminador
    ("Keywords", "1. Introduction", "Citation", etc.).

Como ninguna heurística es perfecta con 20 maquetaciones distintas, el script
scripts/construir_corpus.py aplica después las correcciones manuales que estén
registradas en data/correcciones.json (y deja constancia de cuáles se usaron).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, asdict
from pathlib import Path

import pdfplumber


@dataclass
class Articulo:
    id: int
    archivo: str
    titulo: str
    autores: list[str]
    abstract: str
    fuente: dict = field(default_factory=dict)  # cómo se obtuvo cada campo

    def a_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Utilidades de texto
# --------------------------------------------------------------------------- #
def normalizar_unicode(texto: str) -> str:
    """Descompone ligaduras (ﬁ -> fi) y unifica comillas y guiones."""
    texto = unicodedata.normalize("NFKC", texto)
    reemplazos = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": " - ", "\u2011": "-", "\u2010": "-",
        "\u00a0": " ", "\ufeff": "", "\u2009": " ",
    }
    for a, b in reemplazos.items():
        texto = texto.replace(a, b)
    return re.sub(r"(\w) '(\s|$)", r"\1'\2", texto)   # learners ' -> learners'


# Prefijos/palabras que suelen formar compuestos con guion (AI-driven, self-regulated)
_PREFIJOS_COMPUESTOS = {
    "ai", "self", "well", "human", "data", "co", "non", "multi", "inter", "pre",
    "post", "meta", "cross", "long", "short", "high", "low", "real", "large",
    "small", "evidence", "technology", "computer", "student", "teacher", "machine",
    "problem", "decision", "simulation", "mixed", "open", "peer", "game", "web",
    "rule", "time", "deep", "learner", "user", "knowledge", "socio", "e", "one",
    "two", "three", "four", "five", "first", "second", "third", "top", "full",
    "semi", "anti", "under", "over", "trans", "sub", "end", "state", "art",
}

GUION_SUAVE = "­"


def _quitar_guion(izquierda: str, derecha: str, vocabulario: set[str] | None) -> bool:
    """Decide si "izq-<salto>der" es un corte de palabra (True) o un compuesto (False)."""
    if not derecha or not derecha[0].islower():
        return False
    izq = re.sub(r"^\W+", "", izquierda).lower()
    m = re.match(r"[a-zA-Z]+", derecha)
    der = m.group(0).lower() if m else ""
    if vocabulario:
        if (izq + der) in vocabulario:
            return True
        if f"{izq}-{der}" in vocabulario:
            return False
    return izq not in _PREFIJOS_COMPUESTOS


def unir_lineas(lineas: list[str], vocabulario: set[str] | None = None) -> str:
    """Une líneas de un párrafo resolviendo los cortes de palabra con guion.

    vocabulario: palabras vistas en el resto del documento; si la palabra unida
    aparece en él, el guion era solo un corte de línea.
    """
    texto = ""
    for linea in lineas:
        linea = linea.replace("-" + GUION_SUAVE, "-").strip()
        if not linea:
            continue
        if not texto:
            texto = linea
        elif texto.endswith(GUION_SUAVE):           # guion suave: corte de palabra
            texto = texto[:-1] + linea
        elif texto.endswith("-") and not texto.endswith(" -"):
            ultima = texto.split()[-1][:-1]
            if _quitar_guion(ultima, linea, vocabulario):
                texto = texto[:-1] + linea         # practi-/tioners -> practitioners
            else:
                texto = texto + linea              # AI-/driven -> AI-driven
        else:
            texto = texto + " " + linea
    texto = texto.replace(GUION_SUAVE, "")
    texto = normalizar_unicode(texto)
    texto = re.sub(r"\s+([̀-ͯ])", r"\1", texto)   # acento suelto: c ́ -> ć
    texto = unicodedata.normalize("NFC", texto)
    texto = re.sub(r"(\w)- (?!and\b|or\b)(\w)", r"\1-\2", texto)  # well- defined
    return re.sub(r"\s+", " ", texto).strip()


# --------------------------------------------------------------------------- #
# Agrupación de palabras en líneas
# --------------------------------------------------------------------------- #
_LIGADURAS = {"fi", "fl", "ff", "ffi", "ffl", "\ufb00", "\ufb01", "\ufb02", "\ufb03", "\ufb04"}


def _palabras(pagina) -> list[dict]:
    """Palabras de la página con posición y tamaño de fuente.

    Algunas revistas dibujan las ligaduras (ﬁ, ﬂ) como un glifo aparte y un poco
    más arriba, lo que parte palabras como "Arti ﬁ cial"; aquí se vuelven a pegar
    cuando los tres trozos están exactamente contiguos en x.
    """
    palabras = [dict(w) for w in pagina.extract_words(
        x_tolerance=1.0, y_tolerance=2, keep_blank_chars=False,
        extra_attrs=["size"],
    )]
    eliminadas: set[int] = set()
    for k, lig in enumerate(palabras):
        if lig["text"] not in _LIGADURAS:
            continue
        tol_y = 0.5 * lig["size"]
        izq = next((i for i, w in enumerate(palabras)
                    if i != k and i not in eliminadas and abs(w["x1"] - lig["x0"]) < 0.6
                    and abs(w["top"] - lig["top"]) < tol_y), None)
        der = next((i for i, w in enumerate(palabras)
                    if i != k and i not in eliminadas and abs(w["x0"] - lig["x1"]) < 0.6
                    and abs(w["top"] - lig["top"]) < tol_y), None)
        if izq is None and der is None:
            continue
        base = palabras[izq] if izq is not None else lig
        texto = (palabras[izq]["text"] if izq is not None else "") + lig["text"] + \
                (palabras[der]["text"] if der is not None else "")
        nueva = dict(base)
        nueva["text"] = texto
        nueva["x0"] = palabras[izq]["x0"] if izq is not None else lig["x0"]
        nueva["x1"] = palabras[der]["x1"] if der is not None else lig["x1"]
        if izq is None:
            nueva["top"] = palabras[der]["top"]
            nueva["bottom"] = palabras[der]["bottom"]
            nueva["size"] = palabras[der]["size"]
        destino = izq if izq is not None else der
        palabras[destino] = nueva
        eliminadas.add(k)
        if izq is not None and der is not None:
            eliminadas.add(der)
    return [w for i, w in enumerate(palabras) if i not in eliminadas]


def _agrupar_lineas(palabras: list[dict], tolerancia: float = 2.5) -> list[list[dict]]:
    """Agrupa palabras con 'top' parecido en una misma línea (orden de lectura)."""
    ordenadas = sorted(palabras, key=lambda w: (round(w["top"]), w["x0"]))
    lineas: list[list[dict]] = []
    for w in ordenadas:
        if lineas and abs(lineas[-1][0]["top"] - w["top"]) <= tolerancia:
            lineas[-1].append(w)
        else:
            lineas.append([w])
    for linea in lineas:
        linea.sort(key=lambda w: w["x0"])
    return lineas


def _texto(linea: list[dict]) -> str:
    return " ".join(w["text"] for w in linea)


# --------------------------------------------------------------------------- #
# Título y autores
# --------------------------------------------------------------------------- #
def extraer_titulo(palabras: list[dict], primera_linea: str) -> tuple[str, float, float]:
    """Devuelve (título, tamaño de fuente, coordenada inferior del bloque)."""
    por_tamano: dict[float, list[dict]] = {}
    for w in palabras:
        por_tamano.setdefault(round(w["size"], 1), []).append(w)
    candidatos = sorted(por_tamano.items(), key=lambda kv: -kv[0])
    for tamano, ws in candidatos:
        texto = _texto(sorted(ws, key=lambda w: (round(w["top"]), w["x0"])))
        compacto = texto.replace(" ", "")
        if len(ws) < 6:                       # nombre de revista, número de página...
            continue
        if primera_linea.replace(" ", "").startswith(compacto):
            continue                          # cabecera con el nombre de la revista
        lineas = _agrupar_lineas(ws, tolerancia=0.45 * tamano)
        titulo = unir_lineas([_texto(l) for l in lineas])
        inferior = max(w["bottom"] for w in ws)
        return titulo, tamano, inferior
    return "", 0.0, 0.0


_MARCAS_AUTOR = re.compile(r"^(?:[a-h]|\d+(?:,\d+)*|\*|∗|,|\||·|and)$")


def extraer_autores(palabras: list[dict], tamano_titulo: float, inferior_titulo: float) -> list[str]:
    """Toma las líneas inmediatamente bajo el título con fuente de tamaño 'autor'."""
    debajo = [w for w in palabras
              if inferior_titulo < w["top"] < inferior_titulo + 45
              and 9.4 <= w["size"] < tamano_titulo - 0.5]
    if not debajo:
        return []
    lineas = _agrupar_lineas(debajo)
    seleccion = []
    tam_ref = None
    for linea in lineas:
        tam = max(w["size"] for w in linea)
        if tam_ref is None:
            tam_ref = tam
        elif abs(tam - tam_ref) > 0.3:
            break
        seleccion.append(linea)
        if len(seleccion) == 2:
            break
    tokens = []
    for linea in seleccion:
        for w in linea:
            # se descartan superíndices (letra o número de afiliación)
            if w["size"] < (tam_ref or 10) - 2:
                tokens.append(",")
                continue
            t = w["text"]
            t = re.sub(r"[\*∗]+$", "", t)
            tokens.append(t if t else ",")
    texto = unir_lineas([" ".join(tokens)])
    partes = re.split(r"\s*(?:,|\||·|\band\b)\s*", texto)
    autores = []
    for p in partes:
        p = " ".join(x for x in p.split() if not _MARCAS_AUTOR.match(x)).strip()
        p = re.sub(r"\s+\d+$", "", p)
        if len(p) > 3 and any(c.isalpha() for c in p) and p.lower() != "and":
            autores.append(p)
    return autores


# --------------------------------------------------------------------------- #
# Abstract
# --------------------------------------------------------------------------- #
_ENCABEZADO = re.compile(r"^(A\s?B\s?S\s?T\s?R\s?A\s?C\s?T|Abstract:?|ABSTRACT)$")
_TERMINADORES = re.compile(
    r"^(Keywords?\b|KEYWORDS\b|Key\s?words\b|1\.?\s+Introduction|1\s*\|\s*I\s?N|Introduction$|"
    r"Citation:|©|Paper type|\d\.?\s+Artificial Intelligence in STEM)",
    re.IGNORECASE,
)


def extraer_abstract(pagina, vocabulario: set[str] | None = None) -> str:
    palabras = _palabras(pagina)
    lineas = _agrupar_lineas(palabras)

    # 1) localizar el encabezado
    encabezado = None
    for linea in lineas:
        # el encabezado puede venir como palabra suelta ("Abstract") o
        # espaciado ("A B S T R A C T"), y a veces comparte línea con otra columna
        for i in range(len(linea)):
            for j in range(i + 1, min(i + 9, len(linea)) + 1):
                trozo = " ".join(w["text"] for w in linea[i:j])
                if _ENCABEZADO.match(trozo) or (j == i + 1 and linea[i]["text"] in ("Abstract", "Abstract:")):
                    encabezado = linea[i:j]
                    break
            if encabezado:
                break
        if encabezado:
            break
    if not encabezado:
        return ""

    x_col = encabezado[0]["x0"] - 4
    y_ini = encabezado[0]["top"] - 1

    # 2) recoger palabras de la columna del abstract
    columna = [w for w in palabras if w["top"] >= y_ini and w["x0"] >= x_col
               and w not in encabezado]
    if not columna:
        return ""
    # tamaño de fuente del cuerpo = moda de los tamaños de la columna
    conteo: dict[float, int] = {}
    primeras = [w for linea in _agrupar_lineas(columna) for w in linea][:60]
    for w in primeras:
        conteo[round(w["size"], 1)] = conteo.get(round(w["size"], 1), 0) + 1
    tam_cuerpo = max(conteo, key=conteo.get)

    resultado: list[str] = []
    for linea in _agrupar_lineas(columna):
        cuerpo = [w for w in linea if abs(w["size"] - tam_cuerpo) <= 0.6]
        if not cuerpo:
            mayor = max(w["size"] for w in linea) > tam_cuerpo
            if mayor and len(resultado) > 3:
                break      # título de sección o texto de la introducción
            continue       # notas al margen, superíndices
        texto = _texto(cuerpo)
        if _TERMINADORES.match(texto):
            if resultado:
                break
            continue
        resultado.append(texto)

    abstract = unir_lineas(resultado, vocabulario)
    abstract = re.sub(r"^(Abstract:?\s*)", "", abstract, flags=re.IGNORECASE)
    abstract = re.sub(r"^[\W_]+", "", abstract)
    return abstract


# --------------------------------------------------------------------------- #
# API principal
# --------------------------------------------------------------------------- #
def numero_desde_nombre(nombre: str) -> int:
    m = re.match(r"\s*(\d+)", nombre)
    return int(m.group(1)) if m else 0


def vocabulario_documento(pdf, max_paginas: int = 8) -> set[str]:
    """Palabras (en minúscula) que aparecen enteras en el documento.

    Sirve para decidir si un guion al final de línea es un corte de palabra.
    """
    vocab: set[str] = set()
    for pagina in pdf.pages[:max_paginas]:
        texto = normalizar_unicode((pagina.extract_text() or "").replace("\u00ad", ""))
        for linea in texto.splitlines():
            # se omite la última palabra de cada línea (puede estar cortada)
            for token in linea.split()[:-1]:
                token = re.sub(r"^\W+|\W+$", "", token).lower()
                if token:
                    vocab.add(token)
    return vocab


def extraer_articulo(ruta: Path) -> Articulo:
    with pdfplumber.open(ruta) as pdf:
        pagina = pdf.pages[0]
        palabras = _palabras(pagina)
        texto_pagina = pagina.extract_text() or ""
        primera_linea = texto_pagina.splitlines()[0] if texto_pagina else ""
        titulo, tam, inferior = extraer_titulo(palabras, primera_linea)
        autores = extraer_autores(palabras, tam, inferior) if titulo else []
        vocabulario = vocabulario_documento(pdf)
        abstract = extraer_abstract(pagina, vocabulario)
    return Articulo(
        id=numero_desde_nombre(ruta.name),
        archivo=ruta.name,
        titulo=titulo,
        autores=autores,
        abstract=abstract,
        fuente={"titulo": "automatica", "autores": "automatica", "abstract": "automatica"},
    )


def extraer_corpus(carpeta: Path) -> list[Articulo]:
    rutas = sorted(Path(carpeta).glob("*.pdf"), key=lambda p: numero_desde_nombre(p.name))
    return [extraer_articulo(r) for r in rutas]
