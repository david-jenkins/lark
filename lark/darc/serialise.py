#darc, the Durham Adaptive optics Real-time Controller.
#Copyright (C) 2010 Alastair Basden.

#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU Affero General Public License as
#published by the Free Software Foundation, either version 3 of the
#License, or (at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU Affero General Public License for more details.

#You should have received a copy of the GNU Affero General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.
#$Id: f2c53358ae53cd3331c66669ac3349a4c3c3ead0 $

"""The DFB serialise library, modified by AGB for improved
functionality.  This module allows efficient serialising of large
arrays (and other data) so that they can be send efficiently over a
socket (or stored in a file), rather like pickle, but with greater
efficiency (most arrays are sent direct, without converting to a
string). """

# Python implementation of functions to read and write serialised data
#import Numeric
import types, os, pickle,numpy
import select
from functools import reduce
if "OS" in os.environ and os.environ["OS"]=="Windows_NT":
    WINDOZE=1
else:
    WINDOZE=0
Tuple = 'TUPLE_TYPE'
Char = 'CHAR_TYPE'
translate = [#currently no more that 128 (was 16) different types allowed (was 8).
    bytes,
    str,
    "b",#numpy.int8,
    "h",#numpy.int16,
    "i",#numpy.int32,
    None,
    "f",#numpy.float32,
    "d",#numpy.float64,
    tuple,
    dict,#added by agb
    int,#added by agb
    float,#added by agb
    list,#added by agb
    "Pickled",#added by agb
    'l',#added by agb
    'D',#added by agb
    'L',#added by agb
    'F',#added by agb
    'I',#added by agb
    'H',#added by agb
    numpy.float32#added by agb - for single float32 values... (ie not arrays)
]

def Deserialise(string, start = None, end = None):
    """Deserialise data obtained back into its original form
    @param string: The string to be deserialised
    @type string: String
    @param start: Starting point
    @type start: Int or None
    @param end: Ending point
    @type end: Int or None
    @return: The data
    @rtype: List
    """
    if (start == None): start = 0
    if (end == None): end = len(string)
    self = []
    while(start < end):
        typ, endian, length = DecodeHeader(string[start:])
        start = start + 5
        if (typ == tuple):
            data = tuple(Deserialise(string, start, start + length))
        elif typ==list:
            data=Deserialise(string,start,start+length)
        elif (typ==dict):#added by agb
            d = Deserialise(string,start, start+length)
            #list of form [key,data,key,data,...]
            data={}
            while len(d)>0:
                key=d.pop(0)
                val=d.pop(0)
                if type(key)==numpy.ndarray:#key must be int or string.
                    key=key[0]
                data[key]=val
        elif (typ == str):
            if (string[start+length-1] == "\0"):
                data = string[start:start + length - 1]
            else:
                data = string[start:start + length]
        elif (typ == bytes):
            if (string[start+length-1] == 0):
                data = string[start:start + length - 1]
            else:
                data = string[start:start + length]
        elif typ==float:
            data=numpy.fromstring(string[start:start+length],numpy.float64)
            if endian!=numpy.little_endian:
                data=float(data.byteswap()[0])
            else:
                data=float(data[0])
        elif typ==int:
            data=numpy.fromstring(string[start:start+length],numpy.int32)
            if endian!=numpy.little_endian:
                data=int(data.byteswap()[0])
            else:
                data=int(data[0])
        elif typ==None:
            data=None
        elif typ==numpy.float32:
            data=numpy.fromstring(string[start:start+length],numpy.float32)
            if endian!=numpy.little_endian:
                data=data.byteswap()[0]
            else:
                data=data[0]
        elif typ=="Pickled":#agb
            if string[start+length-1]=="\0":
                data=string[start:start+length-1]
            else:
                data=string[start:start+length]
            data=pickle.loads(data)
        else:
            #print "deserialise numpy"
            shapelen=numpy.fromstring(string[start:start+4],numpy.int32)
            if endian!=numpy.little_endian:
                shapelen=shapelen.byteswap()
            shapelen=shapelen[0]*4
            shape=numpy.fromstring(string[start+4:start+4+shapelen],numpy.int32)
            if endian!=numpy.little_endian:
                shape=tuple(shape.byteswap())
            else:
                shape=tuple(shape)
            data =numpy.fromstring(string[start+4+shapelen:start+length],typ)
            if endian != numpy.little_endian:
                data = data.byteswap()
            data.shape=shape#=Numeric.reshape(data,shape)
        self.append(data)
        start = start + length
    return(self)


