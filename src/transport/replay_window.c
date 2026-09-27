#include "uav_sec/uav_sec.h"

// Skeleton for Anti-Replay Sliding Window Engine
static uint64_t replay_window_mask = 0;
static uint64_t highest_seq_seen = 0;
#define WINDOW_SIZE 64

void uav_sec_replay_init(void) {
    replay_window_mask = 0;
    highest_seq_seen = 0;
}

bool uav_sec_replay_check_and_update(uint64_t sequence) {
    if (sequence > highest_seq_seen) {
        // Shift window for new highest
        uint64_t diff = sequence - highest_seq_seen;
        if (diff >= WINDOW_SIZE) {
            replay_window_mask = 0;
        } else {
            replay_window_mask <<= diff;
        }
        replay_window_mask |= 1ULL; // Mark as seen
        highest_seq_seen = sequence;
        return true;
    }

    if (sequence <= highest_seq_seen && sequence > (highest_seq_seen >= WINDOW_SIZE ? highest_seq_seen - WINDOW_SIZE : 0)) {
        uint64_t diff = highest_seq_seen - sequence;
        if ((replay_window_mask & (1ULL << diff)) != 0) {
            return false; // Replay detected
        }
        replay_window_mask |= (1ULL << diff); // Mark as seen
        return true;
    }

    return false; // Too old, drop
}
