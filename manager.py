import asyncio
from typing import List

from aiogram.types import LinkPreviewOptions
from peewee import DoesNotExist

from db import User, Task
from layout import answer_layout
from ones_manager import OnesException
from spreadsheet_manager import SpreadsheetManager
from aiogram import Bot
from dotenv import dotenv_values
from pathlib import Path

token = dotenv_values(Path(__file__).resolve().parent.joinpath('docker') / '.env')['TOKEN']
bot = Bot(token=token)
admin_id = 314996804


class Manager:
    sm: SpreadsheetManager

    def __init__(self, sm: SpreadsheetManager):
        self.sm = sm

    def update_note(self, task_id: int, text: str, telegram_id: int) -> None:
        user = User.get(telegram_id=telegram_id)
        task = Task.get(id=task_id)
        new_note = self.sm.update_note(task, user, text, task.note)
        task.note = new_note
        task.save()

    def update_answer(self, task_id: int, text: str, telegram_id: int):
        user = User.get(telegram_id=telegram_id)
        task = Task.get(id=task_id)
        new_answer = self.sm.update_answer(task, user, text, task.result)
        task.result = new_answer
        task.save()

    def get_all_users(self) -> List[User]:
        return [user for user in User.select()]

    def get_current_user(self, telegram_id: int) -> User:
        try:
            return User.get(User.telegram_id == telegram_id)
        except DoesNotExist:
            return None

    def create_user(self, telegram_id: int, name: str) -> User:
        user = User(telegram_id=telegram_id, name=name)
        try:
            user.save()
        except:
            return None

        return user

    def close(self, task_id: int) -> None:
        task = Task.get(id=task_id)
        task.closed = True
        task.save()

    def get_task_by_id(self, task_id: int) -> Task:
        return Task.get(id=task_id)

    def get_current_user_open_tasks(self, telegram_id: int) -> List[Task]:
        user = User.get(telegram_id=telegram_id)
        return Task.select().where(Task.closed == False).where(Task.performer == user.name)

    def get_current_user_tasks(self, telegram_id: int) -> List[Task]:
        user = User.get(telegram_id=telegram_id)
        return Task.select().where(Task.performer == user.name)

    def get_all_open_tasks(self) -> List[Task]:
        return Task.select().where(Task.closed == False)

    def get_task_to_string(self, user: User | None, task: Task) -> str:
        if user is None:
            try:
                user = User.get(name=task.performer)
            except DoesNotExist:
                return task.to_string(None, self.sm.get_row_link(task))
        return task.to_string(user.telegram_id, self.sm.get_row_link(task))

    async def notify_pool(self) -> None:
        while True:
            try:
                tasks = self.sm.sync_tabs()
            except OnesException as e:
                await bot.send_message(admin_id, str(e))
                return
            except Exception:
                return
            for task in tasks:
                try:
                    user = User.get(name=task.performer)
                    if task.closed:
                        continue
                    if task.sent_to is not None and task.sent_to.telegram_id == user.telegram_id:
                        continue
                    if task.address == "" and (task.sent_to is None or task.sent_to.telegram_id != admin_id):
                        link = self.sm.get_row_link(task)
                        admin_user = User.get(telegram_id=admin_id)
                        await bot.send_message(admin_id, f"Не найден адрес по заявке [№{task.inner_id}]({link})",
                                               parse_mode="Markdown",
                                               link_preview_options=LinkPreviewOptions(is_disabled=True)
                                               )
                        task.sent_to = admin_user
                        task.save()
                        continue
                    await bot.send_message(user.telegram_id,
                                           f"*Невыполненная заявка*\n{self.get_task_to_string(user, task)}",
                                           reply_markup=answer_layout(task.id), parse_mode="Markdown",
                                           link_preview_options=LinkPreviewOptions(is_disabled=True))
                    task.sent_to = user
                    task.save()
                except DoesNotExist as e:
                    continue
            await asyncio.sleep(60)
