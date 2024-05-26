from peewee import *
from dotenv import dotenv_values
from pathlib import Path

env = dotenv_values(Path(__file__).resolve().parent.joinpath('docker') / 'pgsql-variables.env')
con = PostgresqlDatabase(
    'tbot',
    # host='localhost',
    host='postgres',
    port=5432,
    # port=5433,
    user=env['POSTGRES_USER'],
    password=env['POSTGRES_PASSWORD']
)


class User(Model):
    name = CharField(unique=False)
    telegram_id = CharField(unique=True)

    class Meta:
        table_name = 'user'
        database = con


class Tab(Model):
    id = PrimaryKeyField(unique=True)
    name = CharField(unique=True)

    class Meta:
        table_name = 'tab'
        database = con


class Task(Model):
    id = PrimaryKeyField(unique=True)
    inner_id = CharField()
    datetime = TextField()
    station = CharField()
    chop = CharField()
    address = TextField()
    type = TextField()
    result = TextField()
    performer = TextField()
    note = TextField()
    sent_to = ForeignKeyField(User, backref='task', null=True, default=None)
    closed = BooleanField(default=False)
    tab = ForeignKeyField(Tab, backref='task')

    def to_string(self, telegram_id: int | None, row_link: str) -> str:
        performer_str = self.performer + "\n"
        if telegram_id is not None:
            performer_str = f"[{self.performer}](tg://user?id={telegram_id})\n"
        return f"Заявка [№{self.inner_id}]({row_link})\n" \
               f"Дата: {self.datetime}\n" \
               f"Номер: {self.station}\n" \
               f"Организация: {self.chop}\n" \
               f"Адрес: {self.address}\n" \
               f"Характер: {self.type}\n" \
               f"Ответ: {self.result}\n" \
               f"Исполнитель: {performer_str}" \
               f"Примечания: {self.note}"

    @classmethod
    def need_to_create(cls):
        if (cls.datetime is not None or cls.station is not None
                or cls.chop is not None or cls.address is not None or cls.type is not None
                or cls.result is not None or cls.performer is not None or cls.note is not None):
            return True
        return None

    class Meta:
        table_name = 'task'
        database = con
        constraints = [SQL('UNIQUE (tab_id, inner_id)')]


con.connect()
con.create_tables([User, Task, Tab])
con.close()
