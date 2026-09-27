#include "uav_sec/uav_sec.h"
#include <stdio.h>

// Skeleton for unit testing replay window
int main(void) {
    printf("Running Replay tests...\n");
    
    uav_sec_replay_init();
    
    // Test in-order
    if (!uav_sec_replay_check_and_update(100)) return 1;
    
    // Test duplicate
    if (uav_sec_replay_check_and_update(100)) return 1; // Should fail
    
    // Test out of window (too old)
    if (!uav_sec_replay_check_and_update(165)) return 1;
    if (uav_sec_replay_check_and_update(100)) return 1; // Should fail, outside 64-bit window
    
    printf("Replay tests passed.\n");
    return 0;
}
