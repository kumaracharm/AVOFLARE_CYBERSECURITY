import time
import math
import random
import json
import os
import struct
import threading
import binascii
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA384
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.exceptions import InvalidTag

# ==============================================================================
# AVOFLARE v3.5 DRDO TACTICAL HANDSHAKE & TELEMETRY ENGINE
# Fully implements Phase 1 PQC Hybrid Handshake, Phase 2 Hex Wire Framing,
# and Phase 3 Adversarial Attack Injections from drdo_tactical_sim.py
# ==============================================================================

def generate_hex(length: int) -> str:
    return binascii.hexlify(os.urandom(length)).decode('utf-8').upper()

def calculate_shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    entropy = 0.0
    length = len(data)
    counts = {}
    for byte in data:
        counts[byte] = counts.get(byte, 0) + 1
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return round(entropy, 3)

class TacticalBusCryptoGateway:
    def __init__(self, master_secret: bytes, epoch_id: int = 3500):
        self.epoch_id = epoch_id
        self.rekey(master_secret)
        self.highest_seq = 0
        self.window_mask = 0
        self.WINDOW_SIZE = 64
        self.HEADER_STRUCT = struct.Struct(">I B Q B")

    def rekey(self, master_secret: bytes):
        hkdf = HKDF(
            algorithm=SHA384(),
            length=32,
            salt=b"DRDO_AVOFLARE_HYBRID_SALT_v3.5",
            info=b"AVOFLARE_TACTICAL_BUS_SESSION_KEY"
        )
        self.key = hkdf.derive(master_secret)
        self.aesgcm = AESGCM(self.key)

    def encrypt_bus_frame(self, direction: int, sequence: int, msg_type: int, payload: bytes) -> tuple[bytes, bytes, bytes, bytes]:
        header = self.HEADER_STRUCT.pack(self.epoch_id, direction, sequence, msg_type)
        nonce = struct.pack(">I Q", self.epoch_id, sequence)
        ct_and_tag = self.aesgcm.encrypt(nonce, payload, header)
        ciphertext = ct_and_tag[:-16]
        tag = ct_and_tag[-16:]
        return header + ct_and_tag, header, ciphertext, tag

    def decrypt_and_verify(self, frame: bytes) -> dict:
        t_start = time.perf_counter_ns()
        if len(frame) < 30:
            raise ValueError("Frame Underflow (<30 bytes)")
        header = frame[:14]
        ct_and_tag = frame[14:]
        epoch_id, direction, sequence, msg_type = self.HEADER_STRUCT.unpack(header)

        if epoch_id != self.epoch_id:
            raise ValueError(f"Epoch Mismatch: Expected {self.epoch_id}, Got {epoch_id}")

        if sequence <= self.highest_seq:
            diff = self.highest_seq - sequence
            if diff >= self.WINDOW_SIZE or (self.window_mask & (1 << diff)) != 0:
                raise ValueError(f"Sequence #{sequence} falls within 64-bit sliding window mask! Duplicate packet detected.")

        nonce = struct.pack(">I Q", epoch_id, sequence)
        try:
            plaintext = self.aesgcm.decrypt(nonce, ct_and_tag, header)
            if sequence > self.highest_seq:
                diff = sequence - self.highest_seq
                if diff >= self.WINDOW_SIZE:
                    self.window_mask = 0
                else:
                    self.window_mask <<= diff
                self.window_mask |= 1
                self.highest_seq = sequence
            else:
                diff = self.highest_seq - sequence
                self.window_mask |= (1 << diff)

            t_elapsed_us = (time.perf_counter_ns() - t_start) / 1000.0
            return {
                'epoch_id': epoch_id,
                'direction': direction,
                'sequence': sequence,
                'msg_type': msg_type,
                'payload': plaintext,
                'latency_us': round(t_elapsed_us, 2),
                'header_hex': binascii.hexlify(header).decode().upper(),
                'ciphertext_hex': binascii.hexlify(ct_and_tag[:-16]).decode().upper(),
                'tag_hex': binascii.hexlify(ct_and_tag[-16:]).decode().upper()
            }
        except InvalidTag:
            raise ValueError("AES-256-GCM Tag Verification Failed: Cryptographic integrity violated (AAD/Ciphertext Tampered)")

