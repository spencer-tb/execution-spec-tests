"""
Define an entry point wrapper for pytest.
"""

from typing import Any, List, Optional

import click

from ethereum_test_vm import Macro
from ethereum_test_vm import Opcodes as Op


def process_evm_bytes(evm_bytes_hex_string: Any) -> str:  # noqa: D103
    if evm_bytes_hex_string.startswith("0x"):
        evm_bytes_hex_string = evm_bytes_hex_string[2:]

    evm_bytes = bytearray(bytes.fromhex(evm_bytes_hex_string))

    opcodes_strings: List[str] = []

    while evm_bytes:
        opcode_byte = evm_bytes.pop(0)

        opcode: Optional[Op] = None
        for op in Op:
            if not isinstance(op, Macro) and op.int() == opcode_byte:
                opcode = op
                break

        if opcode is None:
            raise ValueError(f"Unknown opcode: {opcode_byte}")

        if opcode.data_portion_length > 0:
            data_portion = hex(int.from_bytes(evm_bytes[: opcode.data_portion_length], "big"))
            evm_bytes = evm_bytes[opcode.data_portion_length :]
            opcodes_strings.append(f"Op.{opcode._name_}[{data_portion}]")
        elif opcode == Op.RJUMPV:
            max_index = evm_bytes.pop(0)
            operands: List[str] = []
            for _ in range(max_index + 1):
                operands.append(hex(int.from_bytes(evm_bytes[:2], "big")))
                evm_bytes = evm_bytes[2:]
            opcodes_strings.append(f"Op.{opcode._name_}[{','.join(operands)}]")
        else:
            opcodes_strings.append(f"Op.{opcode._name_}")

    return " + ".join(opcodes_strings)


@click.command()
@click.argument("evm_bytes_hex_string")
def main(evm_bytes_hex_string: str):
    """
    Convert the given EVM bytes hex string to an EEST Opcodes.

    \b
    EVM_BYTES_HEX_STRING: A hex string representing EVM bytes to be processed.
    """  # noqa: D301
    processed_output = process_evm_bytes(evm_bytes_hex_string)
    click.echo(processed_output)


if __name__ == "__main__":
    main()
