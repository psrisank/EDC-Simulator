# This file contains the main simulation loop and the main function
from ComputeNode import *
from MemoryNode import *
from Switch import *
from Packet import *
from Port import *
from Link import *

import sys
from queue import Queue
import math

DEBUG = 0

if (len(sys.argv) != 4):
    print(sys.argv)
    print("Usage: python3 Simulator.py <input_trace_file> <memory_input_file> <trace_log_file>")
    sys.exit(1)

# TODO: Generate fifo queue as a Link

# Overall simulation parameters
queue_size = 128
input_file_name = sys.argv[1]
memory_input_file_name = sys.argv[2]
output_file_name = sys.argv[3]

# Compute node parameters
compute_nodes = []
num_compute_nodes = 128
cacheLineCnt = 10


# Memory node parameters
memory_nodes = []
num_memory_nodes = 128


# Switch parameters
switches = []
num_switches = 1

links = []


def main():
    global queue_size
    global_time = 0
    global_id = 0


    # Initialize the compute nodes
    for id in range(num_compute_nodes):
        compute_nodes.append(ComputeNode(id, cacheLineCnt))
        global_id += 1
    

    # Initialize the memory nodes. TODO: Add memory node parameters
    for id in range(num_memory_nodes):
        memory_nodes.append(MemoryNode(global_id))
        global_id += 1


    # Initialize the switches. TODO: Add switch parameters
    for id in range(num_switches):
        switches.append(Switch(global_id, num_compute_nodes, num_memory_nodes))
        global_id += 1


    print(f"Max global id: {global_id}")
    # Initialize the links
    for id in range(global_id - 1):
        links.append(Link())


    # TODO: Place data inside corresponding memory nodes
    with open(memory_input_file_name, "r") as memfile:
        total_addresses = len(memfile.readlines())
        print(f"Total addresses: {total_addresses}")
        print(f"Each memory node has {address_per_node} addresses") if DEBUG else None
        addr_cnt = 0
        memfile.seek(0)
        for line in memfile.readlines():
            address = int(line.split(",")[0], 16)
            value = int(line.split(",")[1].strip(), 16)
            # print(f"Placed address {hex(address)} into memory node ID {int(addr_cnt / address_per_node)}") if DEBUG else None
            memory_nodes[address % 128].addAddress(address, value)
            addr_cnt += 1


    # TODO: Create packet queue
    overallInstructionCount = 0
    final_time = 0
    with open(input_file_name, "r") as input_trace:
        lines = input_trace.readlines()
        for instruction in lines:
            inst = instruction.split(",")
            inst_time = int(inst[0])
            compute_node_id = int(inst[1])
            inst_addr = int(inst[2], 16)
            inst_op = PacketOp.LD_REQ if int(inst[3]) == 0 else PacketOp.ST_REQ
            inst_wrdata = int(inst[4], 16)
            inst_datalen = int(inst[6])
            dst = inst_addr % 128 + 128
            compute_nodes[compute_node_id].instrQueue.append(Packet(inst_op, compute_node_id, inst_datalen, inst_addr, 0, dst, None, inst_time, inst_wrdata))
            overallInstructionCount += 1
            final_time = inst_time



    # TODO: Entire simulator loop
    global_time = 0
    while (global_time < (final_time + 100)):
        # Iterate through every compute node and perform necessary actions
        for cnode_id, cnode in enumerate(compute_nodes):
            cnode.receive(links[cnode_id])
            cnode.periodicAction(global_time)
            cnode.send(links[cnode_id], global_time)
        
        for switch in switches:
            switch.receive(links)
            switch.periodicAction(global_time)
            switch.send(links, global_time)         

        # # place packets from queues into link

        for mnode_id, memnode in enumerate(memory_nodes):
            memnode.receive(links[mnode_id + 128])
            memnode.periodicAction(global_time)
            memnode.send(links[mnode_id + 128])
        
        # # Increase global time on every iteration            
        global_time += 1
    
    return

if __name__ == "__main__":
    main()