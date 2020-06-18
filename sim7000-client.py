#! /bin/env python3
import math
import os
import sys
from os import system
import serial
import subprocess
from time import sleep,perf_counter
import distutils.util
from datetime import datetime
import json
import socket
from requests import get # to get Public IP address
import uuid, re # to get MAC address

import pubnub
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.callbacks import SubscribeCallback
from pubnub.enums import PNOperationType, PNStatusCategory

from board import SCL, SDA
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
# Create the I2C interface.
i2c = busio.I2C(SCL, SDA)

disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)
# Clear display.
disp.fill(0)
disp.show()
# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new("1", (width, height))
# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)
# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=0)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height - padding
#Move left to right keeping track of the current x position for drawing shapes.
x = 0
# Load default font.
font = ImageFont.load_default()
# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=0)

import I2C_LCD_driver
from urllib.request import urlopen
WRITE_API = "M2U5M5J6ASD8MGZ7"
BASE_URL = "https://api.thingspeak.com/update?api_key={}".format(WRITE_API)

ThingSpeakPrevSec = 0
ThingSpeakInterval = 20 # 20 seconds

CLIENT_ID = "s1"
pnconfig = PNConfiguration()
pnconfig.subscribe_key = "sub-c-cf845704-8def-11ea-8e98-72774568d584"
pnconfig.publish_key = "pub-c-8f52ff44-41bb-422c-a0c0-a63167077c6d"
pnconfig.filter_expression = "uuid == 'client-s1'" # only subscribe to messages containing this meta
pnconfig.uuid = "client-"+CLIENT_ID
pnconfig.ssl = False
pubnub = PubNub(pnconfig)
CHANNEL_ID = "robotronix"

SERIAL_PORT = 'ttyUSB2'
BAUDRATE = 115200
SECONDS_BETWEEN_READS = 1
STREAM_DELAY = 1
INIT_DELAY = 1
index = 0
stream_index = 0
DATA_POINT = 2 # GPS lat/lgt recorded before transmission
s1_activated = False
s1_moved = False
scooterAlarm = False
serverActivation = 0
userActivation = 0

meta = {
    'my': 'meta',
    'name': 'PubNub'
}

pubnub.publish().channel(CHANNEL_ID).meta(meta).message("hello from client-"+CLIENT_ID).sync()

class MySubscribeCallback(SubscribeCallback):
    def status(self, pubnub, status):
        # The status object returned is always related to subscribe but could contain
        # information about subscribe, heartbeat, or errors
        # use the operationType to switch on different options
        if status.operation == PNOperationType.PNSubscribeOperation \
                or status.operation == PNOperationType.PNUnsubscribeOperation:
            if status.category == PNStatusCategory.PNConnectedCategory:
                pass
                # This is expected for a subscribe, this means there is no error or issue whatsoever
            elif status.category == PNStatusCategory.PNReconnectedCategory:
                pass
                # This usually occurs if subscribe temporarily fails but reconnects. This means
                # there was an error but there is no longer any issue
            elif status.category == PNStatusCategory.PNDisconnectedCategory:
                pass
                # This is the expected category for an unsubscribe. This means there
                # was no error in unsubscribing from everything
            elif status.category == PNStatusCategory.PNUnexpectedDisconnectCategory:
                pass
                # This is usually an issue with the internet connection, this is an error, handle
                # appropriately retry will be called automatically
            elif status.category == PNStatusCategory.PNAccessDeniedCategory:
                pass

                # This means that PAM does not allow this client to subscribe to this
                # channel and channel group configuration. This is another explicit error
            else:
                pass
                # This is usually an issue with the internet connection, this is an error, handle appropriately
                # retry will be called automatically
        elif status.operation == PNOperationType.PNSubscribeOperation:
            # Heartbeat operations can in fact have errors, so it is important to check first for an error.
            # For more information on how to configure heartbeat notifications through the status
            # PNObjectEventListener callback, consult http://www.pubnub.com/docs/python/api-reference-configuration#configuration
            if status.is_error():
                pass
                # There was an error with the heartbeat operation, handle here
            else:
                pass
                # Heartbeat operation was successfu
        else:
            pass
            # Encountered unknown status type

    def presence(self, pubnub, presence):
        pass  # handle incoming presence data

    def message(self, pubnub, message):
        global serverActivation
        global userActivation
        receivedMessage = json.dumps(message.message)
        # print(receivedMessage)
        if "askingForAck" in receivedMessage:
            print("REQUEST RECEIVED!")
            payload = { "handshakeAck" : True}
            print("handshakeAck from server to user:{}".format(payload))
            pubnub.publish().channel(CHANNEL_ID).message(payload).pn_async(publish_callback)
            
        if "s_act" in receivedMessage:
            if "s_act_1" in receivedMessage:
                serverActivation = 1
            else:
                serverActivation = 0

        if "u_act_from_s" in receivedMessage:
            # logic for handshake

            if "u_act_1" in receivedMessage:
                userActivation = 1
            else:
                userActivation = 0

        if "u_act_from_API" in receivedMessage:
            # logic for handshake
            if "u_act_1" in receivedMessage:
                userActivation = 1
            else:
                userActivation = 0

        pass  # handle incoming messages

    def signal(self, pubnub, signal):
        print(signal.signal)
        pass # handle incoming signals



