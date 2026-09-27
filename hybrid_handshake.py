import os
import hashlib
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from secure_link_engine import SecureLinkEngine

class MockMLKEM1024:
    """
    A simulation of ML-KEM-1024 (FIPS 203 Kyber) for the purpose of demonstrating
    the hybrid handshake architecture. In a production environment, this would
    be replaced by a C-binding to liboqs (Open Quantum Safe).
    """
    @staticmethod
    def generate_keypair():
        # Simulated Public/Private Keypair
        # Real ML-KEM-1024 pk is 1184 bytes, sk is 2400 bytes
        pk = os.urandom(1184)
        sk = os.urandom(2400)
        return pk, sk
        
    @staticmethod
    def encapsulate(pk: bytes):
        # UAV generates a shared secret and encapsulates it
        # Real ML-KEM-1024 shared secret is 32 bytes, ciphertext is 1568 bytes
        shared_secret = os.urandom(32)
        
        # We simulate the ciphertext cryptographically binding the secret and the pk
        ciphertext = hashlib.sha256(shared_secret + pk).digest() + os.urandom(1568 - 32)
        
        # For the simulation to work without real lattice math, we embed the secret at the end
        ciphertext = ciphertext[:-32] + shared_secret
        return ciphertext, shared_secret
        
    @staticmethod
    def decapsulate(sk: bytes, ciphertext: bytes):
        # GCS decapsulates the ciphertext using its private key
        # In our simulation, we extract the appended secret
        shared_secret = ciphertext[-32:]
        return shared_secret


class HybridHandshake:
    """
    Defense-grade Hybrid Key Exchange combining classical ECDH (X25519) 
    and Post-Quantum KEM (ML-KEM-1024), bound via HKDF-SHA-384.
    """
    def __init__(self, role: str):
        if role not in ("GCS", "UAV"):
            raise ValueError("Role must be GCS or UAV")
        self.role = role
        
        # 1. Classical Keypair (X25519 for Forward Secrecy)
        self.x25519_private_key = x25519.X25519PrivateKey.generate()
        self.x25519_public_key = self.x25519_private_key.public_key()
        
        # 2. PQC Keypair (ML-KEM-1024) - Only GCS generates a keypair for KEM
        self.mlkem_pk = None
        self.mlkem_sk = None
        if self.role == "GCS":
            self.mlkem_pk, self.mlkem_sk = MockMLKEM1024.generate_keypair()
            
    def get_public_keys(self):
        """Returns the public keys to be transmitted."""
        # Note: in a real system, you might want to serialize these with a specific protocol buffer
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        classical_pk = self.x25519_public_key.public_bytes(
            encoding=Encoding.Raw,
            format=PublicFormat.Raw
        )
        if self.role == "GCS":
            return {"classical": classical_pk, "pqc": self.mlkem_pk}
        return {"classical": classical_pk}

    def process_uav_handshake(self, gcs_public_keys: dict):
        """
        UAV side of the handshake.
        """
        assert self.role == "UAV"
        
        # 1. Classical ECDH (K1)
        from cryptography.hazmat.primitives.serialization import PublicFormat, Encoding
        # Load GCS public key
        gcs_classical_pk = x25519.X25519PublicKey.from_public_bytes(gcs_public_keys["classical"])
        k1 = self.x25519_private_key.exchange(gcs_classical_pk)
        
        # 2. PQC Encapsulation (K2)
        ciphertext, k2 = MockMLKEM1024.encapsulate(gcs_public_keys["pqc"])
        
        # 3. Derive Final Key via HKDF
        session_key = self._derive_hkdf(k1, k2)
        
        # Package response for GCS
        uav_public_keys = self.get_public_keys()
        uav_public_keys["pqc_ciphertext"] = ciphertext
        
        return uav_public_keys, session_key, k1, k2
        
    def process_gcs_handshake(self, uav_response: dict):
        """
        GCS side of the handshake.
        """
        assert self.role == "GCS"
        
        # 1. Classical ECDH (K1)
        uav_classical_pk = x25519.X25519PublicKey.from_public_bytes(uav_response["classical"])
        k1 = self.x25519_private_key.exchange(uav_classical_pk)
        
        # 2. PQC Decapsulation (K2)
        k2 = MockMLKEM1024.decapsulate(self.mlkem_sk, uav_response["pqc_ciphertext"])
        
        # 3. Derive Final Key via HKDF
        session_key = self._derive_hkdf(k1, k2)
        
        return session_key, k1, k2

    def _derive_hkdf(self, k1: bytes, k2: bytes) -> bytes:
        """
        Derives the final AES-256 session key using HKDF-SHA-384.
        Follows the standard hybrid combiner: HKDF(K1 || K2)
        """
        hybrid_secret = k1 + k2
        
        hkdf = HKDF(
            algorithm=hashes.SHA384(),
            length=32, # We want a 32-byte (256-bit) key for Layer 1's AES-256-GCM
            salt=b"UAV_GCS_DEFENSE_SALT_v1",
            info=b"HYBRID_SESSION_KEY_DERIVATION"
        )
        return hkdf.derive(hybrid_secret)


