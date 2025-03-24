from enum import IntEnum
from Packet import *
from Port import *
DEBUG = 0
from queue import Queue
from queue import Empty
from queue import Full
import copy
import random

class State(IntEnum):
    # M = 0
    # O = 1
    # E = 2
    # S = 3
    # I = 4
    M = 0
    S = 1
    I = 2

class Cache:
    class CacheLine:
        def __init__(self, addr=0x0, data=0x0, state=State.I):
            self.addr = addr
            self.data = data
            self.state = state

            print(f"Created CacheLine with parameters:\n\taddr={hex(self.addr)}\n\tdata={hex(self.data)}") if DEBUG else None


    def __init__(self, cacheLineCnt=10):
        self.cacheLines = []
        self.LRUIdx = 0
        for i in range(cacheLineCnt):
            self.cacheLines.append(self.CacheLine(0x0, 0x0, State.I))


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
        self.requestQueue = []
        self.windowSize = 1
        self.window = []
        self.prevQueue = "RTR"
        self.transaction = None
        self.busy = 0

        self.unfinished_transaction = 0

        return

    def send(self, link, global_time):
        # Move from port into link
        try:
            if ((self.port.EgressQueue.queue[0].timeToLeave) <= global_time):
                print(f"Compute Node {self.id} sending a packet at time {global_time}")
                pkt = self.port.EgressQueue.get_nowait()
            else:
                return
        except (Empty, IndexError):
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


    def findDataIdx(self, addr):
        for cacheLineidx, cacheLine in enumerate(self.cache.cacheLines):
            if (cacheLine.addr == addr):
                return cacheLineidx
        return None

    def findData(self, addr):
        for cacheLine in self.cache.cacheLines:
            if (cacheLine.addr == addr):
                return cacheLine.data
        return None


    def updateLRU(self):
        self.cache.LRUIdx += 1
        if (self.cache.LRUIdx >= len(self.cache.cacheLines)):
            self.cache.LRUIdx = 0
        return



    # process packet in its queue
    def processInstructionQueue(self, global_time):
        # If there is a pending transaction, we need to wait for that to finish before we can continue
        if (self.transaction != None):
            return
        

        # Make sure there is an instruction to even read
        try:
            instruction = self.instrQueue[0]
        except IndexError:
            return
        
        if (self.instrQueue[0].timeToLeave > global_time):
            return

        # If we can proceed, check if we need to evict a cache line or if address is in cache and is valid
        cacheIdx = self.findDataIdx(self.instrQueue[0].addr)

        idx_found = False
        # If the data isn't in the cache, we need to select a victim candidate
        if (cacheIdx == None):
            # If not in cache, we might need to evict. The process to evict is to check if there are any invalid cache lines. If there are, we can just overwrite that line. We should record this address in LRUidx.
            for cacheindex, cacheLine in enumerate(self.cache.cacheLines):
                if (cacheLine.state == State.I):
                    self.cache.LRUIdx = cacheindex
                    idx_found = True
                    # Send a request packet to mem node
                    inst_copy = copy.deepcopy(self.instrQueue[0])
                    self.transaction = inst_copy
                    self.requestQueue.append(self.instrQueue.pop(0))
                    break

            # If we didn't find any invalid cache lines, we need to evict the LRU cache line
            # Pick a random cache line to evict
            if (idx_found == False):
                self.cache.LRUIdx = random.randint(0, len(self.cache.cacheLines) - 1)
                mem_node = self.cache.cacheLines[self.cache.LRUIdx].addr % 128
                evc_pkt = Packet(PacketOp.EVC, self.id, 0, self.cache.cacheLines[self.cache.LRUIdx].addr, (0, 0), mem_node, None, global_time, None)
                self.transaction = copy.deepcopy(evc_pkt) # Save the eviction as a transaction. Transactions get cleared in process pkt anyway
                self.EVCQueue.append(evc_pkt)



        # Suppose we do find it, we need to check if the data is valid. If it is, we just do the action and remove the instruction from the queue
        else:
            self.cache.LRUIdx = cacheIdx
            match self.cache.cacheLines[cacheIdx].state:
                # If invalid, we need to send a request to memory node
                case State.I:
                    inst_copy = copy.deepcopy(self.instrQueue[0])
                    self.requestQueue.append(self.instrQueue.pop(0))
                    self.transaction = inst_copy
                    print("Transaction is an READ/WRITE")
                    return
                # If shared, and we are reading, we can just read from the cache. Else, we need to send a request to memory node
                case State.S:
                    if (self.instrQueue[0].pktOp == PacketOp.LD_REQ):
                        self.instrQueue.pop(0)
                        self.transaction = None
                        return
                    else:
                        inst_copy = copy.deepcopy(self.instrQueue[0])
                        self.transaction = inst_copy
                        print("Transaction is a WRITE")
                        self.requestQueue.append(self.instrQueue.pop(0))
                        return
                # If modified, we can just read from the cache
                case State.M:
                    self.instrQueue.pop(0)
                    self.transaction = None
                    return

        return
    

    """
    Protcol specific processing of packets
    Currently implemented:
        - MSI
    To implement:
        - MOESI
        - MESI
    """
    def processMSI(self, pkt, global_time):



        # first, check if we need to retransmit a packet
        # ACK
        # if (pkt.ackid == (1, 0)):
        #     print(f"Compute Node {self.id} received an ACK at time {global_time}")
        #     self.pending_transaction = self.window.pop(0)
        #     if (len(self.window) < self.windowSize):
        #         self.unfinished_transaction = 0


        # If NACK we need to resend the packet
        if (pkt.ackid == (0, 1)):
            print(f"Compute Node {self.id} received a NACK at time {global_time} from {pkt.src}")
            rtr_pkt = self.window
            rtr_pkt.timeToLeave = global_time
            self.RTRQueue.append(rtr_pkt)
            self.window = None
        # If we get ACK we can remove from the "window" but not the transaction
        elif (pkt.ackid == (1, 0)):
            print(f"Compute node {self.id} recieved an ACK at time {global_time} from {pkt.src}")
            self.window = None
        else: # if neither, just do wtv the incoming packet makes you do. No need to clear window or retransmit because we eventually will get the NACK or ACK
            pass


        match pkt.pktOp:
            # IPG Packet types
            case PacketOp.STF: # Respond with cache transfer, do a GRT request
                # If I get a STF, I need to write back to memory and send a GRT to the requestor
                cacheidx = self.findDataIdx(pkt.addr)
                if (cacheidx != None):
                    rdma_pkt = Packet(PacketOp.RDMA_WRITE, self.id, 0, pkt.addr, (0, 0), pkt.addr % 128, None, global_time, self.cache.cacheLines[cacheidx])
                    self.requestQueue.append(rdma_pkt)
                    grt_pkt = Packet(PacketOp.GRT, self.id, 0, pkt.addr, (0, 0), pkt.src, None, global_time, None)
                    self.GRTQueue.append(grt_pkt)
                else:
                    raise Exception("Data not found in cache")


            case PacketOp.GRT:
                # If I sent a LD REQ and got a GRT, I need to send an RDMA READ to sender
                if (self.transaction.pktOp == PacketOp.EVC):
                    rdma_pkt = Packet(PacketOp.RDMA_WRITE, self.id, 0, pkt.addr, (0, 0), pkt.src, None, global_time, self.findData(pkt.addr))
                    self.requestQueue.append(rdma_pkt)
                    self.transaction = None
                elif (self.transaction.pktOp == PacketOp.ST_REQ):
                    self.cache.cacheLines[self.cache.LRUIdx].addr = self.transaction.addr
                    self.cache.cacheLines[self.cache.LRUIdx].data = self.transaction.data
                    self.cache.cacheLines[self.cache.LRUIdx].state = State.M
                    self.transaction = None
                elif (self.transaction.pktOp == PacketOp.LD_REQ):
                    rdma_pkt = Packet(PacketOp.RDMA_READ, self.id, 0, pkt.addr, (0, 0), pkt.src, None, global_time, None)
                    self.requestQueue.append(rdma_pkt)
                    print("Sending RDMA READ")


            case PacketOp.INV:
                cacheidx = self.findDataIdx(pkt.addr)
                if (cacheidx != None):
                    self.cache.cacheLines[cacheidx].state = State.I
                else:
                    raise Exception("Data not found in cache")
        
            # RDMA packet types
            case PacketOp.RDMA_READ:
                # Send an RDMA WRITE to requestor
                rdma_pkt = Packet(PacketOp.RDMA_WRITE, self.id, 0, pkt.addr, (0, 0), pkt.src, None, global_time, self.findData(pkt.addr))
                self.requestQueue.append(rdma_pkt)

            case PacketOp.RDMA_WRITE:
                self.cache.cacheLines[self.cache.LRUIdx].addr = pkt.addr
                self.cache.cacheLines[self.cache.LRUIdx].data = pkt.data
                self.cache.cacheLines[self.cache.LRUIdx].state = State.S
                self.transaction = None

        return

    def processPacket(self, pkt, global_time):
        """
        First check if we need to retransmit a packet
        """
        # ACKID is a tuple, where if first idx is 0, we were acked, otherwise we need to retransmit
        # (1, 0) means ACK
        # (0, 1) means NACK
        # (0, 0) means ignore

        print(f"Compute Node {self.id} received a packet of type {pkt.pktOp} at time {global_time}")
        self.processMSI(pkt, global_time)
        print(f"Transaction active? {self.transaction != None}")


    def periodicAction(self, global_time):
        """
        On every cycle, what does a compute node need to do?
            - arbitrate between each one of its queues (EVC, GRT, RTR, INST) (if in a round robin, we need a variable keeping track of which queue to access)
            - place that item on the egress port
            - read from ingress port and perform required actions
        """

        self.processInstructionQueue(global_time)


        # Arbitrate between queues
        out_pkt = None
        # Read from one of our in-built queues if a transaction is completed

        try:
            if (self.prevQueue == "EVC"):
                self.prevQueue = "GRT"
                out_pkt = self.GRTQueue.pop(0)
            elif (self.prevQueue == "GRT"):
                self.prevQueue = "RTR"
                out_pkt = self.RTRQueue.pop(0)
            elif (self.prevQueue == "RTR"):
                self.prevQueue = "INST"
                out_pkt = self.requestQueue.pop(0)
            else:
                self.prevQueue = "EVC"
                out_pkt = self.EVCQueue.pop(0)
        except IndexError:
            out_pkt = None

        # Make a copy of the packet, place into window as well as Egress Queue
        if (out_pkt != None):
            out_pkt.src = self.id
            out_pkt.ackid = (0, 0)
            pkt_copy = copy.deepcopy(out_pkt)
            self.port.EgressQueue.put_nowait(out_pkt)

            # Place packet in window so we have a record of it
            self.window = pkt_copy
            # Mark this node as busy, so instructions in the program can't be processed. However, we will allow incoming data to be processed
            self.busy = 1


        # Read from Ingress queue and process packets
        try:
            in_pkt = self.port.IngressQueue.get_nowait()
        except Empty:
            in_pkt = None
        if (in_pkt != None):
            self.processPacket(in_pkt, global_time)

        return

        

        

    







    