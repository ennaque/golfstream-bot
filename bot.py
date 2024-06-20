import logging
import asyncio
import threading
from aiogram import Bot, Dispatcher
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, LinkPreviewOptions
from dotenv import dotenv_values
from pathlib import Path

from layout import closed_layout, answer_abort_layout, answer_layout, layout_menu, admin_layout_menu, note_abort_layout
from manager import Manager
from ones_manager import OnesManager
from spreadsheet_manager import SpreadsheetManager
from states import RegisterState, TaskState

logging.basicConfig(level=logging.INFO, filename='prod_log.log', filemode='w',
                    format="%(asctime)s %(levelname)s %(message)s")
token = dotenv_values(Path(__file__).resolve().parent.joinpath('docker') / '.env')['TOKEN']
bot = Bot(token=token)
dp = Dispatcher()
ones = OnesManager()
spreadsheet_manager = SpreadsheetManager(ones)
manager = Manager(sm=spreadsheet_manager)
admin_id = 314996804


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    if manager.get_current_user(message.from_user.id) is None:
        await message.answer("Введите фамилию")
        await state.set_state(RegisterState.surname)
    else:
        if message.from_user.id != admin_id:
            await message.answer("Меню", reply_markup=layout_menu)
        else:
            await message.answer("Меню", reply_markup=admin_layout_menu)


@dp.message(Command("users"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    users = manager.get_all_users()
    val = ''
    for user in users:
        val = f"{val}\n[{user.name}](tg://user?id={user.telegram_id})"
    await message.answer(f"*Список зарегестрированных пользователей*:\n{val}", parse_mode="Markdown")


@dp.message(RegisterState.surname)
async def cmd_state(message: Message):
    if manager.create_user(message.from_user.id, message.text.strip()) is None:
        await message.answer('Пользователь уже существует')
    await message.answer('Пользователь создан')


@dp.message(Command("tasks"))
@dp.message(lambda msg: "📋 Невыполненные заявки" == msg.text)
@dp.message(lambda msg: "📋 Мои невыполненные заявки" == msg.text)
async def tasks(message: Message, state: FSMContext) -> None:
    tasks = manager.get_current_user_open_tasks(message.from_user.id)
    for task in tasks:
        await message.answer(f"*Невыполненная заявка*\n{manager.get_task_to_string(None, task)}",
                             reply_markup=answer_layout(task.id), parse_mode="Markdown",
                             link_preview_options=LinkPreviewOptions(is_disabled=True))


@dp.message(Command("all-tasks"))
@dp.message(lambda msg: "📋 Все мои заявки" == msg.text)
@dp.message(lambda msg: "📋 Все заявки" == msg.text)
async def all_tasks(message: Message, state: FSMContext) -> None:
    for task in manager.get_current_user_tasks(message.from_user.id):
        string_task = manager.get_task_to_string(None, task)
        if task.closed:
            await message.answer(f"*Невыполненная заявка*\n{string_task}",
                                 reply_markup=closed_layout(task.id), parse_mode="Markdown",
                                 link_preview_options=LinkPreviewOptions(is_disabled=True))
        else:
            await message.answer(f"*Выполненная заявка*\n{string_task}",
                                 reply_markup=answer_layout(task.id), parse_mode="Markdown",
                                 link_preview_options=LinkPreviewOptions(is_disabled=True))


@dp.message(Command("all-tasks-admin"))
@dp.message(lambda msg: "📋 Все невыполненные заявки" == msg.text)
async def all_tasks(message: Message, state: FSMContext) -> None:
    if message.from_user.id != admin_id:
        return
    tasks = manager.get_all_open_tasks()
    for task in tasks:
        string_task = manager.get_task_to_string(None, task)
        await message.answer(f"*Незакрытая заявка*\n{string_task}",
                             reply_markup=closed_layout(task.id), parse_mode="Markdown",
                             link_preview_options=LinkPreviewOptions(is_disabled=True))


@dp.message(Command('help'))
async def command_help_handler(message: Message, state: FSMContext) -> None:
    await message.answer(
        "<b>Помощь по боту:</b>\n"
        "/help - Помощь\n"
        "/start - Начать работу\n"
        "/tasks - Список невыполненных заявок\n"
        "/all-tasks - Список всех заявок\n"
        "/all-tasks-admin - Список всех невыполненных заявок")


@dp.callback_query(lambda callback: 'answer' in callback.data)
async def get_task_answer_handler(callback: CallbackQuery, state: FSMContext) -> None:
    task_id = callback.data.replace("answer-", "")
    task = manager.get_task_by_id(int(task_id))
    await callback.message.edit_text("Введите ответ на заявку номер " + task.inner_id,
                                     reply_markup=answer_abort_layout(int(task_id)))
    await state.set_state(TaskState.answer)
    await state.update_data(task_id=task_id)


@dp.callback_query(lambda callback: 'note' in callback.data)
async def get_task_note_handler(callback: CallbackQuery, state: FSMContext) -> None:
    task_id = callback.data.replace("note-", "")
    task = manager.get_task_by_id(int(task_id))
    await callback.message.answer("Введите примечание к заявке номер " + task.inner_id,
                                  reply_markup=note_abort_layout())
    await state.set_state(TaskState.note)
    await state.update_data(task_id=task_id)


@dp.callback_query(lambda callback: 'abort' in callback.data)
async def task_answer_close_handler(callback: CallbackQuery, state: FSMContext) -> None:
    task_id = int(callback.data.replace("abort-", ""))
    task = manager.get_task_by_id(task_id)
    if task.closed:
        return
    string_task = manager.get_task_to_string(None, task)
    await callback.message.edit_text(f"*Невыполненная заявка*\n{string_task}",
                                     reply_markup=answer_layout(task_id), parse_mode="MarkdownV2",
                                     link_preview_options=LinkPreviewOptions(is_disabled=True))
    await state.clear()


@dp.callback_query(lambda callback: 'cancel' in callback.data)
async def task_note_close_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Отменено")
    await state.clear()


@dp.message(TaskState.note)
async def task_note_handler(message: Message, state: FSMContext) -> None:
    task_id = await state.get_data()
    task_id = int(task_id.get('task_id', ''))
    task = manager.get_task_by_id(task_id)
    manager.update_note(task_id, message.text.strip(), message.from_user.id)
    await state.clear()
    await message.answer(f"Примечание к заявке {task.inner_id} успешно записано")


@dp.message(TaskState.answer)
async def task_answer_handler(message: Message, state: FSMContext) -> None:
    task_id = await state.get_data()
    task_id = int(task_id.get('task_id', ''))
    task = manager.get_task_by_id(task_id)
    manager.update_answer(task_id, message.text.strip(), message.from_user.id)
    manager.close(task_id)
    await state.clear()
    await message.answer(f"Заявка номер {task.inner_id} закрыта")


async def main():
    await dp.start_polling(bot)


async def pool() -> None:
    while True:
        logging.info("start sync")
        m = Manager(sm=SpreadsheetManager(OnesManager()))
        t = threading.Thread(target=asyncio.run, args=(m.notify_pool(),))
        t.start()
        await asyncio.sleep(40)
        while True:
            if t.is_alive():
                logging.info("wait 10 sec more")
                await asyncio.sleep(10)
            else:
                break
        logging.info("end sync")

if __name__ == "__main__":
    tr = threading.Thread(target=asyncio.run, args=(pool(),))
    tr.start()
    asyncio.run(main())
