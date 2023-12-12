"""
Ethereum `eth_X` JSON-RPC methods used within EEST based hive simulators.
"""

from typing import Dict, List, Literal, Optional, Union

from ..common import Address, Hash
from .base_rpc import BaseRPC

BlockNumberType = Union[int, Literal["latest", "earliest", "pending"]]


class EthRPC(BaseRPC):
    """
    Represents an `eth_X` RPC class for every default ethereum RPC method used within EEST based
    hive simulators.
    """

    def get_block_by_number(self, block_number: BlockNumberType = "latest", full_txs: bool = True):
        """
        `eth_getBlockByNumber`: Returns information about a block by block number.

        Params:
            1) block_number - integer of a block number, or the string "earliest",
            "latest" or "pending", as in the default block parameter.
            2) full_txs - if true it returns the full transaction objects, if false only
            the hashes of the transactions.
        """
        if isinstance(block_number, int):
            block_number = hex(block_number)

        return self.post_request("eth_getBlockByNumber", [block_number, full_txs])

    def get_balance(self, address: str, block_number: BlockNumberType = "latest"):
        """
        `eth_getBalance`: Returns the balance of the account of given address.

        Params:
            1) address - address to check for balance.
            2) block_number - integer block number, or the string "latest", "earliest" or
            "pending", as in the default block parameter.
        """
        if isinstance(block_number, int):
            block_number = hex(block_number)

        return self.post_request("eth_getBalance", [address, block_number])

    def get_transaction_count(self, address: Address, block_number: BlockNumberType = "latest"):
        """
        `eth_getTransactionCount`: Returns the number of transactions sent from an address.

        Params:
            1) address - address to check for balance.
            2) block_number - integer block number, or the string "latest", "earliest" or
            "pending", as in the default block parameter.
        """
        if isinstance(block_number, int):
            block_number = hex(block_number)

        return self.post_request("eth_getTransactionCount", [address, block_number])

    def get_storage_at(
        self, address: str, position: str, block_number: BlockNumberType = "latest"
    ):
        """
        `eth_getStorageAt`: Returns the value from a storage position at a given address.

        Params:
            1) account - address of account in storage.
            2) position - .
            3) block_number - integer block number, or the string "latest", "earliest" or
            "pending", as in the default block parameter.
        """
        if isinstance(block_number, int):
            block_number = hex(block_number)

        return self.post_request("eth_getStorageAt", [address, position, block_number])

    def storage_at_keys(
        self, account: str, keys: List[str], block_number: Optional[int] = "latest"
    ) -> Dict[Hash, Hash]:
        """
        Helper to retrieves the storage values for the specified keys at a given address and block
        number.

        Params:
            1) account - address of account in storage.
            2) keys - list of storage position keys.
            3) block_number - integer block number, or the string "latest", "earliest" or
            "pending", as in the default block parameter.
        """
        if isinstance(block_number, int):
            block_number = hex(block_number)
        results = {}
        for key in keys:
            storage_value = self.get_storage_at(account, key, block_number)
            results[key] = storage_value
        return results
