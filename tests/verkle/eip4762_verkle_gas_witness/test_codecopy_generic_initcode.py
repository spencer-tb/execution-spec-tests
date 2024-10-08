"""
abstract: Tests [EIP-4762: Statelessness gas cost changes]
(https://eips.ethereum.org/EIPS/eip-4762)
    Tests for [EIP-4762: Statelessness gas cost changes]
    (https://eips.ethereum.org/EIPS/eip-4762).
"""

import pytest

from ethereum_test_forks import Verkle
from ethereum_test_tools import (
    Account,
    Block,
    BlockchainTestFiller,
    Environment,
    TestAddress,
    Transaction,
    WitnessCheck,
    compute_create_address,
)
from ethereum_test_tools.vm.opcode import Opcodes as Op

REFERENCE_SPEC_GIT_PATH = "EIPS/eip-4762.md"
REFERENCE_SPEC_VERSION = "2f8299df31bb8173618901a03a8366a3183479b0"


@pytest.mark.valid_from("Verkle")
@pytest.mark.parametrize(
    "instruction",
    [
        Op.CODECOPY,
        Op.EXTCODECOPY,
    ],
)
def test_generic_codecopy_initcode(blockchain_test: BlockchainTestFiller, fork: str, instruction):
    """
    Test *CODECOPY in initcode targeting itself.
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

    contract_address = compute_create_address(address=TestAddress, nonce=0)
    if instruction == Op.EXTCODECOPY:
        data = Op.EXTCODECOPY(contract_address, 0, 0, 100) + Op.ORIGIN * 100
    else:
        data = Op.CODECOPY(0, 0, 100) + Op.ORIGIN * 100

    tx = Transaction(
        ty=0x0,
        chain_id=0x01,
        nonce=0,
        to=None,
        gas_limit=1_000_000,
        gas_price=10,
        data=data,
    )

    witness_check = WitnessCheck(fork=Verkle)
    for address in [TestAddress, contract_address, env.fee_recipient]:
        witness_check.add_account_full(address=address, account=pre.get(address))

    blocks = [
        Block(
            txs=[tx],
            witness_check=witness_check,
        )
    ]

    blockchain_test(
        genesis_environment=env,
        pre=pre,
        post={},
        blocks=blocks,
    )
