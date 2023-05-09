# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-module-docstring

# pylint: disable=redefined-outer-name
# pylint: disable=wildcard-import
# pylint: disable=unused-wildcard-import
# pylint: disable=wrong-import-position

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import timedelta
import pytest
from src.core import *

class TestBoolWithReason:
    true1 = BoolWithReason()
    true2 = BoolWithReason()
    false1 = BoolWithReason('reason1\n')
    false2 = BoolWithReason('reason2\n')

    def test_bool(self):
        assert self.true1
        assert not self.false1

    def test_repr(self):
        assert repr(self.true1) == 'Success'
        assert repr(self.false1) == "Error: reason1\n"

    def test_and_as_bool(self):
        assert self.true1 & self.true2
        assert not self.true1 & self.false1
        assert not self.false1 & self.true1
        assert not self.false1 & self.false2

    def test_and_as_str(self):
        assert (self.true1 & self.true2).reason == ''
        assert (self.true1 & self.false1).reason == 'reason1\n'
        assert (self.false1 & self.true1).reason == 'reason1\n'
        assert (self.false1 & self.false2).reason == 'reason1\nreason2\n'


@pytest.fixture
def bank():
    return Bank(unathorized_withdrawal_limit=1000)


@pytest.fixture
def client(bank: Bank):
    return Client(bank, 'Иван', 'Иванов', '0123 456789', 'Москва')



class TestClient:
    def test_create_account(self, client: Client, bank: Bank):
        accounts = [
            client.default_cash_account,
            client.create_account(DebitAccount),
            client.create_account(DepositAccount, end_date = datetime(2021, 1, 1)),
            client.create_account(CreditAccount, credit_limit = 1000, interest_rate = 0.1),
            client.create_account(CashAccount)
        ]
        for account in accounts:
            assert account in client.accounts.values()
            assert account in bank.accounts.values()

            assert account.client == client
            assert account.balance == 0


class TestAccount:
    def test_info(self, client: Client):
        account = client.default_cash_account
        info = account.info()
        assert isinstance(info['id'], UUID)
        assert info['balance'] == 0
        assert info['type'] == 'CashAccount'


class TestDebitAccount:
    def check_withdraw_permissions(self, client: Client):
        To = client.default_cash_account

        From = client.create_account(DebitAccount)

        transaction = Transaction(From, To, 1000)
        assert not transaction.check_permissions(), 'Нельзя снимать деньги с пустого счета'

        From.balance = 1000
        assert transaction.check_permissions()

        client.passport = None
        assert transaction.check_permissions(), \
            'Можно снимать деньги без паспорта в пределах лимита'

        transaction.amount = 1001
        assert not transaction.check_permissions(), \
            'Нельзя снимать деньги без паспорта, превышающие лимит'

        transaction = Transaction(To, From, 1001)
        assert transaction.check_permissions(), 'Можно вносить деньги без паспорта'


class TestDepositAccount:
    def test_check_permissions(self, client: Client):
        To = client.default_cash_account

        today = datetime.now().date()

        From = client.create_account(DepositAccount, end_date = today)
        From.balance = 1000

        transaction = Transaction(From, To, 1000)
        assert transaction.check_permissions(), 'Можно снимать с депозитного после даты окончания'

        From.end_date = today + timedelta(days = 1) # type: ignore
        assert not transaction.check_permissions(), 'Нельзя снимать до даты окончания'


class TestCreditAccount:
    def test_check_permissions(self, client: Client):
        To = client.default_cash_account
        client.address = None

        From = client.create_account(CreditAccount, credit_limit = 1000, interest_rate = 0.1)

        transaction = Transaction(From, To, 1000)
        assert transaction.check_permissions(), 'Можно уходить в минус вплоть до предела'

        From.balance = -1
        assert not transaction.check_permissions(), 'Нельзя уходить в минус больше предела'


class TestCashAccount:
    def test_check_permissions(self, client: Client):
        client.passport = None
        client.address = None

        From = client.default_cash_account

        To = client.create_account(DepositAccount, end_date = datetime(9999, 1, 1))

        transaction = Transaction(From, To, 10000)
        assert transaction.check_permissions(), 'Можно вносить деньги без ограничений'



