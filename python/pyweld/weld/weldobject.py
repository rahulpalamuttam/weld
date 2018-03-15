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
        weld_hand_opt = int(os.environ.get("HAND_OPT", "0"))
        for name in names:
            if name in self.argtypes:
                argtypes.append(self.argtypes[name].ctype_class)
                encoded.append(self.context[name])
            else:
                argtypes.append(self.encoder.py_to_weld_type(
                    self.context[name]).ctype_class)
                encoded.append(self.encoder.encode(self.context[name], weld_num_threads))
        end = time.time()
        #print "actual function"
        #print function
        verbose, amen = verbose
        if verbose:
            print "Python->Weld:", end - start
            if amen == 1:
                print "executing preprocessing"
                function = """
                |_inp0: vec[i64], _inp1: vec[i64], _inp10: vec[i64], _inp11: vec[vec[i8]], _inp2: vec[i64], _inp3: vec[i64], _inp4: vec[vec[i8]], _inp5: vec[i64], _inp6: vec[i64], _inp7: vec[vec[i8]], _inp8: vec[i64], _inp9: vec[vec[i8]]| 
                let obj100 = (
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
                
                  result(
                    for(
                      obj100,
                      appender,
                      |b, i, e|
                        for(
                          lookup(df2_join_table, e.$1),
                          b,
                          |b2, i2, e2| merge(b2, 
                                                {e.$1, 
                                                 e.$3, 
                                                 e.$0, 
                                                 e.$2,
                                                 lookup(_inp4, e2), 
                                                 lookup(_inp5, e2), 
                                                 lookup(_inp7, e2), 
                                                 lookup(_inp8, e2)}
                                              )
                        )
                    )
                  )
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
            elif amen == 5:
                function = """
                |_inp1: vec[i64], _inp12: vec[i64], _inp13: vec[vec[i8]], _inp14: vec[i64], _inp15: vec[vec[i8]], _inp16: vec[vec[i8]], _inp17: vec[vec[i8]], _inp18: vec[i64], _inp19: vec[i64], _inp20: vec[i64], _inp21: vec[i8], _inp22: vec[i8], _inp23: vec[i8]| let obj106 = (
       result(
         for(
           zip(_inp12, _inp13, _inp14, _inp15, _inp16, _inp17, _inp18, _inp19, _inp1, _inp20),
           appender,
           |b, i, e| merge(b, e)
         )
       )
    );
let obj107 = (
          let bs = for(
            obj106,
            {dictmerger[{vec[i8],vec[i8]},{i64, i64},+], dictmerger[vec[i8],i64,+], dictmerger[vec[i8],i64,+]},
            |b, i, e| {merge(b.$0, {{e.$4, e.$5}, {e.$0, 1L}}),
                       merge(b.$1, {e.$4, 1L}),
                       merge(b.$2, {e.$5, 1L})}
          );
          let agg_dict = result(bs.$0);
          let ind_vec = sort(map(tovec(result(bs.$1)), |x| x.$0), |x| x);
          let col_vec = map(tovec(result(bs.$2)), |x| x.$0);
          let pivot = map(
            col_vec,
            |x:vec[i8]|
            map(ind_vec, |y:vec[i8]| (
              let sum_len_pair = lookup(agg_dict, {y, x});
              f64(sum_len_pair.$0) / f64(sum_len_pair.$1))
            )
        );
        {ind_vec, pivot, col_vec}
    );
let obj108 = (
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
    {
      map(
      group,
        |x:{vec[i8],i64}| x.$0
      ),
      map(
        group,
        |x:{vec[i8],i64}| x.$1
      )
    }
  );
let obj109 = (
      obj108.$0
    );
let obj110 = (
      obj108.$1
    );
let obj111 = (
       map(
         obj110,
         |a: i64| a >= i64(250)
       )
    );
let obj112 = (
       result(
         for(
           zip(obj109, obj111),
           appender,
           |b, i, e| if (e.$1, merge(b, e.$0), b)
         )
       )
    );
let obj113 = (
      obj107.$0
    );
let obj114 = (
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
      map(
        obj113,
        |x: vec[i8]| keyexists(check_dict, x)
      )
    );
