
"""
This module provides base classes and helpers for creating plugin based services.
e.g. A soft real time system, or a diagnostic system. See canapylark for examples.
"""

from abc import ABC, abstractmethod, abstractproperty
from collections import ChainMap
import importlib
import threading
import time
from typing import Any

from .interface import startServiceClient, connectClient

class BasePlugin:
    """The base SrtcPlugin class, must be inherited.
    defaults and arg_desc should be defined in Init(self) for each function
    """
    defaults = {}
    arg_desc = {}
    _name = None
    def __init__(self):
        self.result = None
        self._temp = {}
        self._values = {}
        self.go = 1
        self.thread = None
        self.period = 1
        self.begin_on_start = False
        self.Init()
        self.values = ChainMap(self._temp,self._values,self.defaults)
        
    def __call__(self, _apply=False, **kwargs) -> Any:
        return self.run(_apply, **kwargs)

    def __getitem__(self, name):
        return self.values[name]

    def __setitem__(self, name, value):
        if name in self.defaults:
            self._values[name] = value
        else:
            self._temp[name]

    def run(self, _apply=False, **kwargs):
        self._temp.update(kwargs)
        self.Setup()
        self._run(_apply)
        self._temp.clear()
        return self.result
    
    def _run(self, _apply=False):
        self.Acquire()
        self.Execute()
        self.Check()
        self.Finalise()
        if _apply:
            self.Apply()
        self.store_result(self._name, self.result)
        
    def _thread_func(self, _apply):
        while self.go:
            self._run(_apply=_apply)
            time.sleep(self.period)
        
    def start(self, _period=1, _apply=False, **kwargs):
        self.period = _period
        self.go = 1
        if self.thread is not None:
            if self.thread.is_alive():
                return
        self._temp.update(kwargs)
        self.Setup()
        self.thread = threading.Thread(target=self._thread_func, args=(_apply,))
        self.thread.start()
        
    def stop(self):
        self.go = 0
        self._temp.clear()
        # if self.thread is not None:
        #     self.thread.join()
        #     self.thread = None

    def Values(self):
        return {key:value for key,value in self.values.items()}

    def Configure(self, **kwargs: Any):
        self._values.update({key:value for key,value in kwargs.items() if key in self.defaults})
        # for name, value in kwargs.items():
        #     if name in self.defaults:
        #         self._values[name] = value
        #     else:
        #         print(f"{name} not found")
        
    def Init(self):
        pass

    def Setup(self):
        pass

    def Acquire(self):
        pass

    def Execute(self):
        pass

    def Check(self):
        pass

    def Finalise(self):
        pass

    def Apply(self):
        pass

    def Types(self):
        return self.Configure.__annotations__

    def Result(self):
        return self.result

class NameConflictError(BaseException):
    """Raise for errors in adding functions due to the same name."""

class BaseService:
    @property
    @abstractmethod
    def PLUGINS(self):
        pass
    
    @property
    @abstractmethod
    def INITIALISED(self):
        pass

    @property
    @abstractmethod
    def RESULTS(self):
        pass

    @classmethod
    def store_result(cls,name,result):
        cls.RESULTS[name] = result

    @classmethod
    def register_plugin(cls, name):
        print(f"Registering plugin {name} to {cls}")
        if name in cls.PLUGINS.keys():
            raise NameConflictError(
                f"Plugin name conflict: '{name}'. Double check" \
                " that all plugins have unique names.")
        def plugin_wrapper(plugin_class):
            if hasattr(plugin_class, "run"):
                if callable(plugin_class.run):
                    plugin_class._name = name
                    plugin_class.store_result = cls.store_result
                    cls.PLUGINS[name] = plugin_class
                    print(f"setting self.PLUGINS[{name}] = {plugin_class}")
                    return plugin_class
            raise Exception("A plugin needs a callable run attribute")
        return plugin_wrapper

    def __init__(self, name):
        self.name = name
        for key in self.PLUGINS:
            try:
                iplug = self.PLUGINS[key]()
            except Exception as e:
                print(e)
            else:
                if iplug is not None:
                    self.INITIALISED[key] = iplug
                    self.RESULTS[key] = None
                    self.__setattr__(key, self.INITIALISED[key])

    # def __getattr__(self, name):
    #     if name in self.PLUGINS:
    #         obj = self.PLUGINS[name]()
    #         self.__setattr__(name, obj)
    #         return obj
    #     raise AttributeError(f"No attribute called {name}")

    def getResult(self,name=None):
        if name is not None:
            return self.RESULTS[name]
        else:
            return self.RESULTS

    def getPlugin(self,name=None):
        if name is not None:
            if name in self.INITIALISED:
                return self.INITIALISED[name]
            else:
                raise AttributeError(f"No function called {name}")
        else:
            return self.INITIALISED
            
    def Configure(self,**kwargs):
        for key,value in self.INITIALISED.items():
            local_kwargs = {name:arg for name,arg in kwargs.items() if name in value.defaults}
            value.Configure(**local_kwargs)
    
    def start(self):
        failed = []
        for key,obj in self.INITIALISED.items():
            if obj.begin_on_start:
                try:
                    obj.start()
                except Exception as e:
                    print(e)
                    failed.append(key)
        for key in failed:
            self.INITIALISED.pop(key)

    def stop(self):
        for key,value in self.INITIALISED.items():
            try:
                value.stop()
            except Exception as e:
                print(e)


# class RegisterPlugin(ABC):
#     PLUGINS = {}
#     def __init__(self, name):
#         """Register a plugin to the FUNCTIONS dict."""
#         self.name = name
#         # print("Registering plugin", name)
#         if name in self.PLUGINS.keys():
#             raise NameConflictError(
#                 f"Plugin name conflict: '{name}'. Double check" \
#                 " that all plugins have unique names.")
#         print(f"got name {name}")

#     def __call__(self, plugin_class):
#         if hasattr(plugin_class, "run"):
#             if callable(plugin_class.run):
#                 plugin_class._name = self.name
#                 self.PLUGINS[self.name] = plugin_class
#                 print(f"setting self.PLUGINS[{self.name}] = {plugin_class}")
#                 return plugin_class
#         raise Exception("A plugin needs a callable run attribute")