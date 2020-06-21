#From here: https://github.com/znerol/py-fnvhash/blob/master/fnvhash/__init__.py
from numba import types, njit, jit, prange
from numba import deferred_type, optional
from numba import void,b1,u1,u2,u4,u8,i1,i2,i4,i8,f4,f8,c8,c16
from numba.typed import List, Dict
from numba.core.types import ListType, DictType, unicode_type, Array, Tuple
from numba.experimental import jitclass
from numba.core import sigutils 
import numpy as np
import re
from collections.abc import Iterable 
from collections import deque
import timeit
from pprint import pprint
from utils import cache_safe_exec
import inspect
N = 10

print("START")

def parse_signature(s):
	fn_match = re.match(r"(?P<out_type>\w+)\s?\((?P<arg_types>(?P<args>\w+(,\s?)?)+)\)", s)
	fn_dict = fn_match.groupdict()
	arg_types = [arg.strip() for arg in fn_dict['arg_types'].split(',')]
	return fn_dict['out_type'], arg_types

# def norm_check_types(s):


		# [time][op]

class Var(object):
	def __repr__(self):
		return "?"





class OperatorComposition(object):
	def __init__(self,tup):
		self.tup = tup
		self.template = self._gen_template(tup)

	def _gen_template(self,x):
		if(isinstance(x,(list,tuple))):
			rest = [self._gen_template(x[j]) for j in range(1,len(x))]
			return x[0].template.format(*rest)
		elif(isinstance(x,Var)):
			return "{}"
		else:
			return x

	def _execute_composition(self,tup,dq_args):
		L = len(tup)
		op = tup[0]
		resolved_args = []
		for i in range(1,L):
			t_i = tup[i]
			if(isinstance(t_i,tuple)):
				val = execute_composition(t_i,dq_args)
				resolved_args.append(val)
			elif(isinstance(t_i,Var)):
				a_i = dq_args.popleft()
				resolved_args.append(a_i)
			else:
				resolved_args.append(t_i)

		if(hasattr(op,'condition')):
			if(not op.condition(*resolved_args)):
				raise ValueError()
		return op.forward(*resolved_args)

	def __call__(self,*args):
		value = self._execute_composition(self.tup,deque(args))
		return value






