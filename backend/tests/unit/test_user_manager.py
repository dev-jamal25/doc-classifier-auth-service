from app.api.auth.manager import UserManager
from tests.unit.fakes import FakeUserDatabase


def test_user_manager_uses_supplied_token_secret() -> None:
    manager = UserManager(FakeUserDatabase(), "vault-jwt-secret")

    assert manager.reset_password_token_secret == "vault-jwt-secret"
    assert manager.verification_token_secret == "vault-jwt-secret"


def test_user_manager_password_helper_hash_round_trips() -> None:
    manager = UserManager(FakeUserDatabase(), "vault-jwt-secret")

    hashed = manager.password_helper.hash("TempPass123!")
    verified, updated_hash = manager.password_helper.verify_and_update("TempPass123!", hashed)

    assert verified is True
    assert updated_hash is None
