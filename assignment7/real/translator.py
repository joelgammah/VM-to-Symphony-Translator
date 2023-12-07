from pathlib import Path
import lark

# TO DO:
#   __push
#   __pop
#   __ifgoto
#   __call
#   __return

class Translator(object):
  GRAMMAR = """
  start: statement+
  statement: push
           | pop
           | operator
           | label
           | goto
           | ifgoto
           | fcall
           | fdefine
           | freturn
           | output
  
  push: "push" segment INT
  pop: "pop" segment INT
  segment: "local"      -> local
         | "argument"   -> argument
         | "this"       -> this
         | "that"       -> that
         | "constant"   -> constant
         | "static"     -> static
         | "pointer"    -> pointer
         | "temp"       -> temp
  operator: "and"       -> and
          | "or"        -> or
          | "not"       -> not
          | "xor"       -> xor
          | "add"       -> add
          | "sub"       -> sub
          | "neg"       -> neg
          | "mul"       -> mul
          | "div"       -> div
          | "rem"       -> rem
          | "eq"        -> eq
          | "lt"        -> lt
          | "gt"        -> gt
          | "ne"        -> ne
          | "le"        -> le
          | "ge"        -> ge
  label: "label" CNAME
  goto: "goto" CNAME
  ifgoto: "if-goto" CNAME
  fcall: "call" fname INT
  fdefine: "function" fname INT
  freturn: "return"

  output: "output" segment INT

  fname: CNAME ("." CNAME)*

  
  %import common (INT, WS, CNAME, CPP_COMMENT)
  %ignore CPP_COMMENT
  %ignore WS
  """

 
  def __init__(self):
    self.MARKER = '____'    
    self.__counter = 0
    self.__current_function = None
  

  def translate(self, instructions):
    vm_parser = lark.Lark(self.GRAMMAR)
    ptree = vm_parser.parse('\n'.join(instructions))
    asmins = self.__bootstrap() + self.__call('Main.main', 0)
    asmins.extend(['goto _END_PROGRAM_'])  #asmins.extend(['(_INFINITE_END_PROGRAM_LOOP_)', 'goto _INFINITE_END_PROGRAM_LOOP_'])
    for elt in ptree.children:
      etype = elt.children[0].data.upper()
      if etype in ['AND', 'OR', 'NOT', 'XOR', 'ADD', 
                   'SUB', 'NEG', 'MUL', 'DIV', 'REM', 
                   'EQ', 'LT', 'GT', 'NE', 'LE', 'GE']:
        asmins.extend(self.__operator(etype))
      elif etype == 'PUSH':
        asmins.extend(self.__push(elt.children[0].children[0].data.upper(),
                                  int(elt.children[0].children[1].value)))
      elif etype == 'POP':
        asmins.extend(self.__pop(elt.children[0].children[0].data.upper(),
                                 int(elt.children[0].children[1].value)))
      elif etype == 'LABEL':
        asmins.extend(self.__label(elt.children[0].children[0].value))
      elif etype == 'GOTO':
        asmins.extend(self.__goto(elt.children[0].children[0].value))
      elif etype == 'IFGOTO':
        asmins.extend(self.__ifgoto(elt.children[0].children[0].value))
      elif etype == 'FCALL':
        fname = '.'.join([c.value for c in elt.children[0].children[0].children])
        fargs = int(elt.children[0].children[1].value)
        asmins.extend(self.__call(fname, fargs))
      elif etype == 'FDEFINE':
        fname = '.'.join([c.value for c in elt.children[0].children[0].children])
        fvars = int(elt.children[0].children[1].value)
        asmins.extend(self.__function(fname, fvars))
      elif etype == 'FRETURN':
        asmins.extend(self.__return())
      elif etype == 'OUTPUT':
        asmins.extend(self.__output(elt.children[0].children[0].data.upper(),
                                    int(elt.children[0].children[1].value)))
      else:
        raise RuntimeError(f'Unknown command: {elt.pretty()}')
    return asmins + ['(_END_PROGRAM_)']

  def __bootstrap(self):
    return ['#-------  ' + f'{"BOOTSTRAP":^24}' + '  -------',
            '@256', 'D=A', '@SP', 'M=D']

  def __make_label(self, cmdlabel):
    if self.__current_function is None:
      return cmdlabel
    else:
      return f'{self.__current_function}.{cmdlabel}'
  
  def __push_from(self, reg='D'):
    if reg not in 'BCD':
      raise RuntimeError(f'invalid register {reg}')
    return [f'@SP', 'AM=M+1', 'A=A-1', f'M={reg}']

  def __pop_into(self, reg='D'):
    if reg not in 'BCD':
      raise RuntimeError(f'invalid register {reg}')
    return [f'@SP', 'AM=M-1', f'{reg}=M']

  def __label(self, label):
    comment = f'label {label}'
    comment = '#-------  ' + f'{comment:^24}' + '  -------'
    label = self.__make_label(label)
    self.__counter += 1
    return [comment, f'({label})']

  def __goto(self, label):
    comment = f'goto {label}'
    comment = '#-------  ' + f'{comment:^24}' + '  -------'
    label = self.__make_label(label)
    return [comment, f'goto {label}']

  def __function(self, name, nvars):
    comment = f'function {name} {nvars}'
    comment = '#-------  ' + f'{comment:^24}' + '  -------'
    self.__current_function = name
    push_vars = []
    for _ in range(nvars):
      push_vars.extend(self.__push_from())
    return [comment, f'({name})', '@0', 'D=A'] + push_vars

  def __conditional(self, op, truecmds, falsecmds):
    opmap = {'EQ': '=', 'LT': '<', 'GT': '>', 'NE': '!=', 'LE': '<=', 'GE': '>='}
    asm = [
      f'C{opmap[op]}B? {self.MARKER}{op}_BEGIN{self.__counter:04d}',
      *falsecmds,
      f'GOTO {self.MARKER}{op}_END{self.__counter:04d}',
      f'({self.MARKER}{op}_BEGIN{self.__counter:04d})',
      *truecmds,
      f'({self.MARKER}{op}_END{self.__counter:04d})'
    ]
    self.__counter += 1
    return asm
  
  def __operator(self, op):
    lookup = {
      'AND': ['D=C&B'],
      'OR':  ['D=C|B'],
      'NOT': ['D=!B'],
      'ADD': ['D=C+B'],
      'SUB': ['D=C-B'],
      'NEG': ['D=-B'],
      'MUL': ['D=C*B']
    }
    asm = ['#-------  ' + f'{op:^24}' + '  -------']
    asm.extend(self.__pop_into('B'))
    if op != 'NOT' and op != 'NEG':
      asm.extend(self.__pop_into('C'))
    if op in lookup:
      asm.extend(lookup[op])
      asm.extend(self.__push_from())
    else:
      asm.extend(self.__conditional(op, 
                                    ['D=!0'] + self.__push_from(), 
                                    ['D=0'] + self.__push_from()))
    return asm

  def __advance_A(self, offset=1):
    if offset > 3:
      return ['B=A', f'@{offset}', 'A=A+B']
    else:
      return ['A=A+1' for _ in range(offset)]

  def __output(self, seg, num):
    comment = f'output {seg} {num}'
    comment = ['#-------  ' + f'{comment:^24}' + '  -------']
    if seg == 'ARGUMENT':
      return comment + ['@ARG', 'A=M'] + self.__advance_A(num) + ['D=M', '@OUTPUT', 'M=D']
    elif seg == 'LOCAL':
      return comment + ['@LCL', 'A=M'] + self.__advance_A(num) + ['D=M', '@OUTPUT', 'M=D']
    elif seg == 'STATIC':
      varname = f'{seg}{num:04d}'
      return comment + [f'@{varname}', 'D=M', '@OUTPUT', 'M=D']
    elif seg == 'CONSTANT':
      return comment + [f'@{num}', 'D=A', '@OUTPUT', 'M=D']
    raise RuntimeError('invalid instruction')

  def translate_file(self, vm_filename):
    vmins = []
    with open(vm_filename) as infile:
      vmins = infile.readlines()
    asmins = self.translate(vmins)
    asm_filename = Path(vm_filename).stem + '.sym'
    with open(asm_filename, 'w') as outfile:
      outfile.write('\n'.join(asmins))
    return asmins







  #**************************************************************************
  #                             TO BE COMPLETED
  #**************************************************************************

  def __push(self, seg, num):
    comment = f'push {seg} {num}'
    comment = ['#-------  ' + f'{comment:^24}' + '  -------']
    # return a list of assembly instructions, starting with the comment
    return comment
  
  def __pop(self, seg, num):
    comment = f'pop {seg} {num}'
    comment = ['#-------  ' + f'{comment:^24}' + '  -------']
    # return a list of assembly instructions, starting with the comment
    return comment

  def __ifgoto(self, label):
    comment = f'if-goto {label}'
    comment = '#-------  ' + f'{comment:^24}' + '  -------'
    # return a list of assembly instructions, starting with the comment
    return comment

  def __call(self, name, nargs):
    comment = f'call {name} {nargs}'
    comment = '#-------  ' + f'{comment:^24}' + '  -------'
    return_address_label = f'{name}$ret.{self.__counter}'
    self.__counter += 1
    asm = [comment]
    # return a list of assembly instructions, starting with the comment
    return asm

  def __return(self):
    comment = '#-------  ' + f'{"return":^24}' + '  -------'
    asm = [comment]
    # return a list of assembly instructions, starting with the comment
    return asm
    
  