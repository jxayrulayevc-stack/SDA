"""Generate a new Fernet key for ENCRYPTION_KEY.

Usage: python scripts/generate_key.py
Print the result only into your local, private shell; never commit it.
"""

from storage.crypto import Encryptor


def main() -> None:
    print("ENCRYPTION_KEY=" + Encryptor.generate_key())


if __name__ == "__main__":
    main()
