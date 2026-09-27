# AVOFLARE v2.0 — Typed Security Evidence Bus (TSEB) & Trust State Engine (TSE) Specification

## 1. Typed Security Evidence Bus (TSEB) Architecture

The **Typed Security Evidence Bus (TSEB)** is the core cross-layer architectural innovation of AVOFLARE. Rather than passing scalar "trust scores" (which are semantically meaningless for DO-178C safety certification), security layers emit **typed, structured evidence frames** into an ARINC 653 shared memory partition accessible by the Trust State Engine (TSE).

```
 ┌────────────────────────┐
 │ Layer 1: TPM / Platform│ ───> { pcr_verified, signature_valid } ──────┐
 └────────────────────────┘                                               │
 ┌────────────────────────┐                                               │
 │ Layer 2: Sensor Health │ ───> { gnss_integrity, imu_consistency } ─────┤
 └────────────────────────┘                                               │  ARINC 653 Shared Memory
 ┌────────────────────────┐                                               ├──> [ Typed Security ]
 │ Layer 3: Digital Twin  │ ───> { twin_residual_m, ai_confidence } ──────┤    [ Evidence Bus   ]
 └────────────────────────┘                                               │
 ┌────────────────────────┐                                               │
 │ Layer 4: RF Comms Gate │ ───> { auth_valid, replay_clear, rate_ok } ───┘
 └────────────────────────┘                                               │
                                                                          ▼
                                                               ┌─────────────────────┐
                                                               │ Trust State Engine  │
                                                               │ (Rust no_std FSM)   │
                                                               └─────────────────────┘
```

---

## 2. Evidence Data Structures & Struct Specification

The evidence frame is defined as a static, fixed-size Rust data structure (no heap allocations, deterministic memory layout):

```rust
#[repr(C)]
#[derive(Copy, Clone, Debug)]
pub enum IntegrityStatus {
    Nominal = 0,
    Degraded = 1,
    Fault = 2,
    Compromised = 3,
}

#[repr(C)]
#[derive(Copy, Clone, Debug)]
pub struct TypedSecurityEvidence {
    pub timestamp_ms: u64,
    pub epoch_id: u32,
    
    // Layer 1 Platform Evidence
    pub platform_pcr_match: bool,
    pub firmware_sig_valid: bool,
    
    // Layer 2 Sensor Health Evidence
    pub gnss_integrity: IntegrityStatus,
    pub imu_consistency: IntegrityStatus,
    pub acoustic_injection_alarm: bool,
    
    // Layer 3 Digital Twin & AI Evidence
    pub twin_residual_m: f32,       // Observed Alt - Twin Alt (meters)
    pub twin_speed_residual_mps: f32, // Observed Speed - Twin Speed (m/s)
    pub ai_ensemble_disagreement: bool,
    
    // Layer 4 RF Comms Evidence
    pub comms_auth_valid: bool,
    pub comms_replay_clear: bool,
    pub comms_rate_surge: bool,
    pub mil1553_hmac_valid: bool,
}
```

---

## 3. Trust State Engine (TSE) Finite State Machine (FSM)

The TSE evaluates evidence frames at 10 Hz and maintains a deterministic finite state machine written in Rust `no_std`.

### 3.1 Operating Modes
1. **`TRUSTED`**: All security and physics evidence nominal. Full ground command authority enabled.
2. **`DEGRADED`**: Minor sensor noise or single link anomaly. Non-critical commands enabled; pilot alerted.
3. **`RESTRICTED`**: Cryptographic tamper, correlated GPS spoofing, or twin residual breach ($>15\text{ m}$). Non-safety commands blocked; automated loiter/hold active.
4. **`SAFE_STATE`**: Platform integrity compromise or watchdog timeout. Emergency failsafe: autonomous return-to-base (RTB) or parachute deployment.

