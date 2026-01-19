import configparser
import logging
import sys
import uuid
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import Settings  # noqa: E402
from app.models.core_models import Project, Application, Module, Repo  # noqa: E402
from app.services.project_services import ProjectsService  # noqa: E402
from app.services.apps_services import AppsService  # noqa: E402


class FakeSnapshot:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return self._data


class FakeDocument:
    def __init__(self, client, collection_name, store, doc_id):
        self.client = client
        self.collection_name = collection_name
        self.store = store
        self.id = doc_id

    def set(self, data):
        self.store[self.id] = data
        key = (self.collection_name, self.id)
        self.client.set_calls[key] = self.client.set_calls.get(key, 0) + 1

    def get(self):
        return FakeSnapshot(self.store.get(self.id))

    def update(self, data):
        self.set(data)


class FakeQuery:
    def __init__(self, store, field, value):
        self.store = store
        self.field = field
        self.value = value

    def stream(self):
        for data in self.store.values():
            if isinstance(data, dict) and data.get(self.field) == self.value:
                yield FakeSnapshot(data)


class FakeCollection:
    def __init__(self, client, name, store):
        self.client = client
        self.name = name
        self.store = store

    def document(self, doc_id):
        return FakeDocument(self.client, self.name, self.store, doc_id)

    def stream(self):
        for data in self.store.values():
            yield FakeSnapshot(data)

    def where(self, field, op, value):
        assert op == "==", "FakeCollection only supports equality"
        return FakeQuery(self.store, field, value)


class FakeFirestoreClient:
    def __init__(self):
        self.collections = {}
        self.set_calls = {}

    def collection(self, name):
        store = self.collections.setdefault(name, {})
        return FakeCollection(self, name, store)


def build_settings():
    return Settings(
        environment="DEV",
        config=configparser.ConfigParser(),
        gcp_project="test-project",
        firestore_db="test-db",
        apps_collection="apps",
        projects_collection="projects",
        log_level="INFO",
    )


def build_project(name="Project One"):
    return Project(name=name)


def build_application(project_id, name="App One"):
    repo = Repo(repo_url="https://example.com/repo.git", repo_branch="main")
    module = Module(name="Module A", description="Desc", repo=repo)
    return Application(
        project_id=project_id,
        name=name,
        modules=[module],
    )


class TestProjectService(unittest.TestCase):
    def setUp(self):
        self.fake_client = FakeFirestoreClient()
        self.project_patcher = patch(
            "app.services.project_services.firestore.Client",
            lambda *args, **kwargs: self.fake_client,
        )
        self.app_patcher = patch(
            "app.services.apps_services.firestore.Client",
            lambda *args, **kwargs: self.fake_client,
        )
        self.project_patcher.start()
        self.app_patcher.start()

        self.settings = build_settings()
        self.logger = logging.getLogger("test")
        self.service = ProjectsService(settings=self.settings, logger=self.logger)

    def tearDown(self):
        self.project_patcher.stop()
        self.app_patcher.stop()

    def test_create_project_persists_validated_data(self):
        project = build_project()
        self.service.create_project(project)
        stored = self.fake_client.collections["projects"][project.id]
        self.assertEqual(stored["name"], project.name)
        self.assertEqual(self.fake_client.set_calls[("projects", project.id)], 1)

    def test_update_project_raises_when_missing(self):
        project = build_project()
        with self.assertRaises(ValueError):
            self.service.update_project(project)

    def test_update_project_skips_when_no_changes(self):
        project = build_project()
        self.service.create_project(project)
        self.service.update_project(project)
        self.assertEqual(self.fake_client.set_calls[("projects", project.id)], 1)

    def test_update_project_persists_changes(self):
        project = build_project()
        self.service.create_project(project)
        updated = build_project(name="Updated Name")
        updated.id = project.id
        self.service.update_project(updated)
        self.assertEqual(self.fake_client.set_calls[("projects", project.id)], 2)
        self.assertEqual(
            self.fake_client.collections["projects"][project.id]["name"], "Updated Name"
        )

    def test_get_project_returns_validated_model(self):
        project = build_project()
        self.service.create_project(project)
        fetched = self.service.get_project(project.id)
        self.assertEqual(fetched.id, project.id)
        self.assertEqual(fetched.name, project.name)


class TestAppsService(unittest.TestCase):
    def setUp(self):
        self.fake_client = FakeFirestoreClient()
        self.project_patcher = patch(
            "app.services.project_services.firestore.Client",
            lambda *args, **kwargs: self.fake_client,
        )
        self.app_patcher = patch(
            "app.services.apps_services.firestore.Client",
            lambda *args, **kwargs: self.fake_client,
        )
        self.project_patcher.start()
        self.app_patcher.start()

        self.settings = build_settings()
        self.logger = logging.getLogger("test")
        self.service = AppsService(settings=self.settings, logger=self.logger)

    def tearDown(self):
        self.project_patcher.stop()
        self.app_patcher.stop()

    def test_create_app_persists_validated_data(self):
        project_id = str(uuid.uuid4())
        app = build_application(project_id)
        self.service.create_app(app)
        stored = self.fake_client.collections["apps"][app.id]
        self.assertEqual(stored["project_id"], project_id)
        self.assertEqual(self.fake_client.set_calls[("apps", app.id)], 1)

    def test_update_app_raises_when_missing(self):
        app = build_application(str(uuid.uuid4()))
        with self.assertRaises(ValueError):
            self.service.update_app(app)

    def test_update_app_skips_when_no_changes(self):
        app = build_application(str(uuid.uuid4()))
        self.service.create_app(app)
        self.service.update_app(app)
        self.assertEqual(self.fake_client.set_calls[("apps", app.id)], 1)

    def test_update_app_persists_changes(self):
        app = build_application(str(uuid.uuid4()))
        self.service.create_app(app)
        updated = build_application(app.project_id, name="New Name")
        updated.id = app.id
        self.service.update_app(updated)
        self.assertEqual(self.fake_client.set_calls[("apps", app.id)], 2)
        self.assertEqual(
            self.fake_client.collections["apps"][app.id]["name"], "New Name"
        )

    def test_get_app_returns_validated_model(self):
        app = build_application(str(uuid.uuid4()))
        self.service.create_app(app)
        fetched = self.service.get_app(app.id)
        self.assertEqual(fetched.id, app.id)
        self.assertEqual(fetched.name, app.name)


if __name__ == "__main__":
    unittest.main()
