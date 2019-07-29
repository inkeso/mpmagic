#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#       client.py
"""
=======================
MusicPlayerMagic-Client
=======================

OK, i have to admit, this is only a kind of telnet
"""
IP = '127.0.0.1'

import sys, socket

def mpmsend(command):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    s.connect((IP, 55443))
    s.send(command.encode())
    answer = s.recv(1024)
    s.close()
    return (answer.decode())

def main():
    if len(sys.argv) > 1:
        print(mpmsend(" ".join(sys.argv[1:])))
    else:
        print("AutoPlayList (apl) Status")
        print("=========================")
        print(mpmsend("status apl")) 

        print("Jingle (jgl) Status")
        print("===================")
        print(mpmsend("status jgl")) 

        print("monitor (mnt) Status")
        print("====================")
        print(mpmsend("status mnt")) 

    return 0

if __name__ == '__main__': main()