class BaseOperator(object):
	#Static Attributes
	registered_operators = {}
	operators_by_uid = []

	#Subclass Attributes
	commutes = False
	muted_exceptions = []

	@classmethod
	def _init_signature(cls):
		assert hasattr(cls,'signature'), "Operator %r missing signature." % cls.__name__
		out_type, arg_types = parse_signature(cls.signature)
		out_type = TYPE_ALIASES.get(out_type,out_type)
		arg_types = [TYPE_ALIASES.get(x,x) for x in arg_types]
		print(arg_types)
		cls.out_type = out_type
		cls.arg_types = arg_types
		cls.signature = "{}({})".format(out_type,",".join(arg_types))
		cls.cond_signature = "u1({})".format(",".join(arg_types))

		u_types,u_inds = np.unique(arg_types,return_inverse=True)
		cls.u_arg_types = u_types
		cls.u_arg_inds = u_inds

		if(isinstance(cls.commutes,bool)):
			if(cls.commutes == True):
				cls.commutes = [np.where(i == u_inds)[0].tolist() for i in range(len(u_types))]
			else:
				cls.commutes = []
		else:
			assert(isinstance(cls.commutes,Iterable))

		right_commutes = {}
		for i in range(len(cls.commutes)):
			commuting_set =  cls.commutes[i]
			print(commuting_set)
			for j in range(len(commuting_set)-1,0,-1):
				right_commutes[commuting_set[j]] = commuting_set[0:j]
				for k in commuting_set[0:j]:
					assert u_inds[k] == u_inds[commuting_set[j]], \
					 "invalid 'commutes' argument, argument %s and %s have different types \
					  %s and %s" % (j, k, u_types[u_inds[j]], u_types[u_inds[k]])
		cls.right_commutes = right_commutes
		print(cls.right_commutes)
		print(cls.arg_types)

	@classmethod
	def _check_funcs(cls):
		assert hasattr(cls,'forward'), "Operator %r missing forward() function." % cls.__name__

		args = inspect.getargspec(cls.forward).args
		assert len(args) == len(cls.arg_types),\
		 	"%s.forward(%s) has %s arguments but signature %s has %s arguments." \
		 	%(cls.__name__,",".join(args),len(args),cls.signature,len(cls.arg_types))

		if(hasattr(cls,'condition')):
			args = inspect.getargspec(cls.condition).args
			assert len(args) == len(cls.arg_types),\
		 	"%s.condition(%s) has %s arguments but signature %s has %s arguments." \
		 	%(cls.__name__,",".join(args),len(args),cls.signature,len(cls.arg_types))




	@classmethod
	def _register(cls):
		name = cls.__name__.lower()
		
		if(name in cls.registered_operators):
			raise Warning("Duplicate Operator Definition %s" % name)

		uid = len(cls.operators_by_uid)
		cls.uid = uid
		cls.operators_by_uid.append(cls)
		cls.registered_operators[name] = cls

	@classmethod
	def _init_template(cls):
		if(not hasattr(cls,"template")):
			brks = ["{%i}"%i for i in range(len(cls.arg_types))]
			cls.template = "{name}("+",".join(brks)+")"

	
	def __init_subclass__(cls, **kwargs):
		super().__init_subclass__(**kwargs)

		cls._init_signature()
		cls._check_funcs()
		cls._register()
		cls._init_template()

		compile_forward(cls)

	@classmethod
	def _assert_cargs(cls,args,allow_zero=True):
		# cls = type(self)
		assert (allow_zero and len(args) == 0) or len(cls.arg_types) == len(args), \
			"incorrect number of arguments for signature: %s" % cls.signature
		return args if(len(args) != 0) else [None]*len(cls.arg_types)

	def _assert_iargs(self,args,allow_zero=True):
		assert (allow_zero and len(args) == 0) or len(self.arg_types) == len(args), \
			"incorrect number of arguments for signature: %s" % self.signature
		return args if(len(args) != 0) else [None]*len(self.arg_types)

	def __init__(self,*args):
		pass
		

		

	def __new__(cls,*args):
		raise NotImplemented()
		print(cls)

		args = cls._assert_cargs(args)
		arg_types = []
		arg_strs = []
		for typ, arg in zip(cls.arg_types,args):
			if(isinstance(arg,BaseOperator)):
				arg_types += arg.arg_types
				arg_strs.append(arg.__name__)
			elif(arg is None):
				arg_types.append(typ)
				arg_strs.append("?")
			else:
				arg_strs.append(arg)
		arg_types = arg_types
		signature = cls.out_type + "("+",".join(arg_types) +")"

		def f(*args):
			pass


		print(arg_strs)
		return type("MOOSE",(BaseOperator,),{'signature' : signature, 'forward' : f})


	def get_template(self,*args):
		iargs, cls = self._assert_iargs(args), type(self)

		arg_strs = []
		for arg in self.args:
			if(isinstance(arg,BaseOperator)):
				arg_strs.append(arg.get_template())
			elif(arg is None):
				arg_strs.append("{}")
			else:
				arg_strs.append(str(arg))

		temp = cls.template.format(*arg_strs,name=cls.__name__)
		iarg_strs = ["{}" if (arg is None) else str(arg) for arg in iargs ]
		print(temp, iarg_strs)
		return temp.format(*iarg_strs)

	def __str__(self):
		return self.get_template()

	def __call__(self,*args):
		self._assert_iargs(args,False)
		raise NotImplementedError()
	

LOOPLIFT_UNJITABLES = True
UID_START = 1
TYPE_ALIASES = {
	"float" : 'f8',
	"flt" : 'f8',
	"number" : 'f8',
	"string" : 'unicode_type',
	"str" : 'unicode_type'
}

# ALLOWED_TYPES = []

