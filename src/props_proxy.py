# Waydroid Props Proxy (v1.3.35)
import sys
import os
import importlib.util

# Load the original from the backup location
SPEC = importlib.util.spec_from_file_location("props_orig", "/tmp/orig_props.py")
ORIG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORIG)

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
    "ro.debuggable": "0"
}

def host_get(args, prop):
    if prop in SPOOFED_PROPS:
        return SPOOFED_PROPS[prop]
    return ORIG.host_get(args, prop)

def host_set(args, prop, value): return ORIG.host_set(args, prop, value)
def get(args, prop): return ORIG.get(args, prop)
def set(args, prop, value): return ORIG.set(args, prop, value)
def file_get(args, file, prop): return ORIG.file_get(args, file, prop)
