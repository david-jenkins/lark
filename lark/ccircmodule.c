#define PY_SSIZE_T_CLEAN
#include <Python.h>
/* All other includes and definitions are put here */
#include "ccircmodule.h"

/*

The CircSync Class, used to create a shared pthreads barrier to pass to other classes.

*/

static int
CircSync_traverse(CircSync *self, visitproc visit, void *arg)
{
    // Py_VISIT(self->first);
    // Py_VISIT(self->last);
    return 0;
}

static int
CircSync_clear(CircSync *self)
{
    // Py_CLEAR(self->first);
    // Py_CLEAR(self->last);
    return 0;
}

static void
CircSync_dealloc(CircSync *self)
{
    PyObject_GC_UnTrack(self);
    if (self->barrier) {
        pthread_barrier_destroy(self->barrier);
        free(self->barrier);
    }
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject *
CircSync_new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    CircSync *self;
    self = (CircSync *) type->tp_alloc(type, 0);

    if (self != NULL) {
        self->nthreads = 0;
        self->barrier = NULL;
    }
    return (PyObject *) self;
}

static int
CircSync_init(CircSync *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"nthreads", NULL};
    int nthreads;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "i", kwlist, &nthreads))
    {
        PyErr_SetString(PyExc_TypeError,"Wrong args");
        return -1;
    }

    if (nthreads<=1){
        PyErr_SetString(PyExc_ValueError,"Nthreads must be > 1");
        return -1;
    }

    self->barrier = malloc(sizeof(pthread_barrier_t));
    self->nthreads = nthreads;

    pthread_barrierattr_t attr;
    pthread_barrierattr_init(&attr);
    pthread_barrierattr_setpshared(&attr, PTHREAD_PROCESS_SHARED);

    pthread_barrier_init(self->barrier,&attr,nthreads);
    pthread_barrierattr_destroy(&attr);
    return 0;
}

static PyObject *
CircSync_str(CircSync *self)
{
    return PyUnicode_FromFormat("CircSync: %i", self->nthreads);
}

static PyTypeObject CircSyncType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "ccirc.cCircSync",
    .tp_doc = "cCircSync objects",
    .tp_basicsize = sizeof(CircSync),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = CircSync_new,
    .tp_init = (initproc) CircSync_init,
    .tp_dealloc = (destructor) CircSync_dealloc,
    .tp_str = (reprfunc) CircSync_str,
    .tp_repr = (reprfunc) CircSync_str,
    .tp_traverse = (traverseproc) CircSync_traverse,
    .tp_clear = (inquiry) CircSync_clear,
};

/*

The ZMQContext Class, used to share a single ZMQ context among other classes.

*/

static int
ZMQContext_traverse(ZMQContext *self, visitproc visit, void *arg)
{
    // Py_VISIT(self->first);
    // Py_VISIT(self->last);
    return 0;
}

static int
ZMQContext_clear(ZMQContext *self)
{
    // Py_CLEAR(self->first);
    // Py_CLEAR(self->last);
    return 0;
}

static void
ZMQContext_dealloc(ZMQContext *self)
{
    PyObject_GC_UnTrack(self);
    if (self->context) {
        zmq_ctx_destroy (self->context);
    }
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject *
ZMQContext_new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    ZMQContext *self;
    self = (ZMQContext *) type->tp_alloc(type, 0);

    if (self != NULL) {
        self->context = NULL;
    }
    return (PyObject *) self;
}

static int
ZMQContext_init(ZMQContext *self, PyObject *args, PyObject *kwargs)
{
    self->context = zmq_ctx_new ();
    return 0;
}

static PyObject *
ZMQContext_str(ZMQContext *self)
{
    return PyUnicode_FromFormat("ZMQContext");
}

static PyTypeObject ZMQContextType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "ccirc.cZMQContext",
    .tp_doc = "cZMQContext objects",
    .tp_basicsize = sizeof(ZMQContext),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = ZMQContext_new,
    .tp_init = (initproc) ZMQContext_init,
    .tp_dealloc = (destructor) ZMQContext_dealloc,
    .tp_str = (reprfunc) ZMQContext_str,
    .tp_repr = (reprfunc) ZMQContext_str,
    .tp_traverse = (traverseproc) ZMQContext_traverse,
    .tp_clear = (inquiry) ZMQContext_clear,
};


/*

Common values, structs and functions for CircSubscriber and CircReader

*/

inline int free_threadstruct(thread_struct *tstr, int free_data){
    int rt = 0;
    if (free_data) {
        free(tstr->dataHeader);
        free(tstr->dataHandle);
    }
    if (tstr->shmStruct) {
        circCloseBufReader(tstr->shmStruct->cb);
        free(tstr->shmStruct->fullname);
        free(tstr->shmStruct);
    }
    if (tstr->data_mutex)
        rt = pthread_mutex_destroy(tstr->data_mutex);
    free(tstr->data_mutex);
    if (tstr->data_cond)
        rt = pthread_cond_destroy(tstr->data_cond);
    free(tstr->data_cond);
    if (tstr->cb_mutex)
        rt = pthread_mutex_destroy(tstr->cb_mutex);
    free(tstr->cb_mutex);
    if (tstr->cb_cond)
        rt = pthread_cond_destroy(tstr->cb_cond);
    free(tstr->cb_cond);
    if (tstr->file_mutex)
        rt = pthread_mutex_destroy(tstr->file_mutex);
    free(tstr->file_mutex);
    if (tstr->file_cond)
        rt = pthread_cond_destroy(tstr->file_cond);
    free(tstr->file_cond);

    free(tstr->zmqStruct->host);
    free(tstr->zmqStruct->multicast);
    free(tstr->zmqStruct);
    free(tstr);
    return rt;
}

thread_struct *threadstruct_new(int shm_option) {
    thread_struct *tstr = calloc(1,sizeof(thread_struct));

    if (!tstr)
        return NULL;

    *tstr = (thread_struct){ 0 };

    if (shm_option) {
        tstr->shmStruct = calloc(1,sizeof(shm_struct));
        if (!tstr->shmStruct) {
            free(tstr);
            return NULL;
        }
        *tstr->shmStruct = (shm_struct){ 0 };
    }

    tstr->fileStruct[0] = (file_struct){ 0 };
    tstr->fileStruct[1] = (file_struct){ 0 };

    tstr->zmqStruct = calloc(1,sizeof(zmq_struct));
    if (!tstr->zmqStruct) {
        free(tstr->shmStruct);
        free(tstr);
        return NULL;
    }
    *tstr->zmqStruct = (zmq_struct){ 0 };

    return tstr;
}

int threadstruct_init(thread_struct *tstr) {

    if (!tstr->zmqStruct->host) {
        tstr->zmqStruct->host = strdup("127.0.0.1");
    }
    printf("default host set to %s\n",tstr->zmqStruct->host);
    // else {

    // }

    tstr->zmqStruct->t_len = snprintf(tstr->zmqStruct->topic, TOPIC_LEN, "%s", tstr->streamname);
    snprintf(&tstr->zmqStruct->topic[tstr->zmqStruct->t_len], TOPIC_LEN - tstr->zmqStruct->t_len, "0000000000000");
    tstr->zmqStruct->transport = tr_tcp;

    tstr->zmqStruct->multicast = strdup("239.0.0.1");
    tstr->zmqStruct->port = 18547;
    tstr->decimation = 1;

    tstr->data_mutex = malloc(sizeof(pthread_mutex_t));
    tstr->data_cond = malloc(sizeof(pthread_cond_t));
    pthread_mutex_init(tstr->data_mutex,NULL);
    pthread_cond_init(tstr->data_cond,NULL);

    tstr->cb_mutex = malloc(sizeof(pthread_mutex_t));
    tstr->cb_cond = malloc(sizeof(pthread_cond_t));
    pthread_mutex_init(tstr->cb_mutex,NULL);
    pthread_cond_init(tstr->cb_cond,NULL);

    tstr->file_mutex = malloc(sizeof(pthread_mutex_t));
    tstr->file_cond = malloc(sizeof(pthread_cond_t));
    pthread_mutex_init(tstr->file_mutex,NULL);
    pthread_cond_init(tstr->file_cond,NULL);

    return 0;
}

static int
CircStruct_traverse(CircStruct *self, visitproc visit, void *arg)
{
    // Py_VISIT(self->first);
    // Py_VISIT(self->last);
    return 0;
}

static int
CircStruct_clear(CircStruct *self)
{
    // Py_CLEAR(self->first);
    // Py_CLEAR(self->last);
    return 0;
}

