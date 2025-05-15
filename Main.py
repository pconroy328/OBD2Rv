import sys
sys.path.insert(0, '/home/pconroy/OBD2Rv/obd-0.7.3')



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

###import obd
sys.path.append('/home/pconroy/python-OBD')
import obd
from obd import OBDCommand, Unit, OBDStatus
from obd.protocols import ECU
from obd.utils import bytes_to_int
import serial

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
    return INhg

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


version = '1.1'

pid_topic = 'OBD'
status_topic = 'OBD/STATUS'
alarm_topic = 'OBD/ALARM'

pid_data = collections.OrderedDict()
dtc_data = collections.OrderedDict()


#
# -----------------------------------------------------------------
def read_PIDs (connection):
    logging.info( 'Reading PIDs...' )

    pid_data[ 'topic' ] = pid_topic
    pid_data[ 'version' ] = version
    pid_data[ 'dateTime' ] = time.strftime( "%FT%T%z" )
    pid_data[ 'connected' ] = (connection.is_connected())

    try:
        cmd = obd.commands.ELM_VOLTAGE
        response = connection.query(cmd)
        pid_data[ 'adapterVoltage' ] = round(response.value.magnitude, 1)
    except Exception as ex:
        logging.error('Exception ELM VOLTAGE',ex);
        pid_data[ 'adapterVoltage' ] = 0

    try:
        cmd = obd.commands.AMBIANT_AIR_TEMP
        response = connection.query(cmd)
        pid_data[ 'ambientAirTemp' ] = round(C2F(response.value.magnitude),1)
    except Exception as ex:
        ## SOMETHING is wrong - we may have lost connectivity
        logging.error('Exception AMBIENT AIR TEMP',ex);
        pid_data[ 'ambientAirTemp' ] = 0

    try:
        cmd = obd.commands.BAROMETRIC_PRESSURE
        response = connection.query(cmd)
        pid_data[ 'ambientPressure' ] = round( KP2INHG(response.value.magnitude), 1 )
    except Exception as ex:
        logging.error('Exception BAROMTERIC PRESSURE',ex);
        pid_data[ 'ambientPressure' ] = 0

    try:
        cmd = obd.commands.COOLANT_TEMP
        response = connection.query(cmd)
        pid_data[ 'coolantTemp' ] = round(C2F(response.value.magnitude),1)
    except Exception as ex:
        logging.error('Exception COOLANT TEMP',ex);
        pid_data[ 'coolantTemp' ] = 0

    try:
        cmd = obd.commands.DISTANCE_W_MIL
        response = connection.query(cmd)
        pid_data[ 'distanceWithMIL' ] = round(KPH2MPH(response.value.magnitude),1)
    except Exception as ex:
        logging.error('Exception DISTANCE W MIL',ex);
        pid_data[ 'distanceWithMIL' ] = 0

    try:
        cmd = obd.commands.ELM_VOLTAGE
        response = connection.query(cmd)
        pid_data[ 'adapterVoltage' ] = round(response.value.magnitude, 1)
    except Exception as ex:
        logging.error('Exception ADAPTER VOLTAGE',ex);
        pid_data[ 'adapterVoltage' ] = 0

    try:
        cmd = obd.commands.ENGINE_LOAD
        response = connection.query(cmd)
        pid_data[ 'engineLoad' ] = round(response.value.magnitude,1)
    except Exception as ex:
        logging.error('Exception ENGINE LOAD',ex);
        pid_data[ 'engineLoad' ] = 0

    try:
        cmd = obd.commands.FUEL_LEVEL
        response = connection.query(cmd)
        pid_data[ 'fuelLevel' ] = round(response.value.magnitude, 1)
    except Exception as ex:
        logging.error('Exception FUEL LEVEL',ex);
        pid_data[ 'fuelLevel' ] =0

    try:
        cmd = obd.commands.RPM
        response = connection.query(cmd)
        pid_data[ 'RPM' ] = response.value.magnitude
    except Exception as ex:
        logging.error('Exception RPM',ex);
        pid_data[ 'RPM' ] = -1

    try:
        cmd = obd.commands.SPEED
        response = connection.query(cmd)
        pid_data[ 'speed' ] = round(KPH2MPH( response.value.magnitude),1)
    except Exception as ex:
        logging.error('Exception SPEED',ex);
        pid_data[ 'speed' ] = -1

    try:
        cmd = obd.commands.THROTTLE_POS
        response = connection.query(cmd)
        pid_data[ 'throttlePostion' ] = round( response.value.magnitude, 1 )
    except Exception as ex:
        logging.error('Exception THROTTLE POS',ex);
        pid_data[ 'throttlePostion' ] = -1
       
    try:
        cmd = obd.commands.RUN_TIME
        response = connection.query(cmd)
        pid_data[ 'runTime_mins' ] = round(SECS2MINS( response.value.magnitude ),1)
    except Exception as ex:
        logging.error('Exception RUN TIME',ex);
        pid_data[ 'runTime_mins' ] = -1

    try:
        cmd = obd.commands.CONTROL_MODULE_VOLTAGE           
        response = connection.query(cmd)
        pid_data[ 'moduleVoltage' ] = round( response.value.magnitude, 1 )
    except Exception as ex:
        logging.error('Exception CONTROL MODULE VOLTAGE',ex);
        pid_data[ 'moduleVoltage' ] = -1

    try:
        cmd = obd.commands.RELATIVE_THROTTLE_POS
        response = connection.query(cmd)
        pid_data[ 'relativeThrottlePos' ] = round( response.value.magnitude, 1 )
    except Exception as ex:
        logging.error('Exception RELATIVE THROTTLE POS',ex);
        pid_data[ 'relativeThrottlePos' ] = -1

    try:
        cmd = obd.commands.THROTTLE_ACTUATOR
        response = connection.query(cmd)
        pid_data[ 'throttleActuator' ] = round( response.value.magnitude, 1 )
    except Exception as ex:
        logging.error('Exception THROTTLE ACTUATOR',ex);
        pid_data[ 'throttleActuator' ] = 0


