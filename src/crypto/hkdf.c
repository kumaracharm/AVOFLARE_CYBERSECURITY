#include "uav_sec/uav_sec.h"

// Skeleton for HKDF-SHA-384
int uav_sec_handshake_derive(const uint8_t* shared_secret, size_t secret_len, 
                             uint8_t* tx_key, uint8_t* rx_key) {
    // 1. HKDF-Extract using a static salt or previous epoch material
    // 2. HKDF-Expand to derive TX key (e.g. info="UAV_TX")
    // 3. HKDF-Expand to derive RX key (e.g. info="UAV_RX")
    
    // Stub implementation
    for(int i = 0; i < 32; i++) {
        tx_key[i] = 0x01;
        rx_key[i] = 0x02;
    }
    return 0;
}
