# Weld GPU Backend

## Contents

    * [Overview](#overview)
    * [Compiling](#compiling)
    * [Developer Documentation](#developer-documentation)
    * [Examples](#examples)
    * [TODO](#todo)

## Overview

* Note: Whether weld generates the NVVM code v/s the usual LLVM code is
controlled by a flag, NVVM_FLAG, in weld/llvm.rs.

## Compiling

There seem to be two compilers we can use: the usual llvm compiler (with the
nvptx backend), or NVIDIA's proprietary compiler (libNVVM). In theory, both
should work, but with a few subtler differences:

* libNVVM is usually tied to a particular version of LLVM (not the latest
version) - thus the generated code might need to be slightly modified.
* libNVVM

#### Manual Compilation

* Currently, we emit the generated NVVM file, manually compile it to .ptx, and
then use this .ptx file in the cuda code. The commands for manually compiling
a NVVM file are:

```bash
TODO: add these.
```

#### Programatic Compilation

## Developer Documentation

#### New Code

* The new code is concentrated across the files weld/llvm.rs,
and weld_rt/cpp/weld_cuda_backend.cpp.

#### Code Gen

Note: there are two separate code generation contexts: the NVVM kernel code
(which is essentially the code of a ``for`` loop right now), and the glue llvm
code that ties it back in with the rest of the weld program, launches the
kernel, gets the result back etc.

We generate NVVM code, mostly following the descriptions in llvm's [NVPTX
backend](https://llvm.org/docs/NVPTXUsage.html).


##### Differences from usual Weld code-gen

* No continuation functions:

A few other minor differences are:

* Don't run the vectorization pass as no SIMD for gpu
*

## TODO

#### Reductions:
* currently, we added addition by calling a thrust, but this is
* clearly slow in comparison to generating a
        - compare thrust call, with transform_and_reduce implementation. e.g.,
        for dot product. If it is significant, then we should do something
        about it.

#### Annotations:

* add annotations to each for loop so we can easily add the gpu v/s cpu flag in
the weld code - perhaps during one of the transformations / or let the user
specify it.

#### Programmatic Compilation:

#### Minor

* Add automatic tests (currently python/numpy/test.py serves as the test file - but
because we do not have programmatic compilation, this requires a lot of manual
compilations...)

* free the device output in case of reductions
* Decide when we definitely don't want to offload to gpu:
    - e.g., strided accesses.
* support loops over contiguous arrays specified with iter(e0,start,end,1)
* support result(for([0,1],...merger ... (merge(b, result(for(iter(e0,....) appender)))))
    - this does not seem urgent for now. Probably if we start to use
    continuation functions when generating the nvvm kernels, then this might be
    easy.
* do we need to add if (i < n) in the kernel?
* Streaming kernel support: should only copy partial data at a time using
MemcpyAsync, and then operate on that.
    - Currently, just copy everything first.
    - probably just always do it from the c++ code?
    - need choose block sizes etc.
* All types seem to work, but needs to be tested more thoroughly.

