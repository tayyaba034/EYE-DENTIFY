# Google Colab Deployment Guide

Follow these steps to run the surveillance backend on Google Colab for free.

## 1. Get an Ngrok Token
1.  Sign up/Log in at [ngrok.com](https://dashboard.ngrok.com/get-started/your-authtoken).
2.  Copy your **Your Authtoken**.

## 2. Open Google Colab
1.  Go to [colab.research.google.com](https://colab.research.google.com/).
2.  Create a **New Notebook**.
3.  Change Runtime Type to **GPU** (**Runtime > Change runtime type > T4 GPU**).

## 3. Paste and Run this Code

Copy the code block below into a Colab cell and run it:

```python
# 1. Clone repo and install dependencies
!git clone https://github.com/your-username/eye-dentify.git  # <-- REPLACE WITH YOUR REPO URL
%cd eye-dentify
!pip install -r requirements-deployment.txt
!pip install pyngrok

# 2. Setup Ngrok
from pyngrok import ngrok
import os

# --- PASTE YOUR TOKEN HERE ---
NGROK_TOKEN = "YOUR_NGROK_AUTHTOKEN"
ngrok.set_auth_token(NGROK_TOKEN)

# 3. Start the service in the background
import subprocess
import time

print("[INFO] Starting surveillance service...")
# We use --esp32-mode to receive frames from your camera
cmd = "python surveillance_live_service.py --esp32-mode --host 127.0.0.1 --port 8000"
process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

# 4. Create Tunnel
public_url = ngrok.connect(8000).public_url
print("\n" + "="*50)
print(f" PUBLIC URL: {public_url}")
print("="*50)
print("\n[INSTRUCTIONS]")
print(f"1. Open {public_url} in your browser to see the dashboard.")
print(f"2. Put '{public_url.replace('https://', '')}' in your Arduino SERVER_HOST.")
print("="*50 + "\n")

# Keep showing logs
try:
    while True:
        line = process.stdout.readline()
        if not line: break
        print(line.strip())
except KeyboardInterrupt:
    process.terminate()
    ngrok.disconnect(public_url)
```

## 4. Update ESP32-CAM Code

1.  From the Colab output, copy the `xxxx.ngrok-free.app` part (without `https://`).
2.  In your Arduino code (`esp32cam_eyedentify_simple.ino`):
    ```cpp
    #define SERVER_HOST "your-id.ngrok-free.app"
    #define SERVER_PORT 80
    ```
    *Note: Ngrok handles port forwarding, so use port 80 for the host.*

3.  Upload to your ESP32-CAM.

## Important Notes
- **Free Account Limit:** Ngrok allows only 1 tunnel at a time on the free plan.
- **Session Timeout:** If Colab disconnects, you must re-run the code and get a NEW URL.
