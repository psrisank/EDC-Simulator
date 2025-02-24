from Port import *
from Packet import *
from queue import Empty

class Switch:
    def __init__(self, id, num_compute_nodes=128, num_memory_nodes=128):
        self.top_ports = []
        self.bot_ports = []
        self.invalidation_buffer = []
        self.forward_buffer = []
        for port_cnt_iterator in range(num_compute_nodes):
            self.top_ports.append(Port())
        for port_cnt_iterator in range(num_memory_nodes):
            self.bot_ports.append(Port())

    def processPorts(self, global_time, num_memory_nodes):
        index = 0
        # Process top RX from compute
        for top_port in self.top_ports:
            in_pkt = Packet()
            try:
                in_pkt = top_port.RX.get_nowait()
            except Empty:
                continue

            mem_node = int(in_pkt.addr / num_memory_nodes)
            self.bot_ports[mem_node].TX.put_nowait(in_pkt)


        # Process bottom RX aimed at compute
        for bot_port in self.bot_ports:
            in_pkt = Packet()
            try:
                in_pkt = bot_port.RX.get_nowait()
            except Empty:
                continue

            compute_node = in_pkt.dst
            self.top_ports[compute_node].TX.put_nowait(in_pkt)
        

    def processMemoryPorts(self, global_time):
        return
