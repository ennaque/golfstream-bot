from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, InlineKeyboardButton, KeyboardButton


layout_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📋 Все заявки")],
    [KeyboardButton(text="📋 Невыполненные заявки")]
])

admin_layout_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📋 Все мои заявки")],
    [KeyboardButton(text="📋 Мои невыполненные заявки")],
    [KeyboardButton(text="📋 Все невыполненные заявки")]
])


def answer_layout(task_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ответить", callback_data=f"answer-{task_id}"),
         InlineKeyboardButton(text="Примечание", callback_data=f"note-{task_id}")]])


def closed_layout(task_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ответить", callback_data=f"answer-{task_id}"),
         InlineKeyboardButton(text="Заявка закрыта", callback_data=f"done")]])


def answer_abort_layout(task_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отменить", callback_data=f"abort-{task_id}")]])

def note_abort_layout():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отменить", callback_data="cancel")]])
