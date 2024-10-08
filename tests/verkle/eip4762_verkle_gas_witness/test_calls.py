"""
abstract: Tests [EIP-4762: Statelessness gas cost changes]
(https://eips.ethereum.org/EIPS/eip-4762)
    Tests for [EIP-4762: Statelessness gas cost changes]
    (https://eips.ethereum.org/EIPS/eip-4762).
"""

import pytest

from ethereum_test_forks import Verkle
from ethereum_test_forks import Fork
from ethereum_test_tools import (
    Account,
    Address,
    Alloc,
    Block,
    BlockchainTestFiller,
    Bytecode,
    Environment,
    TestAddress,
    TestAddress2,
    Transaction,
    WitnessCheck,
)
from ethereum_test_tools.vm.opcode import Opcodes as Op
from ethereum_test_types.verkle.helpers import chunkify_code

REFERENCE_SPEC_GIT_PATH = "EIPS/eip-4762.md"
REFERENCE_SPEC_VERSION = "2f8299df31bb8173618901a03a8366a3183479b0"

caller_address = Address("0xd94f5374fce5edbc8e2a8697c15331677e6ebf0c")
system_contract_address = Address("0xfffffffffffffffffffffffffffffffffffffffe")
precompile_address = Address("0x04")


@pytest.mark.valid_from("Verkle")
@pytest.mark.parametrize(
    "call_instruction, value",
    [
        (Op.CALL, 0),
        (Op.CALL, 1),
        (Op.CALLCODE, 0),
        (Op.CALLCODE, 1),
        (Op.DELEGATECALL, 0),
        (Op.DELEGATECALL, 1),
        (Op.STATICCALL, 0),
    ],
)
@pytest.mark.parametrize(
    "target",
    [
        TestAddress2,
        precompile_address,
        system_contract_address,
    ],
)
def test_calls(
    blockchain_test: BlockchainTestFiller,
    fork: Fork,
    call_instruction: Bytecode,
    target: Address,
    value,
):
    """
    Test *CALL instructions gas and witness.
    """
    _generic_call(blockchain_test, fork, call_instruction, target, value)


@pytest.mark.valid_from("Verkle")
@pytest.mark.parametrize(
    "call_instruction",
    [
        Op.CALL,
        Op.CALLCODE,
        Op.DELEGATECALL,
        Op.STATICCALL,
    ],
)
def test_calls_warm(blockchain_test: BlockchainTestFiller, fork: Fork, call_instruction: Bytecode):
    """
    Test *CALL warm cost.
    """
    _generic_call(blockchain_test, fork, call_instruction, TestAddress2, 0, warm=True)


@pytest.mark.valid_from("Verkle")
@pytest.mark.skip("Pending TBD gas limits")
@pytest.mark.parametrize(
    "call_instruction, gas_limit",
    [
        (Op.CALL, "TBD_insufficient_dynamic_cost"),
        (Op.CALL, "TBD_insufficient_value_bearing"),
        (Op.CALL, "TBD_insufficient_63/64"),
        (Op.CALLCODE, "TBD_insufficient_dynamic_cost"),
        (Op.CALLCODE, "TBD_insufficient_value_bearing"),
        (Op.CALLCODE, "TBD_insufficient_63/64"),
        (Op.DELEGATECALL, "TBD_insufficient_dynamic_cost"),
        (Op.DELEGATECALL, "TBD_insufficient_63/64"),
        (Op.STATICCALL, "TBD_insufficient_dynamic_cost"),
        (Op.STATICCALL, "TBD_insufficient_63/64"),
    ],
    ids=[
        "CALL_insufficient_dynamic_cost",
        "CALL_insufficient_value_bearing",
        "CALL_insufficient_minimum_63/64",
        "CALLCODE_insufficient_dynamic_cost",
        "CALLCODE_insufficient_value_bearing",
        "CALLCODE_insufficient_minimum_63/64",
        "DELEGATECALL_insufficient_dynamic_cost",
        "DELEGATECALL_insufficient_minimum_63/64",
        "STATICCALL_insufficient_dynamic_cost",
        "STATICCALL_insufficient_minimum_63/64",
    ],
)
def test_calls_insufficient_gas(
    blockchain_test: BlockchainTestFiller, fork: Fork, call_instruction: Bytecode, gas_limit
):
    """
    Test *CALL witness assertion when there's insufficient gas for different scenarios.
    """
    _generic_call(
        blockchain_test,
        fork,
        call_instruction,
        TestAddress2,
        0,
        gas_limit=gas_limit,
        enough_gas_read_witness=False,
    )


