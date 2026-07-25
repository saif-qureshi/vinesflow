from app.core.security import hash_password
from app.modules.media import service as media_service
from app.modules.media.schemas import MediaCreate
from app.modules.media.service import MediaService
from app.modules.orgs.service import OrgService
from app.modules.users.models import User


class _FakeStorage:
    def __init__(self, sink):
        self.sink = sink

    def delete(self, key):
        self.sink.append(key)

    def key_from_url(self, url):
        from app.core.storage import _key_from_url

        return _key_from_url(url)


def _org(db):
    user = User(email="media@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    return OrgService(db).create_org_with_owner(owner=user, name="Media Co")


def test_media_stores_key_and_cleans_only_removed(db, monkeypatch):
    deleted: list[str] = []
    monkeypatch.setattr(media_service, "get_storage", lambda: _FakeStorage(deleted))
    org = _org(db)
    svc = MediaService(db)

    svc.replace_for(
        org_id=org.id, attachable_type="product", attachable_id=1,
        media=[MediaCreate(url="http://x/org-1/a.png"), MediaCreate(url="http://x/org-1/b.png")],
    )
    db.flush()
    assert {a.storage_key for a in svc.list_for("product", 1)} == {"org-1/a.png", "org-1/b.png"}

    # keep a, drop b -> only b's object is removed
    svc.replace_for(
        org_id=org.id, attachable_type="product", attachable_id=1,
        media=[MediaCreate(url="http://x/org-1/a.png")],
    )
    db.flush()
    assert deleted == ["org-1/b.png"]

    deleted.clear()
    svc.delete_for("product", 1)
    db.flush()
    assert deleted == ["org-1/a.png"]
