#!/usr/bin/env python
# -*- coding: utf-8 -*-

#       client.py
"""
=======================
MusicPlayerMagic-Client
=======================

OK, i have to admit, this is only a kind of telnet
"""
IP = '127.0.0.1'

import socket

def mpmsend(command):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    s.connect((IP, 55443))
    s.send(command)
    answer = s.recv(1024)
    s.close()
    return (answer)

def main():
    print "AutoPlayList (apl) Status"
    print "========================="
    print mpmsend("status apl") 

    print "Jingle (jgl) Status"
    print "==================="
    print mpmsend("status jgl") 

    print "monitor (mnt) Status"
    print "===================="
    print mpmsend("status mnt") 

    return 0

if __name__ == '__main__': main()

