import io

from PySide6.QtWidgets import QDialog
from numpy import sign
from bidict import bidict
from importlib import import_module
from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFileDialog, QMessageBox

from receiver_ui import Ui_MainWindow

from mpylab.device.receiver import RECEIVER
from mpylab.tools.util import format_block, case_insensitive_string_compare
from mpylab.tools.configuration import Configuration
from mpylab.device.ui_ini_draft import load_ini_with_draft

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
        load_ini_with_draft(
            self,
            self.plainTextEdit_ini,
            io.StringIO(self.plainTextEdit_ini.toPlainText()),
            self.plainTextEdit_ini.toPlainText(),
            "receiver_ui",
        )
        self.conftmpl = RECEIVER().conftmpl
        self.after_init = False
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

        lev_timer = QTimer(self)
        lev_timer.timeout.connect(self.update_level)
        lev_timer.start(1000)


        self.pushButton_init.clicked.connect(self.init_clicked)

        self.pushButton_trigger.clicked.connect(self.trigger_clicked)

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

        self.doubleSpinBox_minatt.valueChanged.connect(self.minatt_changed)

        self.comboBox_preamp.currentIndexChanged.connect(self.preamplifier_changed)

        self.comboBox_detec.currentIndexChanged.connect(self.detect_changed)

        # menue
        self.actionInfo.triggered.connect(self.info_clicked)
        self.actionOpen_Ini_File.triggered.connect(self.open_Ini_File_clicked)


        self.update_from_ini()

    def update_level(self):
        obj = None
        txt = 'None'
        if self.after_init:
            self.error, obj = self.dev.GetDataNB(retrigger=True)
            if obj is None:
                txt = 'None'
            else:
                txt = str(round(self.dev._get_db_from_obj(obj), 2))
                self.plainTextEdit_output.appendPlainText(str(obj))
        self.label_level.setText(txt)

    def info_clicked(self):
        dialog = QMessageBox()
        dialog.setWindowTitle("Info")
        dialog.setText("This program is part of MpyLab.")
        dialog.exec()

    def open_Ini_File_clicked(self):
        dialog = QFileDialog()
        inifilemame, _ = dialog.getOpenFileName(self, "Open Ini File",".", "Ini-Files (*.ini)")
        if inifilemame:
            initxt = open(inifilemame, 'r').read()
            self.plainTextEdit_ini.setPlainText(initxt)


    def update_preamplifier(self):
        self.preamplifier = self.comboBox_preamp.currentText()
        if self.after_init:
            err, self.preamplifier = self.dev.SetPreamplifier(self.preamplifier)
        return self.preamplifier

    def update_detector(self):
        self.detector = self.comboBox_detec.currentText()
        if self.after_init:
            err, self.detector = self.dev.SetDetector(self.detector)
        return self.detector

    def freq_changed(self):
        val = self.doubleSpinBox_freq.value()
        for n, attr in self.freq_units.items():
            if getattr(self, attr).isChecked():
                self.freq = val * 10**n
                break
        if self.after_init:
            err, self.freq = self.dev.SetFreq(self.freq)
        self.update_freq(self.freq)
        self.rbw_changed()
        return self.freq


    def meastime_changed(self):
        val = self.doubleSpinBox_meastime.value()
        for n, attr in self.meastime_units.items():
            if getattr(self, attr).isChecked():
                self.meastime = val * 10**n
                break
        if self.after_init:
            err, self.meastime = self.dev.SetMeasTime(self.meastime)
        self.update_meastime(self.meastime)
        return self.meastime

    def preamplifier_changed(self):
        txt = self.comboBox_preamp.currentText()
        if self.after_init:
            err, self.preamplifier = self.dev.SetPreamplifier(txt)
        return self.preamplifier

    def detect_changed(self):
        txt = self.comboBox_detec.currentText()
        if self.after_init:
            err, self.detector = self.dev.SetDetector(txt)
        return self.detector

    def rbw_changed(self):
        if self.checkBox_rbw_auto.isChecked():
            if self.after_init:
                err, self.rbw = self.dev.SetResolutionBandwidth(None)
                val, n = map_to_1000(float(self.rbw))
                self.doubleSpinBox_rbw.setValue(val)
        else:
            val = self.doubleSpinBox_rbw.value()
            for n, attr in self.rbw_units.items():
                if getattr(self, attr).isChecked():
                    self.rbw = val * 10**n
                    break
            if self.after_init:
                err, self.rbw = self.dev.SetResolutionBandwidth(self.rbw)
                self.update_rbw(self.rbw)
        return self.rbw

    def att_changed(self):
        if self.checkBox_att_auto.isChecked():
            if self.after_init:
                err, self.att = self.dev.SetAttenuation(None)
                self.doubleSpinBox_att.setValue(float(self.att))
        else:
            self.att = self.doubleSpinBox_att.value()
            if self.after_init:
                err, self.att = self.dev.SetAttenuation(self.att)
            self.update_att(self.att)
        return self.att

    def trigger_clicked(self):
        self.error = 0
        if self.after_init:
            self.dev.Trigger()

    def minatt_changed(self):
        self.min_att = self.doubleSpinBox_minatt.value()
        if self.after_init:
            err, self.min_att = self.dev.SetMinAttenuation(self.min_att)
            self.update_minatt(self.min_att)
        self.update_att(self.att)
        return self.min_att

    def update_minatt(self, min_att):
        self.doubleSpinBox_minatt.setValue(min_att)
        err, self.att = self.dev.GetAttenuation()
        self.doubleSpinBox_att.setValue(self.att)

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
        self.update_detector()

        preamplifier = ini_conf['channel_1']['preamplifier']
        idx = self.comboBox_preamp.findText(preamplifier, Qt.MatchFlag.MatchContains)
        self.comboBox_preamp.setCurrentIndex(idx)
        self.update_preamplifier()


        self.ini.seek(0)   # seek to top of ini 'file'


    def init_clicked(self):
        if self.after_init:
            self.dev.Quit()
            self.after_init = False

        self.update_from_ini()
        self.dev.Init(ini=self.ini, channel=1)
        self.after_init = True
        self.label_levelunit.setText(self.dev._internal_unit)
        self.dev.Trigger()
        self.freq_changed()
        self.preamplifier_changed()
        self.detect_changed()
        self.rbw_changed()
        self.meastime_changed()
        self.att_changed()

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
