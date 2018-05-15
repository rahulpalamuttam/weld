import weldnumpy as wn
import numpy as np

NUM_ELS = 10

def simple_test():
    w1 = wn.random.rand(10)
    w2 = wn.random.rand(10)
    print(w1)
    w3 = w1 + w2
    w3 = np.sqrt(w3)
    w3 = w3.evaluate()

def simple_cmp():
    n1 = np.random.rand(NUM_ELS)
    n2 = np.random.rand(NUM_ELS)
    w1 = wn.weldarray(n1)
    w2 = wn.weldarray(n2)

    n3 = (n1-n2)*3.0 + 400.00
    w3 = (w1-w2)*3.0 + 400.00
    # n3 = np.sin(n3)
    # w3 = np.sin(w3)
    w3 = w3.evaluate()

    assert (np.allclose(n3, w3.view(np.ndarray)))

    # for i in range(len(n3)):
        # if np.abs(n3[i] - w3[i]) > 0.1:
            # wrong += 1
            # print(n3[i])
            # print(w3[i])
    # print('wrong = ', wrong)

def blackscholes_bug1():
    n1 = np.random.rand(NUM_ELS)
    n2 = np.random.rand(NUM_ELS)
    w1 = wn.weldarray(n1)
    w2 = wn.weldarray(n2)

    print("n1[0]: ", n1[0])
    print("n2[0]: ", n2[0])

    # bad.
    # w3 = w2 * np.sqrt(w1)
    # n3 = n2 * np.sqrt(n1)

    w3 = w1 * np.sqrt(w2)
    n3 = n1 * np.sqrt(n2)

    w3 = w3.evaluate()

    assert (np.allclose(n3, w3.view(np.ndarray)))

def boundary_error():
    n1 = np.random.rand(NUM_ELS)
    n2 = np.random.rand(NUM_ELS)
    w1 = wn.weldarray(n1)
    w2 = wn.weldarray(n2)

    n1 = n1 * n2
    w1 = w1 * w2

    n4 = n2 - n1
    w4 = w2 - w1
    w4 = w4.evaluate()
    assert (np.allclose(n4, w4.view(np.ndarray)))

    # print("going to do all close without casting to ndarray")
    # print(np.allclose(n4, w4))

def blackscholes_bug_commutativity():
    n1 = np.random.rand(NUM_ELS)
    n2 = np.random.rand(NUM_ELS)
    w1 = wn.weldarray(n1)
    w2 = wn.weldarray(n2)

    # n3 = n1 - n2
    # w3 = w1 - w2
    # w3 = w3.evaluate()
    # print(np.allclose(n3, w3))

    n1 = n1 * n2
    w1 = w1 * w2

    n4 = n2 - n1
    w4 = w2 - w1
    w4 = w4.evaluate()
    assert (np.allclose(n4, w4.view(np.ndarray)))

def dot_product():
    n1 = np.random.rand(NUM_ELS)
    n2 = np.random.rand(NUM_ELS)
    w1 = wn.weldarray(n1)
    w2 = wn.weldarray(n2)

    n3 = n1*n2
    w3 = w1*w2
    # w3 = w3.evaluate()
    n4 = np.sum(n3)
    print('n4: ', n4)

    print("before calling sum")
    w4 = np.sum(w3)
    print("sum completed in python")
    print(type(w4))
    # w4 = w4.evaluate()
    print('w4: ', w4)

    print(np.allclose(n4, w4.view(np.ndarray)))

def simple_unary():
    n1 = np.random.rand(NUM_ELS)
    w1 = wn.weldarray(n1)
    print("w1[0]: ", w1[0])

    n2 = np.exp(n1)
    w2 = np.exp(w1)
    w2 = w2.evaluate()

    print(np.allclose(n2, w2.view(np.ndarray)))

def reduction_along_axis():
    n1 = np.random.rand(2,2)
    w1 = wn.weldarray(n1)

    print('n1[0]: ', n1[0])
    w2 = np.log(w1)
    n2 = np.log(n1)
    n3 = np.sum(n2, axis=0)
    print("n3: ", n3)

    w3 = np.sum(w2, axis=0)
    print(type(w3))
    print(w3.shape)
    print(w3._real_shape)
    print(w3.weldobj.weld_code)
    print("w3: ", w3)

    # print(np.allclose(n3, w3))

# blackscholes_bug1()
simple_test()
# simple_cmp()
# blackscholes_bug_commutativity()
# boundary_error()
# simple_unary()
dot_product()
# reduction_along_axis()
