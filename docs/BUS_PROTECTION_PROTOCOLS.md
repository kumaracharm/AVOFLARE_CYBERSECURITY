# AVOFLARE v2.0 — Avionics Bus Protection Protocols

## 1. Avionics Bus Security Hierarchy

MALE UAV platforms utilize a multi-tier bus hierarchy to separate flight-critical actuation from sensor acquisition and auxiliary systems:

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ MIL-STD-1553B — FLIGHT-CRITICAL BUS (Flight Control, Actuation, Weapons)│
  │ High-Priority | 1 Mbps | Dual-Redundant | Bus Controller (BC) Auth     │
  └─────────────────────────────────────────────────────────────────────────┘
                                       │
  ┌────────────────────────────────────┴────────────────────────────────────┐
  │ ARINC 429 — SENSOR DATA BUS (Air Data, INS, Gyro, Baro)                 │
  │ Point-to-Point | Unidirectional | Receiver Gateway Hash Validation      │
  └────────────────────────────────────┬────────────────────────────────────┘
                                       │
  ┌────────────────────────────────────┴────────────────────────────────────┐
  │ CAN-FD — AUXILIARY SYSTEM BUS (Payload, Thermal, Engine, ECS)           │
  │ Multi-Master | 5 Mbps | AUTOSAR SecOC with 64-Bit CMAC                  │
  └─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. MIL-STD-1553B Authentication Protocol (HMAC-SHA256/64)

### 2.1 Problem Definition
MIL-STD-1553B was specified in 1975 with no cryptographic layer. Any compromised Remote Terminal (RT) or tapped wire can inject command words or spoof data words.

### 2.2 Protocol Specification
AVOFLARE introduces a backwards-compatible message authentication protocol for critical 1553 command/data sequences:

```
  1553 Message Frame Structure (Command Word + 32 Data Words Max):
  
  [Command Word] [Data Word 1] [Data Word 2] ... [Data Word 28] [Auth Word 29] [Auth Word 30] [Auth Word 31] [Auth Word 32]
  └─────────────────────────────── Payload Data ──────────────┘ └────────── 64-Bit HMAC-SHA256 Truncated ─────────┘
```

#### Message Tagging Logic
1. **Freshness Value**: 16-bit monotonic sequence counter appended to message payload.
2. **HMAC Calculation**:
$$\text{HMAC}_{\text{full}} = \text{HMAC-SHA256}(K_{\text{bus}}, \text{CommandWord} \parallel \text{Payload} \parallel \text{Freshness})$$
3. **Truncation**:
$$\text{Tag}_{64} = \text{HMAC}_{\text{full}}[0..63]$$
4. **Encoding into 1553 Words**: The 64-bit tag is split across the final 4 16-bit 1553 data words (Words 29, 30, 31, 32).

#### Bus Controller (BC) Enforcement Rules
- The Bus Controller maintains an RT message permission matrix.
- If an RT responds with an invalid 64-bit HMAC tag, the BC flags the RT as compromised, disables its polling slot, and switches communication to the secondary redundant Bus B line.

---

## 3. CAN-FD AUTOSAR SecOC (64-Bit CMAC Minimum)

### 3.1 Purging 32-Bit CMAC Truncation
Legacy SecOC configurations truncated AES-CMAC to 32 bits ($2^{32} \approx 4.29 \times 10^9$ possibilities). In high-speed CAN-FD networks (5 Mbps), an attacker can forge a valid tag within hours via brute-force frame injection.

**AVOFLARE explicitly mandates a strict 64-bit CMAC minimum** for all CAN-FD frames.

```
  CAN-FD Frame Layout (64 Bytes Data Field):
  
  ┌────────────────────────┬───────────────────┬────────────────────────────┐
  │ User Payload Data      │ Freshness Counter │ Truncated AES-CMAC Tag     │
  │ (52 Bytes)             │ (4 Bytes)         │ (8 Bytes / 64 Bits)        │
  └────────────────────────┴───────────────────┴────────────────────────────┘
```

### 3.2 SecOC Freshness & Verification Pipeline
1. **Freshness Value Management (FVM)**:
   - 32-bit total freshness counter split into:
     - Upper 24 bits: Master Freshness Counter (broadcast periodically by Gateway).
     - Lower 8 bits: Frame-local trip counter.
2. **CMAC Generation**:
$$\text{CMAC}_{\text{full}} = \text{AES-CMAC-128}(K_{\text{SecOC}}, \text{CAN\_ID} \parallel \text{Data} \parallel \text{Freshness}_{\text{full}})$$
$$\text{Tag}_{64} = \text{CMAC}_{\text{full}}[0..63]$$
3. **Receiver Verification**:
   - The ECU reconstitutes the full 32-bit freshness value.
   - If tag check passes and freshness is strictly greater than the last stored value, the message is accepted. Otherwise, it is dropped and logged.

---

## 4. ARINC 429 Sensor Data Validation Logic

### 4.1 Bus Nature & Physical Security
ARINC 429 is a unidirectional, single-transmitter, multi-receiver point-to-point bus. Because it is physically impossible for a receiver node to transmit backwards on an ARINC 429 pair, bus injection attacks require physical wire splicing or sensor node compromise.

### 4.2 Receiver Gateway Hash & Parity Validation
Receiver nodes implement a multi-stage validation gate:

```
  ARINC 429 32-Bit Word:
  
  ┌─────────┬───────────────┬─────────────────────────────────┬───────┬─────────┐
  │ Bit 32  │ Bits 31..30   │ Bits 29..11                     │ B9..10│ Bits 8..1│
  │ Parity  │ SSM (Status)  │ Data Field (BNR / BCD)          │ SDI   │ Label   │
  └─────────┴───────────────┴─────────────────────────────────┴───────┴─────────┘
```

#### Validation Steps
1. **Odd Parity Verification**: Bit 32 checked against hardware line receiver parity bit.
2. **SSM (Sign/Status Matrix) Gate**: Verify status flags represent Normal Operation (`00` or `11`). Reject Failure Warning (`01`) or No Computed Data (`10`).
3. **Plausibility & Rate-of-Change Limit Filter**:
   - Airspeed rate-of-change limit: $|\frac{d V_{ias}}{dt}| \le 25 \text{ m/s}^2$.
   - Altitude rate-of-change limit: $|\frac{d H}{dt}| \le 50 \text{ m/s}$.
   - If consecutive words exceed dynamic physical limits, the channel is flagged as degraded and submitted to the Layer 2 IMM-EKF filter.