static PyObject *
CircStruct_stop_thread(CircStruct *self){

    self->threadStruct->thread_go = 0;
    self->threadStruct->publish_go = 0;
    self->threadStruct->callback_go = 0;
    self->threadStruct->data_go = 0;
    self->threadStruct->file_go = 0;

    debug_print("Stopping thread...\n");

    if (self->threadRunning) {
        pthread_join(self->threadStruct->tid,NULL);
    }

    disconnect_zmq(self);
    self->threadRunning = 0;
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
CircStruct_getprefix(CircStruct *self, void *closure)
{
    return PyUnicode_FromString(self->threadStruct->prefix);
}

static PyObject *
CircStruct_getstreamName(CircStruct *self, void *closure)
{
    return PyUnicode_FromString(self->threadStruct->streamname);
}

static PyObject *
CircStruct_gethost(CircStruct *self, void *closure)
{
    printf("retrieving host %s\n",self->threadStruct->zmqStruct->host);
    return PyUnicode_FromString(self->threadStruct->zmqStruct->host);
}

static PyObject *
CircStruct_getmulticast(CircStruct *self, void *closure)
{
    return PyUnicode_FromString(self->threadStruct->zmqStruct->multicast);
}

static PyObject *
CircStruct_getport(CircStruct *self, void *closure)
{
    return PyLong_FromLong(self->threadStruct->zmqStruct->port);
}

static PyObject *
CircStruct_gettransport(CircStruct *self, void *closure)
{
    return PyLong_FromLong(self->threadStruct->zmqStruct->transport);
}


static PyObject *
CircStruct_getthreadRunning(CircStruct *self, void *closure)
{
    return PyLong_FromLong(self->threadRunning);
}

static PyObject *
CircStruct_getstatus(CircStruct *self, void *closure)
{
    PyObject *tuple = PyTuple_New(5);

    PyTuple_SetItem(tuple,0,PyLong_FromLong(self->threadStruct->thread_go));
    PyTuple_SetItem(tuple,1,PyLong_FromLong(self->threadStruct->publish_go));
    PyTuple_SetItem(tuple,2,PyLong_FromLong(self->threadStruct->callback_go));
    PyTuple_SetItem(tuple,3,PyLong_FromLong(self->threadStruct->data_go));
    PyTuple_SetItem(tuple,4,PyLong_FromLong(self->threadStruct->file_go));

    Py_INCREF(tuple);
    return tuple;
}

static PyObject *
CircStruct_getndim(CircStruct *self, void *closure)
{
    return PyLong_FromLong(self->nd);
}

static PyObject *
CircStruct_getdtype(CircStruct *self, void *closure)
{
    if (self->threadStruct->dataHeader) {
        char *cheader = (char*)self->threadStruct->dataHeader;
        return PyLong_FromLong((int)(cheader[16]));
    } else {
        return Py_INCREF(Py_None), Py_None;
    }
}

static PyObject *
CircStruct_getsize(CircStruct *self, void *closure)
{
    if (self->threadStruct->dataHeader) {
        return PyLong_FromLong(self->threadStruct->dataHeader[5]);
    } else {
        return Py_INCREF(Py_None), Py_None;
    }
    
}

static int
CircStruct_cantset(CircStruct *self, PyObject *value, void *closure)
{
    PyErr_SetString(PyExc_TypeError, "Cannot set this from Python");
    return -1;
}

static PyObject *
CircStruct_getdecimation(CircStruct *self, void *closure)
{
    return PyLong_FromLong(self->threadStruct->decimation);
    // return PyLong_FromLong(FREQ(self->threadStruct->shmStruct->cb));
}

static int
CircStruct_sethost(CircStruct *self, PyObject *value, void *closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "Cannot delete the host attribute");
        return -1;
    }
    if (!PyUnicode_Check(value)) {
        PyErr_SetString(PyExc_TypeError,
                        "The host attribute value must be a string");
        return -1;
    }
    const char *host = PyUnicode_AsUTF8(value);
    free(self->threadStruct->zmqStruct->host);
    self->threadStruct->zmqStruct->host = strdup(host);
    printf("set host to %s\n",self->threadStruct->zmqStruct->host);
    return 0;
}

static int
CircStruct_setmulticast(CircStruct *self, PyObject *value, void *closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "Cannot delete the multicast attribute");
        return -1;
    }
    if (!PyUnicode_Check(value)) {
        PyErr_SetString(PyExc_TypeError,
                        "The multicast attribute value must be a string");
        return -1;
    }
    const char *multicast = PyUnicode_AsUTF8(value);
    free(self->threadStruct->zmqStruct->multicast);
    self->threadStruct->zmqStruct->multicast = strdup(multicast);
    return 0;
}

static int
CircStruct_setport(CircStruct *self, PyObject *value, void *closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "Cannot delete the port attribute");
        return -1;
    }
    if (!PyLong_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "The port attribute value must be an integer");
        return -1;
    }
    int port = PyLong_AsLong(value);
    if (port<1024) {
        PyErr_SetString(PyExc_ValueError, "The port attribute value must be greater than 1024");
        return -1;
    }
    self->threadStruct->zmqStruct->port = port;
    return 0;
}

static PyObject *
CircStruct_getshape(CircStruct *self, void *closure)
{
    PyObject *list = PyList_New(0);
    int i;
    for (i=0;i<self->nd;i++) {
        PyList_Append(list, PyLong_FromLong((int)self->ndim[i]));
    }
    Py_INCREF(list);
    return list;
}

static PyObject *
CircStruct_getcbdata(CircStruct *self, void *closure)
{
    if (self->threadStruct->cb_data && self->threadStruct->cb_ftim && self->threadStruct->cb_fnum){
        PyObject *retval = Py_BuildValue("(OOO)",self->threadStruct->cb_data, self->threadStruct->cb_ftim, self->threadStruct->cb_fnum);
        return retval;
    } else {
        return Py_INCREF(Py_None), Py_None;
    }
}

static PyObject *
CircStruct_getlatest(CircStruct *self, void *closure)
{

    if (!self->threadRunning) {
        PyErr_SetString(PyExc_RuntimeError, "Thread is not running, start with start_subscriber");
        return NULL;
    }
    Py_BEGIN_ALLOW_THREADS
    int cb_go = self->threadStruct->callback_go;
    self->threadStruct->callback_go = 1;
    pthread_mutex_lock(self->threadStruct->cb_mutex);
    while(self->threadStruct->cb_flag==0) {
        pthread_cond_wait(self->threadStruct->cb_cond,self->threadStruct->cb_mutex);
    }
    self->threadStruct->cb_flag=0;
    pthread_mutex_unlock(self->threadStruct->cb_mutex);

    self->threadStruct->callback_go = cb_go;
    Py_END_ALLOW_THREADS

    PyObject *retval = Py_BuildValue("(OOO)",self->threadStruct->cb_data, self->threadStruct->cb_ftim, self->threadStruct->cb_fnum);
    return retval;
}

static int
CircStruct_setshape(CircStruct *self, PyObject *value, void *closure)
{
    if (!self->threadStruct->dataHeader) {
        PyErr_SetString(PyExc_RuntimeError,"Data Header not yet ready");
        return -1;
    }
    
    if (value) {
        if (!PyList_Check(value)) {
            if (!PyTuple_Check(value)) {
                PyErr_SetString(PyExc_TypeError,"Needs a list or tuple");
                return -1;
            }
        }
    }

    PyObject *iterator = PyObject_GetIter(value);
    PyObject *item;
    int i,nd = 0;
    int ndim[6] = {0};

    while ((item = PyIter_Next(iterator))) {
        if (!PyLong_Check(item)) {
            PyErr_SetString(PyExc_TypeError,"Needs integers");
            Py_DECREF(item);
            return -1;
        }
        ndim[nd] = PyLong_AsLong(item);
        nd++;
        if (nd>5) {
            PyErr_SetString(PyExc_ValueError,"Max 6 dims supported");
            Py_DECREF(item);
            return -1;
        }
        Py_DECREF(item);
    }

    int elems = 1;

    for(i=0;i<nd;i++) {
        elems*=ndim[i];
    }

    if (elems != self->threadStruct->dataHeader[5]) {
        char str[128];
        int index = 0;
        index += sprintf(&str[index], "Cannot reshape array from %d to (%d",self->threadStruct->dataHeader[5],ndim[0]);
        for (i=1; i<nd; i++)
            index += sprintf(&str[index], ",%d", ndim[i]);
        sprintf(&str[index], ")");
        PyErr_SetString(PyExc_ValueError, str);
        return -1;
    }

    self->nd = nd;
    for (i=0;i<self->nd;i++) {
        self->ndim[i] = ndim[i];
    }

    reshape_cb(self);

    return 0;
}

static PyObject *
CircStruct_name(CircStruct *self, PyObject *Py_UNUSED(ignored))
{
    return PyUnicode_FromFormat("%s: %s", self->threadStruct->prefix, self->threadStruct->streamname);
}

static PyObject *
CircStruct_address(CircStruct *self, PyObject *Py_UNUSED(ignored))
{
    char address[64];
    if (self->threadStruct->zmqStruct->transport == tr_ipc){
        snprintf(&address[0],64,"ipc:///dev/shm/zmq_%s%s",self->threadStruct->streamname,self->threadStruct->prefix);
    } else
    if (self->threadStruct->zmqStruct->transport == tr_epgm) {
        snprintf(&address[0],64,"epgm://%s;%s:%d",self->threadStruct->zmqStruct->host,self->threadStruct->zmqStruct->multicast,self->threadStruct->zmqStruct->port);
    } else {
        sprintf(&address[0],"tcp://%s:%d",self->threadStruct->zmqStruct->host,self->threadStruct->zmqStruct->port);
    }
    return PyUnicode_FromFormat("%s", address);
}

static PyObject *
CircStruct_use_tcp(CircStruct *self, PyObject *args){

    debug_print("Got transport = tcp\n");
    self->threadStruct->zmqStruct->transport = tr_tcp;

    return Py_INCREF(Py_None), Py_None;
}

