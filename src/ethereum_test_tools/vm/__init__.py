"""
Ethereum Virtual Machine related definitions and utilities.
"""

from .opcode import Bytecode, Macro, Macros, Opcode, OpcodeCallArg, Opcodes, UndefinedOpcodes

__all__ = (
    "Bytecode",
    "Opcode",
    "Macro",
    "Macros",
    "OpcodeCallArg",
    "Opcodes",
    "UndefinedOpcodes",
)
