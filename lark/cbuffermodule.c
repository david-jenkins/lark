#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <pthread.h>
#include <unistd.h>
#include <numpy/arrayobject.h>

#include "cbuffermodule.h"

static PyObject *BufferError;

// python object struct
typedef struct cParamBuf {
    PyObject_HEAD
    paramBuf *pbufs[2];
    char *c_prefix;
    int numa;
    int buffer_open;
} cParamBuf;

static void
cParamBuf_dealloc(cParamBuf *self)
{
    PyObject_GC_UnTrack(self);
    bufferClose(self->pbufs[0]);
    bufferClose(self->pbufs[1]);
    free(self->c_prefix);
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject *
cParamBuf_new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    cParamBuf *self;
    self = (cParamBuf *) type->tp_alloc(type, 0);

    if (self != NULL) {
        self->pbufs[0] = NULL;
        self->pbufs[1] = NULL;
        self->c_prefix = NULL;
        self->numa = -1;
        self->buffer_open = 0;
    }
    return (PyObject *) self;
}

static int
cParamBuf_init(cParamBuf *self, PyObject *args, PyObject *kwargs)
{
    char *tmp_prefix;
    if (!PyArg_ParseTuple(args, "s|i", &tmp_prefix, &self->numa)){
        PyErr_SetString(BufferError,"Error in parsing args of __init__");
        return -1;
    }

    char numastr[6] = {'\0'};
    if (self->numa != -1) {
        snprintf(numastr,6,"Numa%d",self->numa);
    }

    char *name;
    if (!tmp_prefix) {
        PyErr_SetString(BufferError,"prefix is NULL");
        return -1;
    } else {
        free(self->c_prefix);
        self->c_prefix = strdup(tmp_prefix);
        asprintf(&name,"/%srtcParam1%s",self->c_prefix,numastr);
    }

    if ((self->pbufs[0] = bufferOpen(name))==NULL) {
        PyErr_SetString(BufferError,"First buffer not found");
        free(name);
        return -1;
    }
    free(name);
    asprintf(&name,"/%srtcParam2%s",self->c_prefix,numastr);
    if ((self->pbufs[1] = bufferOpen(name))==NULL) {
        PyErr_SetString(BufferError,"Second buffer not found");
        free(name);
        return -1;
    }
    free(name);
    self->buffer_open = 1;
    return 0;
}

static PyObject *
cParamBuf_getprefix(cParamBuf *self, void *closure)
{
    PyObject *tmp = PyUnicode_FromString(self->c_prefix);
    Py_INCREF(tmp);
    return tmp;
}

// static int
// cParamBuf_setprefix(cParamBuf *self, PyObject *value, void *closure)
// {
//     if(!PyUnicode_Check(value)){
//         PyErr_SetString(PyExc_TypeError,"prefix needs to be a string");
//         return -1;
//     }
//     free(self->c_prefix);
//     self->c_prefix = strdup(PyUnicode_AsUTF8(value));
//     printf("set prefix to %s\n",self->c_prefix);
//     return 0;
// }

static int
cParamBuf_cantset(cParamBuf *self, PyObject *value, void *closure)
{
    PyErr_SetString(BufferError,"Cannot set this from Python");
    return -1;
}

static PyObject *
cParamBuf_getactive(cParamBuf *self, void *closure)
{
    if (!self->buffer_open) {
        PyErr_Format(PyExc_RuntimeError,"buffer not open");
        return NULL;
    }
    int value = bufferGetActive(self->pbufs);
    return PyLong_FromLong(value);
}

static PyObject *
cParamBuf_getinactive(cParamBuf *self, void *closure)
{
    if (!self->buffer_open) {
        PyErr_Format(PyExc_RuntimeError,"buffer not open");
        return NULL;
    }
    int value = bufferGetInactive(self->pbufs);
    return PyLong_FromLong(value);
}

