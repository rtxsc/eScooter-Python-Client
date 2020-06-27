#!/usr/bin/python
# coding: utf8

from __future__ import absolute_import
from geocoder.google import GoogleResult, GoogleQuery
from geocoder.location import Location

# class GoogleReverseResult(GoogleResult):
#
#     @property
#     def ok(self):
#         return bool(self.address)

class GoogleReverse(GoogleQuery):
    """
    Google Geocoding API
    ====================
    Geocoding is the process of converting addresses (like "1600 Amphitheatre
    Parkway, Mountain View, CA") into geographic coordinates (like latitude
    37.423021 and longitude -122.083739), which you can use to place markers or
    position the map.

    API Reference
    -------------
    https://developers.google.com/maps/documentation/geocoding/
    Parameters
    ----------
    :param location: Your search location you want geocoded.
    :param components: Component Filtering
    :param method: (default=geocode) Use the following:
        > geocode
        > places
        > reverse
        > timezone
        > elevation
    :param key: Your Google developers free key.
    :param language: 2-letter code of preferred language of returned address elements.
    :param client: Google for Work client ID. Use with client_secret. Cannot use with key parameter
    :param client_secret: Google for Work client secret. Use with client.
    """
    provider = 'google'
    method = 'reverse'

    _URL = 'https://maps.googleapis.com/maps/api/geocode/json'
    _RESULT_CLASS = GoogleResult
    _KEY = 'AIzaSyBGvn5IKpL8dpo8DPl_kx-Xc4VGWIu86Dw'
    _KEY_MANDATORY = False

    def _location_init(self, location, **kwargs):
        return {
            'latlng': str(Location(location)),
            'sensor': 'false',
        }

if __name__ == '__main__':
    g = GoogleReverse((1.588, 110.388))
    # g.debug()
    print(g.address)
