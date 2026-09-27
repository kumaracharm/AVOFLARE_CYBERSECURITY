#include "uav_sec/uav_sec.h"
#include <stdio.h>

// Skeleton for unit testing crypto Layer 1 & 2
int main(void) {
    printf("Running Crypto tests...\n");
    
    uav_sec_header_t hdr = {
        .epoch_id = 1,
        .direction = 0,
        .sequence = 100,
        .message_type = 5
    };
    
    uint8_t pt[] = "Secret Payload";
    uint8_t ct[64];
    uint8_t tag[16];
    uint8_t key[32] = {0};
    uint8_t iv[12] = {0};
    uint8_t pt_dec[64] = {0};
    
    int enc_res = uav_sec_encrypt(&hdr, pt, sizeof(pt), key, iv, ct, tag);
    if (enc_res != 0) return 1;
    
    int dec_res = uav_sec_decrypt(&hdr, ct, sizeof(pt), key, iv, tag, pt_dec);
    if (dec_res != 0) return 1;
    
    printf("Crypto tests passed.\n");
    return 0;
}