def ReadMessage(infile):
    """Read the next serialised entity (most likely a tuple) from a file/socket
    and return it deserialised.
    Returns None if there is no data but will raise an exception if there
    is a finite but insufficient amount of data
    @param infile: File with a read method.
    @type infile: Object
    @return: The data
    @rtype: List
    """
    if WINDOZE and type(infile)!=type(0):
        header=infile.recv(5)
    else:
        if type(infile)!=type(0):
            infile=infile.fileno()
        header = os.read(infile, 5)#this may need changing for windows... using infile.recv...
    headerSize = len(header)
    if headerSize == 0:
        return None
    if headerSize != 5:
        raise IOError("Serial packet header only %d bytes long" \
              % headerSize) 
    typ, endian, length = DecodeHeader(header)
    readlength = 0
    body = ''
    while readlength < length:
        if WINDOZE and type(infile)!=type(0):
            infile.settimeout(None)
            infile.setblocking(1)
            #print "recv (%d)"%len(body)
            try:
                body+= infile.recv(min(length-readlength,8192))
            except socket.error as msg:
                errno,string=msg
                if errno==10035:
                    pass
                else:
                    print("socket.error",msg)
                    raise
            except:
                print("serialise.ReadMessageerror in recv")
                raise
        else:
            body+=os.read(infile, length-readlength)
        readlength = len(body)
        #print "serialise readlength:",readlength
    # Strip off extra tupling because we know it's a singleton
    return Deserialise(header+body)[0]

def DecodeHeader(string):
    """Decode the header of the string
    @param string: Serialised string
    @type string: String
    @return: Type, endian and length
    @rtype: Tuple
    """
    byte = ord(string[0])
    length = (  (ord(string[1]) << 24)
              | (ord(string[2]) << 16)
              | (ord(string[3]) << 8)
              | (ord(string[4])))
    endian = byte & 1
    type = (byte >> 1) & 0x7f#agb - this causes problems...
    type = translate[type]
    return(type, endian, length)

def Serialise(value):
    """Serialise a value
    @param value: The data to be serialised
    @type value: User defined
    @return: Serialised value
    @rtype: String
    """
    thisType = type(value)
    if thisType == int:
        value = numpy.array(value, numpy.int32)#"i"
    elif thisType == float:
        value = numpy.array(value, numpy.float64)#"d"
    #elif thisType==Numeric.ArrayType:#THIS SHOULD SAY NUMERIC not numpy.
    #    value=numpy.array(value,copy=0)
    #    thisType=type(value)
    #thisType = type(value)
    
    if thisType in [numpy.ndarray,numpy.memmap]:#Numeric.ArrayType
        #print "serialise numpy1",value.dtype
        try:
            headerByte=translate.index(value.dtype.char)#typecode())
        except:#see at start of this file for allowed data types...
            print("Datatype %s of array not known in serialise - conversion will fail - converting to byte."%str(value.dtype.char))
            value=value.view("b")
            headerByte=translate.index(value.dtyp.char)
        stringValue=numpy.array(len(value.shape),numpy.int32).tobytes()
        stringValue+=numpy.array(value.shape,numpy.int32).tobytes()
        stringValue+= value.tobytes()
    elif thisType==int:#added by agb
        headerByte=translate.index(int)
        stringValue=value.tobytes()
    elif thisType==float:#added by agb
        headerByte=translate.index(float)
        stringValue=value.tobytes()
    elif thisType == bytes:
        headerByte=translate.index(thisType)
        stringValue = value + b'\0'
    elif thisType == str:
        headerByte=translate.index(thisType)
        stringValue = value + '\0'
    elif thisType == tuple:
        headerByte=translate.index(tuple)
        stringValue = ''
        for element in value:
            stringValue = stringValue + Serialise(element)
    elif thisType == list:#added by agb
        headerByte=translate.index(list)
        stringValue = ''
        for element in value:
            stringValue = stringValue + Serialise(element)
    elif thisType == dict:#added by agb
        headerByte=translate.index(dict)
        stringValue=''
        for key in value:
            stringValue = stringValue + Serialise(key)+Serialise(value[key])
    elif thisType==type(None):#added by agb
        headerByte=translate.index(None)
        stringValue=''
    elif thisType==numpy.float32:
        headerByte=translate.index(numpy.float32)
        stringValue=value.tobytes()
    elif thisType==type(numpy.empty((1,)).astype("i")[0]):#fix for platforms where l==i (32 bit)
        headerByte=translate.index(int)
        stringValue=value.tobytes()
    else: #added by agb:
        print("WARNING: serialise pickling object with type %s (could be inefficient)"%type(value))
        stringValue=pickle.dumps(value)+'\0'
        headerByte=translate.index("Pickled")
    #else:#added by agb
    #    print "SERIALISE FAILED - unrecognised type:",thisType
    #    raise "SERIALISE ERROR"
    headerByte = (headerByte << 1) | numpy.little_endian#Numeric.LittleEndian
    length = numpy.array(len(stringValue), numpy.int32)
    if numpy.little_endian: length=length.byteswap()
    return chr(headerByte)+length.tobytes().deocde()+stringValue

