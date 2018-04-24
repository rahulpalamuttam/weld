all:libptxgen

libptxgen:ptxgen.o
	ar rc libptxgen.a ptxgen.o
ptxgen.o:
	g++ -Wall -std=c++14 -fPIC -c ptxgen.c -I/usr/local/cuda-8.0/include -I/usr/local/cuda-8.0/nvvm/include

clean:
	rm -rf ptxgen.o libptxgen.a