def compile_forward(op):
	_ = "    "
	nopython = True
	forward_func = njit(op.forward,cache=True)
	condition_func =  njit(op.condition,cache=True) if(hasattr(op,'condition')) else None
	try:
		forward_func.compile(op.signature)
	except Exception:
		forward_func = op.forward
		nopython= False

	if(condition_func != None):
		try:
			condition_func.compile(op.cond_signature)
		except Exception as e:
			raise e
			condition_func = op.condition
			nopython= False


	# condition_func, nopython = njit(op.forward,cache=True), True
	# try:
	# 	forward_func.compile(op.signature)
	# except Exception:
	# 	forward_func, nopython = op.forward, False

	f_name = op.__name__+"_forward"
	if(nopython):
		header = '@jit(nogil=True, fastmath=True, cache=True) \n'
	elif(LOOPLIFT_UNJITABLES and len(op.muted_exceptions) == 0):
		header = '@jit(fastmath=True, looplift=True, forceobj=True) \n'
	else:
		header = ""
	func_def =	'def {}({}): \n' #+ \

	func_def = func_def.format(f_name,
		 ",".join(["x%i"%i for i in range(len(op.u_arg_types))]) )

	defs = _+", ".join(["L%i"%i for i in range(len(op.u_arg_types))]) + " = " + \
			  ", ".join(["len(x%i)"%i for i in range(len(op.u_arg_types))]) + "\n"

	defs += _+"out = np.empty((%s),dtype=np.int64)\n"%",".join(["L%s"%x for x in op.u_arg_inds])
	defs += _+"d = Dict.empty({},i8)\n".format(op.out_type)
	defs += _+"uid = {}\n".format(UID_START)
				
	loops = ""
	curr_indent = 1
	for i in range(len(op.arg_types)):
		curr_indent = i+1
		l = _*curr_indent + "for i{} in range(L{}):\n"
		l = l.format(i,op.u_arg_inds[i])
		loops += l
	

	all_indicies = ["i%s"%i for i in range(len(op.arg_types))]
	arg_terms = ["x{}[i{}]".format(op.u_arg_inds[i],i) for i in range(len(op.arg_types))]
	cond_expr = "{}\n"
	if(len(op.right_commutes) > 0 or condition_func != None):
		curr_indent += 1
		conds = []

		if(len(op.right_commutes) > 0):
			for i_a, i_bs in op.right_commutes.items():
				conds.append("i{} >= i{}".format(i_a,i_bs[-1]))
		if(condition_func != None):
			conds.append("c({})".format(",".join(arg_terms)))

		cond_expr =  _*curr_indent     + "if({}):\n".format(" and ".join(conds))
		cond_expr += "{}\n"#_*(curr_indent+1) + "{}\n"
		cond_expr += _*(curr_indent)   + "else:\n"
		cond_expr += _*(curr_indent+1) + "out[{}] =  0\n".format(",".join(all_indicies))
		print("COMMUTES", op.right_commutes)

	# use_try = False
	try_expr = "{}"
	if(len(op.muted_exceptions) > 0):
		# use_try = True
		try_expr = _*(curr_indent+1) + "try:\n"
		try_expr += "{}\n"
		try_expr += _*(curr_indent+1) + "except ({}):\n".format(",".join([x.__name__ for x in op.muted_exceptions]))
		try_expr += _*(curr_indent+2) + "out[{}] =  0\n".format(",".join(all_indicies))
		curr_indent += 1

	
	exec_code =  _*(curr_indent+1) +"v = f({})\n".format(",".join(arg_terms))
	exec_code += _*(curr_indent+1) +"if(v not in d):\n"
	exec_code += _*(curr_indent+2) +"d[v] = uid; uid +=1;\n"
	exec_code += _*(curr_indent+1) +"out[{}] = d[v]".format(",".join(all_indicies))


	exec_code = try_expr.format(exec_code)

	cond_expr = cond_expr.format(exec_code)
	ret_expr = _+"return out, d\n"
	source = header + func_def + defs +  loops + cond_expr+ret_expr
	print(source)
	print("END----------------------")
	l,g = cache_safe_exec(source,gbls={'f':forward_func,'c': condition_func,**globals()})
	print("TIS HERE:",l[f_name])
	if(nopython):
		op.broadcast_forward = l[f_name]
	else:
		print(op.__name__,"NOPYTHON")
		_bf = l[f_name]
		def bf(*args):
			global f
			f = forward_func
			return _bf(*args)
		op.broadcast_forward = bf
	

	# print(func_def + defs +  loops + cond_expr)

				# '	return {}({}) \n' + \
				# 'out_func = {}'

# def normalize_types():

import math
#from here: https://stackoverflow.com/questions/18833759/python-prime-number-checker
@njit(cache=True)
def is_prime(n):
    if n % 2 == 0 and n > 2: 
        return False
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        if n % i == 0:
            return False
    return True

class SquaresOfPrimes(BaseOperator):
	signature = 'float(float)'
	def condition(x):
		return is_prime(x)

	def forward(x):
		return x**2

class EvenPowersOfPrimes(BaseOperator):
	signature = 'float(float,float)'
	def condition(x,y):
		b = is_prime(x)
		a = (y % 2 == 0) and (y > 0) and (y == int(y))
		return a and b

	def forward(x,y):
		return x**y

class Add(BaseOperator):
	commutes = True
	signature = 'float(float,float)'
	def forward(x, y):
		return x + y

class Subtract(BaseOperator):
	commutes = False
	signature = 'float(float,float)'
	def forward(x, y):
		return x - y

class Concatenate(BaseOperator):
	commutes = True
	signature = 'string(string,string)'
	def forward(x, y):
		return x + y

