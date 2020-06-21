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

	# result is a list containing ordered dictionary.
	pprint.pprint(result)

# Driver function
if __name__=="__main__":

	# Coorinates tuple.Can contain more than one pair.
	coordinates =(1.58, 110.38) #110.388457, 1.583255)


	reverseGeocode(coordinates)
