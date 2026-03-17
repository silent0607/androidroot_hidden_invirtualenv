# Surgical patch for lxc.py
import subprocess
import os
import re
import logging
import glob
import shutil
import time
import platform
import gbinder
import tools.config
import tools.helpers.run

# --- ORIGINAL CORE LOGIC ---
def get_lxc_version(args):
    if shutil.which("lxc-info") is not None:
        command = ["lxc-info", "--version"]
        version_str = tools.helpers.run.user(args, command, output_return=True)
        return int(version_str[0])
    return 0

def add_node_entry(nodes, src, dist, mnt_type, options, check):
    if check and not os.path.exists(src): return False
    entry = f"lxc.mount.entry = {src} {dist if dist else src[1:]} {mnt_type} {options}"
    nodes.append(entry)
    return True

def generate_nodes_lxc_config(args):
    nodes = []
    def make_entry(src, dist=None, mnt_type="none", options="bind,create=file,optional 0 0", check=True):
        return add_node_entry(nodes, src, dist, mnt_type, options, check)

    # Standard nodes
    for n in ["/dev/zero", "/dev/null", "/dev/full", "/dev/ashmem", "/dev/fuse", "/dev/ion", "/dev/tty", "/dev/uhid", "/dev/net/tun", "/dev/sw_sync"]:
        make_entry(n)
    
    # --- PATCH: FAKE CMDLINE ---
    make_entry("/var/lib/waydroid/fake_cmdline", "proc/cmdline", options="bind,ro,create=file,optional 0 0")

    # Hardware nodes
    make_entry("tmpfs", "dev", "tmpfs", "nosuid 0 0", False)
    for n in glob.glob("/dev/kgsl*") + glob.glob("/dev/mali*") + glob.glob("/dev/pvr*") + glob.glob("/dev/pmsg*") + glob.glob("/dev/fb*") + glob.glob("/dev/graphics/fb*") + glob.glob("/dev/video*") + glob.glob("/dev/dma_heap/*"):
        make_entry(n)
        
    render, _ = tools.helpers.gpu.getDriNode(args)
    if render: make_entry(render)

    # Binder
    make_entry("/dev/" + args.BINDER_DRIVER, "dev/binder", check=False)
    make_entry("/dev/" + args.VNDBINDER_DRIVER, "dev/vndbinder", check=False)
    make_entry("/dev/" + args.HWBINDER_DRIVER, "dev/hwbinder", check=False)
    if args.vendor_type != "MAINLINE":
        make_entry("/dev/hwbinder", "dev/host_hwbinder")
        make_entry("/vendor", "vendor_extra", options="rbind,optional 0 0")

    make_entry(tools.config.defaults["host_perms"], "vendor/etc/host-permissions", options="bind,optional 0 0")
    make_entry("/sys/kernel/debug", options="rbind,create=dir,optional 0 0")
    for n in ["/dev/Vcodec", "/dev/MTK_SMI", "/dev/mdp_sync", "/dev/mtk_cmdq"]: make_entry(n)

    make_entry("tmpfs", "mnt_extra", "tmpfs", "nodev 0 0", False)
    for n in ["tmp", "var", "run"]: make_entry("tmpfs", n, "tmpfs", "nodev 0 0", False)
    make_entry("/system/etc/libnfc-nci.conf", options="bind,optional 0 0")

    return nodes

def get_apparmor_status(args):
    try:
        with open("/sys/kernel/security/apparmor/profiles", "r") as f:
            return "lxc-waydroid" in f.read()
    except: return False

