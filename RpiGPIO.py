from SWDErrors import *
import time
import RPi.GPIO as GPIO

# --- BeagleBoneSWD
# Use of BeableBone GPIO to pilot SWD signal
# (c) Paul Pinault - www.disk91.com
#
# Usage :
#    GPIO18 is connected to SWD_CLK signal
#    GPIO23 is connected to SWD_IO signal
#   3.3V    1  2
#           3  4
#           5  6   GND
#           7  8
#           9  10
#          11  12  GPIO18
#          13  14
#          15  16  GPIO23
#         ...  ...
# Add in the header of the existing files
#    from RpiSWD import *
# Modify existing files to use BeagleBoneSWD :
#    busPirate = PirateSWD("/dev/ttyUSB0")
#    busPirate = RpiSWD("")
#
class RpiSWD:

    def __init__ (self,notused, vreg):
        GPIO.setmode(GPIO.BCM)
        self.SWDIO = 23
        self.SWDCK = 18
        self.debug = False
        self.debugFull = False
        GPIO.setup(self.SWDIO, GPIO.OUT)
        GPIO.output(self.SWDIO, GPIO.LOW)
        GPIO.setup(self.SWDCK, GPIO.OUT)
        GPIO.output(self.SWDCK, GPIO.HIGH)

        self.sendBytes([0xFF] * 8)
        self.sendBytes([0x00] * 8)
        self.sendBytes([0xFF] * 8)
        self.sendBytes([0x79, 0xE7]) # activate SWD interface
        self.resyncSWD()

    def resetBP (self):
            print "DEBUG : resetBP"

    def tristatePins (self):
            print "DEBUG : tristatePins"

    # this is the fastest port-clearing scheme I could devise
    def clear (self, more = 0):
            print "DEBUG : clear"

    def short_sleep(self):
        #time.sleep(0.0001)
        i=0

    def readBits (self, count):
        GPIO.setup(self.SWDIO, GPIO.IN)
        ret = []
        for x in xrange(0, count):
           GPIO.output(self.SWDCK,GPIO.HIGH)
           self.short_sleep()
           GPIO.output(self.SWDCK,GPIO.LOW)
           if GPIO.input(self.SWDIO):
              ret.append(1) 
           else:
              ret.append(0)
           self.short_sleep()

        GPIO.setup(self.SWDIO, GPIO.OUT)
        GPIO.output(self.SWDIO, GPIO.LOW)
        if self.debug:
           print "DEBUG - readBits(%d)" % count + "values - %s" %ret
        return ret

    def sendBits ( self, bits ):
           for b in bits:
                    if b == 0 :
                       GPIO.output(self.SWDIO, GPIO.LOW)
                       if self.debugFull:
                          print "DEBUG - writeBits 0"
                    else: 
                       GPIO.output(self.SWDIO, GPIO.HIGH)
                       if self.debugFull:
                          print "DEBUG - writeBits 1"
                    GPIO.output(self.SWDCK,GPIO.HIGH)
                    self.short_sleep()
                    GPIO.output(self.SWDCK,GPIO.LOW)
                    self.short_sleep()

    def skipBits (self, count):
        if self.debug:
           print "DEBUG - skipBits(%d)" % count
        self.readBits (count)

    def readBytes (self, count):
        ret = []
        for x in xrange(0, count):
                v = self.readBits(8)
                k = 0
                for i in v:
                        k = 2*k + i
                ret.append(k);
        if self.debug:
           print "DEBUG - readBytes : %s " % ret
        return ret

    def sendBytes (self, data):
        if self.debug:
           print "DEBUG - sendBytes %s" % data    
        for v in data:
                db = [int(( v >> y) & 1) for y in range(7,-1, -1)]
                self.sendBits(db)
                #self.sendBits(db[::-1])

    def resyncSWD (self):
        self.sendBytes([0xFF] * 8)
        self.sendBytes([0x00] * 8)

    def readSWD (self, ap, register):
        if self.debug:
           print "DEBUG - readSWD %s " % [calcOpcode(ap, register, True)]
        # transmit the opcode
        self.sendBytes([calcOpcode(ap, register, True)])
        # check the response
        ack = self.readBits(3)
        if ack[0:3] != [1,0,0]:
            if   ack[0:3] == [0,1,0]:
                raise SWDWaitError(ack[0:3])
            elif ack[0:3] == [0,0,1]:
                raise SWDFaultError(ack[0:3])
            else:
                raise SWDProtocolError(ack[0:3])
        # read the next 4 bytes
        data = [reverseBits(b) for b in self.readBytes(4)]
        data.reverse()
        # read the parity bit and turnaround period
        extra = self.readBits(3)
        # check the parity
        if sum([bitCount(x) for x in data[0:4]]) % 2 != extra[0]:
            raise SWDParityError()
        # idle clocking to allow transactions to complete
        self.sendBytes([0x00])
        self.sendBytes([0x00])
        # return the data
        return (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3]

    def writeSWD (self, ap, register, data, ignoreACK = False):
        if self.debug:
           print "DEBUG - writeSWD %s " % [calcOpcode(ap, register, False)]
        # transmit the opcode
        self.sendBytes([calcOpcode(ap, register, False)])
        # check the response if required
        if ignoreACK:
            self.skipBits(5)
        else:
            ack = self.readBits(5)
            #print ack
            if ack[0:3] != [1,0,0]:
                if ack[0:3] == [0,1,0]:
                    raise SWDWaitError(ack[0:3])
                elif ack[0:3] == [0,0,1]:
                    raise SWDFaultError(ack[0:3])
                else:
                    raise SWDProtocolError(ack[0:3])
        # mangle the data endianness
        payload = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        payload[0] = reverseBits((data >>  0) & 0xFF)
        payload[1] = reverseBits((data >>  8) & 0xFF)
        payload[2] = reverseBits((data >> 16) & 0xFF)
        payload[3] = reverseBits((data >> 24) & 0xFF)
        # add the parity bit
        if sum([bitCount(x) for x in payload[0:4]]) % 2:
            payload[4] = 0x80
        # output the data, idle clocking is on the end of the payload
        self.sendBytes(payload)

def bitCount(int_type):
    count = 0
    while(int_type):
        int_type &= int_type - 1
        count += 1
    return(count)

def reverseBits (x):
    a = ((x & 0xAA) >> 1) | ((x & 0x55) << 1)
    b = ((a & 0xCC) >> 2) | ((a & 0x33) << 2)
    c = ((b & 0xF0) >> 4) | ((b & 0x0F) << 4)
    return c

def calcOpcode (ap, register, read):
    opcode = 0x00
    opcode = opcode | (0x20 if read else 0x00)
    opcode = opcode | (0x40 if ap else 0x00)
    opcode = opcode | ((register & 0x01) << 4) | ((register & 0x02) << 2)
    opcode = opcode | ((bitCount(opcode) & 1) << 2)
    opcode = opcode | 0x81
    return opcode
