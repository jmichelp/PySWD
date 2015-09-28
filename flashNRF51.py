#!/usr/bin/python

import time
import sys
import array

from PirateSWD import *
from SWDCommon import *
from EFM32 import *

def loadFile(path):
    arr = array.array('I')
    try:
        arr.fromfile(open(sys.argv[1], 'rb'), 1024*1024)
    except EOFError:
        pass
    return arr.tolist()

def main():
    busPirate = RpiSWD("", vreg = True)
    debugPort = DebugPort(busPirate)
    efm32     = EFM32(debugPort)

    part_info = efm32.ahb.readWord(0x0FE081FC) # PART_NUMBER, PART_FAMILY, PROD_REV
    mem_info = efm32.ahb.readWord(0x0FE081F8)  # MEM_INFO_FLASH, MEM_INFO_RAM
    rev = (efm32.ahb.readWord(0xE00FFFE8) & 0xF0) | ((efm32.ahb.readWord(0xE00FFFEC) & 0xF0) >> 4) # PID2 and PID3 - see section 7.3.4 in reference manual
    rev = chr(rev + ord('A'))
    flash_size = mem_info & 0xFFFF
    if (part_info >> 16 & 0xFF) == 71:
        print "Connected."
        print "Part number: EFM32G%dF%d (rev %c, production ID %dd)" % (part_info & 0xFF, 
                flash_size, rev, part_info >> 24 & 0xFF)
    else:
        print "Warning: unknown part"
        sys.exit()
    print "Loading '%s'..." % sys.argv[1],
    vals = loadFile(sys.argv[1])
    size = len(vals) * 4
    print "%d bytes." % size
    if size / 1024.0 > flash_size:
        print "Firmware will not fit into flash!"
        sys.exit(1)

    efm32.halt()
    efm32.flashUnlock()
    print "Erasing Flash...",
    efm32.flashErase(flash_size)
    start_time = time.time()
    print "Programming Flash...",
    efm32.flashProgram(vals)
    time_passed = time.time() - start_time
    print "Programmed %d bytes in %.2f seconds (%.2f kB/sec)." % (size,
            time_passed, (size / 1024.0) / time_passed)

    print "Resetting"
    efm32.sysReset()
    busPirate.tristatePins()

if __name__ == "__main__":
    main()
