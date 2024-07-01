"""
A hive based simulator that executes blocks against clients using the `engine_newPayloadVX` method
from the Engine API. The simulator uses the `BlockchainEngineFixtures` to test against clients.

Each `engine_newPayloadVX` is verified against the appropriate VALID/INVALID responses.
"""

from ethereum_test_fixtures import BlockchainHiveFixture
from ethereum_test_fixtures.blockchain import FixtureHeader
from ethereum_test_tools.rpc import EngineRPC, EthRPC
from ethereum_test_tools.rpc.types import ForkchoiceState, PayloadStatusEnum
from pytest_plugins.consume.hive_simulators.exceptions import GenesisBlockMismatchException


def test_via_engine(
    eth_rpc: EthRPC,
    engine_rpc: EngineRPC,
    blockchain_fixture: BlockchainHiveFixture,
):
    """
    1) Checks that the genesis block hash of the client matches that of the fixture.
    2) Executes the test case fixture blocks against the client under test using the
    `engine_newPayloadVX` method from the Engine API, verifying the appropriate
    VALID/INVALID responses.
    3) Performs a forkchoice update to finalize the chain and verify the post state.
    4) Checks that the post state of the client matches that of the fixture.
    """
    genesis_block = eth_rpc.get_block_by_number(0)
    if genesis_block["hash"] != str(blockchain_fixture.genesis.block_hash):
        raise GenesisBlockMismatchException(
            expected_header=blockchain_fixture.genesis, got_header=FixtureHeader(**genesis_block)
        )

    for payload in blockchain_fixture.payloads:
        payload_response = engine_rpc.new_payload(
            *payload.args(),
            version=payload.version,
        )
        assert payload_response.status == (
            PayloadStatusEnum.VALID if payload.valid() else PayloadStatusEnum.INVALID
        ), f"unexpected status: {payload_response}"

    forkchoice_response = engine_rpc.forkchoice_updated(
        forkchoice_state=ForkchoiceState(head_block_hash=blockchain_fixture.last_block_hash),
        payload_attributes=None,
        version=blockchain_fixture.fcu_version,
    )
    assert (
        forkchoice_response.payload_status.status == PayloadStatusEnum.VALID
    ), f"unexpected status: {forkchoice_response}"
