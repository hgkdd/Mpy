from mpylab.device.amp_ifi_smx25 import AMPLIFIER

ini="ini/amp_ifi_smx25.ini"

amp=AMPLIFIER()
amp.Init(ini)
amp.SetFreq(100e6)
err, s21 = amp.GetData('S21')
amp.Quit()
