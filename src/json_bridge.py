"""Функции, которые принимают JSON-запросы и возвращают JSON-ответы.

Банковское приложение может работать только на сервере, поэтому я реализую JSON-интерфейс.

Есть словарь всех банков и словарь всех клиентов,
которые в будущем можно заменить на БД."""

from datetime import date
from typing import Dict
from uuid import UUID, uuid4

from .core import Bank, Client, ClientFacade


class BankDict(Dict[str, Bank]):
    """Словарь, чтобы находить банки по названию.
    Может проксировать доступ к БД."""

class ClientFacadeDict(Dict[UUID, ClientFacade]):
    """Словарь, чтобы находить клиентов по токену.

    В будущем имеет смысл давать клиентам пароли вместо токенов,
    сохранять их хеши на диск, а также использовать сессионные куки."""

class ServerState:
    """Словари банков и клиентов с токенами.
    Нужно инициализировать при запуске сервера — как и Flask() / aiogram.Bot().

    На данный момент они нигде не хранятся, но теоретически могут быть на диске."""
    def __init__(self):
        self.banks = BankDict()
        self.client_facades = ClientFacadeDict()

    def get_client_facade_by_token(self, token: str) -> ClientFacade | None:
        """Возвращает клиента по токену или None, если такого токена нет"""
        try:
            return self.client_facades[UUID(token)]
        except (KeyError, ValueError):
            return None
            # KeyError: нет такого токена
            # ValueError: неверный формат токена




class SuperuserCommands:
    """Namespace for commands such as 'create_bank'
    that ordinary clients can't use"""

    @staticmethod
    def create_bank(command: Dict[str, str], server_state: ServerState) -> Dict:
        """Создаёт банк и записывает его в словарь banks.
        Принимает на вход JSON с обязательным ключом `name` (название банка)
        и опциональным ключом `unathorized_withdrawal_limit`"""

        if 'unathorized_withdrawal_limit' in command:
            bank = Bank(int(command['unathorized_withdrawal_limit']))
        else:
            bank = Bank()
        server_state.banks[command['name']] = bank
        return {'status': 'ok', 'message': 'Created bank ' + command['name']}


    @staticmethod
    def create_client(command: Dict[str, str], server_state: ServerState) -> Dict:
        """Создаёт клиента и записывает его в словарь client_facades.

        Принимает на вход JSON с обязательными ключами `bank`, `name`, `surname`
        и опциональными ключами `passport`, `address`.

        Возвращает JSON с ключами `status`, `message` и `client_token`"""

        bank = server_state.banks[command['bank']]
        client = Client(bank, command['name'], command['surname'],
                        command.get('passport'), command.get('address'))
        client_facade = ClientFacade(client)
        client_token = uuid4()
        server_state.client_facades[client_token] = client_facade
        return {'status': 'ok', 'message': 'Created client', 'client_token': client_token}


    @staticmethod
    def update_client(command: Dict[str, str], client_facade: ClientFacade) -> Dict:
        """Обновляет данные клиента по его токену.
        Принимает на вход JSON с ключами из подмножества `name`, `surname`, `passport`, `address`.
        Возвращает данные обновлённого клиента."""
        client = client_facade.client
        for key, value in command.items():
            if key in ['name', 'surname', 'passport', 'address']:
                setattr(client, key, value)
        return {'status': 'ok', 'message': 'Now client is ' + str(vars(client))}


    @staticmethod
    def cancel_transaction(command: Dict[str, str], client_facade: ClientFacade) -> Dict:
        """Отменяет транзакцию по её идентификатору.
        Принимает на вход JSON с ключами `transaction_id` и `account_id`.

        `account_id` и `client_token`, который тоже должен быть в запросе,
        нужны для того, чтобы найти транзакцию
        (сейчас нет единого реестра транзакций)."""

        try:
            transaction_id = UUID(command['transaction_id'])
            account_id = UUID(command['account_id'])
            account = client_facade.client.accounts[account_id]
            transaction = account.history[transaction_id]
            result = transaction.cancel()
            assert result
            return {'status': 'ok', 'message': 'Canceled transaction ' + str(transaction_id)}
        except KeyError as e:
            return {'status': 'error', 'message': str(e)}
        except AssertionError:
            return {'status': 'error', 'message': repr(result)} # type: ignore



