#!/usr/bin/env python3 
"""
This will connect the Sickchill platform to Homeassistant, showing stats and switches from Sickchill.
"""
import logging
import time
import re
from datetime import timedelta
import urllib
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

__version__ = "0.3.2"
COMPONENT_NAME = "Sickchill"
COMPONENT_AUTHOR = "psyciknz"

TIMEOUT = 10
INTERVAL = timedelta(minutes=10)
ATTRIBUTES = ['shows_total', 'shows_active', 'ep_downloaded', 'ep_total', 'ep_snatched']
#episode types moved to config.ini
#EPISODETYPES = ['race','qualifying','Practice 2']

#specifc epsiode name regex for Formula one entires in SC (via thetvdb)
#eg an episode name of "Sakhir (Practice 2)"
# splits to two groups, the ep_name - ie place and the type - which is checked against the
# episodetypes config list.
EPISODENAMEREGEX = r"(^.+).\((.+)\)"

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)
_LOGGER.addHandler(ch)

def get_show_by_tvdbid(host,headers,tvdbid):
	url = "{}/api/v3/series/".format(host)
	print(url)
	res = requests.get(url,headers=headers)
	#print(res.json())
	for item in res.json():
		print("Found '{}' with tvbdbid of '{}'.  I want '{}'".format(item['title'],item['tvdbId'],tvdbid))
		if item['tvdbId'] == tvdbid:
			return item
		
		

