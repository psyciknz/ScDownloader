# ScDownloader

Small tool for Using SickChill to obtain files that a generally difficult to find.

Needs fairly strict naming, but bridges the gap between a show in TheTVBD/Sickchill and something with different release names.

# Instructions

Update the config.ini (copy from master) with your sickchill host, api, sabnzbd host and api and newznzb host (tested with nzbgeek).

The show name/show id you obtain from sickchill.

Added rudementary translation between what Sickchill (thetvbd) and the NZB releases.  This appears in a Section with the show name as the section header.

```[Shows]
show=Example|123456

[Example]
Sickchillname=NZb Name
```

eg
```Italy=Italian```
This will allow for any releses with Italy or Italian as a name.



Run with: 
```python scdownloader.py```
when the config.ini is in with the program files.


# Credits

* Uses an NewNZB Wrapper credit to : https://github.com/gugahoi/newznab_python_wrapper @gugahoi
* Sickchill code is based on : https://github.com/custom-components/sickchill 

# Change History

* 2020-12-06 0.3.2 - Set upcoming episode not in the config.ini episode types as skipped if found
                     This is because ot get them to show in upcoming new eps have to be set to wanted.
* 2020-12-05 0.3.1 - Allow specify location of config file, helps when running as cron.                     
                   - Added translate on 1 to One as is common for realeases for Formula 1
* 2020-12-03 0.3   - Added EpisodeType filter to Show Config set types to the partial name of the episode
                     eg Qualifying|Race 
                   - Added an upcoming filter for sickchill.  Choose between today, missed and soon
* 2020-12-02 0.2   - Added new config section for show
                   - Updated shows config to `<showname>|<showid>` if known
                   - Added translate options for show eg, Italy=Italian to help with sickchill episode naming
                     to release naming, it will use both when parsing the search results from the NZB Indexer
* 2020-12-01 0.1   - Initial Build and relese                     
