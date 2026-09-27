# AVOFLARE v3.5 — UAV GCS Security Stack Documentation

## 1. Overview
AVOFLARE v3.5 is a defense-grade cybersecurity engine and active opposition system designed for MALE UAVs (like the TAPAS-BH-201). It encompasses a real-time telemetry analytics platform, a Red-Team Hacker Console, an active counter-offensive engine, and a robust set of security mechanisms designed to secure the UAV and the Ground Control Station (GCS) communication link.

## 2. Architecture & Components
The stack is divided into various security domains and operational components:
- **Dashboard & Telemetry**: Split-screen C4I dashboard & Hacker Console running via a Python 20Hz simulation backend & REST HTTP API server (`avoflare_cyber_system.py`, `index.html`).
- **Secure Link Engine**: A defense-grade cryptographic communication link between the UAV and GCS (`secure_link_engine.py`).
- **Cross-Domain Gateway (CDSG)**: An isolation boundary between Untrusted AI Domains and the Trusted Flight Control Domain (`cross_domain_gateway.py`).
- **Hardware Integrations**: C implementations for secure boot and hardware watchdogs (`src/platform/boot.c`, `src/system/watchdog.c`).
- **Remote Access (Zero-Trust)**: Cloudflare Tunnel integrations (`tunnel_launcher.py`, `cloudflared_config.yml`) for global tactical access.

## 3. Techniques & Security Implementations

### 3.1. Cross-Domain Security Gateway (CDSG)
Located in `cross_domain_gateway.py`, the CDSG separates the complex but potentially vulnerable AI/ML mission computers (Domain A) from the highly trusted, hard real-time flight controller (Domain B). 

**Techniques Used:**
- **Command Whitelisting**: Only high-level navigational intents (e.g., `UPDATE_TARGET`, `SET_WAYPOINT`) are permitted to cross the boundary. Raw actuator overrides (e.g., direct PWM changes) are strictly blocked.
- **Flight Envelope Bounds (Schema Validation)**: Deep packet inspection validates that commands fall within physical limits (e.g., max altitude of 5,000m, max speed of 150m/s).
- **Rate Limiting State (DoS Protection)**: Limits incoming requests to a maximum threshold (e.g., 10 messages per second), dropping excess packets to prevent resource exhaustion and Real-Time Operating System (RTOS) flood attacks.

### 3.2. Hardware Watchdog
Implemented in Python within `cross_domain_gateway.py` and supported via C skeletons in `src/system/watchdog.c`.

**Techniques Used:**
- **Continuous Petting (Heartbeat)**: Requires the main flight control loop to pet the watchdog continuously (every tick). 
- **Failsafe Triggering**: If the watchdog isn't petted within a specified timeout (e.g., 1.5 seconds) due to an RTOS lockup, kernel panic, or DoS attack, it triggers a hardware-level failsafe (e.g., idling engines, deploying parachutes, locking the system).

### 3.3. Secure Link Engine
Located in `secure_link_engine.py`, this implements the cryptographic security for the UAV-GCS telemetry and command link.

**Techniques Used:**
- **AES-256-GCM Authenticated Encryption**: Employs a 32-byte key for symmetric encryption that provides both confidentiality and data authenticity.
- **Sliding-Window Anti-Replay Filter**: Employs a 64-packet bitmask sliding window to detect and drop duplicated, delayed, or actively replayed packets.
- **Monotonic Nonce Generation**: Generates 96-bit nonces using a combination of the current Epoch ID and a monotonic Sequence Number (8 bytes) to guarantee uniqueness. 
- **Wire Format Framing**: Employs structured packet headers containing Epoch ID (4 bytes), Direction (1 byte), Sequence (8 bytes), and Message Type (1 byte) serving as Additional Authenticated Data (AAD). This ensures header integrity.

### 3.4. Secure / Measured Boot
Skeletons in `src/platform/boot.c` detail the hardware root of trust initialization.

**Techniques Used:**
- **Signature Verification**: Verifying the bootloader and the OS image signatures before execution.
- **Hardware Anchors**: Extending Platform Configuration Registers (PCR) in a TPM/HSM and verifying eFuse anti-rollback counters to prevent downgrading to vulnerable firmware versions.

### 3.5. Zero-Trust Tunneling
Enabled via Cloudflare Tunnels (outlined in `README.md` and automated in `tunnel_launcher.py`).

**Techniques Used:**
- **Reverse Tunneling**: `cloudflared` sets up an encrypted outbound connection to Cloudflare's edge network, meaning no inbound ports need to be opened on the deployment firewall.
- **Global Public HTTPS**: Dynamically provisions secure subdomains (`.trycloudflare.com`) to allow authenticated operators access to the C4I dashboard over TLS without a VPN.

## 4. Operation & Deployment

- **Local Execution**: Start the server natively via `python avoflare_cyber_system.py` or `npm start` on `localhost:8080`.
- **Global Exposure**: Run `python tunnel_launcher.py` or `npm run tunnel` to execute the system and spawn the Cloudflare zero-trust ingress tunnel automatically, outputting a secure public URL.
- **Production Persistence**: Utilize `cloudflared_config.yml` with custom domains for persistent static access to the command structure.
