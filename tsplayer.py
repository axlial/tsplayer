#!/usr/bin/env python3

import sqlite3
from systemd import journal
from datetime import datetime
from operator import itemgetter
import npyscreen
import subprocess

class TLDatabase(object):
    '''Извлекает из базы данных записи терминальных сессий tlog'''
    def __init__(self, filename="/var/db/tldatabase.db"):
        self.dbfilename = filename

    def list_all_records(self):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('SELECT tl_id, user, tl_date, tl_time, hostname FROM tlrecords ORDER BY tl_date DESC, tl_time DESC')
        records = c.fetchall()
        c.close()
        return records

        
    def create_sqltable(self, start_date, end_date):
        #Метод используется для хранения отфильтрованных по дате записей
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        #Очищаем таблицу от записей
        c.execute("DELETE FROM tmprecords")
        #Вставляем записи
        c.execute('INSERT INTO tmprecords (tl_id, rec, tl_date, tl_time, user, message, hostname) SELECT tl_id, rec, tl_date, tl_time, user, message, hostname FROM tlrecords WHERE tl_date BETWEEN ? AND ?', (start_date, end_date))
        db.commit()
        c.close()
        
    def list_tmp_records(self):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        #Поиск записей по диапазону дат
        c.execute('SELECT tl_id, user, tl_date, tl_time, hostname FROM tmprecords ORDER BY tl_date DESC, tl_time DESC')
        records = c.fetchall()
        c.close()
        return records

    def get_record(self, record_id):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('SELECT tl_id, rec, hostname, user, tl_date, tl_time, message FROM tlrecords WHERE tl_id=?', (record_id,))
        records = c.fetchall()
        c.close()
        return records[0]

    def play_record(self, rec_id):
        tlog_rec = f'TLOG_REC={rec_id}'
        result = subprocess.run(['tlog-play', '-r', 'journal', '-M', tlog_rec])

class RecordList(npyscreen.MultiLineAction):
    def __init__(self, *args, **keywords):
        super(RecordList, self).__init__(*args, **keywords)
        self.add_handlers({
            "^S": self.when_search_record,
            "^R": self.when_reset_record,
            "^Q": self.exit_func
        })

    def display_value(self, vl):
        #форматируем отображаемый текст
        vl_records = f"{vl[1]:<20} {vl[2]:<15} {vl[3]:<15} {vl[4]:<15}"
        return vl_records

    def actionHighlighted(self, act_on_this, keypress):
        self.parent.parentApp.getForm('EDITRECORDFM').value =act_on_this[0]
        self.parent.parentApp.switchForm('EDITRECORDFM')

    def when_add_record(self, *args, **keywords):
        self.parent.parentApp.getForm('EDITRECORDFM').value = None
        self.parent.parentApp.switchForm('EDITRECORDFM')

    def actionSearch(self, act_on_this, keypress):
        self.parent.parentApp.getForm('SEARCHRECORDFM').value =act_on_this[0]
        self.parent.parentApp.switchForm('SEARCHRECORDFM')

    def when_search_record(self, *args, **keywords):
        self.parent.parentApp.getForm('SEARCHRECORDFM').value = None
        self.parent.parentApp.switchForm('SEARCHRECORDFM')
    
    def when_reset_record(self, *args, **keywords):
        #Если пользователь нажал ^R переходим на форму MAIN  
        self.parent.parentApp.switchForm("MAIN")
    
    def exit_func(self, _input):
        exit(0)

class RecordListDisplay(npyscreen.FormMutt):
    MAIN_WIDGET_CLASS = RecordList
    def beforeEditing(self):
        self.update_list()

    def update_list(self):
        self.wStatus1.value = "[ Воспроизведение терминальных сессий tlog ]"
        self.wStatus2.value = '[ ^S Установить фильтр ] [ ^R Сбросить фильтр ] [ ^Q Выход ]'
        self.wMain.values = self.parentApp.myDatabase.list_all_records()
        self.wMain.display()

class SearchListDisplay(npyscreen.FormMutt):
    MAIN_WIDGET_CLASS = RecordList
    def beforeEditing(self):
        self.update_list()

    def update_list(self):
        self.wStatus1.value = "[ Воспроизведение терминальных сессий tlog ]"
        self.wStatus2.value = '[ ^S Установить фильтр ] [ ^R Сбросить фильтр ] [ ^Q Выход ]'

        self.wMain.values = self.parentApp.myDatabase.list_tmp_records()
        self.wMain.display()

