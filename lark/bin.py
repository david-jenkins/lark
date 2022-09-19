
### COMMAND LINE FUNCTIONS

# larkNames and larkDaemon shouldn't need to be used, they should be used by the services.
# but if you don't use the services these should be started in their own terminal/screen
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
    from .display.main import main
    main()

def larkplot():
    from .display.main import larkplot as lp
    lp()
    
def resetAll():
    from .daemon import resetAll as ra
    ra()

def launcher():
    from .display.modes import modeselector
    modeselector()

if __name__ == "__main__":
    larkcontrol()