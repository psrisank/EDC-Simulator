from queue import Queue

class Port:
    def __init__(self):
        self.TX = Queue()
        self.RX = Queue()