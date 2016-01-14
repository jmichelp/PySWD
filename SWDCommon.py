import sys
import time

class DebugPort:
    ID_CODES = {
            0x1BA01477: "EFM32", # EFM32
            0x2BA01477: "STM32", # STM32
            0x0BB11477: "NUC1xx", # NUC1xx
        }
    def __init__ (self, swd):
        self.swd = swd
        # read the IDCODE
        # Hugo: according to ARM DDI 0316D we should have 0x2B.. not 0x1B.., but 
        # 0x1B.. is what upstream used, so leave it in here...
        idcode = self.idcode()
        if idcode not in DebugPort.ID_CODES.keys():
            print "warning: unexpected idcode: ", idcode
        else:
            print "Got IDCODE %s [0x%08x]" % (DebugPort.ID_CODES[idcode], idcode)
        # power shit up
        self.swd.writeSWD(False, 1, 0x54000000)
        if (self.status() >> 24) != 0xF4:
            print "error powering up system"
            sys.exit(1)
        # get the SELECT register to a known state
        self.select(0,0)
        self.curAP = 0
        self.curBank = 0

    def idcode (self):
        return self.swd.readSWD(False, 0)

    def abort (self, orunerr, wdataerr, stickyerr, stickycmp, dap):
        value = 0x00000000
        value = value | (0x10 if orunerr else 0x00)
        value = value | (0x08 if wdataerr else 0x00)
        value = value | (0x04 if stickyerr else 0x00)
        value = value | (0x02 if stickycmp else 0x00)
        value = value | (0x01 if dap else 0x00)
        self.swd.writeSWD(False, 0, value)

    def status (self):
        return self.swd.readSWD(False, 1)

    def control (self, trnCount = 0, trnMode = 0, maskLane = 0, orunDetect = 0):
        value = 0x54000000
        value = value | ((trnCount & 0xFFF) << 12)
        value = value | ((maskLane & 0x00F) << 8)
        value = value | ((trnMode  & 0x003) << 2)
        value = value | (0x1 if orunDetect else 0x0)
        self.swd.writeSWD(False, 1, value)

    def select (self, apsel, apbank):
        value = 0x00000000
        value = value | ((apsel  & 0xFF) << 24)
        value = value | ((apbank & 0x0F) <<  4)
        self.swd.writeSWD(False, 2, value)

    def readRB (self):
        return self.swd.readSWD(False, 3)

    def readAP (self, apsel, address):
        adrBank = (address >> 4) & 0xF
        adrReg  = (address >> 2) & 0x3
        if apsel != self.curAP or adrBank != self.curBank:
            self.select(apsel, adrBank)
            self.curAP = apsel
            self.curBank = adrBank
        return self.swd.readSWD(True, adrReg)

    def writeAP (self, apsel, address, data, ignore = False):
        adrBank = (address >> 4) & 0xF
        adrReg  = (address >> 2) & 0x3
        if apsel != self.curAP or adrBank != self.curBank:
            self.select(apsel, adrBank)
            self.curAP = apsel
            self.curBank = adrBank
        self.swd.writeSWD(True, adrReg, data, ignore)

class MEM_AP:
    def __init__ (self, dp, apsel):
        self.dp = dp
        self.apsel = apsel
        self.csw(1,2) # 32-bit auto-incrementing addressing

    def csw (self, addrInc, size):
        """ Set control/status word register """
        self.dp.readAP(self.apsel, 0x00)
        csw = self.dp.readRB() & 0xFFFFFF00
        self.dp.writeAP(self.apsel, 0x00, csw + (addrInc << 4) + size)

    def idcode (self):
        self.dp.readAP(self.apsel, 0xFC)
        return self.dp.readRB()

    def readWord (self, adr):
        self.dp.writeAP(self.apsel, 0x04, adr)
        self.dp.readAP(self.apsel, 0x0C)
        return self.dp.readRB()

    def writeWord (self, adr, data):
        self.dp.writeAP(self.apsel, 0x04, adr)
        self.dp.writeAP(self.apsel, 0x0C, data)
        return self.dp.readRB()

    def readBlock (self, adr, count):
        self.dp.writeAP(self.apsel, 0x04, adr)
        vals = [self.dp.readAP(self.apsel, 0x0C) for off in range(count)]
        vals.append(self.dp.readRB())
        return vals[1:]

    def writeBlock (self, adr, data):
        self.dp.writeAP(self.apsel, 0x04, adr)
        for val in data:
            time.sleep(0.01)
            self.dp.writeAP(self.apsel, 0x0C, val)

    def writeBlockNonInc (self, adr, data):
        self.csw(0, 2) # 32-bit non-incrementing addressing
        self.dp.writeAP(self.apsel, 0x04, adr)
        for val in data:
            self.dp.writeAP(self.apsel, 0x0C, val)
        self.csw(1, 2) # 32-bit auto-incrementing addressing

    def writeHalfs (self, adr, data):
        """ Write half-words """
        self.csw(2, 1) # 16-bit packed-incrementing addressing
        self.dp.writeAP(self.apsel, 0x04, adr)
        for val in data:
            time.sleep(0.001)
            self.dp.writeAP(self.apsel, 0x0C, val, ignore = True)
        self.csw(1, 2) # 32-bit auto-incrementing addressing