class StrToFloat(BaseOperator):
	signature = 'float(string)'
	muted_exceptions = [ValueError]
	def forward(x):
		return float(x)



# a = Add(None,Add())
# print(type(a).signature , ":", a.signature )
# print(a.get_template(1,2,None))

# print(a.forward)
# a(1,2,3)
v = Var()
t = (Add,v,v)
oc = OperatorComposition(t)
print(oc)
print(oc(1,2))

# Add(None)

raise ValueError("STOP")
# compile_forward(Add)
# compile_forward(Subtract)
# compile_forward(Concatenate)

# def Multiply(x, y):
# 	return x * y

# def forward(state, goal, operators):
# 	for op in operators:
# 		for i in range(len(state)):
# 			for j in range(len(state)):
# 				pass




# @njit(nogil=True,fastmath=True,parallel=True) 
# def Add_forward1(x0,x1): 

#     L0, L1 = len(x0), len(x1)
#     Total_Len = (L0)*(L0-1)*(L0-2)/(1*2*3) * \
#     			 L1 
#     Total_Len = int(Total_Len)    			 
#     # print(Total_Len)
#     # Total_Len = L0*L0*L0*L1
#     # out = np.empty((L0,L0,L1,L0))
#     out = np.empty((Total_Len,))
#     ind = 0
#     for i0 in prange(0,L0):
#         for i1 in prange(i0+1,L0):
#             for i2 in prange(0,L1):
#                 for i3 in prange(i1+1,L0):
#                 	# ind = i0*L0*L0*L1 + i1*L0*L1 + i2*L0 + i3
#                 	# out[i0,i1,i2,i3] = x0[i0] + x0[i1] + x0[i3] * x1[i2]
#                 	out[ind] = x0[i0] + x0[i1] + x0[i3] * x1[i2]
#                 	ind += 1
#     return out

bloop_type = ListType(u8[:])
sloop_type = u8[:]
@njit(nogil=True,fastmath=True,parallel=True,cache=True) 
def Grumbo_forward1(x0,x1): 
	L0, L1 = len(x0), len(x1)

	out = np.empty((L0,L0,L1,L0))
	da =[]
	for i0 in range(0,L0):
		da.append(Dict.empty(f8,i8))

	for i0 in prange(0,L0):
		d = da[i0]
		# ind = 0
		for i1 in range(i0+1,L0):
			for i2 in range(i1+1,L0):
				for i3 in range(0,L1):
					v = x0[i0] + x0[i1] + x0[i2] * x1[i3]
					if(v not in d):
						d[v] = 1

					out[i0,i1,i2,i3] = v
					# beezl = np.array([u4(i0),u4(i1),u4(i2),u4(i3)])

	d_out = Dict.empty(f8,i8)
	for i0 in range(0,L0):
		for v in da[i0]:
			if(v not in d_out):
				d_out[v] = 1

	u_vs = np.empty(len(d_out))
	for i,v in enumerate(d_out):
		u_vs[i] = v

	# sqeep = np.where(out == 1)
	# out[sqeep[0]] = 7
	return u_vs


# HE_deffered = deferred_type()
# @jitclass([('op_id', i8),
#            ('args',  i8[:]),
#            ('next', optional(HE_deffered))])
# class HistElm(object):
#     def __init__(self,op_id,args):
#         self.op_id = op_id
#         self.args = args
#         self.next = None
# # print(BinElem)
# HE = HistElm.class_type.instance_type
# HE_deffered.define(HE)


bloop_type = ListType(u8[:])
sloop_type = u8[:]
@njit(nogil=True,fastmath=True,parallel=False,cache=True) 
def Grumbo_forward2(x0,x1): 
	L0, L1 = len(x0), len(x1)

	out = np.empty((L0,L0,L1,L0))
	# da =[]
	# for i0 in range(0,L0):
	# 	da.append(Dict.empty(f8,i8))
	d = Dict.empty(f8,i8)
	uid = 0
	for i0 in range(0,L0):
		# d = da[i0]
		# uid = 0
		# d = Dict.empty(f8,i8)
		# for i1 in range(i0+1,L0):
		# 	for i2 in range(i1+1,L0):
		for i1 in range(0,L0):
			for i2 in range(0,L0):
				for i3 in range(0,L1):
					if(i1 > i0 and i2 > i1):
						v = x0[i0] + x0[i1] + x0[i2] * x1[i3]
						# v = x0[i0] + x0[i1]# + x0[i2] + x0[i3] 
						if(v not in d):
							d[v] =uid; uid +=1; 
						out[i0,i1,i2,i3] = d[v]
						# HistElm(0,np.array([i0,i1,i2,i3]))
					else:
						out[i0,i1,i2,i3] = 0
					
	# d_out = d
	# u_vs = np.empty(len(d_out))
	# for i,v in enumerate(d_out):
	# 	u_vs[i] = v

	# sqeep = np.where(out == 1)
	return out, d


