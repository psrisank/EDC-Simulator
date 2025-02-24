from ComputeNode import State

class MemoryNode:
    class MemLine:
        def __init__(self, addr=0x0, data=0x0):
            self.addr = addr
            self.data = data
            self.nodeStates = []
    
    def __init__(self, id=0):
        self.id = 0
        self.memlines = []

    def addAddress(self, addr, data):
        self.memlines.append(self.MemLine(addr, data))
    
    def processPort(self, global_time):
        return