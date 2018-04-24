target datalayout = "e-p:64:64:64-i1:8:8-i8:8:8-i16:16:16-i32:32:32-i64:64:64-f64:32:32-f64:64:64-v16:16:16-v32:32:32-v64:64:64-v128:128:128-n16:32:64"
target triple = "nvptx64-nvidia-cuda"

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

%s0 = type { double, double }

; Intrinsic to read X component of thread ID
declare i32 @llvm.nvvm.read.ptx.sreg.tid.x() readnone nounwind
declare i32 @llvm.nvvm.read.ptx.sreg.ctaid.x() readnone nounwind
declare i32 @llvm.nvvm.read.ptx.sreg.ntid.x() readnone nounwind
