# Startia | Application Management API

API en FastAPI para gestionar proyectos, aplicaciones, módulos y repositorios, con persistencia en Firestore y rutas mock para pruebas sin GCP.

## Endpoints principales
- `POST /projects` / `GET /projects` / `GET /projects/{project_id}`: crear y consultar proyectos.
- `POST /applications` / `PUT /applications` / `GET /applications/{app_id}` / `GET /applications?project_id=...`: CRUD de aplicaciones asociadas a un proyecto.
- `POST /applications/{application_id}/modules` / `PUT /applications/{application_id}/modules`: crear/actualizar módulos (solo nombre y descripción).
- `POST /applications/{application_id}/modules/{module_id}/repo`: crear/actualizar repo de un módulo (token se hashea).
- Mock equivalents bajo `/mocks/...` para probar sin Firestore.

## Requisitos
- Python 3.11+ (local).
- GCP Firestore y credenciales si usas persistencia real (`GOOGLE_APPLICATION_CREDENTIALS`).
- Archivo de configuración INI accesible vía `CONFIG_FILE` (por defecto `app/config.ini`).

## Configuración
Variables relevantes (env):
- `CONFIG_FILE`: ruta al INI con colecciones/DB (`app/config.ini` por defecto).
- `SYNAPTIA_ENV`: `DEV`/`PROD` (default `DEV`).
- `GOOGLE_CLOUD_PROJECT`: opcional, sobreescribe el del INI.
- `GOOGLE_APPLICATION_CREDENTIALS`: JSON de credenciales GCP para Firestore/Logging.

## Ejecutar local
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
export CONFIG_FILE=app/config.ini
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

## Ejecutar en Docker
Build local:
```bash
docker build -t startia-app-mgmt .
docker run -p 8080:8080 \
  -e CONFIG_FILE=/app/config.ini \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp.json \
  -v $(pwd)/app/config.ini:/app/config.ini \
  -v $(pwd)/secrets:/secrets \
  startia-app-mgmt
```
La imagen publicada (si aplica) puede usarse de la misma forma. El Dockerfile ya expone `PYTHONPATH=/app` y arranca con `uvicorn main:app`.

### Imagen publicada
La imagen docker del manager de aplicaciones se encuentra en el  registry de gitlab:
`registry.gitlab.com/ingeniaca/archiwise/application-management
Para poder obtener la imagen y correr localmente:

docker login registry.gitlab.com -u <usuario> <token_o_password>
docker pull registry.gitlab.com/ingeniaca/archiwise/application-management:latest


Luego, para levantarlo:
(Modifica el comando para que tmp y secrets apunten a una carpeta local correcta)

docker run -p 8000:8080 -v ./app/tmp:/tmp -v ./secrets:/secrets --env-file .env_local -d startia-func


#### Condiciones para hacerlo funcionar

Para poder ejecutar los mocks, no hace falta mas que contar con el docker. Si en cambio, quisiera ademas correr la logica completa, debiera contar con un secret de google para acceder a las collections firestore.

Para poder obtener el secret de google, pedirle a algun administrador de GCP de Ingenia, que provea uno en el proyecto adecuado.

## Rutas mock
Usa `/mocks/projects`, `/mocks/applications`, `/mocks/applications/{id}/modules`, `/mocks/applications/{id}/modules/{module}/repo` para probar sin Firestore. Los datos viven en memoria del proceso.

## Tests
```bash
python -m unittest discover -s app/tests
```

## Estructura relevante
- `app/main.py`: arranque FastAPI y wiring de servicios.
- `app/api/routes/`: routers de proyectos, aplicaciones y mocks.
- `app/services/`: lógica de negocio y persistencia en Firestore.
- `app/models/core_models.py`: modelos y validaciones (UUIDs, longitudes, URL http/https).
