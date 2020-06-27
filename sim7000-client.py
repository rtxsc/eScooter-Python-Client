#! /bin/env python3
from __future__ import absolute_import
from geocoder.google import GoogleResult, GoogleQuery
from geocoder.location import Location
from telegram.ext import CommandHandler
from telegram.ext import Updater
from telegram.ext import MessageHandler, Filters
import logging
import requests
import telegram
import twilio
from twilio.rest import Client
import math
import os
import psutil
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
import reverse_geocoder as rg
import pprint

from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub, SubscribeListener
from pubnub.callbacks import SubscribeCallback
from pubnub.enums import PNOperationType, PNStatusCategory

from gpiozero import LED
from board import SCL, SDA
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

red = LED(20)
grn = LED(21)
procPID = ""
pid = os.getpid()
print(pid)

process_name = "python3"

def checkIfProcessRunning(processName):
    global procPID
    '''
    Check if there is any running process that contains the given name processName.
    '''
    #Iterate over the all the running process
    for proc in psutil.process_iter():
        print(proc)
        try:
            # Check if process name contains the given name string.
            if processName.lower() in proc.name().lower():
                procPID = str(proc.pid)
                # print("Python3 is affiliated with PID:" + str(proc.pid))
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

if checkIfProcessRunning(process_name):
    pid_found = "Python3 PID: "+ procPID
else:
    pid_found = "Python3 aborted"


