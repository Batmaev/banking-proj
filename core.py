"""Модуль с основными классами банка."""

from typing import Dict, Set, Type
from uuid import uuid4, UUID
from datetime import date, datetime


class BoolWithReason:
    """Класс для результатов каких-либо проверок.

    Представляет собой обёртку над строкой.
    В строке записывается причина, по которой проверка не прошла.
    Если строка пустая, то это значит, что проверка прошла успешно.
    bool(BoolWithReason) возвращает True, если строка пустая, и False, если нет.

    Позволяет объединять результаты проверок с помощью оператора &
    и вызывать исключение с помощью метода raise_if_false().

    Этот класс нужен, чтобы проверять валидность операции
    на уровне счётов и клиентов, а потом объединять результаты проверок."""

    def __init__(self, reason: str = ""):
        self.reason = reason

    def __and__(self, other: "BoolWithReason") -> "BoolWithReason":
        return BoolWithReason(self.reason + other.reason)

    def __bool__(self) -> bool:
        return self.reason == ""

    def raise_if_false(self) -> None:
        "Если результат проверки False, выбрасывает ValueError с причиной."
        if not self:
            raise ValueError(self.reason)


class Transaction:
    """Структура банковской операции, содержащая поля:
        - From: Account - счёт, с которого списывается деньги 
            (название From с большой буквы, т.к. from - зарезервированное слово)
        - To: Account
        - amount: int
        - datetime
        - id: UUID4

        Каждую транзакцию можно записать двумя способами: 
            `Transaction(A, B, n)` и `Transaction(B, A, -n)`
        Эти два представления эквивалентны.
        Второе представление можно получить как `transaction.mirror`.

        Чтобы выполнить транзакцию, нужно вызвать метод `perform`."""
    def __init__(self, From: "Account", To: "Account", amount: int):
        self.From = From
        self.To = To
        self.amount = amount
        self.datetime = datetime.now()
        self.id = uuid4()

    @property
    def mirror(self) -> "Transaction":
        """`Transaction(account_A, account_B, n).mirror == Transaction(account_B, account_A, -n)`

        Это экивалентная транзакция, записанная с точки зрения второй стороны."""
        mirror = Transaction(self.To, self.From, -self.amount)
        mirror.datetime = self.datetime
        mirror.id = self.id
        return mirror

    def check_permissions(self) -> "BoolWithReason":
        """Проверяет, есть ли ограничения на вывод средств у счёта и у клиента.
        
        Использование:
        ```python
        transaction.check_all_permissions().raise_if_false()
        transaction.mirror.check_all_permissions().raise_if_false() 
        ```
        Вторая проверка нужна, если у операции отрицательный amount.
        """
        return self.From.check_withdraw_permissions(self) \
            & self.From.client.check_withdraw_permissions(self)

    def perform(self) -> "Transaction":
        """Проверяет допустимость транзакции и выполняет её.
        Записывает транзакцию в историю обоих счётов."""
        self.check_permissions().raise_if_false()
        self.mirror.check_permissions().raise_if_false()
        return self._perform_without_checking_permissions()

    def _perform_without_checking_permissions(self) -> "Transaction":
        self.From.balance -= self.amount
        self.To.balance += self.amount

        self.To.history.append(self)
        self.From.history.append(self.mirror)
        return self

    def __hash__(self) -> int:
        return hash(self.id)

    def cancel(self) -> "Transaction":
        """Безусловно отменяет транзакцию.
        Даже если у бывшего получателя, например, окажется отрицательный баланс.
        Записывает отменяющую транзакцию в списки транзакций."""
        return Transaction(self.From, self.To, -self.amount)._perform_without_checking_permissions() # pylint: disable=protected-access


class TransactionList:
    """Класс для хранения истории транзакций, играющий роль БД.
    Есть у каждого счёта.

    Возможно, в будущем будет заменен на настоящую БД. 
    Остальные классы менять при этом не придётся."""

    def __init__(self):
        self.transactions: Set[Transaction] = set()

    def append(self, transaction: Transaction) -> None:
        """Добавляет транзакцию в список транзакций.
        Если транзакция уже есть в списке, ничего не делает."""
        self.transactions.add(transaction)


class Account:
    """Базовый класс для счётов.
    Cодержит поля:
        - id: UUID4
        - client: Client
        - balance: int
        - history: TransactionList

    Дочерние классы отличаются правилами вывода средств,
    которые задаются в методе `check_withdraw_permissions`."""
    def __init__(self, client: "Client"):
        self.id = uuid4()
        self.client = client
        self.balance = 0
        self.history: "TransactionList" = TransactionList()

    def check_withdraw_permissions(self, transaction: "Transaction") -> "BoolWithReason": # pylint: disable=unused-argument
        """Проверяет, можно ли совершить транзакцию со счёта данного типа."""
        return NotImplemented

