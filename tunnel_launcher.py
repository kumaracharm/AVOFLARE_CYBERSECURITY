import os
import sys
import time
import subprocess
import urllib.request
import re

# ==============================================================================
# AVOFLARE v3.5 - CLOUDFLARED TUNNEL AUTOMATED LAUNCHER
# Automatically launches the local backend & creates a free HTTPS Cloudflare Tunnel.
# ==============================================================================

CLOUDFLARED_DOWNLOAD_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
LOCAL_PORT = 8000
EXE_NAME = "cloudflared.exe"

def ensure_backend_running():
    """Checks if the local AVOFLARE server is running on port 8080; starts it if not."""
    try:
        urllib.request.urlopen(f"http://localhost:{LOCAL_PORT}/api/telemetry", timeout=1)
        print(f"[+] Local AVOFLARE backend is active on http://localhost:{LOCAL_PORT}")
    except Exception:
        print(f"[*] Starting local AVOFLARE backend on port {LOCAL_PORT}...")
        subprocess.Popen([sys.executable, "avoflare_cyber_system.py"], cwd=os.path.dirname(os.path.abspath(__file__)))
        time.sleep(2)

def ensure_cloudflared_binary() -> str:
    """Finds system cloudflared or downloads standalone executable to working directory."""
    # 1. Check PATH
    try:
        res = subprocess.run(["cloudflared", "--version"], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[+] Found system-installed cloudflared: {res.stdout.strip()}")
            return "cloudflared"
    except FileNotFoundError:
        pass

    # 2. Check local directory
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), EXE_NAME)
    if os.path.exists(local_path):
        print(f"[+] Found local binary: {local_path}")
        return local_path

    # 3. Download cloudflared.exe
    print(f"[*] Downloading official cloudflared binary from Cloudflare GitHub releases...")
    try:
        urllib.request.urlretrieve(CLOUDFLARED_DOWNLOAD_URL, local_path)
        print(f"[+] Successfully downloaded: {local_path}")
        return local_path
    except Exception as e:
        print(f"[!] Error downloading cloudflared: {e}")
        print("    Please manually install cloudflared from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/")
        sys.exit(1)

def run_tunnel():
    print("\n" + "="*70)
    print("  AVOFLARE v3.5 -- CLOUDFLARE TUNNEL (TRYCLOUDFLARE PUBLIC HTTPS ENGINE)")
    print("="*70 + "\n")

    ensure_backend_running()
    cmd_path = ensure_cloudflared_binary()

    print(f"\n[*] Launching Cloudflare Tunnel pointing to http://localhost:{LOCAL_PORT}...\n")

    cmd = [cmd_path, "tunnel", "--url", f"http://localhost:{LOCAL_PORT}"]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    tunnel_url_found = False
    url_pattern = re.compile(r"https://[-a-zA-Z0-9]+\.trycloudflare\.com")

    try:
        for line in iter(proc.stdout.readline, ''):
            print(line, end='')
            match = url_pattern.search(line)
            if match and not tunnel_url_found:
                tunnel_url_found = True
                pub_url = match.group(0)
                print("\n" + "*"*70)
                print(f"  LIVE PUBLIC CLOUDFLARE TUNNEL URL:")
                print(f"  --> {pub_url}")
                print("*"*70 + "\n")
    except KeyboardInterrupt:
        print("\n[*] Stopping Cloudflare Tunnel...")
        proc.terminate()

if __name__ == "__main__":
    run_tunnel()