let obj115 = (
    let index_filtered =
      result(
        for(
          zip(obj107.$0, obj114),
          appender,
          |b, i, e| if (e.$1, merge(b, e.$0), b)
        )
      );
    let pivot_filtered =
      map(
        obj107.$1,
        |x|
          result(
            for(
              zip(x, obj114),
              appender,
              |b, i, e| if (e.$1, merge(b, e.$0), b)
            )
          )
      );
    {index_filtered, pivot_filtered, obj107.$2}
    );
let obj116 = (
      let col_dict = result(for(
        obj115.$2,
        dictmerger[vec[i8],i64,+],
        |b, i, e| merge(b, {e, i})
      ));
    {obj115.$0, lookup(obj115.$1, lookup(col_dict, _inp21))}
    );
let obj117 = (
      let col_dict = result(for(
        obj115.$2,
        dictmerger[vec[i8],i64,+],
        |b, i, e| merge(b, {e, i})
      ));
    {obj115.$0, lookup(obj115.$1, lookup(col_dict, _inp22))}
    );
let obj118 = (
      obj116.$0
    );
let obj119 = (
      obj116.$1
    );
let obj121 = (
      obj117.$1
    );
let obj122 = (
       map(
         zip(obj119, obj121),
         |a| a.$0 - a.$1
       )
    );
let obj123 = ({obj118, obj122});
let obj124 = (
      obj123.$1
    );
let obj125 = (
    let pv_cols = for(
      obj115.$1,
      appender[vec[f64]],
      |b, i, e| merge(b, e)
    );
    let col_names = for(
      obj115.$2,
      appender[vec[i8]],
      |b, i, e| merge(b, e)
    );
    let new_pivot_cols = result(merge(pv_cols, obj124));
    let new_col_names = result(merge(col_names, _inp23));

    {obj115.$0, new_pivot_cols, new_col_names}
    );