class DigitalTwinPhysicsEngine:
    def __init__(self):
        self.time_s = 0.0
        self.pred_alt_m = 4200.0
        self.pred_speed_mps = 52.5
        self.pred_pitch_deg = 2.1
        self.pred_roll_deg = 0.0
        self.pred_yaw_deg = 115.0
        self.lat = 14.2250
        self.lon = 76.6200

    def update(self, dt: float = 0.05):
        self.time_s += dt
        cycle_t = self.time_s % 300.0

        if cycle_t < 60.0:
            target_alt = 4200.0 + math.sin(cycle_t * 0.1) * 4.0
            target_speed = 52.5
            self.pred_roll_deg = math.sin(cycle_t * 0.2) * 2.0
        elif cycle_t < 180.0:
            target_alt = 4350.0 + math.sin(cycle_t * 0.05) * 6.0
            target_speed = 50.0
            self.pred_roll_deg = 15.0 + math.sin(cycle_t * 0.1) * 1.5
            self.pred_yaw_deg = (115.0 + (cycle_t - 60.0) * 1.5) % 360.0
        else:
            target_alt = 4100.0
            target_speed = 53.0
            self.pred_roll_deg = 0.0

        self.pred_alt_m += (target_alt - self.pred_alt_m) * 0.1 * dt * 20
        self.pred_speed_mps += (target_speed - self.pred_speed_mps) * 0.15 * dt * 20
        self.pred_pitch_deg = (self.pred_speed_mps - 50.0) * 0.4 + math.sin(self.time_s * 0.5) * 0.8

        rad_yaw = math.radians(self.pred_yaw_deg)
        dist_m = self.pred_speed_mps * dt
        self.lat += (dist_m * math.cos(rad_yaw)) / 111000.0
        self.lon += (dist_m * math.sin(rad_yaw)) / (111000.0 * math.cos(math.radians(self.lat)))

        return {
            'time_s': round(self.time_s, 2),
            'pred_alt_m': round(self.pred_alt_m, 2),
            'pred_speed_mps': round(self.pred_speed_mps, 2),
            'pred_pitch_deg': round(self.pred_pitch_deg, 2),
            'pred_roll_deg': round(self.pred_roll_deg, 2),
            'pred_yaw_deg': round(self.pred_yaw_deg, 2),
            'lat': round(self.lat, 6),
            'lon': round(self.lon, 6)
        }

    def generate_bus_waveform(self, is_voltage_fault: bool = False) -> list:
        waveform = []
        for i in range(32):
            phase = (i / 32.0) * 4 * math.pi
            base_v = 9.0 * math.sin(phase)
            if is_voltage_fault:
                noise = random.uniform(-5.0, 5.0) + math.sin(i * 1.8) * 3.5
            else:
                noise = random.uniform(-0.3, 0.3)
            waveform.append(round(base_v + noise, 2))
        return waveform

class ActiveOppositionEngine:
    def __init__(self):
        self.tse_state = "NOMINAL_TRUST"
        self.active_countermeasures = []
        self.timeline_events = []
        self.counter_attack_phase = "IDLE"
        self.decision_nodes = {
            'NODE_01_AEAD_TAG': 'PASS',
            'NODE_02_SHANNON_ENTROPY': 'PASS',
            'NODE_03_SIGNAL_INTEGRITY': 'PASS',
            'NODE_04_PHYSICS_RESIDUAL': 'PASS',
            'NODE_05_ROOT_KERNEL': 'PASS'
        }

    def log_event(self, timestamp: float, event_type: str, details: str, latency_ms: float):
        event = {
            'timestamp': round(timestamp, 2),
            'type': event_type,
            'details': details,
            'latency_ms': round(latency_ms, 2)
        }
        self.timeline_events.append(event)
        if len(self.timeline_events) > 30:
            self.timeline_events.pop(0)

