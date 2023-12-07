import operator


class Computer(object):
  """
  4 16-bit registers (A, B, C, D)
  virtual register M is treated as the RAM value of address at A
  
  FEDCBA9876543210
  0...............  Immediate
  1mmmmaaabbbrrrrr  Operation

  Immediate: entire instruction byte is loaded into A
  @value or @varname (e.g., @42 or @count)
  
  Operation: mmmm is the mode, 
             aaa/bbb are the operand registers/values, 
             rrrrr is the result register(s)
  aaa/bbb   rrrrr
  000  A    ABCDM  where a 1 bit uses the corresponding register
  001  B
  010  C
  011  D
  100  0
  101  1
  110  unused
  111  M

  mmmm
  0000  unused
  0001  NOT    (rrrr = !aaa)
  0010  AND    (rrrr = aaa & bbb)
  0011  OR     (rrrr = aaa | bbb) 
  0100  XOR    (rrrr = aaa ^ bbb)
  0101  unused
  0110  unused
  0111  unused

  1000  CPY  (rrrr = aaa)
  1001  NEG  (rrrr = -aaa)
  1010  ADD  (rrrr = aaa + bbb)
  1011  SUB  (rrrr = aaa - bbb)
  1100  MUL  (rrrr = aaa * bbb)
  1101  DIV  (rrrr = aaa / bbb)
  1110  REM  (rrrr = aaa % bbb)
  1111  JMP  (uses final 3 bits of instruction for comparison; jump to instruction A)
             (aaa op bbb? label)

  comp (aaa op bbb)
  000  nil
  001  =
  010  <
  011  <=
  100  jmp
  101  !=
  110  >=
  111  >


  The SYMPHONY computer has 4 16-bit registers (A, B, C, and D), 
  along with 24,576 16-bit registers of RAM (214 + 213 registers). 
  The A register can also be interpreted as the address of one of 
  those RAM registers or as the instruction to jump to. 
  (The virtual register M does this "dereferencing".)
  
  This RAM is laid out as follows:
  
    Registers 0-15: predefined uses described below 
    (and can be accessed by @R0, @R1, …, @R15 in assembly)
    	R0: the STACK pointer (@SP)
    	R1: the LOCAL pointer (@LCL)
    	R2: the ARGUMENT pointer (@ARG)
    	R3: the THIS pointer (@THIS)
    	R4: the THAT pointer (@THAT)
    	R5-R12: the TEMPORARY segment
    	R13-R15: general use registers
    
    Registers 16-255: used to hold static variables
    
    Registers 256-2047: used to hold the stack
    
    Registers 2048-16383: used to hold the heap
    
    Registers 16384-20479: used to hold the screen map 
    (@SCREEN holds the base address 16384)
    
    Register 20480: used to hold the currently pressed key from the keyboard (@KEYBOARD)
    
    Registers 20481-20485: used to hold 5 13-segment displays 
    (@DISPLAY holds the base address 20481)
    
    Register 20486: used to hold external input (@INPUT)

    Register 20487: used to hold external output (@OUTPUT)
    
    Register 20488-24575: currently unused
    
    The computer can perform the following operations between A, B, C, D, 
    or the currently selected memory location (represented as M and using 
    the value in A as the memory address):
     
    •	Not
    •	And
    •	Or
    •	Xor
    •	Negation
    •	Addition
    •	Subtraction
    •	Multiplication
    •	Division
    •	Remainder
    •	Copy
     
    One of the operands can also be the constant 0 or 1.
  
  """
  RAM_REGISTER = 0
  RAM_SIZE = 24576
  MAX_ITERS = 16384
  STATIC = 16
  STACK = 256
  HEAP = 2048
  SCREEN = 16384
  SCREEN_SIZE = 4096
  KEYBOARD = 20480    # self.SCREEN + self.SCREEN_SIZE
  DISPLAY = 20481     # 5 segments in 20481-20485
  INPUT = 20486       # immediately follows the segment display
  OUTPUT = 20487      # immediately follows the INPUT
  
  def __init__(self):
    self.__MODES = {
      1:  self.__not,
      2:  self.__and,
      3:  self.__or,
      4:  self.__xor,
      8:  self.__copy,
      9:  self.__neg,
      10: self.__add,
      11: self.__sub,
      12: self.__mul,
      13: self.__div,
      14: self.__rem,
      15: self.__jmp
    }
    self.__COMPARISONS = {
      1: operator.eq,
      2: operator.lt,
      3: operator.le,
      5: operator.ne,
      6: operator.ge,
      7: operator.gt
    }
    self.reset()

  def load(self, program):
    self.reset()
    self.program = program

  def step(self, debug=False):
    if self.finished:
      return False
    if self.counter >= len(self.program):
      self.finished = True
      return False
    if self.iters >= self.MAX_ITERS:
      self.finished = True
      return False
    self.iters += 1
    jump = -1
    instruction = self.program[self.counter]
    if debug:
      print('-------------------------  DEBUG  -------------------------')
      print(f'{self}')
      print(f'\n{instruction}')
      print(f'{self.__encode(instruction)}\n')
    type, mode, arg1, arg2, res = self.__decode(instruction)

    if type == 0:
      self.__immediate(instruction)
    else:
      jump = self.__MODES[mode](arg1, arg2, res)

    if jump < 0:
      self.counter += 1
    else:
      self.counter = jump
    if debug:
        print(f'{self}')
        print('-----------------------------------------------------------')
    return True
  
  def run(self, debug=False):
    while not self.finished:
      self.step(debug)
    
      
  def reset(self):
    self.register = [0] * 4
    self.counter = 0
    self.ram = [0] * self.RAM_SIZE
    self.iters = 0
    self.finished = False

  def __decode(self, instruction):
    return (int(instruction[0], 2), 
            int(instruction[1:5], 2),
            int(instruction[5:8], 2),
            int(instruction[8:11], 2),
            int(instruction[11:], 2))

  def __encode(self, instruction):
    if instruction[0] == '0':
      return 'IMMEDIATE'
    else:
      return self.__MODES[int(instruction[1:5], 2)].__name__

  def __immediate(self, instruction):
    self.register[0] = int(instruction, 2)

  def __copy(self, arg1, arg2, res):
    self.__setval(res, self.__getval(arg1))
    return -1

  def __not(self, arg1, arg2, res):
    self.__setval(res, ~self.__getval(arg1))
    return -1

  def __and(self, arg1, arg2, res):
    self.__setval(res, self.__getval(arg1) & self.__getval(arg2))
    return -1

  def __or(self, arg1, arg2, res):
    self.__setval(res, self.__getval(arg1) | self.__getval(arg2))
    return -1

  def __xor(self, arg1, arg2, res):
    self.__setval(res, self.__getval(arg1) ^ self.__getval(arg2))
    return -1

  def __neg(self, arg1, arg2, res):
    self.__setval(res, -self.__getval(arg1))
    return -1
  
  def __add(self, arg1, arg2, res):
    self.__setval(res, self.__getval(arg1) + self.__getval(arg2))
    return -1

  def __sub(self, arg1, arg2, res):
    self.__setval(res, self.__getval(arg1) - self.__getval(arg2))
    return -1

  def __mul(self, arg1, arg2, res):
    self.__setval(res, self.__getval(arg1) * self.__getval(arg2))
    return -1
    
  def __div(self, arg1, arg2, res):
    self.__setval(res, self.__getval(arg1) // self.__getval(arg2))
    return -1

  def __rem(self, arg1, arg2, res):
    self.__setval(res, self.__getval(arg1) % self.__getval(arg2))
    return -1

  def __jmp(self, arg1, arg2, res):
    if self.__cmp(self.__getval(arg1), self.__getval(arg2), res):
      return self.__getval(0)
    return -1

  def __cmp(self, a, b, op):
    if op == 0:
      return False
    elif op == 4:
      return True
    elif op in self.__COMPARISONS:
      return self.__COMPARISONS[op](a, b)
    else:
      raise RuntimeError(f'{op} is not a valid comparison')

  def __getval(self, src):
    valmap = {4: 0, 5: 1}
    if src in valmap:
      return valmap[src]
    if src == 7:
      return self.ram[self.register[self.RAM_REGISTER]]
    return self.register[src]

  def __setval(self, dst, val):
    bdst = f'{dst:05b}'
    if bdst[-1] == '1':
      self.ram[self.register[self.RAM_REGISTER]] = val
    for i, bit in enumerate(bdst[:-1]):
      if bit == '1':
        self.register[i] = val
  
  
  def __str__(self):
    regs = 'ABCD'
    return '\n'.join([f'{regs[i]}:   {self.register[i]:6d}' for i in range(len(self.register))]) + \
          f'\nCTR: {self.counter:6d}' + \
          f'\nRAM: {self.ram[self.register[self.RAM_REGISTER]]} @ {self.register[self.RAM_REGISTER]}' + \
          f'\nINPUT: {self.ram[self.INPUT]}' + \
          f'\nOUTPUT: {self.ram[self.OUTPUT]}' + \
          f'\nCRIT: {[self.ram[i] for i in range(5)]}' + \
          f'\nSTK: {[self.ram[i] for i in range(self.STACK, self.ram[0])]}'
