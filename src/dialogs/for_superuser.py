from aiogram import types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ..json_bridge import SuperuserCommands, check_if_bank_exists
from .utils import sudo, clean_state_preserving_user


router = Router()


class BankCreationState(StatesGroup):
    wait_for_bank_name = State()
    wait_for_unathorized_withdrawal_limit = State()


@router.message(Command('create_bank'))
@sudo
async def create_bank1(message: types.Message, state: FSMContext):
    await message.answer('Введите название банка')
    await state.set_state(BankCreationState.wait_for_bank_name)


@router.message(BankCreationState.wait_for_bank_name)
async def create_bank2(message: types.Message, state: FSMContext):
    if message.text is None:
        return
    await state.update_data({'name': message.text})
    await message.answer('Введите лимит неавторизованного снятия (целое число рублей, можно 0)')
    await state.set_state(BankCreationState.wait_for_unathorized_withdrawal_limit)


@router.message(BankCreationState.wait_for_unathorized_withdrawal_limit)
async def create_bank3(message: types.Message, state: FSMContext):
    if message.text is None:
        return
    try:
        limit = int(message.text)
    except ValueError:
        await message.answer('Не удалось распарсить как целое число')
        return
    command = await state.get_data()
    command['unathorized_withdrawal_limit'] = limit
    result = SuperuserCommands.create_bank(command)
    await message.answer(str(result))
    await clean_state_preserving_user(state)



class ClientCreationState(StatesGroup):
    wait_for_bank_name = State()
    wait_for_client_name = State()
    wait_for_client_surname = State()
    wait_for_client_passport = State()
    wait_for_client_address = State()

@router.message(Command('create_client'))
@sudo
async def create_client1(message: types.Message, state: FSMContext):
    await message.answer('Введите название банка')
    await state.set_state(ClientCreationState.wait_for_bank_name)

@router.message(ClientCreationState.wait_for_bank_name)
async def create_client2(message: types.Message, state: FSMContext):
    if message.text is None:
        return
    if not check_if_bank_exists(message.text):
        await message.answer('Банк с таким названием не существует')
        return
    await state.update_data({'bank': message.text})
    await message.answer('Введите имя клиента')
    await state.set_state(ClientCreationState.wait_for_client_name)

@router.message(ClientCreationState.wait_for_client_name)
async def create_client3(message: types.Message, state: FSMContext):
    if message.text is None:
        return
    await state.update_data({'name': message.text})
    await message.answer('Введите фамилию клиента')
    await state.set_state(ClientCreationState.wait_for_client_surname)

@router.message(ClientCreationState.wait_for_client_surname)
async def create_client4(message: types.Message, state: FSMContext):
    if message.text is None:
        return
    await state.update_data({'surname': message.text})
    await message.answer('Введите паспорт клиента или команду /skip')
    await state.set_state(ClientCreationState.wait_for_client_passport)

@router.message(ClientCreationState.wait_for_client_passport, Command('skip'))
async def create_client5(message: types.Message, state: FSMContext):
    result = SuperuserCommands.create_client(await state.get_data())
    await message.answer(str(result))
    await state.set_state(None)

@router.message(ClientCreationState.wait_for_client_passport)
async def create_client6(message: types.Message, state: FSMContext):
    if message.text is None:
        return
    await state.update_data({'passport': message.text})
    await message.answer('Введите адрес клиента')
    await state.set_state(ClientCreationState.wait_for_client_address)

@router.message(ClientCreationState.wait_for_client_address)
async def create_client7(message: types.Message, state: FSMContext):
    if message.text is None:
        return
    command = await state.get_data()
    command['address'] = message.text
    result = SuperuserCommands.create_client(command)
    await message.answer(str(result))
    await clean_state_preserving_user(state)


