"""
abstract: Tests [EIP-7709: Read BLOCKHASH from storage and update cost]
(https://eips.ethereum.org/EIPS/eip-7709)
    Tests for [EIP-7709: Read BLOCKHASH from storage and update cost]
    (https://eips.ethereum.org/EIPS/eip-7709).
"""

import pytest

from ethereum_test_forks import Verkle
from ethereum_test_tools import (
    Account,
    Address,
    Block,
    BlockchainTestFiller,
    Environment,
    TestAddress,
    TestAddress2,
    Transaction,
    WitnessCheck,
)
from ethereum_test_types.verkle.helpers import Hash, chunkify_code
from ethereum_test_tools.vm.opcode import Opcodes as Op

REFERENCE_SPEC_GIT_PATH = "EIPS/eip-7709.md"
REFERENCE_SPEC_VERSION = "TODO"

system_contract_address = Address("0xfffffffffffffffffffffffffffffffffffffffe")
HISTORY_SERVE_WINDOW = 8192
BLOCKHASH_SERVE_WINDOW = 256
block_number = BLOCKHASH_SERVE_WINDOW + 5


@pytest.mark.valid_from("Verkle")
@pytest.mark.parametrize(
    "blocknum_target",
    [
        block_number + 1,
        block_number,
        block_number - 1,
        block_number - 2,
        block_number - BLOCKHASH_SERVE_WINDOW,
        block_number - BLOCKHASH_SERVE_WINDOW - 1,
    ],
    ids=[
        "future_block",
        "current_block",
        "previous_block",  # Note this block is also written by EIP-2935
        "previous_previous_block",
        "last_supported_block",
        "too_old_block",
    ],
)
def test_blockhash(blockchain_test: BlockchainTestFiller, blocknum_target: int):
    """
    Test BLOCKHASH witness.
    """
    _blockhash(blockchain_test, blocknum_target)


@pytest.mark.valid_from("Verkle")
def test_blockhash_warm(blockchain_test: BlockchainTestFiller):
    """
    Test BLOCKHASH witness with warm cost.
    """
    _blockhash(blockchain_test, block_number - 2, warm=True)


@pytest.mark.valid_from("Verkle")
def test_blockhash_insufficient_gas(blockchain_test: BlockchainTestFiller):
    """
    Test BLOCKHASH with insufficient gas.
    """
    _blockhash(blockchain_test, block_number - 2, gas_limit=21_020, fail=True)


def _blockhash(
    blockchain_test: BlockchainTestFiller,
    blocknum_target: int,
    gas_limit: int = 1_000_000,
    warm: bool = False,
    fail: bool = False,
):
    env = Environment(
        fee_recipient="0x2adc25665018aa1fe0e6bc666dac8fc2697ff9ba",
        difficulty=0x20000,
        gas_limit=10000000000,
        number=0,
        timestamp=1000,
    )

    pre = {
        TestAddress: Account(balance=1000000000000000000000),
        TestAddress2: Account(code=Op.BLOCKHASH(blocknum_target) * (2 if warm else 1)),
    }

    # Create block_number-1 empty blocks to fill the ring buffer.
    blocks: list[Block] = []
    for b in range(block_number - 1):
        blocks.append(Block())

    tx = Transaction(
        ty=0x0,
        chain_id=0x01,
        nonce=0,
        to=TestAddress2,
        gas_limit=gas_limit,
        gas_price=10,
    )

    witness_check = WitnessCheck(fork=Verkle)
    for address in [env.fee_recipient, TestAddress, TestAddress2]:
        witness_check.add_account_full(address=address, account=pre.get(address))
    code_chunks = chunkify_code(pre[TestAddress2].code)
    for i, chunk in enumerate(code_chunks, start=0):
        witness_check.add_code_chunk(address=TestAddress2, chunk_number=i, value=chunk)

    # TODO(verkle): fill right values when WitnessCheck allows to assert 2935 contract witness.
    hardcoded_blockhash = {
        block_number - 2: Hash(0x1B027321A3F7FE2F073F9B9C654CF3E62ABD2A8324A198FD7C46D056BC3CE976),
        block_number - BLOCKHASH_SERVE_WINDOW: Hash(0xCCCCCCCCC),
    }

    # This is the condition described in EIP-7709 which doesn't return 0.
    if not fail and not (
        blocknum_target >= block_number or blocknum_target + BLOCKHASH_SERVE_WINDOW < block_number
    ):
        witness_check.add_storage_slot(
            system_contract_address,
            blocknum_target % HISTORY_SERVE_WINDOW,
            hardcoded_blockhash.get(blocknum_target),
        )

    # The last block contains a single transaction with the BLOCKHASH instruction(s).
    blocks.append(
        Block(
            txs=[tx],
            witness_check=witness_check,
        )
    )

    blockchain_test(
        genesis_environment=env,
        pre=pre,
        post={},
        blocks=blocks,
    )
