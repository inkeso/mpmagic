#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
========================
|   MusicPlayerMagic   |
========================
"""
import os, time, re, random, threading, mpd

DEBUG=True

### SOME HELPERS ###

def tobool(what):
    try:
        ws = str(what).upper()
    except Exception, e:
        if DEBUG: print e
    if ws in ("YES", "ON",  "1", "T", "TRUE",  "ENABLE" ): return True
    if ws in ("NO",  "OFF", "0", "F", "FALSE", "DISABLE"): return False
    return None

def checkregex(what):
    try:
        re.compile(str(what))
        return True
    except:
        return False

def iswritable(what):
    try:
        x = open(what, "a")
        x.close()
        return True
    except:
        return False



### THE AUTOMAGIC PLAYLIST ###

class AutoPlaylist(threading.Thread):
    def __init__(self, mpdconnection):
        threading.Thread.__init__(self)
        self.MPD_CONNECTION = mpdconnection
        self.mc = mpd.MPDClient()
        self.__config = {}
        # When auto-adding, files are moved from pool to history (with timestamp)
        self.__tPool = []
        self.__tHist = []
        self.__tHistIds = []

    def getpool(self): return self.__tPool
    def gethist(self): return self.__tHist
    def gethistids(self): return self.__tHistIds
    def getconf(self): return self.__config

    def validset(self, what, val=""):
        """validate setting and write to config, if everything is fine"""
        valid = {
            "addfiles"  : [int,    lambda x: x in range (1, 101)],
            "keepfiles" : [int,    lambda x: x in range (1, 101)],
            "service"   : [tobool, lambda x: x != None],
            "blacklist" : [str,    checkregex],
            "interval"  : [int,    lambda x: x in range (2, 121)]
        }
        # Step 1: check key & cast value
        try: cval = valid[what][0](val)
        except: return "invalid config-parameter or value-type"
        # Step 2: check value & set key to value
        if valid[what][1](cval): self.__config[what] = cval
        else: return "value out of range or not valid"
        return True

    # get a list of all tracks from MPD, filter the blacklisted music out,
    # empty the History and update all READABLE.
    def fillPool(self):
        self.__tPool = []
        self.__tHist = []
        try:
            if self.mc.mpd_version is None:
                self.mc.connect(*self.MPD_CONNECTION)
            verilen = int(self.mc.stats()["songs"])
            listall = self.mc.listall()
            self.mc.disconnect()
        except Exception, e:
            print "apl.fillpool:", e
            return False
        blc = 0
        black = re.compile(self.__config["blacklist"])
        # temp: export blacklist
        blf = open("/tmp/mpm_blacklist.txt", "w")
        for song in listall:
            if "file" in song:
                if not black.search(song["file"]):
                    self.__tPool.append(song["file"])
                else:
                    blf.write(song["file"]+"\n")
                    blc+=1
        blf.close()
        self.__config["played"] = 0
        self.__config["remain"] = len(self.__tPool)
        #self.__config["blacklist"] = blc
        self.__config["blacklistlen"] = blc
        if DEBUG: print "apl.fillpool:", len(self.__tPool), "songs"
        return (verilen == blc + len(self.__tPool))

    def run(self):
        self.fillPool()
        self.running = True
        while self.running:
            for slp in range(self.__config["interval"]):
                time.sleep(1)
                if not self.running: break
                
            if not self.__config["service"]: continue

            # connect to server, check playliststatus
            s = { "playlistlength": -1, "song": -1}

            try:    self.mc.connect(*self.MPD_CONNECTION)
            except Exception, e:
                print "apl.connect:", e

            try:    s = self.mc.status()
            except Exception, e:
                print "apl.status:", e
            ll = int(s["playlistlength"])
            cs = 0 # try, because there may be no song attribute.
            try:    cs = int(s["song"])
            except: pass

            poolen = len(self.__tPool)
            if poolen == 0:
                try:
                    self.fillPool()
                except Exception, e:
                    print "apl.fillpool:", e
                    continue

            if (cs >= 0) and (ll >= 0):
                for x in range (ll - cs, self.__config["addfiles"]+1):
                    # take a random song from the pool
                    if poolen == 0:
                        break
                    else:
                        poolen -= 1
                    randompool = random.randint(0,poolen)
                    randomsong = self.__tPool.pop(randompool)
                    # try to add it to the playlist
                    try:
                        if DEBUG: print "apl.add:", randomsong
                        nid = self.mc.addid(randomsong)
                        # successful? Than add to History (including timestamp) and ID to HistIds
                        self.__tHist.append((time.strftime("%a, %d. %b %Y %X"), randomsong))
                        self.__tHistIds.append(str(nid))
                    except Exception, e:
                        print "apl.add:", e, randomsong
                        # something went wrong, so just throw the song away.
                        # previously, it was added to the pool again, resulting in a never-empty
                        # pool of unavailable files.
                        # self.__tPool.append(randomsong)
                        poolen+=1

                # delete old songs from playlist (and IDs from HistIds)
                try:
                    for x in range(self.__config["keepfiles"], cs):
                        did = self.mc.playlistinfo()[0]["id"]
                        if did in self.__tHistIds:
                            self.__tHistIds.remove(did)
                        else: 
                            self.mc.delete(0)
                except Exception, e: 
                    print "apl.delete:", e

            # update counts
            self.__config["remain"] = poolen
            self.__config["played"] = len(self.__tHist)

            try:    self.mc.disconnect()
            except Exception, e:
                if DEBUG: print "apl.disconnect:", e


### PLAY JINGLES ###

class Jingle(threading.Thread):
    def __init__(self, mpdconnection):
        threading.Thread.__init__(self)
        self.MPD_CONNECTION = mpdconnection
        self.mc = mpd.MPDClient()
        self.__config = {}
        self.__tPool = []

    def getpool(self): return self.__tPool
    def getconf(self): return self.__config

    def validset(self, what, val=""):
        """validate setting and write to config, if everything is fine"""
        valid = {
            "dir"      : [str,    os.path.isdir],
            "ext"      : [str,    checkregex],
            "service"  : [tobool, lambda x: x != None],
            "player"   : [str,    lambda x: "%s" in x],
            "minpause" : [int,    lambda x: 0 < x], # < self.__config["maxpause"]
            "maxpause" : [int,    lambda x: self.__config["minpause"] < x],
            "fadeup"   : [int,    lambda x: x in range(1,101)],
            "fadedown" : [int,    lambda x: x in range(1,101)],
            "fadestep" : [int,    lambda x: x in range(1,101)],
            "fademsec" : [int,    lambda x: x in range(1,101)],
            "secsleft" : [int,    lambda x: x in range(2,1001)]

        }
        # Step 1: check key & cast value
        try: cval = valid[what][0](val)
        except: return "invalid config-parameter or value-type"
        # Step 2: check value & set key to value
        if valid[what][1](cval): self.__config[what] = cval
        else: return "value out of range or not valid"
        return True

    def fade(self, inout="out"):
        faderange = range(self.__config["fadedown"],
                          self.__config["fadeup"],
                          self.__config["fadestep"])
        if inout == "out": faderange.reverse()
        if DEBUG: print "jgl.fade:", inout, faderange
        try:
            self.mc.connect(*self.MPD_CONNECTION)
            for vol in faderange:
                self.mc.setvol(vol)
                time.sleep(self.__config["fademsec"] / 100.0)
            self.mc.disconnect()
        except Exception, e:
            print ("jgl.fade(%s):" % inout), e

    def fillPool(self):
        self.__tPool = []
        white = re.compile(self.__config["ext"])
        for f in os.listdir(self.__config["dir"]):
            if white.search(f):
                self.__tPool.append(os.path.join(self.__config["dir"],f))
        self.__config["jingles"] = len(self.__tPool)
        return (len(self.__tPool) > 0)

    def run(self):
        self.fillPool()
        self.running = True
        while self.running:
            ranti = random.randint(self.__config["minpause"],
                                   self.__config["maxpause"]) * 60
            self.__config["nextjingle"] = int(time.time()+ranti)
            # split the time.sleep into slices to allow thread-termination
            for slt in range(ranti):
                time.sleep(1)
                if not self.running: break
            if not self.__config["service"]: continue

            # prepare the play-command
            pjing = self.__config["player"] % random.choice(self.__tPool)

            # connect to server, check songstatus every second.
            # If there are (less than) 10 sec. left in a song, play a jingle
            jinged = False
            while not jinged and self.running:
                # connect to server, check playliststatus
                s = { "time": "", "state": ""}
                tl = 0x7fffff # seconds remaining in the song
                try:    self.mc.connect(*self.MPD_CONNECTION)
                except Exception, e:
                    print "jgl.connect:", e

                try:    s = self.mc.status()
                except Exception, e:
                    print "jgl.status:", e

                try:    self.mc.disconnect()
                except Exception, e:
                    print "jgl.disconnect:", e

                try:
                    st = s["time"].split(":")
                    tl = int(st[1]) - int(st[0])
                except:
                    pass

                # skip this jingle, if music is not playing.
                if tl <= self.__config["secsleft"] and s["state"] == "play":
                    self.fade("out")
                    os.system(pjing)
                    if DEBUG: print "playing jingle", pjing
                    self.fade("in")
                    jinged = True

                time.sleep(1)


### LOG CURRENT SONG ###

class Monitor(threading.Thread):
    def __init__(self, mpdconnection):
        threading.Thread.__init__(self)
        self.MPD_CONNECTION = mpdconnection
        self.mc = mpd.MPDClient()
        self.__config = {}
        # also set self.aplinstance before running this to store whether a track
        # is added by APL or not
    
    def getconf(self): return self.__config
    
    def validset(self, what, val=""):
        """validate setting and write to config, if everything is fine"""
        valid = {
            "service"   : [tobool, lambda x: x != None],
            "logfile"   : [str,    iswritable],
            "interval"  : [int,    lambda x: x in range (2, 121)]
        }
        # Step 1: check key & cast value
        try: cval = valid[what][0](val)
        except: return "invalid config-parameter or value-type"
        # Step 2: check value & set key to value
        if valid[what][1](cval): self.__config[what] = cval
        else: return "value out of range or not valid"
        return True

    def run(self):
        lastsong = ["" ,0, False] # filename, duration (secs) and magic
        lasttime = int(time.time())
        self.running = True
        while self.running:
            for slp in range(self.__config["interval"]):
                time.sleep(1)
                if not self.running: break
            if not self.__config["service"]: continue
            
            # connect to server, check songstatus
            s = lastsong
            try:    self.mc.connect(*self.MPD_CONNECTION)
            except Exception, e:
                print "mnt.connect:", e
            
            try:
                x = self.mc.currentsong()
                autoadded = self.aplinstance and x["id"] in self.aplinstance.gethistids()
                s = [x["file"], int(x["time"]), autoadded]
            except Exception, e:
                print "mnt.status:", e
            
            try:
                self.mc.disconnect()
            except Exception, e:
                print "mnt.disconnect:", e
            
            # different/new song?
            if lastsong[0] != s[0]:
                f = open(self.__config["logfile"], "a")
                # check if last song was skipped
                if (lasttime + s[1]) > int(time.time() + self.__config["interval"]):
                    f.write("[SKIP]")
                    if DEBUG: print "mnt.log: [SKIP]"
                # write new song to log
                f.write(time.strftime("\n[%a, %d. %b %Y %X]\t"))
                f.write(("[HUMAN]", "[MAGIC]")[s[2]])
                f.write("\t"+s[0]+"\t")
                f.write(time.strftime("%H:%M:%S\t", time.gmtime(s[1])))
                f.close()
                if DEBUG: print "mnt.log:", s
                lastsong = s
                lasttime = int(time.time())
        