def here_now_callback(result, status):
    if status.is_error():
        # handle error
        return

    for channel_data in result.channels:
        print("---")
        print("channel: %s" % channel_data.channel_name)
        print("occupancy: %s" % channel_data.occupancy)
        print("occupants: %s" % channel_data.channel_name)

    for occupant in channel_data.occupants:
        print("uuid: %s, state: %s" % (occupant.uuid, occupant.state))


def str2bool_util(inp):
    str2int = distutils.util.strtobool(inp)
    boolean = bool(str2int)
    return boolean

def publish_callback(result, status):
    pass
    # Handle PNPublishResult and PNStatus
# Start PPPD
def openPPPD():
    # Check if PPPD is already running by looking at syslog output
    print("Opening PPPD...")
    output1 = subprocess.check_output("cat /var/log/syslog | grep pppd | tail -1", shell=True)
    if "secondary DNS address" not in output1 and "locked" not in output1:
        while True:
            # Start the "fona" process
            print("starting fona process...")
            subprocess.call("sudo pon fona", shell=True)
            sleep(2)
            output2 = subprocess.check_output("cat /var/log/syslog | grep pppd | tail -1", shell=True)
#             print(output2)
            if "script failed" not in output2:
                break
#     # Make sure the connection is working
    while True:
        print("Connection check...")
        output2 = subprocess.check_output("cat /var/log/syslog | grep pppd | tail -1", shell=True)
#         output3 = subprocess.check_output("cat /var/log/syslog | grep pppd | tail -3", shell=True)
#         print("Out2:{}".format(output2))
#         print("Out3:{}".format(output3))
#         if "secondary DNS address" in output2 or "DNS address" in output3:
        if "secondary DNS address" in output2:
            print("Connection is ready...Device is online...")
            return True

# Stop PPPD
def closePPPD():
    print ("\nTurning off cell connection using sudo poff fona...")
    # Stop the "fona" process
    subprocess.call("sudo poff fona", shell=True)
    # Make sure connection was actually terminated
    while True:
        output = subprocess.check_output("cat /var/log/syslog | grep pppd | tail -1", shell=True)
        if "Exit" in output:
            print("pppd is now close...")
            return True

