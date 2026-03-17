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
            uid = os.getuid()
            log(f"Starting spoofed Waydroid sequence (v1.3.40 Session Shield) as UID {uid}")
            child = None
            try:
                t = lambda m: f"[{time.strftime('%H:%M:%S')}] {m}"
                pyotherside.send('status', t('Authorizing...'), False)
                time.sleep(0.5)
                
                # Normalize environment for Lomiri/Waydroid
                env = os.environ.copy()
                env['XDG_RUNTIME_DIR'] = f"/run/user/{uid}"
                env['DBUS_SESSION_BUS_ADDRESS'] = f"unix:path=/run/user/{uid}/bus"
                env['WAYLAND_DISPLAY'] = 'wayland-0'
                env['XDG_SESSION_TYPE'] = 'wayland'
                log(f"Environment Normalized: DBUS={env.get('DBUS_SESSION_BUS_ADDRESS')}, WAYLAND={env.get('WAYLAND_DISPLAY')}")

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
                    
                    # 1. CLEANUP
                    pyotherside.send('status', t('Clearing environment...'), False)
                    child.sendline("waydroid session stop 2>/dev/null; systemctl stop waydroid-container 2>/dev/null")
                    child.sendline("pkill -9 -f waydroid || true")
                    child.sendline("umount -l /usr/lib/waydroid/tools/helpers/lxc.py 2>/dev/null || true")
                    child.sendline("umount -l /usr/lib/waydroid/tools/helpers/props.py 2>/dev/null || true")
                    child.sendline("rm -f /var/lib/waydroid/fake_cmdline /tmp/orig_*.py 2>/dev/null || true")
                    child.expect(prompt_regex, timeout=20)
                    
                    # 2. PROXY DEPLOY
                    log("Deploying Proxy Identity")
                    child.sendline("cp /usr/lib/waydroid/tools/helpers/lxc.py /tmp/orig_lxc.py")
                    child.sendline("cp /usr/lib/waydroid/tools/helpers/props.py /tmp/orig_props.py")
                    
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    child.sendline(f"mount --bind {os.path.join(script_dir, 'lxc_proxy.py')} /usr/lib/waydroid/tools/helpers/lxc.py")
                    child.sendline(f"mount --bind {os.path.join(script_dir, 'props_proxy.py')} /usr/lib/waydroid/tools/helpers/props.py")
                    child.sendline(f"echo 'androidboot.verifiedbootstate=green androidboot.flash.locked=1 androidboot.vbmeta.device_state=locked buildvariant=user' > /var/lib/waydroid/fake_cmdline")
                    
                    # 3. START CONTAINER
                    pyotherside.send('status', t('Starting Container...'), False)
                    child.sendline("systemctl start waydroid-container")
                    child.expect(prompt_regex, timeout=15)
                    
                    child.sendline("exit")
                    child.close()
                    child = None
                
                # 4. START SESSION
                pyotherside.send('status', t('Starting Session...'), False)
                log("Session start triggered")
                subprocess.Popen(["waydroid", "session", "start"], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
                
                # 5. STABILIZATION
                log("Waiting for container handshake")
                for i in range(40):
                    time.sleep(2)
                    try:
                        out = subprocess.check_output(["waydroid", "status"], env=env).decode()
                        if "Session:	RUNNING" in out and "Container:	RUNNING" in out:
                            log(f"Container is UP at T+{i*2}s")
                            break
                    except: pass
                    pyotherside.send('status', t(f'Booting... ({i+1}/40)'), False)

                # 6. LAUNCH UI (Double-Launch Workaround)
                log("Launching UI with double-tap")
                pyotherside.send('status', t('Opening UI...'), False)
                
                with open("/tmp/waydroid-ui.log", "a") as uilog:
                    uilog.write(f"--- Launch v1.3.42 at {time.ctime()} ---\n")
                    subprocess.Popen(["waydroid", "show-full-ui"], env=env, stdout=uilog, stderr=subprocess.STDOUT)
                    time.sleep(2)
                    subprocess.Popen(["waydroid", "show-full-ui"], env=env, stdout=uilog, stderr=subprocess.STDOUT)
                
                pyotherside.send('status', t("Waydroid Connected!"), True)
                threading.Timer(600, self.cleanup, args=[password]).start()
                
            except Exception as e:
                log(f"ERROR: {str(e)}")
                if child:
                    try: child.close()
                    except: pass
                pyotherside.send('error', str(e))

        threading.Thread(target=run).start()

    def start_ui(self):
        uid = os.getuid()
        log("Manual UI retry triggered")
        env = os.environ.copy()
        env['XDG_RUNTIME_DIR'] = f"/run/user/{uid}"
        env['DBUS_SESSION_BUS_ADDRESS'] = f"unix:path=/run/user/{uid}/bus"
        env['WAYLAND_DISPLAY'] = 'wayland-0'
        with open("/tmp/waydroid-ui.log", "a") as uilog:
            subprocess.Popen(["waydroid", "show-full-ui"], env=env, stdout=uilog, stderr=subprocess.STDOUT)

    def cleanup(self, password):
        log("Cleanup phase")
        try:
            subprocess.run(["sudo", "-S", "umount", "-l", "/usr/lib/waydroid/tools/helpers/lxc.py"], 
                          input=password.encode(), check=False)
            subprocess.run(["sudo", "-S", "umount", "-l", "/usr/lib/waydroid/tools/helpers/props.py"], 
                          input=password.encode(), check=False)
        except: pass

wrapper = WaydroidWrapper()
