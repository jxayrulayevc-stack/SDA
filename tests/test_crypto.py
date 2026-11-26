import pytest

from storage.crypto import Encryptor, EncryptionError
from storage.crypto import Fernet


def test_generate_key_is_fernet_key() -> None:
    key = Encryptor.generate_key()
    assert isinstance(Fernet(key), Fernet)


def test_roundtrip(fake_mafile: dict, encryptor: Encryptor) -> None:
    token = encryptor.encrypt(fake_mafile)
    assert token != fake_mafile["shared_secret"]
    assert encryptor.decrypt(token) == fake_mafile


def test_wrong_key_fails(fake_mafile: dict, encryptor: Encryptor) -> None:
    token = encryptor.encrypt(fake_mafile)
    other = Encryptor(Fernet.generate_key().decode())
    with pytest.raises(EncryptionError):
        other.decrypt(token)


def test_tampered_token_fails(fake_mafile: dict, encryptor: Encryptor) -> None:
    token = encryptor.encrypt(fake_mafile)
    with pytest.raises(EncryptionError):
        encryptor.decrypt(token[:-3] + "AAA")
