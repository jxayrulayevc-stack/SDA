"""The scanner is tested with values generated at runtime, never literals."""

from scripts.check_secrets import scan_path


def _write(path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_detects_generated_token(tmp_path) -> None:
    token = "1" * 9 + ":" + "A" * 35
    target = tmp_path / "sample.py"
    _write(target, f"TOKEN = '{token}'\n")
    findings = scan_path(target)
    assert any(label == "telegram_bot_token" for _, _, label in findings)


def test_detects_forbidden_filename(tmp_path) -> None:
    target = tmp_path / "accounts.db"
    _write(target, "safe text\n")
    findings = scan_path(target)
    assert any(label == "forbidden filename" for _, _, label in findings)


def test_detects_generated_fernet_key(tmp_path) -> None:
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    target = tmp_path / "settings.txt"
    _write(target, f"ENCRYPTION_KEY={key}\n")
    findings = scan_path(target)
    assert any(label in {"fernet_key", "env_secret_value"} for _, _, label in findings)


def test_safe_source_is_not_flagged(tmp_path) -> None:
    target = tmp_path / "example.py"
    _write(target, "shared_secret = payload['shared_secret']\n")
    assert scan_path(target) == []
