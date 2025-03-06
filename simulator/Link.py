class Link:
    def __init__(self):
        self.downStream = []
        self.upStream = []
        return
    
    def pushPkt(self, packet, stream):
        if (stream == "downstream"):
            self.downStream.push(packet)
        else:
            self.upStream.push(packet)

    def getPkt(self, stream):
        if (stream == "downstream"):
            self.downStream.pop(0)
        else:
            self.upStream.pop(0)