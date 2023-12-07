from pathlib import Path
import operator
import lark
import computer


class Assembler(object):
  GRAMMAR = """
  start: expression+
  expression: immediate
            | copy
            | negate
            | negative
            | calculate     
            | conditional   
            | goto          
            | label         
            | jump
  
  copy: registerset "=" (register | constant)
  negate: registerset "=" "!" (register | constant)
  negative: registerset "=" "-" (register | constant)
  calculate: registerset "=" ((register operator constant) | (constant operator register) | (register operator register))
  conditional: condition "?" labelname
  goto: "GOTO"i labelname
  condition: (nonmemreg comp constant) | (constant comp nonmemreg) | (nonmemreg comp nonmemreg)
  label: "(" labelname ")"
  jump: "JUMP"i
  labelname: LNAME
  LNAME: ("_"|LETTER) ("_"|":"|"."|"$"|LETTER|DIGIT)*
  name: CNAME
  
  
  number: INT
  constant: "0" -> zero | "1" -> one
  immediate: "@" (number | name | labelname)
  registerset: register [register*]
  nonmemreg: A | B | C | D
  register: A | B | C | D | M
  A: "A"
  B: "B"
  C: "C"
  D: "D"
  M: "M"

  operator: and | or | xor | add | sub | mul | div | rem
  and: "&"
  or: "|"
  xor: "^"
  add: "+"
  sub: "-"
  mul: "*"
  div: "/"
  rem: "%"

  comp: eq | ne | gt | ge | lt | le
  eq: "="
  ne: "!="
  gt: ">"
  ge: ">="
  lt: "<"
  le: "<="
  
  COMMENT: /#.*/
  
  %import common (INT, WS, LETTER, DIGIT, CNAME)
  %ignore COMMENT
  %ignore WS
  """
  
  def __init__(self):
    self.reset()

  def reset(self):
    self.varlookup = {
      'R0': 0, 'R1': 1, 'R2': 2, 'R3': 3,
      'R4': 4, 'R5': 5, 'R6': 6, 'R7': 7,
      'R8': 8, 'R9': 9, 'R10': 10, 'R11': 11,
      'R12': 12, 'R13': 13, 'R14': 14, 'R15': 15,
      'SP': 0, 'LCL': 1, 'ARG': 2, 'THIS': 3, 'THAT': 4,
      'SCREEN': computer.Computer.SCREEN, 
      'DISPLAY': computer.Computer.DISPLAY,
      'KEYBOARD': computer.Computer.KEYBOARD,
      'INPUT': computer.Computer.INPUT,
      'OUTPUT': computer.Computer.OUTPUT
    }
    self.predefined_variables = len(self.varlookup)

    self.labelmap = {}
    self.__MARKER = '_____'

    self.reg_map = {
      'A': '000',
      'B': '001',
      'C': '010',
      'D': '011',
      'zero': '100',
      'one': '101',
      'M': '111'
    }
    self.op_map = {
      'not': '0001',
      'and': '0010',
      'or':  '0011',
      'xor': '0100',
      'cpy': '1000',
      'neg': '1001',
      'add': '1010',
      'sub': '1011',
      'mul': '1100',
      'div': '1101',
      'rem': '1110',
      'jmp': '1111'
    }
    self.cmp_map = {
      'eq':  '001',
      'lt':  '010',
      'le':  '011',
      'ne':  '101',
      'ge':  '110',
      'gt':  '111'
    }

  def assemble(self, instructions):
    self.reset()
    parse_map = {
      'immediate': self.__immediate,
      'copy': self.__copy,
      'negate': self.__negate,
      'negative': self.__negative,
      'calculate': self.__calculate,
      'goto': self.__goto,
      'conditional': self.__conditional,
      'label': self.__label,
      'jump': self.__jump
    }
    sym_parser = lark.Lark(self.GRAMMAR)
    ptree = sym_parser.parse('\n'.join(instructions))
    for inst in ptree.children:
      etype = inst.children[0].data
      if etype == 'label':
        label = inst.children[0].children[0].children[0].value
        if label in self.labelmap:
          raise RuntimeError(f'Label {label} already defined')
        self.labelmap[label] = None
    pre_instructions = []
    for inst in ptree.children:
      etype = inst.children[0].data
      if etype in parse_map:
        pre_instructions.extend(parse_map[etype](inst.children[0]))
    linenum = 0
    for instruction in pre_instructions:
      if instruction.startswith(self.__MARKER):
        label = instruction.replace(self.__MARKER, '')
        self.labelmap[label] = linenum
      else:
        linenum += 1
    binary_instructions = []
    for instruction in pre_instructions:
      if instruction.endswith(self.__MARKER):
        label = instruction.replace(self.__MARKER, '')
        if label not in self.labelmap:
          raise RuntimeError(f'Label {label} not defined')
        binary_instructions.append(f'0{self.labelmap[label]:015b}')
      elif not instruction.startswith(self.__MARKER):
        binary_instructions.append(instruction)
    
    return binary_instructions

  def __immediate(self, instruction):
    t = instruction.children[0].data
    x = instruction.children[0].children[0].value
    v = 0
    if t != 'number' and x in self.labelmap:
      return [f'{x}{self.__MARKER}']
    if t == 'number':
      v = int(x)
    else:
      if x not in self.varlookup:
        self.varlookup[x] = computer.Computer.STATIC + len(self.varlookup) - self.predefined_variables
      v = self.varlookup[x]
    return [f'0{v:015b}']

  def __registers(self, instruction):
    index = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'M': 4}
    bits = ['0', '0', '0', '0', '0']
    for node in instruction.children:
      bits[index[node.children[0].value]] = '1'
    return ''.join(bits)
  
  def __register_or_constant(self, instruction):
    k = instruction.data
    if k == 'register' or k == 'nonmemreg':
      k = instruction.children[0].value.upper()
    return self.reg_map[k]
  
  def __copy(self, instruction):
    binary_instructions = []
    dst, src = instruction.children
    res = self.__registers(dst)
    arg = self.__register_or_constant(src)
    if len(arg) > 3:
      binary_instructions.append(arg)
      arg = '000'
    binary_instructions.append(f'1{self.op_map["cpy"]}{arg}000{res}')
    return binary_instructions

  def __negate(self, instruction):
    binary_instructions = []
    arg2 = '000'
    res = self.__registers(instruction.children[0])
    arg1 = self.__register_or_constant(instruction.children[1])
    if len(arg1) > 3:
      binary_instructions.append(arg1)
      arg1 = '000'
    binary_instructions.append(f'1{self.op_map["not"]}{arg1}{arg2}{res}')
    return binary_instructions

  def __negative(self, instruction):
    binary_instructions = []
    arg2 = '000'
    res = self.__registers(instruction.children[0])
    arg1 = self.__register_or_constant(instruction.children[1])
    if len(arg1) > 3:
      binary_instructions.append(arg1)
      arg1 = '000'
    binary_instructions.append(f'1{self.op_map["neg"]}{arg1}{arg2}{res}')
    return binary_instructions
  
  def __calculate(self, instruction):
    binary_instructions = []
    res = self.__registers(instruction.children[0])
    arg1 = self.__register_or_constant(instruction.children[1])
    op = self.op_map[instruction.children[2].children[0].data.value]
    arg2 = self.__register_or_constant(instruction.children[3])
    if len(arg1) > 3:
      binary_instructions.append(arg1)
      arg1 = '000'
    if len(arg2) > 3:
      binary_instructions.append(arg2)
      arg2 = '000'
    binary_instructions.append(f'1{op}{arg1}{arg2}{res}')
    return binary_instructions

  def __goto(self, instruction):
    binary_instructions = []
    label = instruction.children[0].children[0].value
    binary_instructions.append(f'{label}{self.__MARKER}')
    binary_instructions.append('1111100000000100')
    return binary_instructions

  def __conditional(self, instruction):
    binary_instructions = []
    x = self.__register_or_constant(instruction.children[0].children[0])
    cmp = self.cmp_map[instruction.children[0].children[1].children[0].data]
    y = self.__register_or_constant(instruction.children[0].children[2])
    label = instruction.children[1].children[0].value
    binary_instructions.append(f'{label}{self.__MARKER}')
    binary_instructions.append(f'11111{x}{y}00{cmp}')
    return binary_instructions

  def __label(self, instruction):
    return [f'{self.__MARKER}{instruction.children[0].children[0].value}']

  def __jump(self, instruction):
    return ['1111100000000100']
  
  
  def assemble_file(self, asm_filename):
    asmins = []
    with open(asm_filename) as infile:
      asmins = infile.readlines()
    macins = self.assemble(asmins)
    bin_filename = Path(asm_filename).stem + '.bin'
    with open(bin_filename, 'w') as outfile:
      outfile.write('\n'.join(macins))
    return macins



