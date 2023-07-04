import time
import pyvisa


class scr3502(object):
    def __init__(self, port="COM1",
                 baudrate='9600',
                 term_char="\n",
                 timeout=1,
                 xonxoff=0,
                 debug=False):
        self.debug = debug
        self.rm = pyvisa.ResourceManager('@py')
        self.scr = self.rm.open_resource(port)
        # self.scr = pyvisa.instrument(port, term_chars = term_char)
        self.scr.read_termination = term_char
        self.scr.write_termination = term_char
        self.scr.write("SY:P baudrate")
        self.scr.write("*RST")
        self.scr.write("*CLS")

    def setFreq(self, freq):
        #        testfreq = "%dMHZ"%(freq/1000)
        #        self.scr.write("FR testfreq")
        #        self.buf="FR %e"%(freq)
        #        self.scr.write("self.buf")
        self.scr.write("FR %e" % (freq))

    def getFreq(self):
        recfrq = self.scr.query("FR?")
        return recfrq

    def getLevel(self):
        level = self.scr.ask("LE?")
        return level

    def quit(self):
        self.scr.write("SY:GTL")


if __name__ == '__main__':
    instr = scr3502()
    for i in range(50):
        f = 20e6 + i * 1e6
        instr.setFreq(f)
        time.sleep(0.2)
        recfrequency = instr.getFreq()
        data = instr.getLevel()
        print(f, recfrequency, data)
        instr.quit()
