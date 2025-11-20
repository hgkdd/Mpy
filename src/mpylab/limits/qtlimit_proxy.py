import re

from PySide6.QtCore import QSortFilterProxyModel
from PySide6.QtWidgets import QTreeView, QFileSystemModel, QApplication


class Tree(QTreeView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        model = QFileSystemModel(self)
        model.setReadOnly(True)

        skip_exts = ['.ui']   # a list exentions to skip
        skip_regex = [r'__']  #, r'limit', 'qtlimit']
        proxy = HideFileTypesProxy(excludes=skip_exts, regexes=skip_regex, parent=self)
        proxy.setDynamicSortFilter(True)
        proxy.setSourceModel(model)

        self.setModel(proxy)

        idx = model.setRootPath(".")
        self.setRootIndex(proxy.mapFromSource(idx))

        self._model = model
        self._proxy = proxy
        self.hideColumn(1)
        self.hideColumn(2)
        self.hideColumn(3)

        self.resize(600,400)


class HideFileTypesProxy(QSortFilterProxyModel):
    """
    A proxy model that excludes files from the view
    that end with the given extension
    """

    def __init__(self, excludes=None, regexes=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if excludes is None:
            self._excludes = []
        else:
            self._excludes = excludes[:]
        if regexes is None:
            self._regexes = []
        else:
            self._regexes = regexes[:]

    def filterAcceptsRow(self, srcRow, srcParent):
        idx = self.sourceModel().index(srcRow, 0, srcParent)
        name = idx.data()

        # Can do whatever kind of tests you want here,
        # against the name
        for exc in self._excludes:
            if name.endswith(exc):
                return False
        for regex in self._regexes:
            if re.match(regex, name):
                return False

        return True

if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    tree = Tree()
    tree.show()
    tree.raise_()
    sys.exit(app.exec_())