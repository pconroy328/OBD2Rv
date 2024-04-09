#!/bin/bash

MAC="13:E0:2F:8D:51:20"
PIN="1234"


pair_device() {
    #MAC=$1                      # BT MAC address
    #PIN=$2                      # PIN needed for pairing

    printf "\n"
    echo "Setup device $MAC with PIN $PIN"
    printf "\n"

    # This block will be piped to bluetoothctl line by line
    {
        printf "power on\n\n"          # Enable BT controller
        printf "scan on\n\n"           # Enable scan mode, adds discovered devices to an internal list 
        sleep 20                       # Wait a bit until we're sure that our device is discovered
        printf "scan off\n\n"          # Disable scan mode
        printf "agent on\n\n"          # Enable agent (needed for pairing)
        printf "pair $MAC\n\n"         # Start pairing process
        sleep 5                        # Wait for the 'Enter pin' prompt
        printf "$PIN\n\n"              # Send PIN           
        sleep 5                         
        printf "trust $MAC\n\n"        # Trust this device so that the PIN is not 
        sleep 5                        # needed the next time the device is accessed
        printf "quit\n\n"
    } | bluetoothctl

    
    # The 'info' command gives information about a device, among others if a device is paired and/of trusted
    
    STATUS=$(bluetoothctl info $MAC | grep yes)     

    # Check output
    if [[ $STATUS == *"Paired"* ]] && [[ $STATUS == *"Trusted"* ]] ; then
    echo "Successfully paired $MAC "
    return 0
    fi

    echo "ERROR: $MAC not succesfully paired"
    printf "\n"
    return 1
}

connect()
{
   sudo sdptool browse $MAC | grep Channel | awk '{ print $2 }'
   sudo rfcomm bind /dev/rfcomm $MAC 
   sudo chmod a+rwx /dev/rfcomm*
   rfcomm -a >> /tmp/obd2connect.txt
   ## rfcomm0: 13:E0:2F:8D:51:20 channel 1 clean 
}

while true
do
   if ! [ -e /dev/rfcomm0 ]; then
      echo "rfcomm device file not there - attempting to reconnect"
      pair_device
      connect
   fi
   sleep 5
done
