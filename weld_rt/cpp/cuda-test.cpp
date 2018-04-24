#include <iostream>
#include <fstream>
#include <cassert>
#include "cuda.h"
#include <cuda_runtime.h>
#include <unistd.h>
#include <thread>
//#include <stdlib.h>
//#include <stdio.h>
#include <math.h>

#define THREAD_BLOCK_SIZE 512

void checkCudaErrors(CUresult err) {
  //printf("cuda err = %d\n", (size_t)err);
  if (err != CUDA_SUCCESS) {
    //printf("cuda success failure!!\n");
    //char errMsg[10000];
    const char *errMsg = (char *) malloc(10000);
    const char **errMsgptr = &errMsg;
    cuGetErrorString (err, errMsgptr);
    printf("cuda string error: %s\n", *errMsgptr);
  } else {
    //printf("cuda init actually worked!\n");
  }
  assert(err == CUDA_SUCCESS);
}

/*
 * @hostA: First array on which the operation is to be performed. This cannot be NULL.
 * @hostB: Second array. If the operations are all unary, then this can be NULL, and it would be
 * ignored.
 * @output: For now, we are assuming an output of the same length as hostA - which would presumably
 * be filled in by the PTX code passed in.
 * @num_elements: number of elements in the host arrays and output.
 * @size: size in bytes of the host arrays and output.
 */
extern "C" void weld_ptx_execute(void *hostA, void *hostB, void *output, int num_elements,
        int size)
{
    printf("weld ptx execute called!\n");
    printf("size = %d\n", size);
    if (!hostB) {
        printf("hostB was null!\n");
    };

    CUdevice    device;
    CUmodule    cudaModule;
    CUcontext   context;
    CUfunction  function;
    //CUlinkState linker;       // TODO: what is the use for this?
    int         devCount;
    // CUDA initialization
    // TODO: maybe this does not have to be reinitialized every time?
    checkCudaErrors(cuInit(0));
    checkCudaErrors(cuDeviceGetCount(&devCount));
    checkCudaErrors(cuDeviceGet(&device, 0));

    char name[128];
    checkCudaErrors(cuDeviceGetName(name, 128, device));
    printf("Using CUDA device %s\n", name);

    int devMajor, devMinor;
    checkCudaErrors(cuDeviceComputeCapability(&devMajor, &devMinor, device));
    printf("Device Compute Capability: %d.%d\n", devMajor, devMinor);
    if (devMajor < 2) {
        std::cerr << "ERROR: Device 0 is not SM 2.0 or greater\n";
    }

    /* TODO: this string should be passed in. */
    /* loading in file */
    std::ifstream t("/lfs/1/pari/kernel.ptx");
    if (!t.is_open()) {
        printf("kernel.ptx not found!\n");
        exit(0);
    }
    std::string str((std::istreambuf_iterator<char>(t)),
                std::istreambuf_iterator<char>());

    /* Create driver context */
    checkCudaErrors(cuCtxCreate(&context, 0, device));
    /* Create module */
    checkCudaErrors(cuModuleLoadDataEx(&cudaModule, str.c_str(), 0, 0, 0));
    /* Get kernel function */
    checkCudaErrors(cuModuleGetFunction(&function, cudaModule, "kernel"));

    CUdeviceptr devBufferA;
    CUdeviceptr devBufferB;
    CUdeviceptr devBufferC;

    printf("before malloc\n");
    checkCudaErrors(cuMemAlloc(&devBufferA, size));
    checkCudaErrors(cuMemAlloc(&devBufferC, size));
    checkCudaErrors(cuMemcpyHtoD(devBufferA, hostA, size));

    if (hostB) {
        checkCudaErrors(cuMemAlloc(&devBufferB, size));
        checkCudaErrors(cuMemcpyHtoD(devBufferB, hostB, size));
    }

    /* FIXME: be more flexible about different dimensions? */
    unsigned blockSizeX = THREAD_BLOCK_SIZE;
    unsigned blockSizeY = 1;
    unsigned blockSizeZ = 1;

    unsigned gridSizeX  = (size_t) ceil((float) num_elements / (float) THREAD_BLOCK_SIZE);
    unsigned gridSizeY  = 1;
    unsigned gridSizeZ  = 1;

    /* Kernel parameters */
    void *KernelParams[] = {&devBufferA, &devBufferB, &devBufferC};
    // FIXME: this seems hacky.
    if (!hostB) KernelParams[1] = &devBufferC;

    printf("Launching kernel\n");
    //// Kernel launch
    checkCudaErrors(cuLaunchKernel(function, gridSizeX, gridSizeY, gridSizeZ,
                             blockSizeX, blockSizeY, blockSizeZ,
                             0, NULL, KernelParams, NULL));
    // TODO: does it need any synchronize call here?

    //// Retrieve device data
    checkCudaErrors(cuMemcpyDtoH(output, devBufferC, size));

    //// Clean-up
    if (hostB) checkCudaErrors(cuMemFree(devBufferB));
    checkCudaErrors(cuMemFree(devBufferA));
    checkCudaErrors(cuMemFree(devBufferC));
    checkCudaErrors(cuModuleUnload(cudaModule));
    checkCudaErrors(cuCtxDestroy(context));
}