def disassemble(instruction):
  modes = {
    '0001': 'NOT',
    '0010': 'AND',
    '0011': 'OR',
    '0100': 'XOR',
    '1000': 'CPY',
    '1001': 'NEG',
    '1010': 'ADD',
    '1011': 'SUB',
    '1100': 'MUL',
    '1101': 'DIV',
    '1110': 'REM',
    '1111': 'JMP'
  }
  ops = {
    '000': 'A',
    '001': 'B',
    '010': 'C',
    '011': 'D',
    '100': '0',
    '101': '1',
    '111': 'M'
  }
  cmps = {
    '000': 'NIL',
    '001': '=',
    '010': '<',
    '011': '<=',
    '100': 'JMP',
    '101': '!=',
    '110': '>=',
    '111': '>'
  }
  if instruction[0] == '0':
    return f'@{int(instruction[1:], 2)}'
  else:
    mode = modes[instruction[1:5]]
    x = ops[instruction[5:8]]
    y = ops[instruction[8:11]]
    res = ''.join([a for a, i in zip('ABCDM', instruction[11:]) if i == '1'])
    if mode == 'JMP':
      cmp = cmps[instruction[13:]]
      if cmp in ['NIL', 'JMP']:
        return cmp
      else:
        return f'JMP {x} {cmp} {y}'
    elif mode in ['NOT', 'CPY', 'NEG']:
      v = {'NOT': '!', 'CPY': '', 'NEG': '-'}
      return f'{res} = {v[mode]}{x}'
    else:
      v = {'AND': '&', 'OR': '|', 'XOR': '^', 'ADD': '+', 'SUB': '-', 'MUL': '*', 'DIV': '/', 'REM': '%'}
      return f'{res} = {x} {v[mode]} {y}'
