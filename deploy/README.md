# AWS EC2 Production Deployment & Optimization Guide

This guide details how to run **MudaDemote** 24/7 on AWS EC2 (including Free Tier `t2.micro` or `t3.micro`) with maximum performance, memory safety, and zero downtime.

---

## 1. Launching Your EC2 Instance

1. **AMI**: Ubuntu 24.04 LTS or Ubuntu 22.04 LTS (x86_64 or arm64).
2. **Instance Type**: 
   - `t2.micro` or `t3.micro` (1 vCPU, 1 GB RAM — Free Tier eligible).
   - Alternatively `t4g.micro` / `t4g.small` (AWS Graviton — ultra low cost and fast).
3. **Storage**: Standard 8 GB - 20 GB gp3 EBS volume.
4. **Security Group Inbound Rules**:
   - `SSH` (Port 22) — Source: `My IP`
   - `Custom TCP` (Port 8080) — Source: `Anywhere` (`0.0.0.0/0`) or `My IP`

---

## 2. One-Click Setup (Recommended)

SSH into your EC2 instance:
```bash
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>
```

Clone the repository and run the automated setup script:
```bash
git clone https://github.com/fizzynob/MudaDemote.git
cd MudaDemote
sudo bash deploy/ec2_setup.sh
```

The script automatically:
1. **Creates a 2GB swapfile** with tuned swappiness (`vm.swappiness=10`), protecting 1GB RAM instances from Out-Of-Memory (OOM) kills.
2. Installs system build libraries and Python 3.
3. Sets up a clean virtual environment and installs **`uvloop`** (C-based event loop yielding 2x-4x lower CPU overhead to conserve AWS burst credits).
4. Creates and activates the **`mudademote.service`** systemd daemon configured to auto-restart on boot or failures.

---

## 3. Managing the Service

| Action | Command |
|---|---|
| Check Status | `sudo systemctl status mudademote` |
| View Live Logs | `sudo journalctl -u mudademote -f` |
| Restart Service | `sudo systemctl restart mudademote` |
| Stop Service | `sudo systemctl stop mudademote` |

---

## 4. Alternative: Docker Deployment

If you prefer containerized deployment:

```bash
docker compose up -d --build
```

The Docker container includes:
- Built-in healthcheck hitting `http://localhost:8080/healthz`.
- Log rotation (`max-size: 10m`, `max-file: 3`) preventing disk exhaustion.
- Memory reservation & limit guards (`512M`).

---

## 5. Built-in Cloud Optimizations

- **`uvloop` Engine**: On Linux/EC2, standard `asyncio` is automatically replaced with `uvloop`, minimizing CPU core wakeups.
- **Discord Message Cache Bounded**: Default 1,000-message memory cache capped to `max_messages=100`, reducing RAM consumption by ~150MB.
- **Ring Buffer Event Logging**: Web dashboard logs use \(O(1)\) ring deques, never exceeding memory limits.
- **Background GC Trim**: Garbage collection runs every 10 minutes to clean cyclical memory references during quiet roll intervals.
- **Cloud Health Endpoint**: `/healthz` and `/api/health` expose process memory, CPU utilization, and bot status for AWS ALBs or CloudWatch probes.
