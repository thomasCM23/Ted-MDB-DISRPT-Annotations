import io, sys, re, os, tempfile, subprocess
from glob import glob
from argparse import ArgumentParser
from collections import defaultdict
from nltk import sent_tokenize, word_tokenize
from six import iterkeys
from depedit import DepEdit
from tt2conll import conllize

PY3 = sys.version_info[0] == 3

parser_path = 'C:\\Uni\\HK\\Parsers\\stanford-parser-full-2018-02-27\\*;'
ud1_path = "C:\\Uni\\HK\\Parsers\\stanford-corenlp-full-2018-02-27\\*;"
ud2_path = "C:\\Uni\\HK\\Parsers\\corenlp_experimental_ud2\\*;"
dep_edit_ini = "C:\\Uni\\HK\\Parsers\\corenlp_experimental_ud2\\udpos.ini"


parser_path = 'C:\\Uni\\HK\\Parsers\\UDPipe\\udpipe-1.2.0-bin\\bin-win64\\'
parse_cmd = [parser_path+'udpipe.exe', '--tag','--parse', parser_path+'english-ewt-ud-2.3-181115.udpipe','tempfilename']


def process_offsets(*args):
	"""

	:param args: a list of strings with PDTB style char offsets, e.g. "3420..3434;3440..3615"
	:return: two lists with numerical start positions and numerical end positions
	"""

	starts = set([])
	ends = set([])
	for offset_list in args:
		spans = offset_list.split(";")
		for span in spans:
			if ".." in span:
				start, end = span.split("..")
				starts.add(int(start))
				ends.add(int(end))
	return starts, ends


