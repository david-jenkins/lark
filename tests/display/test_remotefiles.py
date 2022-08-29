

import sys
from pathlib import Path, PurePath

from PyQt5 import QtWidgets as QtW

from lark.display.widgets.remote_files import RemoteFilePicker

DATA_DIR = "/home/canapyrtc"

def getDataDir(subdir=""):
    tmp = Path(DATA_DIR)/subdir
    if subdir == "":
        if not tmp.exists():
            tmp.mkdir(parents=True)
    if not tmp.is_dir():
        if tmp.exists():
            return str(tmp)
    stuff = [p for p in tmp.iterdir() if not p.name.startswith(".")]
    return {
        "name":str(tmp),
        "dirs":[p.name for p in stuff if p.is_dir()],
        "file":[p.name for p in stuff if not p.is_dir()]
    }

class Dummy: pass
config = Dummy()
config.lark = Dummy()
config.lark.getDataDir = getDataDir

# config.lark = None

class TestWidget(QtW.QWidget):
    def __init__(self,parent=None):
        QtW.QWidget.__init__(self,parent=parent)

        self.vlay = QtW.QVBoxLayout()

        self.button = QtW.QPushButton("Open")

        self.vlay.addWidget(self.button)

        self.setLayout(self.vlay)

        self.button.clicked.connect(self.callback)

    def callback(self):
        if config.lark is not None:
            d = RemoteFilePicker(self)#,dirs_only=True)
            answer = d.exec()
            if answer:
                print(d.fname)
            else:
                self.close()

def main():
    app = QtW.QApplication(sys.argv)
    win = TestWidget()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()