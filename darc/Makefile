
DARCDIR=/opt/darc
LIB=lib

all:
	$(MAKE) -C src all
	test -d $(LIB) || mkdir $(LIB)
	cp src/circ.o $(LIB)
	cp src/buffer.o $(LIB)
	cp src/mutex.o $(LIB)

install:
	test -d $(DARCDIR) || (echo "No DARC installed at $(DARCDIR)" && exit 1)
	sudo cp $(LIB)/circ.o $(DARCDIR)/lib
	sudo cp $(LIB)/buffer.o $(DARCDIR)/lib
	sudo cp $(LIB)/mutex.o $(DARCDIR)/lib

clean:
	rm -rf lib
	$(MAKE) -C src clean