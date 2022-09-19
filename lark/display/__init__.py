import sys

from PyQt5 import QtWidgets as QtW
from lark.display.main import MainLarkWindow
import pyqtgraph as pg
    # pyqtgraph does some cleanup that is MAYBE not necessary anymore
    # it raises an exception on exit when using RPyC, this disables the
    # cleanup routine
pg.setConfigOption('exitCleanup', False)

from lark import LarkConfig

def larkplot(prefix):
    larkconfig = LarkConfig(prefix)
    app = QtW.QApplication(sys.argv)
    win = MainLarkWindow(larkconfig)
    win.show()
    sys.exit(app.exec())