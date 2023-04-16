"""Flask app and routes.

Функции в этом модуле авторизуют пользователей с помощью токена
и передают их запросы в функции из json_interface.py.

Этот модуль — скорее заглушка для нормального интерфейса.
Сейчас я использую Flask, но в будущем я могу перейти на другой фреймворк,
потому что все Flask-специфичные функции находятся в этом файле."""

from functools import wraps
from typing import Dict

from flask import Flask, request
from core import ClientFacade
from json_interface import ServerState, SuperuserCommands, ClientCommands


flask_app = Flask('banks')
bank_app = ServerState()


def json_only(f):
    """Декоратор, который проверяет, что запрос содержит JSON-тело,
    и передаёт его первым аргументом в оборачиваемую функцию"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.is_json and request.json is not None:
            return f(request.json, *args, **kwargs)
        else:
            return {'status': 'error', 'message': 'No json in request'}, 400
    return wrapper


@flask_app.route('/superuser/create_bank', methods=['POST'])
@json_only
def route_superuser_create_bank(command: Dict):
    return SuperuserCommands.create_bank(command, bank_app.banks)


@flask_app.route('/superuser/create_client', methods=['POST'])
@json_only
def route_superuser_create_client(command: Dict):
    return SuperuserCommands.create_client(command, bank_app)


@flask_app.route('/superuser/update_client', methods=['POST'])
@json_only
@bank_app.with_client_token
def route_superuser_update_client(command: Dict, client_facade: ClientFacade):
    return SuperuserCommands.update_client(command, client_facade)


@flask_app.route('/superuser/cancel_transaction', methods=['POST'])
@json_only
@bank_app.with_client_token
def route_superuser_cancel_transaction(command: Dict, client_facade: ClientFacade):
    return SuperuserCommands.cancel_transaction(command, client_facade)



@flask_app.route('/client/create_account', methods=['POST'])
@json_only
@bank_app.with_client_token
def route_client_create_account(command: Dict, client_facade: ClientFacade) -> Dict:
    return ClientCommands.create_account(command, client_facade)


@flask_app.route('/client/withdraw', methods=['POST'])
@json_only
@bank_app.with_client_token
def route_client_withdraw(command: Dict, client_facade: ClientFacade) -> Dict:
    return ClientCommands.withdraw(command, client_facade)


@flask_app.route('/client/deposit', methods=['POST'])
@json_only
@bank_app.with_client_token
def route_client_deposit(command: Dict, client_facade: ClientFacade) -> Dict:
    return ClientCommands.deposit(command, client_facade)


@flask_app.route('/client/transfer', methods=['POST'])
@json_only
@bank_app.with_client_token
def route_client_transfer(command: Dict, client_facade: ClientFacade) -> Dict:
    return ClientCommands.transfer(command, client_facade, bank_app.banks)


@flask_app.route('/client/show_accounts', methods=['POST'])
@json_only
@bank_app.with_client_token
def route_client_show_accounts(command: Dict, client_facade: ClientFacade) -> Dict:
    return ClientCommands.show_accounts(command, client_facade)


@flask_app.route('/client/show_history', methods=['POST'])
@json_only
@bank_app.with_client_token
def route_client_show_history(command: Dict, client_facade: ClientFacade) -> Dict:
    return ClientCommands.show_history(command, client_facade)




if __name__ == '__main__':
    flask_app.run(port=8000, debug=True)
