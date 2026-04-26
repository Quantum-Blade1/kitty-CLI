import hashlib
import hmac
import json
import time
from pathlib import Path
from kittycode.config.settings import KITTY_PROJECT_DIR
from kittycode.quantum.rng import QuantumRNG

AUDIT_LOG = KITTY_PROJECT_DIR / "audit_chain.jsonl"

# We derive a stable but unique key for the audit chain.
# In a real system, this would be stored in a secure hardware vault.
_rng = QuantumRNG()
_STATIC_SALT = b"kittycode-audit-salt-v1"
CHAIN_KEY = _rng.derive_key(salt=_STATIC_SALT, length=32)

class AuditChain:
    """
    Blockchain-inspired immutable audit log.
    Each event is a block: {index, ts, event, data, prev_hash, block_hash}
    block_hash = HMAC-SHA256(CHAIN_KEY, prev_hash + event + data + ts)
    Tampering any block breaks the chain.
    """

    def __init__(self, key: bytes = None):
        self._log = AUDIT_LOG
        self._key = key or CHAIN_KEY
        self._last_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        if not self._log.exists():
            return "0" * 64  # genesis
        with open(self._log, "rb") as f:
            lines = f.read().splitlines()
        if not lines:
            return "0" * 64
        try:
            last = json.loads(lines[-1])
            return last.get("block_hash", "0" * 64)
        except (json.JSONDecodeError, IndexError):
            return "0" * 64

    def _compute_hash(self, index: int, ts: float, event: str,
                      data: str, prev_hash: str) -> str:
        payload = f"{index}:{ts}:{event}:{data}:{prev_hash}".encode()
        return hmac.new(self._key, payload, hashlib.sha256).hexdigest()

    def append(self, event: str, data: dict = None) -> dict:
        """Append a security event to the chain. Returns the new block."""
        index = self._count()
        ts = time.time()
        data_str = json.dumps(data or {}, sort_keys=True)
        block_hash = self._compute_hash(index, ts, event, data_str, self._last_hash)
        block = {
            "index": index,
            "ts": ts,
            "event": event,
            "data": data_str,
            "prev_hash": self._last_hash,
            "block_hash": block_hash,
        }
        with open(self._log, "a", encoding="utf-8") as f:
            f.write(json.dumps(block) + "\n")
        self._last_hash = block_hash
        return block

    def verify(self) -> tuple[bool, str]:
        """
        Walk the entire chain and verify every block_hash.
        Returns (True, "Chain valid") or (False, "Tampered at block N").
        """
        if not self._log.exists():
            return True, "Chain empty — valid"
        prev_hash = "0" * 64
        with open(self._log, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    block = json.loads(line)
                    expected = self._compute_hash(
                        block["index"], block["ts"], block["event"],
                        block["data"], prev_hash
                    )
                    if not hmac.compare_digest(expected, block["block_hash"]):
                        return False, f"Chain tampered at block {block['index']}"
                    prev_hash = block["block_hash"]
                except json.JSONDecodeError:
                    return False, "Corrupt block format"
        return True, "Chain valid"

    def _count(self) -> int:
        if not self._log.exists():
            return 0
        with open(self._log, "rb") as f:
            return sum(1 for _ in f)
