import datetime
import pytest
import mock
from configparser import ConfigParser
import sondownloader

@mock.patch('requests.get')
def test_get_show_by_tvdbid(mock_get):
    
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
    shows,myshow = sondownloader.get_show_by_tvdbid(host,headers,tvdbid)
    assert(shows is not None)
    assert(myshow is not None)
    assert(len(shows) == len(my_mock_response.json.return_value))

def test_get_config_shows():
    cp = ConfigParser(allow_no_value=True)
    cp.add_section("Shows")
    cp.set("Shows", "Formula 1|387219")

    cp.write(open("test.ini","w"))

