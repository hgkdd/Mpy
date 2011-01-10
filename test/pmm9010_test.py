import time
import serial

class PMM(object):
    def __init__(self):
        self.dev=None
    
    def _write(self, cmd):
        self.dev.flushInput()
        self.dev.flushOutput()
        self.dev.write(cmd)
        time.sleep(0.1)

    def _read(self, num=None):
        if num == None:
            bytes=[]
            while True:
                b=self.dev.read(1)
                if b == '\r':
                    self.dev.flushInput()
                    break
                bytes.append(b)
            ans=''.join(bytes)
        else:
            ans=self.dev.read(num)
        return ans

    def _query(self, cmd, num=None):
        self._write(cmd)
        ans=self._read(num)
        return ans

    def Init(self):
        self.dev=serial.Serial(port='COM%d'%5, 
                               timeout=1,
                               baudrate=115200)

        ans=self._query('#?IDN*')
        print ans, repr(ans)

if __name__ == '__main__':
    rec=PMM()
    rec.Init()