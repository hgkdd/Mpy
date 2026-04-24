# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'limits_ui.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

"""mpylab.limits.limits_ui module."""
from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QMainWindow, QMenuBar,
    QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
    QStatusBar, QTabWidget, QTextEdit, QTreeView,
    QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    """Ui_MainWindow class."""
    def setupUi(self, MainWindow):
        """setupUi method."""
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1342, 772)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout_3 = QGridLayout(self.centralwidget)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.frame = QFrame(self.centralwidget)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.treeView = QTreeView(self.frame)
        self.treeView.setObjectName(u"treeView")

        self.horizontalLayout_2.addWidget(self.treeView)

        self.groupBox_variations = QGroupBox(self.frame)
        self.groupBox_variations.setObjectName(u"groupBox_variations")
        self.verticalLayout = QVBoxLayout(self.groupBox_variations)
        self.verticalLayout.setObjectName(u"verticalLayout")

        self.horizontalLayout_2.addWidget(self.groupBox_variations)

        self.tabWidget = QTabWidget(self.frame)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab_description = QWidget()
        self.tab_description.setObjectName(u"tab_description")
        self.gridLayout = QGridLayout(self.tab_description)
        self.gridLayout.setObjectName(u"gridLayout")
        self.textEdit_description = QTextEdit(self.tab_description)
        self.textEdit_description.setObjectName(u"textEdit_description")
        self.textEdit_description.setAcceptDrops(False)
        self.textEdit_description.setUndoRedoEnabled(False)
        self.textEdit_description.setReadOnly(True)

        self.gridLayout.addWidget(self.textEdit_description, 0, 0, 1, 1)

        self.tabWidget.addTab(self.tab_description, "")
        self.tab_graph = QWidget()
        self.tab_graph.setObjectName(u"tab_graph")
        self.gridLayout_2 = QGridLayout(self.tab_graph)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.scrollArea_graph = QScrollArea(self.tab_graph)
        self.scrollArea_graph.setObjectName(u"scrollArea_graph")
        self.scrollArea_graph.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 542, 540))
        self.gridLayout_5 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.verticalLayout_graph = QVBoxLayout()
        self.verticalLayout_graph.setObjectName(u"verticalLayout_graph")

        self.gridLayout_5.addLayout(self.verticalLayout_graph, 0, 0, 1, 1)

        self.scrollArea_graph.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.scrollArea_graph, 0, 0, 1, 1)

        self.tabWidget.addTab(self.tab_graph, "")

        self.horizontalLayout_2.addWidget(self.tabWidget)


        self.gridLayout_3.addWidget(self.frame, 0, 0, 1, 1)

        self.frame_2 = QFrame(self.centralwidget)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame_2)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(1220, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.pushButton_quit = QPushButton(self.frame_2)
        self.pushButton_quit.setObjectName(u"pushButton_quit")

        self.horizontalLayout.addWidget(self.pushButton_quit)


        self.gridLayout_3.addWidget(self.frame_2, 1, 0, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1342, 33))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.pushButton_quit.clicked.connect(MainWindow.close)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        """retranslateUi method."""
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.groupBox_variations.setTitle(QCoreApplication.translate("MainWindow", u"Variations", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_description), QCoreApplication.translate("MainWindow", u"Description", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_graph), QCoreApplication.translate("MainWindow", u"Graph", None))
        self.pushButton_quit.setText(QCoreApplication.translate("MainWindow", u"Quit", None))
    # retranslateUi

