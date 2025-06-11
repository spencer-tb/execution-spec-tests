"""
abstract: Test [EIP-7934: RLP Execution Block Size Limit](https://eips.ethereum.org/EIPS/eip-7934)
    Tests for [EIP-7934: RLP Execution Block Size Limit](https://eips.ethereum.org/EIPS/eip-7934).
"""

from typing import List

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


def create_test_header() -> FixtureHeader:
    """Create a standard test header for RLP size calculations."""
    return FixtureHeader(
        difficulty="0x0",
        number="0x1",
        gas_limit="0x5f5e100",  # 100M gas limit
        timestamp="0x499602d2",
        coinbase="0x" + "00" * 20,
        parent_hash="0x" + "00" * 32,
        uncle_hash="0x1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347",
        state_root="0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421",
        transactions_trie="0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421",
        receiptTrie="0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421",
        bloom="0x" + "00" * 256,
        gas_used="0x0",
        extra_data="0x00",
        mix_hash="0x" + "00" * 32,
        nonce="0x0000000000000042",
        base_fee_per_gas="0x0",
        withdrawals_root="0x" + "00" * 32,
        blob_gas_used="0x0",
        excess_blob_gas="0x0",
        parent_beacon_block_root="0x" + "00" * 32,
        requests_hash="0xe3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )


def get_block_rlp_size(transactions: List[Transaction]) -> int:
    """Calculate the RLP size of a block with given transactions."""
    header = create_test_header()

    total_gas = sum((tx.gas_limit or 21000) for tx in transactions)
    header.gas_used = ZeroPaddedHexNumber(total_gas)

    test_block = FixtureBlockBase(blockHeader=header)
    return len(test_block.with_rlp(txs=transactions).rlp)


@pytest.fixture
def exact_size_transactions(
    sender, block_size_limit: int, fork: Fork
) -> List[Transaction]:
    """Generate transactions that fill a block to exactly the RLP size limit."""
    transactions = []
    target_size = block_size_limit

    # Calculate base block size without transactions
    base_size = get_block_rlp_size([])
    available_bytes = target_size - base_size

    print(f"Target: {target_size}, Base: {base_size}, Available: {available_bytes}")

    nonce = 0
    total_gas_used = 0
    max_block_gas = 99_500_000

    LARGE_CALLDATA_SIZE = 500_000
    BASE_TX_GAS = 21_000

    calculator = fork.transaction_intrinsic_cost_calculator()

    data_large = b"\x00" * LARGE_CALLDATA_SIZE
    gas_limit_large = calculator(calldata=data_large)

    while total_gas_used + gas_limit_large <= max_block_gas:
        tx = Transaction(
            sender=sender,
            nonce=nonce,
            max_fee_per_gas=10**11,
            max_priority_fee_per_gas=10**11,
            gas_limit=gas_limit_large,
            data=data_large,
        )

        test_size = get_block_rlp_size(transactions + [tx])
        if test_size > target_size:
            print(
                f"Transaction {nonce} would exceed target ({test_size:,} > {target_size:,})"
            )
            break

        transactions.append(tx)
        total_gas_used += gas_limit_large
        nonce += 1

        if nonce % 2 == 0:
            current_size = get_block_rlp_size(transactions)
            remaining_bytes = target_size - current_size
            print(
                f"  {nonce} txs: size={current_size:,}, remaining={remaining_bytes:,}, gas={total_gas_used:,}"
            )

    current_size = get_block_rlp_size(transactions)
    remaining_bytes = target_size - current_size
    remaining_gas = max_block_gas - total_gas_used

    print(f"\nAfter main transactions:")
    print(f"  Transactions: {len(transactions)}")
    print(f"  Current size: {current_size:,}")
    print(f"  Remaining bytes: {remaining_bytes:,}")
    print(f"  Remaining gas: {remaining_gas:,}")

    if remaining_bytes > 1000 and remaining_gas > 100_000:
        print(f"Final precise targeting for {remaining_bytes} remaining bytes...")
        print(f"  Available gas: {remaining_gas:,}")

        # Use binary search with intrinsic gas calculator (from version 1)
        print(f"  Using binary search with intrinsic gas calculator...")

        best_calldata = 0
        best_diff = remaining_bytes

        # Calculate approximate max calldata we can afford
        # Test a sample to estimate gas per byte
        sample_calldata = b"\x00" * 1000  # 1KB sample
        sample_gas = calculator(calldata=sample_calldata)
        gas_per_kb = sample_gas - calculator(calldata=b"")  # Subtract base gas

        # Estimate max calldata bytes we can afford
        max_calldata_estimate = (
            (remaining_gas * 1000) // gas_per_kb if gas_per_kb > 0 else 100_000
        )
        max_calldata = min(
            remaining_bytes * 2, max_calldata_estimate, 500_000
        )  # Cap at 500KB

        print(f"  Estimated max calldata: {max_calldata:,} bytes")

        low, high = 0, max_calldata

        while low <= high:
            mid = (low + high) // 2
            test_calldata = b"\x00" * mid
            gas_needed = calculator(calldata=test_calldata)

            if gas_needed > remaining_gas:
                high = mid - 1
                continue

            test_tx = Transaction(
                sender=sender,
                nonce=nonce,
                max_fee_per_gas=10**11,
                max_priority_fee_per_gas=10**11,
                gas_limit=gas_needed,
                data=test_calldata,
            )

            test_size = get_block_rlp_size(transactions + [test_tx])

            if test_size == target_size:
                best_calldata = mid
                best_diff = 0
                print(f"  🎯 EXACT MATCH found at {mid:,} bytes!")
                break
            elif test_size < target_size:
                if target_size - test_size < best_diff:
                    best_diff = target_size - test_size
                    best_calldata = mid
                low = mid + 1
            else:
                high = mid - 1

        # Add the best final transaction
        if best_calldata > 0:
            final_calldata = b"\x00" * best_calldata
            final_gas = calculator(calldata=final_calldata)

            final_tx = Transaction(
                sender=sender,
                nonce=nonce,
                max_fee_per_gas=10**11,
                max_priority_fee_per_gas=10**11,
                gas_limit=final_gas,
                data=final_calldata,
            )
            transactions.append(final_tx)
            total_gas_used += final_gas

            print(
                f"  Added final transaction: {best_calldata:,} bytes calldata (diff: {best_diff})"
            )

            # Ultra-fine adjustment for those last few bytes
            if best_diff > 0 and best_diff <= 100:
                print(f"  🔧 Ultra-fine adjustment for final {best_diff} bytes...")
                found_exact = False

                # Strategy 1: Try slightly increasing calldata
                for extra_bytes in range(1, min(best_diff + 20, 100)):
                    new_calldata = b"\x00" * (best_calldata + extra_bytes)
                    new_gas = calculator(calldata=new_calldata)

                    if new_gas <= remaining_gas:
                        test_tx = Transaction(
                            sender=sender,
                            nonce=nonce,
                            max_fee_per_gas=10**11,
                            max_priority_fee_per_gas=10**11,
                            gas_limit=new_gas,
                            data=new_calldata,
                        )

                        test_size = get_block_rlp_size(transactions[:-1] + [test_tx])

                        if test_size == target_size:
                            transactions[-1] = test_tx
                            print(
                                f"    🎯 PERFECT! Added {extra_bytes} bytes calldata!"
                            )
                            found_exact = True
                            break
                        elif test_size > target_size:
                            break

                # Strategy 2: Try adjusting gas limit (different RLP encoding)
                if not found_exact:
                    print(f"    Trying gas limit adjustments...")
                    last_tx = transactions[-1]
                    base_gas = last_tx.gas_limit

                    for gas_extra in range(
                        1, min(50000, remaining_gas - total_gas_used)
                    ):
                        test_tx = Transaction(
                            sender=last_tx.sender,
                            nonce=last_tx.nonce,
                            max_fee_per_gas=last_tx.max_fee_per_gas,
                            max_priority_fee_per_gas=last_tx.max_priority_fee_per_gas,
                            gas_limit=base_gas + gas_extra,
                            data=last_tx.data,
                        )

                        test_size = get_block_rlp_size(transactions[:-1] + [test_tx])

                        if test_size == target_size:
                            transactions[-1] = test_tx
                            print(f"    🎯 PERFECT! Added {gas_extra} gas!")
                            found_exact = True
                            break
                        elif test_size > target_size:
                            break

                # Strategy 3: Try different fee values (different RLP encoding)
                if not found_exact:
                    print(f"    Trying fee adjustments...")
                    last_tx = transactions[-1]

                    fee_multipliers = [2, 3, 5, 10, 100, 1000, 10000]
                    for multiplier in fee_multipliers:
                        new_fee = 10**11 * multiplier

                        test_tx = Transaction(
                            sender=last_tx.sender,
                            nonce=last_tx.nonce,
                            max_fee_per_gas=new_fee,
                            max_priority_fee_per_gas=new_fee,
                            gas_limit=last_tx.gas_limit,
                            data=last_tx.data,
                        )

                        test_size = get_block_rlp_size(transactions[:-1] + [test_tx])

                        if test_size == target_size:
                            transactions[-1] = test_tx
                            print(f"    🎯 PERFECT! Used {multiplier}x fee multiplier!")
                            found_exact = True
                            break

                # Strategy 4: Try adding a minimal transaction
                if not found_exact and remaining_gas > 50_000:
                    print(f"    Trying minimal transaction...")

                    minimal_tx = Transaction(
                        sender=sender,
                        nonce=len(transactions),
                        max_fee_per_gas=10**11,
                        max_priority_fee_per_gas=10**11,
                        gas_limit=calculator(calldata=b""),
                        data=b"",
                    )

                    test_size = get_block_rlp_size(transactions + [minimal_tx])
                    if test_size == target_size:
                        transactions.append(minimal_tx)
                        print(f"    🎯 PERFECT! Added minimal transaction!")
                        found_exact = True
                    elif test_size < target_size:
                        print(
                            f"    Minimal tx still {target_size - test_size} bytes short"
                        )

                        # Try minimal tx with small calldata
                        for small_data_size in range(1, min(best_diff + 10, 50)):
                            small_data = b"\x00" * small_data_size
                            small_gas = calculator(calldata=small_data)

                            if total_gas_used + small_gas <= max_block_gas:
                                small_tx = Transaction(
                                    sender=sender,
                                    nonce=len(transactions),
                                    max_fee_per_gas=10**11,
                                    max_priority_fee_per_gas=10**11,
                                    gas_limit=small_gas,
                                    data=small_data,
                                )

                                test_size = get_block_rlp_size(
                                    transactions + [small_tx]
                                )
                                if test_size == target_size:
                                    transactions.append(small_tx)
                                    print(
                                        f"    🎯 PERFECT! Added minimal tx with {small_data_size} bytes!"
                                    )
                                    found_exact = True
                                    break
                                elif test_size > target_size:
                                    break

                if not found_exact:
                    print(f"    Could not close final {best_diff} byte gap")

    # Final results
    final_size = get_block_rlp_size(transactions)
    final_gas = sum(tx.gas_limit for tx in transactions)

    print(f"\nFinal results:")
    print(f"  Transactions: {len(transactions)}")
    print(f"  Block RLP size: {final_size:,} bytes")
    print(f"  Target size: {target_size:,} bytes")
    print(f"  Difference: {final_size - target_size:,} bytes")
    print(f"  Total gas used: {final_gas:,}")
    print(f"  Gas efficiency: {final_size / final_gas:.6f} bytes per gas")

    return transactions


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


def test_block_at_exact_rlp_size_limit(
    blockchain_test: BlockchainTestFiller,
    pre: Alloc,
    post: Alloc,
    exact_size_transactions: List[Transaction],
    block_size_limit: int,
    env: Environment,
):
    """Test that a block at exactly the MAX_RLP_BLOCK_SIZE is accepted."""
    block_rlp_size = get_block_rlp_size(exact_size_transactions)

    assert block_rlp_size == block_size_limit, (
        f"Block RLP size {block_rlp_size} does not exactly match limit {block_size_limit}, "
        f"difference: {block_rlp_size - block_size_limit} bytes"
    )

    block = Block(
        txs=exact_size_transactions,
        # TODO: test is passing right now... we need to figure out why this is
        #  not raising an exception
        # exception=BlockException.RLP_BLOCK_LIMIT_EXCEEDED,
    )

    blockchain_test(
        genesis_environment=env,
        pre=pre,
        post=post,
        blocks=[block],
    )


def test_block_slightly_over_rlp_size_limit(
    blockchain_test: BlockchainTestFiller,
    pre: Alloc,
    post: Alloc,
    exact_size_transactions: List[Transaction],
    sender,
    block_errors: List[BlockException],
):
    """Test that blocks slightly over the MAX_RLP_BLOCK_SIZE are rejected."""
    extra_tx = Transaction(
        sender=sender,
        nonce=len(exact_size_transactions),
        max_fee_per_gas=10**9,
        max_priority_fee_per_gas=10**9,
        gas_limit=100_000,
        data=b"\x00" * 100,
    )

    oversized_transactions = exact_size_transactions + [extra_tx]

    block = Block(
        txs=oversized_transactions,
        exception=block_errors[0],
    )

    blockchain_test(
        pre=pre,
        post=post,
        blocks=[block],
    )
