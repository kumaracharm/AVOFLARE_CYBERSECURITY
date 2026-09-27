#ifndef UAV_SEC_H
#define UAV_SEC_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

/**
 * Layer 1 & 4: Packet Structure & AEAD
 */
#pragma pack(push, 1)
typedef struct {
    uint32_t epoch_id;
    uint8_t  direction;
    uint64_t sequence;
    uint8_t  message_type;
} uav_sec_header_t;
#pragma pack(pop)

// Encryption/Decryption
int uav_sec_encrypt(const uav_sec_header_t* header, const uint8_t* plaintext, size_t pt_len, 
                    const uint8_t* key, const uint8_t* iv, uint8_t* ciphertext, uint8_t* tag);

int uav_sec_decrypt(const uav_sec_header_t* header, const uint8_t* ciphertext, size_t ct_len,
                    const uint8_t* key, const uint8_t* iv, const uint8_t* tag, uint8_t* plaintext);

/**
 * Layer 2: Key Establishment (PQC + ECDH)
 */
int uav_sec_handshake_init(uint8_t* pubkey_out, size_t* pubkey_len);
int uav_sec_handshake_derive(const uint8_t* shared_secret, size_t secret_len, 
                             uint8_t* tx_key, uint8_t* rx_key);

/**
 * Layer 3: Platform Security
 */
int uav_sec_boot_verify(void);
int uav_sec_hsm_get_key(uint32_t key_id, uint8_t* key_out, size_t max_len);

/**
 * Layer 4: Anti-Replay Sliding Window
 */
void uav_sec_replay_init(void);
bool uav_sec_replay_check_and_update(uint64_t sequence);

/**
 * Layer 5: System Isolation
 */
void uav_sec_watchdog_pet(void);
int uav_sec_cdsg_validate_transition(int source_domain, int dest_domain);

#endif // UAV_SEC_H
