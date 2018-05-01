#include <math.h>
#include <cuda.h>
#include "drvapi_error_string.h"
#include "nvvm.h"
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>

/* Two levels of indirection to stringify LIBDEVICE_MAJOR_VERSION and
 * LIBDEVICE_MINOR_VERSION correctly. */
#define getLibDeviceNameForArch(ARCH)                 \
  _getLibDeviceNameForArch(ARCH,                      \
                           LIBDEVICE_MAJOR_VERSION,   \
                           LIBDEVICE_MINOR_VERSION)
#define _getLibDeviceNameForArch(ARCH, MAJOR, MINOR)  \
  __getLibDeviceNameForArch(ARCH, MAJOR, MINOR)
#define __getLibDeviceNameForArch(ARCH, MAJOR, MINOR) \
  ("/libdevice/libdevice.compute_" #ARCH ".10.bc")

#define getLibnvvmHome _getLibnvvmHome(/usr/local/cuda-8.0/nvvm/)
#define _getLibnvvmHome(NVVM_HOME) __getLibnvvmHome(NVVM_HOME)
#define __getLibnvvmHome(NVVM_HOME) (#NVVM_HOME)


// This will output the proper CUDA error strings in the event that a CUDA host call returns an error
#define checkCudaErrors(err)  __checkCudaErrors (err, __FILE__, __LINE__)

// These are the inline versions for all of the SDK helper functions
void __checkCudaErrors( CUresult err, const char *file, const int line )
{
    if( CUDA_SUCCESS != err) {
        fprintf(stderr, "checkCudaErrors() Driver API error = %04d \"%s\" from file <%s>, line %i.\n",
                err, getCudaDrvErrorString(err), file, line );
        exit(-1);
    }
}

typedef struct stat Stat;

typedef enum {
  PTXGEN_SUCCESS                    = 0x0000,
  PTXGEN_FILE_IO_ERROR              = 0x0001,
  PTXGEN_BAD_ALLOC_ERROR            = 0x0002,
  PTXGEN_LIBNVVM_COMPILATION_ERROR  = 0x0004,
  PTXGEN_LIBNVVM_ERROR              = 0x0008,
  PTXGEN_INVALID_USAGE              = 0x0010,
  PTXGEN_LIBNVVM_HOME_UNDEFINED     = 0x0020,
  PTXGEN_LIBNVVM_VERIFICATION_ERROR = 0x0040
} PTXGENStatus;


static PTXGENStatus getLibDeviceName(int computeArch, char **buffer)
{
  const char *libnvvmPath = getLibnvvmHome;
  const char *libdevice   = NULL;

  if (libnvvmPath == NULL) {
    fprintf(stderr, "The environment variable LIBNVVM_HOME undefined\n");
    return PTXGEN_LIBNVVM_HOME_UNDEFINED;
  }

  /* Use libdevice for compute_20, if the target is not compute_20, compute_30,
   * or compute_35. */
  switch (computeArch) {
  default:
    libdevice = getLibDeviceNameForArch(20);
    break;
  case 30:
    libdevice = getLibDeviceNameForArch(30);
    break;
  case 35:
    libdevice = getLibDeviceNameForArch(35);
    break;
  }

  *buffer = (char *) malloc(strlen(libnvvmPath) + strlen(libdevice) + 1);
  if (*buffer == NULL) {
    fprintf(stderr, "Failed to allocate memory\n");
    return PTXGEN_BAD_ALLOC_ERROR;
  }

  /* Concatenate libnvvmPath and name. */
  *buffer = strcat(strcpy(*buffer, libnvvmPath), libdevice);

  return PTXGEN_SUCCESS;
}


CUdevice cudaDeviceInit()
{
    CUdevice cuDevice = 0;
    int deviceCount = 0;
    CUresult err = cuInit(0);
    char name[100];
    int major=0, minor=0;

    if (CUDA_SUCCESS == err)
        checkCudaErrors(cuDeviceGetCount(&deviceCount));
    if (deviceCount == 0) {
        fprintf(stderr, "cudaDeviceInit error: no devices supporting CUDA\n");
        exit(-1);
    }
    checkCudaErrors(cuDeviceGet(&cuDevice, 0));
    cuDeviceGetName(name, 100, cuDevice);
    printf("Using CUDA Device [0]: %s\n", name);

    checkCudaErrors( cuDeviceComputeCapability(&major, &minor, cuDevice) );
    if (major < 2) {
        fprintf(stderr, "Device 0 is not sm_20 or later\n");
        exit(-1);
    }
    return cuDevice;
}


CUresult initCUDA(CUcontext *phContext,
                  CUdevice *phDevice,
                  CUmodule *phModule,
                  CUfunction *phKernel,
                  const char *ptx)
{
    // Initialize 
    *phDevice = cudaDeviceInit();

    // Create context on the device
    checkCudaErrors(cuCtxCreate(phContext, 0, *phDevice));

    // Load the PTX 
    checkCudaErrors(cuModuleLoadDataEx(phModule, ptx, 0, 0, 0));

    // Locate the kernel entry poin
    checkCudaErrors(cuModuleGetFunction(phKernel, *phModule, "simple"));

    return CUDA_SUCCESS;
}

char *loadProgramSource(const char *filename, size_t *size) 
{
    struct stat statbuf;
    FILE *fh;
    char *source = NULL;
    *size = 0;
    fh = fopen(filename, "rb");
    if (fh) {
        stat(filename, &statbuf);
        source = (char *) malloc(statbuf.st_size+1);
        if (source) {
            fread(source, statbuf.st_size, 1, fh);
            source[statbuf.st_size] = 0;
            *size = statbuf.st_size+1;
        }
    }
    else {
        fprintf(stderr, "Error reading file %s\n", filename);
        exit(-1);
    }
    return source;
}

static PTXGENStatus addFileToProgram(const char *filename, nvvmProgram prog)
{
  char        *buffer;
  size_t       size;
  Stat         fileStat;

  /* Open the input file. */
  FILE *f = fopen(filename, "rb");
  if (f == NULL) {
    fprintf(stderr, "Failed to open %s\n", filename);
    return PTXGEN_FILE_IO_ERROR;
  }

  /* Allocate buffer for the input. */
  fstat(fileno(f), &fileStat);
  buffer = (char *) malloc(fileStat.st_size);
  if (buffer == NULL) {
    fprintf(stderr, "Failed to allocate memory\n");
    return PTXGEN_BAD_ALLOC_ERROR;
  }
  size = fread(buffer, 1, fileStat.st_size, f);
  if (ferror(f)) {
    fprintf(stderr, "Failed to read %s\n", filename);
    fclose(f);
    free(buffer);
    return PTXGEN_FILE_IO_ERROR;
  }
  fclose(f);

  if (nvvmAddModuleToProgram(prog, buffer, size, filename) != NVVM_SUCCESS) {
    fprintf(stderr,
            "Failed to add the module %s to the compilation unit\n",
            filename);
    free(buffer);
    return PTXGEN_LIBNVVM_ERROR;
  }

  free(buffer);
  return PTXGEN_SUCCESS;
}

extern "C" char *generatePTX(const char *ll, size_t size, const char *filename);
extern "C" char *generatePTX(const char *ll, size_t size, const char *filename)
{
    PTXGENStatus status;
    char *libDeviceName;
    nvvmResult result;
    nvvmProgram program;
    size_t PTXSize;
    char *PTX = NULL;

    // initialize nvvm program and check resulting error
    result = nvvmCreateProgram(&program);
    if (result != NVVM_SUCCESS) {
        fprintf(stderr, "nvvmCreateProgram: Failed\n");
        exit(-1); 
    }

      /* Add libdevice. */
    /* int computeArch = 20; */
    /* status = getLibDeviceName(computeArch, &libDeviceName); */
    /* if (status != PTXGEN_SUCCESS) { */
    /*   fprintf(stderr, "getLibDeviceName : Failed\n"); */
    /*   //nvvmDestroyProgram(&program); */
    /*   exit(-1); */
    /* } */
    /* status = addFileToProgram(libDeviceName, program); */
    /* free(libDeviceName); */
    /* if (status != PTXGEN_SUCCESS) { */
    /*   fprintf(stderr, "addFileToProgram (libDeviceName): Failed\n"); */
    /*   //nvvmDestroyProgram(&program); */
    /*   exit(-1); */
    /* 	//return status; */
    /* } */

    /* result = nvvmAddModuleToProgram(program, libdeviceMod, libdeviceModSize); */
    /* if (result != NVVM_SUCCESS) { */
    /*     fprintf(stderr, "nvvmAddModuleToProgram (libdeviceMod): Failed\n"); */
    /*     exit(-1); */
    /* } */
    
    // add nvvm module to program
    // what is a module? apparently you can add more than one module
    // ll is the llvm string
    result = nvvmAddModuleToProgram(program, ll, size, NULL);
    if (result != NVVM_SUCCESS) {
        fprintf(stderr, "nvvmAddModuleToProgram: Failed\n");
        exit(-1);
    }

    // Declare compile options
    // const char *options[] = { "-nvvm-reflect -O3" };
    fprintf(stderr, "attempting to nvvm compile");
    result = nvvmCompileProgram(program,  0, NULL);
    if (result != NVVM_SUCCESS) {
        char *Msg = NULL;
        size_t LogSize;
        fprintf(stderr, "nvvmCompileProgram: Failed\n");
        nvvmGetProgramLogSize(program, &LogSize);
        Msg = (char*)malloc(LogSize);
        nvvmGetProgramLog(program, Msg);
	fprintf(stderr, "%s\n", ll);
	fprintf(stderr, "%u\n", size);
        fprintf(stderr, "%s\n", Msg);

        free(Msg);
        exit(-1);
    }
    
    result = nvvmGetCompiledResultSize(program, &PTXSize);
    if (result != NVVM_SUCCESS) {
        fprintf(stderr, "nvvmGetCompiledResultSize: Failed\n");
        exit(-1);
    }

    PTX = (char*)malloc(PTXSize);
    result = nvvmGetCompiledResult(program, PTX);
    if (result != NVVM_SUCCESS) {
        fprintf(stderr, "nvvmGetCompiledResult: Failed\n");
        free(PTX);
        exit(-1);
    }

    // cleanup
    result = nvvmDestroyProgram(&program);
    if (result != NVVM_SUCCESS) {
      fprintf(stderr, "nvvmDestroyProgram: Failed\n");
      free(PTX);
      exit(-1);
    }
    return PTX;
}
