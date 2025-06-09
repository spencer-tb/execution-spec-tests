"""
abstract: Test [EIP-7934: RLP Execution Block Size Limit](https://eips.ethereum.org/EIPS/eip-7934)
    Tests for [EIP-7934: RLP Execution Block Size Limit](https://eips.ethereum.org/EIPS/eip-7934).
"""

from typing import List

import pytest

from ethereum_test_forks import Fork
from ethereum_test_tools import (
    Alloc,
    Block,
    BlockchainTestFiller,
    BlockException,
    Bytes,
    Transaction,
)

from .spec import Spec, ref_spec_7934

REFERENCE_SPEC_GIT_PATH = ref_spec_7934.git_path
REFERENCE_SPEC_VERSION = ref_spec_7934.version

pytestmark = pytest.mark.valid_from("Osaka")  # TODO: should this be Prague?


@pytest.fixture
def block_size_limit(fork: Fork) -> int:
    """Get the fork-specific block RLP size limit."""
    limit = fork.block_rlp_size_limit()
    if limit is None:
        raise ValueError("Fork does not implement block RLP size limit")
    assert limit == Spec.MAX_RLP_BLOCK_SIZE, (
        f"Expected block RLP size limit to be {Spec.MAX_RLP_BLOCK_SIZE}, "
        f"but got {limit} for fork {fork.name}"
    )
    return limit


@pytest.fixture
def block_errors() -> List[BlockException]:
    """Block exceptions expected for blocks that exceed the `MAX_RLP_BLOCK_SIZE`."""
    return [BlockException.RLP_BLOCK_LIMIT_EXCEEDED]


@pytest.fixture
def oversized_calldata(block_size_limit: int) -> Bytes:
    """Generate oversized calldata that exceeds the block limit."""
    size = block_size_limit + 10000  # Add buffer to exceed the limit
    return Bytes(b"0x" + b"ff" * size)


@pytest.fixture
def large_calldata(block_size_limit: int) -> Bytes:
    """Generate large calldata that's about 1/4 of the block limit."""
    size = block_size_limit // 4
    return Bytes(b"0x" + b"00" * size)


@pytest.fixture
def oversized_transaction(sender, oversized_calldata: Bytes):
    """Create a single transaction with oversized calldata."""
    from ethereum_test_tools import Transaction

    return Transaction(
        sender=sender,
        nonce=0,
        gas_price=1,
        data=oversized_calldata,
    )


@pytest.fixture
def multiple_large_transactions(sender, large_calldata: Bytes):
    """Create multiple transactions with large calldata."""
    from ethereum_test_tools import Transaction

    txs = []
    for i in range(5):
        tx = Transaction(
            sender=sender,
            nonce=i,
            gas_price=1,
            data=large_calldata,
        )
        txs.append(tx)
    return txs


def test_block_exceeds_rlp_size_limit(
    blockchain_test: BlockchainTestFiller,
    pre: Alloc,
    post: Alloc,
    oversized_transaction: Transaction,
):
    """Test that blocks exceeding the `MAX_RLP_BLOCK_SIZE` are rejected with a single tx."""
    block = Block(
        txs=[oversized_transaction],
        exception=BlockException.RLP_BLOCK_LIMIT_EXCEEDED,
    )

    blockchain_test(
        pre=pre,
        post=post,
        blocks=[block],
    )


def test_multiple_transactions_exceed_limit(
    blockchain_test: BlockchainTestFiller,
    pre: Alloc,
    post: Alloc,
    multiple_large_transactions: List[Transaction],
):
    """
    Test that blocks with multiple large transactions, that when combined exceed, the
    `MAX_RLP_BLOCK_SIZE` and are rejected.
    """
    block = Block(
        txs=multiple_large_transactions,
        exception=BlockException.RLP_BLOCK_LIMIT_EXCEEDED,
    )

    blockchain_test(
        pre=pre,
        post=post,
        blocks=[block],
    )
