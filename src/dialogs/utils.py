from functools import wraps
from aiogram import types
from aiogram.fsm.context import FSMContext

def sudo(func):
    @wraps(func)
    async def wrapper(message: types.Message, state: FSMContext):
        data = await state.get_data()
        if data.get('mode') != 'superuser':
            await message.answer('Недоступно, нужно поменять /mode')
            return
        await func(message, state)
    return wrapper

def require_auth(func):
    @wraps(func)
    async def wrapper(message: types.Message, state: FSMContext):
        data = await state.get_data()
        if data.get('client_facade') is None:
            await message.answer('Нужно авторизоваться')
            return
        await func(message, state)
    return wrapper

async def clean_state_preserving_user(state: FSMContext):
    data = await state.get_data()
    await state.set_data({
        'mode': data.get('mode'),
        'client_facade': data.get('client_facade'),
    })
    await state.set_state(None)