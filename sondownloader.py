#!/usr/bin/env python3 
"""
This will connect the Sickchill platform to Homeassistant, showing stats and switches from Sickchill.
"""
import logging
import time
import html
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
COMPONENT_NAME = "Sonarr"
COMPONENT_AUTHOR = "psyciknz"

SONARR_HOST = 'host'
#Sonar Series Identification field
CONFIG_SHOW_SERIESID = "seriesid"
#TVDBID field name for searching Sonarr for a show if the series id is not known
CONFIG_SHOW_TVDBID = "tvdbid"
#Episodes types value
CONFIG_SHOW_EPISODETYPES = "episodetypes"


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

sonarshows = {}

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)
_LOGGER.addHandler(ch)

def get_show_by_tvdbid(host,headers,tvdbid) -> dict:
	"""
	Gets a specific sonar show from sonar.
	"""
	if len(sonarshows) == 0:
		url = "{}/api/v3/series/".format(host)
		print(url)
		
		res = requests.get(url,headers=headers)
		#print(res.json())
		for item in res.json():
			print("Found '{}' with tvbdbid of '{}'.  I want '{}'".format(item['title'],item['tvdbId'],tvdbid))
			sonarshows[item['id']] = item
			if tvdbid is not None and item['tvdbId'] == tvdbid:
				returnitem = item
	else:
		for show in sonarshows.values():
			if tvdbid is not None and show['tvdbId'] == tvdbid:
				return show
	#for item in res.json():
	return returnitem
#def get_show_by_tvdbid(host,headers,tvdbid):

def get_config(filename):
	cp = ConfigParser(allow_no_value=True)
	cp.optionxform = str
	_LOGGER.info("Loading config")
	if filename is None:
		filename = {"config.ini","conf/config.ini"}
	dataset = cp.read(filename[1])
	config = {}
	try:
		if len(dataset) != 1:
			raise ValueError( "Failed to open/find all files")

		config[SONARR_HOST] = cp.get("Sonarr","host")
		config["sonarr_api_key"] = cp.get("Sonarr","api_key")
		config['sonarr_upcoming'] = cp.get("Sonarr","upcoming",fallback="missed|today|soon")
		config["newznzb_host"] = cp.get("NewzNZB","host")
		config["newznzb_api"] = cp.get("NewzNZB","api_key")
		config["newznzb_cat"] = cp.get("NewzNZB","cat",fallback="5000")
		config["sab_api_key"] = cp.get("SabNZBd","api_key")
		config["sab_host"] = cp.get("SabNZBd","host")
		config["sab_category"] = cp.get("SabNZBd","category")

		shows = get_config_shows(cp)
		config['shows'] = shows
	except Exception as ex:
		_LOGGER.error("Error starting:" + str(ex))
		sys.exit(0)
	return config
#def get_config(filename):

def get_config_shows(cp):
	"""
	Gets the shows from config resturns as a dictionary
	"""
	shows = {}

	showsconfig  = dict(cp['Shows'])
	for value in showsconfig:
		# added Sonar ID to show entry so it can bypass the sonarr lookup if neded.
		#Formula 1|387219|4
		show = str(value).split("|")
		
		showdata = {}
		# populate the show name and id if there.
		showdata['name'] = show[0]
		if len(show) >=2:
			showdata[CONFIG_SHOW_TVDBID] = int(show[1])
		if len(show) ==3:
			showdata[CONFIG_SHOW_SERIESID] = int(show[2])
	
		showdata = cp._sections[show[0]]
		showdata['name'] = show[0]

		#regardless how it got there, for the TVDBID and Series IDs to Int, as from cp._sections, it's a string.
		if CONFIG_SHOW_TVDBID in showdata:
			showdata[CONFIG_SHOW_TVDBID] = int(showdata[CONFIG_SHOW_TVDBID])
		if CONFIG_SHOW_SERIESID in showdata:
			showdata[CONFIG_SHOW_SERIESID] = int(showdata[CONFIG_SHOW_SERIESID])
		
		if 'EpisodeTypes' in showdata and showdata['EpisodeTypes'] != '':
			showdata[CONFIG_SHOW_EPISODETYPES] = showdata['EpisodeTypes'].split("|")

		#set shows dictionary to show data, keyed by showname
		shows[show[0]] = showdata
		#Storing shows by sonary show id as used for upcoming episodes.
		

	return shows
#def get_config_shows(cp):