static int
cParamBuf_setactive(cParamBuf *self,  PyObject *value, void *closure)
{
    if (!self->buffer_open) {
        PyErr_Format(PyExc_RuntimeError,"buffer not open");
        return -1;
    }
    if (!PyLong_Check(value)) {
        PyErr_SetString(BufferError,"Needs to be integer");
        return -1;
    }
    int val = PyLong_AsLong(value);
    if (val!=0 && val!=1) {
        PyErr_SetString(BufferError,"Incorrect value");
        return -1;
    }
    int active = bufferGetActive(self->pbufs);
    if (val==active) {
        return 0;
    }
    if (switchBuffer(self->pbufs,0)) {
        PyErr_SetString(BufferError,"Error in switchBuffer");
        self->buffer_open = 0;
        return -1;
    }
    return 0;
}

static int
cParamBuf_setinactive(cParamBuf *self,  PyObject *value, void *closure)
{
    if (!self->buffer_open) {
        PyErr_Format(PyExc_RuntimeError,"buffer not open");
        return -1;
    }

    if (!PyLong_Check(value)) {
        PyErr_SetString(BufferError,"Needs to be an integer");
        return -1;
    }
    int val = PyLong_AsLong(value);
    if (val!=0 && val!=1) {
        PyErr_SetString(BufferError,"Incorrect value");
        return -1;
    }
    int inactive = bufferGetInactive(self->pbufs);
    if (val==inactive) {
        return 0;
    }
    if (switchBuffer(self->pbufs,0)) {
        PyErr_SetString(BufferError,"Error in switchBuffer");
        self->buffer_open = 0;
        return -1;
    }
    return 0;
}

static PyGetSetDef cParamBuf_getsetters[] = {
    {"_buf_prefix", (getter) cParamBuf_getprefix, (setter) cParamBuf_cantset,
     "_buf_prefix", NULL},
    {"_active", (getter) cParamBuf_getactive, (setter) cParamBuf_setactive,
     "_active", NULL},
    {"_inactive", (getter) cParamBuf_getinactive, (setter) cParamBuf_setinactive,
     "_inactive", NULL},
    {NULL}  /* Sentinel */
};

static PyObject *
cParamBuf_str(cParamBuf *self)
{
    return PyUnicode_FromFormat("cParamBuf: %s", self->c_prefix);
}

static PyObject *
cParamBuf_get(cParamBuf *self, PyObject *args){

    if (!self->buffer_open) {
        PyErr_Format(PyExc_RuntimeError,"buffer not open");
        return NULL;
    }

    char *name;
    int inactive = 0;
    PyObject *retval;

    if (!PyArg_ParseTuple(args, "s|i", &name, &inactive)){
        PyErr_SetString(PyExc_TypeError,"Expects _get(name:str | inactive=0:int)");
        return NULL;
    }

    int index = bufferGetActive(self->pbufs);
    if (inactive==1) index = 1-index;
    // printf("Getting: %s from pbuf[%d]\n", name, index);
    bufferVal *bval = bufferGetWithShape(self->pbufs[index],name);
    // printf("Got: %s from pbuf[%d]\n", name, index);
    if (bval==NULL) {
        PyErr_Format(PyExc_KeyError,"%s not found",name);
        return NULL;
    }

    retval = makePyFromBufVal(bval);

    free(bval);

    return retval;
}

static PyObject *
cParamBuf_getN(cParamBuf *self, PyObject *args){

    if (!self->buffer_open) {
        PyErr_Format(PyExc_RuntimeError,"buffer not open");
        return NULL;
    }

    PyObject *list;
    int inactive = 0;
    int i,nelem,index;
    PyObject *retval = PyDict_New();
    bufferVal *bval;
    const char *name;
    PyObject *tmp;

    if (!PyArg_ParseTuple(args, "O!|i", &PyList_Type, &list, &inactive)){
        PyErr_SetString(PyExc_TypeError,"Expects _getN(names:list(str) | inactive=0:int)");
        return NULL;
    }

    nelem = PyList_Size(list);

    for(i=0;i<nelem;i++){
        tmp = PyList_GetItem(list,i);
        if(!PyUnicode_Check(tmp)){
            continue;
        }
        name = PyUnicode_AsUTF8(tmp);
        index = bufferGetActive(self->pbufs);
        if (inactive==1) index = 1-index;
        // printf("Getting: %s from pbuf[%d]\n", name, index);
        bval = bufferGetWithShape(self->pbufs[index],name);
        // printf("Got: %s from pbuf[%d]\n", name, index);
        if (bval==NULL) {
            continue;
        }

        PyDict_SetItem(retval,tmp,makePyFromBufVal(bval));

        free(bval);
    }

    return retval;
}

