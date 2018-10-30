# MPMagic

Autoplaylist for mpd. Will remove old songs from playlist and add new songs from a pool of shuffled tracks.

Also you can play a jingle every so often and log what is added (by user or by shuffle)

It is as custom as my interface mpdremote. So to use it, you probably have to read some code. Check `mpm.ini` and `mpms.py` for a start.

`mpmc.py` is a simple commandline-client for querying status of mpmagic.

`mpmclient.php` is a frontend for configuration of a running mpmagic. The config is not saved uppon termination/restert (TODO).
It is pretty hacked-together so don't expect too much. Pull requests welcome ;-).

`mpm_stats.r` is a R-script to create some fancy plots about what's going on inside mpmagic.
