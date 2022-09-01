
OPTS=
#-DUSESPINLOCKS
OLEVEL=-O3
CC=gcc -std=gnu11 -finline-functions
SINC=../include

all: circ.o buffer.o mutex.o

circ.o: circ.c $(SINC)/circ.h
	$(CC) $(OPTS) -Wall $(OLEVEL) -I$(SINC) -c circ.c -o circ.o -DUSEGSL -fPIC
	
buffer.o: buffer.c $(SINC)/buffer.h
	$(CC) -Wall $(OPTS) $(OLEVEL) -fPIC -I$(SINC) -c buffer.c -o buffer.o
	
mutex.o: $(SINC)/mutex.h mutex.c
	$(CC) $(OPTS) -lpthread -Wall $(OLEVEL) -c -I$(SINC) -o mutex.o mutex.c -fPIC
	
clean:
	rm -f circ.o
	rm -f buffer.o
	rm -f mutex.o