def SerialiseToList(value,sendList=[]):
    """Puts serialised data into a list which should then be sent over a
    socket.  This reduces the overhead by not copying
    numeric arrays into a string.  This should reduce overhead for large
    numeric arrays.
    @param value:  Value to be serialised
    @type value: User defined
    @param sendList: List to be sent
    @type sendList: List of arrays and strings
    @return: The length of the list
    @rtype: Int
    """
    thisType = type(value)
    if thisType in [int,numpy.int32,type(numpy.array([0]).astype("i").view("i")[0])]:
        value = numpy.array(value, numpy.int32).tobytes().decode()#"i"
    elif thisType in [float,numpy.float64]:
        value = numpy.array(value, numpy.float64).tobytes().decode()#"d"
    elif thisType==numpy.float32:
        value = value.tobytes().deocde()
    #elif thisType==Numeric.ArrayType:#THIS SHOULD SAY NUMERIC not numpy.
    #    value=numpy.array(value,copy=0)
    #    thisType=type(value)

    #thisType = type(value)
    length=None
    hdr=None
    ending=None
    hdrSize=5
    if thisType in [numpy.ndarray,numpy.memmap]:
        #print "serialise numpy",value.dtype,translate.index(value.dtype),value.dtype==numpy.float64
        try:
            headerByte=translate.index(value.dtype.char)#code())
        except:
            print("util.serialise - headerByte unknown '%s' converting to b"%value.dtype.char)
            value=value.view("b")
            headerByte=translate.index(value.dtype.char)#code())
        hdr=numpy.array(len(value.shape),numpy.int32).tobytes()
        hdr+=numpy.array(value.shape,numpy.int32).tobytes()
        if len(value.shape)==0:
            length=value.itemsize
        else:
            length=reduce(lambda x,y:x*y,value.shape)*value.itemsize
        length+=len(hdr)
        #if not value.flags.contiguous:#make contiguous so can be sent...
        #    value=numpy.array(value)
        value=value.ravel().view('b')#convert to a byte format...
        #print headerByte,hdr
    elif thisType in [int,numpy.int32,type(numpy.array([0]).astype("i").view("i")[0])]:#added by agb - the last one is necessary for 32 bit machines where numpy screws up...
        headerByte=translate.index(int)
        length=len(value)#value.itemsize
    elif thisType in [float,numpy.float64]:#added by agb
        headerByte=translate.index(float)
        length=len(value)#value.itemsize
    elif thisType==numpy.float32:
        headerByte=translate.index(numpy.float32)
        length=len(value)
    elif thisType == bytes:
        headerByte=translate.index(thisType)
        ending=['\0']#need to send value+'\0'
        length = len(value)+1
    elif thisType == str:
        headerByte=translate.index(thisType)
        ending=['\0']#need to send value+'\0'
        length = len(value)+1
    elif thisType == tuple:
        headerByte=translate.index(tuple)
        ending=[]
        length=0
        for element in value:
            length+=SerialiseToList(element,ending)+hdrSize
    elif thisType == list:#added by agb
        headerByte=translate.index(list)
        ending=[]
        length=0
        for element in value:
            length+=SerialiseToList(element,ending)+hdrSize
        
    elif thisType == dict:#added by agb
        headerByte=translate.index(dict)
        ending=[]
        length=0
        for key in value:
            length+=SerialiseToList(key,ending)+hdrSize
            length+=SerialiseToList(value[key],ending)+hdrSize
    elif thisType==type(None):#added by agb
        headerByte=translate.index(None)
        ending=[]
        length=0
    else:#added by agb:
        print("WARNING: serialiseToList pickling object with type %s (could be inefficient) %s"%(type(value),str(value)))
        value=pickle.dumps(value)
        headerByte=translate.index("Pickled")
        length=len(value)+1
        ending=['\0']
    #else:#added by agb
    #    print "SERIALISE FAILED - unrecognised type:",thisType
    #    raise Exception("SERIALISE ERROR")
    headerByte = (headerByte << 1) | numpy.little_endian
    lngth=numpy.array(length,numpy.int32)
    if numpy.little_endian: lngth=lngth.byteswap()
    txt=chr(headerByte)+lngth.tobytes().decode()
    if hdr!=None:
        txt+=hdr
    if len(sendList)>0 and type(sendList[-1])==bytes:
        sendList[-1]+=txt.encode()
    else:
        sendList.append(txt)
    if type(value) not in [list,dict,tuple]:
        if type(value)==bytes and len(sendList)>0 and type(sendList[-1])==bytes:
            sendList[-1]+=value
        elif type(value)!=type(None):
            sendList.append(value)
    if ending!=None:
        for t in ending:
            if type(t)==bytes and len(sendList)>0 and type(sendList[-1])==bytes:
                sendList[-1]+=t
            else:
                sendList.append(t)
        #sendList+=ending
    return length

