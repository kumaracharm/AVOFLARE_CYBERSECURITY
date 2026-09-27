import struct
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

class SecureLinkEngine:
    """
    Defense-grade UAV <-> GCS Secure Link Engine.
    Implements AES-256-GCM authenticated encryption with a sliding-window anti-replay filter.
    """
    
    def __init__(self, key: bytes, epoch_id: int):
        if len(key) != 32:
            raise ValueError("AES-256-GCM requires a 32-byte key.")
        
        self.key = key
        self.aesgcm = AESGCM(key)
        self.epoch_id = epoch_id
        
        # Anti-replay state
        self.highest_seq = 0
        self.window_mask = 0
        self.WINDOW_SIZE = 64
        
        # Wire Format Framing
        # [Epoch ID (4B)] | [Direction (1B)] | [Sequence (8B)] | [Message Type (1B)]
        # Total: 14 bytes header (used as AAD)
        # Format specifiers: > (Big-Endian), I (uint32), B (uint8), Q (uint64), B (uint8)
        self.HEADER_STRUCT = struct.Struct(">I B Q B")
        self.HEADER_SIZE = self.HEADER_STRUCT.size
        self.TAG_SIZE = 16

    def _generate_nonce(self, epoch_id: int, sequence: int) -> bytes:
        # Nonce is exactly 96 bits (12 bytes): Epoch ID (4B) + Sequence (8B)
        # This guarantees monotonic, non-repeating nonces as long as sequence increments.
        return struct.pack(">I Q", epoch_id, sequence)

    def encrypt_packet(self, direction: int, sequence: int, msg_type: int, payload: bytes) -> bytes:
        header = self.HEADER_STRUCT.pack(self.epoch_id, direction, sequence, msg_type)
        nonce = self._generate_nonce(self.epoch_id, sequence)
        
        # cryptography's AESGCM returns ciphertext + tag appended together
        ciphertext_and_tag = self.aesgcm.encrypt(nonce, payload, header)
        
        return header + ciphertext_and_tag

    def check_replay(self, sequence: int) -> bool:
        """
        Sliding-window bitmask filter.
        Returns True if packet is valid, False if it is a replay or too old.
        """
        if sequence > self.highest_seq:
            diff = sequence - self.highest_seq
            if diff >= self.WINDOW_SIZE:
                self.window_mask = 0
            else:
                self.window_mask <<= diff
            self.window_mask |= 1
            self.highest_seq = sequence
            return True
            
        if sequence <= self.highest_seq:
            diff = self.highest_seq - sequence
            if diff >= self.WINDOW_SIZE:
                return False # Packet too old (outside window)
            
            # Check if we already saw this packet (bit is set)
            if (self.window_mask & (1 << diff)) != 0:
                return False # Replayed / duplicate
                
            self.window_mask |= (1 << diff)
            return True
            
        return False

    def decrypt_packet(self, packet: bytes) -> dict:
        if len(packet) < self.HEADER_SIZE + self.TAG_SIZE:
            raise ValueError("Packet is too short to be valid.")
            
        header = packet[:self.HEADER_SIZE]
        ciphertext_and_tag = packet[self.HEADER_SIZE:]
        
        epoch_id, direction, sequence, msg_type = self.HEADER_STRUCT.unpack(header)
        
        # 1. Invalid Epoch Check (before crypto)
        if epoch_id != self.epoch_id:
            raise ValueError(f"Invalid Epoch ID: expected {self.epoch_id}, got {epoch_id}")
            
        # 2. Anti-Replay Check (before crypto)
        if not self.check_replay(sequence):
            raise ValueError(f"Replay detected or packet too old for Sequence: {sequence}")
            
        # 3. Decrypt and Verify Tag
        nonce = self._generate_nonce(epoch_id, sequence)
        try:
            plaintext = self.aesgcm.decrypt(nonce, ciphertext_and_tag, header)
            return {
                'direction': direction,
                'sequence': sequence,
                'msg_type': msg_type,
                'payload': plaintext
            }
        except InvalidTag:
            # Revert the replay window bit since authentication failed
            # (An attacker could otherwise intentionally drop a valid packet by injecting a tampered one first)
            diff = self.highest_seq - sequence
            self.window_mask &= ~(1 << diff)
            raise ValueError("Authentication failed: invalid AEAD tag or corrupted header/payload.")

if __name__ == "__main__":
    print("--- Initializing Defense-Grade Secure Link Engine ---")
    
    # 1. Setup shared epoch and 32-byte (256-bit) key
    shared_key = os.urandom(32)
    current_epoch = 1337
    
    tx_engine = SecureLinkEngine(shared_key, current_epoch)
    rx_engine = SecureLinkEngine(shared_key, current_epoch)
    
    flight_cmd = b"THROTTLE: 85%"
    direction = 1 # GCS to UAV
    sequence = 45000
    msg_type = 2 # e.g. FLIGHT_CMD
    
    # 2. Encrypt a valid command
    print(f"\n[+] Encrypting Flight Command: {flight_cmd}")
    valid_packet = tx_engine.encrypt_packet(direction, sequence, msg_type, flight_cmd)
    print(f"    Packet encoded! Total Size: {len(valid_packet)} bytes")
    
    # 3. Simulate Valid Receive
    print("\n[+] Simulating normal reception of valid packet...")
    try:
        result = rx_engine.decrypt_packet(valid_packet)
        print(f"    Success! Decrypted Payload: {result['payload']}")
    except Exception as e:
        print(f"    FAIL: {e}")
        
    # 4. Simulate Active Replay Attack
    print("\n[!] ATTACK SIMULATION: Adversary captures and replays the exact same packet...")
    try:
        rx_engine.decrypt_packet(valid_packet)
        print("    FAIL: Engine accepted replay!")
    except ValueError as e:
        print(f"    SECURITY ENFORCED: Packet dropped -> {e}")
        
    # 5. Simulate Header Tampering (AAD Tampering)
    print("\n[!] ATTACK SIMULATION: Adversary captures a new packet and modifies the Message Type header...")
    sequence += 1
    new_packet = tx_engine.encrypt_packet(direction, sequence, msg_type, flight_cmd)
    
    tampered_packet = bytearray(new_packet)
    tampered_packet[13] = 99 # Modify Message Type from 2 to 99
    
    try:
        rx_engine.decrypt_packet(tampered_packet)
        print("    FAIL: Engine accepted tampered header!")
    except ValueError as e:
        print(f"    SECURITY ENFORCED: Packet dropped -> {e}")
        
    # 6. Simulate Out of Window (Too Old) Packet
    print("\n[!] ATTACK SIMULATION: Adversary injects an old packet outside the sliding window...")
    try:
        rx_engine.decrypt_packet(tx_engine.encrypt_packet(direction, sequence - 100, msg_type, b"SPOOF"))
        print("    FAIL: Engine accepted out-of-window packet!")
    except ValueError as e:
        print(f"    SECURITY ENFORCED: Packet dropped -> {e}")