#
# -----------------------------------------------------------------
def checkForDTCs (connection, mqttClient):
    logging.info( 'Checking to see if Check Enging Light is on or Diagnostic Trouble Codes are present...' )

    dtc_data[ 'topic' ] = alarm_topic
    dtc_data[ 'version' ] = version
    dtc_data[ 'dateTime' ] = time.strftime( "%FT%T%z" )

    try:
        cmd = obd.commands.GET_DTC
        response = connection.query(cmd)
        dtcCount = len(response.value)
        dtc_data[ 'dtcCount' ] = dtcCount

        #
        # Have we driven some distance with the CEL/MIL on?
        cmd = obd.commands.DISTANCE_W_MIL
        response = connection.query(cmd)
        miles=response.value.to("miles")
        dtc_data[ 'dtcDistance' ] = round(KPH2MPH(response.value.magnitude),1)

        if dtcCount > 0 or response.value.magnitude > 0.0:
            mqttClient.publish( alarm_topic, json.dumps( dtc_data ) )
            #pass

    except Exception as ex:
        logging.error( 'Error reading DTCs - exception thrown. Did we lose connectivity?', ex )

#
# -----------------------------------------------------------------
# The callback for when the mqttClient receives a CONNACK response from the server.
def on_connect (client, userdata, flags, reason_code, properties):
    logging.info( "MQTT Broker connected with result code " + str( reason_code ) )

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # mqttClient.subscribe("$SYS/#")

#
# -----------------------------------------------------------------
# The callback for when a PUBLISH message is received from the server.
def on_message (mqttClient, userdata, msg):
    logging.info( msg.topic + " " + str( msg.payload ) )


#
#
# -----------------------------------------------------------------
def send_obd_status (mqttClient, connection):
    statusData = collections.OrderedDict()

    statusData[ 'topic' ] = status_topic
    statusData[ 'version' ] = version
    statusData[ 'dateTime' ] = time.strftime( "%FT%T%z" )
    if (connection == None):
        statusData[ 'connected' ] = 'None'
    else:
        statusData[ 'connected' ] = (connection.is_connected())
    mqttClient.publish(status_topic, json.dumps(statusData))

