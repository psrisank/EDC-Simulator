from enum import IntEnum

class PacketOp(IntEnum):
    LD_REQ = 0 # Load request
    ST_REQ = 1 # Store request
    EVC = 2 # Eviction notice
    GRT = 3 # Grant
    INV = 4 # Invalidation
    STF = 5 # State change
    DATA = 6 # standard data packet
    RDMA_READ = 7
    RDMA_WRITE = 8

class Packet():
    def __init__(self, pktOp=PacketOp.LD_REQ, src=0, len=0, addr=0x0, ackid=(0,1), dst=0, invalidations=None, time=0, data=0xDEADBEEF):
        self.pktOp = pktOp
        self.src = src
        self.len = len
        self.addr = addr
        self.ackid = ackid # empty if retransmitting (for the future)
        self.dst = dst
        self.invalidation_bitmap = invalidations
        self.timeToLeave = time
        self.data = data
        # record time to leave in switch
        # isAck field (1 bit)


    def __str__(self):
        return f"Packet:\n\tTime: {self.time}\n\tSrc: {self.src}\n\tDst: {self.dst}\n\tLen: {self.len}\n\tMemory Address: {self.addr}"
    
    def periodicUpdate(self):
        self.time += 1