@njit(nogil=True,fastmath=True,parallel=False,cache=True) 
def Add_forward(x0): 
	L0 = len(x0)
	out = np.empty((L0,L0),dtype=np.int64)
	d = Dict.empty(f8,i8)
	uid = 1
	for i0 in range(0,L0):
		for i1 in range(0,L0):
			if(i1 > i0):
				v = x0[i0] + x0[i1]
				if(v not in d):
					d[v] = uid; uid +=1; 
				out[i0,i1] = d[v]
			else:
				out[i0,i1] = 0
	return out, d


@njit(nogil=True,fastmath=True,parallel=False,cache=True) 
def Subtract_forward(x0): 
	L0 = len(x0)
	out = np.empty((L0,L0),dtype=np.int64)
	d = Dict.empty(f8,i8)
	uid = 1
	for i0 in range(0,L0):
		for i1 in range(0,L0):
			if(i1 != i0):
				v = x0[i0] - x0[i1]
				if(v not in d):
					d[v] = uid; uid +=1; 
				out[i0,i1] = d[v]
			else:
				out[i0,i1] = 0
	return out, d



@njit(nogil=True,fastmath=True,parallel=False,cache=True) 
def cat_forward(x0): 
	L0= len(x0)
	out = np.empty((L0,L0),dtype=np.int64)
	d = Dict.empty(unicode_type,i8)
	uid = 1
	for i0 in range(0,L0):
		# d = da[i0]
		for i1 in range(0,L0):
			# for i2 in range(i1+1,L0):
			# 	for i3 in range(0,L0):
			# if(i1 != i0):
				v = x0[i0] + x0[i1]# + x0[i2] + x0[i3] 
				if(v not in d):
					d[v] = uid; uid +=1; 
				out[i0,i1] = d[v]
			# else:
			# 	out[i0,i1] = 0
				# d[v] = 1
			# print(v)

			# out[i0,i1,i2,i3] = v

	# d_out = Dict.empty(unicode_type,i8)
	# for i0 in range(0,L0):
	# 	for v in da[i0]:
	# 		if(v not in d_out):
	# 			d_out[v] = 1
	# print(d_out)

	# u_vs = np.empty(len(d_out))
	# for i,v in enumerate(d_out):
	# 	u_vs[i] = v
	return out, d#, uid

@njit(nogil=True,fastmath=True,cache=True) 
def join_new_vals(vd,new_ds,depth):
	for d in new_ds:
		for v in d:
			if(v not in vd):
				vd[v] = depth
	return vd

@njit(nogil=True,fastmath=True,cache=True) 
def array_from_dict(d):
	out = np.empty(len(d))
	for i,v in enumerate(d):
		out[i] = v
	return out

@njit(nogil=True,fastmath=True,cache=True) 
def list_from_dict(d):
	out = List()
	for i,v in enumerate(d):
		out.append(v)
	return out
	
class NBRT_KnowledgeBase(object):
	def __init__(self):
		self.hists = {}
		self.hist_structs = {}
		self.curr_infer_depth = 0
		# self.vmaps = {}
		self.u_vds = {}
		self.u_vs = {}
		self.registered_types ={'f8': f8, 'unicode_type' : unicode_type}


# @njit(nogil=True,fastmath=True,parallel=False) 

def insert_record(kb,depth,op, btsr, vmap):
	# print('is')
	typ = op.out_type
	if(typ not in kb.hist_structs):
		typ_cls = kb.registered_types[typ]
		kb.hist_structs[typ] = Tuple([i8,
									 i8[::1], i8[::1], ListType(unicode_type),
									 DictType(typ_cls,i8)])

	typ_store = kb.hists[typ] = kb.hists.get(typ,Dict.empty(i8,ListType(kb.hist_structs[typ])))
	tsd = typ_store[depth] = typ_store.get(depth, List.empty_list(kb.hist_structs[typ]))
	tsd.append(tuple([op.uid,
					  btsr.reshape(-1), np.array(btsr.shape,np.int64), List(op.arg_types),
					  vmap]))
	# print('istop')
	return tsd

# @njit(cache=True):
# def extract_vmaps():