class EditRecord(npyscreen.ActionForm):
    def create(self):
        self.value = None
        self.wgrecid = self.add(npyscreen.TitleText, name = "RecID", editable=False)
        self.wghostname = self.add(npyscreen.TitleText, name = "Hostname", editable=False)
        self.wguser = self.add(npyscreen.TitleText, name = "User", editable=False)
        self.wgdate = self.add(npyscreen.TitleText, name = "Date", editable=False)
        self.wgtime = self.add(npyscreen.TitleText, name = "Time", editable=False)
        self.wgmessage = self.add(npyscreen.TitleText, name = "Message")
        self_check = self.add(npyscreen.FixedText, value = "")
        self_check = self.add(npyscreen.FixedText, value = 'Для воспроизведения записи нажмите ОК', editable=False)
        self_check = self.add(npyscreen.FixedText, value = "Для возврата на главный экран нажмите Cancel", editable=False)
        self_check = self.add(npyscreen.FixedText, value = "")
        self_check = self.add(npyscreen.FixedText, value = "")
        self_check = self.add(npyscreen.FixedText, value = "")
        self_check = self.add(npyscreen.FixedText, value = "Воспроизведением можно управлять с помощью следующих клавиш:", editable=False)
        self_check = self.add(npyscreen.FixedText, value = "")
        self_check = self.add(npyscreen.FixedText, value = "SPACE, p - пауза/возобновление воспроизведение", editable=False)
        self_check = self.add(npyscreen.FixedText, value = "} - увеличить вдвое скорость воспроизведения, максимум 16x", editable=False)
        self_check = self.add(npyscreen.FixedText, value = "{ - уменьшить скорость воспроизведения, минимум 1/16x", editable=False)
        self_check = self.add(npyscreen.FixedText, value = "BACKSPACE - сбросить скорость воспроизведения до нормальной 1x", editable=False)
        self_check = self.add(npyscreen.FixedText, value = ". - пропустить паузу во время воспроизведения (пользователь авторизовался, но не производит никаких действий)", editable=False)
        self_check = self.add(npyscreen.FixedText, value = "G - перемотка записи. 30G - перемотка на 30 секунд. 30:G - перемотка на 30 минут. 120:G - перемотка на 2 часа", editable=False)
        heck = self.add(npyscreen.FixedText, value = "q - остановить воспроизведение и выйти", editable=False)

    def beforeEditing(self):
        record = self.parentApp.myDatabase.get_record(self.value)
        self.name = "Текущая запись: %s" % record[0]
        self.record_id = record[0]
        self.rec_id = record[1]
        self.wgrecid.value = record[1]
        self.wghostname.value = record[2]
        self.wguser.value = record[3]
        self.wgdate.value  = record[4]
        self.wgtime.value      = record[5]
        self.wgmessage.value = f'{record[6]:10}'

    def on_ok(self):
        self.erase()
        self.parentApp.myDatabase.play_record(self.rec_id)
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()

class SearchRecord(npyscreen.ActionForm):
    def create(self):
        self.value = None
        self.wgstart_date = self.add(npyscreen.TitleText, name = "Дата начала:")
        self.wgend_date = self.add(npyscreen.TitleText, name = "Дата окончания:")
        self_check = self.add(npyscreen.FixedText, value = "Формат даты YYYY-MM-DD", editable=False)

    def beforeEditing(self):
        self.name = "Установка фильтра по дате"
        self.wgstart_date.value = ''
        self.wgend_date.value = ''

    def on_ok(self):
        self.parentApp.myDatabase.create_sqltable(start_date=self.wgstart_date.value, end_date=self.wgend_date.value)
        #Переходим в другую форму    
        self.parentApp.setNextForm("SLD")    

    def on_cancel(self):
        self.parentApp.switchFormPrevious()

class TLApplication(npyscreen.NPSAppManaged):
    def onStart(self):
        npyscreen.setTheme(npyscreen.Themes.ElegantTheme)
        self.myDatabase = TLDatabase()
        self.addForm("MAIN", RecordListDisplay)
        self.addForm('SLD', SearchListDisplay)
        self.addForm("EDITRECORDFM", EditRecord)
        self.addForm("SEARCHRECORDFM", SearchRecord)

    def on_ok(self):
        self.parentApp.setNextForm(None)

if __name__ == '__main__':
    try:
        myApp = TLApplication()
        myApp.run()
    except KeyboardInterrupt:
        pass

