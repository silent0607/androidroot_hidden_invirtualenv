#!/bin/bash
# High-precision debug wrapper for Waydroid Wrapper
LOG="/tmp/waydroid-wrapper-startup.log"
echo "--- Startup Trace $(date) ---" > $LOG
export DISPLAY=:0
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/32011/bus"

# Get the app directory
APP_DIR=$(dirname $(readlink -f $0))
cd $APP_DIR

echo "App Dir: $APP_DIR" >> $LOG
echo "Executing qmlscene..." >> $LOG

/usr/bin/qmlscene qml/Main.qml >> $LOG 2>&1
echo "Exit code: $?" >> $LOG
