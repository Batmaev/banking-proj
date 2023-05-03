from typing import Dict
from uuid import UUID
from aiogram import types

from json_interface import ServerState


class TgAppState:
    def __init__(self, server_state: ServerState):
        self.server_state = server_state
        self.client_tokens: Dict[int, UUID] = {}
        self.modes: Dict[int, str] = {}

    def available_for(self, mode):
        def decorator(f):
            async def wrapper(message: types.Message, *args, **kwargs):
                if self.modes.get(message.from_user.id) == mode:
                    return await f(message, *args, **kwargs)
                else:
                    return await message.answer(f'Команда доступна только в /mode {mode}')
            return wrapper
        return decorator

    def with_client_from_tg_id(self, f):
        async def wrapper(message: types.Message, *args, **kwargs):
            if message.from_id not in self.client_tokens:
                await message.answer('Сначала нужно авторизоваться (/auth)')
                return
            client_token = self.client_tokens[message.from_id]
            if client_token not in self.server_state.client_facades:
                await message.answer('Вы авторизованы под несуществующим клиентом')
                return
            client_facade = self.server_state.client_facades[client_token]
            return await f(message, client_facade, *args, **kwargs)
        return wrapper