def Send(value,sock,verbose=0):
    """Send a message/value over a socket.
    @param value: Data to be sent
    @type value: User defined
    @param sock: Socket
    @type sock: socket.socket instance
    @param verbose: Flag, whether to print messages
    @type verbose: Int
    """
    l=[]
    SerialiseToList(value,l)
    #print "sertolist"
    #print l,len(l)
    for v in l:
        if verbose==1:
            if type(v)==bytes:
                print(v)
            elif type(v)==numpy.ndarray:#Numeric.ArrayType:
                print("numpy array, shape",v.shape)
            else:
                print("Type unknown",type(v))
        if sock!=None:
            try:
                sock.sendall(v)
            except:
                print("Error - sock.sendall failed - couldn't send serialised data")
                raise

def Recv(sock,data):
    """Receive non-blocking from a socket... adding the result to data.  Then return (data,valid) with valid==1 if the data is a complete message ready for deserialisation.
    """
    if data==None:
        data=""
    #print "serialise.Recv datalen=%d"%len(data)
    datawaiting=1
    while datawaiting:
        rtr,rtw,err=select.select([sock],[],[],0.)
        if len(rtr)>0:#sock has some data...
            dlen=len(data)
            if dlen<5:
                length=5#get the 5 byte header first...
            else:
                length=5+DecodeHeader(data[:5])[2]
            if dlen==length:
                datawaiting=0
            else:
                newdata=sock.recv(length-dlen)
                if len(newdata)==0:#nothing received - must be error...
                    print("sock.recv didn't - datalen: %d left %d"%(dlen,length-dlen))
                    raise Exception("Failed to receive data")
                data+=newdata
        else:
            datawaiting=0
    #now see if the data is complete:
    dlen=len(data)
    if dlen>=5 and dlen==5+DecodeHeader(data[:5])[2]:
        valid=1
    else:
        valid=0
    #print "done Recv, len %d, valid=%d"%(len(data),valid)
    return data,valid


if __name__ == "__main__":
    """Testing function"""
    import sys
    option = sys.argv[1]
    fileName = sys.argv[2]
    if option == 'w':
        file = open(fileName, 'w')
        file.write(Serialise(["python test first part!",
                              #Numeric.array([1.2345678,3.45,4.5], Numeric.Float32),
                              numpy.array([[1,2,3],[4,5,6]], numpy.int16),
                              numpy.array(99,numpy.int32),
                              ("inner string", 0x12345), 12345.6789]))
        file.write(Serialise(["python test second part!", "the end"]))
    else:
        file = open(fileName, 'r')
        while 1:
            a = ReadMessage(file.fileno())
            if a is None: break
            print(a)
