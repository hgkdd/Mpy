from mpy.device.pm_rxatt import POWERMETER

SearchPaths = ['c:\\MpyConfig\\LargeRC\\']
ini = "c:\\MpyConfig\\LargeRC\\ini\\pm_rxatt.ini"

pm = POWERMETER(SearchPaths=SearchPaths)
pm.Init(ini)
pm.SetFreq(100e6)
err, p = pm.GetData()
print(p)
pm.Quit()

pm = POWERMETER(SearchPaths=SearchPaths)
pm.Init(ini)
pm.SetFreq(100e6)
err, p = pm.GetData()
print(p)
pm.Quit()
