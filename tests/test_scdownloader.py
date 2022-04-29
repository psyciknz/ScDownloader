import datetime
import pytest
import mock
import os
from configparser import ConfigParser
import sondownloader

@mock.patch('requests.get')
def test_get_show_by_tvdbid(mock_get):
    """
    Tests getting shows from Sonarr, then calls again to get a new show, shouldn't connect to sonnar the 2nd time
    """
    host = 'https://fake-sonarr.com'
    tvdbid = 387219
    headers = {
            'X-Api-Key': "1234"
        }

    my_mock_response = mock.Mock(status_code=200)
    my_mock_response.json.return_value = [
        { 
            "title": "Formula 1",
            "tvdbId": 387219,
            "id": 4
        },
        {
            "title": "Formula 1: Drive to Survive",
            "tvdbId": 359913,
            "id": 5
        },
        {
            "title": "V8 Supercars Highlights Show",
            "tvdbId": 370078,
            "id": 54
        }
    ]
            
    mock_get.return_value = my_mock_response     
    myshow = sondownloader.get_show_by_tvdbid(host,headers,tvdbid)
    assert(sondownloader.sonarshows is not None)
    assert(myshow is not None)
    assert(len(sondownloader.sonarshows) == len(my_mock_response.json.return_value))
    assert(myshow['title'] == 'Formula 1')
    tvdbid = 359913
    myshow = sondownloader.get_show_by_tvdbid(host,headers,tvdbid)
    assert(myshow is not None)
    assert(myshow['title'] == 'Formula 1: Drive to Survive')

#def test_get_show_by_tvdbid(mock_get):


def test_get_config_shows(tmpdir):
    cp = ConfigParser(allow_no_value=True)
    cp.add_section("Shows")
    cp.set("Shows", "Formula 1|387219")
    cp.set("Shows", "v8 supercars|387220")


    cp.add_section("formula 1")
    cp.set("formula 1","EpisodeTypes=race|qualifying|day")
    cp.set("formula 1","Hungary=Hungarian")
    cp.set("formula 1","Great Britain=British")
    cp.set("formula 1","Italy=Italian")

    cp.add_section("v8 supercars")
    cp.set("v8 supercars","EpisodeTypes=race|qualifying|day")
    
    cp.write(open(os.path.join(tmpdir,"config.ini"),"w"))
    cp.read(open(os.path.join(tmpdir,"config.ini"),"r"))

    config = sondownloader.get_config_shows(cp)

    assert(config is not None)
    assert(config['formula 1'] is not None)
    assert(config['v8 supercars'] is not None)
#def test_get_config_shows(tmpdir): 

def test_process_upcoming_episode(tmpdir):
    config = {}
    episode = {
        "seriesId": 4, 
        "tvdbId": 9017877,
        "episodeFileId": 0,
        "seasonNumber": 2022,
        "episodeNumber": 20, 
        "title": "Great Britain (Qualifying)", 
        "airDate": "2022-04-22", 
        "airDateUtc": "2022-04-22T19:00:00Z",
            "overview": "The Emilia Romagna Grand Prix (Italian: Gran Premio dell\"Emilia Romagna) is a Formula One motor racing event held at the Autodromo Internazionale Enzo e Dino Ferrari, often shortened to 'Imola' after the town where it is located. The Imola circuit previously hosted the Italian Grand Prix in 1980, and the San Marino Grand Prix from 1981 to 2006.", 
            "id": 4571, 
            "show": {
                "tvdbid": 387219, 
                "seriesid": 4, 
                "EpisodeRegex": "(^.+).\\((.+)\\)", 
                "EpisodeTypes": "race|qualifying|day", 
                "name": "Formula 1",
                "Hungary": "Hungarian", "Great Britain": "British", "Italy": "Italian", "Portugal": "Portuguese"
                }
    }
    result = sondownloader.process_upcoming_episode(config, episode)
     
#def test_process_upcoming_episode(tmpdir):
