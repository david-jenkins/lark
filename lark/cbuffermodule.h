#include "buffer.h"

typedef struct CParamBuff CParamBuff;

PyObject *
makePyFromBufVal(bufferVal *bval);

bufferVal *
makeBufValFromPy(PyObject *value);

int
switchBuffer(paramBuf *pbufs[2], int wait);

int
bufferWait(paramBuf *pbuf);