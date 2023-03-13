from typing import Dict, Set, Type
from uuid import uuid4, UUID
from datetime import date, datetime


class Client:
    def __init__(self, bank: "Bank", name: str, surname: str, passport: str | None = None, address: str | None = None):
        self.bank = bank
        self.name = name
        self.surname = surname
        self.passport = passport
        self.address = address
        self.accounts: Dict[UUID, "Account"] = {}

    def create_account(self, account_type: Type["Account"], **kwargs) -> "Account":
        account = account_type(self, **kwargs)
        self.accounts[account.id] = account
        self.bank.accounts[account.id] = account
        return account

    def check_priveleges(self, subtraction_amount: int = 0) -> bool:
        if self.passport is not None and self.address is not None:
            return True
        else:
            return subtraction_amount <= self.bank.unathorized_withdrawal_limit


class Account:
    def __init__(self, client: "Client"):
        self.id = uuid4()
        self.client = client
        self.balance = 0

    def add(self, amount: int) -> None:
        self.balance += amount

    def subtract(self, amount: int) -> None:
        NotImplemented


class DebitAccount(Account):
    def subtract(self, amount: int) -> None:
        if self.balance >= amount:
            self.balance -= amount
        else:
            raise ValueError("Not enough money")

class DepositAccount(Account):
    def __init__(self, client: "Client", end_date: date):
        super().__init__(client)
        self.end_date = end_date

    def subtract(self, amount: int) -> None:
        if date.today() < self.end_date:
            raise ValueError("Can't withdraw money before end date")
        if self.balance < amount:
            raise ValueError("Not enough money")
        else:
            self.balance -= amount

class CreditAccount(Account):
    def __init__(self, client: "Client", credit_limit: int, interest_rate: float):
        super().__init__(client)
        self.credit_limit = credit_limit
        self.interest_rate = interest_rate

    def subtract(self, amount: int) -> None:
        if self.balance - amount < -self.credit_limit:
            raise ValueError("Not enough money")
        else:
            self.balance -= amount

class CashAccount(Account):
    """Счёт - черная дыра. Служебный. 
    Является полем 'From' в операции внесения наличных и полем 'To' в операции снятия наличных."""
    def add(self, amount: int) -> None:
        pass
    def subtract(self, amount: int) -> None:
        pass


class Transaction:
    def __init__(self, From: "Account", To: "Account", amount: int):
        self.From = From
        self.To = To
        self.amount = amount
        self.datetime = None

    def perform(self) -> "Transaction":
        if not self.From.client.check_priveleges(self.amount):
            raise ValueError("Not enough priveleges")
        else:
            self.From.subtract(self.amount)
            self.To.add(self.amount)
            self.datetime = datetime.now()

            self.From.client.bank.transaction_list.append(self)
            self.To.client.bank.transaction_list.append(self)
            return self

    def __hash__(self) -> int:
        return hash((self.From.id, self.To.id, self.amount, self.datetime))

    def cancel(self) -> None:
        """Безусловно отменяет транзакцию.
        У бывшего получателя, например, может оказаться отрицательный баланс.
        Записывает отменяющую транзакцию в списки транзакций."""
        self.From.balance += self.amount
        self.To.balance -= self.amount

        cancel_transaction = Transaction(self.To, self.From, self.amount)
        cancel_transaction.datetime = datetime.now()
        self.From.client.bank.transaction_list.append(cancel_transaction)
        self.To.client.bank.transaction_list.append(cancel_transaction)


class TransactionList:
    """Класс для хранения транзакций, играющий роль БД.
    Есть у каждого банка.

    Возможно, в будущем будет заменен на настоящую БД. 
    Остальные классы менять при этом не придётся."""

    def __init__(self):
        self.transactions: Set[Transaction] = set()

    def append(self, transaction: Transaction) -> None:
        """Добавляет транзакцию в список транзакций.
        Если транзакция уже есть в списке, ничего не делает."""
        self.transactions.add(transaction)


class Bank:
    def __init__(self, unathorized_withdrawal_limit: int = 0) -> None:
        self.accounts: Dict[UUID, "Account"] = {}
        self.transaction_list = TransactionList()
        self.unathorized_withdrawal_limit = unathorized_withdrawal_limit