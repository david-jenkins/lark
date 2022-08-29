
### COMMAND LINE FUNCTIONS

def larkNames():
    from .interface import larkNameServer
    larkNameServer()

def larkDaemon():
    from .daemon import startDaemon
    startDaemon()

def larkmagic():
    from .larkcli import main as larkcli_main
    larkcli_main()

def larkcontrol():
    from .control import main as control_main
    control_main()

def larkgui():
    from .display.main import main as lg
    lg()

def larkplot():
    from .display.main import larkplot as lp
    lp()
    
def resetAll():
    from .daemon import resetAll as ra
    ra()

def launcher():
    from .display.modules.main import modeselector
    modeselector()

if __name__ == "__main__":
    larkcontrol()