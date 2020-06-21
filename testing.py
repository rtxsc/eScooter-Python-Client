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

CLIENT_ID = "s1"
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
data = {}
data['coordinates'] = []
geojson_list = []

def main_without_pppd():
    global index
    global serverActivation
    global userActivation
    start_coordinate_set = False
    stop_coordinate_set = False
    s1_last_seen = 0,0
    s1_start_coordinate = 0,0
    s1_stop_coordinate = 0,0
    fileNum = 0

    idle_time = 0.0
    active_time = 0.0
    idle_flag = True
    active_flag = True

    for c in range(INIT_DELAY):
        print ("Starting in T-minus {} second".format(INIT_DELAY-c))
        sleep(1)

    while True:
        print("Stream index:{} \n".format(index))
        s1_activated = (serverActivation and userActivation)

        if s1_activated:
            Nearby = True
            if not idle_flag:
                idle_flag = True
                idle_end = perf_counter()
                idle_time = idle_end - idle_start
                # print("/////////////{} was IDLE for {} sec".format(CLIENT_ID,idle_time))
                active_flag = True
                start_coordinate_set = False
                stop_coordinate_set = True


            if active_flag:
                active_start = perf_counter()
                active_flag = False
            # print("Scooter {} is now active for {:.1f} sec".format(CLIENT_ID,perf_counter()-active_start))

        else:
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


        # print("ACTIVATION_client-{}:{}".format(CLIENT_ID,s1_activated))

        # Make sure there's a GPS fix
        if checkForFix():
            index+=1
            longitude,latitude,groundSpeed = getNavigationInfo()
            gndSpeed = float(groundSpeed)

            data['coordinates'].append({
                "lon" : float(longitude),
                "lat" : float(latitude)
                })
            if gndSpeed != 0.0: # if speed is not 0 km/h, scooter is moving
                s1_moved = 1
            else:
                s1_moved = 0

            if not s1_activated and s1_moved:
                scooterAlarm = True
                SMSalert = True
            else:
                scooterAlarm = False
                SMSalert = False

            """
            f1 = Server Act /
            f2 = User Act /
            f3 = Nearby X
            f4 = Activated /
            f5 = Moved /
            f6 = Speed /
            f7 = Alarm /
            f8 = SMS /
            """

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

            # print("\nNext stream in:\n")
            for c in range(STREAM_DELAY): # default to 5
                sleep(SECONDS_BETWEEN_READS)

def checkForFix():
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
                    sleep(1)
                    ser.write(b"AT+CGNSINF\r")
                    response = ser.readline()
                    if b"+CGNSINF: 1,1," in response:
                        return True
                    print ("Unable to find fix. Looking for fix...")
                # save to file before restarting
                with open('data.txt', 'w') as outfile:
                    json.dump(data, outfile)
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                ser.write(b"AT+CGNSINF\r")


# # Read the GNSS Navigation Information by parsing the complete NMEA sentence
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
            print("coord:{}{} speed:{}".format(clon,clat,spdg))
            return clon,clat,spdg

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
    # return clon,clat,spdg


if __name__ == "__main__":
    try:
        main_without_pppd()
    except KeyboardInterrupt:
        with open('data.txt', 'w') as outfile:
            json.dump(data, outfile)

        sleep(1)

        with open('data.txt', 'r') as json_file:
            json_object = json.load(json_file)
            print(json_object)
            print(json.dumps(json_object))

        print(json.dumps(json_object, indent=1))

        sleep(1)

        with open('data.txt') as json_file:
            data = json.load(json_file)
            for p in data['coordinates']:
                print('['+str(p['lon'])+","+str(p['lat'])+'],')
                # stringify = str(str(p['lon'])+","+str(p['lat']))
                stringify = str('['+str(p['lon'])+","+str(p['lat'])+'],')
                # # collect this format into another array
                geojson_list.append(stringify)
            # print(geojson_list)

        with open('geojson.txt', 'w') as outfile:
            json.dump(geojson_list, outfile)


        print("Turning off GPS for client-{}\n".format(CLIENT_ID))
