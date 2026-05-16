# Google Cloud Platform (GCP) Deployment Guide

This guide explains how to deploy the EYE-DENTIFY `surveillance_live_service.py` to a Google Compute Engine (GCE) instance and connect your ESP32-CAM to it.

## 1. Create a GPU-Enabled VM Instance

1.  **Go to the GCP Console:** Navigate to **Compute Engine > VM instances**.
2.  **Click "Create Instance"**.
3.  **Machine Configuration:**
    *   **Region:** Select a region that has GPU availability (e.g., `us-central1`).
    *   **Machine family:** General-purpose.
    *   **Series:** N1.
    *   **GPU:** Click **+ ADD GPU**. Select **NVIDIA T4** (cost-effective) or **NVIDIA L4**.
4.  **Boot Disk:**
    *   Click **CHANGE**.
    *   **Operating System:** Select **Deep Learning on Linux**.
    *   **Version:** Select **Deep Learning VM with CUDA 12.1 M124** (or latest CUDA 12.x).
    *   **Size:** 50-100 GB.
5.  **Firewall:**
    *   Check **Allow HTTP traffic**.
    *   Check **Allow HTTPS traffic**.
6.  **Identity and API access:**
    *   Ensure "Allow full access to all Cloud APIs" is selected (or at least storage access if using Supabase/Vertex).

## 2. Configure GCP Firewall

By default, GCP blocks port 8000. You must open it for the ESP32-CAM.

1.  Navigate to **VPC network > Firewall**.
2.  Click **CREATE FIREWALL RULE**.
3.  **Name:** `allow-eyedentify-8000`.
4.  **Targets:** All instances in the network (or use a specific target tag).
5.  **Source IPv4 ranges:** `0.0.0.0/0` (or your specific home IP for better security).
6.  **Protocols and ports:** Check **TCP** and enter `8000`.
7.  Click **CREATE**.

## 3. Deployment Steps

SSH into your VM and run the following:

```bash
# 1. Clone the repository
git clone <your-repo-url> eye-dentify
cd eye-dentify

# 2. Build the Docker image
# We can use Dockerfile.runpod as it is already configured for CUDA 12.1
docker build -f Dockerfile.runpod -t ed-surveillance .

# 3. Run the container in ESP32 mode
# Replace <YOUR_SECRET> with a strong key for API security
docker run -d \
  --name surveillance-app \
  --gpus all \
  -p 8000:8000 \
  -e API_AUTH_REQUIRED=1 \
  -e API_JWT_SECRET=YOUR_SECRET_KEY_HERE \
  -e ESP32_MODE=1 \
  ed-surveillance
```

## 4. Connect ESP32-CAM

1.  Get your **External IP** from the VM instances page.
2.  Open `esp32cam_eyedentify_simple.ino` in Arduino IDE.
3.  Update the following:
    ```cpp
    #define SERVER_HOST "YOUR_GCP_EXTERNAL_IP"
    #define SERVER_PORT 8000
    ```
4.  Upload the sketch to your ESP32-CAM.

## 5. Access the Dashboard

Visit `http://<YOUR_GCP_EXTERNAL_IP>:8000` in your browser.
If you enabled `API_AUTH_REQUIRED`, you will need to log in or use the JWT token.

---

### Troubleshooting

- **GPU Not Found:** Run `nvidia-smi` on the VM to ensure drivers are working.
- **Connection Refused:** Ensure the firewall rule for port 8000 is active.
- **Quota Error:** If you can't create the VM, go to **IAM & Admin > Quotas** and search for `Nvidia T4 GPUs`. Request an increase to 1.
