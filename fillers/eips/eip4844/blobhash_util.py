"""
Utility Module: BLOBHASH Opcode
Tests: fillers/eips/eip4844/
    > blobhash_opcode_contexts.py
    > blobhash_opcode.py
"""

from ethereum_test_tools import (
    TestAddress,
    Yul,
    add_kzg_version,
    compute_create2_address,
    compute_create_address,
    to_address,
)
from ethereum_test_tools.vm.opcode import Opcodes as Op

BLOBHASH_GAS_COST = 3
TARGET_BLOB_PER_BLOCK = 2
MAX_BLOB_PER_BLOCK = 4
BLOB_COMMITMENT_VERSION_KZG = 1


# Simple list of blob versioned hashes ranging from bytes32(1 to 4)
simple_blob_hashes: list[bytes] = add_kzg_version(
    [(1 << x) for x in range(MAX_BLOB_PER_BLOCK)],
    BLOB_COMMITMENT_VERSION_KZG,
)

# Random fixed list of blob versioned hashes
random_blob_hashes = add_kzg_version(
    [
        "0x00b8c5b09810b5fc07355d3da42e2c3a3e200c1d9a678491b7e8e256fc50cc4f",
        "0x005b4c8cc4f86aa2d2cf9e9ce97fca704a11a6c20f6b1d6c00a6e15f6d60a6df",
        "0x00878f80eaf10be1a6f618e6f8c071b10a6c14d9b89a3bf2a3f3cf2db6c5681d",
        "0x004eb72b108d562c639faeb6f8c6f366a28b0381c7d30431117ec8c7bb89f834",
        "0x00a9b2a6c3f3f0675b768d49b5f5dc5b5d988f88d55766247ba9e40b125f16bb",
        "0x00a4d4cde4aa01e57fb2c880d1d9c778c33bdf85e48ef4c4d4b4de51abccf4ed",
        "0x0071c9b8a0c72d38f5e5b5d08e5cb5ce5e23fb1bc5d75f9c29f7b94df0bceeb7",
        "0x002c8b6a8b11410c7d98d790e1098f1ed6d93cb7a64711481aaab1848e13212f",
        "0x00d78c25f8a1d6aa04d0e2e2a71cf8dfaa4239fa0f301eb57c249d1e6bfe3c3d",
        "0x00c778eb1348a73b9c30c7b1d282a5f8b2c5b5a12d5c5e4a4a35f9c5f639b4a4",
    ],
    BLOB_COMMITMENT_VERSION_KZG,
)

# Blobhash index values for test_blobhash_gas_cost
blobhash_index_values = [
    0x00,
    0x01,
    0x02,
    0x03,
    0x04,
    2**256 - 1,
    0xA12C8B6A8B11410C7D98D790E1098F1ED6D93CB7A64711481AAAB1848E13212F,
]


