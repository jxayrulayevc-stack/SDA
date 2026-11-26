"""Generate a new Fernet key for ENCRYPTION_KEY.

Usage: python scripts/generate_key.py
Print the result only into your local, private shell; never commit it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage.crypto import Encryptor  # noqa: E402


def main() -> None:
    print("ENCRYPTION_KEY=" + Encryptor.generate_key())


if __name__ == "__main__":
    main()
