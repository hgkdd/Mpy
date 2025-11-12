# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'receiver_ui.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
    QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QMainWindow, QMenu, QMenuBar,
    QPlainTextEdit, QPushButton, QRadioButton, QScrollArea,
    QSizePolicy, QSpacerItem, QStatusBar, QVBoxLayout,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(954, 654)
        self.actionInfo = QAction(MainWindow)
        self.actionInfo.setObjectName(u"actionInfo")
        self.actionQuit = QAction(MainWindow)
        self.actionQuit.setObjectName(u"actionQuit")
        self.actionOpen_Ini_File = QAction(MainWindow)
        self.actionOpen_Ini_File.setObjectName(u"actionOpen_Ini_File")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_2 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.frame_3 = QFrame(self.centralwidget)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_6 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer)

        self.pushButton_trigger = QPushButton(self.frame_3)
        self.pushButton_trigger.setObjectName(u"pushButton_trigger")

        self.horizontalLayout_6.addWidget(self.pushButton_trigger)

        self.label_8 = QLabel(self.frame_3)
        self.label_8.setObjectName(u"label_8")
        font = QFont()
        font.setPointSize(24)
        self.label_8.setFont(font)

        self.horizontalLayout_6.addWidget(self.label_8)

        self.label_level = QLabel(self.frame_3)
        self.label_level.setObjectName(u"label_level")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_level.sizePolicy().hasHeightForWidth())
        self.label_level.setSizePolicy(sizePolicy)
        font1 = QFont()
        font1.setPointSize(24)
        font1.setBold(True)
        self.label_level.setFont(font1)
        self.label_level.setTextFormat(Qt.TextFormat.PlainText)
        self.label_level.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_6.addWidget(self.label_level)

        self.label_levelunit = QLabel(self.frame_3)
        self.label_levelunit.setObjectName(u"label_levelunit")
        self.label_levelunit.setFont(font)

        self.horizontalLayout_6.addWidget(self.label_levelunit)


        self.verticalLayout_2.addWidget(self.frame_3)

        self.frame_2 = QFrame(self.centralwidget)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_2)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.groupBox = QGroupBox(self.frame_2)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout = QVBoxLayout(self.groupBox)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.scrollArea = QScrollArea(self.groupBox)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 426, 258))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.plainTextEdit_ini = QPlainTextEdit(self.scrollAreaWidgetContents)
        self.plainTextEdit_ini.setObjectName(u"plainTextEdit_ini")

        self.gridLayout_2.addWidget(self.plainTextEdit_ini, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout.addWidget(self.scrollArea)

        self.widget_4 = QWidget(self.groupBox)
        self.widget_4.setObjectName(u"widget_4")
        self.horizontalLayout = QHBoxLayout(self.widget_4)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.pushButton_load_ini = QPushButton(self.widget_4)
        self.pushButton_load_ini.setObjectName(u"pushButton_load_ini")

        self.horizontalLayout.addWidget(self.pushButton_load_ini)

        self.pushButton_init = QPushButton(self.widget_4)
        self.pushButton_init.setObjectName(u"pushButton_init")

        self.horizontalLayout.addWidget(self.pushButton_init)


        self.verticalLayout.addWidget(self.widget_4)


        self.horizontalLayout_2.addWidget(self.groupBox)

        self.groupBox_2 = QGroupBox(self.frame_2)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_4 = QGridLayout(self.groupBox_2)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.label_3 = QLabel(self.groupBox_2)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout_4.addWidget(self.label_3, 4, 0, 1, 1)

        self.doubleSpinBox_freq = QDoubleSpinBox(self.groupBox_2)
        self.doubleSpinBox_freq.setObjectName(u"doubleSpinBox_freq")
        self.doubleSpinBox_freq.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.doubleSpinBox_freq.setDecimals(0)
        self.doubleSpinBox_freq.setMinimum(1.000000000000000)
        self.doubleSpinBox_freq.setMaximum(1000.000000000000000)

        self.gridLayout_4.addWidget(self.doubleSpinBox_freq, 0, 1, 1, 1)

        self.label_2 = QLabel(self.groupBox_2)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout_4.addWidget(self.label_2, 2, 0, 1, 1)

        self.label = QLabel(self.groupBox_2)
        self.label.setObjectName(u"label")

        self.gridLayout_4.addWidget(self.label, 0, 0, 1, 1)

        self.doubleSpinBox_att = QDoubleSpinBox(self.groupBox_2)
        self.doubleSpinBox_att.setObjectName(u"doubleSpinBox_att")
        self.doubleSpinBox_att.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.doubleSpinBox_att.setDecimals(1)
        self.doubleSpinBox_att.setMaximum(200.000000000000000)
        self.doubleSpinBox_att.setValue(10.000000000000000)

        self.gridLayout_4.addWidget(self.doubleSpinBox_att, 5, 1, 1, 1)

        self.label_7 = QLabel(self.groupBox_2)
        self.label_7.setObjectName(u"label_7")

        self.gridLayout_4.addWidget(self.label_7, 7, 0, 1, 1)

        self.label_10 = QLabel(self.groupBox_2)
        self.label_10.setObjectName(u"label_10")

        self.gridLayout_4.addWidget(self.label_10, 5, 2, 1, 1)

        self.label_11 = QLabel(self.groupBox_2)
        self.label_11.setObjectName(u"label_11")

        self.gridLayout_4.addWidget(self.label_11, 7, 2, 1, 1)

        self.doubleSpinBox_meastime = QDoubleSpinBox(self.groupBox_2)
        self.doubleSpinBox_meastime.setObjectName(u"doubleSpinBox_meastime")
        self.doubleSpinBox_meastime.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.doubleSpinBox_meastime.setDecimals(2)
        self.doubleSpinBox_meastime.setMinimum(0.000000000000000)
        self.doubleSpinBox_meastime.setMaximum(1000.000000000000000)

        self.gridLayout_4.addWidget(self.doubleSpinBox_meastime, 4, 1, 1, 1)

        self.widget_3 = QWidget(self.groupBox_2)
        self.widget_3.setObjectName(u"widget_3")
        self.horizontalLayout_5 = QHBoxLayout(self.widget_3)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.radioButton_meastime_ms = QRadioButton(self.widget_3)
        self.radioButton_meastime_ms.setObjectName(u"radioButton_meastime_ms")
        self.radioButton_meastime_ms.setChecked(True)

        self.horizontalLayout_5.addWidget(self.radioButton_meastime_ms)

        self.radioButton_meastime_s = QRadioButton(self.widget_3)
        self.radioButton_meastime_s.setObjectName(u"radioButton_meastime_s")

        self.horizontalLayout_5.addWidget(self.radioButton_meastime_s)


        self.gridLayout_4.addWidget(self.widget_3, 4, 2, 1, 1, Qt.AlignmentFlag.AlignLeft)

        self.label_5 = QLabel(self.groupBox_2)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout_4.addWidget(self.label_5, 9, 0, 1, 1)

        self.doubleSpinBox_rbw = QDoubleSpinBox(self.groupBox_2)
        self.doubleSpinBox_rbw.setObjectName(u"doubleSpinBox_rbw")
        self.doubleSpinBox_rbw.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.doubleSpinBox_rbw.setDecimals(0)
        self.doubleSpinBox_rbw.setMinimum(1.000000000000000)
        self.doubleSpinBox_rbw.setMaximum(1000.000000000000000)

        self.gridLayout_4.addWidget(self.doubleSpinBox_rbw, 2, 1, 1, 1)

        self.comboBox_detec = QComboBox(self.groupBox_2)
        self.comboBox_detec.addItem("")
        self.comboBox_detec.addItem("")
        self.comboBox_detec.addItem("")
        self.comboBox_detec.setObjectName(u"comboBox_detec")

        self.gridLayout_4.addWidget(self.comboBox_detec, 8, 1, 1, 1)

        self.widget = QWidget(self.groupBox_2)
        self.widget.setObjectName(u"widget")
        self.horizontalLayout_3 = QHBoxLayout(self.widget)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.radioButton_freq_1 = QRadioButton(self.widget)
        self.radioButton_freq_1.setObjectName(u"radioButton_freq_1")

        self.horizontalLayout_3.addWidget(self.radioButton_freq_1)

        self.radioButton_freq_k = QRadioButton(self.widget)
        self.radioButton_freq_k.setObjectName(u"radioButton_freq_k")
        self.radioButton_freq_k.setChecked(True)

        self.horizontalLayout_3.addWidget(self.radioButton_freq_k)

        self.radioButton_freq_M = QRadioButton(self.widget)
        self.radioButton_freq_M.setObjectName(u"radioButton_freq_M")

        self.horizontalLayout_3.addWidget(self.radioButton_freq_M)

        self.radioButton_freq_G = QRadioButton(self.widget)
        self.radioButton_freq_G.setObjectName(u"radioButton_freq_G")

        self.horizontalLayout_3.addWidget(self.radioButton_freq_G)


        self.gridLayout_4.addWidget(self.widget, 0, 2, 1, 3, Qt.AlignmentFlag.AlignLeft)

        self.widget_2 = QWidget(self.groupBox_2)
        self.widget_2.setObjectName(u"widget_2")
        self.horizontalLayout_4 = QHBoxLayout(self.widget_2)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.radioButton_rbw_1 = QRadioButton(self.widget_2)
        self.radioButton_rbw_1.setObjectName(u"radioButton_rbw_1")

        self.horizontalLayout_4.addWidget(self.radioButton_rbw_1)

        self.radioButton_rbw_k = QRadioButton(self.widget_2)
        self.radioButton_rbw_k.setObjectName(u"radioButton_rbw_k")
        self.radioButton_rbw_k.setChecked(True)

        self.horizontalLayout_4.addWidget(self.radioButton_rbw_k)

        self.radioButton_rbw_M = QRadioButton(self.widget_2)
        self.radioButton_rbw_M.setObjectName(u"radioButton_rbw_M")

        self.horizontalLayout_4.addWidget(self.radioButton_rbw_M)


        self.gridLayout_4.addWidget(self.widget_2, 2, 2, 1, 3, Qt.AlignmentFlag.AlignLeft)

        self.label_4 = QLabel(self.groupBox_2)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout_4.addWidget(self.label_4, 8, 0, 1, 1)

        self.label_6 = QLabel(self.groupBox_2)
        self.label_6.setObjectName(u"label_6")

        self.gridLayout_4.addWidget(self.label_6, 5, 0, 1, 1)

        self.comboBox_preamp = QComboBox(self.groupBox_2)
        self.comboBox_preamp.addItem("")
        self.comboBox_preamp.addItem("")
        self.comboBox_preamp.setObjectName(u"comboBox_preamp")

        self.gridLayout_4.addWidget(self.comboBox_preamp, 9, 1, 1, 1)

        self.doubleSpinBox_minatt = QDoubleSpinBox(self.groupBox_2)
        self.doubleSpinBox_minatt.setObjectName(u"doubleSpinBox_minatt")
        self.doubleSpinBox_minatt.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.doubleSpinBox_minatt.setDecimals(1)
        self.doubleSpinBox_minatt.setMaximum(200.000000000000000)
        self.doubleSpinBox_minatt.setValue(10.000000000000000)

        self.gridLayout_4.addWidget(self.doubleSpinBox_minatt, 7, 1, 1, 1)

        self.checkBox_rbw_auto = QCheckBox(self.groupBox_2)
        self.checkBox_rbw_auto.setObjectName(u"checkBox_rbw_auto")

        self.gridLayout_4.addWidget(self.checkBox_rbw_auto, 3, 1, 1, 1)

        self.checkBox_att_auto = QCheckBox(self.groupBox_2)
        self.checkBox_att_auto.setObjectName(u"checkBox_att_auto")

        self.gridLayout_4.addWidget(self.checkBox_att_auto, 6, 1, 1, 1)


        self.horizontalLayout_2.addWidget(self.groupBox_2)


        self.verticalLayout_2.addWidget(self.frame_2)

        self.groupBox_3 = QGroupBox(self.centralwidget)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.gridLayout_3 = QGridLayout(self.groupBox_3)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.scrollArea_2 = QScrollArea(self.groupBox_3)
        self.scrollArea_2.setObjectName(u"scrollArea_2")
        self.scrollArea_2.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 898, 98))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents_2)
        self.gridLayout.setObjectName(u"gridLayout")
        self.plainTextEdit_output = QPlainTextEdit(self.scrollAreaWidgetContents_2)
        self.plainTextEdit_output.setObjectName(u"plainTextEdit_output")

        self.gridLayout.addWidget(self.plainTextEdit_output, 0, 0, 1, 1)

        self.scrollArea_2.setWidget(self.scrollAreaWidgetContents_2)

        self.gridLayout_3.addWidget(self.scrollArea_2, 1, 0, 1, 1)


        self.verticalLayout_2.addWidget(self.groupBox_3)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 954, 30))
        self.menuReceiver = QMenu(self.menubar)
        self.menuReceiver.setObjectName(u"menuReceiver")
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)
#if QT_CONFIG(shortcut)
        self.label_3.setBuddy(self.doubleSpinBox_meastime)
        self.label_2.setBuddy(self.doubleSpinBox_rbw)
        self.label.setBuddy(self.doubleSpinBox_freq)
        self.label_7.setBuddy(self.doubleSpinBox_minatt)
        self.label_5.setBuddy(self.comboBox_preamp)
        self.label_4.setBuddy(self.comboBox_detec)
        self.label_6.setBuddy(self.doubleSpinBox_att)
