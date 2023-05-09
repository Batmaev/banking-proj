from aiogram import types, Router
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ..core import ClientFacade
from ..json_bridge import ServerState, ClientCommands
from .utils import require_auth, clean_state_preserving_user


router = Router()


class AuthState(StatesGroup):
    wait_for_user_id = State()

@router.message(Command('auth'))
async def auth1(message: types.Message, state: FSMContext):
    await message.answer('Введите токен клиента')
    await state.set_state(AuthState.wait_for_user_id)

@router.message(AuthState.wait_for_user_id)
async def auth2(message: types.Message, state: FSMContext, server_state: ServerState):
    if message.text is None:
        return
    if (client_facade := server_state.get_client_facade_by_token(message.text)) is None:
        await message.answer('Неверный токен')
    else:
        await state.update_data({'client_facade': client_facade})
        await state.update_data({'mode': 'client'})
        await message.answer('Вы авторизованы')
        await state.set_state(None)




class CreateAccountState(StatesGroup):
    wait_for_account_type = State()
    wait_for_end_date = State()
    wait_for_credit_limit = State()
    wait_for_interest_rate = State()

@router.message(Command('create_account'))
@require_auth
async def ask_type(message: types.Message, state: FSMContext):
    await message.answer('Выберите тип счёта:', reply_markup=types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text='DebitAccount'),
                types.KeyboardButton(text='DepositAccount'),
            ],
            [
                types.KeyboardButton(text='CreditAccount'),
                types.KeyboardButton(text='CashAccount'),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    ))
    await state.set_state(CreateAccountState.wait_for_account_type)

@router.message(CreateAccountState.wait_for_account_type, Text(['DebitAccount', 'DepositAccount', 'CreditAccount', 'CashAccount']))
async def create_account2(message: types.Message, state: FSMContext):
    await state.update_data({'account_type': message.text})
    if message.text == 'DebitAccount' or message.text == 'CashAccount':
        await create_account_finalize(message, state)
    elif message.text == 'DepositAccount':
        await message.answer('Введите дату окончания срока действия счёта в формате YYYY-MM-DD')
        await state.set_state(CreateAccountState.wait_for_end_date)
    elif message.text == 'CreditAccount':
        await message.answer('Введите credit limit')
        await state.set_state(CreateAccountState.wait_for_credit_limit)

@router.message(CreateAccountState.wait_for_end_date)
async def create_account3(message: types.Message, state: FSMContext):
    await state.update_data({'end_date': message.text})
    await create_account_finalize(message, state)

@router.message(CreateAccountState.wait_for_credit_limit)
async def create_account4(message: types.Message, state: FSMContext):
    await state.update_data({'credit_limit': message.text})
    await message.answer('Введите interest rate')
    await state.set_state(CreateAccountState.wait_for_interest_rate)

@router.message(CreateAccountState.wait_for_interest_rate)
async def create_account5(message: types.Message, state: FSMContext):
    await state.update_data({'interest_rate': message.text})
    await create_account_finalize(message, state)

async def create_account_finalize(message: types.Message, state: FSMContext):
    command = await state.get_data()
    client_facade = command['client_facade']

    posiible_kwargs = ['end_date', 'credit_limit', 'interest_rate']
    kwargs = {key: command[key] for key in posiible_kwargs if key in command}
    command = {'account_type': command['account_type'], 'kwargs': kwargs}

    result = ClientCommands.create_account(command, client_facade)
    await message.answer(str(result), reply_markup=types.ReplyKeyboardRemove(remove_keyboard=True))
    await clean_state_preserving_user(state)




async def select_account(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client_facade: ClientFacade = data['client_facade']
    accounts = ClientCommands.show_accounts({}, client_facade)['accounts']
    if accounts == []:
        await message.answer('У вас нет счетов')
        await clean_state_preserving_user(state)
        return
    await message.answer('Выберите счёт:', reply_markup=types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text=str(account['id']))]
            for account in accounts
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    ))




class DepositState(StatesGroup):
    wait_for_account_id = State()
    wait_for_amount = State()

@router.message(Command('deposit'))
@require_auth
async def deposit1(message: types.Message, state: FSMContext):
    await select_account(message, state)
    await state.set_state(DepositState.wait_for_account_id)

@router.message(DepositState.wait_for_account_id)
async def deposit2(message: types.Message, state: FSMContext):
    await state.update_data({'account_id': message.text}, reply_markup=types.ReplyKeyboardRemove(remove_keyboard=True))
    await message.answer('Введите сумму')
    await state.set_state(DepositState.wait_for_amount)

@router.message(DepositState.wait_for_amount)
async def deposit3(message: types.Message, state: FSMContext):
    command = await state.get_data()
    command['amount'] = message.text
    client_facade = command['client_facade']

    result = ClientCommands.deposit(command, client_facade)
    await message.answer(str(result))
    await clean_state_preserving_user(state)






@router.message(Command('show_accounts'))
@require_auth
async def show_accounts(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client_facade: ClientFacade = data['client_facade']
    result = ClientCommands.show_accounts({}, client_facade)
    await message.answer(str(result))




class ShowHistoryState(StatesGroup):
    wait_for_account_id = State()

@router.message(Command('show_history'))
@require_auth
async def show_history(message: types.Message, state: FSMContext):
    await select_account(message, state)
    await state.set_state(ShowHistoryState.wait_for_account_id)

@router.message(ShowHistoryState.wait_for_account_id)
async def show_history2(message: types.Message, state: FSMContext):
    client_facade = (await state.get_data())['client_facade']
    result = ClientCommands.show_history({'account_id': message.text}, client_facade)
    await message.answer(str(result),reply_markup=types.ReplyKeyboardRemove(remove_keyboard=True))
    await clean_state_preserving_user(state)