static PyObject *
CircStruct_use_ipc(CircStruct *self, PyObject *args){

    debug_print("Got transport = ipc\n");
    self->threadStruct->zmqStruct->transport = tr_ipc;

    return Py_INCREF(Py_None), Py_None;
}

static PyObject *
CircStruct_use_epgm(CircStruct *self, PyObject *args){

    debug_print("Got transport = epgm\n");
    self->threadStruct->zmqStruct->transport = tr_epgm;

    return Py_INCREF(Py_None), Py_None;
}

static PyObject *
CircStruct_set_callback(CircStruct *self, PyObject *args){

    CircSync *value = NULL;

    if (!PyArg_ParseTuple(args, "|O!", &CircSyncType, &value)){
        PyErr_SetString(PyExc_TypeError, "Wrong Args");
        return NULL;
    }

    Py_BEGIN_ALLOW_THREADS
    if (value) {
        pthread_barrier_wait(value->barrier);
    }
    self->threadStruct->callback_go = 1;
    Py_END_ALLOW_THREADS

    PyObject *retval = Py_BuildValue("(OOO)",self->threadStruct->cb_data, self->threadStruct->cb_ftim, self->threadStruct->cb_fnum);

    return retval;
}

static PyObject *
CircStruct_wait_for_cb(CircStruct *self, PyObject *args){

    if (self->threadStruct->thread_go!=1) {
        PyErr_SetString(PyExc_RuntimeError, "Thread not running");
        return NULL;
    }

    struct timespec waitfor;
    int rv = 0;

    Py_BEGIN_ALLOW_THREADS
    clock_gettime(CLOCK_REALTIME,&waitfor);
    waitfor.tv_sec += 2;
    pthread_mutex_lock(self->threadStruct->cb_mutex);
    while(self->threadStruct->cb_flag==0) {
        if(pthread_cond_timedwait(self->threadStruct->cb_cond,self->threadStruct->cb_mutex,&waitfor)){
            rv = 1;
            break;
        }
    }
    self->threadStruct->cb_flag=0;
    pthread_mutex_unlock(self->threadStruct->cb_mutex);
    Py_END_ALLOW_THREADS

    if (rv) {
        PyErr_SetString(PyExc_TimeoutError,"Nothing received");
        return NULL;
    }
    
    if (self->threadStruct->sizechanged) {
        PyErr_SetString(PyExc_MemoryError,"Telemetry buffer size changed");
        return NULL;
    }

    return Py_INCREF(Py_None), Py_None;
}

static PyObject *
CircStruct_stop_callback(CircStruct *self, PyObject *args){

    self->threadStruct->callback_go = 0;

    return Py_INCREF(Py_None), Py_None;
}

static PyObject *
CircStruct_prepare_data(CircStruct *self, PyObject *args){

    int i;
    int nframe;
    char *cheader = (char*)self->threadStruct->dataHeader;
    PyArray_Descr *array_desc;

    if (!PyArg_ParseTuple(args, "i", &nframe)){
        PyErr_SetString(PyExc_TypeError, "Wrong Args");
        return NULL;
    }

    npy_intp ndim[6] = {0};
    ndim[0] = nframe;
    for (i=0;i<self->nd;i++) {
        ndim[i+1] = self->ndim[i];
    }

    array_desc = PyArray_DescrFromType(cheader[16]);
    self->threadStruct->data_array = (PyArrayObject *)PyArray_Zeros(self->nd+1, ndim, array_desc, 0);

    array_desc = PyArray_DescrFromType(NPY_DOUBLE);
    self->threadStruct->ftim_array = (PyArrayObject *)PyArray_Zeros(1, ndim, array_desc, 0);

    array_desc = PyArray_DescrFromType(NPY_UINT32);
    self->threadStruct->fnum_array = (PyArrayObject *)PyArray_Zeros(1, ndim, array_desc, 0);

    self->threadStruct->data_index = 0;

    PyObject *retval = Py_BuildValue("(iOOO)",self->threadStruct->dataHeader[1], self->threadStruct->data_array, self->threadStruct->ftim_array, self->threadStruct->fnum_array);

    return retval;
}

static PyObject *
CircStruct_get_data(CircStruct *self, PyObject *args){

    if (self->threadStruct->thread_go!=1) {
        PyErr_SetString(PyExc_RuntimeError, "Thread not running");
        return NULL;
    }

    CircSync *value = NULL;

    if (!PyArg_ParseTuple(args, "|O!", &CircSyncType, &value)){
        PyErr_SetString(PyExc_TypeError, "Wrong Args");
        return NULL;
    }

    Py_BEGIN_ALLOW_THREADS
    if (value) {
        pthread_barrier_wait(value->barrier);
    }
    self->threadStruct->data_go = (int)(PyArray_SHAPE(self->threadStruct->data_array)[0]);
    pthread_mutex_lock(self->threadStruct->data_mutex);
    while(self->threadStruct->data_go!=0) {
       pthread_cond_wait(self->threadStruct->data_cond,self->threadStruct->data_mutex);
    }
    pthread_mutex_unlock(self->threadStruct->data_mutex);
    Py_END_ALLOW_THREADS

    return Py_INCREF(Py_None), Py_None;
}

static PyObject *
CircStruct_prepare_save(CircStruct *self, PyObject *args){

    debug_print("Running prepare_save..\n");
    int i;

    int file_desc;
    long data_off;
    long ftim_off;
    long fnum_off;
    int file_elem;
    struct stat fprops;
    file_struct *fsA;
    file_struct *fsB;

    if (!PyArg_ParseTuple(args, "illli", &file_desc, &data_off, &ftim_off, &fnum_off, &file_elem)){
        PyErr_SetString(PyExc_TypeError, "Wrong Args");
        return NULL;
    }
    
    // printf("ccirc prepare_save got (%d,%d,%d,%d,%d)\n",file_desc,data_off,ftim_off,fnum_off,file_elem);

    for (i=0;i<10;i++) {
        fsB = &(self->threadStruct->fileStruct[1-self->threadStruct->file_index]);
        if (fsB->file_elem == 0) {
            break;
        } else {
            printf("Error file already queued for saving, retrying....\n");
            struct timespec ts;
            ts.tv_sec = 0;
            ts.tv_nsec = 7500000;
            nanosleep(&ts,NULL);
        }
    }
    
    if (i>=9) {
        printf("fsB->file_elem = %d\n",fsB->file_elem);
        PyErr_SetString(PyExc_RuntimeError, "Error file already queued for saving");
        return NULL;
    }
    
    fstat(file_desc,&fprops);
    fsB->ptr = mmap(NULL, fprops.st_size, PROT_READ | PROT_WRITE, MAP_SHARED, file_desc, 0);

    if(fsB->ptr == MAP_FAILED){
        PyErr_SetString(PyExc_RuntimeError, "mmap Mapping Failed");
        return NULL;
    }

    fsB->mmap_size = fprops.st_size;
    fsB->file_data = &fsB->ptr[data_off];
    fsB->file_ftim = (double *)(&fsB->ptr[ftim_off]);
    fsB->file_fnum = (unsigned int *)(&fsB->ptr[fnum_off]);
    fsB->file_elem = file_elem;
    fsB->file_count = 0;

    // printf("got (%d,%d,%d,%d,%d)\n",file_desc,data_off,ftim_off,fnum_off,file_elem);

    fsA = &(self->threadStruct->fileStruct[self->threadStruct->file_index]);

    if (fsA->file_elem == 0 ) {
        self->threadStruct->file_index = 1-self->threadStruct->file_index;
        return PyLong_FromLong(self->threadStruct->file_index);
    }

    return PyLong_FromLong(1-self->threadStruct->file_index);
}

static PyObject *
CircStruct_cancel_save(CircStruct *self, PyObject *args){
    
    int i;
    self->threadStruct->file_go = 0;
    thread_struct *tstr = self->threadStruct;
    
    file_struct fs;
    
    for (i=0;i<2;i++) {
    
        fs = self->threadStruct->fileStruct[i];

        if (fs.ptr) {
            pthread_cond_signal(tstr->file_cond);
            int err = munmap(fs.ptr, fs.mmap_size);
            fs.ptr = NULL;
            if(err != 0){
                printf("UnMapping Failed\n");
            }
        }
        fs = (file_struct){ 0 };
    }
    return Py_INCREF(Py_None), Py_None;
}
    

static PyObject *
CircStruct_start_save(CircStruct *self, PyObject *args){

    CircSync *value = NULL;

    if (!PyArg_ParseTuple(args, "|O!", &CircSyncType, &value)){
        PyErr_SetString(PyExc_TypeError, "Wrong Args");
        return NULL;
    }

    Py_BEGIN_ALLOW_THREADS
    if (value) {
        pthread_barrier_wait(value->barrier);
    }
    self->threadStruct->file_go = 1;
    Py_END_ALLOW_THREADS

    return Py_INCREF(Py_None), Py_None;
}

static PyObject *
CircStruct_wait_for_save(CircStruct *self, PyObject *args){

    if (self->threadStruct->thread_go!=1) {
        PyErr_SetString(PyExc_RuntimeError, "Thread not running");
        return NULL;
    }

    int file_index;

    if (!PyArg_ParseTuple(args, "i", &file_index)){
        PyErr_SetString(PyExc_TypeError,"Wrong Args");
        return NULL;
    }

    Py_BEGIN_ALLOW_THREADS
    pthread_mutex_lock(self->threadStruct->file_mutex);
    while(self->threadStruct->fileStruct[file_index].file_elem > 0) {
        pthread_cond_wait(self->threadStruct->file_cond,self->threadStruct->file_mutex);
    }
    pthread_mutex_unlock(self->threadStruct->file_mutex);
    Py_END_ALLOW_THREADS
    return Py_INCREF(Py_None), Py_None;
}

