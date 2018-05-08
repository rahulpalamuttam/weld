
LLVM_FLAGS=$(llvm-config --cxxflags)

all:libptxgen

libptxgen:ptxgen.o
	ar rc libptxgen.a ptxgen.o
ptxgen.o:
	g++ -Wall -std=c++14 -fPIC -c ptxgen.c -I/usr/local/cuda-8.0/include -I/usr/local/cuda-8.0/nvvm/include -I/usr/lib/llvm-3.8/include -std=c++0x -fPIC -fvisibility-inlines-hidden -Wall -W -Wno-unused-parameter -Wwrite-strings -Wcast-qual -Wno-missing-field-initializers -pedantic -Wno-long-long -Wno-maybe-uninitialized -Wdelete-non-virtual-dtor -Wno-comment -std=c++11 -ffunction-sections -fdata-sections -O2 -g -DNDEBUG  -fno-exceptions -D_GNU_SOURCE -D__STDC_CONSTANT_MACROS -D__STDC_FORMAT_MACROS -D__STDC_LIMIT_MACROS

clean:
	rm -rf ptxgen.o libptxgen.a
