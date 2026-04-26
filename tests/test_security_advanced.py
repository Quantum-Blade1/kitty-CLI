import os
import json
from kittycode.quantum.rng import QuantumRNG
from kittycode.security.audit_chain import AuditChain
from kittycode.security.vault import MemoryVault

def test_quantum_rng_produces_different_bytes():
    rng = QuantumRNG()
    b1 = rng.random_bytes(32)
    b2 = rng.random_bytes(32)
    assert b1 != b2
    assert len(b1) == 32
    assert len(b2) == 32

def test_quantum_rng_derive_key_length():
    rng = QuantumRNG()
    key = rng.derive_key(length=32)
    assert len(key) == 32
    assert isinstance(key, bytes)

def test_audit_chain_appends_and_verifies():
    # Use a temporary log path for testing
    from kittycode.security import audit_chain
    import tempfile
    from pathlib import Path
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    original_log = audit_chain.AUDIT_LOG
    audit_chain.AUDIT_LOG = tmp_path
    
    try:
        chain = AuditChain()
        chain.append("TEST_EVENT_1", {"foo": "bar"})
        chain.append("TEST_EVENT_2", {"baz": 123})
        chain.append("TEST_EVENT_3")
        
        valid, msg = chain.verify()
        assert valid is True
        assert "Chain valid" in msg
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
        audit_chain.AUDIT_LOG = original_log

def test_audit_chain_detects_tampering():
    from kittycode.security import audit_chain
    import tempfile
    from pathlib import Path
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    original_log = audit_chain.AUDIT_LOG
    audit_chain.AUDIT_LOG = tmp_path
    
    try:
        chain = AuditChain()
        chain.append("EVENT_1", {"data": "safe"})
        chain.append("EVENT_2", {"data": "safe"})
        
        # Manually corrupt the second line
        with open(tmp_path, "r") as f:
            lines = f.readlines()
        
        # Change data in the first block
        block = json.loads(lines[0])
        block["data"] = '{"data": "tampered"}'
        lines[0] = json.dumps(block) + "\n"
        
        with open(tmp_path, "w") as f:
            f.writelines(lines)
            
        valid, msg = chain.verify()
        assert valid is False
        assert "Chain tampered" in msg
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
        audit_chain.AUDIT_LOG = original_log

def test_vault_encrypt_decrypt_roundtrip():
    vault = MemoryVault(passphrase="test-password")
    plaintext = "hello kitty security"
    ciphertext = vault.encrypt(plaintext)
    assert ciphertext != plaintext
    
    decrypted = vault.decrypt(ciphertext)
    assert decrypted == plaintext