```
                  ┌──────────────────────────────────────────────┐
                  │                  TRUSTED                     │
                  └──────┬───────────────────────────────▲───────┘
                         │                               │
       (Minor Noise /    │                               │ (Evidence Re-Nominalized)
       Single Link Anom) │                               │
                         ▼                               │
                  ┌───────────────┐              ┌───────┴───────┐
                  │   DEGRADED    │              │  RESTRICTED   │
                  └──────┬────────┘              └───────▲───────┘
                         │                               │
                         │ (Residual > 15m / Auth Fail)  │
                         └───────────────────────────────┘
                                         │
                                         │ (Platform Compromise / Watchdog Timeout)
                                         ▼
                                  ┌───────────────┐
                                  │  SAFE_STATE   │
                                  └───────────────┘
```

### 3.2 FSM Rule Evaluation Implementation

```rust
#![no_std]

pub enum SystemTrustState {
    Trusted = 0,
    Degraded = 1,
    Restricted = 2,
    SafeState = 3,
}

pub struct TrustStateEngine {
    current_state: SystemTrustState,
    anomaly_counter: u32,
}

impl TrustStateEngine {
    pub const fn new() -> Self {
        Self {
            current_state: SystemTrustState::Trusted,
            anomaly_counter: 0,
        }
    }

    pub fn evaluate_frame(&mut self, evidence: &TypedSecurityEvidence) -> SystemTrustState {
        // Rule 1: Platform Compromise -> Immediate SAFE_STATE
        if !evidence.platform_pcr_match || !evidence.firmware_sig_valid {
            self.current_state = SystemTrustState::SafeState;
            return SystemTrustState::SafeState;
        }

        // Rule 2: Comms Cryptographic Attack / MIL-1553 HMAC Failure -> RESTRICTED
        if !evidence.comms_auth_valid || !evidence.comms_replay_clear || !evidence.mil1553_hmac_valid {
            self.current_state = SystemTrustState::Restricted;
            return SystemTrustState::Restricted;
        }

        // Rule 3: Digital Twin Residual Breach (Correlated GPS/IMU Spoofing)
        if evidence.twin_residual_m > 50.0 {
            self.current_state = SystemTrustState::Restricted;
            return SystemTrustState::Restricted;
        } else if evidence.twin_residual_m > 15.0 {
            self.current_state = SystemTrustState::Degraded;
            return SystemTrustState::Degraded;
        }

        // Rule 4: Sensor Health / Rate Surge Anomalies
        if matches!(evidence.gnss_integrity, IntegrityStatus::Fault) || evidence.comms_rate_surge {
            self.current_state = SystemTrustState::Degraded;
            return SystemTrustState::Degraded;
        }

        // Nominal Execution
        self.current_state = SystemTrustState::Trusted;
        SystemTrustState::Trusted
    }
}
```

---

## 4. JSBSim 6-DOF Digital Twin Oracle Implementation

### 4.1 Un-Spoofable Ground-Truth Principle
Sensors can be spoofed; physical aerodynamic laws cannot. The **Digital Twin Oracle** runs a 100 Hz 6-DOF rigid-body aerodynamic model using the JSBSim flight dynamics framework.

To prevent circularly trusting spoofed sensor data, **inputs to the Digital Twin are strictly limited to**:
1. Actuator position commands (Elevator, Aileron, Rudder, Engine Throttle).
2. Direct pitot-static pressure (Airspeed $V_{ias}$, Altitude $H_{\text{baro}}$).
3. Airframe aerodynamic coefficient tables ($C_L, C_D, C_m$).

**GNSS position, GNSS velocity, and IMU inputs are explicitly excluded.**

```
  Control Commands (Elevator, Throttle) ──┐
                                           ├──> [ JSBSim 100 Hz 6-DOF Engine ] ──> Expected Altitude / Speed
  Pitot Static Pressure (Airspeed) ───────┘
```

### 4.2 Residual Calculation
The twin residual $\Delta\text{Residual}$ is computed against fused sensor observations:
$$\Delta\text{Residual}_{\text{alt}} = | H_{\text{sensor\_fused}} - H_{\text{twin\_predicted}} |$$

If an adversary spoofs GNSS position to induce a fake altitude drift, the Digital Twin physics engine continues predicting the true trajectory based on actuator inputs. The resulting residual $\Delta\text{Residual}_{\text{alt}} > 15\text{ m}$ triggers the TSE to transition to `RESTRICTED` state, flagging the spoofing attack instantly.