#endif // QT_CONFIG(shortcut)
        QWidget.setTabOrder(self.plainTextEdit_ini, self.plainTextEdit_output)
        QWidget.setTabOrder(self.plainTextEdit_output, self.doubleSpinBox_freq)
        QWidget.setTabOrder(self.doubleSpinBox_freq, self.radioButton_freq_1)
        QWidget.setTabOrder(self.radioButton_freq_1, self.radioButton_freq_k)
        QWidget.setTabOrder(self.radioButton_freq_k, self.radioButton_freq_M)
        QWidget.setTabOrder(self.radioButton_freq_M, self.radioButton_freq_G)
        QWidget.setTabOrder(self.radioButton_freq_G, self.doubleSpinBox_rbw)
        QWidget.setTabOrder(self.doubleSpinBox_rbw, self.radioButton_rbw_1)
        QWidget.setTabOrder(self.radioButton_rbw_1, self.radioButton_rbw_k)
        QWidget.setTabOrder(self.radioButton_rbw_k, self.radioButton_rbw_M)
        QWidget.setTabOrder(self.radioButton_rbw_M, self.doubleSpinBox_meastime)
        QWidget.setTabOrder(self.doubleSpinBox_meastime, self.radioButton_meastime_ms)
        QWidget.setTabOrder(self.radioButton_meastime_ms, self.radioButton_meastime_s)
        QWidget.setTabOrder(self.radioButton_meastime_s, self.doubleSpinBox_att)
        QWidget.setTabOrder(self.doubleSpinBox_att, self.doubleSpinBox_minatt)
        QWidget.setTabOrder(self.doubleSpinBox_minatt, self.comboBox_detec)
        QWidget.setTabOrder(self.comboBox_detec, self.comboBox_preamp)
        QWidget.setTabOrder(self.comboBox_preamp, self.scrollArea)
        QWidget.setTabOrder(self.scrollArea, self.scrollArea_2)

        self.menubar.addAction(self.menuReceiver.menuAction())
        self.menubar.addAction(self.menuFile.menuAction())
        self.menuReceiver.addAction(self.actionInfo)
        self.menuReceiver.addSeparator()
        self.menuReceiver.addAction(self.actionQuit)
        self.menuFile.addAction(self.actionOpen_Ini_File)

        self.retranslateUi(MainWindow)
        self.actionQuit.triggered.connect(MainWindow.close)
        self.pushButton_load_ini.clicked.connect(self.actionOpen_Ini_File.trigger)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionInfo.setText(QCoreApplication.translate("MainWindow", u"Info", None))
        self.actionQuit.setText(QCoreApplication.translate("MainWindow", u"Quit", None))
        self.actionOpen_Ini_File.setText(QCoreApplication.translate("MainWindow", u"Open Ini-File", None))
        self.pushButton_trigger.setText(QCoreApplication.translate("MainWindow", u"Trigger", None))
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"Level:", None))
        self.label_level.setText(QCoreApplication.translate("MainWindow", u"-100,5", None))
        self.label_levelunit.setText(QCoreApplication.translate("MainWindow", u"dBuV", None))
        self.groupBox.setTitle(QCoreApplication.translate("MainWindow", u"Ini File", None))
        self.plainTextEdit_ini.setPlainText(QCoreApplication.translate("MainWindow", u"[DESCRIPTION]\n"
"description: R&S ESHS30\n"
"type:            RECEIVER\n"
"vendor:       Rohde&Schwarz\n"
"serialnr:\n"
"deviceid:\n"
"driver:         rec_rs_ESHS30.py\n"
"\n"
"[Init_Value]\n"
"fstart: 9e3\n"
"fstop: 30e6\n"
"fstep: 1\n"
"visa: GPIB0::17::INSTR\n"
"virtual: 0\n"
"\n"
"[Channel_1]\n"
"name: RFin\n"
"min_attenuation: 10\n"
"meas_time: 0.05\n"
"preamplifier: on\n"
"unit: Watt\n"
"attenuation: auto\n"
"rbw: auto\n"
"detector: PEAK", None))
        self.pushButton_load_ini.setText(QCoreApplication.translate("MainWindow", u"Load Ini-File", None))
        self.pushButton_init.setText(QCoreApplication.translate("MainWindow", u"Init", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("MainWindow", u"Functions", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Meas Time", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Bandwidth", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Frequency", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"Min Attenuation", None))
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"dB", None))
        self.label_11.setText(QCoreApplication.translate("MainWindow", u"dB", None))
        self.radioButton_meastime_ms.setText(QCoreApplication.translate("MainWindow", u"ms", None))
        self.radioButton_meastime_s.setText(QCoreApplication.translate("MainWindow", u"s", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Preamplifier", None))
        self.comboBox_detec.setItemText(0, QCoreApplication.translate("MainWindow", u"Peak", None))
        self.comboBox_detec.setItemText(1, QCoreApplication.translate("MainWindow", u"Average", None))
        self.comboBox_detec.setItemText(2, QCoreApplication.translate("MainWindow", u"QPeak", None))

        self.radioButton_freq_1.setText(QCoreApplication.translate("MainWindow", u"1", None))
        self.radioButton_freq_k.setText(QCoreApplication.translate("MainWindow", u"k", None))
        self.radioButton_freq_M.setText(QCoreApplication.translate("MainWindow", u"M", None))
        self.radioButton_freq_G.setText(QCoreApplication.translate("MainWindow", u"G", None))
        self.radioButton_rbw_1.setText(QCoreApplication.translate("MainWindow", u"1", None))
        self.radioButton_rbw_k.setText(QCoreApplication.translate("MainWindow", u"k", None))
        self.radioButton_rbw_M.setText(QCoreApplication.translate("MainWindow", u"M", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Detector", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"Attenuation", None))
        self.comboBox_preamp.setItemText(0, QCoreApplication.translate("MainWindow", u"Off", None))
        self.comboBox_preamp.setItemText(1, QCoreApplication.translate("MainWindow", u"On", None))

        self.checkBox_rbw_auto.setText(QCoreApplication.translate("MainWindow", u"Auto", None))
        self.checkBox_att_auto.setText(QCoreApplication.translate("MainWindow", u"Auto", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("MainWindow", u"Output", None))
        self.menuReceiver.setTitle(QCoreApplication.translate("MainWindow", u"Receiver", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
    # retranslateUi

