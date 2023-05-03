from aiogram import types, Router
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from .utils import clean_state_preserving_user # pylint: disable=relative-beyond-top-level

router = Router()

@router.message(Command('start', 'help'))
async def send_welcome(message: types.Message):
    await message.answer("""
Привет! Я бот для работы с игрушечным банком.

Список команд, доступных суперпользователю:
/create_bank - создать банк
/create_client - создать клиента
/update_client - обновить данные клиента
/cancel_transaction - отменить транзакцию
/mode - переключиться в режим клиента

Список команд, доступных клиенту:
/auth - авторизоваться
/create_account - создать счёт
/withdraw - снять деньги со счёта
/deposit - положить деньги на счёт
/transfer - перевести деньги на другой счёт / другому клиенту / в другой банк
/mode - переключиться в режим суперпользователя
""")


class SelectingMode(StatesGroup):
    selecting_mode = State()


@router.message(Command('mode'))
async def select_mode(message: types.Message, state: FSMContext):
    await message.answer('Выберите режим:', reply_markup=types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text='client'),
                types.KeyboardButton(text='superuser'),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    ))
    await state.set_state(SelectingMode.selecting_mode)


@router.message(SelectingMode.selecting_mode, Text(['client', 'superuser']))
async def set_mode(message: types.Message, state: FSMContext):
    await state.update_data(mode=message.text)
    await message.answer(
        f'Установлен {message.text} mode',
        reply_markup=types.ReplyKeyboardRemove(remove_keyboard=True)
    )
    await state.set_state(None)


@router.message(Command('back'))
async def cancel(message: types.Message, state: FSMContext):
    await clean_state_preserving_user(state)
    await message.answer(
        'Диалог отменен, состояние очищено',
        reply_markup=types.ReplyKeyboardRemove(remove_keyboard=True)
    )



@router.errors()
async def errors_handler(error: types.ErrorEvent):
    exception = error.exception
    if error.update.message is not None:
        await error.update.message.reply(f'Ошибка: {exception}')
    raise exception

@router.message(Command('make_error'))
async def make_error(message: types.Message):
    raise RuntimeError('Это тестовая ошибка')



@router.message()
async def unknown(message: types.Message):
    await message.answer('Эта команда ещё не реализована')
