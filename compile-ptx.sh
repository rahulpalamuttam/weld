#!/bin/bash
opt -internalize -internalize-public-api-list=kernel -nvvm-reflect-list=__CUDA_FTZ=0 -nvvm-reflect -O3 /tmp/t2.linked.bc -o /tmp/t2.opt.bc
rm -f /tmp/t2.linked.bc
llc -mcpu=sm_20 /tmp/t2.opt.bc -o /tmp/kernel.ptx
rm -f /tmp/t2.opt.bc
