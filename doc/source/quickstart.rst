Get Started
============

Installing Lark
------------------

Lark is available from here https://github.com/david-jenkins/lark. It can either be installed to run darc or installed as a client only to control lark/darc remotely. 

Installing Lark to run DARC
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If you are using Lark to control darc you must first install darc, see :ref:`installing_darc`.

The standard way of installing lark involves creating a directory at /opt/lark and creating a Python virtual environment that lives there. The Lark Makefile includes commands for building a compatible version of Python from source, creating the directory structure and then making a Python virtual environment called pylark at /opt/lark. Lark should then be installed in this virtual environment, the /opt/lark directory is read/write/execute enabled for a group called lark so that all users added to the group can use the pylark virtual environment to run Lark. This was implemented for older systems that can't install Python >3.8 through the usual means but without replacing the system Python.

The /opt/lark dir is also used as the default place to store data.

Lark currently has helpers for installing on 3 operating systems, Centos7.5, Ubuntu1804 and Fedora34. These are commands in the Makefile, either run the one that fits your system or adapt for your Linux OS.

Next run make group_dir_setup which is used to create the lark group, add the current user, make /opt/lark, and update it's permissions. See the command in the Makefile for the full functionality.

If your system doesn't have Python >3.8 installed there is a command to build either Python 3.8 or 3.10 from source and do an alternative install, this installs the Python interpreter to the system but doesn't add it to the path so it won't mess with the system python. These commands are make python38 or make python310. There are other commands, python38_all and python310_all which will run group_dir_setup and then also create the virtual environment pylark at /opt/lark. These commands result in a working Python virtual environment that can be activated by running, source /opt/lark/pylark/bin/activate.

The last step is to install the Lark Python package itself, this is done by running pip install . when inside the lark directory. This should be done after activating the pylark virtual environment.

Installing Client Lark
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To use lark simply as a client, you can simply install the Python package to a Python version >3.8 using ``pip install .`` . *THIS NEEDS TESTING*.

.. _installing_darc:
Installing DARC
----------------

Get darc from here gitlink, and first install system dependencies using one of the named OS commands eg. ubuntu1804 in the Makefile. The run make install.

Running Lark
------------

There are a number of commands that are installed with lark.

+------------------------+-------------+------------+
| Command                | Arguments   | Description|
+========================+=============+============+
| larkcontrol            | column 2    | column 3   |
+------------------------+-------------+------------+
| body row 2             | ...         | ...        |
+------------------------+-------------+------------+


