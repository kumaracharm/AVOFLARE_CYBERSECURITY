import time
import random
import os
import binascii
import json
import struct

# ANSI Color Codes
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'

def print_header(title):
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}{'='*60}")
    print(f" {title}")
    print(f"{'='*60}{Colors.RESET}\n")

def sim_delay(base_ms, jitter_ms=10):
    ms = base_ms + random.uniform(-jitter_ms, jitter_ms)
    time.sleep(ms / 1000.0)

def generate_hex(length):
    return binascii.hexlify(os.urandom(length)).decode('utf-8').upper()

def phase1_handshake():
    print_header("PHASE 1: Post-Quantum Hybrid Key Establishment")
    print(f"{Colors.CYAN}[UAV -> GCS] Initiating Hybrid Handshake (X25519 + ML-KEM-1024)...{Colors.RESET}")
    sim_delay(200, 20)
    
    x25519_pub = generate_hex(32)
    kem_pub = generate_hex(1184)[:64] + "..."
    print(f"  {Colors.YELLOW}[+] Ephemeral X25519 Public Key: {x25519_pub}{Colors.RESET}")
    print(f"  {Colors.YELLOW}[+] ML-KEM-1024 Encapsulation Key: {kem_pub}{Colors.RESET}")
    
    sim_delay(300, 50)
    print(f"\n{Colors.CYAN}[GCS -> UAV] Deriving Shared Secrets via HKDF-SHA-384...{Colors.RESET}")
    sim_delay(150, 10)
    
    session_key = generate_hex(32)
    print(f"  {Colors.GREEN}[+] SUCCESS: AES-256-GCM Session Key Derived{Colors.RESET}")
    print(f"  {Colors.BOLD}{Colors.GREEN}[MASTER KEY HEX] {session_key[:32]}...{session_key[32:]}{Colors.RESET}\n")

def phase2_telemetry():
    print_header("PHASE 2: Live Secure Telemetry & Hex Wire Framing")
    
    for i in range(3):
        # Generate fake telemetry
        seq = 1000 + i
        alt = 1500.5 + random.uniform(-2, 2)
        payload = json.dumps({"type": "IMU_GPS", "alt": round(alt,2), "obj_det": "CLEAR"}).encode()
        
        # Frame: Epoch(4B) | Dir(1B) | Seq(8B) | MsgType(1B)
        header = struct.pack(">I B Q B", 1337, 1, seq, 1)
        aad_hex = binascii.hexlify(header).decode('utf-8').upper()
        
        ciphertext = generate_hex(len(payload))
        tag = generate_hex(16)
        
        print(f"{Colors.CYAN}--- Packet Seq #{seq} ---{Colors.RESET}")
        print(f"  {Colors.YELLOW}[AAD HEADER]  {aad_hex}{Colors.RESET}")
        print(f"  {Colors.YELLOW}[CIPHERTEXT]  {ciphertext}{Colors.RESET}")
        print(f"  {Colors.YELLOW}[GCM TAG]     {tag}{Colors.RESET}")
        
        sim_delay(10, 2) # Simulate transmission
        latency_us = random.uniform(8.5, 14.2)
        
        print(f"  {Colors.GREEN}[DECRYPT OK]  {payload.decode('utf-8')}{Colors.RESET}")
        print(f"  {Colors.BOLD}{Colors.GREEN}[LATENCY]     Processing Time: {latency_us:.2f} µs{Colors.RESET}\n")
        time.sleep(0.5)

def phase3_attacks():
    print_header("PHASE 3: Adversarial Red-Team Attack Injections")
    
    # Attack A: Replay
    print(f"{Colors.CYAN}[*] INJECTING ATTACK A: Replay Attack (Re-transmitting Packet Seq #1001)...{Colors.RESET}")
    sim_delay(200)
    print(f"  {Colors.RED}[!] WARNING: Sequence 1001 falls within 64-bit sliding window mask!{Colors.RESET}")
    print(f"  {Colors.BOLD}{Colors.RED}[!] DROPPED: Duplicate packet detected. Discarding at hardware ingress.{Colors.RESET}\n")
    time.sleep(1)
    
    # Attack B: MITM
    print(f"{Colors.CYAN}[*] INJECTING ATTACK B: MITM Header Tampering (Modifying Message Type in AAD)...{Colors.RESET}")
    sim_delay(200)
    print(f"  {Colors.RED}[!] ERROR: AES-256-GCM Tag Verification Failed.{Colors.RESET}")
    print(f"  {Colors.BOLD}{Colors.RED}[!] DROPPED: Cryptographic integrity violated (AAD Tampered).{Colors.RESET}\n")
    time.sleep(1)
    
    # Attack C: AI Actuator Override
    print(f"{Colors.CYAN}[*] INJECTING ATTACK C: Malicious Edge AI attempting RAW_ACTUATOR_OVERRIDE (0xFF)...{Colors.RESET}")
    sim_delay(200)
    payload_str = '{"cmd": "RAW_ACTUATOR_OVERRIDE", "val": 0}'
    print(f"  {Colors.YELLOW}[CDSG INSPECTION] Analyzing decoded payload: {payload_str}{Colors.RESET}")
    print(f"  {Colors.RED}[CDSG DENY] Command strictly blocked across isolation boundary.{Colors.RESET}")
    print(f"  {Colors.BOLD}{Colors.RED}[!] DROPPED: Firewall rule triggered by Cross-Domain Security Gateway.{Colors.RESET}\n")
    time.sleep(1)
    
    # Attack D: RTOS Freeze
    print(f"{Colors.CYAN}[*] INJECTING ATTACK D: Kernel Panic / RTOS Task Lockup...{Colors.RESET}")
    print(f"  {Colors.YELLOW}[*] Halting telemetry heartbeat... waiting for watchdog...{Colors.RESET}")
    
    # Simulate a loop missing its heartbeat
    for ms in range(0, 130, 20):
        print(f"  {Colors.YELLOW}[WATCHDOG] Heartbeat missed... {ms}ms elapsed{Colors.RESET}")
        time.sleep(0.2)
        
    print(f"  {Colors.BOLD}{Colors.RED}\n[WATCHDOG CRITICAL] 120ms Threshold Exceeded! RTOS is unresponsive.{Colors.RESET}")
    print(f"  {Colors.BOLD}{Colors.RED}[EMERGENCY FAILSAFE] Engines Idled. Parachute Deployed. Secure Wiped.{Colors.RESET}")

def main():
    print(f"\n{Colors.BOLD}{Colors.CYAN}--- DRDO Tactical Simulation: UAV <-> GCS Secure Network ---{Colors.RESET}\n")
    time.sleep(1)
    
    phase1_handshake()
    time.sleep(1)
    
    phase2_telemetry()
    time.sleep(1)
    
    phase3_attacks()
    
    print_header("TACTICAL SIMULATION COMPLETE")

if __name__ == "__main__":
    main()
