# AVOFLARE v3.5 — DRDO MALE UAV Cybersecurity Layer & Cloudflare Tunnel Deployment

> **AVOFLARE v3.5** is a defense-grade cybersecurity engine and active opposition system for MALE UAVs (TAPAS-BH-201). It includes real-time telemetry analytics, a Red-Team Hacker Console, an active counter-offensive engine, and complete Cloudflare Tunnel (`cloudflared`) readiness.

---

## ⚡ Quick Start Options

### Option 1: Run Local Dashboard Server
To start the local server on `http://localhost:8080`:
```bash
npm start
# OR
python avoflare_cyber_system.py
```

---

### Option 2: Expose Public HTTPS Dashboard via Cloudflare Tunnel (`cloudflared`)

To generate a free, public, secure `https://xxx.trycloudflare.com` URL that exposes the live tactical dashboard to remote operators anywhere in the world:

```bash
npm run tunnel
# OR
python tunnel_launcher.py
```

#### What `tunnel_launcher.py` does automatically:
1. Verifies that `avoflare_cyber_system.py` is running on port `8080` (launches it if inactive).
2. Checks for `cloudflared` in your system PATH or downloads official standalone `cloudflared.exe` automatically.
3. Establishes an encrypted zero-trust tunnel.
4. Outputs the live public HTTPS URL in your console:
   ```text
   ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
     LIVE PUBLIC CLOUDFLARE TUNNEL URL:
     --> https://random-subdomain.trycloudflare.com
   ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
   ```

---

## ☁️ Persistent Cloudflare Named Tunnel Setup (`cloudflared_config.yml`)

For production deployment with your own custom domain (e.g. `uav-gcs.yourdomain.com`):

1. **Authenticate Cloudflare CLI**:
   ```bash
   cloudflared tunnel login
   ```
2. **Create a Tunnel**:
   ```bash
   cloudflared tunnel create avoflare-tunnel
   ```
3. **Configure Ingress**: Update `cloudflared_config.yml` with your Tunnel UUID and credentials file path.
4. **Run Ingress Tunnel**:
   ```bash
   cloudflared tunnel --config cloudflared_config.yml run
   ```

---

## 🛠️ File Structure

- [`avoflare_cyber_system.py`](file:///d:/project/avoflare/uav-gcs-sec-stack/avoflare_cyber_system.py): Python 20 Hz simulation backend & REST HTTP API server.
- [`index.html`](file:///d:/project/avoflare/uav-gcs-sec-stack/index.html): DRDO Tactical Lab split-screen C4I dashboard & Hacker Console.
- [`tunnel_launcher.py`](file:///d:/project/avoflare/uav-gcs-sec-stack/tunnel_launcher.py): Automated Cloudflare Tunnel orchestrator.
- [`cloudflared_config.yml`](file:///d:/project/avoflare/uav-gcs-sec-stack/cloudflared_config.yml): Production Cloudflare Tunnel ingress configuration.
- [`package.json`](file:///d:/project/avoflare/uav-gcs-sec-stack/package.json): NPM scripts configuration.
