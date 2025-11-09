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
        self.freq = None
        self.meastime = None
        self.rbw = None
        self.att = None
        self.min_att = None
        self.detector = None
        self.preamplifier = None

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

        self.doubleSpinBox_rbw.valueChanged.connect(self.rbw_changed)
        self.radioButton_rbw_1.toggled.connect(self.rbw_changed)
        self.radioButton_rbw_k.toggled.connect(self.rbw_changed)
        self.radioButton_rbw_M.toggled.connect(self.rbw_changed)
        self.checkBox_rbw_auto.toggled.connect(self.rbw_changed)

        self.doubleSpinBox_meastime.valueChanged.connect(self.meastime_changed)
        self.radioButton_meastime_s.toggled.connect(self.meastime_changed)
        self.radioButton_meastime_ms.toggled.connect(self.meastime_changed)

        self.doubleSpinBox_att.valueChanged.connect(self.att_changed)
        self.checkBox_att_auto.toggled.connect(self.att_changed)

        self.update_from_ini()

    def freq_changed(self):
        val = self.doubleSpinBox_freq.value()
        for n, attr in self.freq_units.items():
            if getattr(self, attr).isChecked():
                self.freq = val * 10**n
                break
        err, self.freq = self.dev.SetFreq(self.freq)
        self.update_freq(self.freq)
        return self.freq

    def meastime_changed(self):
        val = self.doubleSpinBox_meastime.value()
        for n, attr in self.meastime_units.items():
            if getattr(self, attr).isChecked():
                self.meastime = val * 10**n
                break
        err, self.meastime = self.dev.SetMeasTime(self.meastime)
        self.update_meastime(self.meastime)
        return self.meastime

    def rbw_changed(self):
        if self.checkBox_rbw_auto.isChecked():
            pass  # TODO: Implement auto rbw
        else:
            val = self.doubleSpinBox_rbw.value()
            for n, attr in self.rbw_units.items():
                if getattr(self, attr).isChecked():
                    self.rbw = val * 10**n
                    break
            err, self.rbw = self.dev.SetResolutionBandwidth(self.rbw)
            self.update_rbw(self.rbw)
        return self.rbw

    def att_changed(self):
        if self.checkBox_att_auto.isChecked():
            pass  # TODO: Implement auto att
        else:
            self.att = self.doubleSpinBox_att.value()
            err, self.att = self.dev.SetAttenuation(self.att)
            self.update_att(self.att)
        return self.rbw

    def update_att(self, att):
        if att is None:   # auto
            self.checkBox_att_auto.setChecked(True)
            self.doubleSpinBox_att.setEnabled(False)
        else:
            self.checkBox_att_auto.setChecked(False)
            self.doubleSpinBox_att.setEnabled(True)
            self.doubleSpinBox_att.setValue(att)

    def update_freq(self, freq):
        val, n = map_to_1000(freq)
        self.doubleSpinBox_freq.setValue(val)
        getattr(self, self.freq_units[n]).setChecked(True)

    def update_meastime(self, meastime):
        val, n = map_to_1000(meastime)
        self.doubleSpinBox_meastime.setValue(val)
        getattr(self, self.meastime_units[n]).setChecked(True)

    def update_rbw(self, rbw):
        if rbw is None:
            self.checkBox_rbw_auto.setChecked(True)
            self.doubleSpinBox_rbw.setEnabled(False)
        else:
            self.checkBox_rbw_auto.setChecked(False)
            self.doubleSpinBox_rbw.setEnabled(True)
            val, n = map_to_1000(float(rbw))
            self.doubleSpinBox_rbw.setValue(val)
            getattr(self, self.rbw_units[n]).setChecked(True)

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
        self.update_freq(minfreq)

        meastime = ini_conf['channel_1']['meas_time']
        self.update_meastime(meastime)

        min_att = ini_conf['channel_1']['min_attenuation']
        self.doubleSpinBox_minatt.setValue(min_att)

        att = ini_conf['channel_1']['attenuation']
        if case_insensitive_string_compare(att, 'auto'):
            self.update_att(None)
        else:
            self.update_att(float(att))

        rbw = ini_conf['channel_1']['rbw']
        if case_insensitive_string_compare(rbw, 'auto'):
            self.update_rbw(None)
        else:
            self.update_rbw(float(rbw))
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