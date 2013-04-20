# -*- coding: utf8 -*-
import sublime
import sublime_plugin
import json
import datetime
from collections import defaultdict
import platform
import re
from pprint import pprint
from ordereddict import OrderedDict
# from collections import OrderedDict


class memTask(sublime_plugin.EventListener):
    def __init__(self):
        if not hasattr(self, "setting") is None:
            self.setting = {}
            settings = sublime.load_settings(__name__ + '.sublime-settings')
            self.setting['idle'] = settings.get('idle')
            self.setting['date_format'] = settings.get('date_format')

        if platform.system() == 'Windows':
            self.dirSep = "\\"
        else:
            self.dirSep = '/'

        self.setting['file_path'] = self.dirSep + "User" + self.dirSep + "memTask.json"
        self.stopTimer = True
        self.fileName = False
        self.fileView = False
        self.today = datetime.datetime.now().strftime(self.setting['date_format'])
        self.base = self.ReadBaseFromFile()
        self.TryReID()

    def TryReID(self):
        if 'id' not in self.base.itervalues().next():
            i = 0
            for path in self.base:
                self.base[path]['id'] = i
                i += 1
            self.WriteBaseToFile(self.base)

    def ElapsedTime(self):
        if self.stopTimer is False:
            timeSec = (datetime.datetime.now() - self.lastChangeTime).seconds

            if timeSec > self.setting['idle']:
                self.stopTimer = True
                return
            else:
                if self.fileName is None:
                    self.fileName = 'temp files'
                fp = self.today + self.dirSep + self.fileName
                if fp in self.base:
                    self.base[fp]["time"] = int(self.base[fp]["time"]) + int(5)
                else:
                    self.base[fp] = {
                        "time": 5,
                        "id": len(self.base),
                        "path_divider": self.dirSep
                    }
                self.SetStatus('elapsedTime', 'Elapsed time: ' + str(self.SecToHM(self.base[fp]["time"])))
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

    def on_post_save(self, view):
        self.WriteBaseToFile(self.base)

    def SetStatus(self, place, phrase):
        self.fileView.set_status(place, phrase)

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
            print 'memTask: Database file created.' + str(e)
            return data

    def WriteBaseToFile(self, data):
        json_data_file = open(sublime.packages_path() + self.setting['file_path'], "w+")
        json_data_file.write(json.dumps(data, indent=4, sort_keys=True))
        json_data_file.close()

MT = memTask()


class ShowTimeCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.ShowReportVariants()

    def IsDate(self, line):
        try:
            datetime.datetime.strptime(line, MT.setting['date_format'])
            return True
        except Exception:
            return False

    def treeify(self, seq, removeDate):
        ret = {}
        if removeDate:
            newSeq = {}
            for path in seq:
                if "\\" in path:
                    newPath = re.sub(r'^([^\\]+)\\', '', path)
                else:
                    newPath = re.sub(r'^([^/]+)/', '', path)
                if newPath in newSeq:
                    newSeq[newPath]["time"] = int(newSeq[newPath]["time"]) + seq[path]["time"]
                else:
                    newSeq[newPath] = seq[path]
            seq = newSeq

        for path in seq:
            if not hasattr(seq[path], "path_divider"):
                if "\\" in path:
                    seq[path]["path_divider"] = "\\"
                else:
                    seq[path]["path_divider"] = "/"

            seq[path]['pathArray'] = path.split(seq[path]["path_divider"])

            # Не брать файлы с временных папок
            if 'temp' not in seq[path]['pathArray'] and 'Temp' not in seq[path]['pathArray']:
                cur = ret
                for ind, node in enumerate(seq[path]['pathArray']):
                    # Если последний элемент, то нужно взять время, а не детей
                    if ind == len(seq[path]['pathArray']) - 1:
                        cur = cur.setdefault(node, {'time': seq[path]['time'], 'id': seq[path]['id']})
                    else:
                        cur = cur.setdefault(node, {})
        return ret

    def ShowGroupedBy(self, type):
        def printLine(edit, tree, level):
            forkAmount = 0
            for key, value in tree.iteritems():
                if key == 'time':
                    amount = value
                    view.insert(edit, view.size(), ' [+]')
                elif key == 'id':
                    view.insert(edit, view.size(), ' #' + str(value) + '#')
                else:
                    amount = 0
                    view.insert(edit, view.size(), "\n")
                    i = 0
                    while i < level:
                        view.insert(edit, view.size(), u"  ")
                        i += 1
                    view.insert(edit, view.size(), key)
                    tempViewSize = view.size()
                    if self.IsDate(key):
                        MT.startFolding = view.size()
                    # вот тут скорее всего дописать условие отправку ключа
                    amount = printLine(edit, tree[key], level + 1)
                    view.insert(edit, tempViewSize, ': ' + MT.SecToHM(amount))
                    forkAmount += amount
                    if self.IsDate(key):
                        if key != MT.today:
                            view.fold(sublime.Region(MT.startFolding + 7, view.size()))
            return forkAmount or amount

        view = self.window.new_file()
        view.set_syntax_file('Packages/memTask/' + __name__ + '.tmLanguage')
        Tree = lambda: defaultdict(Tree)
        tree = Tree()
        self.base = MT.ReadBaseFromFile()

        tree = self.treeify(self.base, False if type == 'date' else True)

        # tree = OrderedDict(sorted(tree.items(), key=lambda k: datetime.datetime.strptime(k[0][:10], MT.setting['date_format'])))
        if type == 'date':
            tree = OrderedDict(sorted(tree.items(), key=lambda k: k[0][:10].split('.')[::-1], reverse=True))

        edit = view.begin_edit()
        printLine(edit, tree, 0)
        view.insert(edit, view.size(), "\n")
        view.set_name("all.time")

    def ShowReportVariants(self):
        self.variants = [
            ['Group time by date'],
            ['Group time by project']
        ]

        self.window.show_quick_panel(self.variants, self.VariantClick)

    def VariantClick(self, picked):
        if picked == -1:
            return

        if picked == 0:
            self.ShowGroupedBy('date')
            return

        if picked == 1:
            self.ShowGroupedBy('project')


class AddCommentCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        line = self.view.line(self.view.sel()[0])
        self.view.insert(edit, self.view.sel()[0].b, '\n')
        print line