class BlobhashContext:
    """
    A utility class for mapping common EVM opcodes in different contexts
    to specific bytecode (with BLOBHASH), addresses and contracts.
    """

    addresses = {
        "blobhash_sstore": to_address(0x100),
        "blobhash_return": to_address(0x600),
        "call": to_address(0x200),
        "delegatecall": to_address(0x300),
        "callcode": to_address(0x800),
        "staticcall": to_address(0x700),
        "create": to_address(0x400),
        "create2": to_address(0x500),
    }

    @staticmethod
    def _get_blobhash_verbatim():
        """
        Returns the BLOBHASH verbatim as a formatted string.
        """
        return "verbatim_{}i_{}o".format(
            Op.BLOBHASH.popped_stack_items,
            Op.BLOBHASH.pushed_stack_items,
        )

    @classmethod
    def address(cls, context_name):
        """
        Maps an opcode context to a specific address.
        """
        address = cls.addresses.get(context_name)
        if address is None:
            raise ValueError(f"Invalid context: {context_name}")
        return address

    @classmethod
    def code(cls, context_name):
        """
        Maps an opcode context to bytecode that utilizes the BLOBHASH opcode.
        """
        blobhash_verbatim = cls._get_blobhash_verbatim()

        code = {
            "blobhash_sstore": Yul(
                f"""
                {{
                   let pos := calldataload(0)
                   let end := calldataload(32)
                   for {{}} lt(pos, end) {{ pos := add(pos, 1) }}
                   {{
                    let blobhash := {blobhash_verbatim}
                        (hex"{Op.BLOBHASH.hex()}", pos)
                    sstore(pos, blobhash)
                   }}
                   let blobhash := {blobhash_verbatim}
                        (hex"{Op.BLOBHASH.hex()}", end)
                   sstore(end, blobhash)
                   return(0, 0)
                }}
                """
            ),
            "blobhash_return": Yul(
                f"""
                {{
                   let pos := calldataload(0)
                   let blobhash := {blobhash_verbatim}
                        (hex"{Op.BLOBHASH.hex()}", pos)
                   mstore(0, blobhash)
                   return(0, 32)
                }}
                """
            ),
            "call": Yul(
                """
                {
                    calldatacopy(0, 0, calldatasize())
                    pop(call(gas(), 0x100, 0, 0, calldatasize(), 0, 0))
                }
                """
            ),
            "delegatecall": Yul(
                """
                {
                    calldatacopy(0, 0, calldatasize())
                    pop(delegatecall(gas(), 0x100, 0, calldatasize(), 0, 0))
                }
                """
            ),
            "callcode": Yul(
                f"""
                {{
                    let pos := calldataload(0)
                    let end := calldataload(32)
                    for {{ }} lt(pos, end) {{ pos := add(pos, 1) }}
                    {{
                    mstore(0, pos)
                    pop(callcode(gas(),
                        {cls.address("blobhash_return")}, 0, 0, 32, 0, 32))
                    let blobhash := mload(0)
                    sstore(pos, blobhash)
                    }}

                    mstore(0, end)
                    pop(callcode(gas(),
                        {cls.address("blobhash_return")}, 0, 0, 32, 0, 32))
                    let blobhash := mload(0)
                    sstore(end, blobhash)
                    return(0, 0)
                }}
                """
            ),
            "staticcall": Yul(
                f"""
                {{
                    let pos := calldataload(0)
                    let end := calldataload(32)
                    for {{ }} lt(pos, end) {{ pos := add(pos, 1) }}
                    {{
                    mstore(0, pos)
                    pop(staticcall(gas(),
                        {cls.address("blobhash_return")}, 0, 32, 0, 32))
                    let blobhash := mload(0)
                    sstore(pos, blobhash)
                    }}

                    mstore(0, end)
                    pop(staticcall(gas(),
                        {cls.address("blobhash_return")}, 0, 32, 0, 32))
                    let blobhash := mload(0)
                    sstore(end, blobhash)
                    return(0, 0)
                }}
                """
            ),
            "create": Yul(
                """
                {
                    calldatacopy(0, 0, calldatasize())
                    pop(create(0, 0, calldatasize()))
                }
                """
            ),
            "create2": Yul(
                """
                {
                    calldatacopy(0, 0, calldatasize())
                    pop(create2(0, 0, calldatasize(), 0))
                }
                """
            ),
            "initcode": Yul(
                f"""
                {{
                   for {{ let pos := 0 }} lt(pos, 10) {{ pos := add(pos, 1) }}
                   {{
                    let blobhash := {blobhash_verbatim}
                        (hex"{Op.BLOBHASH.hex()}", pos)
                    sstore(pos, blobhash)
                   }}
                   return(0, 0)
                }}
                """
            ),
        }
        code = code.get(context_name)
        if code is None:
            raise ValueError(f"Invalid context: {context_name}")
        return code

    @classmethod
    def created_contract(cls, context_name):
        """
        Maps contract creation to a specific context to a specific address.
        """
        contract = {
            "tx_created_contract": compute_create_address(TestAddress, 0),
            "create": compute_create_address(
                cls.address("create"),
                0,
            ),
            "create2": compute_create2_address(
                cls.address("create2"),
                0,
                cls.code("initcode").assemble(),
            ),
        }
        contract = contract.get(context_name)
        if contract is None:
            raise ValueError(f"Invalid contract: {context_name}")
        return contract


class BlobhashScenario:
    """
    A utility class for generating blobhash calls.
    """

    MAX_BLOB_PER_BLOCK = 4

    @staticmethod
    def blobhash_sstore(index: int):
        """
        Returns an BLOBHASH sstore to the given index.
        """
        return Op.SSTORE(index, Op.BLOBHASH(index))

    @classmethod
    def generate_blobhash_calls(cls, scenario_name: str) -> bytes:
        """
        Returns BLOBHASH bytecode calls for the given scenario.
        """
        scenarios = {
            "single_valid": lambda: b"".join(
                cls.blobhash_sstore(i) for i in range(cls.MAX_BLOB_PER_BLOCK)
            ),
            "repeated_valid": lambda: b"".join(
                b"".join(cls.blobhash_sstore(i) for _ in range(10))
                for i in range(cls.MAX_BLOB_PER_BLOCK)
            ),
            "valid_invalid": lambda: b"".join(
                cls.blobhash_sstore(i)
                + cls.blobhash_sstore(cls.MAX_BLOB_PER_BLOCK)
                + cls.blobhash_sstore(i)
                for i in range(cls.MAX_BLOB_PER_BLOCK)
            ),
            "varied_valid": lambda: b"".join(
                cls.blobhash_sstore(i)
                + cls.blobhash_sstore(i + 1)
                + cls.blobhash_sstore(i)
                for i in range(cls.MAX_BLOB_PER_BLOCK - 1)
            ),
            "invalid_calls": lambda: b"".join(
                cls.blobhash_sstore(i)
                for i in range(-5, cls.MAX_BLOB_PER_BLOCK + 5)
            ),
        }
        scenario = scenarios.get(scenario_name)
        if scenario is None:
            raise ValueError(f"Invalid scenario: {scenario_name}")
        return scenario()
