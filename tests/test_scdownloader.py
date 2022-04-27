import datetime
import pytest


def test_get_show_by_tvdbid():
    host = 'https://internal.andc.nz/sonarr'
    api = '20e93a5e68a344fb9df3dd47e5dcd02a'
    tvdbid = 387219

    show = sondownloader.get_show_by_tvdbid(host,headers,tvdbid)
    assert(show is not None)
