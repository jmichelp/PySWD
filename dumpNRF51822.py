#!/usr/bin/python

import time
import sys
import array

import PirateSWD
import SWDCommon
import NUC1XX

def loadFile(path):
    arr = array.array('I')
    try:
        arr.fromfile(open(sys.argv[1], 'rb'), 1024*1024)
    except EOFError:
        pass
    return arr.tolist()

def main(port):
    if not port:
        port = "/dev/buspirate"
    busPirate = PirateSWD.PirateSWD(port, vreg = True)
    debugPort = SWDCommon.DebugPort(busPirate)
    chip     = NUC1XX.NUC1XX(debugPort)

    print "Config: 0x%08x" % chip.readConfig()
    chip.halt()
    print "Config: 0x%08x" % chip.readConfig()

    print "Resetting"
    chip.reset()
    busPirate.tristatePins()

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) == 2 else None)
