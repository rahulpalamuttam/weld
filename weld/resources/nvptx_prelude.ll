target datalayout = "e-p:64:64:64-i1:8:8-i8:8:8-i16:16:16-i32:32:32-i64:64:64-f64:32:32-f64:64:64-v16:16:16-v32:32:32-v64:64:64-v128:128:128-n16:32:64"
target triple = "nvptx64-nvidia-cuda"

; Unsigned data types -- we use these in the generated code for clarity and to make
; template substitution work nicely when calling type-specific functions
%u8 = type i8;
%u16 = type i16;
%u32 = type i32;
%u64 = type i64;

; work_t struct in runtime.h
%work_t = type { i8*, i64, i64, i64, i32, i64*, i64*, i32, i64, void (%work_t*)*, %work_t*, i32, i32, i32 }
; vec_piece struct in runtime.h
%vb.vp = type { i8*, i64, i64, i64*, i64*, i32 }
; vec_output struct in runtime.h
%vb.out = type { i8*, i64 }

; Input argument (input data pointer, nworkers, mem_limit)
%input_arg_t = type { i64, i32, i64 }
; Return type (output data pointer, run ID, errno)
%output_arg_t = type { i64, i64, i64 }

; LLVM intrinsic functions
declare void @llvm.memcpy.p0i8.p0i8.i64(i8*, i8*, i64, i32, i1)
declare void @llvm.memset.p0i8.i64(i8*, i8, i64, i32, i1)

; libdevice functions
declare double @__nv_log(double)
declare float @__nv_logf(float)
declare double @__nv_exp(double)
declare float @__nv_expf(float)
declare double @__nv_sqrt(double)
declare float @__nv_sqrtf(float)
declare double @__nv_erf(double)
declare float @__nv_erff(float)

declare double @__nv_sin(double)
declare float @__nv_sinf(float)
declare double @__nv_cos(double)
declare float @__nv_cosf(float)
declare double @__nv_tan(double)
declare float @__nv_tanf(float)

declare double @__nv_sinh(double)
declare float @__nv_sinhf(float)
declare double @__nv_cosh(double)
declare float @__nv_coshf(float)
declare double @__nv_tanh(double)
declare float @__nv_tanhf(float)

declare double @__nv_asin(double)
declare float @__nv_asinf(float)
declare double @__nv_acos(double)
declare float @__nv_acosf(float)
declare double @__nv_atan(double)
declare float @__nv_atanf(float)

; Intrinsic to read X component of thread ID
declare i32 @llvm.nvvm.read.ptx.sreg.tid.x() readnone nounwind
declare i32 @llvm.nvvm.read.ptx.sreg.ctaid.x() readnone nounwind
declare i32 @llvm.nvvm.read.ptx.sreg.ntid.x() readnone nounwind


