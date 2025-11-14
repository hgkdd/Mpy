import os
from importlib import import_module

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from PySide6 import QtWidgets
from PySide6.QtWidgets import (QFileSystemModel, QFileIconProvider,
                               QLabel, QSpacerItem, QSizePolicy, QComboBox, QLayout)
from PySide6.QtCore import QDir
from PySide6.QtGui import QAbstractFileIconProvider

from mpylab.tools.spacing import linspace, logspace

from limits_ui import Ui_MainWindow

os.environ["QT_API"] = "PySide6"


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.mod = None
        self.limit = None

        self.setupUi(self)
        self.populate_tree()

        self.treeView.clicked.connect(self.tree_view_clicked)

        self.plot_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        #self.plot_canvas.axes.plot([0, 1, 2, 3, 4], [10, 1, 20, 3, 40])
        self.plot_toolbar = NavigationToolbar(self.plot_canvas, self)
        layout = self.verticalLayout_graph
        layout.addWidget(self.plot_toolbar)
        layout.addWidget(self.plot_canvas)
        self.plot_canvas.show()




    def populate_tree(self, root_path='.'):
        model = QFileSystemModel()
        icon_provider = QFileIconProvider()
        model.setIconProvider(icon_provider)
        model.setRootPath("")
        model.setOption(QFileSystemModel.DontUseCustomDirectoryIcons)
        model.setOption(QFileSystemModel.DontWatchForChanges)
        tree = self.treeView
        tree.setModel(model)
        if root_path:
            root_index = model.index(QDir.cleanPath(root_path))
            if root_index.isValid():
                tree.setRootIndex(root_index)
        tree.hideColumn(1)
        tree.hideColumn(2)
        tree.hideColumn(3)

    def tree_view_clicked(self):
        index = self.treeView.selectedIndexes()[0]
        info = self.treeView.model().fileInfo(index)
        name = info.fileName()
        path = info.absolutePath()
        try:
            self.mod = import_module(f'.{name.rstrip('.py')}', package='mpylab.limits.conducted_emission')
            #des = mod.LIMIT().description
            self.textEdit_description.setMarkdown('Please choose from variations.')
        except Exception as e:
            pass
        self.variations = self.mod.LIMIT().variations
        self.var_combobox = {}
        layout = self.groupBox_variations.layout()
        self.clearLayout(layout)
        for label, vars in self.variations.items():
            qlabel = QLabel(label)
            layout.addWidget(qlabel)
            qlabel.show()
            combobox = QComboBox()
            combobox.addItems((str(_v) for _v in vars))
            layout.addWidget(combobox)
            self.var_combobox[label] = combobox
            combobox.show()
            combobox.currentIndexChanged.connect(self.update_description)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.update_description()


    def update_description(self):
        kw = {}
        for label, vars in self.variations.items():
            combobox = self.var_combobox[label]
            txt = combobox.currentText()
            kw[label.lower()] = txt

        self.limit = self.mod.LIMIT(**kw)
        des = self.limit.description
        self.textEdit_description.setMarkdown(des)
        self.update_plot()

    def update_plot(self):
        if not self.limit:
            return
        fmin = self.limit.fmin
        fmax = self.limit.fmax
        freqs = logspace(fmin,fmax,1.01,endpoint=True)
        limits = self.limit.limitline(freqs)
        self.plot_canvas.axes.cla()  # Clear the canvas.
        self.plot_canvas.axes.semilogx(freqs, limits)
        self.plot_canvas.axes.grid(True)
        self.plot_canvas.axes.set_xlabel('Frequency in Hz')
        self.plot_canvas.axes.set_ylabel(f'Limit in {self.limit.unit}')
        self.plot_canvas.axes.set_title(self.limit.description_title)
        # Trigger the canvas to update and redraw.
        self.plot_canvas.draw()

    def clearLayout(self, layout):
        if isinstance(layout, QLayout):
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clearLayout(item.layout())

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()

    window.show()
    app.exec()