class DebitAccount(Account):
    """счёт, на котором должно находиться неотрицательное количество средств"""
    def check_withdraw_permissions(self, transaction: "Transaction") -> "BoolWithReason":
        if self.balance < transaction.amount:
            return BoolWithReason("Not enough money\n")
        return BoolWithReason()

class DepositAccount(Account):
    """Счёт, с которого нельзя выводить деньги до его окончания."""
    def __init__(self, client: "Client", end_date: date):
        super().__init__(client)
        self.end_date = end_date

    def check_withdraw_permissions(self, transaction: "Transaction") -> "BoolWithReason":
        if transaction.datetime < self.end_date:
            return BoolWithReason("Can't withdraw money before end date\n")
        if self.balance < transaction.amount:
            return BoolWithReason("Not enough money\n")
        else:
            return BoolWithReason()

class CreditAccount(Account):
    """Счёт, в котором можно уходить в минус до определённого предела.
    При этом начисляется процентная ставка."""
    def __init__(self, client: "Client", credit_limit: int, interest_rate: float):
        super().__init__(client)
        self.credit_limit = credit_limit
        self.interest_rate = interest_rate

    def check_withdraw_permissions(self, transaction: "Transaction") -> "BoolWithReason":
        if self.balance - transaction.amount < -self.credit_limit:
            return BoolWithReason("Not enough money\n")
        else:
            return BoolWithReason()

class CashAccount(Account):
    """Счёт - черная дыра. Служебный. 
    Является полем 'From' в операции внесения наличных и полем 'To' в операции снятия наличных."""
    def check_withdraw_permissions(self, transaction: "Transaction") -> "BoolWithReason":
        return BoolWithReason()


class Bank:
    """Класс банка, содержит словарь с счетами клиентов 
    и лимит на вывод без предоставления документов."""
    def __init__(self, unathorized_withdrawal_limit: int = 0) -> None:
        self.accounts: Dict[UUID, "Account"] = {}
        self.unathorized_withdrawal_limit = unathorized_withdrawal_limit


class Client:
    """Класс c информацией о клиенте,
    содержит в том числе словарь со счетами и ссылку на банк."""
    def __init__(self, bank: "Bank", name: str, surname: str, passport: str | None = None, address: str | None = None):
        self.bank = bank
        self.name = name
        self.surname = surname
        self.passport = passport
        self.address = address
        self.accounts: Dict[UUID, "Account"] = {}
        self.default_cash_account = self.create_account(CashAccount)

    def create_account(self, account_type: Type["Account"], **kwargs) -> "Account":
        """Создаёт счёт и записывает его в объекты банка и клиента."""
        account = account_type(self, **kwargs)
        self.accounts[account.id] = account
        self.bank.accounts[account.id] = account
        return account

    def check_withdraw_permissions(self, transaction: "Transaction") -> "BoolWithReason":
        """Проверяет, можно ли совершить транзакцию с учётом документов клиента.

        Если у клиента нет паспорта или адреса,
        то он может переводить средства между своими счетами,
        но может за раз снять / перевести только до определённого предела, установленного банком."""

        if self.passport is None or self.address is None:
            if isinstance(transaction.To, CashAccount) or transaction.To.client != self:
                if transaction.amount > self.bank.unathorized_withdrawal_limit:
                    return BoolWithReason("Client doesn't have passport or address\n")
        return BoolWithReason()


class ClientFacade:
    """Utility-класс с операциями, доступными клиенту."""
    def __init__(self, client: "Client"):
        self.client = client

    def create_account(self, account_type: Type["Account"], **kwargs) -> "Account":
        """Создаёт счёт и записывает его в объекты банка и клиента."""
        return self.client.create_account(account_type, **kwargs)

    def withdraw(self, account: "Account", amount: int) -> "Transaction":
        """Создаёт транзакцию со счёта на наличные и выполняет её."""
        return Transaction(account, self.client.default_cash_account, amount).perform()

    def deposit(self, account: "Account", amount: int) -> "Transaction":
        """Создаёт транзакцию внесения наличных на счёт и выполняет её."""
        return Transaction(self.client.default_cash_account, account, amount).perform()

    def transfer(self, from_account: "Account", to_account_id: UUID,
                 amount: int, to_bank: Bank | None = None) -> "Transaction":
        """Создаёт транзакцию перевода средств по номеру счёта и выполняет её.

        Если банк не указан, то считается, что счёт находится в том же банке, что и клиент."""
        if to_bank is None:
            to_bank = self.client.bank
        if to_account_id not in to_bank.accounts:
            raise ValueError("Reciever account not found")
        return Transaction(from_account, to_bank.accounts[to_account_id], amount).perform()
