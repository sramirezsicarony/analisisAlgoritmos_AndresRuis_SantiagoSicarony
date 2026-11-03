"""
Preprocesamiento de los abstracts.

Pipeline (cada paso es opcional y se puede activar desde la aplicación):
  1. normalizar: minúsculas y eliminación de todo lo que no sea letra o dígito.
  2. tokenizar: división en palabras.
  3. eliminar stopwords: palabras funcionales del inglés (the, of, and...).
  4. stemming ligero (S-stemmer de Harman, 1991): reduce plurales
     ("assessments" -> "assessment", "studies" -> "study").

Todo está implementado con recorridos explícitos sobre cadenas y listas.
"""
from __future__ import annotations

# Lista de stopwords del inglés (basada en la lista clásica de SMART / NLTK)
STOPWORDS = frozenset("""
a about above after again against all also am an and any are aren't as at be
because been before being below between both but by can can't cannot could
couldn't did didn't do does doesn't doing don't down during each either et al
etc few for from further had hadn't has hasn't have haven't having he her here
hers herself him himself his how however i i.e e.g if in into is isn't it it's
its itself just let's may me might more most much must mustn't my myself no nor
not now of off on once only or other ought our ours ourselves out over own per
same shall she should shouldn't so some such than that that's the their theirs
them themselves then there there's these they this those through thus to too
under until up upon us very via was wasn't we were weren't what what's when
where which while who whom whose why will with within without won't would
wouldn't yet you your yours yourself yourselves one two three four five six
seven eight nine ten whereof thereby therein whilst among amongst
""".split())

LETRAS_VALIDAS = set("abcdefghijklmnopqrstuvwxyz0123456789")


def normalizar(texto: str) -> str:
    """Pasa a minúsculas y reemplaza por espacio cualquier carácter que no sea
    letra (a-z) o dígito. Las letras acentuadas se reducen a su base."""
    resultado = []
    for c in texto.lower():
        if c in LETRAS_VALIDAS:
            resultado.append(c)
        elif c in "áàäâã":
            resultado.append("a")
        elif c in "éèëê":
            resultado.append("e")
        elif c in "íìïî":
            resultado.append("i")
        elif c in "óòöôõ":
            resultado.append("o")
        elif c in "úùüû":
            resultado.append("u")
        elif c in "ñ":
            resultado.append("n")
        else:
            resultado.append(" ")
    # colapsar espacios repetidos
    salida = []
    anterior_espacio = True
    for c in resultado:
        if c == " ":
            if not anterior_espacio:
                salida.append(c)
            anterior_espacio = True
        else:
            salida.append(c)
            anterior_espacio = False
    return "".join(salida).strip()


def tokenizar(texto_normalizado: str) -> list[str]:
    """Divide en palabras recorriendo el texto carácter a carácter."""
    tokens = []
    actual = []
    for c in texto_normalizado:
        if c == " ":
            if actual:
                tokens.append("".join(actual))
                actual = []
        else:
            actual.append(c)
    if actual:
        tokens.append("".join(actual))
    return tokens


def s_stemmer(palabra: str) -> str:
    """S-stemmer de Harman (1991): solo trata plurales regulares del inglés."""
    n = len(palabra)
    if n > 4 and palabra.endswith("ies") and not palabra.endswith(("eies", "aies")):
        return palabra[:-3] + "y"
    if n > 3 and palabra.endswith("es") and not palabra.endswith(("aes", "ees", "oes")):
        # "processes" -> "process", "analyses" -> "analyse"
        if palabra.endswith(("sses", "xes", "ches", "shes")):
            return palabra[:-2]
        return palabra[:-1]
    if n > 3 and palabra.endswith("s") and not palabra.endswith(("us", "ss", "is")):
        return palabra[:-1]
    return palabra


def preprocesar(texto: str, quitar_stopwords: bool = True, stemming: bool = True,
                longitud_minima: int = 2, quitar_numeros: bool = True,
                excepciones: tuple[str, ...] = ("ai",)) -> list[str]:
    """Pipeline completo: devuelve la lista de tokens del texto.

    excepciones: tokens cortos que se conservan aunque no alcancen la longitud
    mínima (regla del Seguimiento 1: se descartan palabras de <= 2 letras salvo "ai").
    """
    tokens = tokenizar(normalizar(texto))
    resultado = []
    for t in tokens:
        if len(t) < longitud_minima and t not in excepciones:
            continue
        if quitar_numeros and t.isdigit():
            continue
        if quitar_stopwords and t in STOPWORDS:
            continue
        resultado.append(s_stemmer(t) if stemming else t)
    return resultado
