#!/bin/bash

if ! [ -e /dev/rfcomm0 ]; then
   echo "rfcomm device file not there - attempting to reconnect"
   sudo systemctl stop obd2.service
   sleep 5
   ./connectOBD2.sh
fi
sleep 5
echo "Attempting to start obd2 service"
sudo systemctl start obd2.service
sudo systemctl status obd2.service
#python3 Main.py $1
#python3 Main.py mqttrv.lan
#python3 Main.py gx100.lan
#python3 Main.py localhost
