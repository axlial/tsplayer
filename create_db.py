#!/usr/bin/env python3

import sqlite3
from systemd import journal
from datetime import datetime
from operator import itemgetter

class TPDatabase():
    '''Создает и наполняет базу данных записями терминальных сессий tlog'''
    def __init__(self, filename="tldatabase.db"):
        self.dbfilename = filename
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute("DROP TABLE IF EXISTS tlrecords")
        c.execute(
        "CREATE TABLE tlrecords \
            ( tl_id INTEGER PRIMARY KEY, \
              rec     TEXT, \
              tl_date TEXT, \
              tl_time TEXT, \
              user   TEXT, \
              message TEXT, \
              hostname TEXT \
              )" \
            )
        #Создаем таблицу для хранения отфильтрованных по датам записей    
        c.execute(
        "CREATE TABLE IF NOT EXISTS tmprecords \
            ( tl_id INTEGER PRIMARY KEY, \
              rec     TEXT, \
              tl_date TEXT, \
              tl_time TEXT, \
              user   TEXT, \
              message TEXT, \
              hostname TEXT \
              )" \
            )
        db.commit()
        c.close()

    def create_records(self):
        j = journal.Reader(path='/var/log/journal/remote/')
        j.add_match('_COMM=tlog-rec-sessio')
        #Инициализируем пустой список для хранения словарей
        tlog_messages = []
        #Инициализируем пустой список для хранения TLOG_REC
        tlog_rec = []
        for entry in j:
            #Инициализируем пустой словарь для добавления в список
            tlog_journal = {}
            #Добавляем полученные значения в словарь
            #tlog_journal['date'] = entry['_SOURCE_REALTIME_TIMESTAMP'].strftime('%d.%m.%G')
            tlog_journal['date'] = entry['_SOURCE_REALTIME_TIMESTAMP'].strftime('%G-%m-%d')
            tlog_journal['time'] = entry['_SOURCE_REALTIME_TIMESTAMP'].strftime('%H:%M:%S')
            tlog_journal['user'] = entry['TLOG_USER']
            tlog_journal['hostname'] = entry['_HOSTNAME']
            tlog_journal['rec'] = entry['TLOG_REC']
            tlog_journal['message'] = entry['MESSAGE']

            #Добавляем словарь в список
            if tlog_journal['rec'] not in tlog_rec:
                tlog_messages.append(tlog_journal)
            #Добавляем TLOG_REC в список
            tlog_rec.append(tlog_journal['rec'])
            #Удаляем дубли из списка
            tlog_rec = list(dict.fromkeys(tlog_rec))

        #Сортируем список словарей по дате
        #tlog_messages = sorted(tlog_messages, key=itemgetter('date', 'hostname'))
        #Возвращаем список словарей
        return tlog_messages

    def insert_records(self, tlog_messages):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        for tlog_message in tlog_messages:
            c.execute('INSERT INTO tlrecords(rec, tl_date, tl_time, user, hostname, message) \
                        VALUES(?,?,?,?,?,?)', (tlog_message['rec'], tlog_message['date'], tlog_message['time'], tlog_message['user'], tlog_message['hostname'], tlog_message['message']))
            db.commit()
        c.close()

if __name__ == '__main__':
    initdb = TPDatabase()
    filename="tldatabase.db"
    tlog_messages = initdb.create_records()
    initdb.insert_records(tlog_messages)
   
