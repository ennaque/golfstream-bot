from dotenv import dotenv_values
from pathlib import Path
from typing import List, Any
import requests
from base64 import b64encode


class OnesException(Exception):
    pass


class OnesManager:

    golfstream_ref = 'ea132768-54e7-11e4-a5b8-080027aff4d1'
    barrier_ref = 'ef7e5245-5a9f-11e4-a5bc-080027aff4d1'
    pioner_ref = '1914ffc2-5aa1-11e4-a5bc-080027aff4d1'
    lyn_ref = '3c421c76-5ee9-11e6-bdd4-6cf049727633'
    si_ref = '9e0e1a8e-7681-11eb-9d52-000c29310e9d'

    chop_rif_ref = 'f4ded4b7-5ea4-11e4-8cb9-8c89a563a406'
    chop_partner_ref = '8864aaf9-5e9e-11e4-b602-6cf049727633'
    chop_barrier_ref = '8864aafb-5e9e-11e4-b602-6cf049727633'
    chop_pg_ref = '22a55669-754c-11e4-8e3e-6cf049727633'
    chop_sod_ref = '110d684f-e1b5-11e4-a8ad-6cf049727633'

    def __init__(self):
        self.host = dotenv_values(Path(__file__).resolve().parent.joinpath('docker') / '.env')['ONES_API_HOST']
        self.user = dotenv_values(Path(__file__).resolve().parent.joinpath('docker') / '.env')['ONES_API_USERNAME']
        self.password = dotenv_values(Path(__file__).resolve().parent.joinpath('docker') / '.env')['ONES_API_PASSWORD']

    def get_chop_by_station_number(self, station: str) -> str | None:
        docs = self.__get_documents_by_station_number(station)
        if len(docs) == 1:
            doc = docs[0]
            doc_key = doc.get('Договор_Key')
            path = self.host + (
                f"Document_Договор(guid'{doc_key}')?$format=json")
            st = f"{self.user}:{self.password}".encode()
            resp = requests.get(path,
                                headers={"Authorization": f"Basic {b64encode(st).decode()}"})
            data = resp.json()
            if resp.status_code != 200:
                return None

            keys = {data.get('ОрганизацияОС_Key'), data.get('ОрганизацияКТС_Key'), data.get('ОрганизацияПС_Key'),
                    data.get('ОрганизацияБюджет_Key')}
            keys.remove('00000000-0000-0000-0000-000000000000')
            if len(keys) == 1:
                val = keys.pop()
                if val == self.chop_rif_ref:
                    return 'Р'
                if val == self.chop_partner_ref:
                    return 'П'
                if val == self.chop_pg_ref:
                    return 'П-Г'
                if val == self.chop_barrier_ref:
                    return 'Б'
                if val == self.chop_sod_ref:
                    return 'С'
            return None

    def __get_documents_by_station_number(self, station: str) -> List[Any]:
        station_number = ''.join(filter(str.isdigit, station))
        station_postfix = ''.join([i for i in station if i.isalpha()]).lower()
        if len(station_number) == 1:
            station_number = f'000{station_number}'
        if len(station_number) == 2:
            station_number = f'00{station_number}'
        if len(station_number) == 3:
            station_number = f'0{station_number}'
        station_ref = self.__get_station_ref_key(station_number)
        if station_ref is None:
            raise OnesException(f"Пультовой номер {station} не найден")
        return self.__get_document_key(station_ref, station_postfix)

    def get_addresses_by_station_number(self, station: str) -> str:
        docs = self.__get_documents_by_station_number(station)
        addresses = []
        for doc in docs:
            addresses.append(self.__get_addresses(doc.get('Recorder_Key')))
        addresses = set(addresses)
        if len(addresses) == 0:
            raise OnesException(f'Ни одного адреса по номеру пульта {station} не найдено')
        if len(addresses) > 1:
            exs_str = f'Найдено более одного адреса по номеру пульта {station}, варианты:\n'
            for add in addresses:
                exs_str = f'{exs_str}- {add}\n'
            raise OnesException(exs_str)
        return addresses.pop()

    def __get_organization_name(self, ref: str) -> str | None:
        path = self.host + (
            f"Catalog_%D0%9A%D0%BE%D0%BD%D1%82%D1%80%D0%B0%D0%B3%D0%B5%D0%BD%D1%82%D1%8B("
            f"guid'{ref}')?$format=json")
        st = f"{self.user}:{self.password}".encode()
        resp = requests.get(path,
                            headers={"Authorization": f"Basic {b64encode(st).decode()}"})
        data = resp.json()
        if resp.status_code != 200:
            return None
        value = data.get('Description')
        if value is not None:
            return value
        return None

    def __get_station_ref_key(self, station_number: str) -> str | None:
        path = self.host + (f"Catalog_%D0%9F%D1%83%D0%BB%D1%8C%D1%82%D0%BE%D0%B2%D1%8B%D0%B5%D0%9D%D0%BE%D0%BC%D0%B5%D1%80%D0%B0"
                       f"?$format=json&$filter=Code%20eq%20%27{station_number}%27")
        st = f"{self.user}:{self.password}".encode()
        resp = requests.get(path,
                    headers={"Authorization": f"Basic {b64encode(st).decode()}"})
        data = resp.json()
        if resp.status_code != 200:
            return None
        value = data.get('value')
        if value is not None and len(value) == 1:
            return value[0].get('Ref_Key')
        return None

    def __get_document_key(self, station_ref_key: str, postfix: str) -> List[Any]:
        postfix_ref = ''
        if postfix == 'пг':
            postfix_ref = self.golfstream_ref
        if postfix == 'б':
            postfix_ref = self.barrier_ref
        if postfix == 'л':
            postfix_ref = self.lyn_ref
        if postfix == 'пр':
            postfix_ref = self.pioner_ref
        if postfix == 'си':
            postfix_ref = self.si_ref
        path = self.host + (f"InformationRegister_%D0%94%D0%B8%D1%81%D0%BB%D0%BE%D0%BA%D0%B0%D1%86%D0%B8%D1%8F_RecordType/"
                       f"SliceLast?$format=json&Condition=%D0%9F%D1%83%D0%BB%D1%8C%D1%82%D0%BE%D0%B2%D0%BE%D0%B9%D"
                       f"0%9D%D0%BE%D0%BC%D0%B5%D1%80_Key%20eq%20guid%27{station_ref_key}%27")
        st = f"{self.user}:{self.password}".encode()
        resp = requests.get(path,
                            headers={"Authorization": f"Basic {b64encode(st).decode()}"})
        data = resp.json()
        if resp.status_code != 200:
            return []
        value = data.get('value')
        if value is None:
            return []
        docs = []
        for doc in value:
            if doc.get('Состояние') == 'Действует' and doc.get('Передатчик_Key') == postfix_ref:
                docs.append(doc)
        return docs

    def __get_addresses(self, document_key: str) -> str | None:
        path = self.host + f"Document_%D0%94%D0%BE%D0%B3%D0%BE%D0%B2%D0%BE%D1%80(guid'{document_key}')?$format=json"
        st = f"{self.user}:{self.password}".encode()
        resp = requests.get(path,
                            headers={"Authorization": f"Basic {b64encode(st).decode()}"})
        data = resp.json()
        if resp.status_code != 200:
            return None
        address = data.get('Адрес')
        org_key = data.get('Контрагент_Key')
        if org_key is not None:
            name = self.__get_organization_name(org_key)
            if name is not None:
                return f"{name}, {address}"
            else:
                return address
        return address