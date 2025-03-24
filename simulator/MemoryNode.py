from ComputeNode import State
from queue import Queue
from queue import Empty
from queue import Full
from Port import *
from Packet import *
import copy


class MemoryNode:
    class MemLine:
        def __init__(self, addr=0x0, data=0x0):
            self.addr = addr
            self.data = data
            self.nodeStates = [State.I] * 128
    
    def __init__(self, id=0):
        self.id = id
        self.memlines = []
        self.port = Port()
        self.window = []
        self.windowsize = 1
        self.unfinished_transaction = 0
        self.sendQueue = []
        self.resend = 0
        self.retransmit = None

    def addAddress(self, addr, data):
        self.memlines.append(self.MemLine(addr, data))
    
    def receive(self, link):
        # Move from link into port
        pkt = link.getPkt("downstream")
        if (pkt == None):
            return
    
        self.port.IngressQueue.put_nowait(pkt)
        return
    
    def send(self, link):
        # Move from port into link
        try:
            pkt = self.port.EgressQueue.get_nowait()
            link.pushPkt(pkt, "upstream")
            # print("MEMORY NODE: Sent a packet")
        except Empty:
            return
        
        return
    

    def findData(self, addr):
        for line in self.memlines:
            if (line.addr == addr):
                return line.data
        return None
    
    def findDataIndex(self, addr):
        for i, line in enumerate(self.memlines):
            if (line.addr == addr):
                return i
        raise Exception("MemoryNode: Address not found")
    

    def processPacket(self, pkt, global_time):

        # ACK

        # Resend 0 means we can pop, resend 1 means we should retransmit, resend 2 means we should not send any packets since we have an unacknowledged packet of some sort
        if (pkt.ackid == (1, 0)):
            self.resend = 0
            self.retransmit = None
        elif (pkt.ackid == (0, 1)):
            self.resend = 1
        else:
            self.resend = 2


        


        match pkt.pktOp:
            case PacketOp.LD_REQ:
                data = self.findData(pkt.addr)
                if (data == None):
                    raise Exception("MemoryNode: Address not found")
                
                # If received a load request, check to see if anyone is in modfied state. If so, send STF to them. They will need to send a RDMA_WRITE to the memory node, and a GRT to the requestor
                data_idx = self.findDataIndex(pkt.addr)
                modified = False
                for i, nodeState in enumerate(self.memlines[data_idx].nodeStates):
                    if (nodeState == State.M):
                        stf_pkt = Packet(PacketOp.STF, self.id, 0, pkt.addr, (0, 0), i, None, global_time, None)
                        self.sendQueue.append(stf_pkt)
                        modified = True
                        break

                if (modified == False):
                    grt_pkt = Packet(PacketOp.GRT, self.id, 0, pkt.addr, (0, 0), pkt.src, None, global_time, None)
                    self.sendQueue.append(grt_pkt)


            case PacketOp.ST_REQ:
                # Send invalidation to the switch, it will take care of the rest. Then send GRT to the requestor
                data_idx = self.findDataIndex(pkt.addr)
                inv_list = []
                needs_invalidation = False
                for i, nodeState in enumerate(self.memlines[data_idx].nodeStates):
                    if (i == pkt.src):
                        continue
            
                    if (nodeState != State.I):
                        inv_list.append(1)
                        needs_invalidation = True
                    else:
                        inv_list.append(0)
                    
                inv_pkt1 = Packet(PacketOp.INV, self.id, 0, pkt.addr, (0, 0), 0, None, global_time, None)
                inv_pkt2 = Packet(PacketOp.INV, self.id, 0, None, (0, 1), None, inv_list[0:64], global_time, None)
                inv_pkt3 = Packet(PacketOp.INV, self.id, 0, None, (1, 0), None, inv_list[64:], global_time, None)

                if (needs_invalidation):
                    self.sendQueue.append(inv_pkt1)
                    self.sendQueue.append(inv_pkt2)
                    self.sendQueue.append(inv_pkt3)


                # Send out the GRT so it can go ahead and do the write while everyone else is 
                grt_pkt = Packet(PacketOp.GRT, self.id, 0, pkt.addr, (0, 0), pkt.src, None, global_time, None)
                self.sendQueue.append(grt_pkt)
                for i in range(0, 128):
                    self.memlines[data_idx].nodeStates[i] = State.I
                    if (i == pkt.src):
                        self.memlines[data_idx].nodeStates[i] = State.M



            case PacketOp.EVC:
                # Send a GRT packet to the source, telling it that it is okay to RDMA WRITE
                grt_pkt = Packet(PacketOp.GRT, self.id, 0, pkt.addr, (0, 0), pkt.src, None, global_time, None)
                self.sendQueue.append(grt_pkt)

            case PacketOp.RDMA_READ:
                data = self.findData(pkt.addr)
                rdma_pkt = Packet(PacketOp.RDMA_WRITE, self.id, 0, pkt.addr, (0, 0), pkt.src, None, global_time, data)
                self.sendQueue.append(rdma_pkt)
            
            case PacketOp.RDMA_WRITE:
                # I need to set the source to shared, and update the value
                data_idx = self.findDataIndex(pkt.addr)
                self.memlines[data_idx].nodeStates[pkt.src] = State.S # only time we can go to shared for a node is when that data comes back ot us
                self.memlines[data_idx].data = pkt.data





    
    def periodicAction(self, global_time):
        out_pkt = None
        
            
        try:
            if (self.resend != 1):
                out_pkt = self.sendQueue.pop(0)
            else:
                out_pkt = self.retransmit
        except IndexError:
            out_pkt = None


            
        if (out_pkt != None):
            out_pkt.src = self.id
            # out_pkt.ackid = (0, 0)
            out_pkt.timeToLeave = global_time
            self.retransmit = copy.deepcopy(out_pkt)
            self.port.EgressQueue.put_nowait(out_pkt)
            print(f"Memory node {self.id} sent a packet at time {global_time}")


        try:
            in_pkt = self.port.IngressQueue.get_nowait()
        except Empty:
            in_pkt = None


        if (in_pkt != None):
            print("Received packet")
            self.processPacket(in_pkt, global_time) # sets the resend bool to yes or no

        return
