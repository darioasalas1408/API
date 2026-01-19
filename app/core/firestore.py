from google.cloud import firestore

def get_firestore_client(project: str | None = None, database: str | None = None) -> firestore.Client:
    kwargs = {}
    if project:
        kwargs["project"] = project
    if database:
        kwargs["database"] = database

    return firestore.Client(**kwargs)