#
# -----------------------------------------------------------------
def sendDisconnectedMessage ():
    logging.critical('Disconnected from MQTT broker')
    pass

#
# ------------------------------------------------------------------
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
    try:
        cmd = OBDCommand( "FORD_OIL_TEMP",      \
                   "Ford Engine Oil Temp",      \
                   "221310",                    \
                   2,                           \
                   temp,                        \
                   ECU.ENGINE,                  \
                   True)             # (optional) allow a "01" to be added for speed
        response = connection.query( cmd, force=True )
        logging.info( response )
        return response.value.magnitude
    except:
        logging.error('Error reading FORD Oil Temps')
        return 0

#
# ----------------------------------------------------------------
def connect_obd():
    try:
        connection = obd.OBD(start_low_power=True)
    except serial.serialutil.SerialException as ex:
        logging.critical('Serial Port Exception opening port.')
        connection = None
    except Exception as ex:
        logging.critical('Exception opening port: ', ex )
        connection = None
    else:
        if (connection.status() == OBDStatus.CAR_CONNECTED): 
            logging.info('Port is open, connection is ready!')
            logging.info('Using protocol:', connection.protocol_name())
        elif (connection.status() == OBDStatus.OBD_CONNECTED):
            logging.info('Ignition is off')
            connection = None
        elif (connection.status() == OBDStatus.ELM_CONNECTED):
            logging.info('Connected to adapter, but nothing else is working')
            connection = None
        else:
            connection = None

    return connection
    

host_name = None
host_address = None
service_info = None

#
# ----------------------------------------------------------------
def discover_mqtt_host():
    #
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
def connect_mqtt_broker(mqtt_broker_address):
    logging.debug('Connecting to {}'.format(mqtt_broker_address))
    try:
        try:
            mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except Exception as ex:
            mqttc = mqtt.Client(client_id="", clean_session=True, userdata=None)


        mqttc.on_connect = on_connect
        mqttc.on_message = on_message
        mqttc.connect(mqtt_broker_address, 1883, 60)
        mqttc.loop_start()
        return mqttc
    except Exception as ex:
        logging.critical('Unable to connect to our MQTT Broker!')
        logging.critical(ex)
        sys.exit(1)
        return None

#
# -----------------------------------------------------------------
if __name__ == "__main__":
    #time_format = "%Y-%m-%d %H:%M:%S"
    time_format = "%d%b%Y %H:%M:%S"
    logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt=time_format, filename='/tmp/obd2rv.log', level=logging.INFO)
    logging.warning('OBD2Rv v1.0')

    ## 
    ## Use argv or mDNS to connect to an MQTT Broker
    try:
        mqtt_broker_address = sys.argv[1]
    except Exception as ex:
        logging.debug( 'No host passed in on command line. Trying mDNS' )
        host = discover_mqtt_host()
        if (host is not None):
            mqtt_broker_address = host[0]
            logging.debug( 'Found MQTT Broker using mDNS on {}.{}'.format(host[0], host[1]))
        else:
            logging.warning('Unable to locate MQTT Broker using mDNS')
            try:
                mqtt_broker_address = sys.argv[1]
            except Exception as ex:
                logging.critical('mDNS failed and no MQTT Broker address passed in via command line. Exiting')
                logging.critical(ex)
                sys.exit(1)

    mqttc = connect_mqtt_broker(mqtt_broker_address)
    if (mqttc == None):
        sys.exit(1)

    try: 
        logging.info( 'Connecting to the OBD-II port...' )
        connection = connect_obd()
        if (connection == None):
            send_obd_status(mqttc,None)
            sys.exit(1)

        while 1:
            send_obd_status(mqttc,connection)
            read_PIDs(connection)
            mqttc.publish(pid_topic, json.dumps( pid_data ))
            checkForDTCs(connection, mqttc)
            if not connection.is_connected():
                break 
            else:
                time.sleep(10)

    except Exception as ex:
        send_obd_status(mqttc,None)
        logging.error('Exiting main loop on exception: ', ex )
        mqttc.loop_stop()
        mqttc.disconnect()
        try:
            connection.close()
        except:
            pass
        sys.exit(1)


