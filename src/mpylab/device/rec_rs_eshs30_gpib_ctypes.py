from gpib_ctypes import gpib

try:
    dev = gpib.dev(0, 17)

    gpib.write(dev, b'*IDN?')
    result = gpib.read(dev, 1000)
    print(result)
except gpib.GpibError as err:
    # do something with err.code
    print(err)

fstart = 150e3
fstop = 30e6
fstep = 1e3


def get_level(interface, device):
    gpib.serial_poll(device)  # reset SRQ-Bit
    gpib.write(device, "LEVEL?")  # start measurement
    gpib.wait(interface, 0x1000)  # wait for SRQ-Bit
    x = gpib.read(device, 1024)
    gpib.wait(interface, 0x100)  # wait forI/O-Operation complete
    return float(x)

f = fstart
while f <= fstop:
    gpib.write(dev, f"FREQUENCY {f} HZ")
    lev = get_level(0, 17)
    print(f"{f}: {lev}")
    f += fstep
