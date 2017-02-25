
def invoke(func):
	'''
	Immediately invoke the decorated function and replace it with the result.

	Provides a capability similar to a common pattern in JavaScript known as
	IIFEs, or "immediately-invoked function expressions".
	It's purpose is to allow one to use inner functions to simulate scoped
	code blocks.

	Example: Life in a universe without the ``sorted`` function.
	>>> xs = [2, 5, 6, 1, 7, 3, 7, 5]
	>>> @invoke
	... def sorted_copy():
	...     # This function acts like a scoped code block;
	...     # the binding 'tmp' will have a scope limited to the function.
	...     tmp = list(xs)
	...     tmp.sort()
	...     return tmp
	...
	>>> xs
	[2, 5, 6, 1, 7, 3, 7, 5]
	>>> sorted_copy
	[1, 2, 3, 5, 5, 6, 7, 7]
	>>> tmp
	Traceback (most recent call last):
	    ...
	NameError: name 'tmp' is not defined
	'''
	return func()

def memoize(func):
	'''
	Decorator to memoize a function.

	This caches the output of every call to the function, and returns the
	recorded result whenever the same set of arguments are seen again.
	This is intended to be used on recursive functions that would otherwise
	result in an exceedingly large number of calls with the same values.
	This technique is known in academic circles as "dynamic programming."

	Example: The Fibonacci sequence.
	>>> @memoize
	... def fib(n):
	...    return 1 if n < 2 else fib(n-1) + fib(n-2)
	...
	>>> fib(10)
	89
	>>> # The dictionary of cached results can also be accessed directly.
	>>> # The keys are argument tuples.
	>>> fib.memo_dict[9,]
	55

	Tips:

	``memoize`` can only be used when all arguments to a function are
	hashable. Functions taking large variables as input is a bad idea.
	A common scenario is that all calls to the function may need access
	to some shared data source; in this case, consider returning a closure.

	>>> # Instead of this...
	>>> @memoize
	... def foo(x, y, massive_string):
	...     if x==0: return 3
	...     rec = foo(x-1, y//2, massive_string)
	...     # ... do stuff with massive_string ...
	...
	>>> foo(5, 6, "four score and seven years ago...")
	>>>
	>>> # Consider doing this...
	>>> def make_foo_func(massive_string):
	...     @memoize
	...     def inner(x, y):
	...         if x==0: return 3
	...         rec = inner(x-1, y//2)
	...         # ... do stuff with massive_string ...
	...     return inner
	...
	>>> foo = make_foo_func("four score and seven years ago...")
	>>> foo(5, 6)

	As a final note, be wary of returning mutable values, as any
	modifications to them will be reflected in the cache.
	In particular, this means you cannot memoize a generator!!

	>>> # Here is a generator function.
	>>> def foo(x):
	...     if x > 0: yield from foo(x-1)
	...     yield x
	...     if x > 0: yield from foo(x-1)
	...
	>>> list(foo(3))
	[0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0]
	>>>
	>>> # Try memoizing it and mayhem ensues!
	>>> foo = memoize(foo)
	>>> list(foo(3))
	[0, 1, 2, 3]
	>>> list(foo(3))
	[]

	You can correct this by making a tuple-returning wrapper and
	memoizing that instead.

	>>> @memoize
	... def foo(x):
	...     def inner():
	...         if x > 0: yield from foo(x-1)
	...         yield x
	...         if x > 0: yield from foo(x-1)
	...     return tuple(inner())
	...
	>>> list(foo(3))
	[0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0]
	>>> list(foo(3))
	[0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0]
	'''
	lookup = {}

	@functools.wraps(func)
	def wrapped(*args):
		if args not in lookup:
			lookup[args] = func(*args)
		return lookup[args]

	wrapped.memo_dict = lookup
	wrapped.memo_func = func
	return wrapped

def memoize_onevar(func):
	'''
	Decorator to memoize a function of one variable.

	In some cases using this version can be up to twice as fast
	as code using ``@memoize``.
	'''
	lookup = {}

	@functools.wraps(func)
	def wrapped(x):
		if x not in lookup:
			lookup[x] = func(x)
		return lookup[x]

	wrapped.memo_dict = lookup
	wrapped.memo_func = func
	return wrapped

def debug(file=sys.stderr):
	'''
	Intercept all calls to a function and print the input and output.

	Use delicately...
	'''
	def deco(func):
		@functools.wraps(func)
		def wrapped(*args, **kwargs):
			callstr = _format_call(func, *args, **kwargs)
			try: result = func(*args, **kwargs)
			except:
				print('%s = ...oh, my.' % callstr, file=file)
				raise
			else:
				print('%s = %r' % (callstr, result), file=file)
			return result
		return wrapped
	return deco

# technically, if we just wanted to indent for a single function,  we could
#  just use nonlocal to update a local 'indent' variable.
# However, using a global allows mutually recursive functions to be debugged
#  and "share" the indent level.
_debug_rec__indent_level = 0
def debug_rec(file=sys.stderr):
	'''
	Intercept all calls to a function and print the input and output in a
	 manner more suitable for debugging recursive functions.

	This differs from ``debug`` in that output is printed immediately, and
	is indented based on invocation depth. As one might imagine, this entire
	function is just a complete and utter hack, and one is advised to use
	it very delicately, and not while the wind is not blowing (lest it fly
	away and take the foundation with it)
	'''
	def deco(func):
		INDENT_CHARS = '  '
		MAX_INDENT = 16

		@functools.wraps(func)
		def wrapped(*args, **kwargs):
			global _debug_rec__indent_level # noqa
			# need to save this to have any sensible way of restoring indentation properly
			#  after hitting the max indent
			savedlevel = _debug_rec__indent_level
			indent = INDENT_CHARS * _debug_rec__indent_level

			_debug_rec__indent_level = min(MAX_INDENT, _debug_rec__indent_level+1)

			callstr = _format_call(func, *args, **kwargs)
			print(indent + '%s:' % callstr, file=file)

			try: result = func(*args, **kwargs)
			except:
				_debug_rec__indent_level = savedlevel
				print(indent + '%s failed horribly!' % callstr, file=file)
				raise
			else:
				_debug_rec__indent_level = savedlevel
				print(indent + '%s = %r' % (callstr, result), file=file)
			return result
		return wrapped
	return deco

def _format_call(func, *args, **kwargs):
	return '{}({}{}{})'.format(
		func.__name__,
		', '.join(repr(x) for x in args),
		', ' if (args and kwargs) else '',
		', '.join('%s=%r' % (k,v) for (k,v) in kwargs.items()),
	)