let obj126 = (
      let key_col = lookup(obj125.$1, 2L);
      let sorted_indices = map(
        sort(
          result(
            for(
              key_col,
              appender[{f64,i64}],
              |b,i,e| merge(b, {e,i})
            )
          ),
          |x| x.$0
        ),
        |x| x.$1
      );
      let new_piv = map(
        obj125.$1,
        |x| result(
          for(
            x,
            appender[f64],
            |b,i,e| merge(b, lookup(x, lookup(sorted_indices, i)))
          )
        )
      );
      let new_index = result(
        for(
          obj125.$0,
          appender[vec[i8]],
          |b,i,e| merge(b, lookup(obj125.$0, lookup(sorted_indices, i)))
        )
      );
    {new_index, new_piv, obj125.$2}
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
let obj128 = (
    let unzip_builder = for(
      obj127,
      {appender[vec[i8]], appender[f64]},
      |b,i,e| {merge(b.$0, e.$0), merge(b.$1, e.$1)}
    );
    {result(unzip_builder.$0), result(unzip_builder.$1)}
    );
let obj129 = (
      obj128.$0
    );
let obj130 = (
     |_inp1,_inp12,_inp13,_inp14,_inp15,_inp16,_inp17,_inp18,_inp19,_inp20,_inp21,_inp22,_inp23|
  (let obj107=((let bs=(for(
    zip(
      _inp12,
      _inp13,
      _inp14,
      _inp15,
      _inp16,
      _inp17,
      _inp18,
      _inp19,
      _inp1,
      _inp20
    ),
    {dictmerger[{vec[i8],vec[i8]},{i64,i64},+],dictmerger[vec[i8],i64,+],dictmerger[vec[i8],i64,+]},
    |b#2,i#2,e|
      {merge(b#2.$0,{{e.$4,e.$5},{e.$0,1L}}),merge(b#2.$1,{e.$4,1L}),merge(b#2.$2,{e.$5,1L})}
  ));(let agg_dict=(result(
    bs.$0
  ));(let ind_vec=(sort(result(
    for(
      toVec(result(
          bs.$1
        )),
      appender[vec[i8]],
      |b#3,i#3,x#1|
        merge(b#3,x#1.$0)
    )
  ), |x#3|
    x#3));(let col_vec=(result(
    for(
      toVec(result(
          bs.$2
        )),
      appender[vec[i8]],
      |b#4,i#4,x#4|
        merge(b#4,x#4.$0)
    )
  ));{ind_vec,result(
    for(
      col_vec,
      appender[vec[f64]](len(col_vec)),
      |b#5,i#5,x#6|
        merge(b#5,result(
          for(
            ind_vec,
            appender[f64](len(ind_vec)),
            |b#6,i#6,x#8|
              merge(b#6,(let sum_len_pair=(lookup(agg_dict,{x#8,x#6}));((f64(sum_len_pair.$0))/(f64(sum_len_pair.$1)))))
          )
        ))
    )
  ),col_vec})))));(let obj108=((let group=(sort(toVec(result(
    for(
      _inp16,
      dictmerger[vec[i8],i64,+],
      |b#7,i#7,e#2|
        merge(b#7,{e#2,1L})
    )
  )), |x#9|
    x#9.$0));{result(
    for(
      group,
      appender[vec[i8]](len(group)),
      |b#8,i#8,x#10|
        merge(b#8,x#10.$0)
    )
  ),result(
    for(
      group,
      appender[i64](len(group)),
      |b#9,i#9,x#12|
        merge(b#9,x#12.$1)
    )
  )}));(let obj112=(result(
    for(
      zip(
        obj108.$0,
        result(
          for(
            obj108.$1,
            appender[bool],
            |b#10,i#10,x#14|
              merge(b#10,(x#14>=(i64(250))))
          )
        )
      ),
      appender[vec[i8]],
      |b#11,i#11,e#3|
        if(
          e#3.$1,
          merge(b#11,e#3.$0),
          b#11
        )
    )
  ));(let obj114=((let check_dict=(result(
    for(
      obj112,
      dictmerger[vec[i8],i32,+],
      |b#13,i#13,x#15|
        merge(b#13,{x#15,0})
    )
  ));result(
    for(
      obj107.$0,
      appender[bool],
      |b#14,i#14,x#16|
        merge(b#14,keyexists(check_dict,x#16))
    )
  )));(let obj115=({result(
    for(
      zip(
        obj107.$0,
        obj114
      ),
      appender[vec[i8]],
      |b#15,i#15,e#5|
        if(
          e#5.$1,
          merge(b#15,e#5.$0),
          b#15
        )
    )
  ),result(
    for(
      obj107.$1,
      appender[vec[f64]],
      |b#16,i#16,x#18|
        merge(b#16,result(
          for(
            zip(
              x#18,
              obj114
            ),
            appender[f64],
            |b#17,i#17,e#6|
              if(
                e#6.$1,
                merge(b#17,e#6.$0),
                b#17
              )
          )
        ))
    )
  ),obj107.$2});(let obj116=({obj115.$0,lookup(obj115.$1,lookup(result(
    for(
      obj115.$2,
      dictmerger[vec[i8],i64,+],
      |b#18,i#18,e#7|
        merge(b#18,{e#7,i#18})
    )
  ),_inp21))});(let obj125=({obj115.$0,result(
    merge(for(
      obj115.$1,
      appender[vec[f64]],
      |b#20,i#20,e#9|
        merge(b#20,e#9)
    ),result(
      (let a=(obj116.$1);(let a#1=(lookup(obj115.$1,lookup(result(
        for(
          obj115.$2,
          dictmerger[vec[i8],i64,+],
          |b#21,i#21,e#10|
            merge(b#21,{e#10,i#21})
        )
      ),_inp22)));for(
        zip(
          fringeiter(a),
          fringeiter(a#1)
        ),
        for(
          zip(
            simditer(a),
            simditer(a#1)
          ),
          appender[f64],
          |b#22,i#22,x#20|
            merge(b#22,(x#20.$0-x#20.$1))
        ),
        |b#23,i#23,x#21|
          merge(b#23,(x#21.$0-x#21.$1))
      )))
    ))
  ),result(
    merge(for(
      obj115.$2,
      appender[vec[i8]],
      |b#24,i#24,e#11|
        merge(b#24,e#11)
    ),_inp23)
  )});(let obj128=((let unzip_builder=(for(
    (let sum_dict=(result(
        for(
          zip(
            _inp16,
            _inp12
          ),
          dictmerger[vec[i8],{i64,i64},+],
          |b#27,i#27,e#14|
            merge(b#27,{e#14.$0,{e#14.$1,1L}})
        )
      ));(let mean_dict=(result(
        for(
          toVec(sum_dict),
          dictmerger[vec[i8],f64,+],
          |b#28,i#28,e#15|
            merge(b#28,{e#15.$0,((f64(e#15.$1.$0))/(f64(e#15.$1.$1)))})
        )
      ));result(
        for(
          sort(toVec(result(
              for(
                zip(
                  _inp16,
                  _inp12
                ),
                dictmerger[vec[i8],f64,+],
                |b#29,i#29,e#16|
                  merge(b#29,{e#16.$0,(let m=(lookup(mean_dict,e#16.$0));(((f64(e#16.$1))-m)*((f64(e#16.$1))-m)))})
              )
            )), |x#26|
              x#26.$0),
          appender[{vec[i8],f64}],
          |b#30,i#30,x#27|
            merge(b#30,{x#27.$0,(sqrt((x#27.$1/(f64((lookup(sum_dict,x#27.$0).$1-1L))))))})
        )
      ))),
    {appender[vec[i8]],appender[f64]},
    |b#31,i#31,e#17|
      {merge(b#31.$0,e#17.$0),merge(b#31.$1,e#17.$1)}
  ));{result(
    unzip_builder.$0
  ),result(
    unzip_builder.$1
  )}));(let obj131=({obj128.$0,obj128.$1});(let obj132=(obj131.$0);{(let sorted_indices=(result(
    for(
      sort(result(
          for(
            lookup(obj125.$1,2L),
            appender[{f64,i64}],
            |b#32,i#32,e#18|
              merge(b#32,{e#18,i#32})
          )
        ), |x#28|
          x#28.$0),
      appender[i64],
      |b#33,i#33,x#29|
        merge(b#33,x#29.$1)
    )
  ));{result(
    for(
      obj125.$0,
      appender[vec[i8]],
      |b#34,i#34,e#19|
        merge(b#34,lookup(obj125.$0,lookup(sorted_indices,i#34)))
    )
  ),result(
    for(
      obj125.$1,
      appender[vec[f64]],
      |b#35,i#35,x#30|
        merge(b#35,result(
          for(
            x#30,
            appender[f64](len(x#30)),
            |b#36,i#36,e#20|
              merge(b#36,lookup(x#30,lookup(sorted_indices,i#36)))
          )
        ))
    )
  ),obj125.$2}),(let unzip_builder#1=(for(
    zip(
      result(
        for(
          zip(
            obj132,
            obj131.$1
          ),
          appender[{vec[i8],f64}](len(obj132)),
          |b#37,i#37,e#21|
            merge(b#37,e#21)
        )
      ),
      (let check_dict#1=(result(
        for(
          obj112,
          dictmerger[vec[i8],i32,+],
          |b#40,i#40,x#31|
            merge(b#40,{x#31,0})
        )
      ));result(
        for(
          obj132,
          appender[bool](len(obj132)),
          |b#41,i#41,x#32|
            merge(b#41,keyexists(check_dict#1,x#32))
        )
      ))
    ),
    {appender[vec[i8]],appender[f64]},
    |b#43,i#43,e#23|
      if(
        e#23.$1,
        {merge(b#43.$0,e#23.$0.$0),merge(b#43.$1,e#23.$0.$1)},
        b#43
      )
  ));{result(
    unzip_builder#1.$0
  ),result(
    unzip_builder#1.$1
  )})}))))))))))
 obj128.$1
    );
let obj131 = ({obj129, obj130});
let obj132 = (
      obj131.$0
    );
let obj133 = (
      obj131.$1
    );
let obj134 = (
       result(
         for(
           zip(obj132, obj133),
           appender,
           |b, i, e| merge(b, e)
         )
       )
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
      map(
        obj132,
        |x: vec[i8]| keyexists(check_dict, x)
      )
    );
let obj136 = (
       result(
         for(
           zip(obj134, obj135),
           appender,
           |b, i, e| if (e.$1, merge(b, e.$0), b)
         )
       )
    );
let obj137 = (
    let unzip_builder = for(
      obj136,
      {appender[vec[i8]], appender[f64]},
      |b,i,e| {merge(b.$0, e.$0), merge(b.$1, e.$1)}
    );
    {result(unzip_builder.$0), result(unzip_builder.$1)}
    );
{obj126, obj137}
                """
            elif amen == 3:
                print function
                print "executing analysis"
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
#            print function


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