def get_upcoming_episodes(config, headers) -> []:
	"""
	Gets the upcoming episodes for the shows the user wants
	Returns a list of each episode that is wanted after filtering out any shows not relevant and episode types
	"""

	# Get the shows from the config object.
	shows = config['shows']
	showsbyid = {}
	for show in shows:
		showsbyid[shows[show][CONFIG_SHOW_SERIESID]] = shows[show]['name']

	url = "{}/api/v3/wanted/missing?sortKey=airDateUtc".format(config[SONARR_HOST])
	print (url)
	res = requests.get(url, headers=headers)
	#print (res.json())
	episodelist = res.json()
	upcoming = []
	if episodelist is not None and episodelist['totalRecords'] > 0:
		#print ("Has results")
		for episode in episodelist['records']:
			if episode['seriesId'] in showsbyid:
				episodeshow = episode['seriesId']
				epid = episode['id']
				show = shows[showsbyid[episodeshow]]
				#if using episode types (eg race/qualifying) try and find one of those values
				#in the title of the upcoming episode.
				#if episode types not used, then get any result for processing.
				if CONFIG_SHOW_EPISODETYPES in show and len(show[CONFIG_SHOW_EPISODETYPES]) > 0:
					result = [element for element in show[CONFIG_SHOW_EPISODETYPES] if element.lower() in episode['title'].lower() ]
				else:
					result = "yes"
				
				# processing of particular wanted episode types.  
				if len(result) > 0:
					episode['show'] = show
					upcoming.append(episode)
				else:
					#is a show we want, but not an episode type (applicable to formula 1 where you might only
					# want race and qualifying)
					_LOGGER.debug("---------------------------------------------------------------------------------------------")
					_LOGGER.debug("Non Wanted Episode Found as upcoming, setting as skipped '%s' - '%s'" % (showname,full_ep_name))  
					url = "{}/api/v3/episode/{}".format(config[SONARR_HOST],epid)
					
					#request_uri ='http://'+self.sonarr_address+'/api/episode/'+str(sonarr_epid)+'?apikey='+self.sonarr_apikey
					sonarr_episode_json = requests.get(url,headers=headers).json()
					sonarr_episode_json["monitored"] = False
					r = requests.put(url,headers=headers,json=sonarr_episode_json)
					if r.status_code != 200 and r.status_code != 202:
						print("   Error: "+str(r.json()["message"]))


				#full_ep_name = episode['title'] # Sakhir (Practice 2)
				#episodeshow = episode['seriesId']
				#season = episode['seasonNumber']
				#ep_number = episode['episodeNumber']
				#epid = episode['id']
			#if showid != episode['seriesId']:
		#for episode in episodelist['records']:
	#if episodelist is not None and episodelist['totalRecords'] > 0:
	return upcoming
#def get_upcoming_episodes(config):				

