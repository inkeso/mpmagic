#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=============================
#+-   MusicPlayerMagic    -+#
=============================

This Service/Daemon takes care of MPDs Playlist by adding random Songs to it and
removing old ones.

It can also play a Jingle every now and them.

The service can be configured at runtime via a simple socket-connection (e.g.
using telnet or netcat). A PHP-frontend is included.

Features include:

- Remove old playlistentries (keep a configurable amount of old entries)
- Add random songs to playlist, so that there are always songs comming up.
- Songs are taken from the internal filepool, which is filled with files from
  the MPD-Database but allows blacklisting of files/directories so that you
  can prevent your audiobook-collection from being added.
- Blacklisting is done with a regular expression and thus is very powerful.
- Added songs are moved from the pool to a history (with timestamp) so you always
  know how many (and which) songs have already been added to MPDs playlist and
  how many remain in the pool. (pool is refilled automaticly if it runs empty)

- Play a jingle after a random amount of time (the constraints of randomnes are
  configurable)
- Playing jingles can be limited to only play a few seconds before a song ends
  for not disturbing your listening-pleasure.
- Jingles are chosen randomly from a dir (which is also read in a pool and can
  be re-read at any time)

- TODO: The complete state of the service (pools, settings, ...) is always saved

---------------------------------------------------------------------------------
|  Commands  |  (apl = AutoPlayList, jgl = JinGLes, mnt = MoNiTor)              |
---------------------------------------------------------------------------------

status [apl|jgl|mnt]               --  print status (all config- and state-vars)
config [apl|jgl|mnt] tOption Value --  alter the given option (see status for
                                       available options)
refill [apl|jgl]                   --  refill the file-pool (read MPD-filelist,
                                       filter it, put the files to the apl-pool
                                       and clear history or reread the jingle-dir)
pool [apl|jgl]                     --  print the filepool
history [apl|mnt]                  --  print the apl-history (songs added to
                                       playlist)
historyids                         --  give a comma-seperated list of IDs of songs
                                       added to the playlist by apl
quit                               --  Quit / Kill the deamon

You could try this when running the service:

echo "status apl" | nc 127.0.0.1 55443
(to show the AutoPlaylist Status)

watch -tn10 'echo history | nc 127.0.0.1 55443 | tail'
(this should look almost like your current MPD-Playlist)

If you haven't netcat installed you could use telnet:
(echo "status apl" ; sleep 1) | telnet 127.0.0.1 55443

"""
import sys, os, re, socketserver, cmd, configparser, mpmagic

### READ CONFIG ###

cffi = ["/etc/mpm.ini", 
        os.path.expanduser("~/.config/mpm/mpm.ini"), 
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "mpm.ini")]
cfg = configparser.SafeConfigParser()
if len(cfg.read(cffi)) == 0:
    print("No configfile found in", " or ".join(cffi))
    exit (1)

try:
    MAGIC_CONNECTION = (cfg.get("Service", "mpmhost"), cfg.getint("Service", "mpmport"))
    MPD_CONNECTION  =  (cfg.get("Service", "mpdhost"), cfg.getint("Service", "mpdport"))
except Exception as e:
    print("ERROR in config:", e)
    exit (1)


#################################################################################
## this class provides a simple command-based interface
#################################################################################
class CommandDispatcher(cmd.Cmd):

    booltab = {True: "enabled", False: "disabled"}

    def __init__(self): 
        cmd.Cmd.__init__(self)

        # create instances & load config
        for inst in (("apl", "AutoPlaylist"), ("jgl", "Jingle"), ("mnt", "Monitor")):
            exec("self.%s = mpmagic.%s(MPD_CONNECTION)" % inst)
            print("Loading config for", inst[1])
            try:
                for i in cfg.items(inst[1]): 
                    retv = eval("self."+inst[0]).validset(*i)
                    print("Set %s to %s :" % i, retv)
                    if retv != True: exit(1)
            except Exception as e:
                print("ERROR in "+inst[1]+"-config:", e)
                exit (1)
            print()
        # special treatment: Monitor needs the APL-instance.
        self.mnt.aplinstance = self.apl
        
        # now start the 3 services
        for inst in ("apl", "jgl", "mnt"): exec("self.%s.start()" % inst)

    def do_status(self, which):
        r=""
        which = which.lower()
        if which in ("apl", "jgl", "mnt"):
            for k,v in list(eval("self."+which).getconf().items()):
                if k in self.booltab: k = self.booltab[k]
                r+="%s\t%s\n" % (k, str(v))
        else:
            r+="invalid class-identifier (only \"apl\" \"jgl\" and \"mnt\" are valid)"
        return r

    def do_config(self, para):
        p_s = re.split("\s+", para, 2)
        if len(p_s) < 3: return "not enough arguments"
        whc = p_s[0].lower()
        if whc in ("apl", "jgl", "mnt"):
            return eval("self."+whc).validset(*p_s[1:])
        else:
            return "invalid class-identifier (only \"apl\" \"jgl\" and \"mnt\" are valid)"

    def do_refill(self, which):
        which = which.lower()
        if which in ("apl", "jgl"):
            try:
                if eval("self."+which).fillPool():
                    return "%s Pool refilled successful" % which
            except:
                pass
            return "Refilling the %s pool failed" % which
        else:
            return "invalid class-identifier (only \"apl\" and \"jgl\" are valid)"

    def do_pool(self, which):
        which = which.lower()
        if which in ("apl", "jgl"):
            return "\n".join(eval("self."+which).getpool())

    def do_history(self, which):
        which = which.lower()
        r = ""
        if which == "apl":
            for ts, tr in self.apl.gethist():
                r += "%s\t%s\n" % (ts, tr)
        elif which == "mnt":
            # there is no gethist() in Monitor but since it simply writes to a file, we can output that.
            # keep in mind, that this file (unlike apl-pool) can become very big, so you should consider using logrotate.
            try: 
                f = open (self.mnt.getconf()["logfile"], "r")
                for l in f: r += "%s\n" % l.strip()
                f.close()
            except:
                pass
        else:
            return "invalid class-identifier (only \"apl\" and \"mnt\" are valid)"
        return r
    
    def do_historyids(self, args=None):
        return ",".join(self.apl.gethistids())
    
    def do_quit(self, args=None):
        # configfile is NOT written on exit.
        # probably, a additional command can be implemented to store the config
        # but most likely, this is not needed.
        for inst in ("apl","jgl","mnt"): 
            eval("self."+inst).running = False
        print("Shutting down...")
        server.shutdown()
        return "MPM terminated.";
    
    def default(self, args=None):
       return "Unknown Command";

#################################################################################
## Server-Class
#################################################################################
class MagicHandler(socketserver.BaseRequestHandler):
    def handle(self): 
        s = self.request.recv(1024).strip()
        if len(s) > 0:
            self.request.send((str(cmddsp.onecmd(s.decode()))+"\n").encode())

if __name__ == "__main__":
    cmddsp = CommandDispatcher()
    server = socketserver.ThreadingTCPServer(MAGIC_CONNECTION, MagicHandler)
    server.serve_forever()