/*

The CircSubscriber Class, used to subscribe to ZMQ SUB streams from the CircReader Class.

*/

static void
CircSubscriber_dealloc(CircSubscriber *self)
{
    PyObject_GC_UnTrack(self);
    if (self->threadRunning) {
        CircStruct_stop_thread(self);
    }
    debug_print("Subscriber thread stopped...\n");
    free_threadstruct(self->threadStruct, FREE_DATA);
    // printf("Finishing dealloc...\n");
    Py_TYPE(self)->tp_free((PyObject *) self);
    // printf("Finished dealloc...\n");
}

static PyObject *
CircSubscriber_new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    int i;
    CircSubscriber *self;
    self = (CircSubscriber *) type->tp_alloc(type, 0);

    if (self != NULL) {
        self->threadRunning = 0;
        self->nd = 1;
        for (i=0;i<6;i++) {
            self->ndim[i] = 0;
        }
        self->threadStruct = threadstruct_new(WITHOUT_SHMSTRUCT);
    }
    return (PyObject *) self;
}

static int
CircSubscriber_init(CircSubscriber *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"prefix", "streamName", "host", "port", NULL};
    thread_struct *tstr = self->threadStruct;
    int i;
    char *host = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "ss|si", kwlist,
                                     &(tstr->prefix), &(tstr->streamname),
                                     &(host), &(tstr->zmqStruct->port)))
    {
        return 1;
    }

    if (!tstr->streamname) {
        PyErr_SetString(PyExc_TypeError, "streamname is NULL");
        return -1;
    }

    if (host) {
        printf("got host at init = %s\n",host);
        tstr->zmqStruct->host = strdup(host);
    }

    if (check_stream_name(tstr->streamname)) {
        char buf[256];
        strncpy(buf,"The streamName attribute value must be a valid streamName",sizeof(buf)-1);
        for (i=0; i<NUMBER_OF_STREAMS; i++) {
            strncat(buf,"\n",sizeof(buf)-1);
            strncat(buf,streamNameArr[i],sizeof(buf)-1);
        }
        PyErr_SetString(PyExc_ValueError, buf);
        return -1;
    }

    if (!tstr->prefix) {
        PyErr_SetString(PyExc_TypeError, "prefix is NULL");
        return -1;
    }

    threadstruct_init(tstr);

    tstr->dataHandle = calloc(32,sizeof(char));
    tstr->dataHeader = calloc(8,sizeof(int));
    tstr->dataSize = sizeof(char)*32;

    return 0;
}

static int
CircSubscriber_setdecimation(CircSubscriber *self, PyObject *value, void *closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "Cannot delete the decimation attribute");
        return -1;
    }

    if (!PyLong_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "The decimation attribute value must be an integer");
        return -1;
    }

    int dec = PyLong_AsLong(value);

    if (dec<0) {
        PyErr_SetString(PyExc_ValueError, "The decimation attribute value must not be negative");
        return -1;
    }

    int power = 1;
    while (dec >>= 1) power <<= 1;

    debug_print("Got power = %d = 2^%f\n",power, log2(power));

    int old_pow = (int)log2(self->threadStruct->decimation);
    int now_pow = (int)log2(power);

    debug_print("Unsetting value %d and setting %d\n",old_pow,now_pow);

    if (self->threadStruct->zmqStruct->subscriber) {
        zmq_setsockopt (self->threadStruct->zmqStruct->subscriber, ZMQ_UNSUBSCRIBE, self->threadStruct->zmqStruct->topic, self->threadStruct->zmqStruct->t_len+old_pow);
        zmq_setsockopt (self->threadStruct->zmqStruct->subscriber, ZMQ_SUBSCRIBE, self->threadStruct->zmqStruct->topic, self->threadStruct->zmqStruct->t_len+now_pow);
    }

    self->threadStruct->decimation = power;
    return 0;
}


static PyGetSetDef CircSubscriber_getsetters[] = {
    {"_prefix", (getter) CircStruct_getprefix, (setter) CircStruct_cantset,
     "prefix", NULL},
    {"_streamName", (getter) CircStruct_getstreamName, (setter) CircStruct_cantset,
     "stream name", NULL},
    {"_host", (getter) CircStruct_gethost, (setter) CircStruct_sethost,
     "host name", NULL},
    {"_multicast", (getter) CircStruct_getmulticast, (setter) CircStruct_setmulticast,
     "multicast address", NULL},
    {"_port", (getter) CircStruct_getport, (setter) CircStruct_setport,
     "port", NULL},
    {"_transport", (getter) CircStruct_gettransport, (setter) CircStruct_cantset,
     "publisher transport", NULL},
    {"_threadRunning", (getter) CircStruct_getthreadRunning, (setter) CircStruct_cantset,
     "thread flag", NULL},
    {"_status", (getter) CircStruct_getstatus, (setter) CircStruct_cantset,
     "status flags", NULL},
    {"_ndim", (getter) CircStruct_getndim, (setter) CircStruct_cantset,
     "ndim", NULL},
    {"_dtype", (getter) CircStruct_getdtype, (setter) CircStruct_cantset,
     "data type", NULL},
    {"_size", (getter) CircStruct_getsize, (setter) CircStruct_cantset,
     "array size", NULL},
    {"_decimation", (getter) CircStruct_getdecimation, (setter) CircSubscriber_setdecimation,
     "decimation", NULL},
    {"_shape", (getter) CircStruct_getshape, (setter) CircStruct_setshape,
     "shape", NULL},
    {"_cbdata", (getter) CircStruct_getcbdata, (setter) CircStruct_cantset,
     "shape", NULL},
    {"_latest", (getter) CircStruct_getlatest, (setter) CircStruct_cantset,
     "shape", NULL},
    {NULL}  /* Sentinel */
};

static PyObject *
CircSubscriber_start_thread(CircSubscriber *self){

    int rv = 0;
    struct timespec waitfor;

    if (self->threadRunning) {
        PyErr_SetString(PyExc_TypeError, "Thread already running");
        Py_INCREF(Py_None);
        return Py_None;
    }

    connect_zmq(self);

    self->threadStruct->thread_go = 1;
    if (pthread_create(&(self->threadStruct->tid),NULL,subscriber_thread,self->threadStruct)) {
        PyErr_SetString(PyExc_Exception,"Error creating pthread");
    } else {
        self->threadRunning = 1;
    }

    self->threadStruct->callback_go = 1;

    Py_BEGIN_ALLOW_THREADS
    clock_gettime(CLOCK_REALTIME,&waitfor);
    waitfor.tv_sec += 2;
    pthread_mutex_lock(self->threadStruct->cb_mutex);
    while(self->threadStruct->cb_flag==0) {
        if(pthread_cond_timedwait(self->threadStruct->cb_cond,self->threadStruct->cb_mutex,&waitfor)){
            rv = 1;
            break;
        }
    }
    self->threadStruct->cb_flag=0;
    pthread_mutex_unlock(self->threadStruct->cb_mutex);
    Py_END_ALLOW_THREADS

    self->threadStruct->callback_go = 0;

    if (rv) {
        PyErr_SetString(PyExc_TimeoutError,"Nothing received, stopping thread");
        // CircSubscriber_stop_subscriber(self);
        CircStruct_stop_thread(self);
        return NULL;
    }

    self->ndim[0] = self->threadStruct->dataHeader[5];

    PyArray_Descr *array_desc;
    npy_intp ndim[1] = {1};

    char *cheader = (char*)self->threadStruct->dataHeader;

    debug_print("Making array of size %d, shape %d, dtype %c\n",(int)self->ndim[0],self->nd,cheader[16]);
    Py_XDECREF(self->threadStruct->cb_data);
    array_desc = PyArray_DescrFromType(cheader[16]);
    self->threadStruct->cb_data = (PyArrayObject *)PyArray_Zeros(self->nd, self->ndim, array_desc, 0);

    Py_XDECREF(self->threadStruct->cb_ftim);
    array_desc = PyArray_DescrFromType(NPY_DOUBLE);
    self->threadStruct->cb_ftim = (PyArrayObject *)PyArray_Zeros(1, ndim, array_desc, 0);

    Py_XDECREF(self->threadStruct->cb_fnum);
    array_desc = PyArray_DescrFromType(NPY_UINT32);
    self->threadStruct->cb_fnum = (PyArrayObject *)PyArray_Zeros(1, ndim, array_desc, 0);
    
    self->threadStruct->sizechanged = 0;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef CircSubscriber_methods[] = {
    {"name", (PyCFunction) CircStruct_name, METH_NOARGS,
     "Return the name, combining the prefix and stream name"
    },
    {"address", (PyCFunction) CircStruct_address, METH_NOARGS,
     "Return the address, combining the host and port"
    },
    {"start_subscriber", (PyCFunction) CircSubscriber_start_thread, METH_NOARGS,
     "Start the c reader thread"
    },
    {"stop_subscriber", (PyCFunction) CircStruct_stop_thread, METH_NOARGS,
     "Stop the c reader thread"
    },
    {"use_tcp", (PyCFunction) CircStruct_use_tcp, METH_NOARGS,
     "Set TCP Transport"
    },
    {"use_ipc", (PyCFunction) CircStruct_use_ipc, METH_NOARGS,
     "Set IPC Transport"
    },
    {"use_epgm", (PyCFunction) CircStruct_use_epgm, METH_NOARGS,
     "Set EPGM Transport"
    },
    {"prepare_data", (PyCFunction) CircStruct_prepare_data, METH_VARARGS,
     "Prepare to get a block of data"
    },
    {"get_data", (PyCFunction) CircStruct_get_data, METH_VARARGS,
     "Get a block of data"
    },
    {"set_callback", (PyCFunction) CircStruct_set_callback, METH_VARARGS,
     "Add callback to reader thread"
    },
    {"stop_callback", (PyCFunction) CircStruct_stop_callback, METH_VARARGS,
     "Stop callback for reader thread"
    },
    {"wait_for_cb", (PyCFunction) CircStruct_wait_for_cb, METH_NOARGS,
     "Wait for the callback array to be filled"
    },
    {"prepare_save", (PyCFunction) CircStruct_prepare_save, METH_VARARGS,
     "Set mmap numpy arrays to copy data into"
    },
    {"cancel_save", (PyCFunction) CircStruct_cancel_save, METH_NOARGS,
     "cancel the save"
    },
    {"wait_for_save", (PyCFunction) CircStruct_wait_for_save, METH_VARARGS,
     "Wait for the file arrays to be filled"
    },
    {NULL}  /* Sentinel */
};

static PyObject *
CircSubscriber_str(CircSubscriber *self)
{
    return PyUnicode_FromFormat("CircSubscriber: %s, %s, %d", self->threadStruct->prefix, self->threadStruct->streamname,self->threadStruct->decimation);
}

static PyTypeObject CircSubscriberType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "ccirc.cCircSubscriber",
    .tp_doc = "cCircSubscriber objects",
    .tp_basicsize = sizeof(CircSubscriber),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = CircSubscriber_new,
    .tp_init = (initproc) CircSubscriber_init,
    .tp_dealloc = (destructor) CircSubscriber_dealloc,
    .tp_methods = CircSubscriber_methods,
    .tp_getset = CircSubscriber_getsetters,
    .tp_str = (reprfunc) CircSubscriber_str,
    .tp_repr = (reprfunc) CircSubscriber_str,
    .tp_traverse = (traverseproc) CircStruct_traverse,
    .tp_clear = (inquiry) CircStruct_clear,
};