def execute_unix(inputcommand):
    p = subprocess.Popen(inputcommand, stdout=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    return output

try:
    print("Connecting to Telegram...")
    bot = telegram.Bot(token='')
    # print(bot.get_me())
    updater = Updater(token='', use_context=True)
    dispatcher = updater.dispatcher
except telegram.error.InvalidToken:
    print("Invalid Telegram token...Restarting...")
    s = "/home/pi/./speech.sh Invalid Telegram token. Restarting..."
    execute_unix(s)
    os.execv(sys.executable, [sys.executable] + sys.argv)

try:
    print("Connecting to Twilio...")
    # Your Account Sid and Auth Token from twilio.com/console
    # DANGER! This is insecure. See http://twil.io/secure
    account_sid = ''
    auth_token = ''
    client = Client(account_sid, auth_token)
except twilio.base.exceptions.TwilioException:
    print("Invalid Twilio token...Restarting...")
    s = "/home/pi/./speech.sh Credentials are required to create a TwilioClient. Restarting..."
    execute_unix(s)
    os.execv(sys.executable, [sys.executable] + sys.argv)


# Create the I2C interface.
try:
    print("Connecting to i2c interfaces...")
    i2c = busio.I2C(SCL, SDA)
    import I2C_LCD_driver
    mylcd = I2C_LCD_driver.lcd()
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
except OSError:
    s = "/home/pi/./speech.sh Remote i-squared-c Error. Restarting..."
    execute_unix(s)
    os.execv(sys.executable, [sys.executable] + sys.argv)

data = {}
data['coordinates'] = []
geojson_list = []
geojson_index = 0
fileNum = 0
duplication = 0
saveCounter = 0


from urllib.request import urlopen
# WRITE_API = "M2U5M5J6ASD8MGZ7" #1st channel
WRITE_API = "TROIJAB24CO28C72" #2nd channel (truth table)
BASE_URL = "https://api.thingspeak.com/update?api_key={}".format(WRITE_API)

CLIENT_ID = "s1"
pnconfig = PNConfiguration()
pnconfig.subscribe_key = "sub-c-cf845704-8def-11ea-8e98-72774568d584"
pnconfig.publish_key = "pub-c-8f52ff44-41bb-422c-a0c0-a63167077c6d"
pnconfig.filter_expression = "uuid == 'client-s1'"  # ignore any payload from client-s1 (self)
# pnconfig.filter_expression = "uuid == 'web-dashboard'" # ignore any payload from web-dashboard

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
SMSalert = False
spdg = 0
userUUID = "None"

meta = {
    'my': 'meta',
    'name': 'PubNub'
}
pubnub.publish().channel(CHANNEL_ID).meta(meta).message("hello from @client"+CLIENT_ID+"Bot").sync()

def my_publish_callback(envelope, status):
    # Check whether request successfully completed or not
    if not status.is_error():
        pass  # Message successfully published to specified channel.
    else:
        pass  # Handle message publish error. Check 'category' property to find out possible issue
        # because of which request did fail.
        # Request can be resent using: [status retry];

class GoogleReverse(GoogleQuery):
    provider = 'google'
    method = 'reverse'

    _URL = 'https://maps.googleapis.com/maps/api/geocode/json'
    _RESULT_CLASS = GoogleResult
    _KEY = ''
    _KEY_MANDATORY = False

    def _location_init(self, location, **kwargs):
        return {
            'latlng': str(Location(location)),
            'sensor': 'false',
        }

class MySubscribeCallback(SubscribeCallback):
    def presence(self, pubnub, presence):
        pass  # handle incoming presence data

    def status(self, pubnub, status):
        if status.category == PNStatusCategory.PNUnexpectedDisconnectCategory:
            pass  # This event happens when radio / connectivity is lost

        elif status.category == PNStatusCategory.PNConnectedCategory:
            # Connect event. You can do stuff like publish, and know you'll get it.
            # Or just use the connected event to confirm you are subscribed for
            # UI / internal notifications, etc
            # pubnub.publish().channel(CHANNEL_ID).message("hello from MySubscribeCallback!!").pn_async(my_publish_callback)
            pass
        elif status.category == PNStatusCategory.PNReconnectedCategory:
            pass
            # Happens as part of our regular operation. This event happens when
            # radio / connectivity is lost, then regained.
        elif status.category == PNStatusCategory.PNDecryptionErrorCategory:
            pass
            # Handle message decryption error. Probably client configured to
            # encrypt messages and on live data feed it received plain text.


    def message(self, pubnub, message):
        # Handle new message stored in message.message
        global serverActivation
        global userActivation
        global userUUID
        receivedMessage = json.dumps(message.message)
        usertUUID = "Comot"
        print("PAYLOAD FROM ANYONE:{} by {}".format(receivedMessage, userUUID))

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
    global data
    global geojson_list
    # Start the serial connection SIM7000E
    # ser=serial.Serial('/dev/ttyUSB2', BAUDRATE, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=1)
    ser=serial.Serial('/dev/'+SERIAL_PORT, BAUDRATE, timeout=5, rtscts=True, dsrdtr=True)
    countFix = 0
    # Turn on the GPS
    ser.write(b"AT+CGNSPWR=1\r")
    ser.write(b"AT+CGNSPWR?\r")
    while True:
        response = ser.readline()
        if b"1" in response: # remove the whitespace before 1 for SIM7000E
            break
    # Ask for the navigation info parsed from NMEA sentences
    ser.write(b"AT+CGNSINF\r")
    countFix = 0
    while True:
            response = ser.readline()
            # Check if a fix was found
            if b"+CGNSINF: 1,1," in response:
                return True
            # If a fix wasn't found, wait and try again
            if b"+CGNSINF: 1,0," in response:
                while(countFix < 5):
                    countFix += 1
                    s = "/home/pi/./speech.sh Unable to find GPS FIX. Retrying."
                    execute_unix(s)
                    sleep(1)
                    ser.write(b"AT+CGNSINF\r")
                    response = ser.readline()
                    if b"+CGNSINF: 1,1," in response:
                        s = "/home/pi/./speech.sh Yes. Fix found!"
                        execute_unix(s)
                        return True
                    # print ("Unable to find fix. Looking for fix...")
                    mylcd.lcd_display_string("NO FIX FOUND:{}".format(countFix), 1)
                s = "/home/pi/./speech.sh Giving up. Restarting now"
                execute_unix(s)
                mylcd.lcd_clear()
                mylcd.lcd_display_string("GIVING UP", 1)
                mylcd.lcd_display_string("RESTARTING NOW", 2)

                save_geojson_to_file(fileNum)

                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                ser.write(b"AT+CGNSINF\r")

# Read the GPS data for Latitude and Longitude
def getCoord():
    global data
    global geojson_list
    global geojson_index
    global spdg
    global fileNum
    global duplication
    global saveCounter
    prevLat = 0.0
    prevLon = 0.0
    # Start the serial connection SIM7000E
    ser=serial.Serial('/dev/'+SERIAL_PORT, BAUDRATE, timeout=5, rtscts=True, dsrdtr=True)

    ser.write(b"AT+CGNSINF\r")
    while True:
        response = ser.readline()
        if b"+CGNSINF: 1," in response:
            if(geojson_index > 99):
                saveCounter += 1
                save_geojson_to_file(fileNum)
                geojson_index = 0
            # Split the reading by commas and return the parts referencing lat and long
            array = response.split(b",")
            lat = array[3]
            lon = array[4]
            prevLat = lat
            prevLon = lon
            spdg = array[6] # speed over ground variable is shared globally
            if (lat != prevLat or lon != prevLon): # only append to array if coordinates changes
                geojson_index += 1
                duplication = 0
                data['coordinates'].append({"lon" : float(lon),"lat" : float(lat)})
            else:
                duplication += 1
                print("duplication:{}".format(duplication))
                if(duplication > 10):
                    geojson_index += 1
                    data['coordinates'].append({"lon" : float(lon),"lat" : float(lat)})
                    duplication = 0
                else:
                    pass
            return (lat,lon) # return lat & lon value in byte form

# Read the GNSS Navigation Information by parsing the complete NMEA sentence
def getNavigationInfo():
    # Start the serial connection SIM7000E
    ser=serial.Serial('/dev/'+SERIAL_PORT, BAUDRATE, timeout=5, rtscts=True, dsrdtr=True)
    ser.write(b"AT+CGNSINF\r")
    datetime_objc = datetime.now()
    # print(datetime_objc)

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


            # print("MSL altitude:{}m = {}ft".format(altd,round(float(altd)/0.3048),4))
            # print("Speed over Ground:{} km/h".format(spdg))
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
    distance = round(R * c)
    if(distance > 10000):
        distance = 0
    print("-->Distance from current location to start coordinates: {} KM".format(distance))
    return distance

def main_without_pppd():
    pubnub.add_listener(MySubscribeCallback())
    global index
    global geojson_index
    global serverActivation
    global userActivation
    global scooterAlarm
    global SMSalert
    global spdg

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

        print("Stream index:{} \n".format(index))
        # print("server act payload:{}".format(serverActivation))
        # print("user act payload:{}".format(userActivation))

        # do the logic for anti-theft system here
        #  /__\  ( \( )(_  _)(_  _)    (_  _)( )_( )( ___)( ___)(_  _)
        # /(  )\  )  (   )(   _)(_       )(   ) _ (  )__)  )__)   )(
        #(__)(__)(_)\_) (__) (____)     (__) (_) (_)(____)(_)    (__)
        # if(userActivation):
        #     u_act_payload = "u_act_1"
        # else:
        #     u_act_payload = "u_act_0"
        #
        # print("U_ACT_FROM_S PAYLOAD:{}".format(u_act_payload))

        s1_activated = (serverActivation and userActivation)

        if s1_activated:
            red.off()
            grn.on()
            Nearby = True
            if not idle_flag:
                idle_flag = True
                idle_end = perf_counter()
                idle_time = idle_end - idle_start
                # print("/////////////{} was IDLE for {} sec".format(CLIENT_ID,idle_time))
                active_flag = True
                start_coordinate_set = False
                stop_coordinate_set = True
                s = "/home/pi/./speech.sh client-s1 is activated!"
                execute_unix(s)

            if active_flag:
                active_start = perf_counter()
                active_flag = False
            # print("Scooter {} is now active for {:.1f} sec".format(CLIENT_ID,perf_counter()-active_start))

        else:
            red.on()
            grn.off()
            Nearby = False
            if idle_flag:
                idle_start = perf_counter()
                idle_flag = False
            # print("Scooter {} is now idle for {:.1f} sec".format(CLIENT_ID,perf_counter()-idle_start))

            if not active_flag:
                active_end = perf_counter()
                active_time = active_end - active_start
                # print("/////////////{} was ACTIVE for {} sec".format(CLIENT_ID,active_time))
                active_flag = True
                start_coordinate_set = True
                stop_coordinate_set = False
                s = "/home/pi/./speech.sh client-s1 has been deactivated!"
                execute_unix(s)


        # print("ACTIVATION_client-{}:{}".format(CLIENT_ID,s1_activated))

        # Make sure there's a GPS fix
        if checkForFix():
            index+=1  # publish counter
            # groundSpeed = getNavigationInfo()
            gndSpeed = float(spdg)

            if gndSpeed != 0.0: # if speed is not 0 km/h, scooter is moving
                s1_moved = 1
            else:
                s1_moved = 0


            """
            f1 = Server Act /
            f2 = User Act /
            f3 = Nearby X
            f4 = Activated /
            f5 = Moved /
            f6 = Speed /
            f7 = Alarm /
            f8 = SMS / using Twilio and Telegram
            """

            # payload = serverActivation,userActivation,Nearby,s1_activated,s1_moved,gndSpeed,scooterAlarm,SMSalert

            thingspeakHttp = BASE_URL + "&field1={:.2f}&field2={:.2f}&field3={:.2f}&field4={:.2f}&field5={:.2f}&field6={:.2f}&field7={:.2f}&field8={:.2f}".format(serverActivation,userActivation,Nearby,s1_activated,s1_moved,gndSpeed,scooterAlarm,SMSalert)
            conn = urlopen(thingspeakHttp)
            conn.close()

            # print("standby_alarm_S1:{}".format(scooterAlarm))
            # Get lat and long
            if getCoord():
                latitude, longitude = getCoord() # live coordinates
                current_coordinate = float(longitude),float(latitude)
                locateMePlease = float(latitude),float(longitude)

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


                if not s1_activated and s1_moved:
                    scooterAlarm = 1
                    SMSalert = True
                    s = "/home/pi/./speech.sh Unauthorised usage detected!Sending SMS and Telegram Alert"
                    execute_unix(s)
                    # reverseGeocode(locateMePlease)
                    result = GoogleReverse((float(latitude), float(longitude)))
                    telegram_bot_sendtext("\
                    Unauthorised Usage of @clientsS1Bot\n\
                    Here are the location info:\n\
                    Last seen coordinate:{}\n\
                    Address:{}".format(locateMePlease,str(result.address)))

                    message = client.messages \
                                    .create(
                                         body="\
                                         Unauthorised Usage of @clientsS1Bot\n\nHere are the location info:\n\nLast seen coordinate:{}\n\nAddress:{}".format(locateMePlease,str(result.address)),
                                         from_='+12058102291',
                                         to='+60198285105' # '+15558675310'
                                     )

                    print(message.sid)

                else:
                    scooterAlarm = 0
                    SMSalert = False

                # coord = "lat:" + str(latitude) + "," + "lng:" + str(longitude)
                # print (coord)
                print("start location:{}".format(s1_start_coordinate))
                print("current location:{}".format(current_coordinate))
                print("stop location:{}".format(s1_stop_coordinate))
                distance = calcDistance(current_coordinate[0],current_coordinate[1],s1_start_coordinate[0],s1_start_coordinate[1])
                if(distance > 10000):
                    distance = 0

                """
                S0 U0 A0 ALF D00    /16
                000 V00 M0 F0000    /16
                """
                mylcd.lcd_clear()
                mylcd.lcd_display_string("S", 1)
                mylcd.lcd_display_string_pos(str(serverActivation),1,1) #S:0 U:0 A:0 AL:0
                mylcd.lcd_display_string_pos("U",1,3)
                mylcd.lcd_display_string_pos(str(userActivation),1,4)
                mylcd.lcd_display_string_pos("A",1,6)
                mylcd.lcd_display_string_pos(str(s1_activated),1,7)
                mylcd.lcd_display_string_pos("AL",1,9)
                mylcd.lcd_display_string_pos(str(scooterAlarm),1,11)
                mylcd.lcd_display_string_pos("D",1,13)
                mylcd.lcd_display_string_pos(str(distance),1,14)
                mylcd.lcd_display_string_pos(str(index),2,0)
                mylcd.lcd_display_string_pos("V",2,4)
                mylcd.lcd_display_string_pos(str(int(gndSpeed)),2,5)
                mylcd.lcd_display_string_pos("M",2,8)
                mylcd.lcd_display_string_pos(str(s1_moved),2,9)
                mylcd.lcd_display_string_pos("G",2,11)
                mylcd.lcd_display_string_pos(str(geojson_index),2,12)
                mylcd.lcd_display_string_pos(str(saveCounter),2,14)
                # create JSON dictionary (payload)
                if(index<2):
                    ipv4,ipv6 = getPublicIP()

                payload =       {
                                CLIENT_ID+"_index":         float(index),
                                CLIENT_ID+"_mac_address":   getMAC(),
                                CLIENT_ID+"_local_ipv4":    getLocalIP(),
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

                """
                {"s1_public_ipv4":"14.192.209.6",
                "s1_moved":false,
                "s1_mac_address":"b8:27:eb:a5:f8:a5",
                "s1_mileage":12277.5910140142,
                "s1_longitude":110.388507,
                "s1_stop_coord":[110.388507,1.583223],
                "s1_latitude":1.583223,
                "s1_start_coord":[0,0],
                "s1_index":10,"s1_speed":0,
                "s1_active_time":0,
                "s1_idle_time":0,
                "s1_alarm":false,
                "s1_public_ipv6":"2001:d08:e2:7dbf:4bd0:dd67:ba08:5668",
                "s1_uuid":"client-s1",
                "s1_last_known":[110.388507,1.583223],
                "s1_activated":false}

                """

                pubnub.publish().channel(CHANNEL_ID).message(payload).pn_async(publish_callback)
                # print("\nNext stream in:\n")
                for c in range(STREAM_DELAY): # default to 5
                    sleep(SECONDS_BETWEEN_READS)

def getMAC():
    return (':'.join(re.findall('..', '%012x' % uuid.getnode())))

def getPublicIP():
    ipv4 = get('https://api.ipify.org').text
    ipv6 = get('https://api6.ipify.org').text
    # print("Public IPv4:".format(ipv4))
    # print("Public IPv6:".format(ipv6))
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
        # print("Local IPv4:".format(IP))

    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP



def save_geojson_to_file(fileNum):
    global data
    global geojson_list
    num = 0
    with open('/home/pi/eScooter-Python-Client/geojson/data{}.txt'.format(fileNum), 'w') as outfile:
        json.dump(data, outfile)

    with open('/home/pi/eScooter-Python-Client/geojson/data{}.txt'.format(fileNum)) as json_file:
        data = json.load(json_file)
        for p in data['coordinates']:
            num += 1
            # print('['+str(p['lon'])+","+str(p['lat'])+'],' + "New Coordinate Points:{}".format(num))
            # stringify = str(str(p['lon'])+","+str(p['lat']))
            stringify = str('['+str(p['lon'])+","+str(p['lat'])+'],')
            # # collect this format into another array
            geojson_list.append(stringify)
            # print("Total GEOJSON point:{}".format(len(geojson_list)))
        # print(geojson_list)
    with open('/home/pi/eScooter-Python-Client/geojson/geojson{}.txt'.format(fileNum), 'w') as outfile:
        json.dump(geojson_list, outfile)

def reverseGeocode(coordinates):
	result = rg.search(coordinates)
	# result is a list containing ordered dictionary.
	pprint.pprint("Last seen location found:{}".format(result))

def telegram_bot_sendtext(bot_message):

    bot_token = '1242269165:AAHDaelCeHjZBAvFyOxHrgXjwo2SxYzT1PY'
    bot_chatID = '662382293'
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
    response = requests.get(send_text)
    return response.json()

def getLocation(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="My current location is:{}")


if __name__ == "__main__":
    try:
        mylcd.lcd_display_string("Client-S1 Init", 1)
        mylcd.lcd_display_string(getSSID(), 2)
        sleep(1)
        # Shell scripts for system monitoring from here:
        # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
        cmd = "hostname -I | cut -d' ' -f1"
        IP = subprocess.check_output(cmd, shell=True).decode("utf-8")
        ssid = getSSID()
        draw.text((x, top + 0), "IP: " + IP, font=font, fill=255)
        draw.text((x, top + 8), ssid, font=font, fill=255)
        draw.text((x, top + 16), "PID:" + str(pid), font=font, fill=255)
        draw.text((x, top + 24), pid_found, font=font, fill=255)
        # Display image.
        disp.image(image)
        disp.show()
        # c = "espeak -ven-us -ven+m7 'Initializing Client' --stdout | aplay"
        s = "/home/pi/./speech.sh Initializing GNSS"
        execute_unix(s)

        # print("client-{} is connected to {}".format(CLIENT_ID,getSSID()))
        hostname = socket.gethostname()
        # print("hostname:{}".format(hostname))
        ip = getLocalIP();
        if(index<1):
            # print("perform this getPublicIP() check only once!")
            ipv4,ipv6 = getPublicIP()
        else:
            pass
        # print("MAC address:{}".format(getMAC()))



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
        getLocationHandler = CommandHandler('location', getLocation)
        dispatcher.add_handler(getLocationHandler)
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)
        updater.start_polling()
        telegram_bot_sendtext("@clientsS1Bot is initializing!")
        main_without_pppd()
    except RuntimeError:
        s = "/home/pi/./speech.sh Runtime Error Detected! Restarting now..."
        execute_unix(s)
        mylcd.lcd_clear()
        mylcd.lcd_display_string("RUNTIME ERROR", 1)
        os.execv(sys.executable, [sys.executable] + sys.argv)

    except OSError:
        s = "/home/pi/./speech.sh Remote I O Error. Restarting..."
        execute_unix(s)
        os.execv(sys.executable, [sys.executable] + sys.argv)

    except KeyboardInterrupt:
        telegram_bot_sendtext("@clientsS1Bot is going offline!")
        save_geojson_to_file(fileNum)
        s = "/home/pi/./speech.sh Shutting down"
        execute_unix(s)
        mylcd.lcd_clear()
        mylcd.lcd_display_string("BYE BYE", 1)
        mylcd.lcd_display_string("Shutting Down", 2)
        sleep(1)
        print("Turning off GPS for client-{}\n".format(CLIENT_ID))
