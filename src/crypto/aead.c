#include "uav_sec/uav_sec.h"
#include <string.h>

// Skeleton for AES-256-GCM AEAD
int uav_sec_encrypt(const uav_sec_header_t* header, const uint8_t* plaintext, size_t pt_len, 
                    const uint8_t* key, const uint8_t* iv, uint8_t* ciphertext, uint8_t* tag) {
    // 1. Initialize AES-GCM context with key and iv
    // 2. Feed header as Associated Data (AAD)
    // 3. Encrypt plaintext -> ciphertext
    // 4. Generate authentication tag
    
    // Stub implementation: copy plaintext to ciphertext
    if (pt_len > 0) {
        memcpy(ciphertext, plaintext, pt_len);
    }
    // Stub tag
    memset(tag, 0xAA, 16);
    return 0; // Success
}

int uav_sec_decrypt(const uav_sec_header_t* header, const uint8_t* ciphertext, size_t ct_len,
                    const uint8_t* key, const uint8_t* iv, const uint8_t* tag, uint8_t* plaintext) {
    // 1. Initialize AES-GCM context with key and iv
    // 2. Feed header as Associated Data (AAD)
    // 3. Decrypt ciphertext -> plaintext
    // 4. Verify tag (constant time comparison)
    
    // Stub tag verification
    uint8_t expected_tag[16];
    memset(expected_tag, 0xAA, 16);
    if (memcmp(tag, expected_tag, 16) != 0) {
        return -1; // Authentication failed
    }

    // Stub implementation: copy ciphertext to plaintext
    if (ct_len > 0) {
        memcpy(plaintext, ciphertext, ct_len);
    }
    return 0; // Success
}
