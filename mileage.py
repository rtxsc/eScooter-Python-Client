import math

def calcDistance(lon1,lat1,lon2,lat2):
    R = 6373.0 # radius of the Earth

    # coordinates
    # lat1 = math.radians(52.2296756)
    # lon1 = math.radians(21.0122287)
    # lat2 = math.radians(52.406374)
    # lon2 = math.radians(16.9251681)
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
    print("------------------------------------------>Distance: {} m".format(distance))

if __name__ == "__main__":
    try:
        coord1 = 110.588,1.388
        coord2 = 110.0,1.3
        calcDistance(coord1[0],coord1[1],coord2[0],coord2[1]) #lon1,lat1,lon2,lat2

    except KeyboardInterrupt:
        print("bye")