def exec_via_temp(input_text, command_params, workdir="", outfile=False):
	temp = tempfile.NamedTemporaryFile(delete=False)
	if outfile:
		temp2 = tempfile.NamedTemporaryFile(delete=False)
	output = ""
	try:
		if PY3:
			temp.write(input_text.encode("utf8"))
		else:
			temp.write(input_text)
		temp.close()

		command_params = [x if x != 'tempfilename' else temp.name for x in command_params]
		if outfile:
			command_params = [x if x != 'tempfilename2' else temp2.name for x in command_params]
		if workdir == "":
			proc = subprocess.Popen(command_params, stdout=subprocess.PIPE,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
			(stdout, stderr) = proc.communicate()
		else:
			proc = subprocess.Popen(command_params, stdout=subprocess.PIPE,stdin=subprocess.PIPE,stderr=subprocess.PIPE,cwd=workdir)
			(stdout, stderr) = proc.communicate()
		if outfile:
			output = open(temp2.name).read()
			temp2.close()
			os.remove(temp2.name)
		else:
			output = stdout
		#print stderr
		proc.terminate()
	except Exception as e:
		print(e)
	finally:
		os.remove(temp.name)
		return output.decode("utf8")


def map_text(text):
	"""
	Maps character positions in PDTB raw files to indices in stream of non-whitespace characters,
	omitting the mandatory .START prologue
	:param text: the PDTB raw text file
	:return: dictionary from PDTB positions to indices of filled characters
	"""

	mapping = {}
	buffer = []
	empty = set([" ","\n","\t","\r"])
	counter = 0

	# Get rid of .START
	text = text.replace(".START","",1)
	i = 5
	if ".START" in text:  # Some documents contain two .START
		second_start = text.index(".START") + 5
		continuation = 6
	else:
		second_start = 0

	for char in text:
		i += 1
		if i > second_start and second_start > 0:
			if continuation > 0:
				continuation -= 1
				continue
		if not char in empty:
			buffer.append(char)
			mapping[i] = counter
			counter += 1

	filled_text = "".join(buffer)

	return mapping, filled_text


def unescape_deptok(tok):
	tok = tok.replace("``",'"').replace("''",'"')
	tok = tok.replace("-RRB-",")").replace("-LRB-","(").replace("-LSB-","[").replace("-RSB-","]").replace("-LCB-","{").replace("-RCB-","}")
	return tok


def get_missing_parses(error_files, parse_cache):


	to_parse = set([])
	for docname in sorted(list(iterkeys(error_files))):
		text, filled_text, filled_starts, filled_ends = error_files[docname]
		sentences = sent_tokenize(text.replace(".START","").strip())
		sent_cache = []
		for sent in sentences:
			tokens = word_tokenize(sent)
			tokens = [unescape_deptok(tok) for tok in tokens]
			sent_cache.append(" ".join(tokens))
		for sent in sent_cache:
			if sent not in parse_cache:
				to_parse.add(sent)

	sys.stderr.write("o Getting missing parses for " + str(len(to_parse)) + " sentence types")
	to_parse = ["<s>\n" + sent + "\n</s>" for sent in to_parse]
	parser_input = "\n".join(to_parse) + "\n"
	parser_input = parser_input.replace(" ","\n")

	#cmd = ['java','-mx512m','-cp',parser_path,'edu.stanford.nlp.parser.lexparser.LexicalizedParser',
	#	   '-tokenizerFactory','edu.stanford.nlp.process.WhitespaceTokenizer','-tokenizerMethod','newCoreLabelTokenizerFactory',
	#	   '-escaper','edu.stanford.nlp.process.PTBEscapingProcessor','-sentences', 'newline','-outputFormat','penn','edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz','tempfilename']
	#output = exec_via_temp(parser_input,cmd)
	#tree_to_conll = ['java', '-mx512m', "-Dfile.encoding=UTF-8",'-cp', ud2_path,'edu.stanford.nlp.trees.ud.UniversalDependenciesConverter','-encoding', 'UTF-8','-treeFile', 'tempfilename']
	#tree_to_conll = ['java', '-cp', ud1_path, '-mx1g', '-Dfile.encoding=UTF-8', 'edu.stanford.nlp.trees.ud.UniversalDependenciesConverter', '-encoding','UTF-8','-treeFile','tempfilename']
	#output = exec_via_temp(output,tree_to_conll)
	#d = DepEdit(config_file=io.open(dep_edit_ini,encoding="utf8").read().replace("\r","").strip().split("\n"))
	#output = d.run_depedit(output.split("\n"))


	conllized = conllize(parser_input,element="s",ten_cols=True)
	#ssplit = exec_via_temp(tagged,split_cmd)
	#conll = exec_via_temp(ssplit, conll_cmd)
	output = exec_via_temp(conllized, parse_cmd, parser_path)
	output = output.replace("\r","")

	new_trees = {}
	for sent in output.strip().split("\n\n"):
		toks = []
		for line in sent.split("\n"):
			if "\t" in line:
				fields = line.split("\t")
				toks.append(unescape_deptok(fields[1]))
		new_trees[" ".join(toks)] = sent
	return new_trees


def auto_parse(text, parse_cache):

	sentences = sent_tokenize(text.replace(".START","").strip())
	sent_cache = []
	for sent in sentences:
		tokens = word_tokenize(sent)
		tokens = [unescape_deptok(tok) for tok in tokens]
		sent_cache.append(" ".join(tokens))

	output = []
	for sent in sent_cache:
		if sent in parse_cache:
			output.append(parse_cache[sent])
		else:
			raise IOError("Missing sentence in parse cache: " + sent + "\n")

	return "\n\n".join(output) + "\n"

def read_parses(dep_dir	):
	dep_files = glob(dep_dir + "wsj_*.conllu")

	parse_cache = {}
	sys.stderr.write(" o Reading "+str(len(dep_files))+" dependency files... ")
	for file_ in dep_files:
		lines = io.open(file_,encoding="utf8").readlines()
		sent_toks = []
		parse = []
		for line in lines:
			if "\t" in line:
				fields = line.split("\t")
				parse.append(line.strip())
				sent_toks.append(unescape_deptok(fields[1]))
			else:
				# Sentence done
				if len(sent_toks) > 0:
					parse_cache[" ".join(sent_toks)] = "\n".join(parse)
					parse = []
					sent_toks = []


	sys.stderr.write("Done.\n")

	return parse_cache


def align(deplines,filled_text, filled_starts, filled_ends):
	deptext = ""

	out_bi = "# newdoc id = " + docname + "\n"
	cursor = 0
	sentences = []
	this_sent = []
	prev_end = False
	first_tok = True
	in_conn = False

	dep_filled_text = ""
	for line in deplines:
		if "\t" in line:
			fields = line.split("\t")
			fields[1] = unescape_deptok(fields[1])
			dep_filled_text += fields[1]
			if fields[1] == "once":
				a=4
			if cursor in filled_starts:
				label = "Seg=B-Conn"
				in_conn = True
			elif prev_end and in_conn:
				label = "_"
				in_conn = False
			elif in_conn:
				label = "Seg=I-Conn"
			elif first_tok:
				label = "_"
				in_conn = False
			else:
				label = "_"
			first_tok = False
			fields[9] = label
			deptext += fields[1]
			prev_end = False
			cursor += len(fields[1])
			if cursor-1 in filled_ends or cursor in filled_ends:
				prev_end = True
			if filled_text[:cursor] != dep_filled_text[:cursor]:  # Mismatch between discourse and syntax TBs
				return False, None
			else:
				this_sent.append("\t".join(fields))
		else:
			if len(this_sent) > 0:
				sentences.append(this_sent)
				this_sent = []

	if filled_text != dep_filled_text:
		return False, None

	sentences = ["\n".join(sent) for sent in sentences]

	parsed = "\n\n".join(sentences)
	out_bi += parsed + "\n"

	return True, out_bi

p = ArgumentParser()
p.add_argument("-r","--root",default="C:\\uni\\corpora\\PDTB\\pdtbMerge-v9-3\\",help="Root folder of PDTB V3")
p.add_argument("-d","--depdir",default="C:\\Uni\\RST\\DISRPT2019\\shared_task\\PDTB\\wsj_ud2_conllu\\",help="Folder with WSJ dependency parses")

opts = p.parse_args()

rel_dir = opts.root
if not rel_dir.endswith(os.sep):
	rel_dir += os.sep
dep_dir = opts.depdir
if not dep_dir.endswith(os.sep):
	dep_dir += os.sep

rel_files = glob(rel_dir + "gold" + os.sep + "**" + os.sep + "wsj_*", recursive=True)
#text_files = glob(rel_dir + "raw" + os.sep + "**" + os.sep + "wsj_*", recursive=True)
#dep_files = glob(dep_dir + "wsj_*.conll")

outdocs = defaultdict(list)

parse_cache = read_parses(dep_dir)
error_files = {}

for file_ in rel_files:#[:100]:
	docname = os.path.basename(file_)
	if docname == "wsj_0003":
		a=4
	section = docname[-4:-2]
	text_path = os.path.dirname(file_) + os.sep + ".." + os.sep + ".." + os.sep + "raw" + os.sep + section + os.sep + docname
	try:
		text = io.open(text_path,encoding="utf8").read()
	except:
		text = io.open(text_path).read()

	rel_lines = io.open(file_,encoding="utf8").readlines()
	doc_starts = set([])
	doc_ends = set([])
	for line in rel_lines:
		line = line.strip()
		if len(line) > 0:
			fields = line.split("|")
			ConnSpanList = fields[1]  # Chars covered by connective
			ConnFeatSpanList = fields[6]  # Chars covered by connective features
			Arg1SpanList = fields[14] # Chars covered by arg1
			Arg1FeatSpanList = fields[19] # Chars covered by arg1 features
			Arg2SpanList = fields[20] # Chars covered by arg2
			Arg2FeatSpanList = fields[25] # Chars covered by arg2 features
			if "2394" in line and docname == "wsj_0013":
				a=4
			#starts, ends = process_offsets(ConnSpanList,Arg1SpanList,Arg2SpanList,ConnFeatSpanList,Arg1FeatSpanList,Arg2FeatSpanList)
			starts, ends = process_offsets(ConnSpanList)
			doc_starts.update(starts)
			doc_ends.update(ends)
	mapping, filled_text = map_text(text)
	filled_starts = set([])
	filled_ends = set([])
	for s in doc_starts:
		if s in mapping:
			filled_starts.add(mapping[s])
		elif s+1 in mapping:  # Assume this offset points to the space between words - try moving one char forward
			filled_starts.add(mapping[s+1])
		elif s-1 in mapping:
			filled_starts.add(mapping[s-1])
		elif s+2 in mapping:  # Can happen due to double newline
			filled_starts.add(mapping[s+2])
		else:
			raise IOError("Invalid mapping; no word starts at raw position " + str(s) + " in document " + docname + "\n")
	for e in doc_ends:
		if e in mapping:
			filled_ends.add(mapping[e])
		elif e+1 in mapping:  # Assume this offset points to the space between words - try moving one char forward
			filled_ends.add(mapping[e+1])
		elif e-1 in mapping:  # Try moving one char back
			filled_ends.add(mapping[e-1])
		else:
			raise IOError("Invalid mapping; no word ends at raw position " + str(e) + " in document " + docname + "\n")

	deplines = io.open(dep_dir + docname + ".conllu",encoding="utf8").read().strip().replace("\r","").split("\n")
	deplines.append("")  # Ensure last blank to process last sentence


	if docname == "wsj_0034": #20":
		a=5


	dep_filled_text = ""
	this_sent = []
	sent_counter = 0
	success, output = align(deplines,filled_text, filled_starts, filled_ends)
	if not success:
		if len(error_files) < 5:
			sys.stderr.write("! mismatched text in dep file and PDTB file: " + docname +"\n")
		elif len(error_files) == 5:
			sys.stderr.write("! suppressing further warning messages on mismatched text\n")

		error_files[docname] = (text, filled_text, filled_starts, filled_ends)
		continue

	outdocs[docname] = output

new_trees = get_missing_parses(error_files, parse_cache)
parse_cache.update(new_trees)

for docname in sorted(list(iterkeys(error_files))):
	text, filled_text, filled_starts, filled_ends = error_files[docname]
	deplines =  auto_parse(text, parse_cache)
	deplines = deplines.split("\n")
	success, output = align(deplines,filled_text, filled_starts, filled_ends)
	if success:
		outdocs[docname] = re.sub(r'^([^\t\n]+\t[^\t\n]+\t[^\t\n]+\t[^\t\n]+\t[^\t\n]+\t)[^\t\n]+',r'\1_',output,flags=re.MULTILINE)  # Remove feats from udpipe
	else:
		raise IOError("Can't resolve parse for document " + docname + "\n")



trainfile = io.open("PDTB_dep_train.txt",'w',encoding="utf8",newline="\n")
testfile = io.open("PDTB_dep_test.txt",'w',encoding="utf8",newline="\n")
devfile = io.open("PDTB_dep_dev.txt",'w',encoding="utf8",newline="\n")

#test = ["wsj_0101"]
#dev = ["wsj_0100"]

for doc in sorted(outdocs.keys()):
	if "wsj_22" in doc:
		devfile.write(outdocs[doc] + "\n")
	elif "wsj_23" in doc:
		testfile.write(outdocs[doc] + "\n")
	else:
		trainfile.write(outdocs[doc] + "\n")

sys.stderr.write("\nDone.\n")