static PyObject *
cParamBuf_set(cParamBuf *self, PyObject *args){

    if (!self->buffer_open) {
        PyErr_Format(PyExc_RuntimeError,"buffer not open");
        return NULL;
    }

    char *name;
    int active = 0;
    PyObject *value = NULL;
    bufferVal *bval;

    if (!PyArg_ParseTuple(args, "sO|i", &name, &value, &active)){
        PyErr_SetString(PyExc_TypeError,"Expects _set(name:str,value:obj | active=0:int)");
        return NULL;
    }

    if (!value) {
        PyErr_SetString(PyExc_ValueError,"value is NULL");
        return NULL;
    }

    bval = makeBufValFromPy(value);

    int index = bufferGetInactive(self->pbufs);
    if (active==1)
        index = 1-index;
    if (bufferSet(self->pbufs[index],name,bval) == 1) {
        PyErr_SetString(BufferError,"Error calling bufferSet");
        return NULL;
    }
    free(bval->data);
    free(bval);
    return PyLong_FromLong((long)index);
}

static PyObject *
cParamBuf_setToBuf(cParamBuf *self, PyObject *args){

    if (!self->buffer_open) {
        PyErr_Format(PyExc_RuntimeError,"buffer not open");
        return NULL;
    }

    char *name;
    int index = 0;
    PyObject *value = NULL;
    bufferVal *bval;

    if (!PyArg_ParseTuple(args, "sOi", &name, &value, &index)){
        PyErr_SetString(PyExc_TypeError,"Expects _set(name:str,value:obj | active=0:int)");
        return NULL;
    }

    if (!value) {
        PyErr_SetString(PyExc_ValueError,"value is NULL");
        return NULL;
    }

    if (index!=0 || index!=1) {
        PyErr_SetString(PyExc_ValueError,"index is not 0 or 1");
        return NULL;
    }

    bval = makeBufValFromPy(value);

    if (bufferSetIgnoringLock(self->pbufs[index],name,bval) == 1) {
        PyErr_SetString(BufferError,"Error calling bufferSet");
        return NULL;
    }

    free(bval->data);
    free(bval);

    return PyLong_FromLong((long)index);
}

static PyObject *
cParamBuf_setN(cParamBuf *self, PyObject *args){

    if (!self->buffer_open) {
        PyErr_Format(PyExc_RuntimeError,"buffer not open");
        return NULL;
    }

    const char *name;
    int active = 0;
    PyObject *values = NULL;
    bufferVal *bval;
    PyObject *failed = PyDict_New();

    if (!PyArg_ParseTuple(args, "O!|i", &PyDict_Type, &values, &active)){
        PyErr_SetString(PyExc_TypeError,"Expects _setN(values:dict | active=0:int)");
        return NULL;
    }

    if (!values) {
        PyErr_SetString(PyExc_ValueError,"value is NULL");
        return NULL;
    }

    PyObject *key, *value;
    Py_ssize_t pos = 0;

    while (PyDict_Next(values, &pos, &key, &value)) {
        if (!PyUnicode_Check(key)){
            continue;
        }
        name = PyUnicode_AsUTF8(key);
        bval = makeBufValFromPy(value);
        int index = bufferGetInactive(self->pbufs);
        if ( active==1 )
            index = 1-index;
        if ( bufferSet(self->pbufs[index],name,bval) == 1 ) {
            // PyErr_SetString(BufferError,"Error calling bufferSet");
            // return NULL;
            printf("failed to set %s in buffer %d\n",name,index);
            PyDict_SetItem(failed,key,value);
        }
        free(bval->data);
        free(bval);
    }

    Py_INCREF(failed);
    return failed;
}

