#!/usr/bin/env python3

import sqlite3
from systemd import journal
from datetime import datetime
from operator import itemgetter
import npyscreen
import subprocess

class TLDatabase(object):
    '''Создает и наполняет базу данных записями терминальных сессий tlog'''
    def __init__(self, filename="tldatabase.db"):
        self.dbfilename = filename
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute(
        "CREATE TABLE IF NOT EXISTS tlrecords\
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

    def add_record(self):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        
        j = journal.Reader()
        j.add_match('SYSLOG_IDENTIFIER=-tlog-rec-session')
        #j.add_match('_EXE=/usr/bin/tlog-rec-session')
        #Инициализируем пустой список для хранения словарей
        tlog_messages = []
        #Инициализируем пустой список для хранения TLOG_REC
        tlog_rec = []
        for entry in j:
            #Инициализируем пустой словарь для добавления в список
            tlog_journal = {}
            #Добавляем полученные значения в словарь
            tlog_journal['date'] = entry['_SOURCE_REALTIME_TIMESTAMP'].strftime('%d.%m.%G')
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
        tlog_messages = sorted(tlog_messages, key=itemgetter('date', 'hostname'))
        #Добавялем 10 записей
        for tlog_message in tlog_messages:
            c.execute('INSERT INTO tlrecords(rec, tl_date, tl_time, user, hostname, message) \
                        VALUES(?,?,?,?,?,?)', (tlog_message['rec'], tlog_message['date'], tlog_message['time'], tlog_message['user'], tlog_message['hostname'], tlog_message['message']))
            db.commit()
        c.close()

    def play_record(self, record_id):
        #Извлекаем из записи rec для передачи в качестве аргумента tlog-play
        #db = sqlite3.connect(self.dbfilename)
        #c = db.cursor()
        #c.execute('SELECT rec FROM tlrecords WHERE tl_id=?', (record_id,))
        #records = c.fetchall()
        #c.close()
        result = subprocess.run('tlog-play -r journal -M TLOG_REC=988df62917e04505a13d43616712ce65-13b630-15f7fee6', shell=True)

    def list_all_records(self):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('SELECT tl_id, user, tl_date, tl_time, hostname FROM tlrecords')
        records = c.fetchall()
        c.close()
        return records
        #print(records)

    def get_record(self, record_id):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('SELECT rec, user, tl_date, tl_time, hostname FROM tlrecords WHERE tl_id=?', (record_id,))
        records = c.fetchall()
        c.close()
        return records[0]

class RecordList(npyscreen.MultiLineAction):
    def __init__(self, *args, **keywords):
        super(RecordList, self).__init__(*args, **keywords)
        self.add_handlers({
            "^A": self.when_add_record,
        })
    
    def display_value(self, vl):
        vl_records = f"{vl[1]}\t\t\t\t\t\t\t\t\t\t\t{vl[2]}\t\t\t\t\t{vl[3]}\t\t\t\t\t{vl[4]}"
        return vl_records

    def actionHighlighted(self, act_on_this, keypress):
        self.parent.parentApp.getForm('EDITRECORDFM').value =act_on_this[0]
        self.parent.parentApp.switchForm('EDITRECORDFM')

    def when_add_record(self, *args, **keywords):
        self.parent.parentApp.getForm('EDITRECORDFM').value = None
        self.parent.parentApp.switchForm('EDITRECORDFM')

class RecordListDisplay(npyscreen.FormMutt):
    MAIN_WIDGET_CLASS = RecordList
    def beforeEditing(self):
        self.update_list()

    def update_list(self):
        self.wStatus1.value = "Воспроизведение терминальных сессий tlog"
        self.wCommand.value = 'Для выхода нажмите Ctrl+C'
        self.wMain.values = self.parentApp.myDatabase.list_all_records()
        self.wMain.display()

class EditRecord(npyscreen.ActionForm):
    def create(self):
        self.value = None

    def beforeEditing(self):
        record = self.parentApp.myDatabase.get_record(self.value)
        self.record_id          = '1'

    def on_ok(self):
        self.parentApp.myDatabase.play_record(self.record_id)
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()

class TLApplication(npyscreen.NPSAppManaged):
    def onStart(self):
        self.myDatabase = TLDatabase()
        self.addForm("MAIN", RecordListDisplay)
        self.addForm("EDITRECORDFM", EditRecord)
    def on_ok(self):
        self.parentApp.setNextForm(None)

if __name__ == '__main__':
    try:
        myApp = TLApplication()
        myApp.run()
    except KeyboardInterrupt:
        pass


#mydb = TLDatabase()
#mydb.add_record()
