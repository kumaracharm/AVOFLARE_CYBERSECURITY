# AVOFLARE v2.0 — Cryptographic & Platform Security Specification

## 1. Primary Authenticated Encryption: AES-256-GCM-SIV (RFC 8452)

### 1.1 Vulnerability of Standard AES-GCM in Avionics
Standard AES-GCM (NIST SP 800-38D) requires strictly unique (Key, Nonce) pairs. If a single nonce is reused under the same key:
$$\text{Keystream} = E_K(\text{Nonce}) \oplus \text{Plaintext}$$
An adversary XORs two ciphertexts with identical nonces to extract $\text{Plaintext}_1 \oplus \text{Plaintext}_2$. Furthermore, the authentication key $H = E_K(0^{128})$ is recoverable, allowing forgery of arbitrary valid tags (Joux's forbidden attack).

In airborne embedded systems, power brownouts, RTC battery failures, and multi-core thread preemption introduce high risks of nonce counter resets.

### 1.2 AES-256-GCM-SIV Construction & Nonce-Misuse Resilience
AVOFLARE mandates **AES-256-GCM-SIV (RFC 8452)** as the primary authenticated encryption mode. AES-GCM-SIV is synthetic initialization vector (SIV) based:

```
  Plaintext (P) + AAD ───> PolyVAL ───> AES-256 (K1) ───> Synthetic Nonce (SIV Tag)
                                                                 │
  SIV Tag ───────────────────────────────────────────────────────┴───> CTR Mode Encrypt (K2) ───> Ciphertext (C)
```

#### Key Derivation
The 512-bit input key $K$ is split into encryption key $K_1$ and authentication key $K_2$ using AES-256 in ECB mode over predefined counter blocks:
$$K_1 = \text{AES-256}_K(\text{0x00000004} \parallel \text{Nonce}[0..31])$$
$$K_2 = \text{AES-256}_K(\text{0x00000000} \parallel \text{Nonce}[0..31])$$

#### Synthetic IV Generation
A universal hash over AAD and Plaintext is computed using PolyVAL:
$$V = \text{PolyVAL}_{K_1}(\text{AAD} \parallel P)$$
$$\text{SIV} = \text{AES-256}_{K_2}(V \oplus \text{Nonce})$$

#### Security Guarantee
If a nonce is accidently reused $N$ times with AES-256-GCM-SIV:
1. **Authenticity remains unbroken**: The adversary cannot forge tags for new messages.
2. **Confidentiality degrades gracefully**: Identical plaintexts under the same nonce produce identical ciphertexts, revealing only message equivalence (a determinism leakage), but **no plaintext keystream is compromised**.

---

## 2. Hybrid Post-Quantum Key Establishment Protocol (HPKE RFC 9180)

### 2.1 Post-Quantum Migration Strategy
To protect against "Harvest Now, Decrypt Later" passive interception by quantum computers utilizing Shor's Algorithm, AVOFLARE implements a dual-layer hybrid Key Encapsulation Mechanism (KEM).

### 2.2 Protocol Construction: X25519 + ML-KEM-768 (FIPS 203)
The key exchange combines classical ECDH over Curve25519 with NIST FIPS 203 standardized **ML-KEM-768** (formerly Kyber-768, Module Lattice-based KEM, Security Category 3 / AES-192 equivalent).

```
  UAV (Initiator)                                                GCS (Responder)
  ───────────────                                                ───────────────
  Generate Ephemeral X25519 Pair (epk_u, esk_u)
  Generate Ephemeral ML-KEM-768 Pair (ekm_u, dsk_u)

  (epk_u || ekm_u) ───────────── Handshake Request ────────────>

                                                                 Compute X25519 SS_classical = ECDH(esk_g, epk_u)
                                                                 Encapsulate ML-KEM: (ciphertext_kem, SS_pqc) = Encaps(ekm_u)
                                                                 
                   <──────────── Handshake Response ──────────── (epk_g || ciphertext_kem)

  Compute X25519 SS_classical = ECDH(esk_u, epk_g)
  Decapsulate ML-KEM: SS_pqc = Decaps(dsk_u, ciphertext_kem)

  Combined Shared Secret: SS_master = HKDF-SHA384(SS_classical || SS_pqc)
```

### 2.3 Key Derivation via HKDF-SHA384 (RFC 5869)
The combined master secret is derived via `HKDF-SHA384` to maintain alignment with the 256-bit cryptographic security strength:

$$\text{PRK} = \text{HKDF-Extract}(\text{salt}=\text{EpochID}, \text{IKM} = SS_{\text{classical}} \parallel SS_{\text{pqc}})$$
$$K_{\text{session}} = \text{HKDF-Expand}(\text{PRK}, \text{info} = \text{"AVOFLARE_MALE_UAV_SESSION_KEY"}, L = 32 \text{ bytes})$$

---

## 3. Firmware Dual-Signing Mechanism (Ed25519 + ML-DSA-44)

Firmware images and partition boot binaries are dual-signed using both classical Ed25519 (RFC 8032) and Post-Quantum **ML-DSA-44 (FIPS 204)** (Module Lattice-based Digital Signature Standard, Security Category 2 / AES-128 equivalent).

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ FIRMWARE IMAGE HEADER                                                   │
  ├─────────────────────────────────────────────────────────────────────────┤
  │ Magic Bytes: 0x41564F32 ("AVO2")                                        │
  │ Target Hardware Version / Subsystem ID                                  │
  │ OTP Anti-Rollback Minimum Counter Requirement                           │
  │ SHA-384 Image Payload Hash                                              │
  ├─────────────────────────────────────────────────────────────────────────┤
  │ Signature 1: Ed25519 Classical Signature (64 bytes)                     │
  ├─────────────────────────────────────────────────────────────────────────┤
  │ Signature 2: ML-DSA-44 Post-Quantum Signature (2,420 bytes)             │
  └─────────────────────────────────────────────────────────────────────────┘
```

### Verification Requirements
1. Bootloader reads target firmware header.
2. Both Signature 1 (`Ed25519`) AND Signature 2 (`ML-DSA-44`) MUST pass verification against hardware TPM 2.0 public key roots.
3. If either signature fails, partition load is aborted, NMI alert is raised, and backup factory image is loaded.

---

## 4. Everspin eMRAM Persistent Nonce Counter Integration

To eliminate dependence on battery-backed RAM or wear-prone Flash storage for nonce monotonic counters, AVOFLARE integrates an **Everspin EMR064A Magnetoresistive RAM (eMRAM)** module over SPI/QSPI.

```
  ┌───────────────────────┐   SPI Bus (35 ns Write)   ┌───────────────────────┐
  │ Avionics Processor    │ ────────────────────────> │ Everspin EMR064A      │
  │ Nonce Management Unit │ <──────────────────────── │ 64 KB Persistent MRAM │
  └───────────────────────┘                           └───────────────────────┘
```

### eMRAM Parameters & Characteristics
- **Write Endurance**: Unlimited ($>10^{16}$ cycles).
- **Write Latency**: 35 ns (no erase cycle required).
- **Data Retention**: $>20$ years at 85°C industrial temperature range.
- **Operation**: Monotonic counter block updated on every packet frame burst and committed to MRAM cell within $1 \ \mu\text{s}$. On system reboot, the counter is incremented by a safety gap of $+100,000$ to guarantee nonce monotonicity even under abrupt power loss.