def process_upcoming_episode(config,episode):
	"""
	This method has to take the upconing wanted show from Sonarr and translate it into a nzbsearch
	It will use episode translates if needed Italy = Italian
	and Practice 1 to practice 1 or One
	"""
	full_ep_name = episode['title'] # Sakhir (Practice 2)
	currentshow = episode['show']
	showname = currentshow['name']
	_LOGGER.debug("")
	_LOGGER.debug("*************   Found an episode type \"{}\" for \"{}\"".format(full_ep_name,showname))

	#Formula1 = 'Emilia Romagna (Qualifying)'
	#full_ep_name = "Great Britain (Qualifying)"
	#ep_name = "Great Britain"
	#ep_number = 77
	#ep_type = "Qualifying"

	#V8 = Melbourne 400 Race 4 Highlights
	#nzb Supercars.Championship.2022.Race.9.Beaurepairs.Melbourne.400.Highlights.1080p.HDTV.H264-DARKSPORT


	match =  re.match(currentshow['EpisodeRegex'],full_ep_name)
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
		translate = str(currentshow[ep_name] )
	except:
		_LOGGER.debug('No translate entry for "%s" Found' % ep_name)
		translate = ep_name.lower()

	# quite specific for formula 1, as releases can be Practice 1 or Practice One
	#unsure how to change this for other types.
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

	#TODO: test breaks here.
	nzbregex = '%s.%s.(%s|%s).+%s.+(?P<quality>(720|1080)).+' %(showname,season,ep_name,translate,ep_type_extended)
	_LOGGER.debug("Creating regex for matching NZB Results: %s" % nzbregex.replace(" ",".?"))
	pattern = re.compile(nzbregex.replace(" ",".?"))
	
	#perform NZBGeek Search
	nzbsearch = '%s.%s' % (showname.replace(" ",""),season)
	
	if newznzbresults is None or len(newznzbresults) ==0 :
		_LOGGER.debug('')
		_LOGGER.debug('----------------------------------------------------------')
		_LOGGER.debug('Performing NZB Search for "%s"' % nzbsearch)
		newznzbresults = newznzb.search(q=nzbsearch,maxage=10,cat=config["newznzb_cat"])
	else:
		_LOGGER.debug('Already performed an NZB Search for "%s"' % nzbsearch)
	#(q=str(nzbsearch),maxage=10)
	_LOGGER.debug("Return from NZB Search")
	_LOGGER.debug("")
	
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
			_LOGGER.debug('*****     Checking entry "%s" against the episode regex' % title)
		#match = re.match(pattern,'Formula1.2020.Sakhir.Grand.Prix.Practice.1.720p50.HDTV.DD2.0.x264-wAm')
		#match = re.match(pattern,'Formula1.2020.Sakhir.Grand.Prix.Practice.2.720p50.HDTV.DD2.0.x264-wAm')
			
			if match is not None:
				quality = int(match.group('quality'))
				_LOGGER.debug("---------------    Found rss entry: %s Quality: %s", title, quality)
				if quality > lastquality:
					_LOGGER.debug("++++++++++++++++      Higher quality this one: entry: %s Quality: %s", title, quality)
					lastquality = quality
					resultlink = html.unescape(link)
					resulttitle = title
		#for result in newznzbresults['channel']['item']:

		#send to SAB
		#do i need to rename it as sickchill expects? YES
		if resultlink is not None and resultlink != '':
			_LOGGER.debug("")
			_LOGGER.debug("===================================================================================")
			_LOGGER.debug("Entry to download: entry: %s Quality: %s: link: %s", resulttitle, quality,link)
			nzbname = "%s.S%sE%s.%s.%s" %(showname.replace(' ','.'),season,ep_number,full_ep_name,lastquality)
			_LOGGER.debug("Adding link to sabnzbd with nzb name of \"%s\"" % nzbname)
			sabnzbd.addnzb(resultlink,nzbname)
			_LOGGER.debug("Setting status as snatched")
			#sc.set_episode_status(showid,season,ep_number,"snatched")

		else:
			_LOGGER.info("Nothing found to download")
	#if 'item' in results['channel'] and len(results['channel']['item']) > 0:
	else:
		_LOGGER.info("No NZB Results found")
#def process_upcoming_episode(config,episode):


