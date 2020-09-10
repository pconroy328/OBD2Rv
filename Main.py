# pip3 install paho-mqtt
# pip3 install --user zeroconf

import time
import threading
import obd
import json
import datetime
import paho.mqtt.client as mqtt
import collections
import logging

from obd import OBDCommand, Unit, OBDStatus
from obd.protocols import ECU
from obd.utils import bytes_to_int

import socket
from typing import cast
from zeroconf import IPVersion, ServiceBrowser, ServiceStateChange, Zeroconf, ZeroconfServiceTypes
from time import sleep

#
# ------------------------------------------------------------------
def C2F(degreesC):
    celsius = float(degreesC)
    fahrenheit = (celsius * 1.8) + 32
    return fahrenheit

#
# ------------------------------------------------------------------
def KP2INHG(kp):
    INhg = kp / 0.2953;
    return inhg

#
# ------------------------------------------------------------------
def KPH2MPH(kmph):
    kph = float(kmph)
    mph = (kph * 0.621371)
    return mph

#
# ------------------------------------------------------------------
def SECS2MINS(secs):
    seconds = float(secs)
    minutes = (seconds / 60.0)
    return minutes

#
# ------------------------------------------------------------------
def LPH2GPH(lph):
    gph = (lph / 0.264172)
    return gph


version = '1.0'

pidData = collections.OrderedDict()
statusTopic = 'OBD/STATUS'

dtcData = collections.OrderedDict()
alarmTopic = 'OBD/ALARM'

#
# -----------------------------------------------------------------
def readPIDs (connection, string, sleeptime, lock, *args):
    while 1:
        lock.acquire()
        print( 'Reading PIDs...' )

        pidData[ 'topic' ] = statusTopic
        pidData[ 'version' ] = version
        pidData[ 'dateTime' ] = time.strftime( "%FT%T%z" )
        pidData[ 'connected' ] = (connection.is_connected())

#
#   to do zero these out
#   round voltages

        try:
            cmd = obd.commands.ELM_VOLTAGE
            response = connection.query(cmd)
            pidData[ 'adapterVoltage' ] = response.value.magnitude
        except:
            pidData[ 'adapterVoltage' ] = 0

        try:
            cmd = obd.commands.AMBIANT_AIR_TEMP
            response = connection.query(cmd)
            pidData[ 'ambientAirTemp' ] = C2F( response.value.magnitude )
        except:
            pidData[ 'ambientAirTemp' ] = 0

        try:
            cmd = obd.commands.BAROMETRIC_PRESSURE
            response = connection.query(cmd)
            pidData[ 'ambientPressure' ] = round( KP2INHG( response.value.magnitude ), 1 )
        except:
            pidData[ 'ambientPressure' ] = 0

        try:
            cmd = obd.commands.COOLANT_TEMP
            response = connection.query(cmd)
            pidData[ 'coolantTemp' ] = C2F( response.value.magnitude )
        except:
            pidData[ 'coolantTemp' ] = 0

        try:
            cmd = obd.commands.DISTANCE_W_MIL
            response = connection.query(cmd)
            pidData[ 'distanceWithMIL' ] = KPH2MPH( response.value.magnitude )
        except:
            pidData[ 'distanceWithMIL' ] = 0

        try:
            cmd = obd.commands.ELM_VOLTAGE
            response = connection.query(cmd)
            pidData[ 'adapterVoltage' ] = round( response.value.magnitude, 1 )
        except:
            pidData[ 'adapterVoltage' ] = 0

        try:
            cmd = obd.commands.ENGINE_LOAD
            response = connection.query(cmd)
            pidData[ 'engineLoad' ] = response.value.magnitude
        except:
            pidData[ 'engineLoad' ] = 0

        try:
            cmd = obd.commands.FUEL_LEVEL
            response = connection.query(cmd)
            pidData[ 'fuelLevel' ] = round( response.value.magnitude, 1 )
        except:
            pidData[ 'fuelLevel' ] = 0

        try:
            cmd = obd.commands.RPM
            response = connection.query(cmd)
            pidData[ 'RPM' ] = response.value.magnitude
        except:
            pidData[ 'RPM' ] = 0

        try:
            cmd = obd.commands.SPEED
            response = connection.query(cmd)
            pidData[ 'speed' ] = KPH2MPH( response.value.magnitude )
        except:
            pidData[ 'speed' ] = 0

        try:
            cmd = obd.commands.THROTTLE_POS
            response = connection.query(cmd)
            pidData[ 'throttlePostion' ] = round( response.value.magnitude, 1 )
        except:
            pidData[ 'throttlePostion' ] = 0
       
        try:
            cmd = obd.commands.RUN_TIME
            response = connection.query(cmd)
            pidData[ 'runTime' ] = SECS2MINS( response.value.magnitude )
        except:
            pidData[ 'runTime' ] = 0

        try:
            cmd = obd.commands.CONTROL_MODULE_VOLTAGE           
            response = connection.query(cmd)
            pidData[ 'moduleVoltage' ] = round( response.value.magnitude, 1 )
        except:
            pidData[ 'moduleVoltage' ] = 0

        try:
            cmd = obd.commands.RELATIVE_THROTTLE_POS
            response = connection.query(cmd)
            pidData[ 'relativeThrottlePos' ] = round( response.value.magnitude, 1 )
        except:
            pidData[ 'relativeThrottlePos' ] = 0

        try:
            cmd = obd.commands.THROTTLE_ACTUATOR
            response = connection.query(cmd)
            pidData[ 'throttleActuator' ] = round( response.value.magnitude, 1 )
        except:
            pidData[ 'throttleActuator' ] = 0

        if not connection.is_connected():
            print( 'Yes, we lost connectivity to the ODB unit.' )

        lock.release()
        time.sleep( sleeptime )