def set_lxc_config(args):
    lxc_path = tools.config.defaults["lxc"] + "/waydroid"
    lxc_ver = get_lxc_version(args)
    config_paths = tools.config.tools_src + "/data/configs/config_"
    config_snippets = [ config_paths + "base" ]
    if lxc_ver <= 2: config_snippets.append(config_paths + "1")
    else:
        for ver in range(3, 5):
            snippet = config_paths + str(ver)
            if lxc_ver >= ver and os.path.exists(snippet): config_snippets.append(snippet)

    os.makedirs(lxc_path, exist_ok=True)
    command = ["sh", "-c", "cat {} > \"{}\"".format(' '.join('"{0}"'.format(w) for w in config_snippets), lxc_path + "/config")]
    tools.helpers.run.user(args, command)
    # --- PATCH: FORCE aarch64 ---
    tools.helpers.run.user(args, ["sed", "-i", "s/LXCARCH/aarch64/g", lxc_path + "/config"])
    
    shutil.copy(tools.config.tools_src + "/data/configs/waydroid.seccomp", lxc_path + "/waydroid.seccomp")
    if get_apparmor_status(args):
        tools.helpers.run.user(args, ["sed", "-i", "-E", "/lxc.aa_profile|lxc.apparmor.profile/ s/unconfined/lxc-waydroid/g", lxc_path + "/config"])

    nodes = generate_nodes_lxc_config(args)
    with open(lxc_path + "/config_nodes", "w") as f:
        for node in nodes: f.write(node + "\n")
    open(os.path.join(lxc_path, "config_session"), mode="w").close()

def generate_session_lxc_config(args, session):
    lxc_path = tools.config.defaults["lxc"] + "/waydroid"
    with open(lxc_path + "/config_session", "w") as f:
        f.write(f"lxc.mount.entry = tmpfs {tools.config.defaults['container_xdg_runtime_dir']} tmpfs create=dir 0 0\n")
        f.write(f"lxc.mount.entry = {os.path.realpath(os.path.join(session['xdg_runtime_dir'], session['wayland_display']))} {tools.config.defaults['container_xdg_runtime_dir'][1:]}/{tools.config.defaults['container_wayland_display']} none rbind,create=file 0 0\n")
        f.write(f"lxc.mount.entry = {session['waydroid_data']} data none rbind 0 0\n")

def make_base_props(args):
    # Discovery logic but with our overrides
    props = [
        "ro.product.model=M2004J19C", "ro.product.brand=Redmi", "ro.product.manufacturer=Xiaomi",
        "ro.product.name=lancelot_global", "ro.product.device=lancelot",
        "ro.build.fingerprint=Redmi/lancelot_global/lancelot:11/RP1A.200720.011/V12.5.4.0.RJCMIXM:user/release-keys",
        "ro.build.id=RP1A.200720.011", "ro.build.version.incremental=V12.5.4.0.RJCMIXM",
        "ro.build.version.security_patch=2021-11-01", "ro.build.version.sdk=30",
        "ro.build.type=user", "ro.build.tags=release-keys",
        "ro.boot.flash.locked=1", "ro.boot.verifiedbootstate=green",
        "ro.boot.vbmeta.device_state=locked", "ro.secure=1", "ro.debuggable=0",
        "waydroid.tools_version=" + tools.config.version
    ]
    # Add essential system stuff
    ccodec = tools.helpers.props.host_get(args, "debug.stagefright.ccodec")
    if ccodec: props.append("debug.stagefright.ccodec=" + ccodec)
    
    # Config overrides
    cfg = tools.config.load(args)
    for k, v in cfg["properties"].items():
        props = [p for p in props if not p.startswith(k+"=")]
        props.append(k+"="+v)
    
    with open(args.work + "/waydroid_base.prop", "w") as f:
        for p in props: f.write(p + "\n")

# --- STUBS ---
def setup_host_perms(args): pass
def status(args):
    try: return tools.helpers.run.user(args, ["lxc-info", "-P", tools.config.defaults["lxc"], "-n", "waydroid", "-sH"], output_return=True).strip()
    except: return "STOPPED"
def wait_for_running(args):
    for _ in range(10):
        if status(args) == "RUNNING": return
        time.sleep(1)
    raise OSError("container failed to start")
def start(args):
    tools.helpers.run.user(args, ["lxc-start", "-P", tools.config.defaults["lxc"], "-F", "-n", "waydroid", "--", "/init"], output="background")
    wait_for_running(args)
def stop(args): tools.helpers.run.user(args, ["lxc-stop", "-P", tools.config.defaults["lxc"], "-n", "waydroid", "-k"])
def freeze(args): pass
def unfreeze(args): pass
def shell(args): pass
def logcat(args): pass
