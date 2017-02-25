import argparse, sys, json

class Spec:
	def __init__(self, comment='#', gnu_order='dblw', json_order='dblw'):
		(self._comment, self._gnu_order, self._arr_order) = (comment, gnu_order, json_order)
		self._arr_to_gnu = Spec._solve_permutation(json_order, gnu_order)
		self._gnu_to_arr = Spec._solve_permutation(gnu_order, json_order)

	def comment(self, comment): return Spec(comment, self._gnu_order, self._arr_order)
	def order(self, gnu, json): return Spec(self._comment, gnu, json)
	def has_nontrivial_order(self): return self._gnu_order != self._arr_order

	@staticmethod
	def _solve_permutation(start, end):
		start = list(start)
		end = list(end)

		if set(start) != set(end):
			raise ValueError('{!r} is not a permutation of {!r}'.format(end, start))

		if len(start) != len(set(start)): raise ValueError('{!r} has duplicates'.format(start))
		if len(end)   != len(set(end)):   raise ValueError('{!r} has duplicates'.format(end))

		d = {c:i for (i,c) in enumerate(start)}
		out = [d[c] for c in end]
		assert [start[i] for i in out] == end, "postcondition"
		return out

def dump(data, file, spec=Spec()):
	'''
	Dump a quadruply-nested iterable of floats into a gnuplot data file.

	Data is separated by spaces, then line breaks, then blank lines,
	and then double blank lines.
	'''
	print(dumps(data, spec=spec), file=file)

def load(file, spec=Spec()):
	'''
	Load a gnuplot data file into a quadruply-nested list.

	Data is delimited by non-line-breaking whitespace, then line breaks,
	then blank lines, and then double blank lines.
	'''
	# Split to identify comment lines
	# (defined by gnuplot as a line whose first nonblank is some specified delimiter)
	lines = [line.strip() for line in file]
	if spec._comment:
		lines = [line for line in lines if not line.startswith(spec._comment)]

	# used to filter out empty blocks that split() may produce at the beginning or end
	WHITESPACE = set(' \n\r\t')
	def is_blank(s):
		return not bool(set(s) - WHITESPACE)

	# Rejoin to identify blank line sequences.
	concat = '\n'.join(lines)
	data = [[[[float(x) for x in line.split()]
		for line in block.split('\n')]
		for block in index_block.split('\n\n') if not is_blank(block)]
		for index_block in concat.split('\n\n\n') if not is_blank(index_block)]

	if spec.has_nontrivial_order():
		import numpy
		data = numpy.transpose(data, spec._gnu_to_arr).tolist()
	return data

def dumps(data, spec=Spec()):
	''' Dump to string. '''
	if spec.has_nontrivial_order:
		import numpy
		# iterators to lists...
		data = list(list(list(list(x) for x in x) for x in x) for x in data)
		data = numpy.transpose(data, spec._arr_to_gnu)

	s = '\n\n\n'.join(
	      '\n\n'.join(
	        '\n'.join(
	          ' '.join(map(str, line))
	        for line in block)
	      for block in index_block)
	    for index_block in data)
	return s

def loads(s, spec=Spec()):
	''' Load from string. '''
	from io import StringIO
	return load(file=StringIO(s), spec=spec)

#--------------------------
# CLI

def cli_encoder_main(): return _shared_main('enc')
def cli_decoder_main(): return _shared_main('dec')

def _shared_main(mode):
	assert mode in ['enc', 'dec']
	normalize = lambda s: ' '.join(s.split())

	parser = argparse.ArgumentParser(
		description={
			'enc': "Converts a 4D JSON array into a gnuplot data file.",
			'dec': "Converts a gnuplot data file to a 4D JSON array.",
		}[mode],
		epilog=normalize('''
			This script does not care whether the data file holds a matrix, or 2D data, etc.
			It merely {} (index 1) double blank lines, (index 2) single blank lines,
			(index 3) lines, then (index 4) spaces.
			'''.format({
				'enc': 'delimits data by',
				'dec': 'parses data delimited by',
			}[mode])),
	)

	parser.add_argument('-G', '--gnu-order', default=None, help=normalize('''
		A 4-character string that labels the axes of the gnuplot data file,
		for use together with '-J' to permute the axes. Default is 'dblw', short for
		double, blank, line, word.
		'''))

	group = parser.add_mutually_exclusive_group()
	group.add_argument('-J', '--json-order', default=None,
		help=normalize('''
			A 4-character digit string consisting of the letters from -G,
			 indicating which axis in the file that each axis in the array will be {}.
			 Default is 'dblw' (no permutation).
		''').format({'dec': 'drawn from', 'enc': 'written to'}[mode]))

	group.add_argument('-z', '--zip', default=None,
		help=normalize({
			'enc': '''
				Equivalent to -Gdblw -Jwdbl (i.e. move the first axis to the back).
				Generally speaking, converts data from a object-of-arrays ordering to
				gnuplot's preferred array-of-objects order.
			''',
			'dec': '''
				Equivalent to -Gdblw -Jwdbl (i.e. move the final axis to the front).
				Generally speaking, converts data from gnuplot's array-of-objects order
				to an object-of-arrays ordering.
			''',
		}[mode]))

	args = parser.parse_args()

	if args.gnu_order and not args.json_order:
		parser.error('-G makes no sense without -J')
	if not args.gnu_order: args.gnu_order = 'dblw'
	if not args.json_order: args.json_order = args.gnu_order

	spec = Spec().comment('#').order(gnu=args.gnu_order, json=args.json_order)

	def do_enc(infile, outfile):
		data = json.load(infile)
		dump(data, file=outfile, spec=spec)

	def do_dec(infile, outfile):
		data = load(infile, spec=spec)
		json.dump(data, outfile)

	{'enc': do_enc, 'dec': do_dec}[mode](sys.stdin, sys.stdout)
