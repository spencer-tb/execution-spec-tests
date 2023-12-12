"""
A hive simulator that executes blocks against clients using the
`engine_newPayloadVX` method from the Engine API, verifying
the appropriate VALID/INVALID responses.

Implemented using the pytest framework as a pytest plugin.
"""
import io
import json
from typing import Dict, List, Mapping, Optional

import pytest
from hexbytes import HexBytes
from hive.client import Client, ClientType
from hive.testing import HiveTest

# TODO: Remove when we convert json fixture dict to correct types defined
# forks used within `engine_new_payload()` at `fork = globals()[test_case_fixture.fork]`
# to use the fork class from the String
from ethereum_test_forks import Berlin, Cancun, Frontier, London, Merge, Shanghai  # noqa: F401
from ethereum_test_tools.common import to_hash
from ethereum_test_tools.common.types import Account, Address, Fixture, Hash, Transaction
from ethereum_test_tools.rpc import EngineRPC, EthRPC
from pytest_plugins.consume.consume import TestCase
from pytest_plugins.consume_via_engine_api.client_fork_ruleset import client_fork_ruleset


@pytest.fixture(scope="session")
def test_suite_name() -> str:
    """
    The name of the hive test suite used in this simulator.
    """
    return "EEST Consume Blocks via Engine API"


@pytest.fixture(scope="session")
def test_suite_description() -> str:
    """
    The description of the hive test suite used in this simulator.
    """
    return "Execute blockchain tests by against clients using the `engine_newPayloadVX` method."


@pytest.fixture(scope="function")
def test_case_fixture(test_case: TestCase) -> Fixture:
    """
    The test fixture as a dictionary. If we failed to parse a test case fixture,
    it's None: We xfail/skip the test.
    """
    assert test_case.fixture is not None
    return test_case.fixture


@pytest.fixture(scope="function")
def buffered_genesis(test_case: TestCase) -> Dict[str, io.BufferedReader]:
    """
    Convert the genesis block header of the current test fixture to a buffered reader
    readable by the client under test within hive.
    """
    # Extract genesis and pre-alloc from test case fixture
    genesis = test_case.fixture.genesis
    pre_alloc = test_case.json_as_dict["pre"]
    client_genesis = {
        "nonce": genesis["nonce"],
        "timestamp": genesis["timestamp"],
        "extraData": genesis["extraData"],
        "gasLimit": genesis["gasLimit"],
        "difficulty": genesis["difficulty"],
        "mixhash": genesis["mixHash"],
        "coinbase": genesis["coinbase"],
        "alloc": pre_alloc,
    }
    for field in ["baseFeePerGas", "withdrawalsRoot", "blobFeePerGas", "blobGasUsed"]:
        if field in genesis:
            client_genesis[field] = genesis[field]

    # Convert client genesis to BufferedReader
    genesis_json = json.dumps(client_genesis)
    genesis_bytes = genesis_json.encode("utf-8")
    return io.BufferedReader(io.BytesIO(genesis_bytes))


@pytest.fixture(scope="function")
def client_files(
    client_type: ClientType, buffered_genesis: io.BufferedReader
) -> Mapping[str, io.BufferedReader]:
    """
    Defines the files that hive will start the client with.
    1) The buffered genesis including the pre-alloc.
    """
    files = {}
    # Client specific genesis format
    if client_type.name == "nethermind":
        files["/chainspec/test.json"] = buffered_genesis
    else:
        files["/genesis.json"] = buffered_genesis
    return files


@pytest.fixture(scope="function")
def client_environment(test_case: TestCase) -> Dict:
    """
    Defines the environment that hive will start the client with
    using the fork rules specific for the simulator.
    """
    client_env = {
        "HIVE_FORK_DAO_VOTE": "1",
        "HIVE_CHAIN_ID": "1",
        "HIVE_NODETYPE": "full",
        **{k: f"{v:d}" for k, v in client_fork_ruleset.get(test_case.fixture.fork, {}).items()},
    }
    return client_env


@pytest.fixture(scope="function")
def client(
    hive_test: HiveTest, client_files: Dict, client_environment: Dict, client_type: ClientType
) -> Client:
    """
    Initializes the client with the appropriate files and environment variables.
    """
    client = hive_test.start_client(
        client_type=client_type, environment=client_environment, files=client_files
    )
    assert client is not None
    yield client
    client.stop()


@pytest.fixture(scope="function")
def engine_rpc(client: Client) -> EngineRPC:
    """
    Initializes the engine RPC for the client under test.
    """
    return EngineRPC(client)