if __name__ == '__main__':
	cp = ConfigParser(allow_no_value=True)
	_LOGGER.info("Loading config")
	if len(sys.argv) > 1:
		filename = sys.argv[1]
	else:
		filename = {"config.ini","conf/config.ini"}
	dataset = cp.read(filename)
	config = {}
	try:
		if len(dataset) != 1:
			raise ValueError( "Failed to open/find all files")

		config["sonarr_host"] = cp.get("Sonarr","host")
		config["sonarr_api_key"] = cp.get("Sonarr","api_key")
		config['sonarr_upcoming'] = cp.get("Sonarr","upcoming",fallback="missed|today|soon")
		config["newznzb_host"] = cp.get("NewzNZB","host")
		config["newznzb_api"] = cp.get("NewzNZB","api_key")
		config["newznzb_cat"] = cp.get("NewzNZB","cat",fallback="5000")
		config["sab_api_key"] = cp.get("SabNZBd","api_key")
		config["sab_host"] = cp.get("SabNZBd","host")
		config["sab_category"] = cp.get("SabNZBd","category")

		show  = cp.get("Shows","show").split("|")
		
		config["sports_show_name"] = show[0]
		if len(show) >1:
			config["sports_show_id"] = int(show[1] )#cp.get("Shows","show_id",fallback=None)
		show_cp = cp.items(show[0])
		config["episodetypes"] = cp.get(show[0],'episodetypes',fallback='').split("|")
		config[show[0]] = cp._sections[show[0]]

	except Exception as ex:
		_LOGGER.error("Error starting:" + str(ex))
		sys.exit(0)

	newznzb = wrapper(config["newznzb_host"],config["newznzb_api"],useSSL=True,useJson=True)
	
	sabnzbd = sabnzbd(config,_LOGGER)

	#Set Curl headers for sonarr
	headers = {
            'X-Api-Key': config["sonarr_api_key"]
        }

	#sc.get_shows()
	if  config['sports_show_id'] is not None:
		_LOGGER.debug("Already have a show ID, no need to go find it.")
		showtvdbid = config['sports_show_id']
		show = get_show_by_tvdbid(config["sonarr_host"],headers,showtvdbid)
	else:
		showname = "Formula 1"
		url = "{}/api/v3/series/lookup?term=tvdb:{}".format(config["sonarr_host"], showid)
		print(url)
		#show = sc.get_shows(findshowname=config["sports_show_name"])
		#showid = show['indexerid']
		res = requests.get(url,headers=headers)
		print(res.json())
	showname = show['title']
	showid = show['id']
	#hold newznzbresults here so we don't have to make multiple api calls
	newznzbresults = []

	#season = sc.get_show(showid,'2020')
	#Sonarr get upcoming
	#curl -v -H "x-requested-with: XMLHttpRequest" -H "x-api-key: xxxxxxxxxxxxxxxx" <baseurl>/api/v3/wanted/missing?sortKey=airDateUtc
	url = "{}/api/v3/wanted/missing?sortKey=airDateUtc".format(config["sonarr_host"])
	print (url)
	res = requests.get(url, headers=headers)
	print (res.json())
	episodelist = res.json()
	if episodelist is not None and episodelist['totalRecords'] > 0:
		print ("Has results")
		for episode in episodelist['records']:
			if showid != episode['seriesId']:
				print("Found upcoming episode  {} for series {}, but this is not our series".format(episode['title'],episode['seriesId']))
			else:
				full_ep_name = episode['title'] # Sakhir (Practice 2)
				episodeshow = episode['seriesId']
				season = episode['seasonNumber']
				ep_number = episode['episodeNumber']

				#result = [element for element in EPISODETYPES if element in episode['ep_name']]
				result = [element for element in config["episodetypes"] if element.lower() in episode['title'].lower() ]
				if len(result) > 0 :
					full_ep_name = episode['title'] # Sakhir (Practice 2)
					_LOGGER.debug("Found an episode type '%s' for '%s'",full_ep_name,showname)
					match =  re.match(EPISODENAMEREGEX,full_ep_name)
					ep_name = match[1]
					ep_type = match[2].replace(' ','.') # Practice 2
					#ep_type = result[0].replace(' ','.') # Practice 2
				
					ep_date = episode['airDate']
				
					#Debug entries for testing.
					#Formula1.2020.Bahrain.Grand.Prix.Qualifying.720p50.HDTV.DD2.0.x264-wAm
					#season = 2020
					#full_ep_name = "Great Britain (Qualifying)"
					#ep_name = "Great Britain"
					#ep_number = 77
					#ep_type = "Qualifying"
					
					#look for translation
					try:
						translate = str(config[showname][ep_name.lower()] )
					except:
						_LOGGER.debug('No translate entry for "%s" Found' % ep_name)
						translate = ep_name.lower()
	
					# quite specific for formula 1, as releases can be Practice 1 or Practice One
					ep_type_extended = ep_type.replace("1","(1|One|one|ONE)")
					ep_type_extended = ep_type_extended.replace("2","(2|Two|two|TWO)")
					ep_type_extended = ep_type_extended.replace("3","(3|Three|three|THREE)")
					#ep_type_extended = ep_type_extended.replace("Race","(\.[rR]ace)")
					if 'Sprint' in ep_type_extended:
						ep_type_extended = ep_type_extended.replace("Sprint","(\.[sS]print.+?)")
						ep_type_extended = ep_type_extended.replace("Qualifying","")
					else:
						ep_type_extended = ep_type_extended.replace("Race","((?<!\.Sprint)\.[rR]ace)")
						ep_type_extended = ep_type_extended.replace("Qualify","(\.[qQ]ualify)")
	

					nzbregex = '%s.%s.(%s|%s).+%s.+(?P<quality>(720|1080)).+' %(showname,season,ep_name,translate,ep_type_extended)
					_LOGGER.debug("Creating regex for matching NZB Results: %s" % nzbregex.replace(" ",".?"))
					pattern = re.compile(nzbregex.replace(" ",".?"))
					
					#perform NZBGeek Search
					nzbsearch = '%s.%s' % (showname.replace(" ",""),season)
					
					if newznzbresults is None or len(newznzbresults) ==0 :
						_LOGGER.debug('Performing NZB Search for "%s"' % nzbsearch)
						newznzbresults = newznzb.search(q=nzbsearch,maxage=10,cat=config["newznzb_cat"])
					else:
						_LOGGER.debug('Already performed an NZB Search for "%s"' % nzbsearch)
					#(q=str(nzbsearch),maxage=10)
					_LOGGER.debug("Return from NZB Search")
					
					#highest link and title to download.
					resultlink = ''
					resulttitle = ''
					lastquality = 0
					if 'item' in newznzbresults['channel'] and len(newznzbresults['channel']['item']) > 0:
						_LOGGER.debug("Results have been found: %s" % len(newznzbresults['channel']['item']))
						for result in newznzbresults['channel']['item']:
							title = result['title']
							match = re.match(pattern,title)
							link = result['link']
							_LOGGER.debug('Checking entry "%s" against the episode regex' % title)
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
						#for result in newznzbresults['channel']['item']:
	
						#send to SAB
						#do i need to rename it as sickchill expects? YES
						if resultlink is not None and resultlink != '':
							_LOGGER.debug("Entry to download: entry: %s Quality: %s: link: %s", title, quality,link)
							nzbname = "%s.S%sE%s.%s.%s" %(showname.replace(' ','.'),season,ep_number,full_ep_name,lastquality)
							_LOGGER.debug("Adding link to sabnzbd with nzb name of %s" % nzbname)
							sabnzbd.addnzb(resultlink,nzbname)
							_LOGGER.debug("Setting status as snatched")
							sc.set_episode_status(showid,season,ep_number,"snatched")
	
						else:
							_LOGGER.info("Nothing found to download")
					#if 'item' in results['channel'] and len(results['channel']['item']) > 0:
					else:
						_LOGGER.info("No NZB Results found")
				else:
					_LOGGER.debug("Non Wanted Episode Found as upcoming, setting as skipped '%s' - '%s'" % (showname,full_ep_name))
					#sc.set_episode_status(showid,season,ep_number,"skipped")
			#if showid != episode['seriesId']:
		#for episode in episodelist['records']:

		#if len(result) > 0

		#may need this to trigger post processing
		#https://internal.andc.nz/sonarr/api/v3/manualimport?seriesId=4&folder=%2Ftv%2FFormula%201&filterExistingFiles=true
	else: #if episodelist is not None and len(episodelist) > 0:
		_LOGGER.info("No upcoming episodes for %s" % config["sports_show_name"])

	_LOGGER.debug("fin")