if __name__ == '__main__':
	
	if len(sys.argv) > 1:
		config = get_config(sys.argv)
	else:
		config - get_config(None)

	#create newznzb connection object
	newznzb = wrapper(config["newznzb_host"],config["newznzb_api"],useSSL=True,useJson=True)
	
	# Create sabnzbd connection object
	sabnzbd = sabnzbd(config,_LOGGER)

	#Set Curl headers for sonarr
	headers = {
            'X-Api-Key': config["sonarr_api_key"]
        }

	#all the shows from the config that the user wants to track
	shows = config['shows']

	# get the sonarr series id for each show the users wants to track.
	for show in shows:
		currentshow = shows[show]
		if CONFIG_SHOW_SERIESID not in currentshow:
			_LOGGER.debug("Have to look up show '{}' by TVDBID to get the sonar series id: '{}'".format(show,currentshow[CONFIG_SHOW_TVDBID]))
			sonarshow = get_show_by_tvdbid(config[SONARR_HOST], headers, currentshow[CONFIG_SHOW_TVDBID])
			currentshow[CONFIG_SHOW_SERIESID] = sonarshow['id']
		else:
			_LOGGER.debug("Show '{}' Already has a sonarr series id of '{}' - no need to look for it".format(show,currentshow[CONFIG_SHOW_SERIESID]))
		#if CONFIG_SHOW_SERIESID not in show:

	#hold newznzbresults here so we don't have to make multiple api calls
	newznzbresults = []

	#season = sc.get_show(showid,'2020')
	#Sonarr get upcoming 
	episodelist = get_upcoming_episodes(config, headers)
	_LOGGER.debug("")
	_LOGGER.debug("Have {} upcoming episodes to process and try and find downloads for".format(len(episodelist)))

	#process all the episodes here.
	#Will search NZB do all the filename translations and return an NZB url and what to call the NZB 
	#in sabnznbd to get sonarr to process it.
	for episode in episodelist:
		
		result = process_upcoming_episode(config,episode)
		_LOGGER.debug("")


	



	#curl -v -H "x-requested-with: XMLHttpRequest" -H "x-api-key: xxxxxxxxxxxxxxxx" <baseurl>/api/v3/wanted/missing?sortKey=airDateUtc
	url = "{}/api/v3/wanted/missing?sortKey=airDateUtc".format(config["sonarr_host"])
	print (url)
	res = requests.get(url, headers=headers)
	#print (res.json())
	episodelist = res.json()
	if episodelist is not None and episodelist['totalRecords'] > 0:
		#print ("Has results")
		for episode in episodelist['records']:
			if showid != episode['seriesId']:
				_LOGGER.debug("Found upcoming episode  \"{}\" for series \"{}\", but this is not our series".format(episode['title'],shows[episode['seriesId']]['title']))
			else:
				full_ep_name = episode['title'] # Sakhir (Practice 2)
				episodeshow = episode['seriesId']
				season = episode['seasonNumber']
				ep_number = episode['episodeNumber']
				epid = episode['id']

				#result = [element for element in EPISODETYPES if element in episode['ep_name']]
				result = [element for element in config["episodetypes"] if element.lower() in episode['title'].lower() ]
				if len(result) > 0 :
					full_ep_name = episode['title'] # Sakhir (Practice 2)
					_LOGGER.debug("")
					_LOGGER.debug("*************   Found an episode type \"{}\" for \"{}\"".format(full_ep_name,showname))
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
						_LOGGER.debug('')
						_LOGGER.debug('----------------------------------------------------------')
						_LOGGER.debug('Performing NZB Search for "%s"' % nzbsearch)
						newznzbresults = newznzb.search(q=nzbsearch,maxage=10,cat=config["newznzb_cat"])
					else:
						_LOGGER.debug('Already performed an NZB Search for "%s"' % nzbsearch)
					#(q=str(nzbsearch),maxage=10)
					_LOGGER.debug("Return from NZB Search")
					_LOGGER.debug("")
					
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
							_LOGGER.debug('*****     Checking entry "%s" against the episode regex' % title)
						#match = re.match(pattern,'Formula1.2020.Sakhir.Grand.Prix.Practice.1.720p50.HDTV.DD2.0.x264-wAm')
						#match = re.match(pattern,'Formula1.2020.Sakhir.Grand.Prix.Practice.2.720p50.HDTV.DD2.0.x264-wAm')
							
							if match is not None:
								quality = int(match.group('quality'))
								_LOGGER.debug("---------------    Found rss entry: %s Quality: %s", title, quality)
								if quality > lastquality:
									_LOGGER.debug("++++++++++++++++      Higher quality this one: entry: %s Quality: %s", title, quality)
									lastquality = quality
									resultlink = html.unescape(link)
									resulttitle = title
						#for result in newznzbresults['channel']['item']:
	
						#send to SAB
						#do i need to rename it as sickchill expects? YES
						if resultlink is not None and resultlink != '':
							_LOGGER.debug("")
							_LOGGER.debug("===================================================================================")
							_LOGGER.debug("Entry to download: entry: %s Quality: %s: link: %s", resulttitle, quality,link)
							nzbname = "%s.S%sE%s.%s.%s" %(showname.replace(' ','.'),season,ep_number,full_ep_name,lastquality)
							_LOGGER.debug("Adding link to sabnzbd with nzb name of \"%s\"" % nzbname)
							sabnzbd.addnzb(resultlink,nzbname)
							_LOGGER.debug("Setting status as snatched")
							#sc.set_episode_status(showid,season,ep_number,"snatched")
	
						else:
							_LOGGER.info("Nothing found to download")
					#if 'item' in results['channel'] and len(results['channel']['item']) > 0:
					else:
						_LOGGER.info("No NZB Results found")
				else:
					_LOGGER.debug("---------------------------------------------------------------------------------------------")
					_LOGGER.debug("Non Wanted Episode Found as upcoming, setting as skipped '%s' - '%s'" % (showname,full_ep_name))  
					url = "{}/api/v3/episode/{}".format(config["sonarr_host"],epid)
					
					#request_uri ='http://'+self.sonarr_address+'/api/episode/'+str(sonarr_epid)+'?apikey='+self.sonarr_apikey
					sonarr_episode_json = requests.get(url,headers=headers).json()
					sonarr_episode_json["monitored"] = False
					r = requests.put(url,headers=headers,json=sonarr_episode_json)
					if r.status_code != 200 and r.status_code != 202:
						print("   Error: "+str(r.json()["message"]))
					#sc.set_episode_status(showid,season,ep_number,"skipped")
			#if showid != episode['seriesId']:
		#for episode in episodelist['records']:

		#if len(result) > 0

		#may need this to trigger post processing
		#https://internal.andc.nz/sonarr/api/v3/manualimport?seriesId=4&folder=%2Ftv%2FFormula%201&filterExistingFiles=true
	else: #if episodelist is not None and len(episodelist) > 0:
		_LOGGER.info("No upcoming episodes for %s" % config["sports_show_name"])

	_LOGGER.debug("fin")