/*

The CircReader Class, the main class to read the circular buffers.
Can return N values to Python, can signal for callbacks, can publish on a ZMQ PUB
and can save data to disk.

*/

static void
CircReader_dealloc(CircReader *self)
{
    PyObject_GC_UnTrack(self);
    if (self->threadRunning) {
        CircStruct_stop_thread(self);
    }
    debug_print("Reader thread stopped...\n");
    free_threadstruct(self->threadStruct,KEEP_DATA);
    // printf("Finishing dealloc...\n");
    Py_TYPE(self)->tp_free((PyObject *) self);
    // printf("Finished dealloc...\n");
}

static PyObject *
CircReader_new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    int i;
    CircReader *self;
    self = (CircReader *) type->tp_alloc(type, 0);

    if (self != NULL) {
        self->threadRunning = 0;
        self->nd = 1;
        for (i=0; i<6; i++)
            self->ndim[i] = 0;
        self->threadStruct = threadstruct_new(WITH_SHMSTRUCT);
    }
    return (PyObject *) self;
}

static int
CircReader_init(CircReader *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"prefix", "streamName", "decimation", "host", "port", NULL};
    thread_struct *tstr = self->threadStruct;
    int i;
    char *host = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "ss|isi", kwlist,
                                     &(tstr->prefix), &(tstr->streamname), &(tstr->decimation),
                                     &(host), &(tstr->zmqStruct->port)))
    {
        return 1;
    }

    if (!tstr->streamname) {
        PyErr_SetString(PyExc_TypeError, "streamname is NULL");
        return -1;
    }

    if (host){
        printf("got host on init = %s\n",host);
        tstr->zmqStruct->host = strdup(host);
    }

    if (check_stream_name(tstr->streamname)) {
        char buf[256];
        strncpy(buf,"The streamName attribute value must be a valid streamName",sizeof(buf)-1);
        for (i=0; i<NUMBER_OF_STREAMS; i++) {
            strncat(buf,"\n",sizeof(buf)-1);
            strncat(buf,streamNameArr[i],sizeof(buf)-1);
        }
        PyErr_SetString(PyExc_ValueError, buf);
        return -1;
    }

    if (!tstr->prefix) {
        PyErr_SetString(PyExc_TypeError, "prefix is NULL");
        return -1;
    }

    threadstruct_init(tstr);

    asprintf(&tstr->shmStruct->fullname,"/%s%s",tstr->prefix,tstr->streamname);

    if ((open_shm(self->threadStruct))==1){
        PyErr_SetString(PyExc_FileNotFoundError, "No circbuf found");
        return -1;
    }

    // if (get_next_frame(self->threadStruct)) {
    //     PyErr_SetString(PyExc_TypeError, "Can't get frame");
    //     return -1;
    // }

    // get_info(self->threadStruct);

    // self->ndim[0] = self->threadStruct->dataHeader[5];

    // PyArray_Descr *array_desc;
    // npy_intp ndim[1] = {1};

    // char *cheader = (char*)self->threadStruct->dataHeader;
    // array_desc = PyArray_DescrFromType(cheader[16]);
    // self->threadStruct->cb_data = PyArray_Zeros(self->nd, self->ndim, array_desc, 0);

    // array_desc = PyArray_DescrFromType(NPY_DOUBLE);
    // self->threadStruct->cb_ftim = PyArray_Zeros(1, ndim, array_desc, 0);

    // array_desc = PyArray_DescrFromType(NPY_UINT32);
    // self->threadStruct->cb_fnum = PyArray_Zeros(1, ndim, array_desc, 0);

    return 0;
}

static int
CircReader_setdecimation(CircReader *self, PyObject *value, void *closure)
{
    if (self->threadStruct->thread_go!=1) {
        PyErr_SetString(PyExc_RuntimeError, "Thread not running");
        return -1;
    }

    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "Cannot delete the decimation attribute");
        return -1;
    }

    if (!PyLong_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "The decimation attribute value must be an integer");
        return -1;
    }

    int dec = PyLong_AsLong(value);

    if (dec<0) {
        PyErr_SetString(PyExc_ValueError, "The decimation attribute value must not be negative");
        return -1;
    }
    // try to set cb decimation...
    if (self->threadStruct->shmStruct->shmOpen) {
        FREQ(self->threadStruct->shmStruct->cb) = dec;
        self->threadStruct->decimation = dec;
    } else {
        PyErr_SetString(PyExc_RuntimeError, "The shm is not open, can't set decimation");
        return -1;
    }

    return 0;
}

static PyGetSetDef CircReader_getsetters[] = {
    {"_prefix", (getter) CircStruct_getprefix, (setter) CircStruct_cantset,
     "prefix", NULL},
    {"_streamName", (getter) CircStruct_getstreamName, (setter) CircStruct_cantset,
     "stream name", NULL},
    {"_host", (getter) CircStruct_gethost, (setter) CircStruct_sethost,
     "host name", NULL},
    {"_multicast", (getter) CircStruct_getmulticast, (setter) CircStruct_setmulticast,
     "multicast address", NULL},
    {"_port", (getter) CircStruct_getport, (setter) CircStruct_setport,
     "port", NULL},
    {"_transport", (getter) CircStruct_gettransport, (setter) CircStruct_cantset,
     "publisher transport", NULL},
    {"_threadRunning", (getter) CircStruct_getthreadRunning, (setter) CircStruct_cantset,
     "thread flag", NULL},
    {"_status", (getter) CircStruct_getstatus, (setter) CircStruct_cantset,
     "status flags", NULL},
    {"_ndim", (getter) CircStruct_getndim, (setter) CircStruct_cantset,
     "ndim", NULL},
    {"_dtype", (getter) CircStruct_getdtype, (setter) CircStruct_cantset,
     "data type", NULL},
    {"_size", (getter) CircStruct_getsize, (setter) CircStruct_cantset,
     "array size", NULL},
    {"_decimation", (getter) CircStruct_getdecimation, (setter) CircReader_setdecimation,
     "decimation", NULL},
    {"_shape", (getter) CircStruct_getshape, (setter) CircStruct_setshape,
     "shape", NULL},
    {"_cbdata", (getter) CircStruct_getcbdata, (setter) CircStruct_cantset,
     "shape", NULL},
    {"_latest", (getter) CircStruct_getlatest, (setter) CircStruct_cantset,
     "shape", NULL},
    {NULL}  /* Sentinel */
};