/* pari: testing ptx execution */
extern "C" void weld_ptx_test() {
    CUdevice    device;
    CUmodule    cudaModule;
    CUcontext   context;
    CUfunction  function;
    CUlinkState linker;
    int         devCount;
     //CUDA initialization
    checkCudaErrors(cuInit(0));
    checkCudaErrors(cuDeviceGetCount(&devCount));
    checkCudaErrors(cuDeviceGet(&device, 0));

    char name[128];
    checkCudaErrors(cuDeviceGetName(name, 128, device));
    printf("in ptx test!\n");
    printf("Using CUDA device %s\n", name);

    int devMajor, devMinor;
    checkCudaErrors(cuDeviceComputeCapability(&devMajor, &devMinor, device));
    //std::cout << "Device Compute Capability: "
        //<< devMajor << "." << devMinor << "\n";
    //printf("Device Compute Capability: %d.%d\n", devMajor, devMinor);
    if (devMajor < 2) {
        std::cerr << "ERROR: Device 0 is not SM 2.0 or greater\n";
    }

    std::ifstream t("/lfs/1/pari/kernel.ptx");
    if (!t.is_open()) {
        printf("kernel.ptx not found!\n");
        exit(0);
    }
    std::string str((std::istreambuf_iterator<char>(t)),
                std::istreambuf_iterator<char>());

    //// Create driver context
    checkCudaErrors(cuCtxCreate(&context, 0, device));

    //// Create module for object
    checkCudaErrors(cuModuleLoadDataEx(&cudaModule, str.c_str(), 0, 0, 0));

    //// Get kernel function
    checkCudaErrors(cuModuleGetFunction(&function, cudaModule, "kernel"));

    //// Device data
    CUdeviceptr devBufferA;
    CUdeviceptr devBufferB;
    CUdeviceptr devBufferC;

    checkCudaErrors(cuMemAlloc(&devBufferA, sizeof(double)*16));
    checkCudaErrors(cuMemAlloc(&devBufferB, sizeof(double)*16));
    checkCudaErrors(cuMemAlloc(&devBufferC, sizeof(double)*16));

    double* hostA = new double[16];
    double* hostB = new double[16];
    double* hostC = new double[16];

    // Populate input
    for (unsigned i = 0; i != 16; ++i) {
        hostA[i] = (double)i;
        hostB[i] = (double)(2*i);
        hostC[i] = 0.0f;
    }

    checkCudaErrors(cuMemcpyHtoD(devBufferA, &hostA[0], sizeof(double)*16));
    checkCudaErrors(cuMemcpyHtoD(devBufferB, &hostB[0], sizeof(double)*16));


    unsigned blockSizeX = 16;
    unsigned blockSizeY = 1;
    unsigned blockSizeZ = 1;
    unsigned gridSizeX  = 1;
    unsigned gridSizeY  = 1;
    unsigned gridSizeZ  = 1;

    //// Kernel parameters
    void *KernelParams[] = { &devBufferA, &devBufferB, &devBufferC };
    printf("Launching kernel\n");

    //// Kernel launch
    checkCudaErrors(cuLaunchKernel(function, gridSizeX, gridSizeY, gridSizeZ,
                             blockSizeX, blockSizeY, blockSizeZ,
                             0, NULL, KernelParams, NULL));
    // cudaDeviceSynchronize();
    //// Retrieve device data
    checkCudaErrors(cuMemcpyDtoH(&hostC[0], devBufferC, sizeof(double)*16));


    //std::cout << "Results:\n";
    printf("Results:\n");
    for (unsigned i = 0; i != 16; ++i) {
        //std::cout << hostA[i] << " + " << hostB[i] << " = " << hostC[i] << "\n";
        printf("%f + %f = %f\n", hostA[i], hostB[i], hostC[i]);
    }


    //// Clean up after ourselves
    delete [] hostA;
    delete [] hostB;
    delete [] hostC;

    //// Clean-up
    checkCudaErrors(cuMemFree(devBufferA));
    checkCudaErrors(cuMemFree(devBufferB));
    checkCudaErrors(cuMemFree(devBufferC));
    checkCudaErrors(cuModuleUnload(cudaModule));
    checkCudaErrors(cuCtxDestroy(context));
}

