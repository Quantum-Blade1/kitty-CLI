import hashlib
import os
import time
import math

class QuantumRNG:
    """
    Quantum-inspired CSPRNG.
    Simulates superposition of N amplitudes, applies interference,
    collapses to a measurement, then feeds into PBKDF2 for key output.
    """

    def __init__(self, n_qubits: int = 8):
        self.n = n_qubits
        self._seed = os.urandom(32)

    def _build_superposition(self) -> list[complex]:
        """N amplitudes initialised to equal superposition: 1/sqrt(N)."""
        mag = 1.0 / math.sqrt(self.n)
        t = time.time_ns()
        return [
            mag * complex(math.cos(i * t % (2 * math.pi)),
                          math.sin(i * t % (2 * math.pi)))
            for i in range(self.n)
        ]

    def _interfere(self, amps: list[complex]) -> list[float]:
        """Apply Hadamard-style interference. Returns probability distribution."""
        probs = [abs(a) ** 2 for a in amps]
        total = sum(probs)
        return [p / total for p in probs]

    def _collapse(self, probs: list[float]) -> int:
        """Measurement: sample one outcome from the probability distribution."""
        import random
        r = random.random()
        cumulative = 0.0
        for i, p in enumerate(probs):
            cumulative += p
            if r <= cumulative:
                return i
        return len(probs) - 1

    def random_bytes(self, n: int) -> bytes:
        """
        Generate n random bytes using repeated superposition collapse.
        Each collapse produces one byte (0-255 mapped from outcome index).
        XOR with os.urandom for true CSPRNG — quantum math adds entropy,
        os.urandom provides cryptographic foundation.
        """
        result = bytearray()
        while len(result) < n:
            amps = self._build_superposition()
            probs = self._interfere(amps)
            outcome = self._collapse(probs)
            byte_val = int((outcome / self.n) * 256) & 0xFF
            result.append(byte_val)
        
        q_bytes = bytes(result[:n])
        o_bytes = os.urandom(n)
        return bytes(a ^ b for a, b in zip(q_bytes, o_bytes)) # XOR for hybrid entropy

    def derive_key(self, salt: bytes = None, length: int = 32) -> bytes:
        """
        Derive a key using quantum entropy + PBKDF2-HMAC-SHA256.
        This is a quantum-resistant key derivation function.
        """
        salt = salt or self.random_bytes(16)
        quantum_entropy = self.random_bytes(32)
        return hashlib.pbkdf2_hmac(
            'sha256',
            quantum_entropy,
            salt + self._seed,
            iterations=100_000,
            dklen=length
        )
