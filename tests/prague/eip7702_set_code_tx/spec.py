"""
Defines EIP-7702 specification constants and functions.
"""
from dataclasses import dataclass

from ethereum_test_base_types import Address, Bytes


@dataclass(frozen=True)
class ReferenceSpec:
    """
    Defines the reference spec version and git path.
    """

    git_path: str
    version: str


ref_spec_7702 = ReferenceSpec("EIPS/eip-7702.md", "a6bf54ffc1506ed00f8234731684ccfe935ec9a3")


@dataclass(frozen=True)
class Spec:
    """
    Parameters from the EIP-7702 specifications as defined at
    https://eips.ethereum.org/EIPS/eip-7702
    """

    SET_CODE_TX_TYPE = 0x04
    MAGIC = 0x05
    PER_AUTH_BASE_COST = 2_500
    PER_EMPTY_ACCOUNT_COST = 25_000
    DELEGATION_DESIGNATION = bytes.fromhex("ef0100")

    @staticmethod
    def delegation_designation(address: Address) -> Bytes:
        """
        Returns the delegation designation for the given address.
        """
        return Bytes(Spec.DELEGATION_DESIGNATION + bytes(address))