def mask_secret(secret: bytes) -> str:
    """Helper to securely print partial secrets."""
    return secret.hex()[:8] + "..." + secret.hex()[-8:]

if __name__ == "__main__":
    print("--- Initializing Defense-Grade Hybrid PQC Handshake ---")
    
    # 1. Initialize nodes
    gcs = HybridHandshake(role="GCS")
    uav = HybridHandshake(role="UAV")
    
    # 2. GCS initiates handshake by sending its public keys
    print("\n[+] GCS initiates handshake -> Sends X25519 and ML-KEM-1024 Public Keys")
    gcs_pk = gcs.get_public_keys()
    print(f"    GCS Classical PK size: {len(gcs_pk['classical'])} bytes")
    print(f"    GCS PQC PK size:       {len(gcs_pk['pqc'])} bytes")
    
    # 3. UAV processes GCS keys, encapsulates PQC secret, and derives session key
    print("\n[+] UAV processing GCS keys...")
    uav_response, uav_session_key, uav_k1, uav_k2 = uav.process_uav_handshake(gcs_pk)
    
    # 4. GCS processes UAV response and decapsulates PQC secret
    print("\n[+] GCS processing UAV response...")
    gcs_session_key, gcs_k1, gcs_k2 = gcs.process_gcs_handshake(uav_response)
    
    # 5. Verification Output
    print("\n--- Handshake Verification ---")
    print("Classical Secret (K1):")
    print(f"  GCS: {mask_secret(gcs_k1)}")
    print(f"  UAV: {mask_secret(uav_k1)}")
    assert gcs_k1 == uav_k1
    
    print("\nPost-Quantum Secret (K2):")
    print(f"  GCS: {mask_secret(gcs_k2)}")
    print(f"  UAV: {mask_secret(uav_k2)}")
    assert gcs_k2 == uav_k2
    
    print("\nDerived Final Session Key (HKDF-SHA-384):")
    print(f"  GCS: {mask_secret(gcs_session_key)}")
    print(f"  UAV: {mask_secret(uav_session_key)}")
    assert gcs_session_key == uav_session_key
    
    if gcs_session_key == uav_session_key:
        print("\n[SUCCESS] Hybrid Handshake completed successfully. Keys match exactly.")
        
    # 6. Integration Hook with Layer 4 (Secure Link Engine)
    print("\n--- Integration with Secure Link Engine ---")
    epoch_id = 100
    print(f"[+] Initializing SecureLinkEngine with derived hybrid session key...")
    
    # Initialize engines with the new derived hybrid key
    uav_engine = SecureLinkEngine(key=uav_session_key, epoch_id=epoch_id)
    gcs_engine = SecureLinkEngine(key=gcs_session_key, epoch_id=epoch_id)
    
    flight_cmd = b"UAV_ARM_PAYLOAD_SYSTEM"
    print(f"[+] UAV encrypting packet: {flight_cmd}")
    
    # Encrypt
    packet = uav_engine.encrypt_packet(direction=0, sequence=1, msg_type=5, payload=flight_cmd)
    print(f"    Raw Encrypted packet: {packet.hex()[:40]}... (Total {len(packet)} bytes)")
    
    # Decrypt
    decrypted = gcs_engine.decrypt_packet(packet)
    print(f"[+] GCS decrypted packet payload: {decrypted['payload']}")
    assert decrypted['payload'] == flight_cmd