# Check for a GPS fix
def checkForFix():
    # Start the serial connection SIM7000E
    # ser=serial.Serial('/dev/ttyUSB2', BAUDRATE, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=1)
    ser=serial.Serial('/dev/'+SERIAL_PORT, BAUDRATE, timeout=5, rtscts=True, dsrdtr=True)

    # Turn on the GPS
    ser.write(b"AT+CGNSPWR=1\r")
    ser.write(b"AT+CGNSPWR?\r")
    while True:
        response = ser.readline()
        if b"1" in response: # remove the whitespace before 1 for SIM7000E
            break
    # Ask for the navigation info parsed from NMEA sentences
    ser.write(b"AT+CGNSINF\r")
    while True:
            response = ser.readline()
            # Check if a fix was found
            if b"+CGNSINF: 1,1," in response:
                return True
            # If a fix wasn't found, wait and try again
            if b"+CGNSINF: 1,0," in response:
                s = "/home/pi/./speech.sh Unable to find GPS FIX. Restarting now"
                execute_unix(s)
                sleep(5)
                ser.write(b"AT+CGNSINF\r")
                print ("Unable to find fix. still looking for fix...")
                mylcd = I2C_LCD_driver.lcd()
                mylcd.lcd_display_string("NO FIX FOUND", 1)
                mylcd.lcd_display_string("RESTARTING...", 2)
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                ser.write(b"AT+CGNSINF\r")

# Read the GPS data for Latitude and Longitude
def getCoord():
    # Start the serial connection SIM7000E
    # ser=serial.Serial('/dev/ttyUSB2', BAUDRATE, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=1)
    ser=serial.Serial('/dev/'+SERIAL_PORT, BAUDRATE, timeout=5, rtscts=True, dsrdtr=True)

    ser.write(b"AT+CGNSINF\r")
    while True:
        response = ser.readline()
        if b"+CGNSINF: 1," in response:
            # Split the reading by commas and return the parts referencing lat and long
            array = response.split(b",")
            lat = array[3]
            lon = array[4]
            # thingspeakHttp = BASE_URL + "&field2={:.2f}&field3={:.2f}".format(float(lat), float(lon))
            # print(thingspeakHttp)
            # conn = urlopen(thingspeakHttp)
            # print("Response: {}".format(conn.read()))
            # conn.close()
            # print lon
            return (lat,lon) # return lat & lon value in byte form

# Read the GNSS Navigation Information by parsing the complete NMEA sentence
def getNavigationInfo():
    # Start the serial connection SIM7000E
    # ser=serial.Serial('/dev/ttyUSB2', BAUDRATE, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=1)
    ser=serial.Serial('/dev/'+SERIAL_PORT, BAUDRATE, timeout=5, rtscts=True, dsrdtr=True)

    ser.write(b"AT+CGNSINF\r")
    datetime_objc = datetime.now()
    print(datetime_objc)

    while True:
        response = ser.readline()
        if b"+CGNSINF: 1," in response:
            # Split the reading by commas
            array = response.split(b",")
            grun = array[0] # GNSS run status
            sfix = array[1] # Fix status
            utct = array[2] # UTC date & time
            clat = array[3] # latitude
            clon = array[4] # longitude
            altd = array[5] # MSL altitude
            spdg = array[6] # speed over ground
            csog = array[7] # course over ground
            mfix = array[8] # fix mode
            rsv1 = array[9] # reserved1
            hdop = array[10] # HDOP horizontal dilution of precision
            pdop = array[11] # PDOP position (3D) dilution of precision
            vdop = array[12] # VDOP vertical dilution of precision
            rsv2 = array[13] # reserved2
            gnsv = array[14] # GNSS Satellites in View
            gnsu = array[15] # GNSS Satellites in Use
            glns = array[16] # GLONASS Satellites Used
            rsv3 = array[17] # reserved3
            cnom = array[18] # C/N0 max
            hpa0 = array[19] # Horizontal Position Accuracy
            vpa0 = array[20] # Vertical Position Accuracy

            thingspeakHttp = BASE_URL + "&field4={:.2f}&field5={:.2f}".format(float(gnsv),float(gnsu))
            print(thingspeakHttp)
            conn = urlopen(thingspeakHttp)
            # print("Response: {}".format(conn.read()))
            conn.close()

            thingspeakHttp = BASE_URL + "&field6={:.2f}&field7={:.2f}".format(float(glns),float(hpa0))
            print(thingspeakHttp)
            conn = urlopen(thingspeakHttp)
            # print("Response: {}".format(conn.read()))
            conn.close()

            # thingspeakHttp = BASE_URL + "&field8={:.2f}".format(float(spdg))
            # print(thingspeakHttp)
            # conn = urlopen(thingspeakHttp)
            # print("Response: {}".format(conn.read()))
            # conn.close()

            # print("MSL altitude:{}m = {}ft".format(altd,round(float(altd)/0.3048),4))
            print("Speed over Ground:{} km/h".format(spdg))
            # print("Course over Ground:{} degrees".format(csog))
            # print("HDOP:{}".format(hdop))
            # print("PDOP:{}".format(pdop))
            # print("VDOP:{}".format(vdop))
            # print("C/N0 max:{} dBHz".format(cnom))
            # print("HPA:{} m".format(hpa0))
            # print("VPA:{} m".format(vpa0))
            # print("GNSS Satellites in View:{}".format(gnsv))
            # print("GNSS Satellites in Use:{}".format(gnsu))
            # print("GLONASS in Use:{}".format(glns))

            return spdg

