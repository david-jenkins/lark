
#include <sys/mman.h>
#include <pthread.h>
#include <unistd.h>
#include <numpy/arrayobject.h>
#include <czmq.h>
#include "structmember.h"
#include "circ.h"

#ifndef DEBUG
#define DEBUG 1
#endif

#define debug_print(fmt, ...) \
        do { if (DEBUG) fprintf(stderr, "%s:%d:%s(): " fmt, __FILE__, \
                                __LINE__, __func__, ##__VA_ARGS__); } while (0)

#define NUMBER_OF_STREAMS 12
#define MAX_CALLBACKS 10
#define MAX_FITS_FRAMES 1000
#define TOPIC_LEN 64
#define FRAMES_PER_CHUNK 10
/*

The CircSync Class, used to create a shared pthreads barrier to pass to other classes.

*/

typedef struct {
    PyObject_HEAD
    int nthreads;
    pthread_barrier_t *barrier;
} CircSync;

static int
CircSync_traverse(CircSync *self, visitproc visit, void *arg);

static int
CircSync_clear(CircSync *self);

static void
CircSync_dealloc(CircSync *self);

static PyObject *
CircSync_new(PyTypeObject *type, PyObject *args, PyObject *kwargs);

static int
CircSync_init(CircSync *self, PyObject *args, PyObject *kwargs);

static PyObject *
CircSync_str(CircSync *self);

/*

The ZMQContext Class, used to share a single ZMQ context among other classes.

*/

typedef struct {
    PyObject_HEAD
    void *context;
} ZMQContext;

static int
ZMQContext_traverse(ZMQContext *self, visitproc visit, void *arg);

static int
ZMQContext_clear(ZMQContext *self);

static void
ZMQContext_dealloc(ZMQContext *self);

static PyObject *
ZMQContext_new(PyTypeObject *type, PyObject *args, PyObject *kwargs);

static int
ZMQContext_init(ZMQContext *self, PyObject *args, PyObject *kwargs);

static PyObject *
ZMQContext_str(ZMQContext *self);


/*

Common values, structs and functions for CircSubscriber and CircReader

*/


static const char *streamNameArr[] = {
    "rtcActuatorBuf",  "rtcErrorBuf",   "rtcParam1",  "rtcStatusBuf",
    "rtcCalPxlBuf",    "rtcFluxBuf",    "rtcParam2",  "rtcSubLocBuf",
    "rtcCentBuf",      "rtcMirrorBuf",  "rtcPxlBuf",  "rtcTimeBuf",
};

typedef enum stream_enum {
    rtcCentBuf, rtcPxlBuf, rtcCalPxlBuf, rtcMirrorBuf,rtcActuatorBuf
} stream_enum;

typedef enum zmq_transport {
    tr_tcp, tr_ipc, tr_epgm, tr_inproc
} zmq_transport;

typedef struct zmq_struct {
    char *host;
    int port;
    void *context;
    void *shared_context;
    void *publisher;
    void *subscriber;
    void *buffer;
    char topic[TOPIC_LEN];
    char topic_in[TOPIC_LEN];
    int t_len;
    zmq_transport transport;
    char *multicast;
} zmq_struct;

typedef struct file_struct {
    char *ptr;
    int mmap_size;
    int file_elem;
    int file_count;
    int file_firstfnum;
    char *file_data;
    double *file_ftim;
    unsigned int *file_fnum;
} file_struct;

typedef struct shm_struct {
    char *fullname;
    circBuf *cb;
    int shmOpen;
    int old_dec;
    int data_size;
    int nstore;
    double current_ftime;
    unsigned int current_fnumb;
} shm_struct;

typedef struct thread_struct {

    const char *prefix;
    const char *streamname;
    int decimation;
    char *dataHandle;
    int *dataHeader;
    int dataSize;
    int elsize;

    // shm params
    shm_struct *shmStruct;

    // threading params
    pthread_t tid;
    volatile int thread_go;
    int publish_go;
    volatile int data_go;

    // data params
    int data_index;
    PyArrayObject *data_array;
    PyArrayObject *ftim_array;
    PyArrayObject *fnum_array;
    pthread_mutex_t *data_mutex;
    pthread_cond_t *data_cond;
    int sizechanged;

    // callback params
    int callback_go;
    PyArrayObject *cb_data;
    PyArrayObject *cb_ftim;
    PyArrayObject *cb_fnum;
    volatile int cb_flag;
    pthread_mutex_t *cb_mutex;
    pthread_cond_t *cb_cond;

    // file params
    int file_go;
    int file_index;
    int buffer_index;
    void (*save_fn)(void *);
    char *data_buffer;
    double *ftim_buffer;
    unsigned int *fnum_buffer;
    pthread_mutex_t *file_mutex;
    pthread_cond_t *file_cond;
    file_struct fileStruct[2];

    // publish params
    zmq_struct *zmqStruct;

} thread_struct;

#define FREE_DATA 1
#define KEEP_DATA 0

inline int free_threadstruct(thread_struct *tstr, int free_data);

#define WITH_SHMSTRUCT 1
#define WITHOUT_SHMSTRUCT 0

thread_struct *threadstruct_new(int shm_option);

int threadstruct_init(thread_struct *tstr);

typedef struct CircStruct {
    PyObject_HEAD
    int threadRunning;
    thread_struct *threadStruct;
    int nd;
    npy_intp ndim[6];
} CircStruct;

typedef struct CircStruct CircReader;
typedef struct CircStruct CircSubscriber;

static int
CircStruct_traverse(CircStruct *self, visitproc visit, void *arg);

static int
CircStruct_clear(CircStruct *self);

static PyObject *
CircStruct_stop_thread(CircStruct *self);

static PyObject *
CircStruct_getprefix(CircStruct *self, void *closure);

static PyObject *
CircStruct_getstreamName(CircStruct *self, void *closure);

static PyObject *
CircStruct_gethost(CircStruct *self, void *closure);

static PyObject *
CircStruct_getmulticast(CircStruct *self, void *closure);

static PyObject *
CircStruct_getport(CircStruct *self, void *closure);

static PyObject *
CircStruct_getthreadRunning(CircStruct *self, void *closure);

static PyObject *
CircStruct_getndim(CircStruct *self, void *closure);

static PyObject *
CircStruct_getdtype(CircStruct *self, void *closure);

static PyObject *
CircStruct_getsize(CircStruct *self, void *closure);

static int
CircStruct_cantset(CircStruct *self, PyObject *value, void *closure);

static PyObject *
CircStruct_getdecimation(CircStruct *self, void *closure);

static int
CircStruct_sethost(CircStruct *self, PyObject *value, void *closure);

static int
CircStruct_setmulticast(CircStruct *self, PyObject *value, void *closure);

static int
CircStruct_setport(CircStruct *self, PyObject *value, void *closure);

static PyObject *
CircStruct_getshape(CircStruct *self, void *closure);

static PyObject *
CircStruct_getcbdata(CircStruct *self, void *closure);

static PyObject *
CircStruct_getlatest(CircStruct *self, void *closure);

static int
CircStruct_setshape(CircStruct *self, PyObject *value, void *closure);

static PyObject *
CircStruct_name(CircStruct *self, PyObject *Py_UNUSED(ignored));
static PyObject *
CircStruct_address(CircStruct *self, PyObject *Py_UNUSED(ignored));

static PyObject *
CircStruct_use_tcp(CircStruct *self, PyObject *args);

static PyObject *
CircStruct_use_ipc(CircStruct *self, PyObject *args);

static PyObject *
CircStruct_use_epgm(CircStruct *self, PyObject *args);

static PyObject *
CircStruct_set_callback(CircStruct *self, PyObject *args);

static PyObject *
CircStruct_wait_for_cb(CircStruct *self, PyObject *args);

static PyObject *
CircStruct_stop_callback(CircStruct *self, PyObject *args);

static PyObject *
CircStruct_prepare_data(CircStruct *self, PyObject *args);

static PyObject *
CircStruct_get_data(CircStruct *self, PyObject *args);

static PyObject *
CircStruct_prepare_save(CircStruct *self, PyObject *args);

static PyObject *
CircStruct_start_save(CircStruct *self, PyObject *args);

static PyObject *
CircStruct_wait_for_save(CircStruct *self, PyObject *args);

/*

The CircSubscriber Class, used to subscribe to ZMQ SUB streams from the CircReader Class.

*/

static void
CircSubscriber_dealloc(CircSubscriber *self);

static PyObject *
CircSubscriber_new(PyTypeObject *type, PyObject *args, PyObject *kwargs);

static int
CircSubscriber_init(CircSubscriber *self, PyObject *args, PyObject *kwargs);

static int
CircSubscriber_setdecimation(CircSubscriber *self, PyObject *value, void *closure);

static PyObject *
CircSubscriber_start_thread(CircSubscriber *self);

static PyObject *
CircSubscriber_str(CircSubscriber *self);


/*

The CircReader Class, the main class to read the circular buffers.
Can return N values to Python, can signal for callbacks, can publish on a ZMQ PUB
and can save data to disk.

*/

static void
CircReader_dealloc(CircReader *self);

static PyObject *
CircReader_new(PyTypeObject *type, PyObject *args, PyObject *kwargs);

static int
CircReader_init(CircReader *self, PyObject *args, PyObject *kwargs);

static int
CircReader_setdecimation(CircReader *self, PyObject *value, void *closure);

static PyObject *
CircReader_start_thread(CircReader *self);

static PyObject *
CircReader_set_publish(CircReader *self, PyObject *args);

static PyObject *
CircReader_str(CircReader *self);

/*
    C functions
*/

int
get_stream_index(const char *value, int *index);

int
check_stream_name(const char *value);

void *
reader_thread(void *t_args);

void *
subscriber_thread(void *t_args);

inline int
open_shm(thread_struct *tstr);

inline int
get_next_frame(thread_struct *tstr);

inline int
get_info(thread_struct *tstr);

inline int
int2bin8(int a, char *buffer, int from);

inline int
send_data(thread_struct *tstr);

inline int
receive_data(thread_struct *tstr);

inline int
process_data(thread_struct *tstr);

inline int
copy_data(thread_struct *tstr);

inline int
callback_data(thread_struct *tstr);

inline int
save_each_data(void *arg);

inline int
save_N_data(void *arg);

inline int
save_block_data(void *arg);

inline int
reshape_cb(CircReader *self);

inline int
bind_zmq(CircReader *self);

inline int
connect_zmq(CircReader *self);

inline int
disconnect_zmq(CircReader *self);