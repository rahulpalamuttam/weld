#
# WeldObject
#
# Holds an object that can be evaluated.
#

import ctypes

import os
import time

import bindings as cweld
from types import *


class WeldObjectEncoder(object):
    """
    An abstract class that must be overwridden by libraries. This class
    is used to marshall objects from Python types to Weld types.
    """
    def encode(obj):
        """
        Encodes an object. All objects encodable by this encoder should return
        a valid Weld type using py_to_weld_type.
        """
        raise NotImplementedError

    def py_to_weld_type(obj):
        """
        Returns a WeldType corresponding to a Python object
        """
        raise NotImplementedError


class WeldObjectDecoder(object):
    """
    An abstract class that must be overwridden by libraries. This class
    is used to marshall objects from Weld types to Python types.
    """
    def decode(obj, restype):
        """
        Decodes obj, assuming object is of type `restype`. obj's Python
        type is ctypes.POINTER(restype.ctype_class).
        """
        raise NotImplementedError


class WeldObject(object):
    """
    Holds a Weld program to be lazily compiled and evaluated,
    along with any context required to evaluate the program.

    Libraries that use the Weld API return WeldObjects, which represent
    "lazy executions" of programs. WeldObjects can build on top of each other,
    i.e. libraries should be implemented so they can accept both their
    native types and WeldObjects.

    An WeldObject contains a Weld program as a string, along with a context.
    The context maps names in the Weld program to concrete values.

    When a WeldObject is evaluated, it uses its encode and decode functions to
    marshall native library types into types that Weld understands. The basic
    flow of evaluating a Weld expression is thus:

    1. "Finish" the Weld program by adding a function header
    2. Compile the Weld program and load it as a dynamic library
    3. For each argument, run object.encoder on each argument. See
       WeldObjectEncoder for details on how this works
    4. Pass the encoded arguments to Weld
    5. Run the decoder on the return value. See WeldObjectDecoder for details
       on how this works.
    6. Return the decoded value.
    """

    # Counter for assigning variable names
    _var_num = 0
    _obj_id = 100
    _registry = {}

    def __init__(self, encoder, decoder):
        self.encoder = encoder
        self.decoder = decoder

        # Weld program
        self.weld_code = ""
        self.dependencies = {}

        # Assign a unique ID to the context
        self.obj_id = "obj%d" % WeldObject._obj_id
        WeldObject._obj_id += 1

        # Maps name -> input data
        self.context = {}
        # Maps name -> arg type (for arguments that don't need to be encoded)
        self.argtypes = {}

    def __repr__(self):
        return self.weld_code + " " + str(self.context) + " " + str([obj_id for obj_id in self.dependencies])

    def update(self, value, tys=None, override=True):
        """
        Update this context. if value is another context,
        the names from that context are added into this one.
        Otherwise, a new name is assigned and returned.

        TODO tys for inputs.
        """
        if isinstance(value, WeldObject):
            self.context.update(value.context)
        else:
            # Ensure that the same inputs always have same names
            value_str = str(value)
            if value_str in WeldObject._registry:
                name = WeldObject._registry[value_str]
            else:
                name = "_inp%d" % WeldObject._var_num
                WeldObject._var_num += 1
                WeldObject._registry[value_str] = name
            self.context[name] = value
            if tys is not None and not override:
                self.argtypes[name] = tys
            return name

    def get_let_statements(self):
        queue = [self]
        visited = set()
        let_statements = []
        is_first = True
        while len(queue) > 0:
            cur_obj = queue.pop()
            cur_obj_id = cur_obj.obj_id
            if cur_obj_id in visited:
                continue
            if not is_first:
                let_statements.insert(0, "let %s = (%s);" % (cur_obj_id, cur_obj.weld_code))
            is_first = False
            for key in sorted(cur_obj.dependencies.keys()):
                queue.append(cur_obj.dependencies[key])
            visited.add(cur_obj_id)
        let_statements.sort()  # To ensure that let statements are in the right
                               # order in the final generated program
        return "\n".join(let_statements)

    def to_weld_func(self):
        names = self.context.keys()
        names.sort()
        arg_strs = ["{0}: {1}".format(str(name),
                                      str(self.encoder.py_to_weld_type(self.context[name])))
                    for name in names]
        header = "|" + ", ".join(arg_strs) + "|"
        keys = self.dependencies.keys()
        keys.sort()
        text = header + " " + self.get_let_statements() + "\n" + self.weld_code
        return text

    def evaluate(self, restype, verbose=True, decode=True, passes=None):
        function = self.to_weld_func()

        # Returns a wrapped ctypes Structure
        def args_factory(encoded):
            class Args(ctypes.Structure):
                _fields_ = [e for e in encoded]
            return Args

        # Encode each input argument. This is the positional argument list
        # which will be wrapped into a Weld struct and passed to the Weld API.
        names = self.context.keys()
        names.sort()

        start = time.time()
        encoded = []
        argtypes = []
        weld_num_threads = int(os.environ.get("WELD_NUM_THREADS", "1"))
        for name in names:
            if name in self.argtypes:
                argtypes.append(self.argtypes[name].ctype_class)
                encoded.append(self.context[name])
            else:
                argtypes.append(self.encoder.py_to_weld_type(
                    self.context[name]).ctype_class)
                encoded.append(self.encoder.encode(self.context[name], weld_num_threads))
        end = time.time()
        if verbose:
            if len(argtypes) > 5:
                                function = """
                |_inp0: vec[i64], _inp1: vec[i64], _inp10: vec[i64], _inp11: vec[vec[i8]], _inp2: vec[i64], _inp3: vec[i64], _inp4: vec[vec[i8]], _inp5: vec[i64], _inp6: vec[i64], _inp7: vec[vec[i8]], _inp8: vec[i64], _inp9: vec[vec[i8]]| let obj100 = (
                result(
                for(
                zip(_inp0, _inp1, _inp2, _inp3),
                appender,
                |b, i, e| merge(b, e)
                )
                )
                );
                
                let obj102 = (
                let df2_join_table = result(
                for(
                _inp6,
                groupmerger[i64, i64],
                |b, i, e| merge(b, {e, i})
                )
                );
                
                result(for(
                obj100,
                appender,
                |b, i, e|
                for(
                lookup(df2_join_table, e.$1),
                b,
                |b2, i2, e2| merge(b2, {e.$1, e.$3, e.$0, e.$2, lookup(_inp4, e2), lookup(_inp5, e2), lookup(_inp7, e2), lookup(_inp8, e2)})
                )
                ))
                );
                let obj104 = (
                let df2_join_table = result(
                for(
                _inp10,
                groupmerger[i64, i64],
                |b, i, e| merge(b, {e, i})
                )
                );
                
                for(
                obj102,
                {appender[i64], appender[i64], appender[i64], appender[vec[i8]], appender[vec[i8]], appender[i64], appender[i64], appender[i64], appender[vec[i8]], appender[vec[i8]]},
                |b, i, e|
                for(
                lookup(df2_join_table, e.$2),
                b,
                |b2, i2, e2| {merge(b2.$0, e.$2), merge(b2.$1, e.$1), merge(b2.$2, e.$0), merge(b2.$3, e.$6), merge(b2.$4, e.$4), merge(b2.$5, e.$5), merge(b2.$6, e.$3), merge(b2.$7, e.$7), merge(b2.$8, lookup(_inp9, e2)), merge(b2.$9, lookup(_inp11, e2))}
                )
                )
                );
                
                {result(obj104.$0), result(obj104.$1), result(obj104.$2), result(obj104.$3), result(obj104.$4), result(obj104.$5), result(obj104.$6), result(obj104.$7), result(obj104.$8), result(obj104.$9)}
                """
            elif len(argtypes) == 2:
                                function = """
            |_inp12: vec[i64], _inp16: vec[vec[i8]]| let obj108 = (
    let group = sort(
      tovec(
        result(
          for(
            _inp16,
            dictmerger[vec[i8], i64, +],
            |b, i, e| merge(b, {e, 1L})
          )
        )
      ),
      |x:{vec[i8], i64}| x.$0
    );
   group
  );
let obj112 = (
       result(
         for(
           obj108,
           appender,
           |b, i, e| if (e.$1 >= i64(250), merge(b, e.$0), b)
         )
       )
    );
let obj127 = (
    let sum_dict = result(
      for(
        zip(_inp16, _inp12),
        dictmerger[vec[i8], {i64, i64}, +],
        |b, i, e| merge(b, {e.$0, {e.$1, 1L}})
      )
    );
    let mean_dict = result(
      for(
        tovec(sum_dict),
        dictmerger[vec[i8], f64, +],
        |b, i, e| merge(b, {e.$0, f64(e.$1.$0) / f64(e.$1.$1)})
      )
    );
    let std_dict = result(
      for(
        zip(_inp16, _inp12),
        dictmerger[vec[i8], f64, +],
        |b, i, e| merge(b, {e.$0, (let m = lookup(mean_dict, e.$0); (f64(e.$1) - m)* (f64(e.$1) - m))})
    ));
    map(
      sort(tovec(std_dict), |x| x.$0),
      |x| {x.$0, sqrt((x.$1 / f64(lookup(sum_dict, x.$0).$1 - 1L)))}
    )
  );
let obj129 = (
    result(for(
      obj127,
      appender[vec[i8]],
      |b,i,e| merge(b, e.$0)
    ))
);
let obj135 = (
    let check_dict =
      result(
        for(
          map(
            obj112,
            |p: vec[i8]| {p,0}
          ),
        dictmerger[vec[i8],i32,+],
        |b, i, e| merge(b,e)
        )
      );
    check_dict
    );
let obj136 = (
       result(
         for(
           obj127,
           appender,
           |b, i, e| if (keyexists(obj135, e.$0), merge(b, e), b)
         )
       )
    );
let obj141 = (
    slice(sort(obj136, |x| x.$1* f64(-1)), 0L, 10L)
    );
let obj142 = (
    let unzip_builder = for(
      obj141,
      {appender[vec[i8]], appender[f64]},
      |b,i,e| {merge(b.$0, e.$0), merge(b.$1, e.$1)}
    );
    {result(unzip_builder.$0), result(unzip_builder.$1)}
    );
    obj142
    """
            print "Python->Weld:", end - start

        start = time.time()
        Args = args_factory(zip(names, argtypes))
        weld_args = Args()
        for name, value in zip(names, encoded):
            setattr(weld_args, name, value)

        start = time.time()
        void_ptr = ctypes.cast(ctypes.byref(weld_args), ctypes.c_void_p)
        arg = cweld.WeldValue(void_ptr)
        conf = cweld.WeldConf()
        err = cweld.WeldError()

        if passes is not None:
            conf.set("weld.optimization.passes", ",".join(passes))

        module = cweld.WeldModule(function, conf, err)
        if err.code() != 0:
            raise ValueError("Could not compile function {}: {}".format(
                function, err.message()))
        end = time.time()
        if verbose:
            print "Weld compile time:", end - start

        start = time.time()
        conf = cweld.WeldConf()
        conf.set("weld.threads", str(weld_num_threads))
        conf.set("weld.memory.limit", "100000000000")
        err = cweld.WeldError()
        weld_ret = module.run(conf, arg, err)
        if err.code() != 0:
            raise ValueError(("Error while running function,\n{}\n\n"
                              "Error message: {}").format(
                function, err.message()))
        ptrtype = POINTER(restype.ctype_class)
        data = ctypes.cast(weld_ret.data(), ptrtype)
        end = time.time()
        if verbose:
            print "Weld:", end - start

        start = time.time()
        if decode:
            result = self.decoder.decode(data, restype)
        else:
            data = cweld.WeldValue(weld_ret).data()
            result = ctypes.cast(data, ctypes.POINTER(
                ctypes.c_int64)).contents.value
        end = time.time()
        if verbose:
            print "Weld->Python:", end - start

        return result
