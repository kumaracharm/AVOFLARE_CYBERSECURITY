// cross_domain_gateway.cpp
//
// Cross-Domain Security Gateway (CDSG) - Interactive UDP Server Edition
// Listens on UDP port 8888 for incoming commands from the Attacker GUI.

#include <iostream>
#include <string>
#include <unordered_set>
#include <chrono>
#include <thread>
#include <atomic>
#include <sstream>

// POSIX sockets for WSL/Linux compilation
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <string.h>

// ----------------------------------------------------------------------------
// HardwareWatchdog: 100ms hardware-level timer
// ----------------------------------------------------------------------------
class HardwareWatchdog {
private:
    double timeout_sec;
    std::atomic<double> last_pet_time;
    std::atomic<bool> running;
    std::atomic<bool> failsafe_triggered;
    std::thread monitor_thread;

    double get_current_time_sec() {
        auto now = std::chrono::steady_clock::now();
        return std::chrono::duration<double>(now.time_since_epoch()).count();
    }

    void monitor_loop() {
        while (running) {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            
            if (!failsafe_triggered) {
                double current_time = get_current_time_sec();
                if ((current_time - last_pet_time) > timeout_sec) {
                    std::cerr << "\n[WATCHDOG CRITICAL] Heartbeat lost! Flight loop frozen for >" 
                              << (timeout_sec * 1000.0) << "ms.\n";
                    failsafe_triggered = true;
                    trigger_failsafe();
                }
            }
        }
    }

    void trigger_failsafe() {
        std::cerr << "[WATCHDOG CRITICAL] --> Failsafe Triggered: Engines Idled. Parachute Deployed. System Locked.\n";
    }

public:
    HardwareWatchdog(double timeout_s) 
        : timeout_sec(timeout_s), 
          last_pet_time(get_current_time_sec()), 
          running(true), 
          failsafe_triggered(false) {
        monitor_thread = std::thread(&HardwareWatchdog::monitor_loop, this);
    }

    ~HardwareWatchdog() {
        stop();
    }

    void pet() {
        last_pet_time = get_current_time_sec();
        // If it was triggered, we can optionally reset it here for the demo
        if (failsafe_triggered) {
            std::cout << "[WATCHDOG] System recovered, heartbeat resumed.\n";
            failsafe_triggered = false;
        }
    }

    void stop() {
        running = false;
        if (monitor_thread.joinable()) {
            monitor_thread.join();
        }
    }
};

// ----------------------------------------------------------------------------
// CrossDomainGateway: CDSG Isolation Boundary
// ----------------------------------------------------------------------------
class CrossDomainGateway {
private:
    std::unordered_set<std::string> whitelisted_commands;
    double max_altitude_m;
    double max_speed_mps;
    
    int max_msgs_per_sec;
    int msg_count;
    double window_start;

    double get_current_time_sec() {
        auto now = std::chrono::steady_clock::now();
        return std::chrono::duration<double>(now.time_since_epoch()).count();
    }

    bool check_rate_limit() {
        double now = get_current_time_sec();
        if ((now - window_start) >= 1.0) {
            window_start = now;
            msg_count = 0;
        }
        
        msg_count++;
        return msg_count <= max_msgs_per_sec;
    }

    bool validate_schema(const std::string& cmd_type, double alt, double speed) {
        if (cmd_type == "SET_WAYPOINT") {
            if (alt < 0 || alt > max_altitude_m) {
                std::cerr << "    [CDSG DENY] Altitude " << alt << "m exceeds safe physical flight envelope.\n";
                return false;
            }
            if (speed > max_speed_mps) {
                std::cerr << "    [CDSG DENY] Speed " << speed << "m/s exceeds airframe structural limits.\n";
                return false;
            }
        }
        return true;
    }

public:
    CrossDomainGateway() :
        max_altitude_m(5000.0),
        max_speed_mps(150.0),
        max_msgs_per_sec(10),
        msg_count(0),
        window_start(get_current_time_sec()) {
            
        whitelisted_commands = {"UPDATE_TARGET", "SET_WAYPOINT", "MISSION_LOG", "HEARTBEAT"};
    }

    bool process_message_from_ai(const std::string& cmd_type, double alt = 0.0, double speed = 0.0) {
        if (!check_rate_limit()) {
            std::cerr << "    [CDSG DENY] Rate limit exceeded. Dropping packet.\n";
            return false;
        }

        if (cmd_type == "RAW_ACTUATOR_OVERRIDE") {
            std::cerr << "    [CDSG DENY] Command 'RAW_ACTUATOR_OVERRIDE' is strictly forbidden across the boundary.\n";
            return false;
        }
        
        if (whitelisted_commands.find(cmd_type) == whitelisted_commands.end()) {
            std::cerr << "    [CDSG DENY] Command '" << cmd_type << "' is not whitelisted.\n";
            return false;
        }

        if (!validate_schema(cmd_type, alt, speed)) {
            return false;
        }

        if (cmd_type != "HEARTBEAT") {
            std::cout << "    [CDSG ALLOW] Message passed strict validation: " << cmd_type << "\n";
        }
        return true;
    }
};

// ----------------------------------------------------------------------------
// UDP Server to interact with Python GUI
// ----------------------------------------------------------------------------
int main() {
    std::cout << "--- Initializing Defense-Grade Cross-Domain Security Gateway (C++) ---\n";
    std::cout << "[*] Listening on UDP Port 8888 for incoming commands...\n\n";
    
    CrossDomainGateway cdsg;
    HardwareWatchdog watchdog(1.0); // 1.0s timeout for easier interactive testing

    int sockfd;
    struct sockaddr_in servaddr, cliaddr;
    
    if ( (sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0 ) {
        perror("socket creation failed");
        return 1;
    }
    
    memset(&servaddr, 0, sizeof(servaddr));
    memset(&cliaddr, 0, sizeof(cliaddr));
    
    servaddr.sin_family    = AF_INET;
    servaddr.sin_addr.s_addr = INADDR_ANY;
    servaddr.sin_port = htons(8888);
    
    if ( bind(sockfd, (const struct sockaddr *)&servaddr, sizeof(servaddr)) < 0 ) {
        perror("bind failed");
        return 1;
    }

    char buffer[1024];
    while (true) {
        socklen_t len = sizeof(cliaddr);
        int n = recvfrom(sockfd, (char *)buffer, 1024, MSG_WAITALL, (struct sockaddr *) &cliaddr, &len);
        if (n > 0) {
            buffer[n] = '\0';
            std::string payload(buffer);
            
            // Simple parsing: CMD ALT SPEED
            std::stringstream ss(payload);
            std::string cmd;
            double alt = 0.0, speed = 0.0;
            
            ss >> cmd;
            if (ss >> alt) {
                ss >> speed;
            }

            if (cmd == "HEARTBEAT") {
                // Background heartbeat to keep watchdog happy
                watchdog.pet();
                cdsg.process_message_from_ai(cmd, alt, speed);
            } else if (cmd == "CRASH") {
                std::cout << "\n[!] ATTACK SIMULATION: Adversary crashed the AI Domain process! Heartbeat halted.\n";
                std::cout << "    Waiting for hardware watchdog to intervene...\n";
            } else {
                std::cout << "\n[>] Received packet: " << payload << "\n";
                cdsg.process_message_from_ai(cmd, alt, speed);
            }
        }
    }
    
    return 0;
}
