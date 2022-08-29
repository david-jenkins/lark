import sys
import atexit

from PyQt5 import QtWidgets as QtW
from lark.display.main import MainWindow
import pyqtgraph as pg
    # pyqtgraph does some cleanup that is MAYBE not necessary anymore
    # it raises an exception on exit when using RPyC, this disables the
    # cleanup routine
pg.setConfigOption('exitCleanup', False)

import lark

def larkplot(prefix):
    larkconfig = lark.LarkConfig(prefix)
    app = QtW.QApplication(sys.argv)
    win = MainWindow(larkconfig)
    win.show()


    ret = app.exec()
    sys.exit(ret)