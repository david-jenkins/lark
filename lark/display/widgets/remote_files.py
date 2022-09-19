

import sys
from pathlib import Path, PurePath

from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from PyQt5 import QtGui as QtG

from lark import LarkConfig, NoLarkError
from lark.interface import connectDaemon

class RemoteFilePicker(QtW.QDialog):
    def __init__(self,larkconfig,parent=None,dirs_only=False):
        QtW.QDialog.__init__(self,parent=parent)
        
        self.larkconfig = larkconfig

        self.dirs_only = dirs_only

        self.dirlabel = QtW.QLabel(self)

        self.dirlist = QtW.QListWidget(self)

        self.selectbutton = QtW.QPushButton("Select",self)
        self.cancelbutton = QtW.QPushButton("Cancel",self)

        self.vlay = QtW.QVBoxLayout()
        self.hlay = QtW.QHBoxLayout()

        self.vlay.addWidget(self.dirlabel)
        self.vlay.addWidget(self.dirlist)
        self.vlay.addLayout(self.hlay)

        self.hlay.addWidget(self.cancelbutton)
        self.hlay.addWidget(self.selectbutton)

        self.setLayout(self.vlay)


        self.selectbutton.clicked.connect(self.select_callback)
        self.cancelbutton.clicked.connect(self.cancel_callback)

        self.dirname = None
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
            self.dirlist.addItem("No Lark available")
        else:
            self.files = lrk.getDataDir()
            self.new_files()
            self.dirlist.doubleClicked.connect(self.dblclck_callback)
            self.dirlist.clicked.connect(self.clck_callback)

        self.basedir = self.dirname
        self.fname = self.dirname

        self.resize(400,500)

    def new_files(self):
        self.dirname = self.files["name"]
        self.dirs = self.files["dirs"]
        self.files = self.files["file"]
        self.dirlist.clear()
        self.dirlabel.setText(self.dirname)
        self.dirlist.addItem("(Up a Level)")
        for f in self.dirs:
            icon = QtW.QApplication.style().standardIcon(QtW.QStyle.SP_DirIcon)
            tmp = QtW.QListWidgetItem(icon,f)
            self.dirlist.addItem(tmp)
        if not self.dirs_only:
            for f in self.files:
                icon = QtW.QApplication.style().standardIcon(QtW.QStyle.SP_FileIcon)
                tmp = QtW.QListWidgetItem(icon,f)
                self.dirlist.addItem(tmp)

    def dblclck_callback(self):
        name = self.dirlist.currentItem().text()
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            if name=="(Up a Level)":
                if self.dirname == self.basedir:
                    return
                else:
                    tmp = PurePath(self.dirname).parent.relative_to(self.basedir)
                    self.files = lrk.getDataDir(str(tmp))
            else:
                tmp = (PurePath(self.dirname)/name).relative_to(self.basedir)
                self.files = lrk.getDataDir(str(tmp))
            if isinstance(self.files,str):
                self.fname = self.files
                self.accept()
            elif self.files is None:
                self.fname = ""
                self.dirname = ""
                self.reject()
            else:
                self.new_files()

    def clck_callback(self):
        name = self.dirlist.currentItem().text()
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            if name=="(Up a Level)":
                if self.dirname == self.basedir:
                    return
                else:
                    tmp = PurePath(self.dirname).parent.relative_to(self.basedir)
                    self.files = lrk.getDataDir(str(tmp))
            else:
                self.fname = self.dirname+"/"+name
                return
            if isinstance(self.files,str):
                self.fname = self.files
                self.accept()
            elif self.files is None:
                self.fname = ""
                self.dirname = ""
                self.reject()
            else:
                self.new_files()

    def select_callback(self):
        self.accept()

    def cancel_callback(self):
        self.reject()