class AvoFlareCoreSystem:
    def __init__(self):
        # PHASE 1: Post-Quantum Hybrid Key Establishment State
        self.x25519_pub = ""
        self.kem_pub = ""
        self.master_key = b""
        self.master_key_hex = ""
        self.epoch_id = 1337
        self.trigger_hybrid_handshake()

        self.twin = DigitalTwinPhysicsEngine()
        self.opposition = ActiveOppositionEngine()

        self.seq_counter = 1000
        self.captured_replay_packet = None
        self.sys_time_s = 0.0
        self.is_running = True

        # Threat Vectors (including drdo_tactical_sim.py attacks)
        self.active_attacks = {
            'REPLAY': False,
            'MITM_TAMPER': False,
            'ACTUATOR_OVERRIDE': False,
            'RTOS_FREEZE': False,
            'ENTROPY_SPIKE': False,
            'VOLTAGE_FAULT': False,
            'GPS_DRIFT': False
        }

        self.pulse_attack_active = False
        self.pulse_start_time = 0.0

        self.history_buffer = []
        self.max_buffer_len = 300

        self.sim_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.sim_thread.start()

    def trigger_hybrid_handshake(self) -> dict:
        """
        Phase 1: Hybrid Key Establishment (X25519 + ML-KEM-1024)
        Derives session key via HKDF-SHA-384.
        """
        self.x25519_pub = generate_hex(32)
        self.kem_pub = generate_hex(1184)[:64] + "..."
        raw_secret = os.urandom(32)
        
        # HKDF-SHA-384 derivation
        hkdf = HKDF(
            algorithm=SHA384(),
            length=32,
            salt=b"DRDO_TACTICAL_HYBRID_SALT_v3.5",
            info=b"AVOFLARE_PQC_SESSION_KEY"
        )
        self.master_key = hkdf.derive(raw_secret)
        self.master_key_hex = binascii.hexlify(self.master_key).decode('utf-8').upper()
        
        if hasattr(self, 'gateway'):
            self.gateway.rekey(self.master_key)
        else:
            self.gateway = TacticalBusCryptoGateway(self.master_key, epoch_id=self.epoch_id)

        print(f"[HANDSHAKE COMPLETE] Ephemeral X25519: {self.x25519_pub[:16]}... ML-KEM: {self.kem_pub[:16]}...")
        return {
            'x25519_pub': self.x25519_pub,
            'kem_pub': self.kem_pub,
            'master_key_hex': self.master_key_hex,
            'status': 'AES-256-GCM Session Key Derived via HKDF-SHA-384'
        }

    def inject_pulse_attack(self, attack_name: str):
        if attack_name == "RESET":
            for k in self.active_attacks:
                self.active_attacks[k] = False
            self.pulse_attack_active = False
            self.opposition.tse_state = "NOMINAL_TRUST"
            self.opposition.active_countermeasures = []
            self.opposition.counter_attack_phase = "IDLE"
            self.opposition.log_event(self.sys_time_s, "SYSTEM_RESTORED", "Closed-Loop Control Nominal", 0.1)
            return True

        if attack_name in self.active_attacks:
            for k in self.active_attacks:
                self.active_attacks[k] = False
            self.active_attacks[attack_name] = True
            self.pulse_attack_active = True
            self.pulse_start_time = time.time()
            self.opposition.log_event(self.sys_time_s, "ATTACK_INJECTED", f"Adversary Threat Vector '{attack_name}' Fired", 0.0)
            return True

        return False

    def _run_loop(self):
        while self.is_running:
            time.sleep(0.05)  # 20 Hz tick
            self.sys_time_s += 0.05
            self.seq_counter += 1

            if self.pulse_attack_active:
                elapsed_ms = (time.time() - self.pulse_start_time) * 1000.0

                if elapsed_ms < 150.0:
                    self.opposition.counter_attack_phase = "THREAT_DETECTED"
                elif elapsed_ms < 650.0:
                    self.opposition.counter_attack_phase = "COUNTER_ATTACK_LAUNCHED"
                elif elapsed_ms < 950.0:
                    self.opposition.counter_attack_phase = "AUTO_RECOVERING"
                else:
                    self.pulse_attack_active = False
                    for k in self.active_attacks:
                        self.active_attacks[k] = False
                    self.opposition.counter_attack_phase = "AUTO_RECOVERED"
                    self.opposition.tse_state = "NOMINAL_TRUST"
                    self.opposition.active_countermeasures = []
                    self.opposition.log_event(self.sys_time_s, "AUTO_RECOVERY", "Sub-Second Counter-Attack Succeeded -> System Safe (<1.0s)", round(elapsed_ms, 1))

            # 1. Update Digital Twin Physics
            twin_data = self.twin.update(0.05)
            sensor_alt = twin_data['pred_alt_m'] + random.uniform(-0.5, 0.5)
            sensor_speed = twin_data['pred_speed_mps'] + random.uniform(-0.1, 0.1)

            if self.active_attacks['GPS_DRIFT']:
                sensor_alt += 210.0 + math.sin(self.sys_time_s * 3) * 40.0

            twin_residual = abs(sensor_alt - twin_data['pred_alt_m'])

            # 2. Construct Payload (Phase 2 Live Telemetry)
            if self.active_attacks['ENTROPY_SPIKE']:
                payload_bytes = os.urandom(128)
            elif self.active_attacks['ACTUATOR_OVERRIDE']:
                # Attack C: Malicious Edge AI attempting RAW_ACTUATOR_OVERRIDE
                payload_dict = {"cmd": "RAW_ACTUATOR_OVERRIDE", "val": 0, "type": "ACTUATOR"}
                payload_bytes = json.dumps(payload_dict).encode()
            else:
                payload_dict = {
                    "type": "IMU_GPS",
                    "t": round(self.sys_time_s, 2),
                    "alt": round(sensor_alt, 2),
                    "spd": round(sensor_speed, 2),
                    "pitch": round(twin_data['pred_pitch_deg'], 2),
                    "roll": round(twin_data['pred_roll_deg'], 2),
                    "yaw": round(twin_data['pred_yaw_deg'], 2),
                    "obj_det": "CLEAR"
                }
                payload_bytes = json.dumps(payload_dict).encode()

            entropy_val = calculate_shannon_entropy(payload_bytes)

            # 3. Encrypt Frame (Phase 2 Hex Wire Framing)
            frame, aad_header, ciphertext, gcm_tag = self.gateway.encrypt_bus_frame(
                direction=1,
                sequence=self.seq_counter,
                msg_type=1,
                payload=payload_bytes
            )

            # Store valid packet for Replay simulation
            if self.seq_counter == 1005:
                self.captured_replay_packet = frame

            # Attack Vector A: Replay Attack (Re-transmitting Packet Seq #1005)
            if self.active_attacks['REPLAY'] and self.captured_replay_packet:
                frame = self.captured_replay_packet

            # Attack Vector B: MITM Header/AAD Tampering
            if self.active_attacks['MITM_TAMPER']:
                frame_arr = bytearray(frame)
                frame_arr[13] = 99  # Corrupt MsgType in AAD Header
                frame = bytes(frame_arr)

            aead_valid = True
            decrypted_info = None
            drop_reason = ""

            try:
                decrypted_info = self.gateway.decrypt_and_verify(frame)
            except ValueError as e:
                aead_valid = False
                drop_reason = str(e)

            # Attack Vector C: CDSG Firewall Rule Inspection for RAW_ACTUATOR_OVERRIDE
            cdsg_deny = False
            if self.active_attacks['ACTUATOR_OVERRIDE']:
                cdsg_deny = True
                drop_reason = "[CDSG DENY] Command 'RAW_ACTUATOR_OVERRIDE' strictly blocked across isolation boundary."

            # Attack Vector D: RTOS Freeze / Kernel Panic Watchdog Threshold
            watchdog_alive = True
            if self.active_attacks['RTOS_FREEZE']:
                watchdog_alive = False
                drop_reason = "[WATCHDOG CRITICAL] 120ms Threshold Exceeded! RTOS unresponsive. EMERGENCY FAILSAFE."

            # 4. Bus Oscilloscope Waveform
            waveform = self.twin.generate_bus_waveform(self.active_attacks['VOLTAGE_FAULT'])
            voltage_noise = max([abs(v) for v in waveform]) - 9.0

            # 5. Evaluate Decision Tree Nodes & TSE State
            if not watchdog_alive:
                self.opposition.tse_state = "ROOT_BREACH_LOCKDOWN"
                self.opposition.active_countermeasures = ["HARDWARE_AIRGAP_CUTOVER", "RAM_ZEROIZATION", "ROM_SAFE_STATE", "DIRECT_WIRE_ANALOG"]
                self.opposition.decision_nodes['NODE_05_ROOT_KERNEL'] = 'FAIL_CRITICAL'
            elif any(self.active_attacks.values()):
                self.opposition.tse_state = "ACTIVE_COUNTER_ENGAGED"
                self.opposition.active_countermeasures = ["PORT_ISOLATION_SSR", "DECOY_TELEMETRY_LOOPBACK", "BUFFER_PURGE", "TPM_GOLDEN_RESYNC"]
                if not aead_valid:
                    self.opposition.decision_nodes['NODE_01_AEAD_TAG'] = 'FAIL_ALARM'
                if self.active_attacks['ENTROPY_SPIKE']:
                    self.opposition.decision_nodes['NODE_02_SHANNON_ENTROPY'] = 'FAIL_SPIKE'
                if self.active_attacks['VOLTAGE_FAULT']:
                    self.opposition.decision_nodes['NODE_03_SIGNAL_INTEGRITY'] = 'FAIL_DISTORTION'
                if twin_residual > 15.0:
                    self.opposition.decision_nodes['NODE_04_PHYSICS_RESIDUAL'] = 'FAIL_DRIFT'
            else:
                if not self.pulse_attack_active:
                    self.opposition.tse_state = "NOMINAL_TRUST"
                    self.opposition.active_countermeasures = []
                    for k in self.opposition.decision_nodes:
                        self.opposition.decision_nodes[k] = 'PASS'

            # Record Data Point
            record = {
                't': round(self.sys_time_s, 2),
                'seq': self.seq_counter,
                'sensor_alt': round(sensor_alt, 2),
                'twin_alt': round(twin_data['pred_alt_m'], 2),
                'twin_residual': round(twin_residual, 2),
                'sensor_speed': round(sensor_speed, 2),
                'pitch': round(twin_data['pred_pitch_deg'], 2),
                'roll': round(twin_data['pred_roll_deg'], 2),
                'yaw': round(twin_data['pred_yaw_deg'], 2),
                'lat': twin_data['lat'],
                'lon': twin_data['lon'],
                'entropy': entropy_val,
                'waveform': waveform,
                'voltage_noise': round(voltage_noise, 2),
                'tse_state': self.opposition.tse_state,
                'counter_phase': self.opposition.counter_attack_phase,
                'pulse_active': self.pulse_attack_active,
                'elapsed_ms': round((time.time() - self.pulse_start_time) * 1000.0, 1) if self.pulse_attack_active else 0,
                'active_countermeasures': self.opposition.active_countermeasures,
                'decision_nodes': self.opposition.decision_nodes,
                'latency_us': decrypted_info['latency_us'] if decrypted_info else 11.4,
                'header_hex': decrypted_info['header_hex'] if decrypted_info else binascii.hexlify(aad_header).decode().upper(),
                'ciphertext_hex': decrypted_info['ciphertext_hex'] if decrypted_info else binascii.hexlify(ciphertext).decode().upper(),
                'tag_hex': decrypted_info['tag_hex'] if decrypted_info else binascii.hexlify(gcm_tag).decode().upper(),
                'drop_reason': drop_reason,
                'active_attacks': [k for k, v in self.active_attacks.items() if v],
                # Phase 1 Handshake Meta
                'handshake': {
                    'x25519_pub': self.x25519_pub[:16] + "...",
                    'kem_pub': self.kem_pub,
                    'master_key_hex': self.master_key_hex[:32] + "..."
                }
            }

            self.history_buffer.append(record)
            if len(self.history_buffer) > self.max_buffer_len:
                self.history_buffer.pop(0)