def main_with_pppd():
    pass

def calcDistance(lon1,lat1,lon2,lat2):
    R = 6373.0 # radius of the Earth in KM

    # coordinates
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    # change in coordinates
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    print("------------------------------------------>Distance: {} KM".format(distance))
    return distance

def main_without_pppd():
    global index
    global serverActivation
    global userActivation
    start_coordinate_set = False
    stop_coordinate_set = False
    s1_last_seen = 0,0
    s1_start_coordinate = 0,0
    s1_stop_coordinate = 0,0


    idle_time = 0.0
    active_time = 0.0
    idle_flag = True
    active_flag = True

    for c in range(INIT_DELAY):
        print ("Starting in T-minus {} second".format(INIT_DELAY-c))
        sleep(1)

    while True:
        # start listening to the channel from incoming messages
        pubnub.subscribe()\
        .channels(CHANNEL_ID)\
        .with_presence()\
        .execute()

        # pubnub.here_now()\
        # .channels(CHANNEL_ID)\
        # .include_uuids(True)\
        # .pn_async(here_now_callback)

        print("\n\nStream index:{} \n".format(index))
        # print("server act payload:{}".format(serverActivation))
        # print("user act payload:{}".format(userActivation))

        # do the logic for anti-theft system here
        #  /__\  ( \( )(_  _)(_  _)    (_  _)( )_( )( ___)( ___)(_  _)
        # /(  )\  )  (   )(   _)(_       )(   ) _ (  )__)  )__)   )(
        #(__)(__)(_)\_) (__) (____)     (__) (_) (_)(____)(_)    (__)
        if(userActivation):
            u_act_payload = "u_act_1"
        else:
            u_act_payload = "u_act_0"

        print("U_ACT_FROM_S PAYLOAD:{}".format(u_act_payload))

        s1_activated = (serverActivation and userActivation)

        # thingspeakHttp = BASE_URL + "&field1={:.2f}".format(s1_activated)
        # print(thingspeakHttp)
        # conn = urlopen(thingspeakHttp)
        # print("Response: {}".format(conn.read()))
        # conn.close()
        if s1_activated:
            if not idle_flag:
                idle_flag = True
                idle_end = perf_counter()
                idle_time = idle_end - idle_start
                print("/////////////{} was IDLE for {} sec".format(CLIENT_ID,idle_time))
                active_flag = True
                start_coordinate_set = False
                stop_coordinate_set = True
                s = "/home/pi/./speech.sh client-s1 is activated!"
                execute_unix(s)


            if active_flag:
                active_start = perf_counter()
                active_flag = False
            print("Scooter {} is now active for {:.1f} sec".format(CLIENT_ID,perf_counter()-active_start))

        else:
            if idle_flag:
                idle_start = perf_counter()
                idle_flag = False
            print("Scooter {} is now idle for {:.1f} sec".format(CLIENT_ID,perf_counter()-idle_start))

            if not active_flag:
                active_end = perf_counter()
                active_time = active_end - active_start
                print("/////////////{} was ACTIVE for {} sec".format(CLIENT_ID,active_time))
                active_flag = True
                start_coordinate_set = True
                stop_coordinate_set = False
                s = "/home/pi/./speech.sh client-s1 has been deactivated!"
                execute_unix(s)


        print("ACTIVATION_client-{}:{}".format(CLIENT_ID,s1_activated))


        # Make sure there's a GPS fix
        if checkForFix():

            groundSpeed = getNavigationInfo()
            gndSpeed = float(groundSpeed)

            if gndSpeed is not 0.0:
                s1_moved = 0
            else:
                s1_moved = 1

            if not s1_activated and s1_moved:
                scooterAlarm = True
                s = "/home/pi/./speech.sh Unauthorised usage. Do not move the scooter without proper authorization."
                execute_unix(s)

            else:
                scooterAlarm = False

            print("standby_alarm_S1:{}".format(scooterAlarm))
            # Get lat and long
            if getCoord():
                index+=1
                latitude, longitude = getCoord() # live coordinates
                current_coordinate = float(longitude),float(latitude)

                if not s1_activated:
                    s1_last_seen = float(longitude),float(latitude)
                    if not stop_coordinate_set:
                        s1_stop_coordinate = s1_last_seen
                    else:
                        pass
                else:
                    if not start_coordinate_set:
                        s1_start_coordinate = s1_last_seen
                    else:
                        pass

                # coord = "lat:" + str(latitude) + "," + "lng:" + str(longitude)
                # print (coord)
                print("start location:{}".format(s1_start_coordinate))
                print("current location:{}".format(current_coordinate))
                print("stop location:{}".format(s1_stop_coordinate))
                distance = calcDistance(current_coordinate[0],current_coordinate[1],s1_start_coordinate[0],s1_start_coordinate[1])


                mylcd.lcd_clear()
                mylcd.lcd_display_string("S:", 1)
                mylcd.lcd_display_string_pos(str(serverActivation),1,2) #S:0 U:0 A:0 AL:0
                mylcd.lcd_display_string_pos("U:",1,4)
                mylcd.lcd_display_string_pos(str(userActivation),1,6)
                mylcd.lcd_display_string_pos("A:",1,8)
                mylcd.lcd_display_string_pos(str(s1_activated),1,10)
                mylcd.lcd_display_string_pos("AL:",1,12)
                mylcd.lcd_display_string_pos(str(scooterAlarm),1,15)
                mylcd.lcd_display_string("U:", 2)
                mylcd.lcd_display_string_pos(str(index),2,2) #U:000__
                mylcd.lcd_display_string_pos("V:",2,6) #U:000 V:0.0_M:
                mylcd.lcd_display_string_pos(str(gndSpeed),2,8) #U:000 V:0.0_M:
                mylcd.lcd_display_string_pos("M:",2,12) #U:000 V:0.0_M:
                mylcd.lcd_display_string_pos(str(s1_moved),2,14) #U:0 V:0.0 M:0
                # create JSON dictionary (payload)
                if(index<2):
                    ipv4,ipv6 = getPublicIP()

                payload =       {
                                CLIENT_ID+"_index":         float(index),
                                CLIENT_ID+"_mac_address":   getMAC(),
                                CLIENT_ID+"_public_ipv4":   ipv4,
                                CLIENT_ID+"_public_ipv6":   ipv6,
                                CLIENT_ID+"_uuid":          pubnub.uuid,
                                CLIENT_ID+"_speed":         float(gndSpeed),
                                CLIENT_ID+"_latitude":      float(latitude),
                                CLIENT_ID+"_longitude":     float(longitude),
                                CLIENT_ID+"_activated":     bool(s1_activated),
                                CLIENT_ID+"_moved":         bool(s1_moved),
                                CLIENT_ID+"_alarm":         bool(scooterAlarm),
                                CLIENT_ID+"_last_known":    s1_last_seen,
                                CLIENT_ID+"_start_coord":   s1_start_coordinate,
                                CLIENT_ID+"_stop_coord":    s1_stop_coordinate,
                                CLIENT_ID+"_mileage":       distance,
                                CLIENT_ID+"_idle_time":     idle_time,
                                CLIENT_ID+"_active_time":   active_time
                                # "u_act":                    u_act_payload

                                }
                pubnub.publish().channel(CHANNEL_ID).message(payload).pn_async(publish_callback)

                print("\nNext stream in:\n")
                for c in range(STREAM_DELAY): # default to 5
                    sleep(SECONDS_BETWEEN_READS)

