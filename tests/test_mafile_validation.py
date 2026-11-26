import base64
import json

import pytest

from services.mafile import MaFileValidationError, validate_mafile


def test_valid_mafile(fake_mafile: dict, mafile_bytes: bytes) -> None:
    parsed = validate_mafile(mafile_bytes, "fake.maFile")
    assert parsed["account_name"] == fake_mafile["account_name"]
    assert parsed["shared_secret"] == fake_mafile["shared_secret"]


@pytest.mark.parametrize("missing", ["shared_secret", "account_name", "identity_secret"])
def test_required_fields(fake_mafile: dict, missing: str) -> None:
    data = dict(fake_mafile)
    data.pop(missing)
    with pytest.raises(MaFileValidationError):
        validate_mafile(json.dumps(data).encode(), "fake.json")


def test_invalid_base64_secret(fake_mafile: dict) -> None:
    data = dict(fake_mafile, shared_secret="!!!not-base64!!!")
    with pytest.raises(MaFileValidationError):
        validate_mafile(json.dumps(data).encode(), "fake.json")


def test_invalid_login(fake_mafile: dict) -> None:
    data = dict(fake_mafile, account_name="x")
    with pytest.raises(MaFileValidationError):
        validate_mafile(json.dumps(data).encode(), "fake.json")


def test_bad_extension_and_size(mafile_bytes: bytes) -> None:
    with pytest.raises(MaFileValidationError):
        validate_mafile(mafile_bytes, "fake.txt")
    with pytest.raises(MaFileValidationError):
        validate_mafile(mafile_bytes + b" " * 200_000, "fake.json", 100_000)


def test_not_json() -> None:
    with pytest.raises(MaFileValidationError):
        validate_mafile(b"not json", "fake.json")


def test_short_but_valid_secret_is_rejected(fake_mafile: dict) -> None:
    data = dict(
        fake_mafile,
        shared_secret=base64.b64encode(b"short").decode("ascii"),
    )
    with pytest.raises(MaFileValidationError):
        validate_mafile(json.dumps(data).encode(), "fake.json")
