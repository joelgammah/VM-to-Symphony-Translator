## VM to Symphony Language Translator

This project is a VM to Symphony Language translator developed as part of my Computer Organization and Architecture class. The goal of this project is to translate Virtual Machine (VM) code into Symphony Assembly Language, facilitating a deeper understanding of how high-level instructions are converted into low-level operations.

## Project Overview

The VM to Symphony Language translator takes VM code as input and outputs the corresponding Symphony Assembly code. This translator helps bridge the gap between higher-level language constructs and the underlying hardware-specific instructions.

## Files in the Project

- `main.py`: The main script that drives the translation process.
- `assembler.py`: Contains functions to parse and assemble the Symphony Assembly code.
- `computer.py`: Simulates the Symphony computer, useful for testing the generated assembly code.
- `translator.py`: The core translator that converts VM instructions to Symphony Assembly instructions.
- `fact.vm`: A sample VM code file used to test the translator.

## How to Use

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/vm-to-symphony-translator.git
   cd vm-to-symphony-translator
   ```

2. **Run the Translator**
   ```bash
   python main.py path/to/your/vm/file.vm
   ```

3. **Output**
   The translated Symphony Assembly code will be generated and saved in the same directory as the input VM file with a `.symph` extension.

## Example

Given a `fact.vm` file containing VM code for computing factorial, running the translator will produce a `fact.sym` file with the equivalent Symphony Assembly instructions.

## Prerequisites

- Python 3.x
- Basic understanding of VM and Assembly languages

## Learning Objectives

- Understand the translation process from high-level VM code to low-level Assembly instructions.
- Gain insights into the working of virtual machines and assembly language programming.
- Develop skills in Python programming and script automation.

## Contributing

Contributions are welcome! Feel free to fork this repository and submit pull requests.
