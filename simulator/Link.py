class Link:
    def __init__(self):
        self.downStream = []
        self.upStream = []
        return
    
    def pushPkt(self, packet, stream):
        if (stream == "downstream"):
            self.downStream.append(packet)
        else:
            self.upStream.append(packet)

    def getPkt(self, stream):
        if (stream == "downstream"):
            if (len(self.downStream) > 0):
                return self.downStream.pop(0)
            else:
                return None
        else:
            if (len(self.upStream) > 0):
                return self.upStream.pop(0)
            else:
                return None