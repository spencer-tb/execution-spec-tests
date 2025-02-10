"""Osaka fork definition."""

from typing import List, Tuple

from semver import Version

from ethereum_test_vm import EVMCodeType, Opcodes

from ..prague.fork import Prague


class Osaka(Prague, solc_name="cancun"):
    """Osaka fork."""

    @classmethod
    def evm_code_types(cls, block_number: int = 0, timestamp: int = 0) -> List[EVMCodeType]:
        """EOF V1 is supported starting from Osaka."""
        return super().evm_code_types(
            block_number,
            timestamp,
        ) + [EVMCodeType.EOF_V1]

    @classmethod
    def call_opcodes(
        cls, block_number: int = 0, timestamp: int = 0
    ) -> List[Tuple[Opcodes, EVMCodeType]]:
        """EOF V1 introduces EXTCALL, EXTSTATICCALL, EXTDELEGATECALL."""
        return [
            (Opcodes.EXTCALL, EVMCodeType.EOF_V1),
            (Opcodes.EXTSTATICCALL, EVMCodeType.EOF_V1),
            (Opcodes.EXTDELEGATECALL, EVMCodeType.EOF_V1),
        ] + super().call_opcodes(block_number, timestamp)

    @classmethod
    def is_deployed(cls) -> bool:
        """Flag that the fork has not been deployed to mainnet."""
        return False

    @classmethod
    def solc_min_version(cls) -> Version:
        """Return minimum version of solc that supports this fork."""
        return Version.parse("1.0.0")  # set a high version; currently unknown