#
# -----------------------------------------------------------------
def checkForDTCs (connection, mqttClient, string, sleeptime, lock, *args):

    while 1:
        lock.acquire()
        print( 'Checking to see if Check Enging Light is on or Diagnostic Trouble Codes are present...' )

        dtcData[ 'topic' ] = alarmTopic
        dtcData[ 'version' ] = version
        dtcData[ 'dateTime' ] = time.strftime( "%FT%T%z" )

        try:
            cmd = obd.commands.GET_DTC
            response = connection.query(cmd)
            dtcData[ 'dtcCount' ] = response.value.magnitude

            #
            # Have we driven some distance with the CEL/MIL on?
            cmd = obd.commands.DISTANCE_W_MIL
            response = connection.query(cmd)
            dtcData[ 'dtcDistance' ] = response.value.to("miles")
            if response.value.magnitude > 0.0:
                mqttClient.publish( "OBD/ALARM", json.dumps( dtcData ) )

        except:
            print( 'Error reading DTCs - exception thrown. Did we lose connectivity?' )
            if not connection.is_connected():
                print( 'Yes, we lost connectivity to the ODB unit.' )

        lock.release()
        time.sleep( sleeptime )

#
# -----------------------------------------------------------------
# The callback for when the mqttClient receives a CONNACK response from the server.
def on_connect (mqttClient, userdata, flags, rc):
    print( "MQTT Broker connected with result code " + str( rc ) )

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # mqttClient.subscribe("$SYS/#")

#
# -----------------------------------------------------------------
# The callback for when a PUBLISH message is received from the server.
def on_message (mqttClient, userdata, msg):
    print( msg.topic + " " + str( msg.payload ) )


#
# -----------------------------------------------------------------
def sendMQTTData (mqttClient, string, sleeptime, lock, *args):
    while 1:
        lock.acquire()
        print( 'Keeping Port Alive...' )
        jsonData = json.dumps( pidData )
        print( jsonData )
        #
        # We put the Topic in as part of the packet - but not in the JSON data
        mqttClient.publish("OBD/STATUS", jsonData )
        lock.release()
        time.sleep( sleeptime )

#
# -----------------------------------------------------------------
def sendDisconnectedMessage ():
    pass

#
# ------------------------------------------------------------------
def log(msg):
    print( msg )

#
# -----------------------------------------------------------------
def temperature(messages):
    # "(((A*256)+B)/100)-40)"
    d = messages[0].data
    v = (bytes_to_int(d) / 100) - 40  # helper function for converting byte arrays to ints
    return (v, Unit.TEMP)

#
# -----------------------------------------------------------------
def readEngineOilTemp(connection):
    cmd = OBDCommand( "FORD_OIL_TEMP",      \
               "Ford Engine Oil Temp",      \
               "221310",                    \
               2,                           \
               temp,                        \
               ECU.ENGINE,                  \
               True)             # (optional) allow a "01" to be added for speed
    response = connection.query( cmd, force=True )
    print( response )
    return response.value.magnitude


host_name = None
host_address = None
service_info = None

