import obd
##obd.debug.console = True
obd.logger.setLevel(obd.logging.DEBUG) # enables all debug information

connection = obd.OBD() # auto-connects to USB or RF port

cmd = obd.commands.RPM # select an OBD command (sensor)

response = connection.query(cmd) # send the command, and parse the response

print(response.value)
print(response.unit)


