
import setuptools
import numpy

DEBUG_BUILD = 0
DARC_DIR = "darc/"  # uses copies of darc files included here, allows building and installing without a supported darc installed

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name = "lark",
    version = "2022.08.29",
    author = "David Jenkins",
    author_email = "David.Jenkins@eso.org",
    description = "The Lark RTC Python package",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/david-jenkins/lark",
    project_urls = {
        "Bug Tracker" : "https://github.com/david-jenkins/lark/issues",
    },
    classifiers = [
        "Programming Language :: Python :: 3",
        "Operating System :: Linux",
    ],
    packages = setuptools.find_packages(where="."),
    package_dir = {"":"."},
    python_requires = ">=3.7",
    install_requires=[
          'numpy',
          'PyQt5',
          'pyqtgraph',
          'rpyc',
          'systemd-python',
          'matplotlib',
          'scipy',
          'astropy',
          'toml',
          'numa',
      ],
    dependency_links=['git+git://github.com/pyqtgraph/pyqtgraph.git@master'],
    entry_points = {
        "console_scripts": ["larkNames=lark.bin:larkNames",
                            "larkDaemon=lark.bin:larkDaemon",
                            "resetAll=lark.bin:resetAll",
                            "larkmagic=lark.bin:larkmagic",
                            "larkcontrol=lark.bin:larkcontrol",
                            "larkgui=lark.bin:larkgui",
                            "larklauncher=lark.bin:launcher",
                            "larkplot=lark.bin:larkplot",
                            "resetDaemon=lark.daemon:resetDaemon",
                            "laserpulse=lark.laserpulse:main"
                            ],
    },
    ext_modules=[
        setuptools.Extension("lark.ccirc",
                sources=["lark/ccircmodule.c"],
                depends=["lark/ccircmodule.h"],
                define_macros=[('DEBUG', DEBUG_BUILD)],
                libraries=['rt','zmq'],
                extra_objects=[DARC_DIR+"src/circ.o",DARC_DIR+"src/mutex.o"],
                include_dirs=[DARC_DIR+"include/",numpy.get_include()],
                ),
        setuptools.Extension("lark.cbuffer",
                sources=["lark/cbuffermodule.c"],
                depends=["lark/cbuffermodule.h"],
                define_macros=[('DEBUG', DEBUG_BUILD)],
                libraries=['rt'],
                extra_objects=[DARC_DIR+"src/buffer.o"],
                include_dirs=[DARC_DIR+"include/",numpy.get_include()],
                ),
        setuptools.Extension("lark.darc.utils",
                sources=["lark/darc/utils.c"],
                define_macros=[('DEBUG', DEBUG_BUILD)],
                libraries=['rt'],
                extra_objects=[DARC_DIR+"src/mutex.o"],
                include_dirs=[DARC_DIR+"include/",numpy.get_include()],
                ),
    ],
)