#
# ----------------------------------------------------------------
def discover_mqtt_host():

    def on_service_state_change( zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange) -> None:
        global service_info
        global host_name
        global host_address
        #print("Service %s of type %s state changed: %s" % (name, service_type, state_change))

        if state_change is ServiceStateChange.Added:
            service_info = zeroconf.get_service_info(service_type, name)
            #print("Info from zeroconf.get_service_info: %r" % (info))
            if service_info:
                addresses = ["%s:%d" % (socket.inet_ntoa(addr), cast(int, service_info.port)) for addr in service_info.addresses]
                #print("  Addresses: %s" % ", ".join(addresses))
                #print("  Weight: %d, priority: %d" % (service_info.weight, service_info.priority))
                #print("  Server: %s" % (info.server,))
                host_name = service_info.server
                host_address = socket.inet_ntoa(service_info.addresses[0])
                if service_info.properties:
                    #print("  Properties are:")
                    for key, value in service_info.properties.items():
                        pass
                        #print("    %s: %s" % (key, value))
                else:
                   pass
                   #print("  No properties")
            else:
                #print("  No info")
                pass
        #print('\n')

    zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
    browser = ServiceBrowser(zeroconf, "_mqtt._tcp.local.",handlers=[on_service_state_change])

    i = 0
    while (service_info is None and i < 50):
        sleep( 0.1 )
        i += 1

    zeroconf.close()
    try:
        return host_address, host_name
    except AttributeError:
        return None

#
# -----------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(filename='/tmp/obd2rv.log', level=logging.INFO)
    logging.info('OBD2Rv v1.0 []')
    logging.debug('Attempting to find mqtt broker via mDNS')

    try:
        host = sys.argv[1]
        mqtt_broker_address = sys.argv[1]
    except:
        print( 'No host passed in on command line. Trying mDNS' )
   
    host = discover_mqtt_host()
    if (host is not None):
        mqtt_broker_address = host[0]
        logging.info( 'Found MQTT Broker using mDNS on {}.{}'.format(host[0], host[1]))
    else:
        logging.warning('Unable to locate MQTT Broker using DNS')
        try:
            mqtt_broker_address = sys.argv[1]
        except:
            logging.critical('mDNS failed and no MQTT Broker address passed in via command line. Exiting')
            sys.exit(1)

    logging.debug('Connecting to {}'.format(mqtt_broker_address))
    try:
        print( 'Trying to connect to our MQTT broker...' )
        myMqttClient = mqtt.Client()
        myMqttClient.on_connect = on_connect
        myMqttClient.on_message = on_message
        myMqttClient.connect( mqtt_broker_address, 1883, 60 )
    except:
        print( 'Unable to connect to our MQTT Broker!')

    #obd.debug.console=True
    #obd.debug.handler = log
    obd.logger.setLevel(obd.logging.DEBUG)

    print( 'Connecting to the OBD-II port...' )
    connection = obd.OBD()

    if connection.status() == OBDStatus.ELM_CONNECTED:
        print( 'ELM327 Interface is online. But car is not responding to ATRV command.' )

    if (connection.status() == OBDStatus.CAR_CONNECTED or connection.status() == OBDStatus.OBD_CONNECTED):
        print( 'ELM327 Interface is online and Car is connected.' )

    if connection.is_connected():
        print( 'Successfully connected to the OBD-II device. Car is online and ignition is on.' )

    try:
        lock = threading.Lock()
        # thread.start_new_thread( readPIDs, (connection, "Read PIDs", 2, lock ))
        t1 = threading.Thread( target=readPIDs, args=(connection, "Read PIDs", 2, lock) )
        t1.start()

        #thread.start_new_thread( sendMQTTData, (myMqttClient, "Send MQTT Data", 5, lock ))
        t2 = threading.Thread( target=sendMQTTData, args=(myMqttClient, "Send MQTT Data", 5, lock) )
        t2.start()
        #thread.start_new_thread( checkForDTCs, (myMqttClient, "checkForDTC", 61, lock ))
        t3 = threading.Thread( target=checkForDTCs, args=(connection, myMqttClient, "checkForDTC", 61, lock) )
        t3.start()

        while 1:
            myMqttClient.loop()
            time.sleep( 1 )
    except:
        myMqttClient.disconnect()
        connection.close()
    
    t1.terminate()
    t1.join()
    t2.terminate()
    t2.join()
    t3.terminate()
    t3.join()


