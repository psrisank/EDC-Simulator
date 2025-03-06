from enum import IntEnum
from Packet import *
from Port import *
DEBUG = 0
from queue import Queue
from queue import Empty
from queue import Full
import copy


class State(IntEnum):
    M = 0
    O = 1
    E = 2
    S = 3
    I = 4

class Cache:
    class CacheLine:
        def __init__(self, addr=0x0, data=0x0, state=State.I, windowSize=4):
            self.addr = addr
            self.data = data
            self.state = state

            print(f"Created CacheLine with parameters:\n\taddr={hex(self.addr)}\n\tdata={hex(self.data)}") if DEBUG else None

    def __init__(self, cacheLineCnt=10):
        self.cacheLines = []
        self.LRUIdx = 0
        for i in range(cacheLineCnt):
            self.cacheLines.append(self.CacheLine(0x0, 0x0))


class ComputeNode:
    def __init__(self, id=0, cacheLineCnt=10):
        queueSize = 256

        self.id = id
        self.cache = Cache(cacheLineCnt)
        self.port = Port()
        self.instrQueue = []

        # maintain EVC, GRT, RTR queue
        self.EVCQueue = []
        self.GRTQueue = []
        self.RTRQueue = []
        self.windowSize = 4
        self.window = []
        self.prevQueue = "RTR"

        return


    def send(self, link):
        # Move from port into link
        try:
            pkt = self.port.EgressQueue.get_nowait()
        except Empty:
            return
        link.pushPkt(pkt, "downstream")
        return

    
    def receive(self, link):
        # Move from link into port
        pkt = link.getPkt("upstream")
        if (pkt == None):
            return
        self.port.IngressQueue.put_nowait(pkt)
        return

    # process packet in its queue
    def processInstructionQueue(self, global_time):
        if (len(self.instrQueue) > 0 and self.instrQueue[0] != None and self.instrQueue[0].time <= global_time):
            pkt = self.instrQueue.pop(0)
            pkt.time = global_time
            return pkt
        
        return None


    def processPacket(self, pkt, global_time):
        """
        First check if we need to retransmit a packet
        """

        # TODO: Deal with NACKS and ACKS



        match pkt.pktOp:
            case PacketOp.INV:
                # IMPLEMENT AFTER MOESI DONE
                return None
            case PacketOp.STF:
                # send a grant packet to the requestor
                new_pkt = Packet(PacketOp.GRT, self.id, 0, pkt.addr, (0, 0), pkt.src, None, global_time)
                self.GRTQueue.append(new_pkt)
                return
            case PacketOp.GRT:
                # Send an RDMA read or write
                return None
            case PacketOp.DATA:
                return None

    def periodicAction(self, global_time):
        """
        On every cycle, what does a compute node need to do?
            - arbitrate between each one of its queues (EVC, GRT, RTR, INST) (if in a round robin, we need a variable keeping track of which queue to access)
            - place that item on the egress port
            - read from ingress port and perform required actions
        """

        # Arbitrate between queues
        out_pkt = None
        try:
            if (self.prevQueue == "EVC"):
                out_pkt = self.GRTQueue.pop(0)
            elif (self.prevQueue == "GRT"):
                out_pkt = self.RTRQueue.pop(0)
            elif (self.prevQueue == "RTR"):
                out_pkt = self.processInstructionQueue(global_time)
            else:
                out_pkt = self.EVCQueue.pop(0)
        except IndexError:
            out_pkt = None




        if (out_pkt != None):
            out_pkt.src = self.id
            # Place a copy of this packet into a window in case of retransmit need
            pkt_copy = copy.deepcopy(out_pkt)
            self.window.append(pkt_copy)
            # Place packet into egress queue
            self.port.EgressQueue.put_nowait(out_pkt)




        # Now attempt to read from ingress queue
        try:
            in_pkt = self.port.IngressQueue.get_nowait()
        except Empty:
            in_pkt = None

        if (in_pkt != None):
            self.processPacket(in_pkt, global_time)

        

        

    







    