static PyObject *
cParamBuf_setNToBuf(cParamBuf *self, PyObject *args){

    if (!self->buffer_open) {
        PyErr_Format(PyExc_RuntimeError,"buffer not open");
        return NULL;
    }

    const char *name;
    int index = 0;
    PyObject *values = NULL;
    bufferVal *bval;
    PyObject *failed = PyDict_New();

    if (!PyArg_ParseTuple(args, "O!i", &PyDict_Type, &values, &index)){
        PyErr_SetString(PyExc_TypeError,"Expects _setN(values:dict | active=0:int)");
        return NULL;
    }

    if (!values) {
        PyErr_SetString(PyExc_ValueError,"value is NULL");
        return NULL;
    }

    if (index!=0 || index!=1) {
        PyErr_SetString(PyExc_ValueError,"index is not 0 or 1");
        return NULL;
    }

    PyObject *key, *value;
    Py_ssize_t pos = 0;

    while (PyDict_Next(values, &pos, &key, &value)) {
        if (!PyUnicode_Check(key)){
            continue;
        }
        name = PyUnicode_AsUTF8(key);
        bval = makeBufValFromPy(value);
        if ( bufferSetIgnoringLock(self->pbufs[index],name,bval) == 1 ) {
            // PyErr_SetString(BufferError,"Error calling bufferSet");
            // return NULL;
            printf("failed to set %s in buffer %d\n",name,index);
            PyDict_SetItem(failed,key,value);
        }
        free(bval->data);
        free(bval);
    }

    Py_INCREF(failed);
    return failed;
}

static PyObject *
cParamBuf_switch(cParamBuf *self, PyObject *args){

    if (!self->buffer_open) {
        PyErr_Format(PyExc_RuntimeError,"buffer not open");
        return NULL;
    }

    int wait = 0;

    if (!PyArg_ParseTuple(args, "|i", &wait)){
        PyErr_SetString(PyExc_TypeError,"Expects _switch( | wait=0:int)");
        return NULL;
    }

    if ( wait!=0 && wait!=1 ) {
        PyErr_SetString(PyExc_ValueError,"wait is not 0 or 1");
        return NULL;
    }

    if (switchBuffer(self->pbufs,wait)) {
        PyErr_SetString(BufferError,"Error in switchBuffer");
        self->buffer_open = 0;
        return NULL;
    }
    return Py_INCREF(Py_None), Py_None;
}

static PyObject *
cParamBuf_copy_to_inactive(cParamBuf *self, PyObject *args){

    if (!self->buffer_open) {
        PyErr_Format(PyExc_RuntimeError,"buffer not open");
        return NULL;
    }

    if (bufferCopyToInactive(self->pbufs)) {
        PyErr_SetString(BufferError,"Error in bufferCopyToInactive");
        return NULL;
    }
    
    return Py_INCREF(Py_None), Py_None;
}


static PyObject *
cParamBuf_switchonframe(cParamBuf *self, PyObject *args){

    if (!self->buffer_open) {
        PyErr_Format(PyExc_RuntimeError,"buffer not open");
        return NULL;
    }

    /*
    This needs more thought... Where should this be done?
    Maybe a new parameter switchOnFrame=switchFrameNo should be checked by darcmain.c
    When switchRequested is set, darcmain gets switchOnFrame too, then just
    before doing the switch checks if switchFrameNo>currentFrameNo, if so then continues
    without doing the switch until the next frame.
    */
    int fnum;

    if (!PyArg_ParseTuple(args, "i", &fnum)){
        PyErr_SetString(BufferError,"Expects: _switchonframe(frameNo:int)");
        return NULL;
    }

    printf("Switching on frame %d\n",fnum);

    if (switchBuffer(self->pbufs,0)) {
        PyErr_SetString(BufferError,"Error in switchBuffer");
        self->buffer_open = 0;
        return NULL;
    }
    return Py_INCREF(Py_None), Py_None;
}

