from typing import List
import pygsheets
from dotenv import dotenv_values
from pathlib import Path
from pygsheets import Spreadsheet
from db import Tab, Task, User
from datetime import datetime
from pytz import timezone
from ones_manager import OnesManager, OnesException
import logging

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']


class SpreadsheetManager:
    url: str
    ones: OnesManager

    def __init__(self, ones: OnesManager):
        self.url = dotenv_values(Path(__file__).resolve().parent.joinpath('docker') / '.env')["SPREADSHEET_ID"]
        self.ones = ones

    def get_row_link(self, task: Task) -> str:
        return (f"https://docs.google.com/spreadsheets/d/"
                f"{self.url}/edit?range={int(task.inner_id) + 5}:{int(task.inner_id) + 5}#gid=461729850")

    def update_note(self, task: Task, user: User, text: str, old_text: str) -> str:
        return self.update_field(task, user, 'I', text, old_text)

    def update_answer(self, task: Task, user: User, text: str, old_text: str) -> str:
        return self.update_field(task, user, 'G', text, old_text)

    def update_datetime(self, task: Task, text: str) -> None:
        tab = task.tab
        sh = self.__get_spreadsheet()
        wsh = sh.worksheet_by_title(tab.name)
        row = int(task.inner_id) + 5
        wsh.update_value(f"B{row}", text)

    def update_address(self, task: Task, text: str):
        tab = task.tab
        sh = self.__get_spreadsheet()
        wsh = sh.worksheet_by_title(tab.name)
        row = int(task.inner_id) + 5
        wsh.update_value(f"E{row}", text)

    def update_chop(self, task: Task, text: str):
        tab = task.tab
        sh = self.__get_spreadsheet()
        wsh = sh.worksheet_by_title(tab.name)
        row = int(task.inner_id) + 5
        wsh.update_value(f"D{row}", text)

    def update_field(self, task: Task, user: User, field: str, text: str, old_text: str) -> str:
        tab = task.tab
        sh = self.__get_spreadsheet()
        wsh = sh.worksheet_by_title(tab.name)
        row = int(task.inner_id) + 5
        now = datetime.now().astimezone(timezone('Europe/Moscow')).strftime("%Y-%m-%d %H:%M")
        if old_text == '':
            text = f"{text}({now})({user.name})"
        else:
            text = f"{old_text}\n{text}({now})({user.name})"
        wsh.update_value(f"{field}{row}", text)
        return text

    def sync_tabs(self) -> List[Task]:
        sh = self.__get_spreadsheet()
        tabs = sh.worksheets()
        tabModels = []
        for tab in tabs:
            if self.__need_to_sync(tab.title):
                try:
                    tab_model, created = Tab.get_or_create(name=tab.title)
                    tabModels.append(tab_model)
                except:
                    continue
        notify = self.__sync_data(tabModels, sh)
        return notify

    def __need_to_sync(self, month: str) -> bool:
        year = int(''.join(filter(str.isdigit, month)))
        month = self.__get_month(''.join([i for i in month if i.isalpha()]).lower())
        now_year = datetime.now().year
        now_month = datetime.now().month
        if now_month == 1 or now_month == 2:
            if month == 12 or month == 1 or month == 2:
                if year == now_year or year == (now_year - 1):
                    return True
        if year < now_year:
            return False
        if month >= (now_month - 1):
            return True
        return False

    def __get_month(self, month: str) -> int:
        match month:
            case 'январь':
                return 1
            case 'февраль':
                return 2
            case 'март':
                return 3
            case 'апрель':
                return 4
            case 'май':
                return 5
            case 'июнь':
                return 6
            case 'июль':
                return 7
            case 'август':
                return 8
            case 'сентябрь':
                return 9
            case 'октябрь':
                return 10
            case 'ноябрь':
                return 11
            case 'декабрь':
                return 12

    def __sync_data(self, tabs: List[Tab], sh: Spreadsheet) -> List[Task]:
        to_notify = []
        for tab in tabs:
            logging.info("sync tab " + tab.name)
            data = sh.worksheet_by_title(tab.name).get_values('A6', 'I999')
            for i in range(len(data)):
                task_value = data[i]
                if (task_value[1] != '' or task_value[2] != ''
                        or task_value[3] != '' or task_value[4] != '' or task_value[5] != ''
                        or task_value[6] != '' or task_value[7] != '' or task_value[8] != ''):
                    task: Task = None
                    created: bool = False
                    closed: bool = task_value[6] != ''
                    update_datetime = False
                    update_address = False
                    update_chop = False
                    if task_value[1] == '':
                        update_datetime = True
                        datetime_to_write = datetime.now().astimezone(timezone('Europe/Moscow')).strftime("%Y-%m-%d %H:%M")
                    else:
                        datetime_to_write = task_value[1]
                    chop_to_write = ''
                    if task_value[3] == '':
                        update_chop = True
                        try:
                            chop_to_write = self.ones.get_chop_by_station_number(task_value[2])
                            if chop_to_write is None:
                                chop_to_write = ''
                        except Exception:
                            pass
                    else:
                        chop_to_write = task_value[3]
                    address_to_write = ''
                    if task_value[4] == '':
                        update_address = True
                        try:
                            address_to_write = self.ones.get_addresses_by_station_number(task_value[2])
                        except OnesException as e:
                            pass
                    else:
                        address_to_write = task_value[4]
                    try:
                        task = Task.get(tab=tab, inner_id=task_value[0])
                    except Exception:
                        pass
                    if task is None:
                        task, created = Task.get_or_create(
                            tab=tab,
                            inner_id=task_value[0],
                            datetime=datetime_to_write,
                            station=task_value[2],
                            chop=chop_to_write,
                            address=address_to_write,
                            type=task_value[5],
                            result=task_value[6],
                            performer=task_value[7],
                            note=task_value[8],
                            closed=closed,
                        )
                    else:
                        task.datetime = datetime_to_write
                        task.station = task_value[2]
                        task.chop = chop_to_write
                        task.address = address_to_write
                        task.type = task_value[5]
                        task.result = task_value[6]
                        task.performer = task_value[7]
                        task.note = task_value[8]
                        task.closed = closed
                        task.save()
                    if update_datetime:
                        self.update_datetime(task, datetime_to_write)
                    if update_address:
                        self.update_address(task, address_to_write)
                    if update_chop:
                        self.update_chop(task, chop_to_write)
                    if self.__need_to_notify(task, created):
                        to_notify.append(task)
        return to_notify

    def __need_to_notify(self, task: Task, created: bool) -> bool:
        if task.closed:
            return False
        if created is True:
            return task.performer != ''
        return True

    def __get_spreadsheet(self) -> Spreadsheet:
        gc = pygsheets.authorize(
            service_file=Path(__file__).resolve().parent.joinpath('docker').absolute().as_posix() + '/gtoken.json')

        return gc.open_by_key(self.url)
