all:libptxgen

libptxgen:ptxgen.o
	ar rc libptxgen.a ptxgen.o
ptxgen.o:
	g++ -Wall -fno-use-cxa-atexit -std=c++11 -fPIC -c ptxgen.c -I/usr/local/cuda-8.0/include -I/usr/local/cuda-8.0/nvvm/include -Wl, -BStatic -lcudart -Wl, -BStatic -lnvvm

clean:
	rm -rf ptxgen.o libptxgen.a
