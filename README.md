# Análisis de algoritmos en el contexto de la bibliometría

Proyecto final de **Análisis de Algoritmos 2026-2** (Universidad del Quindío).
Aplicación en Python que analiza los *abstracts* de 20 artículos científicos sobre IA
(generativa) en educación con algoritmos implementados desde cero.

| Sección | Algoritmos |
|---|---|
| Req. 1 · Similitud textual | Levenshtein, Needleman-Wunsch, coseno TF-IDF, Jaccard · IA: GloVe y FastText (embeddings preentrenados) |
| Req. 2 · Clustering jerárquico | Single, Complete y Average linkage (+ Ward), dendrogramas, correlación cofenética y silueta |
| Req. 3 · Búsqueda de patrones | Knuth-Morris-Pratt, Boyer-Moore (carácter malo + sufijo bueno), Rabin-Karp |
| Seguimiento 1 | Counting Sort, Radix Sort y Bucket Sort para el ranking de términos |

## 1. Instalación (Windows, VS Code)

Requisitos: Python 3.10 o superior.

```powershell
cd "ruta\a\Proyecto"
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
```

`requirements.txt` trae solo lo que usa la aplicación (es lo que instala Streamlit Cloud);
`requirements-dev.txt` agrega lo necesario para extraer los PDF, generar el documento y correr las pruebas.

En VS Code: `Ctrl+Shift+P` → *Python: Select Interpreter* → elegir `.venv`.

## 2. Ejecutar la aplicación

```powershell
streamlit run app.py
```

Se abre en el navegador en http://localhost:8501. El menú lateral tiene las secciones
Corpus, Req. 1, Req. 2, Req. 3 y Seguimiento 1.

## 3. Pruebas automáticas

```powershell
python -m pytest
```

Verifican los algoritmos con casos clásicos, contra búsqueda por fuerza bruta en miles de
casos aleatorios y contra SciPy / scikit-learn (que solo se usan como referencia en las pruebas).

## 4. Regenerar datos y documento

Los datos ya vienen generados en `data/`. Los PDF de los artículos no están en el repositorio
(son de sus editoriales); para reconstruir el corpus hay que copiarlos a `articulos/`. Para reconstruirlos:

```powershell
python scripts/construir_corpus.py       # PDF de articulos/ -> data/corpus.json
python scripts/construir_embeddings.py   # descarga GloVe y FastText (~1,2 GB, una sola vez) -> data/embeddings/
python scripts/generar_documento.py      # -> docs/Documento_Tecnico.docx, docs/figuras, docs/resultados
```

## 5. Estructura

```
app.py                      Interfaz web (Streamlit)
articulos/                  Los 20 PDF del corpus (no se publican en el repositorio)
data/corpus.json            Título, autores y abstract de cada artículo
data/correcciones.json      Correcciones manuales opcionales (vacío: no fueron necesarias)
data/embeddings/            Vectores GloVe/FastText de las palabras del corpus
src/extraccion/             Extracción de metadatos y abstract de los PDF
src/preprocesamiento/       Normalización, tokenización, stopwords, S-stemmer
src/similitud/              Req. 1
src/clustering/             Req. 2
src/busqueda/               Req. 3
src/ordenamiento/           Seguimiento 1
scripts/                    Construcción de datos y del documento técnico
tests/                      Pruebas (pytest)
docs/                       Documento técnico, figuras y resultados en CSV
```

## 6. Despliegue

La aplicación está publicada en **Google Cloud Run**:
https://analisis-algoritmos-1055040261530.us-central1.run.app

Cloud Run construye la imagen con el `Dockerfile` (python:3.12-slim + `requirements.txt`,
puerto 8501), la publica en una URL HTTPS y escala a cero cuando nadie la usa. Los datos de
`data/` van dentro de la imagen, así que no se descarga nada en el servidor.

Se desplegó desde **Cloud Shell** (consola de Google Cloud), con el proyecto
`analisis-algoritmos-513706`:

```bash
gcloud config set project analisis-algoritmos-513706
git clone https://github.com/sramirezsicarony/analisisAlgoritmos_AndresRuis_SantiagoSicarony.git
cd analisisAlgoritmos_AndresRuis_SantiagoSicarony
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# Solo la primera vez en un proyecto nuevo: permiso de compilación para la cuenta de servicio
# por defecto (sin esto el despliegue falla con 403 storage.objects.get)
gcloud projects add-iam-policy-binding analisis-algoritmos-513706 \
    --member=serviceAccount:1055040261530-compute@developer.gserviceaccount.com \
    --role=roles/run.builder

gcloud run deploy analisis-algoritmos --source . --region us-central1 --port 8501 \
    --memory 1Gi --timeout 3600 --session-affinity --allow-unauthenticated
```

`--timeout 3600` y `--session-affinity` son necesarios porque Streamlit mantiene un WebSocket
abierto por usuario. Para publicar cambios: `git pull` en Cloud Shell y repetir el
`gcloud run deploy` (crea una revisión nueva sin cortar el servicio).

**Otras opciones.** Streamlit Community Cloud (https://share.streamlit.io → *Create app* →
este repositorio, rama `main`, archivo `app.py`) o Docker en cualquier servicio de contenedores:

```bash
docker build -t bibliometria .
docker run -p 8501:8501 bibliometria
```

## 7. Uso de IA generativa

Ver la sección 9 de `docs/Documento_Tecnico.docx` (declaración del uso de IA).