class RemoteFilePicker(QtW.QDialog):
    def __init__(self,larkconfig:LarkConfig,parent=None,dirs_only=False):
        QtW.QDialog.__init__(self,parent=parent)
        
        self.larkconfig = larkconfig

        self.dirs_only = dirs_only

        self.dirlist = QtW.QTreeWidget(self)
        self.dirlist.populated = 0

        self.selectbutton = QtW.QPushButton("Select",self)
        self.cancelbutton = QtW.QPushButton("Cancel",self)

        self.vlay = QtW.QVBoxLayout()
        self.hlay = QtW.QHBoxLayout()

        self.vlay.addWidget(self.dirlist)
        self.vlay.addLayout(self.hlay)

        self.hlay.addWidget(self.cancelbutton)
        self.hlay.addWidget(self.selectbutton)

        self.setLayout(self.vlay)

        self.selectbutton.clicked.connect(self.select_callback)
        self.cancelbutton.clicked.connect(self.cancel_callback)

        self.items = []
        self.basedir = ""
        self.fname = ""
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
            tmp = QtW.QTreeWidgetItem(self.dirlist)
            tmp.setText(0,"No Lark available")
            self.items.append(tmp)
        else:
            self.files = lrk.getDataDir()
            self.new_files(self.dirlist)
            self.basedir = self.files["name"]
            self.fname = self.basedir
            self.dirlist.setHeaderLabel(self.basedir)
            self.dirlist.doubleClicked.connect(self.dblclck_callback)
            self.dirlist.itemSelectionChanged.connect(self.clck_callback)
            self.dirlist.keyPressEvent = self.keypress

        self.resize(400,500)

    def new_files(self,parent):
        dirname = self.files["name"]
        dirs = self.files["dirs"]
        files = self.files["file"]
        for f in dirs:
            tmp = QtW.QTreeWidgetItem(parent)
            icon = QtW.QApplication.style().standardIcon(QtW.QStyle.SP_DirIcon)
            tmp.setIcon(0,icon)
            tmp.setText(0,f)
            tmp.populated = 0
            tmp.dirname = dirname
            self.items.append(tmp)
        if not self.dirs_only:
            for f in files:
                tmp = QtW.QTreeWidgetItem(parent)
                icon = QtW.QApplication.style().standardIcon(QtW.QStyle.SP_FileIcon)
                tmp.setIcon(0,icon)
                tmp.setText(0,f)
                tmp.populated = 0
                tmp.dirname = dirname
                self.items.append(tmp)
        parent.populated = 1

    def dblclck_callback(self):
        item = self.dirlist.currentItem()
        if item.populated:
            return
        try:
            lrk = self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            name = item.text(0)
            print(f"NAME IS {name}")
            print(f"THIS {item.dirname} - {self.basedir}")
            tmp = (PurePath(item.dirname)/name).relative_to(self.basedir)
            self.files = lrk.getDataDir(tmp)
            print("got files", self.files)
            if isinstance(self.files,str):
                self.fname = self.files
                self.accept()
            elif self.files is None:
                self.fname = ""
                self.reject()
            else:
                self.new_files(self.dirlist.currentItem())

    def clck_callback(self):
        print("CLICK")
        item = self.dirlist.currentItem()
        name = item.text(0)
        self.fname = item.dirname+"/"+name

    def select_callback(self):
        self.accept()

    def cancel_callback(self):
        self.reject()

    def keypress(self,event):
        if (event.type()==QtC.QEvent.KeyPress) and (event.key()==QtC.Qt.Key_Space):
            print(event)
            item = self.dirlist.currentItem()
            self.dblclck_callback()
            if item.isExpanded():
                item.setExpanded(False)
            else:
                item.setExpanded(True)
        super(QtW.QTreeWidget,self.dirlist).keyPressEvent(event)


