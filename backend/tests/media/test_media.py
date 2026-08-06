import pytest

from app.core.exceptions import BadRequestError
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


def _org(db, email="media@test.io", name="Media Co"):
    user = User(email=email, hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    return OrgService(db).create_org_with_owner(owner=user, name=name)


def test_media_stores_key_and_cleans_only_removed(db, monkeypatch):
    deleted: list[str] = []
    monkeypatch.setattr(media_service, "get_storage", lambda: _FakeStorage(deleted))
    org = _org(db)
    svc = MediaService(db)
    a, b = f"org-{org.id}/a.png", f"org-{org.id}/b.png"

    svc.replace_for(
        org_id=org.id, attachable_type="product", attachable_id=1,
        media=[MediaCreate(storage_key=a), MediaCreate(storage_key=b)],
    )
    db.flush()
    assert {x.storage_key for x in svc.list_for(org.id, "product", 1)} == {a, b}

    # keep a, drop b -> only b's object is removed
    svc.replace_for(
        org_id=org.id, attachable_type="product", attachable_id=1,
        media=[MediaCreate(storage_key=a)],
    )
    db.flush()
    assert deleted == [b]

    deleted.clear()
    svc.delete_for(org.id, "product", 1)
    db.flush()
    assert deleted == [a]


@pytest.mark.parametrize(
    "key",
    ["/etc/passwd", "../../etc/passwd", "org-1/../../etc/passwd", "not-an-org-key.png"],
)
def test_media_rejects_keys_outside_the_org_prefix(db, monkeypatch, key):
    deleted: list[str] = []
    monkeypatch.setattr(media_service, "get_storage", lambda: _FakeStorage(deleted))
    org = _org(db)

    with pytest.raises(BadRequestError):
        MediaService(db).replace_for(
            org_id=org.id, attachable_type="product", attachable_id=1,
            media=[MediaCreate(storage_key=key)],
        )
    assert deleted == []


def test_media_rejects_another_orgs_key(db, monkeypatch):
    deleted: list[str] = []
    monkeypatch.setattr(media_service, "get_storage", lambda: _FakeStorage(deleted))
    org = _org(db)
    other = _org(db, email="other@test.io", name="Other Co")

    with pytest.raises(BadRequestError):
        MediaService(db).replace_for(
            org_id=org.id, attachable_type="product", attachable_id=1,
            media=[MediaCreate(storage_key=f"org-{other.id}/logo.png")],
        )
    assert deleted == []


def test_media_is_scoped_to_its_org(db, monkeypatch):
    monkeypatch.setattr(media_service, "get_storage", lambda: _FakeStorage([]))
    org = _org(db)
    other = _org(db, email="other@test.io", name="Other Co")
    svc = MediaService(db)

    svc.replace_for(
        org_id=org.id, attachable_type="product", attachable_id=1,
        media=[MediaCreate(storage_key=f"org-{org.id}/a.png")],
    )
    db.flush()

    assert svc.list_for(other.id, "product", 1) == []
