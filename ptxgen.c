#include <math.h>
#include <cuda.h>
#include "drvapi_error_string.h"
#include "nvvm.h"
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/Pass.h"
//#include "NVPTX.h"

namespace llvm { FunctionPass *createNVVMReflectPass(const StringMap<int>& Mapping); }

//extern llvm::FunctionPass* llvm::createNVVMReflectPass(const llvm::StringMap<int>& Mapping);

extern "C" void NVVMReflectPass(llvm::legacy::PassManager pmb);

extern "C" void NVVMReflectPass(llvm::legacy::PassManager pmb){
  llvm::StringMap<int> reflect_mapping;
  reflect_mapping[llvm::StringRef("__CUDA_FTZ")] = 1;
  pmb.add(createNVVMReflectPass(reflect_mapping));
}