static PyObject *
CircReader_start_thread(CircReader *self){

    if (get_next_frame(self->threadStruct)) {
        PyErr_SetString(PyExc_TypeError, "Can't get frame");
        return NULL;
    }

    get_info(self->threadStruct);

    self->ndim[0] = self->threadStruct->dataHeader[5];

    PyArray_Descr *array_desc;
    npy_intp ndim[1] = {1};

    char *cheader = (char*)self->threadStruct->dataHeader;
    array_desc = PyArray_DescrFromType(cheader[16]);
    self->threadStruct->cb_data = (PyArrayObject *)PyArray_Zeros(self->nd, self->ndim, array_desc, 0);

    array_desc = PyArray_DescrFromType(NPY_DOUBLE);
    self->threadStruct->cb_ftim = (PyArrayObject *)PyArray_Zeros(1, ndim, array_desc, 0);

    array_desc = PyArray_DescrFromType(NPY_UINT32);
    self->threadStruct->cb_fnum = (PyArrayObject *)PyArray_Zeros(1, ndim, array_desc, 0);

    if (self->threadRunning) {
        return PyLong_FromLong(1);
    }

    self->threadStruct->thread_go = 1;
    if (pthread_create(&(self->threadStruct->tid),NULL,reader_thread,self->threadStruct)) {
        PyErr_SetString(PyExc_Exception,"Error creating pthread");
    } else {
        self->threadRunning = 1;
    }

    return PyLong_FromLong(0);
}