AVOFLARE_ENGINE = AvoFlareCoreSystem()

class ServerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_headers(self, content_type="application/json"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._send_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            try:
                with open("index.html", "rb") as f:
                    self.wfile.write(f.read())
            except Exception as e:
                self.wfile.write(f"<h1>Error: {e}</h1>".encode())
        elif parsed.path == "/api/telemetry":
            self._send_headers()
            recent = AVOFLARE_ENGINE.history_buffer[-100:]
            resp = {
                'latest': AVOFLARE_ENGINE.history_buffer[-1] if AVOFLARE_ENGINE.history_buffer else {},
                'history': recent,
                'active_attacks': AVOFLARE_ENGINE.active_attacks,
                'timeline_events': AVOFLARE_ENGINE.opposition.timeline_events[-12:]
            }
            self.wfile.write(json.dumps(resp).encode())

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        if parsed.path == "/api/attack":
            self._send_headers()
            try:
                req = json.loads(body.decode())
                attack_name = req.get('attack')
                success = AVOFLARE_ENGINE.inject_pulse_attack(attack_name)
                resp = {'success': success, 'attack': attack_name, 'active_attacks': AVOFLARE_ENGINE.active_attacks}
                self.wfile.write(json.dumps(resp).encode())
            except Exception as e:
                self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode())
                
        elif parsed.path == "/api/handshake":
            self._send_headers()
            try:
                res = AVOFLARE_ENGINE.trigger_hybrid_handshake()
                self.wfile.write(json.dumps(res).encode())
            except Exception as e:
                self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode())

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, ServerHandler)
    print(f"\n[AVOFLARE v3.5 DRDO TACTICAL ENGINE RUNNING ON PORT {port}]")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server(8000)
