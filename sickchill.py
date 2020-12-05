"""
This will connect the Sickchill platform to Homeassistant, showing stats and switches from Sickchill.
Original based on https://github.com/custom-components/sickchill by @Swetoast
"""
import logging
import time
import re
from datetime import timedelta
import urllib
import html
import requests
try:
    #python 3+
    from configparser import ConfigParser
except:
    # Python 2.7
    from ConfigParser import ConfigParser

#import newznab
from newznab import wrapper
from sabnzbd import sabnzbd

__version__ = "0.1"
COMPONENT_NAME = "Sickchill"
COMPONENT_AUTHOR = "psyciknz"

TIMEOUT = 10
INTERVAL = timedelta(minutes=10)
ATTRIBUTES = ['shows_total', 'shows_active', 'ep_downloaded', 'ep_total', 'ep_snatched']

EPISODENAMEREGEX = r"(^.+).\("

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)
_LOGGER.addHandler(ch)


class sickchill:

	def __init__(self,config):
		"""Set up the component."""
		_LOGGER.info('Starting sickchill')
		_LOGGER.warning(' %s (%s) is starting, report any issues to %s', COMPONENT_NAME,__version__, COMPONENT_AUTHOR)
		self.config = config
		self.host = config["sc_host"]
		self.api = config["sc_api_key"]

	def restart_sickrage_service(self):
		"""Set up recuring update."""
		generic_command(self.self.host, self.self.api, 'sb.restart')

	def update_sickrage_service(self):
		"""Set up recuring update."""
		generic_command(self.host, self.api, 'sb.update')

	def shutdown_sickrage_service(self):
		"""Set up recuring update."""
		generic_command(self.host, self.api, 'sb.shutdown')

	def clearlogs_sickrage_service(self):
		"""Set up recuring update."""
		generic_command(self.host, self.api, 'clear.logs')

	def clearhistory_sickrage_service(self):
		"""Set up recuring update."""
		generic_command(self.host, self.api, 'clear.history')

	def forcepropersearch_sickrage_service(self):
		"""Set up recuring update."""
		generic_command(self.host, self.api, 'sb.propersearch')

	def forcedailysearch_sickrage_service(self):
		"""Set up recuring update."""
		generic_command(self.host, self.api, 'sb.dailysearch')

	def sensor_update(self):
		"""Update sensor values"""
		result = generic_command(self.host, self.api, 'shows.stats')
		for attr in ATTRIBUTES:
			_LOGGER.debug('Updating value for %s', attr)
		_LOGGER.debug('Update done...')

	def get_shows(self,findshowname=None):
		"""Update sensor values"""
		result = generic_command(self.host, self.api, 'shows')
		for show in result['data']:
			for field in result['data'][show]:
				_LOGGER.debug('Value for %s field %s=%s', show,field,result['data'][show][field])
				showname = result['data'][show][field]
				if field == "show_name" and findshowname is not None and showname == findshowname:
					return result['data'][show]
		_LOGGER.debug('Update done...')

	def get_show(self,showid,season=None):
		"""Update sensor values"""
		cmd = 'show.seasons&tvdbid=%s' % showid
		if not season is None:
			cmd = cmd + '&season=' + season
		result = generic_command(self.host, self.api, cmd)
		for show in result['data']:
			for field in result['data'][show]:
				_LOGGER.debug('Value for %s field %s=%s', show,field,result['data'][show][field])
				showname = result['data'][show][field]
			return result['data'][show]
		_LOGGER.debug('Update done...')

	def get_upcoming(self,showid,states):
		"""Get Upcoming shows for states"""
		cmd = 'future&type=%s' % states
		_LOGGER.debug("Performing Upcoming search for " + states)
		result = generic_command(self.host, self.api, cmd)
		episodes = []
		for section in result['data']: #soon
			counter = 0
			if result['data'][section] is None:
				break
			for counter in range(len(result['data'][section])):
				episode = result['data'][section][counter]
				for field in episode:
					#_LOGGER.debug('Value for section %s field %s=%s', section,field,result['data'][section][counter][field])
					if field=='tvdbid' and showid==result['data'][section][counter]['tvdbid']:
						_LOGGER.debug("Found upcoming episode of show with id: %s:%s" % (showid,result['data'][section][counter]))
						episodes.append(result['data'][section][counter])						

		return episodes	
		_LOGGER.debug('Update done...')

	def set_episode_status(self,showid,season,episode,state):
		"""Set Episdoe state -episode.setstatus"""

		#episode.setstatus&indexerid=387219&season=2020&episode=18&status=skipped&force=0
		cmd = 'episode.setstatus&indexerid=%s&season=%s&episode=%s&status=%s' % (showid,season,episode,state)
		_LOGGER.debug("Performing Set episode state S%sE%s to %s" % (season,episode,state))
		result = generic_command(self.host, self.api, cmd)
		
		_LOGGER.debug('Update done...')

def generic_command(host, api, command):
	"""Place docstring here!"""
	fetchurl = "{host}/api/{api}/?cmd={command}".format(host=host, api=api, command=command)
	_LOGGER.debug("Calling url: %s",fetchurl)
	result = requests.get(fetchurl, timeout=TIMEOUT, verify=True).json()
	return result