static PyObject *
CircReader_set_publish(CircReader *self, PyObject *args){

    if (self->threadStruct->thread_go!=1) {
        PyErr_SetString(PyExc_RuntimeError, "Thread not running");
        return NULL;
    }

    int pub = 0;
    ZMQContext *value = NULL;

    if (!PyArg_ParseTuple(args, "i|O!", &pub, &ZMQContextType, &value)){
        PyErr_SetString(PyExc_TypeError, "Wrong Args");
        return NULL;
    }

    if (value) {
        Py_INCREF(value);
        self->threadStruct->zmqStruct->shared_context = value->context;
    }

    if (pub==0) {
        self->threadStruct->publish_go = pub;
        disconnect_zmq(self);
        // printf("Thread publish_go = %d....\n",pub);
    } else
    if (pub==1) {
        bind_zmq(self);
        self->threadStruct->publish_go = pub;
        // printf("Thread publish_go = %d....\n",pub);
    }
    else {
        PyErr_SetString(PyExc_ValueError, "Wrong value");
        return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef CircReader_methods[] = {
    {"name", (PyCFunction) CircStruct_name, METH_NOARGS,
     "Return the name, combining the prefix and stream name"
    },
    {"address", (PyCFunction) CircStruct_address, METH_NOARGS,
     "Return the address, combining the host and port"
    },
    {"start_reader", (PyCFunction) CircReader_start_thread, METH_NOARGS,
     "Start the c reader thread"
    },
    {"stop_reader", (PyCFunction) CircStruct_stop_thread, METH_NOARGS,
     "Stop the c reader thread"
    },
    {"set_publish", (PyCFunction) CircReader_set_publish, METH_VARARGS,
     "Start publishing"
    },
    {"use_tcp", (PyCFunction) CircStruct_use_tcp, METH_NOARGS,
     "Set TCP Transport"
    },
    {"use_ipc", (PyCFunction) CircStruct_use_ipc, METH_NOARGS,
     "Set IPC Transport"
    },
    {"use_epgm", (PyCFunction) CircStruct_use_epgm, METH_NOARGS,
     "Set IPC Transport"
    },
    {"prepare_data", (PyCFunction) CircStruct_prepare_data, METH_VARARGS,
     "Prepare to get a block of data"
    },
    {"get_data", (PyCFunction) CircStruct_get_data, METH_VARARGS,
     "Get a block of data"
    },
    {"set_callback", (PyCFunction) CircStruct_set_callback, METH_VARARGS,
     "Add callback to reader thread"
    },
    {"stop_callback", (PyCFunction) CircStruct_stop_callback, METH_VARARGS,
     "Stop callback for reader thread"
    },
    {"wait_for_cb", (PyCFunction) CircStruct_wait_for_cb, METH_NOARGS,
     "Wait for the callback array to be filled"
    },
    {"prepare_save", (PyCFunction) CircStruct_prepare_save, METH_VARARGS,
     "Set mmap numpy arrays to copy data into"
    },
    {"cancel_save", (PyCFunction) CircStruct_cancel_save, METH_NOARGS,
     "cancel the save"
    },
    {"start_save", (PyCFunction) CircStruct_start_save, METH_VARARGS,
     "Set mmap numpy arrays to copy data into"
    },
    {"wait_for_save", (PyCFunction) CircStruct_wait_for_save, METH_VARARGS,
     "Wait for the file arrays to be filled"
    },
    {NULL}  /* Sentinel */
};

static PyObject *
CircReader_str(CircReader *self)
{
    return PyUnicode_FromFormat("cCircReader: %s, %s, %d", self->threadStruct->prefix, self->threadStruct->streamname, self->threadStruct->decimation);
}

static PyTypeObject CircReaderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "ccirc.cCircReader",
    .tp_doc = "cCircReader objects",
    .tp_basicsize = sizeof(CircReader),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = CircReader_new,
    .tp_init = (initproc) CircReader_init,
    .tp_dealloc = (destructor) CircReader_dealloc,
    .tp_methods = CircReader_methods,
    .tp_getset = CircReader_getsetters,
    .tp_str = (reprfunc) CircReader_str,
    .tp_repr = (reprfunc) CircReader_str,
    .tp_traverse = (traverseproc) CircStruct_traverse,
    .tp_clear = (inquiry) CircStruct_clear,
};

static PyModuleDef ccircmodule = {
    PyModuleDef_HEAD_INIT,
    .m_name = "telelmetry",
    .m_doc = "Example module that creates an extension type.",
    .m_size = -1,
};

PyMODINIT_FUNC
PyInit_ccirc(void)
{
    PyObject *m;
    if (PyType_Ready(&CircReaderType) < 0)
        return NULL;

    if (PyType_Ready(&CircSubscriberType) < 0)
        return NULL;

    if (PyType_Ready(&CircSyncType) < 0)
        return NULL;

    if (PyType_Ready(&ZMQContextType) < 0)
        return NULL;

    import_array();
    m = PyModule_Create(&ccircmodule);
    if (m == NULL)
        return NULL;

    Py_INCREF(&CircReaderType);
    if (PyModule_AddObject(m, "cCircReader", (PyObject *) &CircReaderType) < 0) {
        Py_DECREF(&CircReaderType);
        Py_DECREF(m);
        return NULL;
    }

    Py_INCREF(&CircSubscriberType);
    if (PyModule_AddObject(m, "cCircSubscriber", (PyObject *) &CircSubscriberType) < 0) {
        Py_DECREF(&CircSubscriberType);
        Py_DECREF(m);
        return NULL;
    }

    Py_INCREF(&CircSyncType);
    if (PyModule_AddObject(m, "cCircSync", (PyObject *) &CircSyncType) < 0) {
        Py_DECREF(&CircSyncType);
        Py_DECREF(m);
        return NULL;
    }

    Py_INCREF(&ZMQContextType);
    if (PyModule_AddObject(m, "cZMQContext", (PyObject *) &ZMQContextType) < 0) {
        Py_DECREF(&ZMQContextType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}


int
get_stream_index(const char *value, int *index)
{
    int i;
    for (i=0; i<NUMBER_OF_STREAMS; i++) {
        if (!strcmp(value,streamNameArr[i])) {
            *index = i;
            return 0;
        }
    }
    debug_print("Error, wrong streamName\n");
    return 1;
}


int
check_stream_name(const char *value)
{
    int i;
    for (i=0; i<NUMBER_OF_STREAMS; i++) {
        if (!strcmp(value,streamNameArr[i])) {
            return 0;
        }
    }
    return 1;
}

void *
reader_thread(void *t_args)
{
    thread_struct *t_struct = t_args;
    // dummy_open(t_struct);
    // printf("[Before Loop] Got t_struct->dataHeader[0] = %d\n",t_struct->dataHeader[0]);
    // printf("[Before Loop] Got t_struct->dataHeader[5] = %d\n",t_struct->dataHeader[5]);
    int cnt = 0;
    while (t_struct->thread_go) {
        if (get_next_frame(t_struct)) {
            cnt+=1;
            if (cnt>5) {
                printf("circbuf going down....");
                t_struct->thread_go = 0;
                return NULL;
            }
            continue;
        }
        // printf("[After get] Got t_struct->dataHeader[0] = %d\n",t_struct->dataHeader[0]);
        // printf("[After get] Got t_struct->dataHeader[5] = %d\n",t_struct->dataHeader[5]);
        // dummy_get(t_args);
        if (t_struct->publish_go){
            // send_hdr(t_args);
            // printf("[Publish] Got t_struct->dataHeader[0] = %d\n",t_struct->dataHeader[0]);
            // printf("[Publish] Got t_struct->dataHeader[5] = %d\n",t_struct->dataHeader[5]);
            send_data(t_args);
            // dummy_send(t_args);
        }
        if (t_struct->data_go > 0){
            copy_data(t_struct);
        }
        if (t_struct->callback_go) {
            callback_data(t_struct);
        }
        if (t_struct->file_go) {
            save_data(t_struct);
        }
        // usleep(1000000);
        cnt=0;
    }
    return NULL;
}

void *
subscriber_thread(void *t_args)
{
    thread_struct *t_struct = t_args;
    // dummy_open(t_struct);
    int cnt=0;
    while (t_struct->thread_go) {
        // if (get_data(t_struct)) {
        //     continue;
        // }
        if (receive_data(t_args)) {
            cnt+=1;
            if (cnt>5) {
                printf("circsubscriber going down....\n");
                t_struct->thread_go = 0;
                return NULL;
            }
            continue;
        }
        // dummy_get(t_args);
        if (t_struct->data_go > 0){
            copy_data(t_struct);
        }
        if (t_struct->callback_go) {
            callback_data(t_struct);
        }
        if (t_struct->file_go) {
            save_data(t_struct);
        }
        cnt=0;
        // usleep(1000000);
    }
    return NULL;
}

inline int
open_shm(thread_struct *tstr)
{
    tstr->shmStruct->shmOpen = 0;
    // while(tstr->shmStruct->shmOpen==0){
    if((tstr->shmStruct->cb=circOpenBufReader(tstr->shmStruct->fullname))!=NULL){
        tstr->shmStruct->shmOpen=1;
    } else {
        printf("No circbuf found\n");
        // usleep(1000000);
        return 1;
    }
    // }
    circHeaderUpdated(tstr->shmStruct->cb);
    tstr->shmStruct->old_dec = FREQ(tstr->shmStruct->cb);
    debug_print("setting decimation....\n");
    FREQ(tstr->shmStruct->cb) = tstr->decimation;
    debug_print("/dev/shm%s opened\n",tstr->shmStruct->fullname);
    return 0;
}

inline int
get_next_frame(thread_struct *tstr)
{
    int lw;
    int diff;
    float wait = 2;
    char *ret = circGetNextFrame(tstr->shmStruct->cb,wait,1);
    if(ret==NULL){
      return 1;
	}
    lw = LASTWRITTEN(tstr->shmStruct->cb);//circbuf.lastWritten[0];
    if (lw>=0) {
        diff = lw-tstr->shmStruct->cb->lastReceived;
        if (diff<0) {
            diff+=NSTORE(tstr->shmStruct->cb);//circbuf.nstore[0];
        }
        //printf("diff %d %d %d\n",diff,lw,tstr->cb->lastReceived);
        if (diff>NSTORE(tstr->shmStruct->cb)*0.75) {//ircbuf.nstore[0]*.75){
            // if (tstr->contig==0) {
            printf("Sending of %s lagging - skipping %d frames\n",tstr->shmStruct->fullname,diff-1);
            ret=circGetFrame(tstr->shmStruct->cb,lw);//tstr->circbuf.get(lw,copy=1);
            // } else {
            //     printf("Sending of %s lagging - contig requested - hoping to catch up!!!\n",tstr->shmStruct->fullname);
            // }
        }
    }

    if (ret==NULL) {
        return 1;
    }

    tstr->dataHeader = (int *)ret;
    tstr->dataHandle = &((char *)ret)[32];

    tstr->dataSize = tstr->dataHeader[0] - 28;

    tstr->dataHeader[5] = (int)(SHAPEARR(tstr->shmStruct->cb)[0]);
    tstr->dataHeader[6] = tstr->elsize;

    // char *cheader = (char*)tstr->dataHeader;
    // char *dheader = (double*)tstr->dataHeader;
    // if (DTYPE(tstr->shmStruct->cb)!=cheader[16]){
    //     cheader[16] = DTYPE(tstr->shmStruct->cb);
    //     lw=1;
    //     printf("circbuf dtype changed, should only happen on init...\n");
    // }
    // if (SHAPEARR(tstr->shmStruct->cb)[0]!=tstr->dataHeader[1]){
    //     tstr->dataHeader[1] = SHAPEARR(tstr->shmStruct->cb)[0];
    //     printf("circbuf shapearr changed, should only happen on init...\n");
    // }

    // tstr->data_size=((int*)ret)[0]+4;
    // tstr->shmStruct->current_ftime=((double *)ret)[1];
    // ((double *)tstr->dataHeader)[2] = ((double *)tstr->dataHandle)[1];
    // tstr->shmStruct->current_fnumb=((int *)ret)[1];
    // tstr->dataHeader[3] = ((int *)tstr->dataHandle)[1];
    // printf("Setting tstr->dataHeader[0] = %d\n",((int *)tstr->dataHandle)[0]);
    // tstr->dataHeader[0] = ((int *)tstr->dataHandle)[0];
    return 0;
}

inline int
get_info(thread_struct *tstr){

    switch(DTYPE(tstr->shmStruct->cb)){
        case 'f':
            tstr->elsize=4;
            break;
        case 'i':
            tstr->elsize=4;
            break;
        case 'h':
            tstr->elsize=2;
            break;
        case 'H':
            tstr->elsize=2;
            break;
        case 'c':
            tstr->elsize=1;
            break;
        case 'b':
            tstr->elsize=1;
            break;
        case 'B':
            tstr->elsize=1;
            break;
        case 'd':
            tstr->elsize=8;
            break;
        default:
            printf("Unknown datatype %c in sender.c - recode...\n",DTYPE(tstr->shmStruct->cb));
            tstr->elsize=4;
            break;
    }

    // printf("Setting tstr->dataHeader[0] = %d\n",((int *)tstr->dataHandle)[0]);
    // tstr->dataHeader[0] = ((int *)tstr->dataHandle)[0];

    return 0;
}

inline int
int2bin8(int a, char *buffer, int from) {
    int i;
    buffer += from;
    for (i = from+7; i >= from; i--) {
        *buffer++ = (a & 1) + '0';
        a >>= 1;
    }
    return 0;
}

inline int
send_data(thread_struct *tstr)
{
    int nsent;
    int size = tstr->dataSize;
    int2bin8(tstr->dataHeader[1],tstr->zmqStruct->topic,tstr->zmqStruct->t_len);

    debug_print("[%s] %d, %d, %f, %d, %d, %c\n",tstr->zmqStruct->topic, tstr->dataHeader[0], tstr->dataHeader[1], ((double*)tstr->dataHeader)[1], tstr->dataHeader[5], tstr->dataHeader[6], ((char*)tstr->dataHeader)[16]);

    nsent = zmq_send (tstr->zmqStruct->publisher, tstr->zmqStruct->topic, TOPIC_LEN, ZMQ_SNDMORE);
    // nsent = zmq_send (tstr->zmqStruct->publisher, tstr->dataHandle, 32, ZMQ_SNDMORE);
    // printf("Sending dataHeader[1] as %d\n",tstr->dataHeader[1]);
    // printf("Sending dataHeader[5] as %d\n",tstr->dataHeader[5]);
    nsent = zmq_send (tstr->zmqStruct->publisher, tstr->dataHeader, 32, ZMQ_SNDMORE);
    nsent = zmq_send (tstr->zmqStruct->publisher, tstr->dataHandle, size, 0);
    // nsent = zmq_send (tstr->zmqStruct->publisher, &tstr->dataHandle[32], size, 0);

    return nsent;
}

inline int
receive_data(thread_struct *tstr)
{

    int nreceived;
    nreceived = zmq_recv (tstr->zmqStruct->subscriber, tstr->zmqStruct->topic_in, TOPIC_LEN, 0);
    if (nreceived == -1) {
        printf("Timeout...\n");
        return 1;
    }
    nreceived = zmq_recv (tstr->zmqStruct->subscriber, tstr->dataHeader, 32, 0);
    debug_print("[%s] %d, %d, %f, %d, %d, %c\n",tstr->zmqStruct->topic, tstr->dataHeader[0], tstr->dataHeader[1], ((double*)tstr->dataHeader)[1], tstr->dataHeader[5], tstr->dataHeader[6], ((char*)tstr->dataHeader)[16]);

    // if (tstr->dataSize < tstr->dataHeader[0]+4) {
    //     printf("got datsize = %d != %d\n",tstr->dataHeader[0]+4,tstr->dataSize);
    //     process_data(tstr);
    // }
    // printf("Got dataHeader[5] as %d\n",tstr->dataHeader[5]);
    if (tstr->dataSize < tstr->dataHeader[0]-28) {
        printf("got datsize = %d != %d\n",tstr->dataHeader[0]-28,tstr->dataSize);
        process_data(tstr);
    }
    nreceived = zmq_recv (tstr->zmqStruct->subscriber, tstr->dataHandle, tstr->dataSize, 0);
    debug_print("Received %d bytes\n",nreceived);
    if (nreceived != tstr->dataSize) {
        printf("Received wrong size... got %d, should be %d\n",nreceived, tstr->dataSize);
        return 1;
    }
    return 0;
}

inline int
process_data(thread_struct *tstr)
{

    // if (tstr->dataSize < tstr->dataHeader[0]+4) {
    //     free(tstr->dataHandle);
    //     tstr->dataHandle = malloc(sizeof(char)*(tstr->dataHeader[0]+4));
    //     tstr->dataSize = sizeof(char)*(tstr->dataHeader[0]+4);
    //     printf("making data of size %d\n",tstr->dataSize);
    // }

    if (tstr->dataSize < tstr->dataHeader[0]-28) {
        if (tstr->dataHandle)
            free(tstr->dataHandle);
        tstr->dataHandle = malloc(sizeof(char)*(tstr->dataHeader[0]-28));
        tstr->dataSize = sizeof(char)*(tstr->dataHeader[0]-28);
        debug_print("making data of size %d\n",tstr->dataSize);
    }

    tstr->elsize = tstr->dataHeader[6];

    return 0;
}


inline int
copy_data(thread_struct *tstr)
{
    int size = tstr->dataSize;
    int index = tstr->data_index;
    double *ftime_arr = (double *)PyArray_DATA(tstr->ftim_array);
    unsigned int *fnumb_arr = (unsigned int *)PyArray_DATA(tstr->fnum_array);
    void *data_loc = PyArray_DATA(tstr->data_array)+index*size;
    memcpy(data_loc,tstr->dataHandle,size);
    ftime_arr[index] = ((double *)tstr->dataHeader)[1];
    fnumb_arr[index] = tstr->dataHeader[1];
    tstr->data_index++;
    tstr->data_go--;
    if (tstr->data_go==0) {
        pthread_cond_signal(tstr->data_cond);
    }
    return 0;
}

inline int
callback_data(thread_struct *tstr){
    // int size = ((int*)tstr->dataHandle)[0]+4;
    int size = tstr->dataSize;
    // if (tstr->cb_data)
    memcpy(PyArray_DATA(tstr->cb_data),tstr->dataHandle,size);
    // if (tstr->cb_ftim)
    memcpy(PyArray_DATA(tstr->cb_ftim),&tstr->dataHeader[2],sizeof(double));
    // if (tstr->cb_fnum)
    memcpy(PyArray_DATA(tstr->cb_fnum),&tstr->dataHeader[1],sizeof(unsigned int));
    pthread_mutex_lock(tstr->cb_mutex);
    tstr->cb_flag = 1;
    pthread_cond_broadcast(tstr->cb_cond);
    pthread_mutex_unlock(tstr->cb_mutex);
    return 0;
}

inline int
save_data(thread_struct *tstr){
    int size = tstr->dataSize;
    int count;
    file_struct *fs = &(tstr->fileStruct[tstr->file_index]);
    if (fs->file_elem > 0) {
        //copy into current index
        count = fs->file_count;
        // double *ftime_arr = (double *)PyArray_DATA(tstr->file_ftim[tstr->file_index]);
        // unsigned int *fnumb_arr = (unsigned int *)PyArray_DATA(tstr->file_fnum[tstr->file_index]);
        memcpy(&(fs->file_data[count*size]),tstr->dataHandle,size);
        fs->file_ftim[count] = ((double *)tstr->dataHeader)[1];
        fs->file_fnum[count] = tstr->dataHeader[1];
        debug_print("Copying into current index=%d:%d\n",tstr->file_index,count);
        pthread_mutex_lock(tstr->file_mutex);
        fs->file_elem--;
        fs->file_count++;
        pthread_mutex_unlock(tstr->file_mutex);
        return 0;
    }
    //signal that a file is done
    pthread_cond_signal(tstr->file_cond);
    debug_print("file is done...\n");
    int err = munmap(fs->ptr, fs->mmap_size);
    fs->ptr = NULL;
    if(err != 0){
        printf("UnMapping Failed\n");
    }
    // swap the index
    tstr->file_index = 1-tstr->file_index;
    fs = &(tstr->fileStruct[tstr->file_index]);
    if ((fs->file_elem > 0)) {
        count = fs->file_count;
        // copy into new index
        memcpy(&(fs->file_data[count*size]),tstr->dataHandle,size);
        fs->file_ftim[count] = ((double *)tstr->dataHeader)[1];
        fs->file_fnum[count] = tstr->dataHeader[1];
        debug_print("Copying into new index=%d\n",1-tstr->file_index);
        pthread_mutex_lock(tstr->file_mutex);
        fs->file_elem--;
        fs->file_count++;
        pthread_mutex_unlock(tstr->file_mutex);
        return 0;
    }
    tstr->file_go=0;
    return 0;
}

inline int
reshape_cb(CircReader *self){
    PyArray_Dims dims;
    dims.ptr = self->ndim;
    dims.len = self->nd;
    self->threadStruct->cb_data = (PyArrayObject *)PyArray_Newshape(self->threadStruct->cb_data, &dims, NPY_CORDER);
    return 0;
}

inline int
bind_zmq(CircReader *self){

    debug_print("Binding ZMQ...\n");

    int pub_go = self->threadStruct->publish_go;
    self->threadStruct->publish_go = 0;

    if (!self->threadStruct->zmqStruct->shared_context) {
        if (!self->threadStruct->zmqStruct->context) {
            self->threadStruct->zmqStruct->context = zmq_ctx_new();
        }
        self->threadStruct->zmqStruct->publisher = zmq_socket(self->threadStruct->zmqStruct->context, ZMQ_PUB);
    } else {
        // printf("Connecting ZMQ.2..\n");
        disconnect_zmq(self);
        // printf("Connecting ZMQ.3..\n");
        self->threadStruct->zmqStruct->publisher = zmq_socket (self->threadStruct->zmqStruct->shared_context, ZMQ_PUB);
    }

    char address[64];
    int bind = 1;
    // printf("Connecting ZMQ.4..\n");
    if (self->threadStruct->zmqStruct->transport == tr_ipc){
        // printf("Doing IPC\n");
        snprintf(&address[0],64,"ipc:///dev/shm/zmq_%s%s",self->threadStruct->streamname,self->threadStruct->prefix);
    } else
    if (self->threadStruct->zmqStruct->transport == tr_epgm) {
        // printf("Doing EPGM\n");
        snprintf(&address[0],64,"epgm://%s;%s:%d",self->threadStruct->zmqStruct->host,self->threadStruct->zmqStruct->multicast,self->threadStruct->zmqStruct->port);
        // bind = 0;
    } else
    {
        // printf("Doing TCP\n");
        sprintf(&address[0],"tcp://%s:%d",self->threadStruct->zmqStruct->host,self->threadStruct->zmqStruct->port);
    }
    debug_print("Address = %s\n",address);
    if (bind) {
        zmq_bind (self->threadStruct->zmqStruct->publisher, address);
    } else {
        zmq_connect (self->threadStruct->zmqStruct->publisher, address);
    }
    int sndhwm = 3;
    zmq_setsockopt (self->threadStruct->zmqStruct->publisher, ZMQ_SNDHWM, &sndhwm, sizeof(int));
    self->threadStruct->publish_go = pub_go;
    return 0;
}

inline int
connect_zmq(CircReader *self){

    debug_print("Connecting ZMQ...\n");

    int pub_go = self->threadStruct->publish_go;
    self->threadStruct->publish_go = 0;

    if (!self->threadStruct->zmqStruct->shared_context) {
        if (!self->threadStruct->zmqStruct->context) {
            self->threadStruct->zmqStruct->context = zmq_ctx_new();
        }
        self->threadStruct->zmqStruct->subscriber = zmq_socket(self->threadStruct->zmqStruct->context, ZMQ_SUB);
    } else
    {
        // printf("Connecting ZMQ.2..\n");
        disconnect_zmq(self);
        // printf("Connecting ZMQ.3..\n");
        self->threadStruct->zmqStruct->subscriber = zmq_socket (self->threadStruct->zmqStruct->shared_context, ZMQ_SUB);
    }

    char address[64];
    // printf("Connecting ZMQ.4..\n");
    int bind = 0;
    if (self->threadStruct->zmqStruct->transport == tr_ipc){
        // printf("Doing IPC\n");
        snprintf(&address[0],64,"ipc:///dev/shm/zmq_%s%s",self->threadStruct->streamname,self->threadStruct->prefix);
    } else
    if (self->threadStruct->zmqStruct->transport == tr_epgm) {
        // printf("Doing EPGM\n");
        snprintf(&address[0],64,"epgm://%s;%s:%d",self->threadStruct->zmqStruct->host,self->threadStruct->zmqStruct->multicast,self->threadStruct->zmqStruct->port);
        // bind = 1;
    } else
    {
        // printf("Doing TCP\n");
        sprintf(&address[0],"tcp://%s:%d",self->threadStruct->zmqStruct->host,self->threadStruct->zmqStruct->port);
    }
    debug_print("Address = %s\n",address);
    int pow = log2(self->threadStruct->decimation);
    if (bind) {
        zmq_bind (self->threadStruct->zmqStruct->subscriber, address);
    } else {
        zmq_connect (self->threadStruct->zmqStruct->subscriber, address);
    }
    zmq_setsockopt (self->threadStruct->zmqStruct->subscriber, ZMQ_SUBSCRIBE, self->threadStruct->zmqStruct->topic, self->threadStruct->zmqStruct->t_len+pow);
    int timeout = 1000;
    zmq_setsockopt (self->threadStruct->zmqStruct->subscriber, ZMQ_RCVTIMEO, &timeout, sizeof(int));
    int rcvhwm = 3;
    zmq_setsockopt (self->threadStruct->zmqStruct->subscriber, ZMQ_RCVHWM, &rcvhwm, sizeof(int));
    self->threadStruct->publish_go = pub_go;
    return 0;
}

inline int
disconnect_zmq(CircReader *self){

    debug_print("Disconnecting ZMQ...\n");

    self->threadStruct->publish_go = 0;

    if (self->threadStruct->zmqStruct->publisher)
        zmq_close (self->threadStruct->zmqStruct->publisher);
    self->threadStruct->zmqStruct->publisher = NULL;
    if (self->threadStruct->zmqStruct->subscriber)
        zmq_close (self->threadStruct->zmqStruct->subscriber);
    self->threadStruct->zmqStruct->subscriber = NULL;
    if (self->threadStruct->zmqStruct->context)
        zmq_ctx_destroy(self->threadStruct->zmqStruct->context);
    self->threadStruct->zmqStruct->context = NULL;

    return 0;
}