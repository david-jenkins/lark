




from abc import ABC
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from PyQt5 import QtGui as QtG
from lark.display.widgets.misc import ModeItem, OptionsItem, OptionsWidget
from lark.utils import UpperDict

class HorizontalTabBar(QtW.QTabBar):
    def paintEvent(self, event):
        painter = QtW.QStylePainter(self)
        option = QtW.QStyleOptionTab()
        for index in range(self.count()):
            self.initStyleOption(option, index)
            painter.drawControl(QtW.QStyle.CE_TabBarTabShape, option)
            painter.drawText(self.tabRect(index),
                             QtC.Qt.AlignCenter | QtC.Qt.TextDontClip,
                             self.tabText(index))

    def tabSizeHint(self, index):
        size = QtW.QTabBar.tabSizeHint(self, index)
        if size.width() < size.height():
            size.transpose()
        return size

class TabWidget(QtW.QTabWidget):
    def __init__(self, parent=None):
        QtW.QTabWidget.__init__(self, parent)
        if parent is not None and not isinstance(parent,QtW.QMainWindow):
            # self.setTabBar(HorizontalTabBar())
            # self.setTabPosition(QtW.QTabWidget.West)
            # self.setTabPosition(QtW.QTabWidget.South)
            self.setTabPosition(QtW.QTabWidget.North)

class SubTabWidget(TabWidget):
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        self.widgets = {}
        self.popout = QtW.QPushButton("Pop Out")
        self.popout.clicked.connect(self.popout_tab)
        self.setCornerWidget(self.popout, corner=QtC.Qt.TopRightCorner)
        # self.tabBar().setB
        self.menu = QtW.QMenu("Menu",self)
        self.poppedout = {}

    def addWidget(self, widget, name):
        self.widgets[name] = widget
        self.addTab(widget, name)
        if widget.menu is not None:
            self.menu.addMenu(widget.menu)

    def insertWidget(self, index, widget, name):
        self.widgets[name] = widget
        self.insertTab(index, widget, name)
        if widget.menu is not None:
            self.menu.addMenu(widget.menu)

    def closeEvent(self, event):
        for name,widget in self.widgets.items():
            widget.close()
        for name in list(self.poppedout):
            self.poppedout[name].close()
        return super().closeEvent(event)

    def addMenus(self,menu):
        for name,widget in self.widgets.items():
            if widget.menu is not None:
                menu.addMenu(widget.menu)

    def on_connect(self):
        for name,widget in self.widgets.items():
            widget.on_connect()

    def on_disconnect(self):
        for name,widget in self.widgets.items():
            widget.on_disconnect()
            
    def popout_tab(self):
        widget = self.currentWidget()
        index = self.currentIndex()
        if index != -1:
            txt = self.tabText(index)
            framegeom = widget.frameGeometry()
            dtab = DetachedTab(widget, txt, index)
            dtab.setGeometry(framegeom)
            dtab.move(QtG.QCursor.pos())#-framegeom.bottomRight())
            dtab.popinSig.connect(self.popin_tab)
            self.poppedout[txt] = dtab
            dtab.show()

    def popin_tab(self, widget, name, index):
        widget.setParent(self)
        del self.poppedout[name]
        self.insertTab(index,widget,name)

class DetachedTab(QtW.QMainWindow):
    popinSig = QtC.pyqtSignal(object, str, int)
    def __init__(self,widget,name,index):
        super().__init__(parent=None)
        self.setWindowTitle(name)
        self.setCentralWidget(widget)
        widget.show()
        self.widget = widget
        self.name = name
        self.index = index
        
    def closeEvent(self, event) -> None:
        self.popinSig.emit(self.widget, self.name, self.index)
        super().closeEvent(event)

class MainTabWidget(SubTabWidget):
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        self.subdisplays = []

    def closeEvent(self, event):
        for s in self.subdisplays:
            s.close()
        return super().closeEvent(event)

    def on_connect(self):
        super().on_connect()
        for d in self.subdisplays:
            d.on_connect()

    def on_disconnect(self):
        super().on_disconnect()
        for d in self.subdisplays:
            d.on_disconnect()

    def add_display(self, display):
        self.subdisplays.append(display)

    def remove_display(self, display):
        self.subdisplays.remove(display)

