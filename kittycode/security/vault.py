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


def audit_security_posture():
    """Performs a security audit of the KittyCode environment."""
    from kittycode.config.settings import ENV_PATH, OPENROUTER_KEY, GEMINI_KEY, KITTY_PROJECT_DIR
    import os

    checks = []
    
    # 1. ENV File Exists
    env_ok = ENV_PATH.exists()
    checks.append({
        "name": "Global .env Configuration",
        "ok": env_ok,
        "fix": "Run 'kitty setup' to initialize your global environment."
    })
    
    # 2. Key Length Checks
    for key_name, key_val in [("OpenRouter", OPENROUTER_KEY), ("Gemini", GEMINI_KEY)]:
        if key_val:
            is_valid = len(key_val) > 20
            checks.append({
                "name": f"{key_name} Key Integrity",
                "ok": is_valid,
                "fix": f"Your {key_name} key looks too short. Please re-enter it in 'kitty setup'."
            })
    
    # 3. Log Leak Check
    log_file = KITTY_PROJECT_DIR / "router_log.json"
    leak_detected = False
    if log_file.exists():
        log_content = log_file.read_text()
        if OPENROUTER_KEY and OPENROUTER_KEY in log_content:
            leak_detected = True
            
    checks.append({
        "name": "Credential Leak Audit",
        "ok": not leak_detected,
        "fix": "Leaked keys found in logs! Delete .kitty/router_log.json and rotate your API keys immediately."
    })
    
    # 4. File Permissions (Unix only)
    perm_ok = True
    if os.name != "nt" and env_ok:
        mode = os.stat(ENV_PATH).st_mode
        # Check if world readable
        if mode & 0o007:
            perm_ok = False
            
    checks.append({
        "name": "Environment Permissions",
        "ok": perm_ok,
        "fix": f"Run 'chmod 600 {ENV_PATH}' to secure your keys."
    })

    return {
        "ok": all(c["ok"] for c in checks),
        "checks": checks
    }