static PyObject *
cParamBuf_getnames(cParamBuf *self, PyObject *args){

    if (!self->buffer_open) {
        PyErr_Format(PyExc_RuntimeError,"buffer not open");
        return NULL;
    }

    int a,N,i;
    char *buf;
    PyObject *list = PyList_New(0);
    char tmp[17] = {'\0'};

    a = bufferGetActive(self->pbufs);
    N = bufferGetNEntries(self->pbufs[a]);
    buf = self->pbufs[a]->buf;

    for (i=0;i<N;i++) {
        strncpy(tmp, &buf[i*BUFNAMESIZE], BUFNAMESIZE);
        PyList_Append(list, PyUnicode_FromString(tmp));
    }
    Py_INCREF(list);
    return list;
}

static PyMethodDef cParamBuf_methods[] = {
    {"_set", (PyCFunction) cParamBuf_set, METH_VARARGS,
     "Set a value"
    },
    {"_setToBuf", (PyCFunction) cParamBuf_setToBuf, METH_VARARGS,
     "Set a value to buf"
    },
    {"_setN", (PyCFunction) cParamBuf_setN, METH_VARARGS,
     "Set values"
    },
    {"_setNToBuf", (PyCFunction) cParamBuf_setNToBuf, METH_VARARGS,
     "Set values to buf"
    },
    {"_get", (PyCFunction) cParamBuf_get, METH_VARARGS,
     "Get a param"
    },
    {"_getN", (PyCFunction) cParamBuf_getN, METH_VARARGS,
     "Get N params"
    },
    {"switchBuffer", (PyCFunction) cParamBuf_switch, METH_VARARGS,
     "Switch buffer"
    },
    {"copy_to_inactive", (PyCFunction) cParamBuf_copy_to_inactive, METH_NOARGS,
     "Copy active buffer to inactive"
    },
    {"_switchonframe", (PyCFunction) cParamBuf_switchonframe, METH_VARARGS,
     "Switch the parambuf"
    },
    {"_getnames", (PyCFunction) cParamBuf_getnames, METH_NOARGS,
     "Get active buffer names"
    },
    {NULL}  /* Sentinel */
};

static PyTypeObject cParamBufType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "cbuffer.cParamBuf",
    .tp_doc = "cParamBuf object",
    .tp_basicsize = sizeof(cParamBuf),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = cParamBuf_new,
    .tp_init = (initproc) cParamBuf_init,
    .tp_dealloc = (destructor) cParamBuf_dealloc,
    .tp_methods = cParamBuf_methods,
    .tp_getset = cParamBuf_getsetters,
    .tp_str = (reprfunc) cParamBuf_str,
    .tp_repr = (reprfunc) cParamBuf_str,
};

static PyModuleDef cbuffermodule = {
    PyModuleDef_HEAD_INIT,
    .m_name = "cbuffer",
    .m_doc = "Module for directly accessing DARC parameter buffers",
    .m_size = -1,
};

PyMODINIT_FUNC
PyInit_cbuffer(void)
{
    PyObject *m;
    if (PyType_Ready(&cParamBufType) < 0)
        return NULL;

    import_array();
    m = PyModule_Create(&cbuffermodule);
    if (m == NULL)
        return NULL;

    Py_INCREF(&cParamBufType);
    if (PyModule_AddObject(m, "cParamBuf", (PyObject *) &cParamBufType) < 0) {
        Py_DECREF(&cParamBufType);
        Py_DECREF(m);
        return NULL;
    }

    BufferError = PyErr_NewException("cbuffer.BufferError", NULL, NULL);
    Py_INCREF(BufferError);
    PyModule_AddObject(m, "BufferError", BufferError);

    return m;
}

inline int
switchBuffer(paramBuf *pbufs[2], int wait) {
    // printf("Switch buffer...\n");
    bufferVal *bval;
    int val = 1;
    if ((bval = callocbufferVal()) == NULL) {
        printf("Error allocating for bval in set\n");
        return 1;
    }
    bval->dtype = 'i';
    bval->size = 4;
    bval->data = &val;
    int index = bufferGetActive(pbufs);
    char name[] = "switchRequested";
    bufferSetIgnoringLock(pbufs[index],name,bval);
    int err = bufferWait(pbufs[index]);
    if (err==1) {
        printf("Buffer has left the building");
        return 1;
    }
    bufferCopyToInactive(pbufs);
    return 0;
}

