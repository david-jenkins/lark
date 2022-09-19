




from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from PyQt5 import QtGui as QtG
from lark.display.widgets.misc import ModeItem, OptionsItem, OptionsWidget

class HorizontalTabBar(QtW.QTabBar):
    """A wrapper wround Qt QTabBar to allow easy horizontal tab bars
    when the bar is on the left or right side
    """
    def paintEvent(self, event):
        painter = QtW.QStylePainter(self)
        option = QtW.QStyleOptionTab()
        for index in range(self.count()):
            self.initStyleOption(option, index)
            painter.drawControl(QtW.QStyle.CE_TabBarTabShape, option)
            painter.drawText(self.tabRect(index),
                             QtC.Qt.AlignCenter | QtC.Qt.TextDontClip,
                             self.tabText(index))

    def tabSizeHint(self, index:int) -> QtC.QSize:
        size = QtW.QTabBar.tabSizeHint(self, index)
        if size.width() < size.height():
            size.transpose()
        return size

class TabWidget(QtW.QTabWidget):
    """A wrapper around QTabWidget to globally change the position of the tab bar
    although currently it just puts it at the top to allow the pop out button to work
    I haven't worked out how to use the pop out button with the HorizontalTabBar above...
    """
    def __init__(self, parent:QtW.QWidget = None) -> None:
        QtW.QTabWidget.__init__(self, parent)
        if parent is not None and not isinstance(parent,QtW.QMainWindow):
            self.setTabPosition(QtW.QTabWidget.North) # currently the tab bar is put at the top
            # self.setTabBar(HorizontalTabBar()) # use the horizontal tab names when on the side
            # self.setTabPosition(QtW.QTabWidget.West) # put tab bar on the left
            # self.setTabPosition(QtW.QTabWidget.South) # put the tab bar on the bottom

class SubTabWidget(TabWidget):
    """A wrapper around TabWidget(QTabWidget) to allow popping tabs out to windows.
    And to let them pop back in

    """
    def __init__(self, parent:QtW.QWidget = None) -> None:
        super().__init__(parent=parent)
        self.widgets = {}
        self.popout = QtW.QPushButton("Pop Out")
        self.popout.clicked.connect(self.popout_tab)
        self.setCornerWidget(self.popout, corner=QtC.Qt.TopRightCorner)
        # self.tabBar().setB
        self.menu = QtW.QMenu("Menu",self)
        self.poppedout = {}

    def addWidget(self, widget:QtW.QWidget, name:str) -> None:
        """Add a new widget to the tab page

        Args:
            widget (QtW.QWidget): he widget to add
            name (str): the widget name
        """
        self.widgets[name] = widget
        self.addTab(widget, name)
        if widget.menu is not None:
            self.menu.addMenu(widget.menu)

    def insertWidget(self, index:int, widget:QtW.QWidget, name:str) -> None:
        """Insert a widget at the specified index

        Args:
            index (int): _description_
            widget (QtW.QWidget): _description_
            name (str): _description_
        """
        self.widgets[name] = widget
        self.insertTab(index, widget, name)
        if widget.menu is not None:
            self.menu.addMenu(widget.menu)

    def closeEvent(self, event:QtG.QCloseEvent) -> None:
        """Make sure all widgets and popouts close as well

        Args:
            event (QtG.QCloseEvent): _description_
        """
        for name,widget in self.widgets.items():
            widget.close()
        for name in list(self.poppedout):
            self.poppedout[name].close()
        return super().closeEvent(event)

    def addMenus(self, menu:QtW.QMenu):
        """Add all the menus from child widgets to the supplied menu

        Args:
            menu (_type_): _description_
        """
        for name,widget in self.widgets.items():
            widget:QtW.QWidget
            if widget.menu is not None:
                menu.addMenu(widget.menu)

    def on_connect(self):
        """Propagate on_connect to child widgets
        """
        for name,widget in self.widgets.items():
            try:
                widget.on_connect()
            except AttributeError as e:
                print(e)

    def on_disconnect(self):
        """Propagate on_disconnect to child widgets
        """
        for name,widget in self.widgets.items():
            try:
                widget.on_disconnect()
            except AttributeError as e:
                print(e)

    def popout_tab(self):
        """Called when the pop-out button is pressed and pops out the current
        tab into its own window
        """
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

    def popin_tab(self, widget:QtW.QWidget, name:str, index:int) -> None:
        """Pop a widget back into the tab window, called when the popped out tab closes itself"""
        widget.setParent(self)
        del self.poppedout[name]
        self.insertTab(index,widget,name)

class LarkTab(QtW.QWidget):
    """The default class to inherit when making a GUI tab.
    This ensures it has the right attributes.
    """
    def __init__(self, parent:QtW.QWidget = None) -> None:
        super().__init__(parent=parent)
        self.menu = None

    def on_connect(self) -> None:
        pass

    def on_disconnect(self) -> None:
        pass

class DetachedTab(QtW.QMainWindow):
    """A wrapper class for detached widget tabs to act as windows
    """
    popinSig = QtC.pyqtSignal(object, str, int)
    def __init__(self, widget:QtW.QWidget, name:str, index:int) -> None:
        """
        Args:
            widget (QtW.QWidget): The tab widget to detach
            name (str): THe name of the widget to use as window title
            index (int): The widget index in a tab list for reinsertion later
        """
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
    """The main widget to inherit when creating a tabbed page.
    It can be used to store child displays and will propagate some
    functions to them when called on this class

    Args:
        SubTabWidget (_type_): _description_
    """
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
    def __init__(self, parent:QtW.QWidget = None):
        """A wrapper around QMainWindow, takes the cental widget as an argument
        Propagates function calls to the central widget
        The Main Widget class for creating a GUI window.

        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent=parent)
        menu = self.menuBar()
        self.filemenu = QtW.QMenu("&File")
        self.quitAction = QtW.QAction('&Quit')
        self.filemenu.addAction(self.quitAction)
        self.quitAction.triggered.connect(self.close)
        menu.addMenu(self.filemenu)

    def closeEvent(self, event):
        self.centralWidget().close()
        return super().closeEvent(event)

    def on_connect(self):
        self.centralWidget().on_connect()

    def on_disconnect(self):
        self.centralWidget().on_disconnect()

class ObservingBlockOpener_GUIbase(QtW.QWidget):
    """Base class for the observing block opener widget
    GUIbase classes are used to define the GUI layout instead of in a ui file"""
    def __init__(self, parent:QtW.QWidget = None) -> None:
        super().__init__(parent=parent)
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
