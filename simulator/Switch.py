from Port import *
from Packet import *
from queue import Empty
from queue import Full

# class InvalidationTable:
#     def __init__(self):
    
#     def update(self, src, tag, memaddr):
#         return

class InvalidationTable:
    def __init__ (self, src, tag, address, bitmap):
        self.tag = tag
        self.src = src
        self.addr = address
        self.bitmap = []


class Switch:
    def __init__(self, id, num_compute_nodes=128, num_memory_nodes=128):
        self.ports = []
        self.id = id
        for port_cnt_iterator in range(num_compute_nodes + num_memory_nodes):
            self.ports.append(Port())

    
    def receive(self, links):
        for linkID, link in enumerate(links):
            # link ID < 128 is a compute node
            pkt = None
            if (linkID < 128): # Receive from compute node, therefore downstream
                pkt = link.getPkt("downstream")
            else:  # Receive from memory node, therefore upstream
                pkt = link.getPkt("upstream")
    
            if (self.ports[linkID].IngressQueue.full() == True):
                print("SWITCH: Packet dropped when placing in ingress queue!")
                self.ports[linkID].needsNACK = True
                self.ports[linkID].needsACK = False
                continue

            if (pkt != None and self.ports[linkID].IngressQueue.full() == False):
                self.ports[linkID].IngressQueue.put_nowait(pkt)
                # self.ports[linkID].needsACK = True
                self.ports[linkID].needsNACK = False
            



    def send(self, links, global_time):
        for linkID, link in enumerate(links):
            pkt = None
            try:
                # If we are sending out a message
                if (self.ports[linkID].EgressQueue.queue[0].timeToLeave <= global_time):
                    pkt = self.ports[linkID].EgressQueue.get_nowait()
                    # if we need to send an ACK or NACK
                    if (self.ports[linkID].needsNACK == True):
                        # print(f"SWITCH: Sending NACK to port {linkID}")
                        pkt.ackid = (0, 1)
                        self.ports[linkID].needsNACK = False
                    elif (self.ports[linkID].needsACK == True):
                        pkt.ackid = (1, 0)
                        self.ports[linkID].needsACK = False

                # If no message to be sent, but needs to NACK
                elif (self.ports[linkID].needsNACK == True):
                    # print(f"SWITCH: Sending NACK to port {linkID}")
                    pkt = Packet(PacketOp.NOP, self.id, 0, 0, (0, 1), 0, None, global_time, 0)
                    self.ports[linkID].needsNACK = False
            
                # If no message to be sent, but needs to ACK
                elif (self.ports[linkID].needsACK == True):
                    pkt = Packet(PacketOp.NOP, self.id, 0, 0, (1, 0), 0, None, global_time, 0)
                    self.ports[linkID].needsACK = False
                
                # If neither need to be done, no need to send a NOP packet
                else:
                    continue

            except (Empty, IndexError):
                # If no message to be sent, but needs to NACK
                if (self.ports[linkID].needsNACK == True):
                    # print(f"SWITCH: Sending NACK to port {linkID}")
                    pkt = Packet(PacketOp.NOP, self.id, 0, 0, (0, 1), 0, None, global_time, 0)
                    self.ports[linkID].needsNACK = False
            
                # If no message to be sent, but needs to ACK
                elif (self.ports[linkID].needsACK == True):
                    pkt = Packet(PacketOp.NOP, self.id, 0, 0, (1, 0), 0, None, global_time, 0)
                    self.ports[linkID].needsACK = False

                else:
                    continue

            if (pkt != None):
                if (linkID < 128):
                    link.pushPkt(pkt, "upstream")
                else:
                    # print(f"SWITCH @ {global_time}: Pushing to downstream!")
                    link.pushPkt(pkt, "downstream")


    def periodicAction(self, global_time):
        # do forwarding actions

        # first process the ingress queues
        for portID, port in enumerate(self.ports):
            pkt = None
            # Pop a value from ingress queue
            try:
                pkt = port.IngressQueue.get_nowait()
                if (pkt.pktOp != PacketOp.INV):
                    try:
                        pkt.timeToLeave = global_time + 2
                        self.ports[pkt.dst].fwd_queue.put_nowait(pkt)
                        # print(f"SWITCH: Packet placed in forward queue at time {global_time}")
                    except Full:
                        # Set the ingress queue port as needing a NACK, and reset the needsACK flag
                        # print("SWITCH: Packet dropped when placing in forward queue!")
                        self.ports[pkt.src].needsNACK = True
                        self.ports[pkt.src].needsACK = False
                        continue
                else:
                    if (pkt.ackid == (0, 0)):
                        # first invalidation
                        print("Received first invalidation")
                        self.ports[portID].invalidation_buffer.append(InvalidationTable(portID, "incomplete", pkt.addr, None))
                    elif (pkt.ackid == (0, 1)):
                        # second invalidation
                        print("Received second invalidation")
                        self.ports[portID].invalidation_buffer[len(self.ports[portID].invalidation_buffer) - 1].bitmap = pkt.invalidation_bitmap
                    elif (pkt.ackid == (1, 0)):
                        print("Received third invalidation")
                        self.ports[portID].invalidation_buffer[len(self.ports[portID].invalidation_buffer) - 1].bitmap += pkt.invalidation_bitmap
                        self.ports[portID].invalidation_buffer[len(self.ports[portID].invalidation_buffer) - 1].tag = "complete"
                        print("Completed invalidation table")
                    else:
                        raise Exception("Unkown invalidation packet")

            except Empty:
                continue

        # Send out the packets that are allowed to be transmitted
        for id, port in enumerate(self.ports):
            delete_idx = None

            for idx, invalidation_table in enumerate(port.invalidation_buffer):
                if (invalidation_table.tag == "complete"):
                    print("Found a complete table")
                    for dst, invalidate in enumerate(invalidation_table.bitmap):
                        if (invalidate == 1):
                            print(f"Invalidating compute node {dst}")
                            inv_pkt = Packet(PacketOp.INV, self.id, 0, invalidation_table.addr, (0, 0), dst, None, global_time, None)
                            self.ports[dst].EgressQueue.put_nowait(inv_pkt)
                    delete_idx = idx
                    break
            if (delete_idx != None):
                port.invalidation_buffer.pop(delete_idx)


            if (port.fwd_queue.empty() or port.fwd_queue.queue[0] == None or port.fwd_queue.queue[0].timeToLeave > global_time):
                continue
        


            # Grab packet from forward queue and place in egress queue
            pkt = port.fwd_queue.get_nowait()
            try:
                port.EgressQueue.put_nowait(pkt)
                # If we successfully placed in Egress queue, set the needsACK flag
                self.ports[pkt.src].needsACK = True
                print(f"Packet placed in egress queue {id} at time {global_time}")
            except Full:
                print("Packet dropped when placing in egress queue!")
                self.ports[pkt.src].needsNACK = True
                self.ports[pkt.src].needsACK = False
                continue






        
        return








        
