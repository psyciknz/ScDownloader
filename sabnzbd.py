"""
This will connect the Sickchill platform to Homeassistant, showing stats and switches from Sickchill.
"""
import logging
import time
import re
from datetime import timedelta
import requests
import urllib

#import newznab
from newznab import wrapper

COMPONENT_NAME = "sabnzbd"

class sabnzbd:
	def __init__(self,config,_LOGGER):
		"""Set up the component."""
		self._LOGGER = _LOGGER
		self.category = config['sab_category']
		self.sab_url = config['sab_host']
		self.sab_api_key = config['sab_api_key']

		_LOGGER.warning(' %s is starting', COMPONENT_NAME)

	def addnzb(self,url,name=None):
		'''
		Send a NZB url to SABNZBD

		:param url: The NZBSearchResult object to send to SAB
		'''

		self._LOGGER.debug("Adding url to SABNZBD: %s",url)

		# set up a dict with the URL params in it
		params = {'output': 'json'}
		params['apikey'] = self.sab_api_key

		# Set the sab catgory for sickchill
		params['cat'] = self.category

		self._LOGGER.info('Sending NZB to SABnzbd')
		submiturl = urllib.parse.urljoin(self.sab_url, 'api')

		params['mode'] = 'addurl'
		params['name'] = url

		if name is not None:
			params['nzbname'] = name

		result = requests.post(url=submiturl,data=params)

		self._LOGGER.debug("REturned result form sab: %s",result.status_code)
        