@pytest.fixture(scope="function")
def eth_rpc(client: Client) -> EngineRPC:
    """
    Initializes the eth RPC for the client under test.
    """
    return EthRPC(client)


@pytest.fixture(scope="function")
def fixture_blocks(test_case_fixture: Fixture) -> List[dict]:
    """
    The test case fixture blocks as list of dictionaries.
    """
    return test_case_fixture.blocks


def hex_to_int(hex_str: Optional[str]) -> Optional[int]:
    """
    TODO: remove once we convert json fixture dict to correct types defined
    within ethereum_test_tools.common.types.

    Convert a hexadecimal string to an integer.
    """
    return int(hex_str, 16) if hex_str is not None else None


def serialized_transactions(fixture_block_transactions: dict) -> List[bytes]:
    """
    TODO: update once we convert json fixture dict to correct types defined
    within ethereum_test_tools.common.types. Use the Transaction type directly instead of
    converting it here.

    Convert a list of transactions (dict) from the json fixture to a
    list of serialized rlp Transaction objects.

    Extracts a serialized list of RLP-encoded transactions within a block used within
    the execution payload.
    """
    rlp_txs = []
    for tx_dict in fixture_block_transactions:
        tx = Transaction(
            ty=hex_to_int(tx_dict.get("type")),
            chain_id=hex_to_int(tx_dict.get("chainId", "0x1")),
            nonce=hex_to_int(tx_dict.get("nonce", "0x0")),
            gas_price=hex_to_int(tx_dict.get("gasPrice")),
            max_priority_fee_per_gas=hex_to_int(tx_dict.get("maxPriorityFeePerGas")),
            max_fee_per_gas=hex_to_int(tx_dict.get("maxFeePerGas")),
            gas_limit=hex_to_int(tx_dict.get("gasLimit", "0x5208")),  # Default 21000 in hex
            to=Address(HexBytes(tx_dict.get("to"))) if tx_dict.get("to") else None,
            value=hex_to_int(tx_dict.get("value", "0x0")),
            data=HexBytes(tx_dict.get("data")),
            access_list=tx_dict.get("accessList"),
            max_fee_per_blob_gas=hex_to_int(tx_dict.get("maxFeePerBlobGas")),
            blob_versioned_hashes=[
                Hash(HexBytes(h)) for h in tx_dict.get("blobVersionedHashes", [])
            ],
            v=hex_to_int(tx_dict.get("v")),
            r=hex_to_int(tx_dict.get("r")),
            s=hex_to_int(tx_dict.get("s")),
            wrapped_blob_transaction=tx_dict.get("wrappedBlobTransaction", False),
            blobs=[HexBytes(b) for b in tx_dict.get("blobs", [])],
            blob_kzg_commitments=[HexBytes(c) for c in tx_dict.get("blobKzgCommitments", [])],
            blob_kzg_proofs=[HexBytes(p) for p in tx_dict.get("blobKzgProofs", [])],
            sender=Address(HexBytes(tx_dict.get("sender"))) if tx_dict.get("sender") else None,
            secret_key=Hash(HexBytes(tx_dict.get("secretKey")))
            if tx_dict.get("secretKey")
            else None,
            protected=tx_dict.get("protected", True),
            error=tx_dict.get("error"),
        )
        tx_rlp_bytes = tx.serialized_bytes()
        rlp_txs.append("0x" + tx_rlp_bytes.hex())
    return rlp_txs


def execution_payload(fixture_block: dict) -> dict:
    """
    Extracts the execution payload field for a given block.
    Used within engine new payload.
    """
    block_header = fixture_block["blockHeader"]
    exec_payload = {
        "parentHash": block_header["parentHash"],
        "feeRecipient": block_header["coinbase"],
        "stateRoot": block_header["stateRoot"],
        "receiptsRoot": block_header["receiptTrie"],
        "logsBloom": block_header["bloom"],
        "prevRandao": to_hash(block_header["difficulty"]),
        "blockNumber": hex(int(block_header["number"], 16)),
        "gasLimit": hex(int(block_header["gasLimit"], 16)),
        "gasUsed": hex(int(block_header["gasUsed"], 16)),
        "timestamp": hex(int(block_header["timestamp"], 16)),
        "extraData": block_header["extraData"],
        "baseFeePerGas": hex(int(block_header["baseFeePerGas"], 16)),
        "blockHash": block_header["hash"],
        "transactions": serialized_transactions(fixture_block["transactions"]),
    }
    if "withdrawals" in fixture_block:
        exec_payload["withdrawals"] = fixture_block["withdrawals"]
    for field in ["excessBlobGas", "blobGasUsed"]:
        if field in block_header:
            exec_payload[field] = hex(int(block_header[field], 16))
    return exec_payload


