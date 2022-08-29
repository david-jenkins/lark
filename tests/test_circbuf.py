
from lark.circbuf import CircReader, TelemetrySystem

PREFIX = "canapy"
STREAM = "rtcCentBuf"

def test_CircReader():
    c = CircReader(PREFIX,STREAM)

def test_TelemetrySystem():
    t = TelemetrySystem(PREFIX)

if __name__ == "__main__":

    test_CircReader()
    test_TelemetrySystem()
