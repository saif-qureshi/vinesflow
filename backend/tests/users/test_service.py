import pytest

from app.core.exceptions import BadRequestError
from app.core.security import hash_password, verify_password
from app.modules.orgs.service import OrgService
from app.modules.users.models import User
from app.modules.users.schemas import UserUpdate
from app.modules.users.service import UserService


def _user(db) -> User:
    user = User(email="u@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    OrgService(db).create_org_with_owner(owner=user, name="Acme")
    db.refresh(user)
    return user


def _key(user: User) -> str:
    return f"org-{user.memberships[0].org_id}/a.png"


def test_update_profile_sets_fields(db):
    user = _user(db)
    key = _key(user)
    updated = UserService(db).update_profile(
        user, UserUpdate(full_name="New Name", avatar_key=key)
    )
    assert updated.full_name == "New Name"
    assert updated.avatar_key == key
    assert updated.avatar_url.endswith(key)


def test_update_profile_hashes_new_password(db):
    user = _user(db)
    UserService(db).update_profile(user, UserUpdate(password="brandnew123"))
    assert verify_password("brandnew123", user.hashed_password)


def test_blank_avatar_key_clears_to_none(db):
    user = _user(db)
    user.avatar_key = _key(user)
    db.flush()
    UserService(db).update_profile(user, UserUpdate(avatar_key=""))
    assert user.avatar_key is None
    assert user.avatar_url is None


@pytest.mark.parametrize("key", ["/etc/passwd", "../../etc/passwd", "org-99999/a.png"])
def test_avatar_key_outside_the_users_orgs_is_rejected(db, key):
    user = _user(db)
    with pytest.raises(BadRequestError):
        UserService(db).update_profile(user, UserUpdate(avatar_key=key))
