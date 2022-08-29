#include "buffer.h"

typedef struct CParamBuff CParamBuff;

inline PyObject *
makePyFromBufVal(bufferVal *bval);

inline bufferVal *
makeBufValFromPy(PyObject *value);

inline int
switchBuffer(paramBuf *pbufs[2], int wait);

int
bufferWait(paramBuf *pbuf);