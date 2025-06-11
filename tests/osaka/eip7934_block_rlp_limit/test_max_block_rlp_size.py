"""
abstract: Test [EIP-7934: RLP Execution Block Size Limit](https://eips.ethereum.org/EIPS/eip-7934)
    Tests for [EIP-7934: RLP Execution Block Size Limit](https://eips.ethereum.org/EIPS/eip-7934).
"""

from typing import List, Tuple

import pytest

from ethereum_test_base_types import AccessList, ZeroPaddedHexNumber
from ethereum_test_fixtures.blockchain import (
    FixtureBlockBase,
    FixtureHeader,
)
from ethereum_test_forks import Fork
from ethereum_test_tools import (
    Alloc,
    Block,
    BlockchainTestFiller,
    BlockException,
    Bytes,
    Transaction,
)
from ethereum_test_types import Environment

from .spec import Spec, ref_spec_7934

REFERENCE_SPEC_GIT_PATH = ref_spec_7934.git_path
REFERENCE_SPEC_VERSION = ref_spec_7934.version

pytestmark = pytest.mark.valid_from("Osaka")


HEADER_TIMESTAMP = 123456789
EXTRA_DATA_AT_LIMIT = b"\x00\x00\x00"
BLOCK_GAS_LIMIT = 100_000_000


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


