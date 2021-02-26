import sqlite3
import sys
from datetime import datetime
from os import listdir, path, startfile, remove

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QTableWidgetItem, QAbstractItemView, QInputDialog
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QMessageBox

DEFAULT_REQUEST = "SELECT * FROM photos"


class TagOrganizer(QMainWindow):
    def __init__(self):  # Инициализация приложения
        super().__init__()
        uic.loadUi("proj.ui", self)

        # Инициализация флагов и переменных для дальнейшей работы
        self.conn = None  # БД
        self.cursor = None  # курсор к БД
        self.directory = None  # путь к папке с изображеними
        self.show_side_panel = True  # Показывать ли боковую панель
        self.exclude_search = False  # Настройка поиска: исключающий поиск
        self.exact_search = False  # Настройка поиска: точный поиск
        self.search_any = False  # Настройка поиска: искать любые вхождения
        self.selected = []  # Список выделенных строк
        self.last_request = DEFAULT_REQUEST  # Последний запрос

        self.connect()

    def connect(self):  # Подключение элементов

        # Подключение элементов menuBar
        self.new_file.triggered.connect(self.create_file)
        self.open_file.triggered.connect(self.open)
        self.close_file.triggered.connect(self.close)
        self.show_side_panel_action.toggled.connect(self.change_flags)
        self.add_tag_action.triggered.connect(self.add_tag)
        self.edit_tag_action.triggered.connect(self.edit_tag)
        self.clear_from_tags_action.triggered.connect(self.clear_db)
        self.delete_file_action.triggered.connect(self.delete_db)
        self.delete_tag_action.triggered.connect(self.delete_tag)
        self.delete_all_tags_action.triggered.connect(self.delete_all_tags)
        self.about.triggered.connect(self.open_about)
        self.update_file.triggered.connect(self.update_db)

        # Подключение кнопок и таблицы
        self.btns1.clicked.connect(self.quick_search)
        self.keysearch.editingFinished.connect(self.quick_search)
        self.table.itemSelectionChanged.connect(self.toggle_tag_editor)
        self.table.cellDoubleClicked.connect(self.open_image)

        # Подключение редактора тегов
        self.btn_save_tags.clicked.connect(self.add_tags_to_image)
        self.line_with_tags.editingFinished.connect(self.add_tags_to_image)
        self.add_from_existing.activated.connect(self.add_tags_from_existing)

        # Подключение параметров поиска
        self.exact_checkbox.stateChanged.connect(self.change_flags)
        self.excluding_checkbox.stateChanged.connect(self.change_flags)
        self.checkbox_search_any.stateChanged.connect(self.change_flags)

    def create_file(self):  # Создает новый каталог тегов в выбранной папке с фотографиями
        self.directory = QFileDialog.getExistingDirectory(self, "Выберите папку с изображениями")
        if self.directory == "":  # Если нажата кнопка отмены, ничего не делать
            return
        if "tags.db" in listdir(self.directory):  # Ошибка, если в папке уже есть каталог тегов
            self.get_err("Каталог тегов уже существует в этой папке!")
            return
        self.conn = sqlite3.connect(self.directory + "\\tags.db")  # создание каталога тегов
        self.cursor = self.conn.cursor()
        self.create_table()  # Его заполнение
        self.update_table(DEFAULT_REQUEST)

    def open(self):  # Открывает существующий каталог тегов
        self.directory = QFileDialog.getExistingDirectory(self, "Выберите папку с фотографиями")
        if self.directory == "":  # Если нажата кнопка отмены, ничего не делать
            return
        if "tags.db" not in listdir(self.directory):  # Ошибка, если в папке нет каталога тегов
            self.get_err("Каталога тегов нет в этой папке!")
            return
        self.conn = sqlite3.connect(self.directory + "\\tags.db")  # подключение к каталогу тегов
        self.cursor = self.conn.cursor()
        self.update_table(DEFAULT_REQUEST)

    def create_table(self):  # Создание и заполнение самой таблицы
        if self.dir_is_empty():
            return
        # Создание списка тегов
        self.cursor.execute("""CREATE TABLE tags
                                (id integer PRIMARY KEY AUTOINCREMENT NOT NULL, tag text)""")
        # Создание таблицы с изображениями
        self.cursor.execute("""CREATE TABLE photos
                                (id integer, name text, 
                                tags text, date text, size text)""")
        photos = []
        s = listdir(self.directory)
        k = 0
        for i in s:
            if any([j in i for j in [".bmp", ".jpg", ".jpeg", ".png", ".gif"]]):
                p = self.directory + "\\" + i
                # Обновление индекса, имени, расширения файла, даты создания файла и
                # размера файла в килобайтах
                photos.append((
                    k, i, "", datetime.fromtimestamp(path.getctime(p)).strftime('%d.%m.%Y'),
                    str(round(path.getsize(p) / 1024, 1)) + " КБ"))
                k += 1
        self.cursor.executemany("""INSERT INTO photos VALUES (?,?,?,?,?)""", photos)
        self.conn.commit()

    def update_table(self, to_do):  # Обновляет таблицу в соответствии с фильтрами
        items = self.cursor.execute(to_do).fetchall()  # Выбор из фильтра
        self.table.setRowCount(len(items))  # Подготовка таблицы
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Имя", "Теги", "Дата создания", "Размер"])
        for i in range(len(items)):  # Заполнение таблицы
            for j in range(4):
                fl = 1  # Пропуск id изображения
                if j == 1 and items[i][j + fl] != "":  # Замена номеров тегов на их названия
                    tags = tuple(map(int, items[i][j + fl].split(",\n")))
                    try:
                        if len(tags) == 1:
                            tags = ",\n".join(list(zip(*self.cursor.execute(
                                f"SELECT tag FROM tags WHERE id = {str(tags[0])}").fetchall()))[0])
                        else:
                            tags = ",\n".join(list(zip(*self.cursor.execute(
                                f"SELECT tag FROM tags WHERE id IN {str(tags)}").fetchall()))[0])
                        self.table.setItem(i, j, QTableWidgetItem(tags))
                    except Exception as e:
                        print(e)
                else:
                    self.table.setItem(i, j, QTableWidgetItem(items[i][j + fl]))
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Запрет на edit
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)  # Построчный выбор
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

    def close(self):  # Закрытие каталога и очистка виджетов
        if self.directory is None:
            return
        self.conn.close()  # Отключение от БД
        self.table.clear()  # Очистка таблицы
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.tag_editor.setMaximumHeight(0)  # "Сворачивание" редактора тегов
        self.selected = []
        self.directory = None
        self.last_request = DEFAULT_REQUEST

    def quick_search(self):  # Быстрый поиск
        if self.conn is None:
            self.get_err("Каталог тегов не выбран!")
            return
        # Переменная создается как список для дальнейшего объединения
        # алгоритмов обычного и точного поиска.
        keys = [self.keysearch.text()]
        # Если не включена функция точного поиска, поиск проводится по отдельным словам
        if not self.exact_search:
            keys = keys[0].split(" ")

        # Изменение поиска в соответствии с отмеченными галочками
        any_or_only = " OR " * self.search_any + " AND " * (not self.search_any)
        exclude_or_not = " NOT" * self.exclude_search
        link = " AND " * self.exclude_search + " OR " * (not self.exclude_search)

        # Создание запроса
        s = ["name", "date", "size"]
        # Все это нагромождение - следствие использования id тегов вместо их названий в таблице.
        # Памяти используется меньше, но существует вот это:
        ids = [self.cursor.execute(f"SELECT id FROM tags WHERE tag LIKE \'%{i}%\'").fetchall()
               for i in keys]
        delete = []
        for i in range(len(ids)):
            if len(ids[i]) == 0:
                delete.append(i)
            else:
                ids[i] = f"%\'{link}tags{exclude_or_not} LIKE \'%".join(
                    list(map(str, list(zip(*ids[i]))[0])))
        for i in range(len(delete)):
            ids.pop(delete[i] - i)
        tag_requests = [f"{link}(tags{exclude_or_not} LIKE \'%{i}%\')" for i in ids]
        tag_requests.extend([""] * (len(keys) - len(tag_requests)))

        # Начало сборки самого запроса
        request = "SELECT * FROM photos WHERE "
        request += any_or_only.join(["(" + link.join([f"{j}{exclude_or_not} "
                                                      f"LIKE \'%{keys[i]}%\'" for j in s]) +
                                     tag_requests[i] + ")" for i in range(len(keys))])
        self.update_table(request)
        self.last_request = request

    def change_flags(self):  # Изменение флагов в соответствии с настройками

        # Чекбокс "Точное совпадение"
        if self.sender() == self.exact_checkbox:
            self.exact_search = not self.exact_search
            # Если включен точный поиск, отключаем поиск любых вхождений
            self.checkbox_search_any.setCheckState(False)
            self.checkbox_search_any.setDisabled(self.exact_search)
            self.search_any = False

        # Чекбокс "Исключающий поиск"
        elif self.sender() == self.excluding_checkbox:
            self.exclude_search = not self.exclude_search
            # Здесь же наоборот, нужно включить поиск любых вхождений
            self.checkbox_search_any.setCheckState(self.exclude_search * 2)
            self.checkbox_search_any.setDisabled(self.exclude_search)
            self.search_any = False

        # Чекбокс "Искать любые вхождения"
        elif self.sender() == self.checkbox_search_any:
            self.search_any = not self.search_any

        # Вид->Боковая панель
        elif self.sender() == self.show_side_panel_action:
            # "Сворачивание/разворачивание" вкладки поиска
            self.show_side_panel = not self.show_side_panel
            self.search_tab.setMaximumWidth(16777215 * self.show_side_panel)
            # Поскольку не было времени делать отдельное окно с изменением тегов,
            # появился такой костыль
            self.search_tab.setVisible(self.show_side_panel)
            self.tag_editor.setMaximumWidth(16777215 * self.show_side_panel)

    def update_db(self):  # Проверка папки на новые/удаленные изображения
        # Дисклеймер: программа не может отследить переименовывание/редактирование,
        # Поэтому она просто удаляет у переименованных файлов теги. Вотаквот
        if self.dir_is_empty():
            return
        msg = QMessageBox(self)
        msg.setText("При обновлении данные об удаленных фотографиях сотрутся!")
        msg.setInformativeText("Подтвердить изменения?")
        msg.addButton("Обновить", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        res = msg.exec()
        if res == QMessageBox.ButtonRole.AcceptRole:
            s1 = list(listdir(self.directory))
            s2 = list(list(zip(*self.cursor.execute("SELECT name FROM photos").fetchall()))[0])
            k = 0
            for i in range(len(s2)):
                if s2[i - k] in s1:
                    s1.remove(s2.pop(i - k))
                    k += 1
            for i in s2:
                self.cursor.execute(f"DELETE FROM photos WHERE name = \'{i}\'")
            s1 = list(filter(lambda x: any([j in x for j in [".bmp", ".jpg", ".jpeg",
                                                             ".png", ".gif"]]), s1))
            photos = []
            for i in s1:
                p = self.directory + "/" + i
                photos.append((k, i, "",
                              datetime.fromtimestamp(path.getctime(p)).strftime('%d.%m.%Y'),
                              str(round(path.getsize(p) / 1024, 1)) + " КБ"))
            self.cursor.executemany("""INSERT INTO photos VALUES (?,?,?,?,?)""", photos)
            self.conn.commit()
            self.update_table(self.last_request)

    def toggle_tag_editor(self):  # Открытие/закрытие редактора тегов для выбранного изображения
        # Создание списка выделенных строк
        self.selected = [(self.table.selectedItems()[i].row(),)
                         for i in range(0, len(self.table.selectedItems()), 4)]
        if len(self.selected) == 1:
            line = self.table.item(self.selected[0][0], 1).text()
            line = " ".join(line.split("\n"))
        else:
            line = ""
        self.line_with_tags.setText(line)
        self.tag_editor.setMaximumHeight(16777215 * bool(self.selected))
        # Вписывание тегов в combobox
        self.update_add_combobox()

    def add_tags_to_image(self):  # Добавление тегов в строки, новых тегов в существующие
        try:
            text = self.line_with_tags.text().split(", ")  # Превращение текста в список тегов
            s = list(map(lambda x: (self.table.item(x[0], 0).text(),), self.selected))
            if text == [""]:
                self.cursor.executemany(f"UPDATE photos SET tags = \'\' WHERE name = ?", s)
            else:
                used_tags = []
                for i in range(len(text)):
                    used_tags.extend(text[i].split(","))
                existing = self.cursor.execute("SELECT tag FROM tags").fetchall()
                used_tags = list(zip(used_tags))
                if any([len(i[0]) < 3 for i in used_tags]):
                    self.get_err("Тег не может быть короче трех символов!")
                    return
                # Добавление новых тегов в каталог тегов
                new_tags = list(filter(lambda x: x not in existing, used_tags))
                self.cursor.executemany("INSERT INTO tags(tag) VALUES(?)", new_tags)
                # Добавление тегов в строки
                used_tags = list(zip(*used_tags))[0]
                used_tags = [str(self.cursor.execute(
                    f"SELECT id FROM tags WHERE tag = \'{i}\'").fetchone()[0]) for i in used_tags]
                used_tags = ",\n".join(used_tags)
                self.cursor.executemany(f"UPDATE photos SET tags = \'{used_tags}\' "
                                        f"WHERE name = ?", s)
            self.conn.commit()
            self.update_table(self.last_request)
            self.update_add_combobox()
        except Exception as e:
            print(e)

    def add_tags_from_existing(self):  # Функция вставки тегов из уже использованных
        if self.add_from_existing.currentText() == "Добавить из существующих...":
            return

        if self.add_from_existing.currentText() not in self.line_with_tags.text().split(", "):
            s = self.line_with_tags.text()
            if s == "":
                self.line_with_tags.setText(self.add_from_existing.currentText())
            else:
                if s[-2:] == ", ":
                    s = s[:-2]
                elif s[-1] in (" ", ","):
                    s = s[:-1]
                self.line_with_tags.setText(s + ", " + self.add_from_existing.currentText())

    def add_tag(self):  # Добавление тега в существующие
        if self.dir_is_empty():
            return
        tag = QInputDialog.getText(self, "Добавить тег", "")[0]
        if "," in tag:
            self.get_err("Тег не может содержать запятую!")
            return
        elif (tag,) in self.cursor.execute("SELECT tag FROM tags").fetchall():
            self.get_err("Данный тег уже существует!")
            return
        elif len(tag) < 3:
            self.get_err("Тег не может быть короче трех символов!")
            return
        self.cursor.execute(f"INSERT INTO tags(tag) VALUES(\'{tag}\')")
        self.conn.commit()
        self.update_add_combobox()

    def edit_tag(self):  # Изменение существующего тега
        if self.dir_is_empty():
            return
        s = self.cursor.execute("SELECT tag FROM tags").fetchall()
        if not s:
            self.get_err("В этом каталоге нет существующих тегов!")
            return
        tag = QInputDialog.getItem(self, "Изменить тег", "Выберите тег:",
                                   list(zip(*s))[0], editable=False)
        if not tag[1]:
            return
        tag = tag[0]
        new_tag = QInputDialog.getText(self, "Изменить тег", tag + " - ")
        if not new_tag[1]:
            return
        new_tag = new_tag[0]
        if len(new_tag) < 3:
            self.get_err("Тег не может быть короче трех символов!")
            return
        self.cursor.execute(f"UPDATE tags SET tag = \'{new_tag}\' WHERE tag = \'{tag}\'")
        self.update_table(self.last_request)

    def get_err(self, s):  # Функция, открывающая окно с описанием ошибки
        err = QMessageBox(self)
        err.setText(s)
        err.exec()

    def dir_is_empty(self):
        if self.directory is None:
            self.get_err("Каталог тегов не выбран!")
            return True
        return False

    def open_image(self):  # Открытие изображения в просмотровщике Windows
        image_path = self.directory + "/" + self.table.selectedItems()[0].text()
        try:
            startfile(image_path)
        except FileNotFoundError:
            self.get_err("Файл не найден!")

    def update_add_combobox(self):  # Обновление "Добавить существующие теги"
        s = self.cursor.execute("SELECT tag FROM tags").fetchall()
        for i in s:
            if self.add_from_existing.findText(i[0]) == -1:
                self.add_from_existing.addItem(i[0])
        remove_list = []
        for i in range(self.add_from_existing.count()):
            if self.add_from_existing.itemText(i) != "Добавить из существующих...":
                if (self.add_from_existing.itemText(i),) not in s:
                    remove_list.append(i)
        for i in range(len(remove_list)):
            self.add_from_existing.removeItem(remove_list[i] - i)

    def confirm_delete(self, lbl):  # Предупреждение об удалении чего-либо
        msg = QMessageBox(self)
        msg.setText(lbl)
        msg.setInformativeText("Подтвердить изменения?")
        msg.addButton("Удалить", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        res = msg.exec()
        if res == QMessageBox.ButtonRole.AcceptRole:  # Возвращать, приняты ли изменения
            return True
        else:
            return False

    def delete_tag(self):  # Удаление выбранного тега
        if self.dir_is_empty():
            return
        s = self.cursor.execute("SELECT tag FROM tags").fetchall()
        if not s:
            self.get_err("В этом каталоге нет существующих тегов!")
            return
        tag = QInputDialog.getItem(self, "Удалить тег", "Выберите тег:",
                                   list(zip(*s))[0], editable=False)
        if not tag[1]:
            return
        tag = tag[0]
        if not self.confirm_delete("Это дейстие безвозвратно удалит тег из каталога!"):
            return
        # Нахождение id тега
        tag_id = self.cursor.execute(f"SELECT id FROM tags WHERE tag = \'{tag}\'").fetchone()[0]
        # Нахождение строк с тегом
        s = self.cursor.execute(f"SELECT id FROM photos WHERE tags LIKE "
                                f"\'%{str(tag_id)}%\'").fetchall()
        if s:
            for i in list(zip(*s))[0]:  # Проход по строкам и удаление тега
                prev_tags = self.cursor.execute(f"SELECT tags FROM photos WHERE "
                                                f"id = {str(i)}").fetchone()[0].split(",\n")
                curr_tags = ",\n".join(prev_tags[:prev_tags.index(str(tag_id))] +
                                       prev_tags[prev_tags.index(str(tag_id)) + 1:])
                self.cursor.execute(f"UPDATE photos SET tags = \'{curr_tags}\' "
                                    f"WHERE id = {str(i)}")
        self.cursor.execute(f"DELETE FROM tags WHERE id = \'{str(tag_id)}\'")  # Собственно удаление
        self.conn.commit()
        self.update_table(self.last_request)
        self.update_add_combobox()

    def clear_db(self):  # Очистка фотографий от тегов
        if self.dir_is_empty():
            return
        if self.confirm_delete("Это действие очистит от тегов все фотографии!"):
            self.cursor.execute("UPDATE photos SET tags = \'\'")
            self.conn.commit()
            self.update_table(self.last_request)
            return True
        return False

    def delete_all_tags(self):  # Удаление всех тегов
        if self.clear_db():
            self.cursor.execute("DELETE from tags")
            self.conn.commit()
            self.update_add_combobox()

    def delete_db(self):  # Удаление каталога
        if self.dir_is_empty():
            return
        if self.confirm_delete("Это действие удалит весь каталог и теги в нем!"):
            directory = self.directory  # Сама директория становится None
            self.close()
            remove(directory + "/tags.db")

    def open_about(self):  # Открытие минипаспорта
        try:
            startfile("about.txt")
        except FileNotFoundError:
            self.get_err("Файл не найден!")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = TagOrganizer()
    ex.show()
    sys.exit(app.exec())