def getMAC():
    return (':'.join(re.findall('..', '%012x' % uuid.getnode())))

def getPublicIP():
    ipv4 = get('https://api.ipify.org').text
    ipv6 = get('https://api6.ipify.org').text
    print("Public IPv4:".format(ipv4))
    print("Public IPv6:".format(ipv6))
    return ipv4,ipv6

def getSSID():
    try:
        output = subprocess.check_output(['sudo', 'iwgetid'],universal_newlines=True)
        ssid = output.split('"')[1]
        return ssid
    except Exception:
        pass

def getLocalIP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
        print("Local IPv4:".format(IP))

    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def execute_unix(inputcommand):
    p = subprocess.Popen(inputcommand, stdout=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    return output




if __name__ == "__main__":
    try:

        # Shell scripts for system monitoring from here:
        # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
        cmd = "hostname -I | cut -d' ' -f1"
        IP = subprocess.check_output(cmd, shell=True).decode("utf-8")
        draw.text((x, top + 0), "IP: " + IP, font=font, fill=255)
        # Display image.
        disp.image(image)
        disp.show()
        # c = "espeak -ven-us -ven+m7 'Initializing Client' --stdout | aplay"
        s = "/home/pi/./speech.sh Initializing GNSS"
        execute_unix(s)

        print("client-{} is connected to {}".format(CLIENT_ID,getSSID()))
        hostname = socket.gethostname()
        print("hostname:{}".format(hostname))
        ip = getLocalIP();
        if(index<1):
            print("perform this getPublicIP() check only once!")
            ipv4,ipv6 = getPublicIP()
        else:
            pass
        print("MAC address:{}".format(getMAC()))

        mylcd = I2C_LCD_driver.lcd()
        mylcd.lcd_display_string("Connected to:", 1)
        mylcd.lcd_display_string(getSSID(), 2)
        sleep(1)

        mylcd.lcd_clear()
        mylcd.lcd_display_string("Public IPv4:", 1)
        mylcd.lcd_display_string(ipv4, 2)
        sleep(1)

        mylcd.lcd_clear()
        mylcd.lcd_display_string("Local IPv4:", 1)
        mylcd.lcd_display_string(ip, 2)
        sleep(1)

        mylcd.lcd_clear()
        mylcd.lcd_display_string(getSSID(), 1)
        mylcd.lcd_display_string(ip, 2)
        sleep(1)

        pubnub.add_listener(MySubscribeCallback())
        main_without_pppd()
    except KeyboardInterrupt:
        s = "/home/pi/./speech.sh Shutting down"
        execute_unix(s)
        mylcd.lcd_clear()
        mylcd.lcd_display_string("BYE BYE", 1)
        mylcd.lcd_display_string("Shutting Down", 2)
        sleep(1)
        print("Turning off GPS for client-{}\n".format(CLIENT_ID))