class MainWindow(QtW.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        menu = self.menuBar()
        self.filemenu = QtW.QMenu("&File")
        self.quitAction = QtW.QAction('&Quit')
        self.filemenu.addAction(self.quitAction)
        self.quitAction.triggered.connect(self.close)
        menu.addMenu(self.filemenu)

    def closeEvent(self, event):
        self.main.close()
        return super().closeEvent(event)

    def on_connect(self):
        self.main.on_connect()

    def on_disconnect(self):
        self.main.on_disconnect()

class ObservingBlockOpener_base(QtW.QWidget):
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        """Open an observing block"""

        self.mode_list = QtW.QListWidget()
        # self.mode_list.setStyleSheet("QListWidget::item { background-color: red; border-bottom: 1px solid black; }")
        self.mode_list.setStyleSheet("QListWidget::item { background-color: lightgray;\
    border-style: outset;\
    border-width: 2px;\
    border-radius: 10px;\
    border-color: beige;\
    font: bold 14px;\
    min-width: 10em;  }" "QListWidget::item:selected { \
            background-color: rgba(0, 0, 224, 50); \
            border-style: inset; }")
        self.modestart_button = QtW.QPushButton("Start")
        self.modestop_button = QtW.QPushButton("Stop")
        self.modeopen_button = QtW.QPushButton("Open")
        self.modeinfo_textbox = QtW.QPlainTextEdit()
        self.modeinfo_textbox.setReadOnly(True)

        self.prefix_label = QtW.QLabel("Running DARCS:")
        self.prefix_list = QtW.QListWidget()
        self.prefixopen_button = QtW.QPushButton("Open")
        self.prefixstop_button = QtW.QPushButton("Stop")
        self.stopall_button = QtW.QPushButton("Stop All")

        self.options_item = OptionsItem(self)

        self.options_widget = OptionsWidget(self)

        self.messagebox = QtW.QMessageBox()

        self.prefix_lay = QtW.QGridLayout()

        self.prefix_lay.addWidget(self.prefix_label,0,0,1,2)
        self.prefix_lay.addWidget(self.prefix_list,1,0,1,2)
        self.prefix_lay.addWidget(self.prefixopen_button,2,0,1,1)
        self.prefix_lay.addWidget(self.prefixstop_button,2,1,1,1)
        self.prefix_lay.addWidget(self.stopall_button,3,0,1,2)

        self.mode_lay = QtW.QGridLayout()

        self.mode_lay.addWidget(self.modestart_button,0,0,1,1)
        self.mode_lay.addWidget(self.modeopen_button,0,1,1,1)
        self.mode_lay.addWidget(self.modestop_button,0,2,1,1)
        self.mode_lay.addWidget(self.modeinfo_textbox,1,0,1,3)

        self.mode_frame = QtW.QFrame()
        self.mode_frame.setLayout(self.mode_lay)

        self.hlay = QtW.QHBoxLayout()

        self.vlay = QtW.QVBoxLayout()
        self.vlay.addWidget(self.options_item)
        self.vlay.addWidget(self.mode_list)

        self.hlay.addLayout(self.vlay,1)
        self.hlay.addWidget(self.mode_frame,2)
        self.hlay.addWidget(self.options_widget,2)
        self.hlay.addLayout(self.prefix_lay,1)

        self.setLayout(self.hlay)

    def addModeWidget(self, name, status1, status2):
        mode_widget = ModeItem(self.mode_list)
        mode_widget.setName(name)
        mode_widget.setStatus(status1,status2)
        mode_item = QtW.QListWidgetItem(self.mode_list)
        mode_item.setSizeHint(mode_widget.sizeHint())
        mode_item.setBackground(QtG.QColor(180,180,180,255))
        self.mode_list.addItem(mode_item)
        self.mode_list.setItemWidget(mode_item, mode_widget)
