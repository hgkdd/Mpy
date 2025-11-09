import io

from numpy import sign
from bidict import bidict
from importlib import import_module
from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt

from receiver_ui import Ui_MainWindow

from mpylab.device.receiver import RECEIVER
from mpylab.tools.util import format_block, case_insensitive_string_compare
from mpylab.tools.configuration import Configuration

def map_to_1000(value):
    n = 0
    sgn = sign(value)
    value = abs(value)
    while value > 1000:
        n += 3
        value /= 1000
    while value < 1.00:
        n -= 3
        value *= 1000
    value *= sgn
    return value, n


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.conftmpl = RECEIVER().conftmpl
        self.conf = None
        self.ini = None
        self.dev = None
        self.freq_units = bidict({0: 'radioButton_freq_1',
                                  3: 'radioButton_freq_k',
                                  6: 'radioButton_freq_M',
                                  9: 'radioButton_freq_G'})
        self.rbw_units = bidict({0: 'radioButton_rbw_1',
                                  3: 'radioButton_rbw_k',
                                  6: 'radioButton_rbw_M'})
        self.meastime_units = bidict({0: 'radioButton_meastime_s',
                                  -3: 'radioButton_meastime_ms'})

        self.pushButton_init.clicked.connect(self.init_clicked)
        self.checkBox_att_auto.stateChanged.connect(self.auto_att_changed)
        self.checkBox_rbw_auto.stateChanged.connect(self.auto_rbw_changed)

        self.doubleSpinBox_freq.valueChanged.connect(self.freq_changed)
        self.radioButton_freq_1.toggled.connect(self.freq_changed)
        self.radioButton_freq_k.toggled.connect(self.freq_changed)
        self.radioButton_freq_M.toggled.connect(self.freq_changed)
        self.radioButton_freq_G.toggled.connect(self.freq_changed)

        self.update_from_ini()

    def freq_changed(self):
        val = self.doubleSpinBox_freq.value()
        for n, attr in self.freq_units.items():
            if getattr(self, attr).isChecked():
                self.freq = val * 10**n
                break
        return self.freq


    def update_from_ini(self):
        if self.dev:
            self.dev.Quit()
            self.dev = None

        initxt = self.plainTextEdit_ini.toPlainText()
        ini = format_block(initxt)
        self.ini = io.StringIO(ini)
        ini_conf = Configuration(self.ini, self.conftmpl).conf

        driver = ini_conf['description']['driver']
        mod = import_module(f".{driver.rstrip('.py')}", "mpylab.device")
        self.dev = mod.RECEIVER()

        minfreq = ini_conf['init_value']['fstart']
        maxfreq = ini_conf['init_value']['fstop']
        val, n = map_to_1000(minfreq)
        self.doubleSpinBox_freq.setValue(val)
        getattr(self, self.freq_units[n]).setChecked(True)

        meastime = ini_conf['channel_1']['meas_time']
        val, n = map_to_1000(meastime)
        self.doubleSpinBox_meastime.setValue(val)
        getattr(self, self.meastime_units[n]).setChecked(True)

        min_att = ini_conf['channel_1']['min_attenuation']
        self.doubleSpinBox_minatt.setValue(min_att)

        att = ini_conf['channel_1']['attenuation']
        if case_insensitive_string_compare(att, 'auto'):
            self.checkBox_att_auto.setChecked(True)
        else:
            self.checkBox_att_auto.setChecked(False)
            self.doubleSpinBox_att.setValue(float(att))

        rbw = ini_conf['channel_1']['rbw']
        if case_insensitive_string_compare(rbw, 'auto'):
            self.checkBox_rbw_auto.setChecked(True)
        else:
            self.checkBox_rbw_auto.setChecked(False)
            val, n = map_to_1000(float(rbw))
            self.doubleSpinBox_rbw.setValue(val)
            getattr(self, self.rbw_units[n]).setChecked(True)

        detector = ini_conf['channel_1']['detector']
        idx = self.comboBox_detec.findText(detector, Qt.MatchFlag.MatchContains)
        self.comboBox_detec.setCurrentIndex(idx)

        preamplifier = ini_conf['channel_1']['preamplifier']
        idx = self.comboBox_preamp.findText(preamplifier, Qt.MatchFlag.MatchContains)
        self.comboBox_preamp.setCurrentIndex(idx)
        self.ini.seek(0)   # seek to top of ini 'file'
        self.dev.Init(ini=self.ini, channel=1)
        self.label_levelunit.setText(self.dev._internal_unit)


    def init_clicked(self):
        self.update_from_ini()

    def auto_att_changed(self):
        state = self.checkBox_att_auto.isChecked()
        self.doubleSpinBox_att.setEnabled(not state)

    def auto_rbw_changed(self):
        state = self.checkBox_rbw_auto.isChecked()
        self.doubleSpinBox_rbw.setEnabled(not state)
        self.radioButton_rbw_1.setEnabled(not state)
        self.radioButton_rbw_k.setEnabled(not state)
        self.radioButton_rbw_M.setEnabled(not state)

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()
    window.show()
    app.exec()