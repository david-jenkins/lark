import sys
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from PyQt5 import QtGui as QtG

from lark.display.widgets.main_base import TabWidget

class StatsMain(TabWidget):
    def __init__(self,parent=None):
        TabWidget.__init__(self,parent=parent)
        self.menu = QtW.QMenu("Stats",self)

    def on_connect(self):
        print("connecting stats")

def main():
    app = QtW.QApplication(sys.argv)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()