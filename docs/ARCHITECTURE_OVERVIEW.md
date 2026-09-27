# AVOFLARE v2.0 — System Architecture & Partitioning Specification

## 1. System Scope & Airworthiness Compliance Context

**AVOFLARE v2.0** is a cyber-physical security architecture designed for Medium-Altitude Long-Endurance (MALE) Unmanned Aerial Vehicles (UAVs) operating under DO-178C (Software Considerations in Airborne Systems and Equipment Certification) and DO-326A / ED-202A (Airworthiness Security Process Specification).

The core operational paradigm enforces **strict temporal and spatial partitioning** using an ARINC 653 compliant Real-Time Operating System (RTOS) hypervisor (e.g., PikeOS 5.1 or VxWorks 653). Cyber-security functions, machine learning inference, and telemetry processing are strictly isolated from flight-critical Flight Control Computer (FCC) partitions to guarantee that no security mechanism, AI anomaly detector, or communication fault can impair flight safety.

---

## 2. Seven-Layer Architectural Hierarchy

The AVOFLARE architecture is structured into seven deterministic execution layers:

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  LAYER 7: FLIGHT SAFETY POLICY & FLIGHT CONTROLLER                 │
  │           ARINC 653 Partition 6 — Highest Integrity (DO-178C DAL-A/B)│
  │           Flight Envelope Protection (FEP) | Hardware Watchdog MCU │
  └──────────────────────────────────▲──────────────────────────────────┘
                                     │ (Deterministic Command Path)
  ┌──────────────────────────────────┴──────────────────────────────────┐
  │  LAYER 6: COMMAND VALIDATOR                                         │
  │           ARINC 653 Partition 5 — High Integrity (DO-178C DAL-B)   │
  │           V-n Diagram Limits | Vlo/Vfe Envelope | Schema Validation │
  └──────────────────────────────────▲──────────────────────────────────┘
                                     │ (State Gated Commands)
  ┌──────────────────────────────────┴──────────────────────────────────┐
  │  LAYER 5: TYPED SECURITY EVIDENCE BUS (TSEB) & TRUST STATE ENGINE   │
  │           ARINC 653 Partition 4 — Medium Integrity (DO-178C DAL-C) │
  │           Rust no_std State Machine | Cross-Layer Evidence | TSE    │
  └──────────────▲───────────────────▲───────────────────▲──────────────┘
                 │                   │                   │
  ┌──────────────┴──────────┐ ┌──────┴──────────────┐ ┌──┴──────────────┐
  │ LAYER 4: SECURE RF COMMS│ │ LAYER 3: EDGE AI &  │ │ LAYER 2: SENSOR │
  │          GATEWAY        │ │          DIGITAL    │ │          HEALTH │
  │ Partition 3 (DAL-C)     │ │          TWIN       │ │          FUSION │
  │ AES-GCM-SIV / ML-KEM    │ │ Partition 2 (DAL-C) │ │ Partition 1     │
  └──────────────▲──────────┘ └──────▲──────────────┘ └──▲──────────────┘
                 │                   │                   │
  ┌──────────────┴───────────────────┴───────────────────┴──────────────┐
  │ LAYER 1: PLATFORM TRUST ANCHOR                                      │
  │          TPM 2.0 Hardware Root of Trust | Secure Boot | Anti-Rollback │
  └─────────────────────────────────────────────────────────────────────┘