@pytest.fixture
def transaction(client: Client):
    To = client.create_account(DepositAccount, end_date = date(9999, 1, 1))
    To.balance = 10_000
    From = client.create_account(DebitAccount)
    From.balance = 10_000

    return Transaction(From, To, 1000)

class TestTransaction:
    def test_perform_valid_transaction(self, transaction: Transaction):
        assert transaction.perform()
        assert transaction.From.balance == 9000
        assert transaction.To.balance == 11_000

    def test_perform_invalid_transaction(self, transaction: Transaction):
        transaction.amount = 11_000
        assert not transaction.perform(), \
            'Невозможная транзакция должна возвращать непустой BoolWithReason'
        assert transaction.From.balance == 10_000, \
            'Непроведенная транзакция не должна изменять баланс счёта From'
        assert transaction.To.balance == 10_000, \
            'Непроведенная транзакция не должна изменять баланс счёта To'

    def test_mirror(self, transaction: Transaction):
        """Тестирует, что зеркальная транзакция делает то же, что и обычная"""
        assert transaction != transaction.mirror
        assert transaction.mirror.perform()
        assert transaction.From.balance == 9000
        assert transaction.To.balance == 11_000

        transaction.amount = 11_000
        assert not transaction.mirror.perform()

    def test_cancel(self, transaction: Transaction):
        transaction.perform()
        assert transaction.cancel()
        assert transaction.From.balance == 10_000
        assert transaction.To.balance == 10_000

    def test_hash(self, transaction: Transaction):
        assert hash(transaction) == hash(transaction.mirror)

    def test_lt(self, transaction: Transaction):
        transaction2 = Transaction(transaction.From, transaction.To, transaction.amount)
        transaction2.datetime = transaction.datetime + timedelta(seconds = 1)
        assert transaction < transaction2

class TestTransactionsHistory:
    def test_save(self, transaction: Transaction):
        transaction.perform()
        assert transaction.From.history[transaction.id] == transaction.mirror
        assert transaction.To.history[transaction.id] == transaction

    def test_multiple_save(self, transaction: Transaction):
        history = transaction.From.history
        history.save(transaction)
        history.save(transaction)
        history.save(transaction.mirror)
        assert len(history.see()) == 1



@pytest.fixture
def client_facade(client: Client):
    return ClientFacade(client)

class TestClientFacade:
    def test_create_account(self, client_facade: ClientFacade):

        with pytest.raises(ValueError):
            account = client_facade.create_account('SuperAccount')

        account = client_facade.create_account(
            'CreditAccount', credit_limit = 1000, interest_rate = 0.1)

        assert account in client_facade.client.accounts.values()

    def test_withdraw(self, client_facade: ClientFacade):

        account = client_facade.create_account('DebitAccount')
        assert not client_facade.withdraw(account.id, 1000)
        assert account.balance == 0

        account.balance = 1000
        assert client_facade.withdraw(account.id, 1000)
        assert account.balance == 0

    def test_deposit(self, client_facade: ClientFacade):
        account = client_facade.create_account('DebitAccount')
        assert client_facade.deposit(account.id, 1000)
        assert account.balance == 1000

    def test_transfer(self, client_facade: ClientFacade):
        account1 = client_facade.create_account('DebitAccount')
        account2 = client_facade.create_account('DebitAccount')
        account1.balance = 1000

        assert client_facade.transfer(account1.id, account2.id, 1000)
        assert account1.balance == 0
        assert account2.balance == 1000

    def test_transfer_another_bank(self, client_facade: ClientFacade):
        account1 = client_facade.create_account('DebitAccount')
        account1.balance = 1000

        client_facade2 = ClientFacade(Client(Bank(), 'Альберт', 'Эйнштейн'))
        account2 = client_facade2.create_account('DebitAccount')

        assert not client_facade.transfer(account1.id, account2.id, 1000), 'Банк не найден'

        assert client_facade.transfer(account1.id, account2.id, 1000, client_facade2.client.bank)
        assert account1.balance == 0
        assert account2.balance == 1000
