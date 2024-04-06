import obd
#obd.debug.console = True
connection = obd.OBD() # auto-connects to USB or RF port

cmd = obd.commands.FUEL_LEVEL # select an OBD command (sensor)
response = connection.query(cmd) # send the command, and parse the response
print('fuel level')
print(response.value)
print(response.unit)
print('')


cmd = obd.commands.INTAKE_TEMP # select an OBD command (sensor)
response = connection.query(cmd) # send the command, and parse the response
print('intake temp')
print(response.value)
print(response.unit)
print('')


cmd = obd.commands.AMBIANT_AIR_TEMP # select an OBD command (sensor)
response = connection.query(cmd) # send the command, and parse the response
print('ambient temp')
print(response.value)
print(response.unit)
print('')


cmd = obd.commands.COOLANT_TEMP # select an OBD command (sensor)
response = connection.query(cmd) # send the command, and parse the response
print('coolant temp')
print(response.value)
print(response.unit)
print('')

cmd = obd.commands.RPM # select an OBD command (sensor)
response = connection.query(cmd) # send the command, and parse the response
print('RPM')
print(response.value)
print(response.unit)
print('')

cmd = obd.commands.SPEED # select an OBD command (sensor)
response = connection.query(cmd) # send the command, and parse the response
print('speed')
print(response.value)
print(response.unit)
print('')

r = connection.query(obd.commands.GET_DTC)
print(r.value)