```

### Layer Details

#### Layer 1: Platform Trust Anchor (Hardware Root of Trust)
- **Role**: Establishes immutable cryptographic trust at platform initialization.
- **Components**: Hardware TPM 2.0 (ISO/IEC 11889), One-Time Programmable (OTP) fuse banks for anti-rollback counters, hardware-enforced JTAG lifecycle state control.
- **Execution**: Measured boot sequence extending SHA-384 hashes into TPM Platform Configuration Registers (PCRs). Dual firmware signatures verified prior to partition execution.

#### Layer 2: Sensor Health & Fusion
- **Role**: Pre-processes raw avionics sensor telemetry and flags statistical anomalies.
- **Components**: Interacting Multiple Model (IMM) Kalman filter, CUSUM (Cumulative Sum) change-point detector, Mahalanobis distance gating across physically independent sensor pairs.
- **Inputs**: MEMS IMU, FOG/RLG reference, Pitot/Static air data, GNSS (Galileo OSNMA authenticated), Engine sensors.

#### Layer 3: Edge AI & Digital Twin Physics Oracle
- **Role**: Provides an un-spoofable physical ground-truth baseline independent of sensor feedback.
- **Components**: JSBSim 6-DOF aerodynamic physics engine running at 100 Hz, ONNX Runtime execution engine with Interval Bound Propagation (IBP) certified neural networks.
- **Constraint**: Twin inputs are strictly restricted to control surface actuator commands and pitot airspeed. Sensor fusion output is never recycled into the Digital Twin.

#### Layer 4: Secure RF Communications Gateway
- **Role**: Cryptographic protection of air-to-ground data links (C2 and telemetry).
- **Components**: AES-256-GCM-SIV (RFC 8452) nonce-misuse resistant AEAD, Hybrid X25519 + ML-KEM-768 (FIPS 203) key establishment, HKDF-SHA384 key derivation, 64-bit sliding window anti-replay filter, Everspin eMRAM persistent nonce counter.

#### Layer 5: Typed Security Evidence Bus (TSEB) & Trust State Engine (TSE)
- **Role**: Cross-layer evidence aggregation and system security state evaluation.
- **Components**: Shared memory evidence channels, deterministic Rust (`no_std`) finite state machine managing states: `{TRUSTED, DEGRADED, RESTRICTED, SAFE_STATE}`.

#### Layer 6: Command Validator
- **Role**: Deterministic safety gate for all incoming C2 commands prior to execution.
- **Components**: Whitelist command parser, V-n aerodynamic load envelope validator, airspeed limit checks ($V_{lo}, V_{fe}$), state-dependent command authority gate.

#### Layer 7: Flight Safety Policy & Flight Controller
- **Role**: Core flight execution and airframe envelope protection.
- **Components**: DO-178C DAL-A/B certified flight control algorithms, independent hardware watchdog safety MCU (STM32H7 / Cortex-R5F), automatic autonomous return-to-base (RTB) failsafe triggers.

---

## 3. ARINC 653 Partition Isolation & Spatial/Temporal Guardrails

To meet DO-178C DAL-B airworthiness standards, AVOFLARE enforces complete spatial and temporal isolation between partitions:

| Partition ID | Module Name | Memory Allocation | Execution Budget (per 100ms major frame) | DO-178C DAL |
| :--- | :--- | :--- | :--- | :--- |
| **Partition 1** | Platform Trust & Sensor Health | 64 MB SRAM (ECC) | 15.0 ms | DAL-B |
| **Partition 2** | Digital Twin & AI Inference | 256 MB DDR4 (ECC) | 35.0 ms | DAL-C |
| **Partition 3** | Secure RF Comms Gateway | 128 MB DDR4 (ECC) | 20.0 ms | DAL-C |
| **Partition 4** | TSEB & Trust State Engine | 32 MB SRAM (ECC) | 5.0 ms | DAL-B |
| **Partition 5** | Command Validator | 32 MB SRAM (ECC) | 5.0 ms | DAL-B |
| **Partition 6** | Flight Controller & FEP | 64 MB SRAM (ECC) | 20.0 ms | DAL-A/B |

### Spatial Isolation Rules
1. **Memory Protection Unit (MPU) / IOMMU Configuration**: Configured during initial RTOS bootloader phase. No partition can read or write to another partition's address space.
2. **Direct Memory Access (DMA) Guarding**: Hardware DMA engines (e.g., NPU, FPGA, Ethernet MAC) are bound by Arm SMMUv3 / PCIe Access Control Services (ACS). DMA transfers outside assigned partition physical memory trigger immediate hardware NMI and hypervisor reboot.

### Temporal Isolation Rules
1. **Deterministic Cyclic Scheduling**: Major frame set to 100 ms (10 Hz master tick). Each partition receives a fixed, non-preemptable CPU time budget.
2. **Unused Budget Reclaiming**: Unused time in AI or RF partitions is idle-looped; it is never dynamically allocated to other tasks, maintaining strict worst-case execution time (WCET) determinism.

---

## 4. Deterministic Guardrails vs. Non-Deterministic AI

A fundamental design rule of AVOFLARE is that **no AI/ML system is ever given command authority over flight control surfaces or engine throttles**.

```
┌─────────────────────────┐
│ AI Anomaly Detector     │ ──(Anomaly Score)──┐
│ (ONNX IBP Model)        │                    │
└─────────────────────────┘                    ▼
                                     ┌──────────────────┐       ┌────────────────────┐
                                     │ Trust State      │ ────> │ Command Validator  │
                                     │ Engine (TSE)     │       │ (Deterministic)    │
                                     └──────────────────┘       └─────────┬──────────┘
┌─────────────────────────┐                    ▲                          │ Validated Cmd
│ Digital Twin Oracle     │ ──(State Residual)─┘                          ▼
│ (JSBSim 6-DOF Engine)   │                                     ┌────────────────────┐
└─────────────────────────┘                                     │ Flight Controller  │
                                                                │ & FEP (DAL-A/B)    │
                                                                └────────────────────┘
```

1. **AI Output Scope**: ONNX AI outputs are treated purely as *untrusted diagnostic evidence* fed into the Layer 5 Typed Security Evidence Bus.
2. **Deterministic Command Gate**: The Layer 6 Command Validator and Layer 7 Flight Envelope Protection are written in static C99 / Rust `no_std` with 100% path coverage and zero non-deterministic constructs.
3. **Safety Fallback**: If the AI model exhibits classification drift, high inference latency, or partition timeout, the TSE transitions to `DEGRADED` or `RESTRICTED` mode, bypassing AI evidence inputs entirely and falling back to classical IMM-EKF and deterministic Digital Twin state estimation.
