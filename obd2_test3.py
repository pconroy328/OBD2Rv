# pip3 install paho-mqtt
# pip3 install --user zeroconf

import sys
import time
import threading
import json
import datetime
import paho.mqtt.client as mqtt
import collections
import logging

import obd
from obd import OBDCommand, Unit, OBDStatus
from obd.protocols import ECU
from obd.utils import bytes_to_int

import socket
from typing import cast
from zeroconf import IPVersion, ServiceBrowser, ServiceStateChange, Zeroconf, ZeroconfServiceTypes
from time import sleep
import serial

#
# -----------------------------------------------------------------
if __name__ == "__main__":
    try: 
        logging.info( 'Connecting to the OBD-II port...' )
        connection = obd.OBD()

        if connection.is_connected():
            logging.info( 'Successfully connected to the OBD-II device. Car is online and ignition is on.' )
    except serial.serialutil.SerialException as ex:
        print('Serial Port Exception.')
    except Exception as ex:
        print('Exiting main loop on exception: ' )
    else:
        print('Port is open, connection is ready!')