inline PyObject *
makePyFromBufVal(bufferVal *bval){

    int i;
    int nd = 0;
    npy_intp ndim[6];
    PyArray_Descr *array_desc;
    // PyObject *retval;
    PyArrayObject *retarr;
    // printf("printing info....\n");
    // printf("got bufferVal dtype=%c, size=%d, ndim=%d, dim=",bval->dtype,bval->size,bval->ndim);
    // for (i=0;i<bval->ndim;i++){
    //     printf("%d,",bval->dim[i]);
    // }
    // printf("\n");

    switch(bval->dtype){
        case 'i':
            if (bval->size/4 == 1 && bval->ndim==0) {
                // printf("got integer: %d\n",*(int *)(bval->data));
                return PyLong_FromLong(*(int *)(bval->data));
            }
            break;
        // case 'l':
        //     if (bval->size/8 == 1) {
        //         // printf("got long: %d\n",*(long *)(bval->data));
        //         return PyLong_FromLong(*(long *)(bval->data));
        //     }
        //     break;
        case 'f':
            if (bval->size/4 == 1 && bval->ndim==0) {
                // printf("got float: %f\n",*(float *)(bval->data));
                return PyFloat_FromDouble((double)(*(float *)(bval->data)));
            }
            break;
        // case 'd':
        //     if (bval->size/8 == 1) {
        //         // printf("got double: %f\n",*(double *)(bval->data));
        //         return PyFloat_FromDouble(*(double *)(bval->data));
        //     }
        //     break;
        case 's':
            if (bval->ndim==0) {
                // printf("got string: %s\n",(char *)(bval->data));
                return PyUnicode_FromString((char *)(bval->data));
            } else {
                // printf("got bytes: %.*s\n",bval->size,(char *)(bval->data));
                return PyBytes_FromStringAndSize((char *)(bval->data), bval->size);
            }
            break;
        case 'n':
            // printf("Got None\n");
            return Py_INCREF(Py_None), Py_None;
        default:
            // printf("Trying to make object from unknown dtype...\n");
            break;
    }

    array_desc = PyArray_DescrFromType(bval->dtype);
    if (bval->ndim==0) {
        ndim[0] = 1;
    } else {
        nd = bval->ndim;
        for (i=0;i<nd;i++){
            ndim[i] = bval->dim[i];
        }
    }

    retarr = (PyArrayObject *)PyArray_NewFromDescr(&PyArray_Type, array_desc, nd, ndim, NULL, NULL, 0, NULL);
    memcpy(PyArray_DATA(retarr),bval->data,bval->size);

    Py_INCREF(retarr);
    return PyArray_Return(retarr);
}

