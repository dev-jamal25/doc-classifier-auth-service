from sqlalchemy import Boolean, String

from app.db.base import Base
from app.db.models import User


def test_user_model_table_name_and_metadata_registration() -> None:
    assert User.__tablename__ == "users"
    assert Base.metadata.tables["users"] is User.__table__


def test_user_email_column_matches_fastapi_users_mixin() -> None:
    email = User.__table__.c.email

    assert isinstance(email.type, String)
    assert email.type.length == 320
    assert email.nullable is False
    assert email.index is True
    assert email.unique is True


def test_user_password_column_matches_fastapi_users_mixin() -> None:
    hashed_password = User.__table__.c.hashed_password

    assert isinstance(hashed_password.type, String)
    assert hashed_password.type.length == 1024
    assert hashed_password.nullable is False


def test_user_status_flags_are_required_booleans() -> None:
    for column_name in ("is_active", "is_superuser", "is_verified"):
        column = User.__table__.c[column_name]
        assert isinstance(column.type, Boolean)
        assert column.nullable is False