def _generic_call(
    blockchain_test: BlockchainTestFiller,
    fork: Fork,
    call_instruction,
    target: Address,
    value,
    gas_limit: int = 100000000,
    enough_gas_read_witness: bool = True,
    warm=False,
):
    env = Environment(
        fee_recipient="0x2adc25665018aa1fe0e6bc666dac8fc2697ff9ba",
        difficulty=0x20000,
        gas_limit=10000000000,
        number=1,
        timestamp=1000,
    )

    if call_instruction == Op.CALL or call_instruction == Op.CALLCODE:
        tx_value = 0
        caller_code = call_instruction(1_000, target, value, 0, 0, 0, 32)
    if call_instruction == Op.DELEGATECALL or call_instruction == Op.STATICCALL:
        tx_value = value
        caller_code = call_instruction(1_000, target, 0, 0, 0, 32)

    pre = {
        TestAddress: Account(balance=1000000000000000000000),
        TestAddress2: Account(code=Op.ADD(1, 2)),
        caller_address: Account(
            balance=2000000000000000000000, code=caller_code * (2 if warm else 1)
        ),
        precompile_address: Account(balance=3000000000000000000000),
    }

    tx = Transaction(
        ty=0x0,
        chain_id=0x01,
        nonce=0,
        to=caller_address,
        gas_limit=gas_limit,
        gas_price=10,
        value=tx_value,
    )
    target_account = (
        pre[target]
        if target != system_contract_address
        else Account(**fork.pre_allocation_blockchain()[system_contract_address])
    )
    witness_check = WitnessCheck(fork=Verkle)
    for address in [TestAddress, caller_address, env.fee_recipient]:
        witness_check.add_account_full(address=address, account=pre.get(address))
    if enough_gas_read_witness:
        if value > 0 or (target != precompile_address and target != precompile_address):
            witness_check.add_account_basic_data(address=target, account=target_account)

    code_chunks = chunkify_code(pre[caller_address].code)
    for i, chunk in enumerate(code_chunks, start=0):
        witness_check.add_code_chunk(address=caller_address, chunk_number=i, value=chunk)
    if target != precompile_address:
        code_chunks = chunkify_code(target_account.code)
        for i, chunk in enumerate(code_chunks, start=0):
            witness_check.add_code_chunk(address=target, chunk_number=i, value=chunk)

    if target == system_contract_address:
        # If the target is the 2935 system contract, we should check for the first storage-slot.
        # The account storage address depends on the kind of *CALL done.
        sslot_target = system_contract_address if call_instruction == Op.CALL else caller_address
        witness_check.add_storage_slot(address=sslot_target, storage_slot=0, value=None)

    blocks = [
        Block(
            txs=[tx],
            witness_check=witness_check,
        )
    ]

    if call_instruction == Op.DELEGATECALL:
        post = {
            caller_address: Account(
                balance=pre[caller_address].balance + value, code=pre[caller_address].code
            ),
            target: target_account,
        }
    else:
        post = {
            target: Account(balance=target_account.balance + value, code=target_account.code),
        }

    blockchain_test(
        genesis_environment=env,
        pre=pre,
        post=post,
        blocks=blocks,
    )


@pytest.mark.valid_from("Verkle")
@pytest.mark.parametrize(
    "call_instruction, gas_limit, enough_gas_account_creation",
    [
        (Op.CALL, 100000000, True),
        (Op.CALL, 21_042, False),
        (Op.CALLCODE, 100000000, True),
        (Op.CALLCODE, 21_042, False),
    ],
)
def test_call_non_existent_account(
    blockchain_test: BlockchainTestFiller,
    call_instruction,
    gas_limit: int,
    enough_gas_account_creation: bool,
):
    """
    Test *CALL witness assertion when target account does not exist.
    """
    env = Environment(
        fee_recipient="0x2adc25665018aa1fe0e6bc666dac8fc2697ff9ba",
        difficulty=0x20000,
        gas_limit=10000000000,
        number=1,
        timestamp=1000,
    )

    call_value = 100

    pre = {
        TestAddress: Account(balance=1000000000000000000000),
        caller_address: Account(
            balance=2000000000000000000000,
            code=call_instruction(1_000, TestAddress2, call_value, 0, 0, 0, 32),
        ),
    }

    tx = Transaction(
        ty=0x0,
        chain_id=0x01,
        nonce=0,
        to=caller_address,
        gas_limit=gas_limit,
        gas_price=10,
    )

    witness_check = WitnessCheck(fork=Verkle)
    for address in [TestAddress, caller_address, env.fee_recipient]:
        witness_check.add_account_full(address=address, account=pre.get(address))

    code_chunks = chunkify_code(pre[caller_address].code)
    for i, chunk in enumerate(code_chunks, start=0):
        witness_check.add_code_chunk(address=caller_address, chunk_number=i, value=chunk)

    if enough_gas_account_creation:
        witness_check.add_account_full(address=TestAddress2, account=None)

    blocks = [
        Block(
            txs=[tx],
            witness_check=witness_check,
        )
    ]

    post: Alloc = Alloc()
    if enough_gas_account_creation:
        post = Alloc({TestAddress2: Account(balance=call_value)})

    blockchain_test(
        genesis_environment=env,
        pre=pre,
        post=post,
        blocks=blocks,
    )
