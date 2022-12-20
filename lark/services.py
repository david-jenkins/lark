
"""
This module provides base classes and helpers for creating plugin based services.
e.g. A soft real time system, or a diagnostic system. See canapylark for examples.
"""

from abc import ABC, abstractmethod, abstractproperty
from collections import ChainMap
import copy
import importlib
import threading
import time
import traceback
from typing import Any
import warnings
from lark.interface import startServiceClient, connectClient, CopyDict

class BasePlugin:
    """The base SrtcPlugin class, must be inherited.
    defaults and arg_desc should be defined in Init(self) for each function
    """
    parameters = ()
    arg_desc = {}
    def __init__(self, name:str, parameter_store:dict, result_store:dict):
        self._name = name
        self._parameter_store = parameter_store
        self._result_store = result_store
        self._result = None
        self._temp = {}
        self._go = 1
        self._thread = None
        self._defaults = {name:self.__getattribute__(name) for name in self.parameters}
        self._values = ChainMap(self._temp,self._parameter_store,self._defaults)

        self.loop_period = 1
        self.auto_run_once = False
        self.auto_start = False
        self.Init()
        
    def __call__(self, _apply=False, **kwargs) -> Any:
        return self.run(_apply, **kwargs)

    def __getitem__(self, name):
        if name in self.parameters:
            return self._values[name]
        else:
            raise KeyError

    def __setitem__(self, name, value):
        if name in self.parameters:
            self._parameter_store[name] = value
        else:
            raise KeyError

    def run(self, _apply=False, **kwargs):
        self._temp.update(kwargs)
        self.Setup()
        self._run(_apply)
        self._temp.clear()
        return self.Result
    
    def _run(self, _apply=False):
        self.Acquire()
        self.Execute()
        self.Check()
        self.Finalise()
        if _apply:
            self.Apply()
        self._result_store[self._name] = self.Result
        
    def _thread_func(self, _apply):
        while self._go:
            self._run(_apply=_apply)
            time.sleep(self.loop_period)
        
    def start(self, period=1, apply=False, **kwargs):
        self.loop_period = period
        self._go = 1
        if self._thread is not None:
            if self._thread.is_alive():
                return
        self._temp.update(kwargs)
        self.Setup()
        self._thread = threading.Thread(target=self._thread_func, args=(apply,))
        self._thread.start()
        
    def stop(self):
        self._go = 0
        self._temp.clear()
        # if self.thread is not None:
        #     self.thread.join()
        #     self.thread = None

    @property
    def Values(self):
        return {key:self._values[key] for key in self.parameters}

    def Configure(self, **kwargs: Any):
        for name in kwargs:
            if name not in self.parameters:
                warnings.warn(f"Not setting parameter {name}")
        self._parameter_store.update({key:value for key,value in kwargs.items() if key in self.parameters})
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

    @property
    def Types(self):
        return self.__annotations__

    @property
    def Result(self):
        return self._result
        
    @Result.setter
    def Result(self, value):
        self._result = value
    
    @property
    def Name(self):
        return self._name

class NameConflictError(BaseException):
    """Raise for errors in adding functions due to the same name."""

class BaseService:
    @property
    @abstractmethod
    def PLUGINS(self):
        pass

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
                    cls.PLUGINS[name] = plugin_class
                    print(f"setting self.PLUGINS[{name}] = {plugin_class}")
                    return plugin_class
            raise Exception("A plugin needs a callable run attribute")
        return plugin_wrapper

    def __init__(self, name, parameters={}):
        self.name = name
        self.initialised = {}
        self.results = {}
        self.parameters = {}
        self.parameters.update(parameters)
        for key in self.PLUGINS:
            try:
                iplug = self.PLUGINS[key](key, self.parameters, self.results)
            except Exception as e:
                print(e)
            else:
                if iplug is not None:
                    self.initialised[key] = iplug
                    self.results[key] = None

    def __getattr__(self, __name: str) -> Any:
        try:
            return self.initialised[__name]
        except KeyError:
            return super().__getattr__(__name)

    # def __getattr__(self, name):
    #     if name in self.PLUGINS:
    #         obj = self.PLUGINS[name]()
    #         self.__setattr__(name, obj)
    #         return obj
    #     raise AttributeError(f"No attribute called {name}")

    def getResult(self,name=None):
        if name is not None:
            return self.results[name]
        else:
            return self.results

    def getPlugin(self,name=None):
        if name is not None:
            if name in self.initialised:
                return self.initialised[name]
            else:
                raise AttributeError(f"No function called {name}")
        else:
            return self.initialised
            
    def getParameters(self):
        return self.parameters
            
    def Configure(self, **kwargs):
        print(f"Called Configure on {self.name}")
        print(kwargs)
        print(type(kwargs))
        # kwargs = copy.deepcopy(kwargs)
        for key,value in kwargs.items():
            print(key, type(value))
        self.parameters.update(kwargs)
        # for key,value in self.initialised.items():
        #     local_kwargs = {name:arg for name,arg in kwargs.items() if name in value.defaults}
        #     value.Configure(**local_kwargs)

    def start(self):
        failed = []
        for key,obj in self.initialised.items():
            obj:BasePlugin
            if obj.auto_start:
                try:
                    obj.start()
                except Exception as e:
                    print(e)
                    failed.append(key)
            elif obj.auto_run_once:
                try:
                    obj.run()
                except Exception as e:
                    print(e)
                    failed.append(key)
        for key in failed:
            self.initialised.pop(key)

    def stop(self):
        for key,value in self.initialised.items():
            value:BasePlugin
            try:
                value.stop()
            except Exception as ex:
                print(ex)
                traceback.print_exception(type(ex), ex, ex.__traceback__)


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
