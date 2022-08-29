Progress
========

Lark has a daemon process that runs in the background and starts darc, larkcontrol and custom services.
The custom services can be either soft real time processes or diagnostic processes.
Starting darc and larkcontrol is pretty fleshed out and should be finalised soon.
Starting services is not yet complete.
The custom services need to be defined in an importable package/module, they should inherit from the class
in lark.services. Then they can be pickled and sent to the daemon to launch.
Do I keep the plugin architecture?
Yes but it needs some tweaking, there should NOT be seperate SRTC and diag base classes.
There should be a single base class that gets inherited by the SRTC and diag specific classes.
This base class can have the plugin stuff. It's important that the processes are started in seperate processes
or interpretors as this will allow the plugin system to work. Or I modify the plugin system so instead of
registering a plugin to the module, it registers it directly to the class... perhaps a class method can be a decorator?
