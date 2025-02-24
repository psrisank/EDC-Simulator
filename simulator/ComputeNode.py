from enum import IntEnum
from Packet import *
from Port import *
DEBUG = 0
from queue import Queue
from queue import Empty
from queue import Full


class State(IntEnum):
    M = 0
    O = 1
    E = 2
    S = 3
    I = 4

class Cache:
    class CacheLine:
        def __init__(self, addr=0x0, data=0x0, state=State.I):
            self.addr = addr
            self.data = data
            self.state = state
            self.LRUIdx = 0
            print(f"Created CacheLine with parameters:\n\taddr={hex(self.addr)}\n\tdata={hex(self.data)}") if DEBUG else None

    def __init__(self, cacheLineCnt=10):
        self.cacheLines = []
        for i in range(cacheLineCnt):
            self.cacheLines.append(self.CacheLine(0x0, 0x0))


class ComputeNode:
    def __init__(self, id=0, cacheLineCnt=10):
        queueSize = 256

        self.id = id
        self.cache = Cache(cacheLineCnt)
        self.port = Port()
        self.instrQueue = []

    # process packet in its queue
    def processInstructionQueue(self, global_time):
        if (len(self.instrQueue) > 0 and self.instrQueue[0] != None and self.instrQueue[0].time <= global_time):
            pkt = self.instrQueue.pop(0)
            pkt.time = global_time
            try:
                self.port.TX.put_nowait(pkt)
            except Full:
                self.instrQueue.insert(0, pkt)
    

    def processTXPort(self, global_time, switch):
        # in_pkt = Queue()
        try:
            in_pkt = self.port.TX.get_nowait()
        except Empty:
            print(f"Compute ID {self.id} TX is empty") if DEBUG else None
            return

        try:
            switch.top_ports[self.id].RX.put_nowait(in_pkt)
            print(f"Size of RX queue : {switch.top_ports[self.id].RX.qsize()}")
        except Full:
            print(f"Switch ingress queue full for port {self.id}") if DEBUG else None
            return
    
        return




    