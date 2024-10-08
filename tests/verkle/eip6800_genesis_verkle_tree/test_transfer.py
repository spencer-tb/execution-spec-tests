"""
abstract: Tests [EIP-6800: Ethereum state using a unified verkle tree]
(https://eips.ethereum.org/EIPS/eip-6800)
    Tests for [EIP-6800: Ethereum state using a unified verkle tree]
    (https://eips.ethereum.org/EIPS/eip-6800).
"""

import pytest

from ethereum_test_tools import (
    Account,
    Address,
    Block,
    BlockchainTestFiller,
    Environment,
    TestAddress,
    TestAddress2,
    Transaction,
)

REFERENCE_SPEC_GIT_PATH = "EIPS/eip-6800.md"
REFERENCE_SPEC_VERSION = "2f8299df31bb8173618901a03a8366a3183479b0"

precompile_address = Address("0x04")


@pytest.mark.valid_from("Verkle")
@pytest.mark.parametrize(
    "target",
    [
        TestAddress2,
        precompile_address,
    ],
    ids=["no_precompile", "precompile"],
)
@pytest.mark.parametrize(
    "value",
    [0, 6],
    ids=["zero", "non_zero"],
)
def test_transfer_eth(blockchain_test: BlockchainTestFiller, fork: str, target, value):
    """
    Test that value transfer works as expected targeting accounts and precompiles.
    """
    env = Environment(
        fee_recipient="0x2adc25665018aa1fe0e6bc666dac8fc2697ff9ba",
        difficulty=0x20000,
        gas_limit=10000000000,
        number=1,
        timestamp=1000,
    )
    pre = {
        TestAddress: Account(balance=1000000000000000000000),
    }
    tx = Transaction(
        ty=0x0,
        chain_id=0x01,
        nonce=0,
        to=target,
        gas_limit=100000000,
        gas_price=10,
        value=value,
    )
    blocks = [Block(txs=[tx])]

    post = {
        target: Account(
            balance=value,
        ),
    }

    blockchain_test(
        genesis_environment=env,
        pre=pre,
        post=post,
        blocks=blocks,
    )
