import time
import threading
import json

class HardwareWatchdog:
    """
    Simulates a hardware-level watchdog timer.
    Requires continuous 'pets' from the main flight control loop.
    If the system freezes or locks up, it automatically triggers a failsafe.
    """
    def __init__(self, timeout_sec: float):
        self.timeout = timeout_sec
        self.last_pet = time.time()
        self.running = True
        self.failsafe_triggered = False
        
        # Start a background daemon thread to monitor the heartbeat
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
    def pet(self):
        """Pet the watchdog to indicate the flight control RTOS is healthy."""
        self.last_pet = time.time()
        
    def _monitor_loop(self):
        while self.running:
            time.sleep(0.1)
            # If time since last pet exceeds timeout, trigger failsafe
            if (time.time() - self.last_pet > self.timeout) and not self.failsafe_triggered:
                print("\n[WATCHDOG CRITICAL] Heartbeat lost! Flight loop frozen.")
                self.failsafe_triggered = True
                self.trigger_failsafe()
                    
    def trigger_failsafe(self):
        """Hardware-level override, isolating power or deploying recovery systems."""
        print("[WATCHDOG CRITICAL] --> Failsafe Triggered: Engines Idled. Parachute Deployed. System Locked.")

    def stop(self):
        self.running = False


class CrossDomainGateway:
    """
    The Cross-Domain Security Gateway (CDSG).
    Acts as an isolation boundary between the Untrusted AI Domain (A)
    and the Trusted Flight Control Domain (B).
    """
    def __init__(self):
        # 1. Command Whitelisting
        # Only these high-level navigational intents are allowed to cross the boundary.
        self.WHITELISTED_COMMANDS = {"UPDATE_TARGET", "SET_WAYPOINT", "MISSION_LOG"}
        
        # 2. Flight Envelope Bounds (Schema Validation)
        self.MAX_ALTITUDE_M = 5000.0  # Max altitude 5,000 meters
        self.MAX_SPEED_MPS = 150.0    # Max speed 150 m/s
        
        # 3. Rate Limiting State (DoS Protection)
        self.MAX_MSGS_PER_SEC = 10
        self.msg_count = 0
        self.window_start = time.time()

    def _check_rate_limit(self) -> bool:
        now = time.time()
        if now - self.window_start >= 1.0:
            self.window_start = now
            self.msg_count = 0
            
        self.msg_count += 1
        return self.msg_count <= self.MAX_MSGS_PER_SEC

    def _validate_schema(self, payload: dict) -> bool:
        """Deep inspection of payload arguments ensuring they do not violate physics/safety."""
        cmd_type = payload.get("cmd")
        
        if cmd_type == "SET_WAYPOINT":
            alt = payload.get("altitude_m", 0)
            speed = payload.get("speed_mps", 0)
            
            if not (0 <= alt <= self.MAX_ALTITUDE_M):
                print(f"    [CDSG DENY] Altitude {alt}m exceeds safe physical flight envelope.")
                return False
            if speed > self.MAX_SPEED_MPS:
                print(f"    [CDSG DENY] Speed {speed}m/s exceeds airframe structural limits.")
                return False
                
        return True

    def process_message_from_ai(self, raw_message: str) -> bool:
        """
        The main inspection gate. Returns True if the payload is safe to pass
        into the Flight Control domain, False if it is blocked.
        """
        # 1. Rate Limiting (Prevent flood/DoS on the RTOS)
        if not self._check_rate_limit():
            print("    [CDSG DENY] Rate limit exceeded from AI Domain. Dropping packet.")
            return False
            
        # 2. Parse Payload safely
        try:
            payload = json.loads(raw_message)
        except json.JSONDecodeError:
            print("    [CDSG DENY] Malformed JSON structure.")
            return False
            
        # 3. Whitelisting (Block raw actuator overrides)
        cmd_type = payload.get("cmd")
        if cmd_type not in self.WHITELISTED_COMMANDS:
            print(f"    [CDSG DENY] Command '{cmd_type}' is strictly forbidden across the boundary.")
            return False
            
        # 4. Schema/Envelope Validation
        if not self._validate_schema(payload):
            return False
            
        print(f"    [CDSG ALLOW] Message passed strict validation: {cmd_type}")
        return True


class TrustedFlightDomain:
    """
    Domain B: The highly trusted, hard real-time flight controller.
    """
    def __init__(self):
        # 1.5 second timeout on the hardware watchdog
        self.watchdog = HardwareWatchdog(timeout_sec=1.5)
        # The gateway firewalling us from Domain A
        self.cdsg = CrossDomainGateway()
        
    def receive_from_mission_domain(self, raw_message: str):
        """Entrypoint for messages arriving from Domain A (AI/ML)."""
        # 1. Pass through Gateway filter FIRST
        if self.cdsg.process_message_from_ai(raw_message):
            # 2. If valid, execute in Flight Domain
            self.execute_trusted_command(raw_message)
            
    def execute_trusted_command(self, raw_message: str):
        payload = json.loads(raw_message)
        print(f"    [FLIGHT DOMAIN EXECUTING] Applying trusted command: {payload['cmd']}")

    def main_flight_loop_tick(self):
        """Simulate the primary flight control loop (RTOS)."""
        # Pet the watchdog to prove the system is healthy and alive
        self.watchdog.pet()


if __name__ == "__main__":
    print("--- Initializing Defense-Grade Cross-Domain Security Gateway ---")
    
    # Initialize the highly trusted flight controller (Domain B)
    # The CDSG is instantiated internally to guard it.
    flight_controller = TrustedFlightDomain()
    
    print("\n[+] Normal Operations: AI sends a valid waypoint update...")
    valid_cmd = json.dumps({"cmd": "SET_WAYPOINT", "lat": 34.0, "lon": -118.0, "altitude_m": 1500, "speed_mps": 50})
    flight_controller.receive_from_mission_domain(valid_cmd)
    
    print("\n[!] ATTACK SIMULATION: Compromised AI attempts to directly override motor PWMs...")
    malicious_cmd_1 = json.dumps({"cmd": "RAW_ACTUATOR_OVERRIDE", "motor_1": "OFF", "motor_2": "OFF"})
    flight_controller.receive_from_mission_domain(malicious_cmd_1)
    
    print("\n[!] ATTACK SIMULATION: Compromised AI attempts to command an unrecoverable altitude...")
    malicious_cmd_2 = json.dumps({"cmd": "SET_WAYPOINT", "lat": 34.0, "lon": -118.0, "altitude_m": 85000, "speed_mps": 25})
    flight_controller.receive_from_mission_domain(malicious_cmd_2)
    
    print("\n[!] ATTACK SIMULATION: Compromised AI attempts Denial of Service (DoS) flood...")
    for i in range(12):
        spam_cmd = json.dumps({"cmd": "UPDATE_TARGET", "target_id": i})
        flight_controller.receive_from_mission_domain(spam_cmd)
        
    print("\n[!] WATCHDOG SIMULATION: Simulating a total RTOS lockup / Kernel Panic...")
    print("    Flight control loop is frozen. Waiting for background hardware watchdog to intervene...")
    # By sleeping without calling flight_controller.main_flight_loop_tick(), 
    # the watchdog will naturally expire and trigger the failsafe.
    time.sleep(2.0)
    
    # Cleanup background thread
    flight_controller.watchdog.stop()
    print("\n--- Simulation Complete ---")
