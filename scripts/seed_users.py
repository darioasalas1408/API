from datetime import datetime, timezone

from google.cloud import firestore
from passlib.context import CryptContext

# -----------------------------------------------------------------------------
# Password hashing (DEBE coincidir con AuthService)
# -----------------------------------------------------------------------------
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto"
)

# -----------------------------------------------------------------------------
# Firestore client
# Apunta EXPLÍCITAMENTE a la DB 'synaptia'
# -----------------------------------------------------------------------------
db = firestore.Client(database="synaptia")
print("PROJECT:", db.project, "| DATABASE:", db._database)


# -----------------------------------------------------------------------------
# Upsert user by email
# -----------------------------------------------------------------------------
def upsert_user(*, email: str, full_name: str, password: str, role: str) -> None:
    users = db.collection("users")

    existing = list(
        users.where("email", "==", email)
             .limit(1)
             .stream()
    )

    now = datetime.now(timezone.utc)
    password_hash = pwd_context.hash(password)

    data = {
        "email": email,
        "full_name": full_name,
        "role": role,
        "password_hash": password_hash,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    if existing:
        doc = existing[0]
        users.document(doc.id).set(data, merge=True)
        print(f"🔁 Updated user: {email} (docId={doc.id})")
    else:
        doc_ref = users.add(data)
        print(f"🆕 Created user: {email} (docId={doc_ref[1].id})")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main() -> None:
    print("✅ Running seed_users.py")

    upsert_user(
        email="admin@demo.com",
        full_name="Admin Demo",
        password="admin123",
        role="admin"
    )

    upsert_user(
        email="user@demo.com",
        full_name="User Demo",
        password="user123",
        role="user"
    )

    print("🎉 Seed users completed")


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
