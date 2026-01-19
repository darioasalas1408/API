"""Utilidades para devolver contenidos de mocks JSON usados en pruebas."""

from pathlib import Path
import json
from typing import Any

# Mapear tipos de mock a nombres de archivo en la carpeta app/mocks
MOCK_FILES = {
    "create_job": "create_job_response.json",
    "get_job_running": "get_job-running.json",
    "get_job_done": "get_job_done.json",
    "app_tech_dependencies": "ejemplo_get_app_tech_dependency.json",
    "app_relations": "ejemplo_get_app_relation.json",
    "project_relations": "mock_project_relation_graph.json",
}

def load_mock(mock_type: str) -> Any:
    """Carga un mock JSON desde la carpeta ``app/mocks``.

    Args:
        mock_type: Clave lógica del mock (debe existir en ``MOCK_FILES``).

    Returns:
        El JSON parseado como dict/list/etc.

    Raises:
        ValueError: Si el ``mock_type`` no está soportado.
        FileNotFoundError: Si el archivo de mock no existe.
        json.JSONDecodeError: Si el archivo no contiene JSON válido.
    """
    mock_filename = MOCK_FILES.get(mock_type)
    if mock_filename is None:
        raise ValueError(
            f"Mock type '{mock_type}' no soportado. Opciones: {', '.join(MOCK_FILES)}"
        )

    mocks_dir = Path(__file__).resolve().parent.parent / "mocks"
    mock_path = mocks_dir / mock_filename

    with mock_path.open("r", encoding="utf-8") as f:
        return json.load(f)
