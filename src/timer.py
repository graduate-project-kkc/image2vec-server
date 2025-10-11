import time

class SimpleTimer:
    def __init__(self):
        self.t = 0
    
    def start(self):
        self.t = time.time()
    
    def stop(self):
        return time.time() - self.t