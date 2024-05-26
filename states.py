from aiogram.fsm.state import StatesGroup, State


class RegisterState(StatesGroup):
    surname = State()


class TaskState(StatesGroup):
    answer = State()
    note = State()
