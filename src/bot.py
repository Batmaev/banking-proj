"""Основной модуль бота.
Запускает бота и базу данных (если бы она была)."""
from aiogram import Bot, Dispatcher, types

from .credentials import BOT_TOKEN
from .dialogs import for_superuser, for_client, for_both
from .json_bridge import ServerState

# pylint: disable=missing-function-docstring
# pylint: disable=line-too-long



async def main():

    server_state = ServerState()

    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    dp.include_routers(for_superuser.router, for_client.router, for_both.router)

    await bot.set_my_commands([
        types.BotCommand(command = 'create_bank', description = 'Доступно для суперпользователя'),
        types.BotCommand(command = 'create_client', description = 'Доступно для суперпользователя'),
        types.BotCommand(command = 'update_client', description = 'Доступно для суперпользователя'),
        types.BotCommand(command = 'cancel_transaction', description = 'Доступно для суперпользователя'),
        types.BotCommand(command = 'mode', description = 'Переключиться между режимами'),
        types.BotCommand(command = 'back', description = 'Прервать команду'),
        types.BotCommand(command = 'auth', description = 'Доступно для клиента'),
        types.BotCommand(command = 'create_account', description = 'Доступно для клиента'),
        types.BotCommand(command = 'withdraw', description = 'Доступно для клиента'),
        types.BotCommand(command = 'deposit', description = 'Доступно для клиента'),
        types.BotCommand(command = 'transfer', description = 'Доступно для клиента'),
        types.BotCommand(command = 'show_accounts', description = 'Доступно для клиента'),
        types.BotCommand(command = 'show_history', description = 'Доступно для клиента'),
    ])

    await dp.start_polling(bot, server_state=server_state)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
