"""
Useful Verkle types for generating Ethereum tests.
"""

from typing import Dict

from pydantic import Field, RootModel

from ethereum_test_base_types import Alloc, CamelModel, PaddedFixedSizeBytes

IPA_PROOF_DEPTH = 8


class Hash(PaddedFixedSizeBytes[32]):  # type: ignore
    """
    Class that helps represent an un-padded Hash.
    """

    pass


class VerkleTree(RootModel[Dict[Hash, Hash]]):
    """
    Definition of a Verkle Tree.
    A Verkle Tree is a data structure used to efficiently prove the membership or non-membership
    of elements in a state. This class represents the Verkle Tree as a dictionary, where each key
    and value is a Hash (32 bytes). The root attribute holds this dictionary, providing a mapping
    of the tree's key/values.
    """

    root: Dict[Hash, Hash] = Field(default_factory=dict)


class VerkleAlloc(CamelModel):
    """
    An updated Alloc type specifically for filling tests from Verkle.

    VerkleAlloc contains both the initial Alloc MPT alongside the VerkleTree, where the MPT is used
    pre-dominantly to aid geth t8n's filling.
    """

    vkt: VerkleTree
    mpt: Alloc
