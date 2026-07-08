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
        lines = ["🤖 G4F Renew Status"]
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
        sb.wait_for_element_visible('#sd-timer', timeout=10)
        time.sleep(1)
        return sb.get_text('#sd-timer').strip()
    except:
        try:
            return sb.execute_script("let el = document.querySelector('.countdown-card') || document.querySelector('#sd-timer'); return el ? el.innerText.trim().replace(/\\n/g, '') : 'Unknown';")
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
            
            # 🌟 修复布局错位：滚动到屏幕 1/3 的黄金中间位置，确保核心面板在正中央
            sb.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
            sb.save_screenshot(f"screenshots/{name}_1_loaded.png")

            time_before = get_time(sb)
            print(f"[{name}] Initial time: {time_before}")

            print(f"[{name}] Step 1: Initial click")
            # 清除 Cookie 弹窗干扰
            sb.execute_script("""
                document.querySelectorAll('button, a').forEach(b => {
                    let t = (b.innerText||'').toUpperCase();
                    if(t.includes('ACCEPT') || t.includes('RECOMMENDED')) b.click();
                });
            """)
            time.sleep(1)
            
            # 🌟 修复空点击：严格限制只搜索按钮，杜绝误点背景板
            clicked_initial = sb.execute_script("""
                let els = document.querySelectorAll('button, a, [role="button"]');
                for (let el of els) {
                    let t = (el.innerText||'').toUpperCase();
                    if(t.includes('ADD 90') && !t.includes('VOTE')){
                        el.click(); return true;
                    }
                }
                return false;
            """)
            
            if not clicked_initial:
                print(f"[{name}] Initial button not found via JS, trying exact ID...")
                try: 
                    sb.execute_script("document.querySelector('#sd-vote-btn').click();")
                except: 
                    pass

            time.sleep(4)
            sb.save_screenshot(f"screenshots/{name}_2_after_click1.png")

            print(f"[{name}] Step 2: Captcha")
            for _ in range(3):
                try:
                    sb.uc_gui_click_captcha()
                    time.sleep(2)
                    sb.uc_gui_handle_captcha()
                except:
                    pass
                time.sleep(3)
            
            print(f"[{name}] Step 3: Submit")
            # 🌟 修复空点击：严格匹配最终按钮的各种文字变体
            clicked_submit = sb.execute_script("""
                let els = document.querySelectorAll('button, a, [role="button"]');
                for (let el of els) {
                    let t = (el.innerText||'').toUpperCase();
                    if(t.includes('VOTE') || t.includes('SUBMIT') || t.includes('+90')){
                        el.click(); return true;
                    }
                }
                return false;
            """)
            
            if not clicked_submit:
                print(f"[{name}] Submit button not found via JS, trying exact ID...")
                try: 
                    sb.execute_script("document.querySelector('#vm-submit').click();")
                except: 
                    pass

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