def create_test_header(gas_used: int) -> FixtureHeader:
    """Create a standard test header for RLP size calculations."""
    return FixtureHeader(
        difficulty="0x0",
        number="0x1",
        gas_limit=hex(BLOCK_GAS_LIMIT),
        timestamp=hex(HEADER_TIMESTAMP),
        coinbase="0x" + "00" * 20,
        parent_hash="0x" + "00" * 32,
        uncle_hash="0x1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347",
        state_root="0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421",
        transactions_trie="0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421",
        receiptTrie="0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421",
        bloom="0x" + "00" * 256,
        gas_used=hex(gas_used),
        extra_data=EXTRA_DATA_AT_LIMIT.hex(),
        mix_hash="0x" + "00" * 32,
        nonce="0x0000000000000042",
        base_fee_per_gas="0x0",
        withdrawals_root="0x" + "00" * 32,
        blob_gas_used="0x0",
        excess_blob_gas="0x0",
        parent_beacon_block_root="0x" + "00" * 32,
        requests_hash="0xe3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )


def get_block_rlp_size(transactions: List[Transaction], gas_used: int) -> int:
    """Calculate the RLP size of a block with given transactions."""
    header = create_test_header(gas_used)

    total_gas = sum((tx.gas_limit or 21000) for tx in transactions)
    header.gas_used = ZeroPaddedHexNumber(total_gas)

    test_block = FixtureBlockBase(blockHeader=header, withdrawals=[])
    return len(test_block.with_rlp(txs=transactions).rlp)


@pytest.fixture
def exact_size_transactions(
    sender, block_size_limit: int, fork: Fork
) -> Tuple[List[Transaction], int]:
    """Generate transactions that fill a block to exactly the RLP size limit."""
    transactions = []
    target_size = block_size_limit

    nonce = 0
    total_gas_used = 0
    max_block_gas = 100_000_000

    calculator = fork.transaction_intrinsic_cost_calculator()

    data_large = b"\x00" * 500_000
    gas_limit_large = calculator(calldata=data_large)

    # block with 16 transactions + large calldata remains safely below the limit
    for _ in range(16):
        tx = Transaction(
            sender=sender,
            nonce=nonce,
            max_fee_per_gas=10**11,
            max_priority_fee_per_gas=10**11,
            gas_limit=gas_limit_large,
            data=data_large,
        )

        transactions.append(tx)
        total_gas_used += gas_limit_large
        nonce += 1

    current_size = get_block_rlp_size(transactions, gas_used=total_gas_used)
    remaining_bytes = target_size - current_size
    remaining_gas = max_block_gas - total_gas_used

    if remaining_bytes > 0 and remaining_gas > 50_000:
        base_tx = Transaction(
            sender=sender,
            nonce=nonce,
            max_fee_per_gas=10**11,
            max_priority_fee_per_gas=10**11,
            gas_limit=calculator(calldata=b""),
            data=b"",
        )

        test_block_with_empty = get_block_rlp_size(
            transactions + [base_tx], gas_used=total_gas_used
        )
        empty_tx_contribution = test_block_with_empty - current_size
        available_for_calldata = target_size - current_size - empty_tx_contribution

        if available_for_calldata > 0:
            # RLP encoding overhead for calldata:
            # - If length < 56: 1 byte prefix
            # - If length >= 56: 1 + length_bytes + data
            def calldata_rlp_overhead(size):
                if size < 56:
                    return 1
                else:
                    if size < 256:
                        return 2  # 0x81 + 1 length byte
                    elif size < 65536:
                        return 3  # 0x82 + 2 length bytes
                    else:
                        return 4  # 0x83 + 3 length bytes

            target_calldata_size = available_for_calldata - calldata_rlp_overhead(
                available_for_calldata
            )

            target_calldata = b"\x00" * target_calldata_size
            target_gas = calculator(calldata=target_calldata)

            if target_gas <= remaining_gas:
                final_tx = Transaction(
                    sender=sender,
                    nonce=nonce,
                    max_fee_per_gas=10**11,
                    max_priority_fee_per_gas=10**11,
                    gas_limit=target_gas,
                    data=target_calldata,
                )

                test_size = get_block_rlp_size(
                    transactions + [final_tx], gas_used=total_gas_used + target_gas
                )
                diff = target_size - test_size

                if test_size == target_size:
                    transactions.append(final_tx)
                else:
                    # fine-tune until exact match
                    best_diff = abs(diff)
                    best_tx = final_tx

                    search_range = min(abs(diff) + 50, 200)
                    for adjustment in range(-search_range, search_range + 1):
                        if target_calldata_size + adjustment < 0:
                            continue

                        adjusted_calldata = b"\x00" * (target_calldata_size + adjustment)
                        adjusted_gas = calculator(calldata=adjusted_calldata)

                        if adjusted_gas <= remaining_gas:
                            adjusted_tx = Transaction(
                                sender=sender,
                                nonce=nonce,
                                max_fee_per_gas=10**11,
                                max_priority_fee_per_gas=10**11,
                                gas_limit=adjusted_gas,
                                data=adjusted_calldata,
                            )

                            adjusted_test_size = get_block_rlp_size(
                                transactions + [adjusted_tx],
                                gas_used=total_gas_used + adjusted_gas,
                            )
                            adjusted_diff = abs(target_size - adjusted_test_size)

                            if adjusted_test_size == target_size:
                                transactions.append(adjusted_tx)
                                break
                            elif adjusted_diff < best_diff:
                                best_diff = adjusted_diff
                                best_tx = adjusted_tx

                    else:
                        transactions.append(best_tx)

    final_size = get_block_rlp_size(transactions, gas_used=total_gas_used)
    final_gas = sum(tx.gas_limit for tx in transactions)

    assert final_size == target_size, "could not calculate exact block size"

    return transactions, final_gas


@pytest.fixture
def oversized_calldata(block_size_limit: int) -> Bytes:
    """Generate oversized calldata that exceeds the block limit."""
    size = block_size_limit + 10000
    return Bytes(b"0x" + b"ff" * size)


@pytest.fixture
def large_calldata(block_size_limit: int) -> Bytes:
    """Generate large calldata that's about 1/4 of the block limit."""
    size = block_size_limit // 4
    return Bytes(b"0x" + b"00" * size)


@pytest.fixture
def oversized_transaction(sender, oversized_calldata: Bytes):
    """Create a single transaction with oversized calldata."""
    return Transaction(
        sender=sender,
        nonce=0,
        max_fee_per_gas=10**11,
        max_priority_fee_per_gas=10**11,
        gas_limit=30_000_000,
        data=oversized_calldata,
    )


@pytest.fixture
def multiple_large_transactions(sender, large_calldata: Bytes):
    """Create multiple transactions with large calldata."""
    txs = []
    for i in range(5):
        tx = Transaction(
            sender=sender,
            nonce=i,
            max_fee_per_gas=10**11,
            max_priority_fee_per_gas=10**11,
            gas_limit=30_000_000,
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
    """Test that blocks with multiple large transactions exceed the `MAX_RLP_BLOCK_SIZE`."""
    block = Block(
        txs=multiple_large_transactions,
        exception=BlockException.RLP_BLOCK_LIMIT_EXCEEDED,
    )

    blockchain_test(
        pre=pre,
        post=post,
        blocks=[block],
    )


# TODO: If we try to raise the exception, the test fails on the 2 successful runs. If
#  we don't raise the exception, the test fails on the 3rd run with an exception. Either
#  way, this is currently testing the boundary... we just need a better setup.
# @pytest.mark.exception_test
@pytest.mark.parametrize("from_limit", [-1, 0, 1])
def test_block_at_exact_rlp_size_limit(
    blockchain_test: BlockchainTestFiller,
    pre: Alloc,
    post: Alloc,
    exact_size_transactions: Tuple[List[Transaction], int],
    block_size_limit: int,
    env: Environment,
    from_limit: int,
):
    """
    Test the block rlp size limit.

    - At the limit - 1 byte, the block is valid
    - At the limit, the block is valid
    - At the limit + 1 byte, the block is invalid
    """
    transactions, gas_used = exact_size_transactions
    block_rlp_size = get_block_rlp_size(transactions, gas_used=gas_used)

    assert block_rlp_size == block_size_limit, (
        f"Block RLP size {block_rlp_size} does not exactly match limit {block_size_limit}, "
        f"difference: {block_rlp_size - block_size_limit} bytes"
    )

    # exception = BlockException.RLP_BLOCK_LIMIT_EXCEEDED if from_limit == 1 else None
    block = Block(
        txs=transactions,
        # exception=exception,
    )

    if from_limit == -1:
        # remove last byte
        block.extra_data = Bytes(EXTRA_DATA_AT_LIMIT[:-1])
    elif from_limit == 0:
        block.extra_data = Bytes(EXTRA_DATA_AT_LIMIT)
    elif from_limit == 1:
        block.extra_data = Bytes(EXTRA_DATA_AT_LIMIT + b"\x00")
    else:
        raise ValueError(f"Invalid from_limit value: {from_limit}")
    block.timestamp = ZeroPaddedHexNumber(HEADER_TIMESTAMP)

    blockchain_test(
        genesis_environment=env,
        pre=pre,
        post=post,
        blocks=[block],
    )


@pytest.mark.exception_test
def test_block_slightly_over_rlp_size_limit(
    blockchain_test: BlockchainTestFiller,
    pre: Alloc,
    post: Alloc,
    exact_size_transactions: List[Transaction],
    block_size_limit: int,
    sender,
    env: Environment,
):
    """Test that a block at exactly the MAX_RLP_BLOCK_SIZE is accepted."""
    block_rlp_size = get_block_rlp_size(exact_size_transactions)
    assert block_rlp_size == block_size_limit, (
        f"Block RLP size {block_rlp_size} does not exactly match limit {block_size_limit}, "
        f"difference: {block_rlp_size - block_size_limit} bytes"
    )
    extra_tx = Transaction(
        sender=sender,
        nonce=len(exact_size_transactions),
        max_fee_per_gas=10**9,
        max_priority_fee_per_gas=10**9,
        gas_limit=200_000,
        data=b"\x00" * 100,
    )
    block = Block(
        txs=exact_size_transactions + [extra_tx],
        exception=BlockException.RLP_BLOCK_LIMIT_EXCEEDED,
    )
    blockchain_test(
        genesis_environment=env,
        pre=pre,
        post=post,
        blocks=[block],
    )
