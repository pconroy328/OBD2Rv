#!/bin/bash

if ! [ -e /dev/rfcomm0 ]; then
   echo "rfcomm device file not there - attempting to reconnect"
   ./connectOBD2.sh
fi
sleep 5
python3 Main.py $1
#python3 Main.py mqttrv.lan
#python3 Main.py gx100.lan
#python3 Main.py localhost
