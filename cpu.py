"""
Duck Machine model DM2020W CPU
"""

from instr_format import Instruction, OpCode, CondFlag, decode
from typing import Tuple
from cpu import *
from memory import Memory
from register import Register, ZeroRegister
from mvc import MVCEvent, MVCListenable
import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class ALU(object):
    """The arithmetic logic unit (also called a "functional unit"
    in a modern CPU) executes a selected function but does not
    otherwise manage CPU state. A modern CPU core may have several
    ALUs to boost performance by performing multiple operatons
    in parallel, but the Duck Machine has just one ALU in one core.
    """
    # The ALU chooses one operation to apply based on a provided
    # operation code.  These are just simple functions of two arguments;
    # in hardware we would use a multiplexer circuit to connect the
    # inputs and output to the selected circuitry for each operation.
    ALU_OPS = {
        OpCode.ADD: lambda x, y: x + y,
        OpCode.SUB: lambda x, y: x - y,
        OpCode.MUL: lambda x, y: x * y,
        OpCode.DIV: lambda x, y: x // y,
        #
        # For memory access operations load, store, the ALU
        # performs the address calculation
        OpCode.LOAD: lambda x, y: x + y,
        OpCode.STORE: lambda x, y: x + y,
        # Some operations perform no operation
        OpCode.HALT: lambda x, y: 0
    }

    def exec(self, op: OpCode, in1: int, in2: int) -> Tuple[int, CondFlag]:
        lambda_op = self.ALU_OPS.get(op)
        x = in1
        y = in2
        try:
            result = 0
            my_operation = ALU.ALU_OPS.get(op)
            result = my_operation(x, y)
            if result == 0:
                return (0, CondFlag.Z)
            elif result < 0:
                return (result, CondFlag.M)
            elif result > 0:
                return (result, CondFlag.P)
        except:
            return (0, CondFlag.V)

class CPUStep(MVCEvent):
    """CPU is beginning step with PC at a given address"""
    def __init__(self, subject: "CPU", pc_addr: int,
                 instr_word: int, instr: Instruction)-> None:
        self.subject = subject
        self.pc_addr = pc_addr
        self.instr_word = instr_word
        self.instr = instr

class CPU(MVCListenable):
    """Duck Machine central processing unit (CPU)
    has 16 registers (including r0 that always holds zero
    and r15 that holds the program counter), a few
    flag registers (condition codes, halted state),
    and some logic for sequencing execution.  The CPU
    does not contain the main memory but has a bus connecting
    it to a separate memory.
    """

    def __init__(self, memory: Memory):
        super().__init__()
        self.memory = memory  # Not part of CPU; what we really have is a connection

        self.registers = [ZeroRegister(), Register(), Register(), Register(),
                          Register(), Register(), Register(), Register(),
                          Register(), Register(), Register(), Register(),
                          Register(), Register(), Register(), Register()]
        self.condition = CondFlag.ALWAYS
        self.halted = False
        self.alu = ALU()
        self.pc = self.registers[15]

    def step(self):
        # Fetch
        instr_addr = self.pc.get()
        instr_word = self.memory.get(instr_addr)
        # Decode
        instr = decode(instr_word)
        # Display the CPU state when we have decoded the instruction,
        # before we have executed it
        self.notify_all(CPUStep(self, instr_addr, instr_word, instr))
        # Execute
        instr_predicate = self.condition.value & instr.cond.value
        if instr_predicate:
            left_operand = self.registers[instr.reg_src1].get()
            right_operand = instr.offset + self.registers[instr.reg_src2].get()
            # complete the operation.

            # calling the ALU exec method, giving it instr.opcode and the two operand values.
            result, flag = self.alu.exec(instr.op, left_operand, right_operand)
            # increment the program counter (register 15)
            self.pc.put(self.pc.get() + 1)

            if instr.op.name == "STORE":
                self.memory.put(result, self.registers[instr.reg_target].value)
            elif instr.op.name == "LOAD":
                regis = self.registers[instr.reg_target]
                value = self.memory.get(result)
                regis.put(value)
            elif instr.op.name == "HALT":
                self.halted = True
            elif instr.op.name == "ADD" or "SUB" or "MUL" or "DIV":
                regis = self.registers[instr.reg_target]
                regis.put(result)
                self.condition = CondFlag(flag)
        else:
            increment = self.pc.get() + 1
            self.pc.put(increment)

    def run(self, from_addr=0, single_step=False) -> None:
        self.halted = False
        self.pc.put(from_addr)
        step_count = 0
        while not self.halted:
            if single_step:
                input("Step {}; press enter".format(step_count))
            self.step()
            step_count += 1
