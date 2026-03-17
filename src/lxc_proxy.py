# Waydroid LXC Proxy (v1.3.35)
import sys
import os
import importlib.util

# Load the original from the backup location
SPEC = importlib.util.spec_from_file_location("lxc_orig", "/tmp/orig_lxc.py")
ORIG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORIG)

# Delegate everything by default
def get_lxc_version(args): return ORIG.get_lxc_version(args)
def add_node_entry(nodes, src, dist, mnt_type, options, check): return ORIG.add_node_entry(nodes, src, dist, mnt_type, options, check)
def get_apparmor_status(args): return ORIG.get_apparmor_status(args)
def set_lxc_config(args): return ORIG.set_lxc_config(args)
def generate_session_lxc_config(args, session): return ORIG.generate_session_lxc_config(args, session)
def setup_host_perms(args): return ORIG.setup_host_perms(args)
def status(args): return ORIG.status(args)
def wait_for_running(args): return ORIG.wait_for_running(args)
def start(args): return ORIG.start(args)
def stop(args): return ORIG.stop(args)
def freeze(args): return ORIG.freeze(args)
def unfreeze(args): return ORIG.unfreeze(args)
def shell(args): return ORIG.shell(args)
def logcat(args): return ORIG.logcat(args)

# Intercept and modify
def generate_nodes_lxc_config(args):
    nodes = ORIG.generate_nodes_lxc_config(args)
    # Add SPOOFED CMDLINE MOUNT
    entry = "lxc.mount.entry = /var/lib/waydroid/fake_cmdline proc/cmdline none bind,ro,create=file,optional 0 0"
    if entry not in nodes:
        nodes.append(entry)
    return nodes

def make_base_props(args):
    # Let original do its thing first
    ORIG.make_base_props(args)
    # Now append/overwrite with our spoofed values
    props_path = args.work + "/waydroid_base.prop"
    if os.path.exists(props_path):
        with open(props_path, "r") as f:
            lines = f.readlines()
        
        spoofs = {
            "ro.product.model": "M2004J19C", "ro.product.brand": "Redmi", "ro.product.manufacturer": "Xiaomi",
            "ro.product.name": "lancelot_global", "ro.product.device": "lancelot",
            "ro.build.fingerprint": "Redmi/lancelot_global/lancelot:11/RP1A.200720.011/V12.5.4.0.RJCMIXM:user/release-keys",
            "ro.build.id": "RP1A.200720.011", "ro.build.version.incremental": "V12.5.4.0.RJCMIXM",
            "ro.build.version.security_patch": "2021-11-01", "ro.build.version.sdk": "30",
            "ro.build.type": "user", "ro.build.tags": "release-keys",
            "ro.boot.flash.locked": "1", "ro.boot.verifiedbootstate": "green",
            "ro.boot.vbmeta.device_state": "locked", "ro.secure": "1", "ro.debuggable": "0"
        }
        
        new_lines = []
        seen = set()
        for line in lines:
            line = line.strip()
            if not line: continue
            k = line.split("=")[0] if "=" in line else ""
            if k in spoofs:
                new_lines.append(f"{k}={spoofs[k]}\n")
                seen.add(k)
            else:
                new_lines.append(line + "\n")
        
        for k, v in spoofs.items():
            if k not in seen:
                new_lines.append(f"{k}={v}\n")
        
        with open(props_path, "w") as f:
            f.writelines(new_lines)
