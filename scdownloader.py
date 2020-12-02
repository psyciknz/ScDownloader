#!/usr/bin/env python3 
"""
This will connect the Sickchill platform to Homeassistant, showing stats and switches from Sickchill.
"""
import logging
import time
import re
from datetime import timedelta
import urllib
import html
import requests
import sys
try:
	#python 3+
	from configparser import ConfigParser
except:
	# Python 2.7
	from ConfigParser import ConfigParser

#import newznab
from newznab import wrapper
from sabnzbd import sabnzbd
from sickchill import sickchill

__version__ = "0.1"
COMPONENT_NAME = "Sickchill"
COMPONENT_AUTHOR = "psyciknz"

TIMEOUT = 10
INTERVAL = timedelta(minutes=10)
ATTRIBUTES = ['shows_total', 'shows_active', 'ep_downloaded', 'ep_total', 'ep_snatched']
EPISODETYPES = ['race','qualifying','Practice 2']

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


if __name__ == '__main__':
	cp = ConfigParser(allow_no_value=True)
	_LOGGER.info("Loading config")
	filename = {"config.ini","conf/config.ini"}
	dataset = cp.read(filename)
	config = {}
	try:
		if len(dataset) != 1:
			raise ValueError( "Failed to open/find all files")

		config["sc_host"] = cp.get("Sickchill","host")
		config["sc_api_key"] = cp.get("Sickchill","api_key")
		config["newznzb_host"] = cp.get("NewzNZB","host")
		config["newznzb_api"] = cp.get("NewzNZB","api_key")
		config["sab_api_key"] = cp.get("SabNZBd","api_key")
		config["sab_host"] = cp.get("SabNZBd","host")
		config["sab_category"] = cp.get("SabNZBd","category")

		config["sports_show"] = cp.get("Shows","show")
		config["sports_show_id"] = cp.get("Shows","show_id",fallback=None)
	except Exception as ex:
		_LOGGER.error("Error starting:" + str(ex))
		sys.exit(0)

	newznzb = wrapper(config["newznzb_host"],config["newznzb_api"],useSSL=True,useJson=True)
	
	sabnzbd = sabnzbd(config,_LOGGER)

	sc = sickchill(config)
	#sc.get_shows()
	if  config['sports_show_id'] is not None:
		_LOGGER.debug("Already have a show ID, no need to go find it.")
		showid = config['sports_show_id']
	else:
		show = sc.get_shows(findshowname=config["sports_show"])
		showid = show['indexerid']

	#season = sc.get_show(showid,'2020')
	episodelist = sc.get_upcoming(showid,'missed|today')
	if episodelist is not None and len(episodelist) > 0:
		for episode in episodelist:
			result = [element for element in EPISODETYPES if element in episode['ep_name']]
			if len(result) > 0 :
				_LOGGER.debug("Found an episode type: " + result[0])
				full_ep_name = episode['ep_name'] # Sakhir (Practice 2)
				match =  re.match(EPISODENAMEREGEX,full_ep_name)
				ep_name = match[1]
				ep_type = result[0].replace(' ','.') # Practice 2
				season = episode['season']
				ep_number = episode['episode']
				ep_date = episode['airdate']
				showname = episode['show_name']
				
				#Formula1.2020.Bahrain.Grand.Prix.Qualifying.720p50.HDTV.DD2.0.x264-wAm
				#season = 2020
				#full_ep_name = "Bahrain (Qualifying)"
				#ep_name = "Bahrain"
				#ep_number = 77
				#ep_type = "Qualifying"
				
				_LOGGER.debug("Creating regex for matching NZB Results: %s" % '%s.%s.%s.+%s.+(?P<quality>(720|1080)).+' %(showname.replace(" ",".?"),season,ep_name,ep_type) )
				pattern = re.compile('%s.%s.%s.+%s.+(?P<quality>(720|1080)).+' %(showname.replace(" ",".?"),season,ep_name,ep_type))
				
				#perform NZBGeek Search
				_LOGGER.debug('Performing NZB Search for "%s"' % '%s.%s %s %s' % (showname.replace(" ",""),season,ep_name,ep_type))
				results = wrapper.search(q="%s.%s %s %s" % (showname.replace(" ",""),season,ep_name,ep_type),maxage=10)
				_LOGGER.debug("Return from NZB Search")
				
				#highest link and title to download.
				resultlink = ''
				resulttitle = ''
				lastquality = 0
				if 'item' in results['channel'] and len(results['channel']['item']) > 0:
					_LOGGER.debug("Results have been found: %s" % len(results['channel']['item']))
					for result in results['channel']['item']:
						title = result['title']
						match = re.match(pattern,title)
						link = result['link']
					#match = re.match(pattern,'Formula1.2020.Sakhir.Grand.Prix.Practice.1.720p50.HDTV.DD2.0.x264-wAm')
					#match = re.match(pattern,'Formula1.2020.Sakhir.Grand.Prix.Practice.2.720p50.HDTV.DD2.0.x264-wAm')
						
						if match is not None:
							quality = int(match.group('quality'))
							_LOGGER.debug("Found rss entry: %s Quality: %s", title, quality)
							if quality > lastquality:
								_LOGGER.debug("Higher quality this one: entry: %s Quality: %s", title, quality)
								lastquality = quality
								resultlink = html.unescape(link)
								resulttitle = title
					#send to SAB
					#do i need to rename it as sickchill expects? YES
					if resultlink is not None:
						_LOGGER.debug("Entry to download: entry: %s Quality: %s: link: %s", title, quality,link)
						nzbname = "%s.S%sE%s.%s.%s" %(showname.replace(' ','.'),season,ep_number,full_ep_name,lastquality)
						_LOGGER.debug("Adding link to sabnzbd with nzb name of %s" % nzbname)
						sabnzbd.addnzb(resultlink,nzbname)
					else:
						_LOGGER.info("Nothing found to download")
				#if 'item' in results['channel'] and len(results['channel']['item']) > 0:
				else:
					_LOGGER.info("No Upcoming episodes")
	else: #if episodelist is not None and len(episodelist) > 0:
		_LOGGER.info("No upcoming episodes for %s" % config["sports_show"])

	_LOGGER.debug("fin")