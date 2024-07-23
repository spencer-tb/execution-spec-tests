"""
Pre-allocation fixtures using for test filling.
"""

from itertools import count
from random import randint
from typing import Dict, Iterator, List, Tuple

import pytest
from pydantic import PrivateAttr

from ethereum_test_base_types import Number, ZeroPaddedHexNumber
from ethereum_test_base_types.composite_types import StorageKeyValueTypeConvertible
from ethereum_test_base_types.conversions import BytesConvertible, NumberConvertible
from ethereum_test_tools import EOA, Account, Address
from ethereum_test_tools import Alloc as BaseAlloc
from ethereum_test_tools import Bytecode, Initcode
from ethereum_test_tools import Opcodes as Op
from ethereum_test_tools import Storage, Transaction
from ethereum_test_tools.rpc import EthRPC
from ethereum_test_tools.rpc.types import TransactionByHashResponse

from .senders import Senders


def pytest_addoption(parser):
    """
    Adds command-line options to pytest.
    """
    alloc_group = parser.getgroup("alloc", "Arguments defining allocation characteristics")
    alloc_group.addoption(
        "--eoa-start",
        action="store",
        dest="eoa_iterator_start",
        default=randint(0, 2**256),
        type=int,
        help="The start private key from which tests will deploy EOAs.",
    )


@pytest.hookimpl(trylast=True)
def pytest_report_header(config):
    """A pytest hook called to obtain the report header."""
    bold = "\033[1m"
    reset = "\033[39;49m"
    eoa_start = config.getoption("eoa_iterator_start")
    header = [
        (bold + f"Start seed for EOA: {eoa_start} " + reset),
    ]
    return header


@pytest.fixture(scope="session")
def eoa_iterator(request) -> Iterator[EOA]:
    """
    Returns an iterator that generates EOAs.
    """
    eoa_start = request.config.getoption("eoa_iterator_start")
    print(f"Starting EOA index: {eoa_start}")
    return iter(EOA(key=i, nonce=0) for i in count(start=eoa_start))


class Alloc(BaseAlloc):
    """
    A custom class that inherits from the original Alloc class.
    """

    _senders: Senders = PrivateAttr(...)
    _eth_rpc: EthRPC = PrivateAttr(...)
    _txs: List[Transaction] = PrivateAttr(default_factory=list)
    _funded_eoa: List[Tuple[EOA, Address]] = PrivateAttr(default_factory=list)

    def __init__(
        self, senders: Senders, eth_rpc: EthRPC, eoa_iterator: Iterator[EOA], *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._senders = senders
        self._eth_rpc = eth_rpc
        self._eoa_iterator = eoa_iterator

    def deploy_contract(
        self,
        code: BytesConvertible,
        *,
        storage: Storage
        | Dict[StorageKeyValueTypeConvertible, StorageKeyValueTypeConvertible] = {},
        balance: NumberConvertible = 0,
        nonce: NumberConvertible = 1,
        address: Address | None = None,
        label: str | None = None,
    ) -> Address:
        """
        Deploy a contract to the allocation.

        Warning: `address` parameter is a temporary solution to allow tests to hard-code the
        contract address. Do NOT use in new tests as it will be removed in the future!
        """
        assert address is None, "address parameter is not supported"

        assert isinstance(code, Bytecode), "code must be a Bytecode instance"

        initcode_prefix = Bytecode()
        if isinstance(storage, Storage):
            if len(storage.root) > 0:
                for key, value in storage.root.items():
                    initcode_prefix += Op.SSTORE(int(key), int(value))
        else:
            if len(storage) > 0:
                for key, value in storage.items():  # type: ignore
                    initcode_prefix += Op.SSTORE(key, value)
        initcode = Initcode(deploy_code=code, initcode_prefix=initcode_prefix)

        with self._senders.get_sender() as sender:
            deploy_tx = Transaction(
                sender=sender,
                to=None,
                data=initcode,
                value=balance,
                gas_limit=1_000_000,  # TODO: we need to better estimate the gas limit
            ).with_signature_and_sender()
        self._eth_rpc.send_transaction(deploy_tx)
        self._txs.append(deploy_tx)

        contract_address = deploy_tx.created_contract

        assert Number(nonce) >= 1, "impossible to deploy contract with nonce lower than one"

        self[contract_address] = Account(
            nonce=nonce,
            balance=balance,
            code=code,
            storage=storage,
        )

        contract_address.label = label
        return contract_address

    def fund_eoa(self, amount: NumberConvertible | None = None, label: str | None = None) -> EOA:
        """
        Add a previously unused EOA to the pre-alloc with the balance specified by `amount`.
        """
        eoa = next(self._eoa_iterator)
        # Send a transaction to fund the EOA
        if amount is None:
            amount = self.eoa_fund_amount_default
        with self._senders.get_sender() as sender:
            sender_address = Address(sender)
            fund_tx = Transaction(
                sender=sender,
                to=eoa,
                value=amount,
            ).with_signature_and_sender()
        self._eth_rpc.send_transaction(fund_tx)
        self._txs.append(fund_tx)
        self[eoa] = Account(
            nonce=0,
            balance=amount,
        )
        self._funded_eoa.append((eoa, sender_address))
        return eoa

    def fund_address(self, address: Address, amount: NumberConvertible):
        """
        Fund an address with a given amount.

        If the address is already present in the pre-alloc the amount will be
        added to its existing balance.
        """
        with self._senders.get_sender() as sender:
            fund_tx = Transaction(
                sender=sender,
                to=address,
                value=amount,
            ).with_signature_and_sender()
        self._eth_rpc.send_transaction(fund_tx)
        self._txs.append(fund_tx)
        if address in self:
            account = self[address]
            if account is not None:
                current_balance = account.balance or 0
                account.balance = ZeroPaddedHexNumber(current_balance + Number(amount))
                return

        self[address] = Account(balance=amount)

    def wait_for_transactions(self) -> List[TransactionByHashResponse]:
        """
        Wait for all transactions to be included in blocks.
        """
        return self._eth_rpc.wait_for_transactions(self._txs)


@pytest.fixture(autouse=True, scope="function")
def pre(
    # request,
    sender_keys: Senders,
    eoa_iterator: Iterator[EOA],
    eth_rpc: EthRPC,
) -> Alloc:
    """
    Returns the default pre allocation for all tests (Empty alloc).
    """
    return Alloc(sender_keys, eth_rpc, eoa_iterator)