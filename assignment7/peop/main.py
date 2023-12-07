import assembler
import computer
import translator


if __name__ == '__main__':
  import sys
  if len(sys.argv) > 1:
    fname = sys.argv[1]
    t = translator.Translator()
    asmins = t.translate_file(fname)
    a = assembler.Assembler()
    binins = a.assemble(asmins)
    c = computer.Computer()
    c.load(binins)
    c.run()
    print(c.ram[c.OUTPUT])



