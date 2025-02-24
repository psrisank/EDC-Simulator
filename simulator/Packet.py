from enum import IntEnum

class IPGPacketType(IntEnum):
    LD_REQ = 0 # Load request
    ST_REQ = 1 # Store request
    EVC = 2 # Eviction notice
    GRT = 3 # Grant
    INV = 4 # Invalidation
    STF = 5 # State change

class Packet():
    def __init__(self, pktOp=IPGPacketType.LD_REQ, src=0, len=0, addr=0x0, ackid=0, dst=0, invalidations=None, time=0):
        self.pktOp = pktOp
        self.src = src
        self.len = len
        self.addr = addr
        self.ackid = ackid
        self.dst = dst
        self.invalidations = invalidations
        self.time = time

    def __str__(self):
        return f"Packet:\n\tTime: {self.time}\n\tSrc: {self.src}\n\tDst: {self.dst}\n\tLen: {self.len}\n\tMemory Address: {self.addr}"
    
    def periodicUpdate(self):
        self.time += 1
