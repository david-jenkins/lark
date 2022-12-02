
BUILDDIR=/tmp/djenkins/build
LARK_DIR=/opt/lark
VENV_NAME=pylark
LARK_VENV=$(LARK_DIR)/$(VENV_NAME)/bin/activate
export

canapy: centos75 python310_c75

latte: ubuntu1804 python310_all _venv_notification

install: larkinstall-venv system
	$(MAKE) -C services install
	$(MAKE) -C system/centos-cfg install

build: lark/ccircmodule.c lark/ccircmodule.h lark/cbuffermodule.c lark/cbuffermodule.h
	$(MAKE) -C darc all
	python3 setup.py build_ext --inplace

larkinstall-venv: build
	. $(LARK_VENV) && pip install -e .

larkuninstall-venv:
	. $(LARK_VENV) && pip uninstall lark

system: group_dir_setup
	test -f /etc/lark.cfg && sudo mv /etc/lark.cfg /etc/lark.cfg.old
	sudo bash -c "echo 'LARK_DIR = \"$(LARK_DIR)\"' > /etc/lark.cfg"

centos75:
	sudo yum -y install epel-release
	sudo yum -y install openssl11 openssl11-devel openssl-libs openssl11-static
	sudo yum -y groupinstall "Development Tools"
	sudo yum -y install zsh git yum-utils git gcc fftw3-devel gsl-devel numactl-devel numactl-libs libpng-devel openssl-devel bzip2-devel libffi-devel tcl tcl-devel tkinter tk tk-devel readline readline-devel gdbm gdbm-devel uuid-devel libuuid-devel sqlite-devel systemd-devel czmq-devel zeromq-devel
	sudo yum-builddep python3
	test -d $(BUILDDIR) || mkdir $(BUILDDIR)
	cd $(BUILDDIR) && wget http://vault.centos.org/7.6.1810/os/x86_64/Packages/freetype-2.8-12.el7.x86_64.rpm
	cd $(BUILDDIR) && wget http://vault.centos.org/7.6.1810/os/x86_64/Packages/freetype-devel-2.8-12.el7.x86_64.rpm
	cd $(BUILDDIR) && sudo yum localinstall freetype-2.8-12.el7.x86_64.rpm freetype-devel-2.8-12.el7.x86_64.rpm
	cd $(BUILDDIR) && rm -f freetype-2.8-12.el7.x86_64.rpm && rm -f freetype-devel-2.8-12.el7.x86_64.rpm

ubuntu1804:
	sudo sed -i '0,/^# deb-src/{s/^# deb-src/deb-src/}' /etc/apt/sources.list
	sudo apt -y update
	sudo apt -y build-dep python3
	sudo apt -y install pkg-config
	sudo apt -y install libxcb-xinerama0
	sudo apt -y install build-essential gdb lcov pkg-config libbz2-dev libffi-dev libgdbm-dev libgdbm-compat-dev liblzma-dev libncurses5-dev libreadline6-dev libsqlite3-dev libssl-dev lzma lzma-dev tk-dev uuid-dev zlib1g-dev
	sudo apt -y install zsh git openssh-server libfftw3-3 libfftw3-dev gsl-bin libgsl-dev libnuma-dev python3-distutils python3-numpy python3-dev libczmq-dev libsystemd-dev

fedora34:
	sudo dnf -y install epel-release
	sudo dnf -y install openssl11 openssl11-devel openssl-libs openssl11-static
	sudo dnf -y groupinstall "Development Tools"
	sudo dnf -y install dnf-plugins-core git gcc fftw3-devel gsl-devel numactl-devel numactl-libs libpng-devel openssl-devel bzip2-devel libffi-devel tcl tcl-devel tkinter tk tk-devel readline readline-devel gdbm gdbm-devel uuid-devel libuuid-devel sqlite-devel systemd-devel czmq-devel zeromq-devel
	sudo dnf builddep python3

group_dir_setup:
	sudo groupadd lark || echo "group 'lark' already exists"
	sudo usermod -a -G lark $(USER)
	test -d $(LARK_DIR) || sudo mkdir $(LARK_DIR)
	sudo chmod g+rwxs,a+rwX $(LARK_DIR)
	test -f $(LARK_DIR)/lark.cfg && sudo mv $(LARK_DIR)/lark.cfg $(LARK_DIR)/lark.cfg.old
	sudo ln -sr conf/lark.cfg $(LARK_DIR)/lark.cfg
	# sudo cp conf/lark.cfg $(LARK_DIR)/
	# sudo chmod g+rw $(LARK_DIR)/lark.cfg
	test -d $(LARK_DIR)/log || sudo mkdir $(LARK_DIR)/log
	test -d $(LARK_DIR)/log/lark || sudo mkdir $(LARK_DIR)/log/lark
	sudo chmod -R u+rwX,g+rwX,o+w $(LARK_DIR)/log
	sudo chgrp -R lark $(LARK_DIR)

