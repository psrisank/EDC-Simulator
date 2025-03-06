from Port import *
from Packet import *
from queue import Empty

class Switch:
    def __init__(self, id, num_compute_nodes=128, num_memory_nodes=128):
        self.top_ports = []
        self.bot_ports = []
        
        for port_cnt_iterator in range(num_compute_nodes):
            self.top_ports.append(Port())
        for port_cnt_iterator in range(num_memory_nodes):
            self.bot_ports.append(Port())

    def processRX(self, global_time, num_memory_nodes):
        # Process top RX from compute
        for top_port in self.top_ports:
            in_pkt = Packet()
            try:
                in_pkt = top_port.RX.get_nowait()
            except Empty:
                continue

            mem_node = int(in_pkt.addr / num_memory_nodes)
            in_pkt.dst = mem_node
            self.forward_buffer.append(in_pkt)

        # Process bottom RX aimed at compute
        for bot_port in self.bot_ports:
            in_pkt = Packet()
            try:
                in_pkt = bot_port.RX.get_nowait()
            except Empty:
                continue

            compute_node = in_pkt.dst
            self.forward_buffer.append(in_pkt)
            self.top_ports[compute_node].TX.put_nowait(in_pkt)

    def processBuffers(self):
        # Process the forward buffer
        pkt = self.forward_buffer.pop(0)
        
        if (pkt.dst < 128):
            # place in compute TX
            self.top_ports[pkt.dst].TX.put_nowait(pkt)
        else:
            # place in  mem TX
            self.bot_ports[pkt.dst - 128].TX.put_nowait(pkt)

        return