def enp_params(fixture_block: dict, test_case_fixture: Fixture) -> dict:
    """
    Extracts the engine new payload parameters for a given fixture block.
    """
    block_header = fixture_block["blockHeader"]
    # TODO: Remove when we convert json fixture dict to correct types defined
    fork = globals()[test_case_fixture.fork]
    return {
        "executionPayload": execution_payload(fixture_block),
        "blobVersionedHashes": [
            tx["blobVersionedHashes"]
            for tx in fixture_block["transactions"]
            if "blobVersionedHashes" in tx
        ],
        "parentBeaconBlockRoot": block_header["parentBeaconBlockRoot"]
        if "parentBeaconBlockRoot" in block_header
        else None,
        "valid": False if "expectException" in fixture_block else True,
        "version": fork.engine_new_payload_version(
            block_header["number"], block_header["timestamp"]
        ),
    }


@pytest.fixture(scope="function")
def engine_new_payloads(test_case_fixture: Fixture) -> List[dict]:
    """
    The engine new payloads for each block in the test case fixture.
    """
    return [enp_params(block, test_case_fixture) for block in test_case_fixture.blocks]


def verify_account_state_and_storage(eth_rpc, address, account: Account, test_name):
    """
    Verify the account state and storage matches the expected account state and storage.
    """
    # Retrieve nonce and balance from the RPC
    nonce = eth_rpc.get_transaction_count(address)
    balance = eth_rpc.get_balance(address)

    # Check final nonce & balance matches expected in fixture
    if int(account.nonce, 16) != int(nonce, 16):
        raise AssertionError(f"Nonce mismatch for account {address} in test {test_name}")
    if int(account.balance, 16) != int(balance, 16):
        raise AssertionError(f"Balance mismatch for account {address} in test {test_name}")

    # Check final storage
    if len(account.storage) > 0:
        keys = list(account.storage.keys())
        storage = eth_rpc.storage_at_keys(address, keys)
        for key in keys:
            if int(account.storage[key], 16) != int(storage[key], 16):
                raise AssertionError(
                    f"Storage mismatch for account {address}, key {key} in test {test_name}"
                )


def test_via_engine_api(
    engine_rpc: EngineRPC,
    eth_rpc: EthRPC,
    test_case: TestCase,
    engine_new_payloads: List[dict],
):
    """
    Execute the test case fixture blocks against the client under test using the
    `engine_newPayloadVX` method from the Engine API, verifying the appropriate
    VALID/INVALID responses.

    Then perform a forkchoice update to finalize the chain and verify the post state
    against that of the fixture using the eth RPC methods: `eth_getBalance`,
    `eth_getTransactionCount` and `eth_getStorageAt`.
    """
    # Check that the genesis block hash of the client matches that of the fixture.
    genesis_block = eth_rpc.get_block_by_number(0, False)
    assert genesis_block["hash"] == test_case.fixture.genesis["hash"], "genesis hash mismatch"

    # Start sending the engine new payload requests for each block in the fixture.
    for enp_params in engine_new_payloads:
        payload = {
            "execution_payload": enp_params["executionPayload"],
            "version": enp_params["version"],
        }
        if enp_params["blobVersionedHashes"] != []:
            payload["blob_versioned_hashes"] = enp_params["blobVersionedHashes"]
        if enp_params["parentBeaconBlockRoot"] is not None:
            payload["parent_beacon_block_root"] = enp_params["parentBeaconBlockRoot"]

        # Check the response status of the engine new payload request.
        expect_status = "VALID" if enp_params["valid"] else "INVALID"
        response = engine_rpc.new_payload(**payload)
        assert response["status"] == expect_status, "unexpected status"

        # For invalid payloads, check the error code is as expected.
        # TODO: Get the error code from the default fixture format
        if response["status"] == "INVALID":
            assert response["error"] == enp_params["error"], "unexpected error"
            continue

    # Perform a forkchoice update to finalize the chain.
    response = engine_rpc.forkchoice_updated(
        forkchoice_state={"headBlockHash": test_case.fixture.blocks[-1]["blockHeader"]["hash"]},
        payload_attributes=None,
        version=engine_new_payloads[-1]["version"],
    )

    # Check the post state against that of the fixture
    for address, account in test_case.fixture.post_state.items():
        verify_account_state_and_storage(eth_rpc, address.hex(), account, test_case.fixture_name)
