# -*- coding: utf8 -*-
import sublime
import sublime_plugin
import json
import datetime
from pprint import pprint
from collections import defaultdict


class memTask(sublime_plugin.EventListener):
    def __init__(self):
        if not hasattr(self, "setting") is None:
            self.setting = {}
            settings = sublime.load_settings(__name__ + '.sublime-settings')
            self.setting['idle'] = settings.get('idle')
            self.setting['file_path'] = settings.get('file_path')

        self.stopTimer = True
        self.fileName = False
        self.fileView = False
        self.base = self.ReadBaseFromFile()

    def ElapsedTime(self):
        if self.stopTimer is False:
            timeSec = (datetime.datetime.now() - self.lastChangeTime).seconds

            if timeSec > self.setting['idle']:
                self.stopTimer = True
                return
            else:
                if self.fileName in self.base:
                    self.base[self.fileName]["time"] = int(self.base[self.fileName]["time"]) + int(5)
                    self.WriteBaseToFile(self.base)
                else:
                    self.base[self.fileName] = {"time": 5}
                self.SetStatus('elapsedTime', 'Elapsed time: ' + str(self.SecToHM(self.base[self.fileName]["time"])))
                self.WriteBaseToFile(self.base)
                sublime.set_timeout(self.ElapsedTime, 5000)
        else:
            self.EraseStatus('elapsedTime')

    def on_modified(self, view):
        self.lastChangeTime = datetime.datetime.now()
        if self.fileName is False or self.fileName is None:
            self.fileName = view.file_name()
        if self.fileView is False or self.fileView is None:
            self.fileView = view
        if self.stopTimer is True:
            self.stopTimer = False
            self.ElapsedTime()

    def on_activated(self, view):
        self.fileName = view.file_name()
        self.fileView = view

    def SetStatus(self, place, phrase):
        self.fileView.set_status(place, phrase)
        # def setstatus():
        #     window = sublime.active_window()
        #     if window is not None:
        #         view = sublime.active_window().active_view()
        #         view.set_status(place, phrase)
        # sublime.set_timeout(setstatus, 2000)

    def EraseStatus(self, place):
        for view in sublime.active_window().views():
            view.erase_status(place)

    def SecToHM(self, seconds):
        hours = seconds / 3600
        seconds -= 3600 * hours
        minutes = seconds / 60
        return "%02d:%02d" % (hours, minutes)

    def ReadBaseFromFile(self):
        try:
            with open(sublime.packages_path() + self.setting['file_path'], "r") as json_data:
                data = json.load(json_data)
                json_data.close()
                return data
        except IOError as e:
            self.WriteBaseToFile({})
            data = {}
            print 'Redmine: Database file created.' + str(e)
            return data

    def WriteBaseToFile(self, data):
        json_data_file = open(sublime.packages_path() + self.setting['file_path'], "w+")
        json_data_file.write(json.dumps(data, indent=4, sort_keys=True))
        json_data_file.close()

MT = memTask()


class TimeFileEvents(sublime_plugin.EventListener):
    def on_close(self, view):
        print 1


class ShowTimeCommand(sublime_plugin.WindowCommand):
    def run(self):
        # Может стоит файл все же сразу куда нить сохранять
        view = self.window.new_file()
        view.set_syntax_file('Packages/Redmine/' + __name__ + '.tmLanguage')
        Tree = lambda: defaultdict(Tree)
        tree = Tree()
        base = MT.ReadBaseFromFile()

        TimeFileEvents()

        def treeify(seq):
            ret = {}
            for path in seq:
                seq[path]['pathArray'] = path.split('\\')
                # Не брать файлы с временных папок
                if 'temp' not in seq[path]['pathArray'] and 'Temp' not in seq[path]['pathArray']:
                    cur = ret
                    for ind, node in enumerate(seq[path]['pathArray']):
                        # Если последний элемент, то нужно взять время, а не детей
                        if ind == len(seq[path]['pathArray']) - 1:
                            cur = cur.setdefault(node, {'time': seq[path]['time']})
                        else:
                            cur = cur.setdefault(node, {})
            return ret

        tree = treeify(base)

        def printLine(edit, tree, level):
            forkAmount = 0
            for key, value in tree.iteritems():
                amount = 0
                view.insert(edit, view.size(), "\n")
                i = 0
                while i < level:
                    view.insert(edit, view.size(), u"  ")
                    i += 1
                # Сделать function style вывод
                view.insert(edit, view.size(), key)
                tempViewSize = view.size()
                if key == 'time':
                    amount = value
                    view.insert(edit, view.size(), ': ' + MT.SecToHM(value))
                else:
                    amount = printLine(edit, tree[key], level + 1)
                    view.insert(edit, tempViewSize, ': ' + MT.SecToHM(amount))
                    forkAmount += amount
            return forkAmount or amount

        edit = view.begin_edit()
        printLine(edit, tree, 0)
        view.set_name("all.time")