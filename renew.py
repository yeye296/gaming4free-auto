import os
import sys
import time
import urllib.request
import json
import random
from seleniumbase import SB

if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":1"
if "XAUTHORITY" not in os.environ:
    if os.path.exists("/home/headless/.Xauthority"):
        os.environ["XAUTHORITY"] = "/home/headless/.Xauthority"

TARGETS = [
    {"name": "renqi", "url": "https://g4f.gg/renqi"},
    {"name": "heisi", "url": "https://g4f.gg/heisi"}
]

TG_TOKEN = os.getenv("TG_TOKEN", "")
TG_CHAT = os.getenv("TG_CHAT_ID", "")
PROXY_URL = "socks5://127.0.0.1:10808"

def send_tg(results):
    if not TG_TOKEN or not TG_CHAT:
        return
    try:
        lines = ["G4F Renew Status"]
        for res in results:
            lines.append("-----------------------")
            lines.append(f"Node: {res['name']}")
            lines.append(f"Status: {res['status']}")
            lines.append(f"Time: {res['time']}")
        msg = "\n".join(lines)
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": TG_CHAT, "text": msg}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"TG Error: {e}")

def get_time(sb):
    try:
        sb.wait_for_element_present('#sd-timer', timeout=15)
        time.sleep(1)
        return sb.execute_script("return document.querySelector('#sd-timer').innerText.trim();")
    except:
        return "Unknown"

print("Task started")
task_results = []
os.makedirs("screenshots", exist_ok=True)

for target in TARGETS:
    name = target["name"]
    url = target["url"]
    print(f"\n[{name}] Process started")
    
    try:
        with SB(
            uc=True, 
            test=True, 
            headed=True, 
            headless=False, 
            xvfb=False, 
            chromium_arg="--no-sandbox,--disable-dev-shm-usage,--disable-gpu,--window-position=0,0,--start-maximized",
            proxy=PROXY_URL
        ) as sb:
            
            print(f"[{name}] Loading page")
            sb.uc_open_with_reconnect(url, reconnect_time=5)
            time.sleep(random.uniform(6, 10))
            sb.save_screenshot(f"screenshots/{name}_1_loaded.png")

            time_before = get_time(sb)
            print(f"[{name}] Initial time: {time_before}")

            # 1. Accept Cookies
            sb.execute_script("""
                document.querySelectorAll('button, a').forEach(b => {
                    let t = (b.innerText||'').toUpperCase();
                    if(t.includes('ACCEPT') || t.includes('RECOMMENDED')) b.click();
                });
            """)
            time.sleep(1)

            print(f"[{name}] Step 1: Initial click")
            # 2. JS Click initial button directly (Immune to scroll/overlays)
            try:
                sb.wait_for_element_present("#sd-vote-btn", timeout=15)
                sb.execute_script("document.querySelector('#sd-vote-btn').click();")
            except:
                print(f"[{name}] Warning: #sd-vote-btn not found. Trying text fallback.")
                sb.execute_script("""
                    let els = document.querySelectorAll('button, a, [role="button"]');
                    for (let el of els) {
                        let t = (el.innerText||'').toUpperCase();
                        if(t.includes('ADD 90') && !t.includes('VOTED')){
                            el.click(); break;
                        }
                    }
                """)

            time.sleep(4)
            sb.save_screenshot(f"screenshots/{name}_2_after_click1.png")

            print(f"[{name}] Step 2: Captcha")
            # 3. Handle CF Captcha with early exit if submit button appears
            for _ in range(8):
                if sb.is_element_present("#vm-submit"):
                    print(f"[{name}] Captcha passed early")
                    break
                try:
                    sb.uc_gui_click_captcha()
                    time.sleep(2)
                    sb.uc_gui_handle_captcha()
                except:
                    pass
                time.sleep(3)
            
            print(f"[{name}] Step 3: Submit")
            # 4. JS Click submit button directly (Immune to scroll/overlays)
            submit_clicked = False
            for _ in range(5):
                if sb.is_element_present("#vm-submit"):
                    sb.execute_script("document.querySelector('#vm-submit').click();")
                    submit_clicked = True
                    break
                time.sleep(2)
            
            if not submit_clicked:
                print(f"[{name}] Warning: #vm-submit not found. Trying text fallback.")
                sb.execute_script("""
                    let els = document.querySelectorAll('button, a, [role="button"]');
                    for (let el of els) {
                        let t = (el.innerText||'').toUpperCase();
                        if(t.includes('VOTE') || t.includes('SUBMIT')){
                            el.click(); break;
                        }
                    }
                """)

            print(f"[{name}] Step 4: Wait for reward (45s)")
            time.sleep(45) 
            
            print(f"[{name}] Step 5: Refresh")
            sb.refresh_page()
            time.sleep(8)
            
            final_time = get_time(sb)
            print(f"[{name}] Final time: {final_time}")
            
            if final_time != "Unknown" and final_time != time_before:
                status = "Success"
            else:
                status = "Failed"
                
            sb.save_screenshot(f"screenshots/{name}_3_result.png")
            task_results.append({"name": name, "status": status, "time": final_time})

    except Exception as e:
        print(f"[{name}] Exception: {e}")
        task_results.append({"name": name, "status": "Error", "time": "Unknown"})

print("Task finished, sending notification")
send_tg(task_results)
