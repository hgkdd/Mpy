from importlib import import_module

from PySide6 import QtWidgets
from PySide6.QtWidgets import QFileSystemModel, QFileIconProvider
from PySide6.QtCore import QDir

from limits_ui import Ui_MainWindow

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.populate_tree()

        self.treeView.clicked.connect(self.tree_view_clicked)

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

    def tree_view_clicked(self):
        index = self.treeView.selectedIndexes()[0]
        info = self.treeView.model().fileInfo(index)
        name = info.fileName()
        path = info.absolutePath()
        try:
            mod = import_module(f'.{name.rstrip('.py')}', package='mpylab.limits.conducted_emission')
            des = mod.LIMIT().description
            self.textEdit_description.setMarkdown(des)
        except Exception as e:
            print(e)

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()

    window.show()
    app.exec()