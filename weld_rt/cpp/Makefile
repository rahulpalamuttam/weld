OS = $(shell uname -s)
LLVM_VERSION = $(shell llvm-config --version | cut -d . -f 1,2)

CFLAGS = -O3 -std=c++11 -Wall -fno-use-cxa-atexit -fPIC
ifeq (${OS}, Darwin)
  # OS X
  CLANG ?= clang++-${LLVM_VERSION}
	LIB = libweldrt.a
else ifeq (${OS}, Linux)
  # Linux
  CLANG ?= clang++-${LLVM_VERSION}
	LIB = libweldrt.a
else
  $(error Unsupported platform: ${OS})
endif

all: ${LIB} inline.bc

inline.o: inline.cpp
	${CLANG} ${CFLAGS} -c $< -o $@

inline.bc: inline.cpp
	${CLANG} ${CFLAGS} -c -emit-llvm $< -o $@

vb.o: vb.cpp
	${CLANG} ${CFLAGS} -c $< -o $@

dict.o: dict-new.cpp
	${CLANG} ${CFLAGS} -c $< -o $@

gb.o: gb-new.cpp
	${CLANG} ${CFLAGS} -c $< -o $@

merger.o: merger.cpp
	${CLANG} ${CFLAGS} -c $< -o $@

runtime.o: runtime.cpp
	${CLANG} ${CFLAGS} -c $< -o $@

weld_cuda_backend.o: weld_cuda_backend.cpp
	#${CLANG} ${CFLAGS} -I/usr/local/cuda-8.0/include -lcuda -c $< -o $@
	nvcc -O3 -Xcompiler -fPIC -std=c++11 -lcuda -c -arch=sm_35 $< -o $@

thrust-helpers.o: thrust-helpers.cu
	nvcc -O3 -Xcompiler -fPIC -c -arch=sm_35 $< -o $@

weldrt.o: vb.o dict.o merger.o runtime.o inline.o weld_cuda_backend.o gb.o thrust-helpers.o
	ld -r $^ -o $@


${LIB}: weldrt.o
	ar rcs $@ $^

clean:
	rm -f *.bc *.o ${LIB}

.phony: all