class DaemonFilePicker(QtW.QDialog):
    def __init__(self, host, subdir="/", parent=None, dirs_only=False):
        QtW.QDialog.__init__(self,parent=parent)
        
        self.host = host

        self.dirs_only = dirs_only
        self.dir_selected = False
                
        self.subdir = subdir

        self.dirlist = QtW.QTreeWidget(self)
        self.dirlist.populated = 0

        self.selectbutton = QtW.QPushButton("Select",self)
        self.cancelbutton = QtW.QPushButton("Cancel",self)

        self.vlay = QtW.QVBoxLayout()
        self.hlay = QtW.QHBoxLayout()

        self.vlay.addWidget(self.dirlist)
        self.vlay.addLayout(self.hlay)

        self.hlay.addWidget(self.cancelbutton)
        self.hlay.addWidget(self.selectbutton)

        self.setLayout(self.vlay)

        self.selectbutton.clicked.connect(self.select_callback)
        self.cancelbutton.clicked.connect(self.cancel_callback)

        self.items = []
        self.basedir = ""
        self.fname = ""
        try:
            daemon = connectDaemon(self.host)
        except Exception as e:
            print(e)
            tmp = QtW.QTreeWidgetItem(self.dirlist)
            tmp.setText(0,"No Host available")
            self.items.append(tmp)
        else:
            self.files = daemon.listDir(self.subdir)
            print(f"self.files = {self.files}")
            self.new_files(self.dirlist)
            self.basedir = self.files["name"]
            self.fname = self.basedir
            self.dir_selected = True
            self.dirlist.setHeaderLabel(self.basedir)
            self.dirlist.doubleClicked.connect(self.dblclck_callback)
            self.dirlist.itemSelectionChanged.connect(self.clck_callback)
            self.dirlist.keyPressEvent = self.keypress

        self.resize(400,500)

    def new_files(self, parent):
        dirname = self.files["name"]
        dirs = self.files["dirs"]
        files = self.files["file"]
        for f in dirs:
            tmp = QtW.QTreeWidgetItem(parent)
            icon = QtW.QApplication.style().standardIcon(QtW.QStyle.SP_DirIcon)
            tmp.setIcon(0,icon)
            tmp.setText(0,f)
            tmp.populated = 0
            tmp.dirname = dirname
            tmp.is_dir = True
            self.items.append(tmp)
        # if not self.dirs_only:
        for f in files:
            tmp = QtW.QTreeWidgetItem(parent)
            icon = QtW.QApplication.style().standardIcon(QtW.QStyle.SP_FileIcon)
            tmp.setIcon(0,icon)
            tmp.setText(0,f)
            tmp.populated = 0
            tmp.dirname = dirname
            tmp.is_dir = False
            self.items.append(tmp)
        parent.populated = 1

    def dblclck_callback(self):
        item = self.dirlist.currentItem()
        if item.populated:
            item = self.dirlist.currentItem()
            name = item.text(0)
            self.fname = item.dirname+"/"+name
            if item.isExpanded():
                item.setExpanded(False)
            else:
                item.setExpanded(True)
        else: 
            name = item.text(0)
            try:
                self.files = connectDaemon(self.host).listDir(PurePath(item.dirname)/name)
            except Exception as e:
                print(e)
                return
            print("got files", self.files)
            if isinstance(self.files,str):
                self.dir_selected = False
                self.fname = self.files
                self.select_callback()
            elif self.files is None:
                self.fname = ""
                self.reject()
            elif isinstance(self.files,dict):
                self.dir_selected = True
                self.new_files(self.dirlist.currentItem())
            self.selectbutton.setEnabled(not (not self.dir_selected and self.dirs_only))

    def clck_callback(self):
        print("CLICK")
        item = self.dirlist.currentItem()
        name = item.text(0)
        self.dir_selected = item.is_dir
        self.selectbutton.setEnabled(not (not self.dir_selected and self.dirs_only))
        self.fname = item.dirname+"/"+name

    def select_callback(self):
        if self.dirs_only and not self.dir_selected:
            return
        self.accept()

    def cancel_callback(self):
        self.reject()

    def keypress(self,event):
        if (event.type()==QtC.QEvent.KeyPress) and (event.key()==QtC.Qt.Key_Space):
            print(event)
            item = self.dirlist.currentItem()
            self.dblclck_callback()
            if item.isExpanded():
                item.setExpanded(False)
            else:
                item.setExpanded(True)
        super(QtW.QTreeWidget,self.dirlist).keyPressEvent(event)

class TestWidget(QtW.QWidget):
    def __init__(self,larkconfig,subdir="",parent=None):
        QtW.QWidget.__init__(self,parent=parent)
        
        self.larkconfig = larkconfig
        self.subdir = subdir

        self.vlay = QtW.QVBoxLayout()

        self.button = QtW.QPushButton("Open")

        self.vlay.addWidget(self.button)

        self.setLayout(self.vlay)

        self.button.clicked.connect(self.callback)

    def callback(self):
        try:
            self.larkconfig.getlark()
        except NoLarkError as e:
            print(e)
        else:
            d = RemoteFilePicker(self.larkconfig, self)#,dirs_only=True)
            answer = d.exec()
            if answer:
                print(d.fname)
            else:
                self.close()
            
class DaemonTestWidget(QtW.QWidget):
    def __init__(self,host,subdir="",parent=None):
        QtW.QWidget.__init__(self,parent=parent)
        
        self.host = host
        self.subdir = subdir

        self.vlay = QtW.QVBoxLayout()

        self.button = QtW.QPushButton("Open")

        self.vlay.addWidget(self.button)

        self.setLayout(self.vlay)

        self.button.clicked.connect(self.callback)

    def callback(self):
        try:
            daemon = connectDaemon(self.host)
        except Exception as e:
            print(e)
        else:
            d = DaemonFilePicker(self.host,self.subdir)#,dirs_only=True)
            answer = d.exec()
            if answer:
                print(d.fname)
            else:
                self.close()

def main():
    app = QtW.QApplication(sys.argv)
    win = DaemonTestWidget("LaserLab","/var/log/lark")
    # win = TestWidget(larkconfig=LarkConfig("LgsWF"))
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()