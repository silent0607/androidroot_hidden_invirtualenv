import pyotherside
import os
import sys
import threading
import subprocess
import time

# Robustly find path to deps folder
script_dir = os.path.dirname(os.path.abspath(__file__))
deps_path = os.path.abspath(os.path.join(script_dir, '..', 'deps'))
if deps_path not in sys.path:
    sys.path.append(deps_path)

# Try importing dependencies
try:
    import pexpect
except ImportError:
    # If still not found, try adding current src to path as alternative
    sys.path.append(script_dir)
    import pexpect

LOG_FILE = "/tmp/waydroid-wrapper.log"

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{time.ctime()}] {msg}\n")

import password_type
import pam

class WaydroidWrapper:
    def __init__(self):
        self.child = None
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
        log("Wrapper initialized")

    def start_spoofed_waydroid(self, password):
        def run():
            log("Starting spoofed Waydroid sequence (v1.3.35 Proxy Shield)")
            child = None
            try:
                t = lambda m: f"[{time.strftime('%H:%M:%S')}] {m}"
                pyotherside.send('status', t('Authorizing...'), False)
                time.sleep(0.5)
                
                log("Starting persistent shell")
                child = pexpect.spawn('bash --norc --noprofile', env={"TERM": "dumb"}, timeout=60)
                with open(LOG_FILE, "ab") as f:
                    child.logfile = f
                    
                    prompt_regex = r'[\$#]\s*$'
                    child.expect(prompt_regex, timeout=10)
                    
                    child.sendline('sudo -s')
                    index = child.expect(['[pP]assword', prompt_regex], timeout=10)
                    if index == 0:
                        child.sendline(str(password))
                        child.expect(prompt_regex, timeout=10)
                    
                    log("Root shell ready")
                    
                    # 1. CLEAN RESTART
                    pyotherside.send('status', t('Clearing system state...'), False)
                    child.sendline("waydroid session stop 2>/dev/null; systemctl stop waydroid-container 2>/dev/null")
                    child.expect(prompt_regex, timeout=30)
                    
                    # 2. BACKUP ORIGINAL FILES (For Proxy Use)
                    log("Backing up original Waydroid scripts")
                    child.sendline("cp /usr/lib/waydroid/tools/helpers/lxc.py /tmp/orig_lxc.py")
                    child.sendline("cp /usr/lib/waydroid/tools/helpers/props.py /tmp/orig_props.py")
                    
                    # 3. PROXY MOUNT
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    lxc_proxy = os.path.join(script_dir, "lxc_proxy.py")
                    props_proxy = os.path.join(script_dir, "props_proxy.py")
                    
                    targets = {
                        lxc_proxy: "/usr/lib/waydroid/tools/helpers/lxc.py",
                        props_proxy: "/usr/lib/waydroid/tools/helpers/props.py"
                    }
                    
                    log("Mounting proxy shields")
                    for src, dst in targets.items():
                        child.sendline(f"umount -l {dst} 2>/dev/null || true")
                        child.sendline(f"mount --bind {src} {dst}")
                    
                    # 4. FAKE CMDLINE
                    log("Creating fake cmdline")
                    cmdline_val = "androidboot.verifiedbootstate=green androidboot.flash.locked=1 androidboot.vbmeta.device_state=locked buildvariant=user"
                    child.sendline(f"echo '{cmdline_val}' > /var/lib/waydroid/fake_cmdline")
                    
                    # 5. TRIGGER NATIVE GENERATION
                    pyotherside.send('status', t('Injecting identity (Proxy)...'), False)
                    child.sendline("waydroid upgrade -o")
                    child.expect(prompt_regex, timeout=30)
                    
                    # 6. START CONTAINER
                    pyotherside.send('status', t('Launching container...'), False)
                    child.sendline("systemctl start waydroid-container")
                    child.expect(prompt_regex, timeout=15)
                    
                    log("Proxy Deployment complete")
                    child.sendline("exit")
                    try: child.expect(pexpect.EOF, timeout=2)
                    except: pass
                    child.close()
                    child = None
                
                log("Starting waydroid session")
                subprocess.Popen(["waydroid", "session", "start"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Stabilization
                time.sleep(25) 
                
                log("Launching UI")
                subprocess.Popen(["waydroid", "show-full-ui"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                pyotherside.send('status', t("Waydroid Proxy-SPOOFED!"), True)
                threading.Timer(600, self.cleanup, args=[password]).start()
                
            except Exception as e:
                log(f"ERROR: {str(e)}")
                if child:
                    try: child.close()
                    except: pass
                pyotherside.send('error', str(e))

        threading.Thread(target=run).start()

    def start_ui(self):
        log("Manual UI launch triggered")
        subprocess.Popen(["waydroid", "show-full-ui"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def cleanup(self, password):
        log("Starting cleanup")
        child = None
        try:
            child = pexpect.spawn('bash --norc --noprofile', env={"TERM": "dumb"}, timeout=30)
            prompt_regex = r'[\$#]\s*$'
            child.expect(prompt_regex)
            child.sendline('sudo -s')
            index = child.expect(['[pP]assword', prompt_regex], timeout=5)
            if index == 0:
                child.sendline(str(password))
                child.expect(prompt_regex)
            
            targets = [
                "/usr/lib/waydroid/tools/helpers/lxc.py",
                "/usr/lib/waydroid/tools/helpers/props.py"
            ]
            for target in targets:
                child.sendline(f"umount -l {target} 2>/dev/null || true")
            
            child.sendline("rm -f /var/lib/waydroid/fake_cmdline /tmp/orig_*.py 2>/dev/null || true")
            child.expect(prompt_regex, timeout=20)
            child.close()
            log("Cleanup successful")
        except Exception as e:
            log(f"Cleanup error: {e}")
            if child:
                try: child.close()
                except: pass

wrapper = WaydroidWrapper()