# Add.broadcast_forward = Add_forward
# Subtract.broadcast_forward = Subtract_forward
# Concatenate.broadcast_forward = cat_forward
def forward(kb,ops):
	# print("F_start")
	output_types = set([op.out_type for op in ops])
	new_records = {typ:[] for typ in output_types}
	depth = kb.curr_infer_depth = kb.curr_infer_depth+1
	
	for op in ops:
		typ = op.out_type
		args = [kb.u_vs[t] for t in op.u_arg_types]
		btsr, vmap = op.broadcast_forward(*args)
		records = insert_record(kb,depth,op,btsr,vmap)
		new_records[typ] = records
		
	for typ in output_types:
		if(typ in new_records):
			# print("A")
			vmaps = List([rec[4] for rec in new_records[typ]])
			# print("_A")
			kb.u_vds[typ] = join_new_vals(kb.u_vds[typ],vmaps,depth)

			if(typ == TYPE_ALIASES['float']):
				kb.u_vs[typ] = array_from_dict(kb.u_vds[typ])
			else:
				kb.u_vs[typ] = list_from_dict(kb.u_vds[typ])
	# print("F_end")

HE_deffered = deferred_type()
@jitclass([('op_uid', i8),
		   ('args', i8[:])])
class HistElm(object):
	def __init__(self,op_uid,args):
		self.op_uid = op_uid
		self.args = args
HE = HistElm.class_type.instance_type
HE_deffered.define(HE)

# def new_HE_list(n):
# 	out = List.empty_list(ListType(HE))
# 	for i in range(n):
# 		out.append(List.empty_list(HE))
# 	return out
@njit(cache=True)
def select_from_list(lst,sel):
	out = List()
	for s in sel:
		out.append(lst[s])
	return out

def select_from_collection(col,sel):
	if(isinstance(col,np.ndarray)):
		return col[sel]
	elif(isinstance(col,List)):
		return select_from_list(col,sel)


he_list = ListType(HE)
@njit(cache=True)
def HistElmListList():
	return List.empty_list(he_list)

def retrace_solutions(kb,ops,goal,g_typ):

	# depth = kb.u_vds[g_typ][goal]
	u_vds = kb.u_vds[g_typ]
	records = kb.hists[g_typ]
	# goal = kb.registered_types[g_typ](goal)
	
	# print("RS_S")
	goals = List.empty_list(kb.registered_types[g_typ])
	goals.append(goal)
	# print("RS_E")

	# hist_elems, , new_inds = retrace_one(goals,records)
	# print(":0")
	hist_elems = HistElmListList()#List.empty_list(ListType(HE))#new_HE_list(1)#List([List.empty_list(HE)],listtype=ListType(HE))
	arg_inds = retrace_back_one(goals,records,u_vds,hist_elems)

	out = [{g_typ: hist_elems}]
	
	# goals = kb.u_vs[g_typ][arg_inds[g_typ]]
	finished, i = False, 1
	while(not finished):
		nxt = {}
		# print("AQUI",[(k,type(v),v) for k,v in arg_inds.items()])
		for typ in arg_inds:
			records,u_vds = kb.hists[typ], kb.u_vds[typ]
			hist_elems = HistElmListList()#List.empty_list(ListType(HE))#new_HE_list(len(goals))#List([List.empty_list(HE) for i in range(len(goals))])
			
			goals = select_from_collection(kb.u_vs[typ],arg_inds[typ])
			arg_inds = retrace_back_one(goals,records,u_vds,hist_elems)
			nxt[typ] = hist_elems
			if(len(arg_inds) == 0):
				finished = True
				# print("FINISHED")
				break
		out.append(nxt)
		assert i <= kb.curr_infer_depth, "Retrace has persisted past current infer depth."
		i += 1

			
	# for i in range(len(out)):
	# 	print(i)
	# 	pprint(out[i])

		



	# hist_elems = List.empty_list(ListType(HE))#new_HE_list(1)#List([List.empty_list(HE)],listtype=ListType(HE))
	# arg_inds = retrace_back_one(goals,records,u_vds,hist_elems)
	# print("1:",arg_inds)
	# for typ in arg_inds:
	# 	goals = kb.u_vs[typ][arg_inds[typ]]
	# 	records = kb.hists[typ]
	# 	hist_elems = List.empty_list(ListType(HE))#new_HE_list(len(goals))#List([List.empty_list(HE) for i in range(len(goals))])
	# 	u_vds = kb.u_vds[typ]
	# 	arg_inds = retrace_back_one(goals,records,u_vds,hist_elems)


	# 	print("2:",arg_inds)
		# arg_inds = retrace_back_one(u_vs,records,hist_elems)
		
	# new_goals = new

	# for typ in new_inds:
	# 	u_vs = kb.u_vs[typ][new_inds[typ]]
	# 	print(kb.u_vds[typ])
	# 	print(kb.u_vs[typ])
	# 	print(u_vs)
	# 	for v in u_vs:
	# 		print(kb.u_vds[typ][v])
	# print("moo")
	# for i,record in enumerate(records):
	# 	_hist, shape, vmap = record
	# 	hist = _hist.reshape(shape)

	# 	# print("MEEP")
	# 	# print(np.where(hist == 0))
		
	# 	# print(_hists,_vmaps)
	# 	# for hist,vmap in zip(_hists,_vmaps):
	# 	if(goal in vmap):
	# 		print(ops)
	# 		print(vmap[goal])
	# 		print(np.where(hist == vmap[goal]))

