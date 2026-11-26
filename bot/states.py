from aiogram.fsm.state import State, StatesGroup


class AddStates(StatesGroup):
    confirm_replace = State()


class DeleteStates(StatesGroup):
    confirm = State()
