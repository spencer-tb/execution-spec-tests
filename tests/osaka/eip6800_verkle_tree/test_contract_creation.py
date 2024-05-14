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
    Initcode,
    TestAddress,
    Transaction,
    compute_create_address,
)
from ethereum_test_tools.vm.opcode import Opcodes as Op

# TODO: Update reference spec version
REFERENCE_SPEC_GIT_PATH = "EIPS/eip-6800.md"
REFERENCE_SPEC_VERSION = "2f8299df31bb8173618901a03a8366a3183479b0"


# @pytest.mark.valid_from("Osaka")
# TODO: Update to t8n/geth to use Osaka first
@pytest.mark.valid_from("Prague")
@pytest.mark.parametrize(
    "bytecode",
    [
        "",
        Op.STOP * 1024,
    ],
    ids=["empty", "non_empty"],
)
@pytest.mark.parametrize(
    "value",
    [0, 1],
    ids=["zero", "non_zero"],
)
def test_contract_creation(
    blockchain_test: BlockchainTestFiller,
    fork: str,
    value: int,
    bytecode: str,
):
    """
    Test that contract creation works as expected.
    """
    env = Environment(
        fee_recipient="0x2adc25665018aa1fe0e6bc666dac8fc2697ff9ba",
        difficulty=0x20000,
        gas_limit=10000000000,
        number=1,
        timestamp=1000,
        verkle_conversion_ended=True,  # Should be okay to remove this I think?
    )

    # Using alloc format for pre, as the framework can handle the conversion.
    # This pre mpt alloc, will be converted to the verkle tree format, using the geth
    # `evm verkle tree-keys` command, and the verkle tree input will be used for the pre state.
    pre = {
        TestAddress: Account(balance=1000000000000000000000),
    }

    # Using blocks for now as verkle is currently only supported using blockchain test in the
    # framework. Can swap back to state test once verkle is supported there.
    tx = Transaction(
        ty=0x0,
        chain_id=0x01,
        nonce=0,
        to=Address(""),
        gas_limit=100000000,
        gas_price=10,
        value=value,
        data=Initcode(deploy_code=bytecode),
    )
    blocks = [Block(txs=[tx])]

    contract_address = compute_create_address(TestAddress, tx.nonce)

    # Keeping the following code below for visibility, from previous changes.
    # code_chunks = vkt_chunkify(bytecode)
    # post = {}
    # post[vkt_key_header(contract_address, AccountHeaderEntry.VERSION)] = 0
    # post[vkt_key_header(contract_address, AccountHeaderEntry.BALANCE)] = value
    # post[vkt_key_header(contract_address, AccountHeaderEntry.CODE_HASH)] = keccak256(bytecode)
    # post[vkt_key_header(contract_address, AccountHeaderEntry.CODE_SIZE)] = len(bytecode)
    # for i, chunk in enumerate(code_chunks):
    # post[vkt_key_code_chunk(contract_address, i)] = chunk

    # Using alloc format for post, as the framework can handle the conversion.
    # This post mpt alloc, will be converted to the verkle tree format, using the geth
    # `evm verkle tree-keys` command. This converted verkle tree will be compared with the
    # final output verkle tree from t8n.
    post = {
        contract_address: Account(
            balance=value,
            code=bytecode,
        ),
    }

    blockchain_test(
        genesis_environment=env,
        pre=pre,
        post=post,
        blocks=blocks,
    )
