
"""Stubs for the cbuffermodule C extension
defines the api in a Python readable way"""


from typing import Any, Dict


class cParamBuf:
    """The base c extension class for the darc ParamBuf"""
    @property
    def _buf_prefix(self) -> str: ...
    @property
    def _active(self) -> int: """Get the index of the active buffer"""
    @_active.setter
    def _active(self, value:int): """Set the active buffer, do a buffer swap if the buffer changes"""
    @property
    def _inactive(self) -> int: """Get the index of the inactive buffer"""
    @_inactive.setter
    def _inactive(self,value:int): """Set the inactive buffer, do a buffer swap if the buffer changes"""
    def __init__(self,prefix:str,numa:int=-1): """Open a CParamBuff with prefix=prefix, if numa is not -1 then it opens numa buffer index=numa"""
    def _get(self,name:str,inactive:int=0) -> Any: """Get a value from the active(inactive if inactive==1) buffer"""
    def _getN(self,names:list,inactive:int=0) -> Dict[str,Any]: """Get values from the active(inactive if inactive==1) buffer"""
    def _set(self): """Set a value in the active buffer, it will block until the buffer is not being used."""
    def _setN(self,name:str,value:Any,active:int=0): """Set a value in the inactive(active if active==1) buffer"""
    def _setToBuf(self,name:str,value:Any,index:int): """Set a value in buffer with index=index"""
    def _setN(self,values:dict[str:Any],active:int=0): """Set values in the inactive(active if active==1) buffer"""
    def _setNToBuf(self,values:dict[str:Any],index:int=0): """Set values in buffer with index=index"""
    def switchBuffer(self): """Switch the buffer"""
    def copy_to_inactive(self): """Copy the contents of the active buffer to the inactive one"""
    def _switchonframe(self,frameno:int): """Experimental method to cause a buffer swap to happen on a specific frame number"""
    def _getnames(self): """Get a list of the current keys of the active buffer"""
    
class BufferError(Exception):
    """A cParamBuf specific Exception"""