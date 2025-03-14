"""
A hive based simulator that executes RLP-encoded blocks against clients. The simulator uses the
`BlockchainFixtures` to test this against clients.

Clients consume the genesis and RLP-encoded blocks from input files upon start-up.
"""

from ethereum_test_fixtures import BlockchainFixture
from ethereum_test_rpc import EthRPC
from pytest_plugins.consume.hive_simulators.exceptions import GenesisBlockMismatchExceptionError

from ..timing import TimingData


def test_via_rlp(
    timing_data: TimingData,
    eth_rpc: EthRPC,
    fixture: BlockchainFixture,
):
    """
    1. Check the client genesis block hash matches `fixture.genesis.block_hash`.
    2. Check the client last block hash matches `fixture.last_block_hash`.
    """
    with timing_data.time("Get genesis block"):
        genesis_block = eth_rpc.get_block_by_number(0)
        if genesis_block["hash"] != str(fixture.genesis.block_hash):
            raise GenesisBlockMismatchExceptionError(
                expected_header=fixture.genesis,
                got_genesis_block=genesis_block,
            )
    with timing_data.time("Get latest block"):
        block = eth_rpc.get_block_by_number("latest")
        assert block["hash"] == str(fixture.last_block_hash), "hash mismatch in last block"
