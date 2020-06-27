# Python3 program for reverse geocoding.

# importing necessary libraries

"""
	Dependencies:
	pip install reverse_geocoder
	pip install pprint
	sudo apt-get install libatlas-base-dev
"""
import reverse_geocoder as rg
import pprint

def reverseGeocode(coordinates):
	result = rg.search(coordinates)
	pprint.pprint(result[0])

# Driver function
if __name__=="__main__":
	search_coord = 1.4489, 110.4451
	print("Check:{}".format(search_coord))
	# 3.0697° N, 101.5037° E uitm shah alam
	# 1.4489° N, 110.4451° E uitm sarawak
	# Coorinates tuple.Can contain more than one pair.
	coordinates =(search_coord) #110.388457, 1.583255)


	reverseGeocode(coordinates)
