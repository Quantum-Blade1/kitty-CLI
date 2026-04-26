# pip install cryptography
from cryptography.fernet import Fernet
import hashlib
import os
import base64
from pathlib import Path

class MemoryVault:
    """
    AES-256-GCM encrypted storage for sensitive memory facts.
    Key is derived from machine ID + optional passphrase via PBKDF2.
    """

    def __init__(self, passphrase: str = ""):
        self._key = self._derive_key(passphrase)
        self._fernet = Fernet(self._key)

    def _machine_id(self) -> bytes:
        """Stable machine identifier (not secret, just stable)."""
        try:
            if os.name == "nt":
                import subprocess
                r = subprocess.run(["wmic", "csproduct", "get", "UUID"],
                                   capture_output=True, text=True, check=False)
                if r.returncode == 0:
                    return r.stdout.strip().encode()
        except Exception:
            pass
            
        for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
            if Path(path).exists():
                return Path(path).read_bytes().strip()
        return b"kittycode-fallback-id"

    def _derive_key(self, passphrase: str) -> bytes:
        m_id = self._machine_id()
        salt = hashlib.sha256(m_id).digest()
        key = hashlib.pbkdf2_hmac(
            "sha256",
            passphrase.encode() + m_id,
            salt,
            iterations=200_000,
            dklen=32
        )
        return base64.urlsafe_b64encode(key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()