#Adapted from here: https://gitter.im/numba/numba?at=5dc1f9d13d669b28a0408463
@njit(nogil=True,fastmath=True,cache=True) 
def unravel_indicies(indicies, shape):
	sizes = np.zeros(len(shape), dtype=np.int64)
	result = np.zeros(len(shape), dtype=np.int64)
	sizes[-1] = 1
	for i in range(len(shape) - 2, -1, -1):
		sizes[i] = sizes[i + 1] * shape[i + 1]

	out = np.empty((len(indicies),len(shape)), dtype=np.int64)
	for j,index in enumerate(indicies):
		remainder = index
		for i in range(len(shape)):
			out[j,i] = remainder // sizes[i]
			remainder %= sizes[i]
	return out

i8_i8_dict = DictType(i8,i8)
i8_arr = i8[:]
@njit(nogil=True,fastmath=True,cache=True) 
def retrace_back_one(goals,records,u_vds,hist_elems):
	unq_arg_inds = Dict.empty(unicode_type, i8_i8_dict)
	pos_by_typ = Dict.empty(unicode_type, i8)


	# for record in records[0]:
	# 	op_name, _hist, shape, arg_types, vmap = record
	# 	for typ in arg_types:
	# 		if(typ not in unq_arg_inds):
	# 			unq_arg_inds[typ] = Dict.empty(i8,u1)
	# 			pos_by_typ[typ] = 0

	#Go through each goal in goals, and find applications of operations 
	#	which resulted in each subgoal. Add the indicies of args of each 
	#	goal satisficing operation application to the set of subgoals for 
	#	the next iteration.
	# _hist_elems = List.empty_list(ListType(HE))
	for goal in goals:
		hist_elems_k = List.empty_list(HE)
		hist_elems.append(hist_elems_k)
		shallowest_depth = u_vds[goal]
		# print([x for x in records.keys()],shallowest_depth)
		# print([x for x in u_vds.keys()])
		if(shallowest_depth == 0): continue
		_records = records[shallowest_depth]
		for record in _records:
			op_uid, _hist, shape, arg_types, vmap = record

			#Make a dictionary for each type to collect unique arg values
			# for _records in records:
			# 	print(_records)
			for typ in arg_types:
				if(typ not in unq_arg_inds):
					unq_arg_inds[typ] = Dict.empty(i8,i8)
					pos_by_typ[typ] = 0

			if(goal in vmap):
				wher = np.where(_hist == vmap[goal])[0]
				inds = unravel_indicies(wher,shape)
				
				for i in range(inds.shape[0]):
					arg_uids = np.empty(inds.shape[1],np.int64)
					for j in range(inds.shape[1]):
						d = unq_arg_inds[arg_types[j]]
						v = inds[i,j]
						if(v not in d):
							d[v] = pos_by_typ[typ]
							pos_by_typ[typ] += 1
						arg_uids[j] = d[v]
					
					# print(arg_uids)
					hist_elems_k.append(HistElm(op_uid,arg_uids))

	#Consolidate the dictionaries of unique arg indicies into arrays
	out_arg_inds = Dict.empty(unicode_type,i8_arr)
	for typ in unq_arg_inds:
		u_vals = out_arg_inds[typ] = np.empty((len(unq_arg_inds[typ])),np.int64)
		for i, v in enumerate(unq_arg_inds[typ]):
			u_vals[i] = v
	# print(out_arg_inds)

	return out_arg_inds







