#include "uav_sec/uav_sec.h"

// Skeleton for HSM Interface
int uav_sec_hsm_get_key(uint32_t key_id, uint8_t* key_out, size_t max_len) {
    // In a real system, keys never leave the HSM. This might be used
    // for retrieving public keys or wrapped keys. Operations would
    // instead be pushed down to the HSM (e.g. uav_sec_hsm_encrypt()).
    
    if (max_len < 32) return -1;
    
    // Stub
    for(int i = 0; i < 32; i++) {
        key_out[i] = 0xAA;
    }
    return 0;
}