_python_venv: group_dir_setup
	cd $(LARK_DIR) && /usr/local/bin/python$(SHORT_VER) -m venv $(VENV_NAME)
	. $(LARK_VENV) && pip install --upgrade pip
	. $(LARK_VENV) && pip install -r requirements.txt

_python:
	test -d $(BUILDDIR) || mkdir -p $(BUILDDIR)
	cd $(BUILDDIR) && wget https://www.python.org/ftp/python/$(LONG_VER)/Python-$(LONG_VER).tgz
	cd $(BUILDDIR) && tar -xzvf Python-$(LONG_VER).tgz
	cd $(BUILDDIR)/Python-$(LONG_VER) && ./configure --with-ensurepip=install
	cd $(BUILDDIR)/Python-$(LONG_VER) && make -j 8 && sudo make altinstall

_venv_notification:
	@echo "Before continuing with Lark install, please source the virtual environment"
	@echo "source $(LARK_VENV)"

python38: LONG_VER=3.8.8
python38: SHORT_VER=3.8
python38: _python

python38_all: LONG_VER=3.8.8
python38_all: SHORT_VER=3.8
python38_all: _python _python_venv

python310: LONG_VER=3.10.5
python310: SHORT_VER=3.10
python310: _python

python310_all: LONG_VER=3.10.5
python310_all: SHORT_VER=3.10
python310_all: _python _python_venv
	

_python_c75:
	test -d $(BUILDDIR) || mkdir $(BUILDDIR)
	cd $(BUILDDIR) && wget https://www.python.org/ftp/python/$(LONG_VER)/Python-$(LONG_VER).tgz
	cd $(BUILDDIR) && tar -xzvf Python-$(LONG_VER).tgz
	cd $(BUILDDIR)/Python-$(LONG_VER) && sed -i 's/PKG_CONFIG openssl /PKG_CONFIG openssl11 /g' configure
	cd $(BUILDDIR)/Python-$(LONG_VER) && ./configure --with-ensurepip=install
	cd $(BUILDDIR)/Python-$(LONG_VER) && make -j 8 && sudo make altinstall

python310_c75: LONG_VER=3.10.5
python310_c75: SHORT_VER=3.10
python310_c75: _python_c75 _python_venv

clean:
	$(MAKE) -C darc clean
	$(MAKE) -C doc clean || echo "Sphinx clean failed"
	rm -rf $(BUILDDIR)
	rm -rf lark/*.so
	rm -rf lark/darc/*.so
	rm -rf dist

# TOPTARGETS := all clean

# SUBDIRS := $(wildcard */.)

# $(TOPTARGETS): $(SUBDIRS)
# $(SUBDIRS):
#         $(MAKE) -C $@ $(MAKECMDGOALS)

# .PHONY: $(TOPTARGETS) $(SUBDIRS)



# python310_c75:
# 	test -d $(BUILDDIR) || mkdir $(BUILDDIR)
# 	cd $(BUILDDIR) && wget https://www.python.org/ftp/python/3.10.5/Python-3.10.5.tgz
# 	cd $(BUILDDIR) && tar -xzvf Python-3.10.5.tgz && rm -f Python-3.10.5.tgz
# 	cd $(BUILDDIR)/Python-3.10.5 && sed -i 's/PKG_CONFIG openssl /PKG_CONFIG openssl11 /g' configure
# 	cd $(BUILDDIR)/Python-3.10.5 && ./configure --with-ensurepip=install
# 	cd $(BUILDDIR)/Python-3.10.5 && make -j 8
# 	cd $(BUILDDIR)/Python-3.10.5 && sudo make altinstall
# 	sudo rm -f /usr/bin/python3
# 	sudo rm -f /usr/local/bin/python3
# 	sudo ln -s /usr/local/bin/python3.10 /usr/local/bin/python3
# 	sudo ln -s /usr/local/bin/python3 /usr/bin/python3


# pylark:
# 	sudo mkdir /opt/lark
# 	sudo chmod -R a+rwx /opt/lark
# 	cd /opt/lark && python3 -m venv pylark
# 	. /opt/lark/pylark/bin/activate && pip install --upgrade pip
# 	. /opt/lark/pylark/bin/activate && pip install -r requirements.txt

# python310:
# 	test -d $(BUILDDIR) || mkdir $(BUILDDIR)
# 	cd $(BUILDDIR) && wget https://www.python.org/ftp/python/3.10.5/Python-3.10.5.tgz
# 	cd $(BUILDDIR) && tar -xzvf Python-3.10.5.tgz && rm -f Python-3.10.5.tgz
# 	cd $(BUILDDIR)/Python-3.10.5 && ./configure --with-ensurepip=install
# 	cd $(BUILDDIR)/Python-3.10.5 && make -j 8
# 	cd $(BUILDDIR)/Python-3.10.5 && sudo make altinstall
# 	sudo mkdir $(LARK_DIR)
# 	sudo chmod -R a+rwx $(LARK_DIR)
# 	cd /opt/lark && /usr/local/bin/python3.10 -m venv $(VENV_NAME)
# 	. $(LARK_VENV) && pip install --upgrade pip
# 	. $(LARK_VENV) && pip install -r requirements.txt