from queue import Queue

class Port:
    def __init__(self):
        self.EgressQueue = Queue()
        self.IngressQueue = Queue()

        self.invalidation_buffer = []
        self.fwd_queue = Queue()