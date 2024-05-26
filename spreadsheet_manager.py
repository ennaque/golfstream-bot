from typing import List
import pygsheets
from dotenv import dotenv_values
from pathlib import Path
from pygsheets import Spreadsheet
from db import Tab, Task, User
from datetime import datetime
from pytz import timezone

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']


class SpreadsheetManager:
    url: str

    def __init__(self):
        self.url = dotenv_values(Path(__file__).resolve().parent.joinpath('docker') / '.env')["SPREADSHEET_ID"]

    def get_row_link(self, task: Task) -> str:
        return (f"https://docs.google.com/spreadsheets/d/"
                f"{self.url}/edit?range={int(task.inner_id) + 5}:{int(task.inner_id) + 5}#gid=461729850")

    def update_note(self, task: Task, user: User, text: str, old_text: str) -> str:
        return self.update_field(task, user, 'I', text, old_text)

    def update_answer(self, task: Task, user: User, text: str, old_text: str) -> str:
        return self.update_field(task, user, 'G', text, old_text)

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
            try:
                tabModel, created = Tab.get_or_create(name=tab.title)
                tabModels.append(tabModel)
            except:
                continue
        notify = self.__sync_data(tabModels, sh)
        return notify

    def __sync_data(self, tabs: List[Tab], sh: Spreadsheet) -> List[Task]:
        to_notify = []
        for tab in tabs:
            data = sh.worksheet_by_title(tab.name).get_values('A6', 'I999')
            for i in range(len(data)):
                task_value = data[i]
                if (task_value[1] != '' or task_value[2] != ''
                        or task_value[3] != '' or task_value[4] != '' or task_value[5] != ''
                        or task_value[6] != '' or task_value[7] != '' or task_value[8] != ''):
                    task: Task = None
                    created: bool = False
                    try:
                        task = Task.get(tab=tab, inner_id=task_value[0])
                    except Exception:
                        pass
                    if task is None:
                        task, created = Task.get_or_create(
                            tab=tab,
                            inner_id=task_value[0],
                            datetime=task_value[1],
                            station=task_value[2],
                            chop=task_value[3],
                            address=task_value[4],
                            type=task_value[5],
                            result=task_value[6],
                            performer=task_value[7],
                            note=task_value[8]
                        )
                    else:
                        task.datetime = task_value[1]
                        task.station = task_value[2]
                        task.chop = task_value[3]
                        task.address = task_value[4]
                        task.type = task_value[5]
                        task.result = task_value[6]
                        task.performer = task_value[7]
                        task.note = task_value[8]
                    if task_value[0] == '53':
                        q = 1
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
