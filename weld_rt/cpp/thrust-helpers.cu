#include <thrust/host_vector.h>
#include <thrust/device_vector.h>
#include <thrust/device_ptr.h>

// FIXME: need to add different input params, return arg etc.etc.
// treat input as device ptr.
// FIXME: fix types to accept any generic type.
// TODO: use c++ template's to support different input types etc.
extern "C" double thrust_reduce_wrapper(int8_t *input, int num_elements) {
    printf("hello from thrust reduce wrapper!\n");
    // wrap raw pointer with a device_ptr
    thrust::device_ptr<double> dev_ptr((double *) input);
    double sum = thrust::reduce(dev_ptr, dev_ptr + num_elements, (double) 0, thrust::plus<double>());
    printf("sum = %f\n", sum);
    return sum;
}