inline bufferVal *
makeBufValFromPy(PyObject *value)
{
    int i,ival;
    // double dval;
    float fval;
    char *sval;
    const char *c_sval;
    PyArrayObject *aval;
    bufferVal *bval;

    if ((bval = callocbufferVal()) == NULL) {
        PyErr_SetString(BufferError,"Error allocating for bval in makeBufValFromPy");
        return NULL;
    }

    if (PyLong_Check(value)) {
        ival = (int)PyLong_AsLong(value);
        bval->data = malloc(sizeof(int));
        printf("Got int: %d\n",ival);
        bval->size = 4;
        bval->dtype = 'i';
        memcpy(bval->data,&ival,sizeof(int));
        bval->ndim = 0;
    } else
    if (PyFloat_Check(value)) {
        fval = (float)PyFloat_AsDouble(value);
        bval->data = malloc(sizeof(float));
        printf("Got float: %f\n",fval);
        bval->size = 4;
        bval->dtype = 'f';
        memcpy(bval->data,&fval,sizeof(float));
        bval->ndim = 0;
    } else
    // Python float gets used as double
    // if (PyFloat_Check(value)) {
    //     dval = PyFloat_AsDouble(value);
    //     // printf("Got double: %f\n",dval);
    //     bval->size = 8;
    //     bval->dtype = 'd';
    //     bval->data = &dval;
    //     bval->ndim = 0;
    // } else
    if (PyUnicode_Check(value)) {
        Py_ssize_t s_size;
        c_sval = PyUnicode_AsUTF8AndSize(value, &s_size);
        printf("Got string: %s of size %d\n",c_sval,(int)s_size);
        bval->size = s_size+1; // need size+1 to make sure the terminator gets copied too
        bval->dtype = 's';
        asprintf((char **)&bval->data, c_sval);
        bval->ndim = 0;
    } else
    if (PyBytes_Check(value)) {
        Py_ssize_t s_size;
        PyBytes_AsStringAndSize(value, &sval, &s_size);
        printf("Got bytes: %s of size %d\n",sval,(int)s_size);
        bval->size = s_size;
        bval->dtype = 's';
        asprintf((char **)&bval->data, sval);
        bval->ndim = 1;
        bval->dim[0] = s_size;
    } else
    if (PyArray_Check(value)) {
        aval = (PyArrayObject *)value;
        printf("Got array object\n");
        // gainReconmxT wasn't coming in with contiguous memory.
        // because while astype does make a copy of the array, by
        // default it keeps the memory ordering the same which is stupid.
        // this is technically no longer needed but is safer incase non-
        // contiguous memory is passed in
        if (!PyArray_ISCARRAY(aval)) {
            printf("WARNING: Not CARRAY, COPYING\n");
            aval = (PyArrayObject *)PyArray_NewCopy(aval, NPY_CORDER);
        }
        // printf("size = %d\n",PyArray_NBYTES(aval));
        // printf("ndim = %d\n",PyArray_NDIM(aval));
        // printf("dtype = %c\n",PyArray_DTYPE(aval)->kind);
        // printf("dtype = %c\n",PyArray_DTYPE(aval)->type);
        bval->ndim = PyArray_NDIM(aval);
        for (i=0;i<aval->nd;i++) {
            bval->dim[i] = PyArray_DIMS(aval)[i];
        }
        bval->size = PyArray_NBYTES(aval);
        bval->data = malloc(bval->size);
        bval->dtype = PyArray_DTYPE(aval)->type;
        memcpy(bval->data,PyArray_DATA(aval),bval->size);
    } else
    if (PyArray_CheckScalar(value)) {
        printf("Got numpy scalar\n");
        aval = (PyArrayObject *)PyArray_FromScalar(value, NULL);
        bval->ndim = 0;
        bval->size = PyArray_NBYTES(aval);
        bval->data = malloc(bval->size);
        bval->dtype = PyArray_DTYPE(aval)->type;
        memcpy(bval->data,PyArray_DATA(aval),bval->size);
    } else
    if (value == Py_None) {
        bval->size = 0;
        bval->dtype = 'n';
        bval->data = NULL;
        bval->ndim = 0;
    }

    return bval;
}

int bufferWait(paramBuf *pbuf)
{
  int i = 0, err, rt = 0;
  struct timespec abstime;
//   struct timeval t1;
  pthread_mutex_lock(pbuf->condmutex);
  while ((BUFFLAG(pbuf) & 1) == 1 && i < 10)
  { //currently frozen - wait for unblock.
    // printf("currently frozen - wait for unblock.\n");
    // gettimeofday(&t1, NULL);
    clock_gettime(CLOCK_REALTIME,&abstime);
    abstime.tv_nsec += 500000000;//add 0.05 second.
    if (abstime.tv_nsec > 999999999) {
        abstime.tv_sec += 1;
        abstime.tv_nsec -= 1000000000;
    }
    err = pthread_cond_timedwait(pbuf->cond, pbuf->condmutex, &abstime);
    if (err == ETIMEDOUT)
    {
      printf("Timeout waiting for buffer switch to complete (%d/50)\n", i);
    }
    else if (err != 0)
    {
      printf("pthread_cond_timedwait failed in cbuffermodule.c\n");
    }
    i++;
    if (i == 10)
    {
      printf("Error waiting for buffer to be unlocked\n");
      rt = 1;
    }
  }
  pthread_mutex_unlock(pbuf->condmutex);
  return rt;
}