class ClientCommands:
    """Namespace for commands such as 'create_account',
    that are performed by ordinary clients"""

    @staticmethod
    def create_account(command: Dict, client_facade: ClientFacade) -> Dict:
        """Создаёт счёт, передавая вызов в ClientFacade.
        Принимает на вход JSON с ключами `account_type` и `kwargs`.

        `account_type` должен быть строкой с названием одного из наследников типа Account
        (DebitAccount, DepositAccount, CreditAccount, CashAccount).

        `kwargs` может содержать ключи: 
            - для DepositAccount: `end_date` в формате 'YYYY-MM-DD'
            - для CreditAccount: `credit_limit` и `interest_rate` (в долях единицы)"""
        try:
            account_type = command['account_type']
            kwargs = command.get('kwargs', {})
            if 'end_date' in kwargs:
                year, month, day = kwargs['end_date'].split('-')
                kwargs['end_date'] = date(int(year), int(month), int(day))
            account = client_facade.create_account(account_type, **kwargs)
            return {'status': 'ok', 'message': 'Created account', 'info': account.info()}
        except KeyError:
            return {'status': 'error', 'message': 'No account type in request'}
        except TypeError:
            return {'status': 'error', 'message': 'Invalid kwargs'}
        except ValueError as e:
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def withdraw(command: Dict[str, str], client_facade: ClientFacade) -> Dict:
        """Снимает деньги со счёта, передавая вызов в ClientFacade.
        Принимает на вход JSON с ключами `account_id` и `amount`"""
        try:
            account_id = UUID(command['account_id'])
            amount = int(command['amount'])
            result = client_facade.withdraw(account_id, amount)
            assert result
            return {'status': 'ok', 'message': 'Withdrawn ' + str(amount)}
        except KeyError:
            return {'status': 'error', 'message': 'No account id or amount in request'}
        except AssertionError:
            return {'status': 'error', 'message': repr(result)} # type: ignore

    @staticmethod
    def deposit(command: Dict[str, str], client_facade: ClientFacade) -> Dict:
        """Пополняет счёт, передавая вызов в ClientFacade.
        Принимает на вход JSON с ключами `account_id` и `amount`"""
        try:
            account_id = UUID(command['account_id'])
            amount = int(command['amount'])
            result = client_facade.deposit(account_id, amount)
            assert result
            return {'status': 'ok', 'message': 'Deposited ' + str(amount)}
        except KeyError:
            return {'status': 'error', 'message': 'No account id or amount in request'}
        except ValueError:
            return {'status': 'error', 'message': 'Invalid amount / account id'}
        except AssertionError:
            return {'status': 'error', 'message': repr(result)} # type: ignore

    @staticmethod
    def transfer(command: Dict[str, str],
                 client_facade: ClientFacade, server_state: ServerState) -> Dict:
        """Переводит деньги с одного счёта на другой, передавая вызов в ClientFacade.
        Принимает на вход JSON с обязательными ключами `from_account_id`, `to_account_id`, `amount`
        и опциональным ключом `to_bank_name`. Если `to_bank_name` не указан, то предполагается,
        что отправитель и получатель находятся в одном банке."""
        try:
            from_account_id = UUID(command['from_account_id'])
            to_account_id = UUID(command['to_account_id'])
            to_bank_name = command.get('to_bank_name')
            to_bank = server_state.banks.get(to_bank_name) # type: ignore
            amount = int(command['amount'])
            result = client_facade.transfer(from_account_id, to_account_id, amount, to_bank)
            assert result
            return {'status': 'ok', 'message': 'Transferred ' + str(amount)}
        except KeyError:
            return {'status': 'error',
                    'message': 'No from_account_id / to_account_id or amount in request'}
        except ValueError:
            return {'status': 'error', 'message': 'Invalid amount / account id'}
        except AssertionError:
            return {'status': 'error', 'message': repr(result)} # type: ignore

    @staticmethod
    def show_accounts(_command: Dict, client_facade: ClientFacade) -> Dict:
        """Отдаёт список счетов клиента с основной информацией (id, тип, баланс)"""
        accounts = client_facade.get_accounts()
        accounts_info = [account.info() for account in accounts]
        return {'status': 'ok', 'message': '', 'accounts': accounts_info}

    @staticmethod
    def show_history(command: Dict[str, str], client_facade: ClientFacade) -> Dict:
        """Отдаёт список транзакций (id, from, to, amount, datetime [ISO]).

        Принимает JSON с обязательным полем `account_id`."""
        try:
            account_id = UUID(command['account_id'])
            history = client_facade.get_account_history(account_id)
            history_json = [transaction.info() for transaction in history]
            return {'status': 'ok', 'message': '', 'history': history_json}
        except KeyError:
            return {'status': 'error', 'message': 'No account id in request'}
        except ValueError as e:
            return {'status': 'error', 'message': str(e)}
