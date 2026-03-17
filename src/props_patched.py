# Patched props.py for Waydroid spoofing
from shutil import which
import subprocess
import logging
import os
import tools.helpers.run
from tools.interfaces import IPlatform

# HARDCODED SPOOFED VALUES
SPOOFED_PROPS = {
    "ro.product.vendor.brand": "Redmi",
    "ro.product.vendor.device": "lancelot",
    "ro.product.vendor.manufacturer": "Xiaomi",
    "ro.product.vendor.model": "M2004J19C",
    "ro.product.vendor.name": "lancelot_global",
    "ro.vendor.build.fingerprint": "Redmi/lancelot_global/lancelot:11/RP1A.200720.011/V12.5.4.0.RJCMIXM:user/release-keys",
    "ro.boot.flash.locked": "1",
    "ro.boot.verifiedbootstate": "green",
    "ro.boot.vbmeta.device_state": "locked",
    "ro.build.tags": "release-keys",
    "ro.build.type": "user",
    "ro.secure": "1",
    "ro.debuggable": "0",
    "ro.treble.enabled": "true"
}

def host_get(args, prop):
    if prop in SPOOFED_PROPS:
        return SPOOFED_PROPS[prop]
    
    if which("getprop") is not None:
        command = ["getprop", prop]
        return subprocess.run(command, stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
    else:
        return ""

def host_set(args, prop, value):
    if which("setprop") is not None:
        command = ["setprop", prop, value]
        tools.helpers.run.user(args, command)

def get(args, prop):
    platformService = IPlatform.get_service(args)
    if platformService:
        return platformService.getprop(prop, "")
    else:
        logging.error("Failed to access IPlatform service")

def set(args, prop, value):
    platformService = IPlatform.get_service(args)
    if platformService:
        platformService.setprop(prop, value)
    else:
        logging.error("Failed to access IPlatform service")

def file_get(args, file, prop):
    with open(file) as build_prop:
        for line in build_prop:
            line = line.strip()
            if len(line) == 0 or line[0] == "#":
                continue
            k, _, v = line.partition("=")
            if k == prop:
                return v.strip()
    return ""