def how_search(kb,ops,goal,search_depth=1):
	if(isinstance(goal, (int,float))):
		g_typ = TYPE_ALIASES['float']
	elif(isinstance(goal, (str))):
		g_typ = TYPE_ALIASES['string']
	else:
		raise NotImplemented("Object goals not implemented yet")

	# depth = 0
	while(goal not in kb.u_vds[g_typ]):
		if(kb.curr_infer_depth > search_depth): break
		forward(kb,ops)
		for typ in kb.registered_types:
			# print("MOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO",kb.curr_infer_depth)
			# print(typ)
			print(kb.u_vs[typ])
			pass


	if(goal in kb.u_vds[g_typ]):
		retrace_solutions(kb,ops,goal,g_typ)
	# 	print("FOUND IT ", kb.curr_infer_depth)

		
	# else:
	# 	print("NOT HERE")




def time_ms(f):
		f() #warm start
		return " %0.6f ms" % (1000.0*(timeit.timeit(f, number=N)/float(N)))




X = np.array(np.arange(10),np.float32)
y = 17
# forward(X,y,[Add,Multiply])
# print("OUT",Add_forward1(X,X))
# print(Add_forward2(X,X))

@njit(nogil=True,fastmath=True,cache=True) 
def make_S(offset):
	S = List.empty_list(unicode_type)
	for x in range(48+offset,48+offset+5):
	# for x in range(97+offset,97+offset+5):
		S.append("1"+chr(x))
	S.append("a")
	return S#np.array(S)
S1 = make_S(0)
S2 = make_S(5)


@njit(cache=True)
def newVmap(X,typ):
	d = Dict.empty(typ,i8)
	for x in X:
		d[x] = 0
	return d

def buildKB():
	kb = NBRT_KnowledgeBase()

	kb.u_vs['unicode_type'] = S1
	kb.u_vs['f8'] = X

	kb.u_vds['unicode_type'] = newVmap(S1,unicode_type)
	kb.u_vds['f8'] = newVmap(X,f8)

	# for s in S1:
	# 	kb.u_vds['unicode_type'][s] = 0
	# for x in X:
	# 	kb.u_vds['f8'][x] = 0

	return kb

print("MID")
kb = buildKB()
print("MID2")
# print("STAAAAART")
# for op in [Add,Subtract,Concatenate]:
# 	print(op, op.uid)
# for op in [Add,Subtract,Concatenate]:
# 	print(op, op.uid)
# print(BaseOperator.operators_by_uid)
# forward(kb,[Add,Subtract,Concatenate])
# forward(kb,[Add,Subtract,Concatenate])
import time
# start = time.time()
# how_search(kb,[Add,Subtract,Concatenate],21,2)
# end = time.time()
# print("Time elapsed: ",end - start)

# print(Add.broadcast_forward.stats.cache_hits)


kb = buildKB()
start = time.time()
how_search(kb,[StrToFloat],"abab",1)
end = time.time()
print("Time elapsed: ",end - start)


kb = buildKB()
start = time.time()
print("MOOSE PIMPLE")
forward(kb,[SquaresOfPrimes])
print(kb.u_vs)
# how_search(kb,[HalfOfEven],100,1)
end = time.time()
print("Time elapsed: ",end - start)

# kb = buildKB()
# start = time.time()
# how_search(kb,[Add,Subtract,Concatenate],"abab",2)
# end = time.time()
# print("Time elapsed: ",end - start)

# forward(kb,[Add,Subtract,Concatenate])
# for typ in kb.registered_types:
# 	print(typ)
# 	print(kb.u_vs[typ])

# print(cat_forward1(S))

@njit(nogil=True,fastmath=True,cache=True) 
def g1():
	# uid = 1; d = Dict.empty(f8,i8)
	# Add_forward1(uid,d, X,X)	
	Grumbo_forward1(X,X)	

@njit(nogil=True,fastmath=True,cache=True) 
def g2():
	# uid = 1; d = Dict.empty(f8,i8)
	# Add_forward2(uid,d, X,X)	
	Grumbo_forward2(X,X)	

# @njit
def s1():
	# uid = 1; d = Dict.empty(unicode_type,i8)
	# cat_forward1(uid,d, S1)	
	cat_forward(S1)	

def f1():
	kb = buildKB()
	forward(kb,[Add,Subtract])
	forward(kb,[Add,Subtract])
	forward(kb,[Add,Subtract])
	forward(kb,[Add,Subtract])
	forward(kb,[Add,Subtract])
	forward(kb,[Add,Subtract])

def h1():
	kb = buildKB()
	how_search(kb,[Add,Subtract],21,2)

# d  =Dict()
# d['unicode_type'] = unicode_type
# d['f8'] = f8
# print("g1", time_ms(g1))
# print("g2", time_ms(g2))
# print("s1", time_ms(s1))
print("forward-depth-5", time_ms(f1))
print("search-21-depth-2", time_ms(h1))