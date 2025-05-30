"""
abstract: Tests [EIP-4762: Statelessness gas cost changes]
(https://eips.ethereum.org/EIPS/eip-4762)
    Tests for [EIP-4762: Statelessness gas cost changes]
    (https://eips.ethereum.org/EIPS/eip-4762).
"""

import pytest
from ethereum.crypto.hash import keccak256

from ethereum_test_forks import Verkle
from ethereum_test_tools import (
    Account,
    Address,
    Block,
    BlockchainTestFiller,
    Environment,
    Hash,
    TestAddress,
    TestAddress2,
    Transaction,
    WitnessCheck,
)
from ethereum_test_tools.vm.opcode import Opcodes as Op
from ethereum_test_types.verkle.types import Hash as HashVerkle
from ethereum_test_types.verkle.helpers import chunkify_code

REFERENCE_SPEC_GIT_PATH = "EIPS/eip-4762.md"
REFERENCE_SPEC_VERSION = "2f8299df31bb8173618901a03a8366a3183479b0"

precompile_address = Address("0x04")
system_contract_address = Address("0xfffffffffffffffffffffffffffffffffffffffe")
EmptyAddress = Address("0xd94f5374fce5edbc8e2a8697c15331677e6ebf0c")

TestAccount = Account(balance=1000000000000000000000)

ExampleAddress = Address("0xfffffff4fce5edbc8e2a8697c15331677e6ebf0c")
ExampleAccount = Account(code=Op.PUSH0 * 300)


@pytest.mark.valid_from("Verkle")
@pytest.mark.parametrize(
    "target",
    [
        TestAddress,
        ExampleAddress,
        EmptyAddress,
        system_contract_address,
        precompile_address,
    ],
    ids=[
        "eoa",
        "contract",
        "non_existent_account",
        "system_contract",
        "precompile",
    ],
)
def test_extcodehash(blockchain_test: BlockchainTestFiller, fork: str, target):
    """
    Test EXTCODEHASH witness.
    """
    witness_check_extra = WitnessCheck(fork=Verkle)
    if target == ExampleAddress:
        witness_check_extra.add_account_codehash(
            ExampleAddress, HashVerkle(keccak256(ExampleAccount.code))
        )
    elif target == TestAddress:
        witness_check_extra.add_account_codehash(
            TestAddress, HashVerkle(keccak256(TestAccount.code))
        )
    elif target == EmptyAddress:
        witness_check_extra.add_account_codehash(EmptyAddress, None)
    # For precompile or system contract, we don't need to add any witness.
    _extcodehash(blockchain_test, target, witness_check_extra)


@pytest.mark.valid_from("Verkle")
def test_extcodehash_warm(blockchain_test: BlockchainTestFiller):
    """
    Test EXTCODEHASH with WARM cost.
    """
    witness_check_extra = WitnessCheck(fork=Verkle)
    witness_check_extra.add_account_codehash(
        ExampleAddress, HashVerkle(keccak256(ExampleAccount.code))
    )

    _extcodehash(blockchain_test, ExampleAddress, witness_check_extra, warm=True)


@pytest.mark.valid_from("Verkle")
@pytest.mark.parametrize(
    "gas_limit, witness_assert_codehash",
    [
        (21_203 + 2099, False),
        (21_203 + 2100, True),
    ],
    ids=[
        "insufficient_gas_codehash",
        "just_enough_gas_codehash",
    ],
)
def test_extcodehash_insufficient_gas(
    blockchain_test: BlockchainTestFiller,
    gas_limit: int,
    witness_assert_codehash,
):
    """
    Test EXTCODEHASH with insufficient gas.
    """
    witness_check_extra = WitnessCheck(fork=Verkle)
    if witness_assert_codehash:
        witness_check_extra.add_account_codehash(
            ExampleAddress, Hash(keccak256(ExampleAccount.code))
        )

    _extcodehash(blockchain_test, ExampleAddress, witness_check_extra, gas_limit, fails=True)


def _extcodehash(
    blockchain_test: BlockchainTestFiller,
    target,
    witness_check_extra: WitnessCheck,
    gas_limit=1_000_000,
    warm=False,
    fails=False,
):
    env = Environment(
        fee_recipient="0x2adc25665018aa1fe0e6bc666dac8fc2697ff9ba",
        difficulty=0x20000,
        gas_limit=10000000000,
        number=1,
        timestamp=1000,
    )
    pre = {
        TestAddress: TestAccount,
        TestAddress2: Account(
            code=Op.EXTCODEHASH(target) * (2 if warm else 1) + Op.PUSH0 + Op.SSTORE
        ),
        ExampleAddress: ExampleAccount,
    }

    tx = Transaction(
        ty=0x0,
        chain_id=0x01,
        nonce=0,
        to=TestAddress2,
        gas_limit=gas_limit,
        gas_price=10,
    )

    post = {}
    if not fails:
        post[TestAddress2] = Account(code=pre[TestAddress2].code, storage={0: 0x424242})

    witness_check = witness_check_extra
    for address in [TestAddress, TestAddress2, env.fee_recipient]:
        witness_check.add_account_full(address=address, account=pre.get(address))

    code_chunks = chunkify_code(pre[TestAddress2].code)
    for i, chunk in enumerate(code_chunks, start=0):
        witness_check.add_code_chunk(address=TestAddress2, chunk_number=i, value=chunk)

    if not fails:
        witness_check.add_storage_slot(address=TestAddress2, storage_slot=0, value=None)

    blocks = [
        Block(
            txs=[tx],
            witness_check=witness_check,
        )
    ]

    blockchain_test(
        genesis_environment=env,
        pre=pre,
        post=post,
        blocks=blocks,
    )
