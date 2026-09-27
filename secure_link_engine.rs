// secure_link_engine.rs
//
// Defense-grade UAV <-> GCS Secure Link Engine.
// Implements the zero-allocation 64-bit sliding-window bitmask anti-replay filter.
// Compatible with no_std environments for real-time <15us deterministic performance.

#![no_std]

/// Size of the anti-replay sliding window.
pub const WINDOW_SIZE: u64 = 64;

/// Anti-replay state tracker using a 64-bit sliding window.
pub struct AntiReplayFilter {
    highest_seq: u64,
    window_mask: u64,
}

impl AntiReplayFilter {
    /// Initialize a new AntiReplayFilter.
    pub const fn new() -> Self {
        Self {
            highest_seq: 0,
            window_mask: 0,
        }
    }

    /// Checks if a sequence number is valid (not a replay, not too old).
    /// Updates the internal bitmask if valid.
    /// Returns true if the packet is accepted, false if rejected.
    #[inline]
    pub fn check_replay(&mut self, sequence: u64) -> bool {
        // First packet initialized at 0 or higher
        if sequence > self.highest_seq {
            let diff = sequence - self.highest_seq;
            if diff >= WINDOW_SIZE {
                self.window_mask = 0;
            } else {
                self.window_mask <<= diff;
            }
            // Mark the current sequence as received
            self.window_mask |= 1;
            self.highest_seq = sequence;
            return true;
        }

        // Sequence is older than or equal to the highest seen
        let diff = self.highest_seq - sequence;

        // Packet is too old, outside the 64-packet window
        if diff >= WINDOW_SIZE {
            return false;
        }

        let bit_mask = 1u64 << diff;

        // Check if we already saw this packet (bit is set)
        if (self.window_mask & bit_mask) != 0 {
            return false; // Replay / duplicate
        }

        // Mark as received
        self.window_mask |= bit_mask;
        return true;
    }

    /// Reverts the bitmask for a given sequence in case authentication fails later in the pipeline.
    /// Prevents adversaries from intentionally burning valid sequence numbers.
    #[inline]
    pub fn revert_sequence(&mut self, sequence: u64) {
        if sequence <= self.highest_seq {
            let diff = self.highest_seq - sequence;
            if diff < WINDOW_SIZE {
                let bit_mask = 1u64 << diff;
                self.window_mask &= !bit_mask;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_initial_acceptance() {
        let mut filter = AntiReplayFilter::new();
        assert!(filter.check_replay(1), "First packet should be accepted");
        assert_eq!(filter.highest_seq, 1);
        assert_eq!(filter.window_mask, 1);
    }

    #[test]
    fn test_duplicate_drop() {
        let mut filter = AntiReplayFilter::new();
        assert!(filter.check_replay(100));
        assert!(!filter.check_replay(100), "Duplicate packet must be dropped");
    }

    #[test]
    fn test_out_of_order_acceptance() {
        let mut filter = AntiReplayFilter::new();
        assert!(filter.check_replay(100)); // highest=100, mask=0b1
        
        // Out of order but within window
        assert!(filter.check_replay(99), "Out of order packet within window should be accepted");
        
        // Ensure both are recorded
        // diff for 99 is 1, so bit 1 should be set. diff for 100 is 0, so bit 0 should be set.
        // mask = 0b11 (3 in decimal)
        assert_eq!(filter.window_mask, 3);
        assert_eq!(filter.highest_seq, 100);
    }

    #[test]
    fn test_stale_packet_drop() {
        let mut filter = AntiReplayFilter::new();
        assert!(filter.check_replay(200));
        
        // 200 - 64 = 136. So 136 is just outside the window.
        assert!(!filter.check_replay(136), "Stale packet at exactly WINDOW_SIZE limit must be dropped");
        assert!(!filter.check_replay(135), "Stale packet must be dropped");
    }

    #[test]
    fn test_window_shift() {
        let mut filter = AntiReplayFilter::new();
        assert!(filter.check_replay(10));
        assert!(filter.check_replay(12)); // shifts by 2, mask becomes 0b100 | 1 = 0b101
        
        assert_eq!(filter.highest_seq, 12);
        assert_eq!(filter.window_mask, 5); // 101 in binary
        
        // Check 11 (diff 1)
        assert!(filter.check_replay(11));
        assert_eq!(filter.window_mask, 7); // 111 in binary
        
        // Now shift by more than window size
        assert!(filter.check_replay(100)); // 100 - 12 = 88 (> 64)
        assert_eq!(filter.highest_seq, 100);
        assert_eq!(filter.window_mask, 1);
    }
}
