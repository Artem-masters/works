#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тренажер по командной строке Windows с графическим интерфейсом
50 интерактивных уроков по базовым командам cmd.exe
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import re
import glob
import fnmatch
import difflib
import shutil
import tempfile
import random
import base64
from datetime import datetime
import platform
import sys

# Ключи-ответы к заданиям хранятся в зашифрованном виде,
# чтобы их нельзя было просто прочитать, открыв файл в редакторе.
_KEY = b'WindowsTrainer_2024_do_not_peek!'


def _dec1(blob):
    raw = base64.b64decode(blob.encode('ascii'))
    data = bytes(b ^ _KEY[i % len(_KEY)] for i, b in enumerate(raw))
    return data.decode('utf-8')


def _steps(*blobs):
    return [_dec1(b) for b in blobs]


# Внутри зашифрованного шага допустимые варианты одной и той же команды разделены
# этим символом; первый вариант - основной, именно он показывается в подсказке.
STEP_ALT_SEP = '\x1f'


def _primary_step(step):
    return step.split(STEP_ALT_SEP)[0]


class _PathError(Exception):
    """Путь нельзя использовать; текст исключения - сообщение cmd для пользователя."""


THEORY_LESSONS = [
    ('whoami — кто вошёл в систему',
     '📖 **whoami** — показывает имя текущего пользователя.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    whoami [/groups] [/priv]\n\n'
     '📌 **ОПИСАНИЕ:**\n    Выводит имя учётной записи, под которой открыта\n'
     '    текущая консоль, в формате КОМПЬЮТЕР\\пользователь.\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> whoami\n    desktop-trainer\\student\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    whoami /groups — группы пользователя\n'
     '    whoami /priv  — привилегии пользователя\n'
     '    hostname      — имя компьютера'),

    ('cd — текущая рабочая папка',
     '📖 **cd** (Change Directory) без аргументов показывает, в какой папке ты сейчас находишься.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    cd\n\n'
     '📌 **ОПИСАНИЕ:**\n    Без аргументов cd просто печатает полный путь\n'
     '    текущей папки — аналог pwd в других системах.\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> cd\n    C:\\Users\\Student\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    cd путь — перейти в другую папку\n'
     '    dir     — посмотреть содержимое папки'),

    ('dir — список файлов (базовый)',
     '📖 **dir** — показывает содержимое папки.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    dir [шаблон]\n\n'
     '📌 **ОПИСАНИЕ:**\n    Выводит список файлов и папок с датой изменения\n'
     '    и размером. Можно ограничить список файлами,\n'
     '    подходящими под шаблон имени/расширения.\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> dir\n    C:\\Users\\Student> dir *.txt\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    tree — дерево папок\n    dir /a — с учётом скрытых'),

    ('dir — расширенный просмотр',
     '📖 **dir** с ключами — сортировка, скрытые файлы, рекурсия.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **ПОПУЛЯРНЫЕ КЛЮЧИ:**\n    /a     показать скрытые объекты\n'
     '    /o:d   сортировать по дате изменения\n'
     '    /s     показать содержимое всех вложенных папок\n'
     '    /b     только имена/пути, без заголовков\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> dir /a\n    C:\\Users\\Student> dir /o:d\n'
     '    C:\\Users\\Student> dir /s\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    dir /s /b шаблон — найти файлы по имени рекурсивно'),

    ('md — создание папок',
     '📖 **md** (MaKe Directory, синоним mkdir) — создаёт новую папку.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    md имя_папки\n\n'
     '📌 **ОПИСАНИЕ:**\n    Создаёт папку. Если путь состоит из нескольких\n'
     '    уровней через обратный слэш и часть из них ещё\n'
     '    не существует — md создаст всю цепочку сразу.\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> md Reports\n'
     '    C:\\Users\\Student> md Reports\\2026\\January\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    rd — удалить папку'),

    ('rd — удаление папок',
     '📖 **rd** (Remove Directory, синоним rmdir) — удаляет папку.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    rd [/s] [/q] имя_папки\n\n'
     '📌 **КЛЮЧИ:**\n    /s   удалить папку вместе со всем содержимым\n'
     '    /q   тихий режим, без подтверждающих вопросов\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> rd OldFolder\n'
     '    C:\\Users\\Student> rd /s /q OldFolder\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    md — создать папку\n    del — удалить файл'),

    ('copy nul — пустой файл',
     '📖 **copy nul** — способ быстро создать пустой файл без редактора.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    copy nul имя_файла\n\n'
     '📌 **ОПИСАНИЕ:**\n    nul — специальное «пустое» устройство. Копируя\n'
     '    его в новый файл, получаем файл нулевого размера —\n'
     '    удобная заготовка для дальнейшего наполнения.\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> copy nul draft.txt\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    copy — копирование файлов\n    echo текст > файл — создать файл с текстом'),

    ('echo — вывод текста и запись в файл',
     '📖 **echo** — выводит текст или значение переменной среды.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    echo текст\n    echo %ИМЯ_ПЕРЕМЕННОЙ%\n    echo текст > файл\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> echo Hello, Windows!\n'
     '    C:\\Users\\Student> echo %USERNAME%\n'
     '    C:\\Users\\Student> echo Hello > greeting.txt\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    type — просмотр файла\n    set — переменные среды'),

    ('cd — навигация по папкам',
     '📖 **cd** с аргументом — переход в другую папку.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    cd папка\n    cd ..\n    cd \\\n\n'
     '📌 **ОСОБЫЕ ПУТИ:**\n    cd ..   подняться на уровень выше\n    cd \\   перейти в корень диска\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> cd Documents\n'
     '    C:\\Users\\Student\\Documents> cd ..\n    C:\\Users\\Student> cd \\\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    dir — посмотреть содержимое папки'),

    ('type — просмотр содержимого файла',
     '📖 **type** — выводит на экран содержимое текстового файла.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    type имя_файла\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> type notes.txt\n'
     '    C:\\Users\\Student> type Documents\\file1.txt\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    more — постраничный просмотр\n    findstr — поиск текста в файле'),

    ('del — удаление файлов',
     '📖 **del** (синоним erase) — удаляет файлы.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    del [/q] [/f] имя_файла\n\n'
     '📌 **КЛЮЧИ:**\n    /q   без подтверждения\n    /f   принудительное удаление\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> del oldfile.txt\n'
     '    C:\\Users\\Student> del /q *.tmp\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    rd — удаление папок'),

    ('copy — копирование файлов',
     '📖 **copy** — создаёт копию файла.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    copy источник назначение\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> copy original.txt backup.txt\n'
     '    C:\\Users\\Student> copy report.txt Downloads\\\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    move — перемещение файлов\n    xcopy/robocopy — копирование папок целиком'),

    ('move — перемещение файлов',
     '📖 **move** — переносит файл в другую папку.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    move источник назначение\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> move package.txt Downloads\\\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    copy — копирование\n    ren — переименование'),

    ('ren — переименование файлов',
     '📖 **ren** (синоним rename) — меняет имя файла или папки.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    ren старое_имя новое_имя\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> ren oldname.txt newname.txt\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    move — перемещение файлов'),

    ('findstr — поиск текста в файлах',
     '📖 **findstr** — ищет строки по заданному тексту (аналог grep).\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    findstr [/i] [/n] [/v] текст файл\n\n'
     '📌 **КЛЮЧИ:**\n    /i   без учёта регистра\n    /n   с номерами строк\n    /v   инвертировать (строки БЕЗ текста)\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> findstr ERROR events.log\n'
     '    C:\\Users\\Student> findstr /i error events.log\n'
     '    C:\\Users\\Student> findstr /n ERROR events.log\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    find — простой поиск текста'),

    ('find — поиск и подсчёт строк',
     '📖 **find** — простой поиск точного текста в файле, с возможностью просто посчитать совпадения.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    find "текст" файл\n    find /c "текст" файл\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> find "INFO" events.log\n'
     '    C:\\Users\\Student> find /c "INFO" events.log\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    findstr — расширенный поиск'),

    ('sort — сортировка строк',
     '📖 **sort** — выводит содержимое файла с отсортированными строками.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    sort [/r] файл\n\n'
     '📌 **КЛЮЧИ:**\n    /r   сортировка в обратном порядке\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> sort names.txt\n'
     '    C:\\Users\\Student> sort /r names.txt\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    findstr — поиск строк'),

    ('more — постраничный просмотр',
     '📖 **more** — показывает длинный файл по частям (постранично).\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    more файл\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> more events.log\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    type — вывод файла целиком'),

    ('fc — построчное сравнение файлов',
     '📖 **fc** (File Compare) — сравнивает два текстовых файла построчно.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    fc файл1 файл2\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> fc file_a.txt file_b.txt\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    comp — побайтовое сравнение'),

    ('comp — побайтовое сравнение файлов',
     '📖 **comp** — сравнивает два файла побайтово.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    comp файл1 файл2\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> comp file_a.txt file_b.txt\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    fc — построчное сравнение'),

    ('dir /s /b — поиск файлов по имени',
     '📖 **dir /s /b** — ищет файлы по шаблону имени во всех вложенных папках.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    dir /s /b шаблон\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> dir /s /b *.txt\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    dir — обычный список\n    tree — структура папок'),

    ('where — расположение команды',
     '📖 **where** — показывает полный путь к исполняемому файлу команды.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    where имя_команды\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> where notepad\n    C:\\Windows\\System32\\notepad.exe\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    path — список папок для поиска программ'),

    ('tree — дерево папок',
     '📖 **tree** — показывает вложенные папки в виде дерева.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    tree\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> tree\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    dir /s — рекурсивный список с деталями'),

    ('attrib — атрибуты файлов',
     '📖 **attrib** — показывает и меняет атрибуты файла (скрытый, только чтение).\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    attrib [+h|-h] [+r|-r] файл\n\n'
     '📌 **КЛЮЧИ:**\n    +h/-h   сделать скрытым / снять скрытость\n    +r/-r   поставить / снять защиту от записи\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> attrib +r secret.txt\n'
     '    C:\\Users\\Student> attrib -r secret.txt\n'
     '    C:\\Users\\Student> attrib +h secret.txt\n\n'
     '⚠️ У скрытого файла другие атрибуты не меняются, пока в той же команде не указан\n'
     '   и сам атрибут скрытости (например, attrib -h -r secret.txt).\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    dir /a — показать скрытые файлы'),

    ('icacls — права доступа к файлу',
     '📖 **icacls** — показывает и настраивает список прав доступа (ACL) к файлу.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    icacls файл\n    icacls файл /grant пользователь:право\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> icacls shared.txt\n'
     '    C:\\Users\\Student> icacls shared.txt /grant Users:R\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    takeown — смена владельца файла'),

    ('takeown — смена владельца файла',
     '📖 **takeown** — назначает текущего пользователя владельцем файла.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    takeown /f файл\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> takeown /f ownerless.txt\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    icacls — права доступа'),

    ('hostname — имя компьютера',
     '📖 **hostname** — показывает сетевое имя компьютера.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    hostname\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> hostname\n    desktop-trainer\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    whoami — текущий пользователь'),

    ('ver — версия Windows',
     '📖 **ver** — показывает версию установленной Windows.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    ver\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> ver\n    Microsoft Windows [Version 10.0.19045.4046]\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    systeminfo — подробнее о системе'),

    ('systeminfo — сведения о системе',
     '📖 **systeminfo** — развёрнутый отчёт о характеристиках компьютера.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    systeminfo\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> systeminfo\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    ver — короткая версия ОС'),

    ('date — текущая дата',
     '📖 **date** — показывает текущую системную дату.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    date /t\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> date /t\n    10.09.2026\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    time — текущее время'),

    ('time — текущее время',
     '📖 **time** — показывает текущее системное время.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    time /t\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> time /t\n    14:35\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    date — текущая дата'),

    ('vol — метка тома',
     '📖 **vol** — показывает метку и серийный номер диска.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    vol\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> vol\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    dir — тоже показывает метку тома в заголовке'),

    ('set — переменные среды',
     '📖 **set** — создаёт и показывает переменные окружения текущей сессии.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    set ИМЯ=значение\n    set ИМЯ\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> set MYVAR=Trainer\n'
     '    C:\\Users\\Student> set MYVAR\n    MYVAR=Trainer\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    echo %ИМЯ% — вывести значение переменной'),

    ('path — список папок с программами',
     '📖 **path** — показывает и дополняет список папок для поиска исполняемых файлов.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    path\n    path %path%;новая_папка\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> path\n'
     '    C:\\Users\\Student> path %path%;C:\\Tools\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    where — найти команду в этом списке'),

    ('tasklist — список процессов',
     '📖 **tasklist** — показывает работающие в системе процессы.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    tasklist\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> tasklist\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    taskkill — завершить процесс'),

    ('tasklist — подробности о процессах',
     '📖 **tasklist** с ключами — память сессии и связанные службы.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **КЛЮЧИ:**\n    /v     подробный вывод (память, сеанс)\n    /svc   связанные с процессом службы\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> tasklist /v\n    C:\\Users\\Student> tasklist /svc\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    taskkill — завершить процесс'),

    ('taskkill — завершение процесса',
     '📖 **taskkill** — принудительно останавливает процесс.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    taskkill /pid номер\n    taskkill /im имя.exe /f\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> taskkill /pid 1234\n'
     '    C:\\Users\\Student> taskkill /im notepad.exe /f\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    tasklist — узнать PID процесса'),

    ('shutdown — завершение работы',
     '📖 **shutdown** — планирует перезагрузку или выключение компьютера.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    shutdown /r /t секунды\n    shutdown /s /t секунды\n    shutdown /a\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> shutdown /r /t 60\n    C:\\Users\\Student> shutdown /a\n\n'
     '⚠️ С /t 0 компьютер перезагрузится сразу - отменить через /a будет уже нечего.\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    taskkill — завершение отдельного процесса'),

    ('ipconfig — сетевые настройки',
     '📖 **ipconfig** — показывает текущие сетевые настройки компьютера.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    ipconfig\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> ipconfig\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    ping — проверка связи\n    netstat — активные соединения'),

    ('ping — проверка связи',
     '📖 **ping** — проверяет, отвечает ли указанный узел сети.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    ping адрес\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> ping 8.8.8.8\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    tracert — маршрут до узла'),

    ('netstat — активные соединения',
     '📖 **netstat** — показывает список сетевых соединений и портов.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    netstat\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> netstat\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    ipconfig — сетевые настройки'),

    ('nslookup — определение IP по имени',
     '📖 **nslookup** — узнаёт IP-адрес по доменному имени.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    nslookup домен\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> nslookup example.com\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    ping — проверка связи с узлом'),

    ('tracert — маршрут до узла',
     '📖 **tracert** — показывает путь пакета через промежуточные узлы сети.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    tracert узел\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> tracert example.com\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    ping — быстрая проверка связи'),

    ('whoami /groups — группы и привилегии',
     '📖 **whoami /groups** и **/priv** — группы и привилегии текущего пользователя.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    whoami /groups\n    whoami /priv\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> whoami /groups\n    C:\\Users\\Student> whoami /priv\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    net localgroup — локальные группы компьютера'),

    ('net user — учётные записи',
     '📖 **net user** — список локальных учётных записей и создание новых.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    net user\n    net user имя пароль /add\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> net user\n'
     '    C:\\Users\\Student> net user NewStudent Pass1234 /add\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    net localgroup — группы пользователей'),

    ('net localgroup — локальные группы',
     '📖 **net localgroup** — список локальных групп, создание групп и добавление в них пользователей.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    net localgroup\n    net localgroup группа /add\n    net localgroup группа пользователь /add\n\n'
     '📌 **ПРИМЕРЫ:**\n    C:\\Users\\Student> net localgroup\n'
     '    C:\\Users\\Student> net localgroup Students /add\n'
     '    C:\\Users\\Student> net localgroup Students NewStudent /add\n\n'
     '⚠️ Пользователь должен уже существовать. Новая учётная запись сразу попадает\n'
     '   в группу Users, поэтому добавить её туда повторно не получится.\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    net user — учётные записи'),

    ('query user — активные сеансы',
     '📖 **query user** — показывает, кто сейчас работает в системе.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    query user\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> query user\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    whoami — только своё имя'),

    ('doskey /history — история команд',
     '📖 **doskey /history** — показывает список ранее введённых команд.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    doskey /history\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> doskey /history\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    (клавиша F7 в реальном cmd тоже показывает историю)'),

    ('title — заголовок окна',
     '📖 **title** — меняет текст в заголовке окна терминала.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    title текст_заголовка\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> title Учебная сессия\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    color — цвет окна'),

    ('color — цвет окна терминала',
     '📖 **color** — меняет цвет текста и фона консоли.\n\n'
     '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
     '📌 **СИНТАКСИС:**\n    color код\n\n'
     '📌 **ПРИМЕР:**\n    C:\\Users\\Student> color 0A\n    (зелёный текст на чёрном фоне)\n\n'
     '📌 **СВЯЗАННЫЕ КОМАНДЫ:**\n    title — заголовок окна'),
]


def _rounded_points(x1, y1, x2, y2, r):
    """Точки сглаженного многоугольника для отрисовки скругленного прямоугольника на Canvas."""
    return [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]


class RoundedPanel(tk.Canvas):
    """Контейнер со скругленными углами. Настоящие дочерние виджеты кладутся в .inner —
    сама раскладка (pack/side/fill/...) внутри .inner не меняется, меняется только
    визуальное оформление контейнера."""

    def __init__(self, parent, bg, radius=16, **kwargs):
        try:
            parent_bg = parent.cget('bg')
        except Exception:
            parent_bg = bg
        super().__init__(parent, bg=parent_bg, highlightthickness=0, bd=0, **kwargs)
        self._radius = radius
        self._panel_bg = bg
        self._shape_id = None
        self.inner = tk.Frame(self, bg=bg)
        self._win_id = self.create_window(0, 0, anchor='nw', window=self.inner)
        self.bind('<Configure>', self._redraw)

    def _redraw(self, event=None):
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 4 or h < 4:
            return
        if self._shape_id is not None:
            self.delete(self._shape_id)
        r = min(self._radius, w / 2, h / 2)
        self._shape_id = self.create_polygon(
            _rounded_points(1, 1, w - 1, h - 1, r),
            smooth=True, fill=self._panel_bg, outline=self._panel_bg
        )
        self.tag_lower(self._shape_id)
        self.itemconfig(self._win_id, width=w, height=h)


class RoundedButton(tk.Canvas):
    """Кнопка со скругленными углами, отрисованная на Canvas (обычный tk.Button
    не умеет скругляться). Поддерживает .config(state=...) как обычная кнопка."""

    def __init__(self, parent, text, command=None, bg='#50fa7b', fg='#1e1e2e',
                 hover_bg=None, font=('Arial', 9, 'bold'), radius=10, padx=16, pady=8, **kwargs):
        try:
            parent_bg = parent.cget('bg')
        except Exception:
            parent_bg = bg
        super().__init__(parent, bg=parent_bg, highlightthickness=0, bd=0, cursor='hand2', **kwargs)
        self.command = command
        self._bg = bg
        self._hover_bg = hover_bg or bg
        self._fg = fg
        self._font = font
        self._text = text
        self._radius = radius
        self._state = tk.NORMAL
        self._hovering = False

        measure = tk.Label(parent, text=text, font=font)
        measure.update_idletasks()
        width = measure.winfo_reqwidth() + padx * 2
        height = measure.winfo_reqheight() + pady * 2
        measure.destroy()
        tk.Canvas.config(self, width=width, height=height)

        self.bind('<Configure>', self._redraw)
        self.bind('<Button-1>', self._on_click)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)

    def _current_fill(self):
        if self._state == tk.DISABLED:
            return '#44475a'
        return self._hover_bg if self._hovering else self._bg

    def _redraw(self, event=None):
        w = self.winfo_width() or int(str(self['width']))
        h = self.winfo_height() or int(str(self['height']))
        self.delete('all')
        r = min(self._radius, w / 2, h / 2)
        fill = self._current_fill()
        self.create_polygon(
            _rounded_points(1, 1, w - 1, h - 1, r),
            smooth=True, fill=fill, outline=fill
        )
        fg = self._fg if self._state == tk.NORMAL else '#8f92a8'
        self.create_text(w / 2, h / 2, text=self._text, fill=fg, font=self._font)

    def _on_click(self, event=None):
        if self._state == tk.NORMAL and self.command:
            self.command()

    def _on_enter(self, event=None):
        if self._state == tk.NORMAL:
            self._hovering = True
            self._redraw()

    def _on_leave(self, event=None):
        self._hovering = False
        self._redraw()

    def config(self, **kwargs):
        state = kwargs.pop('state', None)
        if state is not None:
            self._state = state
            self._redraw()
        if kwargs:
            tk.Canvas.config(self, **kwargs)

    configure = config


class WindowsTrainerGUI:
    # Все команды, которые понимает тренажёр (синонимы - в COMMAND_ALIASES)
    COMMAND_ALIASES = {'mkdir': 'md', 'rmdir': 'rd', 'erase': 'del', 'rename': 'ren', 'chdir': 'cd'}
    KNOWN_COMMANDS = {
        'whoami', 'cd', 'dir', 'md', 'rd', 'copy', 'echo', 'type', 'del', 'move', 'ren',
        'findstr', 'find', 'sort', 'more', 'fc', 'comp', 'where', 'tree', 'attrib', 'icacls',
        'takeown', 'hostname', 'ver', 'systeminfo', 'date', 'time', 'vol', 'set', 'path',
        'tasklist', 'taskkill', 'shutdown', 'ipconfig', 'ping', 'netstat', 'nslookup', 'tracert',
        'net', 'query', 'quser', 'doskey', 'title', 'color', 'exit',
        'mkdir', 'rmdir', 'erase', 'rename', 'chdir',
    }
    # Команды, которые берут остаток строки целиком (как текст), а не список аргументов
    RAW_COMMANDS = {'echo', 'title', 'set', 'path', 'cd'}
    # Символы, которые cmd пропускает сразу после ECHO/TITLE (echo. печатает пустую строку)
    ECHO_DELIMS = ' \t.:;,=/\\[]+('
    RESERVED_NAMES = {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$'} | \
        {f'COM{i}' for i in range(1, 10)} | {f'LPT{i}' for i in range(1, 10)}
    # Ключи, после которых идёт значение отдельным аргументом (taskkill /pid 1234)
    VALUE_SWITCHES = {
        'taskkill': {'pid', 'im', 'fi', 's', 'u', 'p'},
        'takeown': {'f', 's', 'u', 'p', 'd'},
        'shutdown': {'t', 'c', 'd', 'm'},
        'icacls': {'grant', 'deny', 'remove', 'setowner', 'save', 'restore', 'substitute'},
        'tasklist': {'fi', 'fo', 's', 'u', 'p', 'm'},
        'sort': {'o', 't', 'l', 'm', 'rec'},
        'systeminfo': {'s', 'u', 'p', 'fo'},
    }
    # Допустимые ключи команд: неизвестный ключ даёт ошибку "Неверный ключ", как в cmd,
    # а не молча игнорируется. Команд, которых нет в словаре, проверка не касается.
    ALLOWED_SWITCHES = {
        'dir': set(), 'md': set(), 'rd': {'s', 'q'}, 'ren': set(), 'type': set(),
        'copy': {'y', '-y', 'a', 'b', 'v', 'z', 'd', 'n', 'l'},
        'del': {'p', 'f', 's', 'q', 'a'}, 'move': {'y', '-y'},
        'sort': {'r', 'o', 'l', 'm', 'rec', 't'}, 'more': {'e', 'c', 'p', 's', 't'},
        'tree': {'f', 'a'}, 'date': {'t'}, 'time': {'t'}, 'vol': set(), 'ver': set(), 'hostname': set(),
        'whoami': {'groups', 'priv', 'user', 'all', 'upn', 'fqdn', 'logonid', 'fo', 'nh'},
        'attrib': {'s', 'd', 'l'},
        'takeown': {'f', 'a', 'r', 'd', 's', 'u', 'p'},
        'taskkill': {'pid', 'im', 'f', 't', 'fi', 's', 'u', 'p'},
        'tasklist': {'v', 'svc', 'm', 'fi', 'fo', 'nh', 's', 'u', 'p', 'apps'},
        'shutdown': {'r', 's', 'a', 't', 'l', 'h', 'f', 'c', 'd', 'm', 'p', 'g', 'e', 'i', 'o',
                     'hybrid', 'fw', 'soft'},
        'find': {'i', 'c', 'v', 'n', 'off', 'offline'},
        'findstr': {'i', 'n', 'v', 'b', 'e', 'l', 'r', 's', 'x', 'm', 'o', 'p', 'off', 'offline'},
        'fc': {'a', 'b', 'c', 'l', 'n', 'off', 'offline', 't', 'u', 'w'},
        'comp': {'d', 'a', 'l', 'c', 'm', 'off', 'offline'},
        'icacls': {'grant', 'deny', 'remove', 'setowner', 'reset', 't', 'c', 'l', 'q', 'save',
                   'restore', 'findsid', 'verify', 'inheritance', 'setintegritylevel', 'substitute'},
        'where': {'r', 'q', 'f', 't'},
        'doskey': {'history', 'macros', 'reinstall', 'listsize', 'exename', 'macrofile',
                   'insert', 'overstrike'},
        'color': set(), 'query': set(), 'quser': set(), 'exit': {'b'},
        'systeminfo': {'s', 'u', 'p', 'fo', 'nh'},
        'ipconfig': {'all', 'release', 'renew', 'flushdns', 'displaydns', 'registerdns',
                     'release6', 'renew6', 'showclassid', 'setclassid', 'allcompartments'},
    }
    # Ключи со встроенным значением (dir /o:-d, del /a:h, findstr /c:"текст", sort /+3)
    SWITCH_PATTERNS = {
        'dir': r'[aot]:?-?[a-z-]*|[swpbqlxnc4r]|-[a-z]',
        'del': r'a:?[-a-z]*',
        'findstr': r'[cgfda]:.*',
        'sort': r'\+\d+',
        'comp': r'n=\d+',
    }
    WHERE_PROGRAMS = {
        'notepad.exe': ['C:\\Windows\\System32\\notepad.exe', 'C:\\Windows\\notepad.exe'],
        'explorer.exe': ['C:\\Windows\\explorer.exe'],
        'regedit.exe': ['C:\\Windows\\regedit.exe'],
        'powershell.exe': ['C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe'],
        **{n: ['C:\\Windows\\System32\\' + n] for n in (
            'calc.exe', 'mspaint.exe', 'cmd.exe', 'taskmgr.exe', 'ping.exe', 'ipconfig.exe',
            'hostname.exe', 'whoami.exe', 'tasklist.exe', 'taskkill.exe', 'shutdown.exe',
            'where.exe', 'findstr.exe', 'find.exe', 'sort.exe', 'more.com', 'fc.exe', 'comp.exe',
            'tree.com', 'attrib.exe', 'icacls.exe', 'takeown.exe', 'systeminfo.exe', 'netstat.exe',
            'nslookup.exe', 'tracert.exe', 'net.exe', 'query.exe', 'quser.exe', 'doskey.exe',
            'xcopy.exe', 'robocopy.exe')},
    }

    def __init__(self, root):
        self.root = root
        self.root.title("🪟 Тренажер командной строки Windows")
        self.root.geometry("1300x750")
        self.root.resizable(True, True)
        self.root.configure(bg='#1e1e2e')

        # Имя пользователя (оно же - имя папки C:\\Users\\<имя>, поэтому без символов,
        # недопустимых в именах папок Windows)
        try:
            login = os.getlogin()
        except Exception:
            login = ''
        login = re.sub(r'[<>:"/\\|?*%\x00-\x1f]', '', login or '').strip(' .')
        self.username = login or "Student"

        # Имя компьютера
        try:
            node = (platform.node() or '').split('.')[0]
        except Exception:
            node = ''
        node = re.sub(r'[^A-Za-z0-9-]', '', node).upper()[:15]
        self.hostname = node or "DESKTOP-TRAINER"

        # Виртуальный диск C:\\ в реальной временной папке, с учебными файлами
        self.workspace = None
        self._raw_args = ''
        self._new_workspace()

        # Статистика
        self.stats = {'attempts': 0, 'successes': 0, 'failed': 0, 'skipped': 0}
        self.current_lesson = 0
        self.history = []

        # Общий лимит подсказок (кнопка "Подсказка") на весь тест, а не на урок -
        # не сбрасывается кнопкой "Сброс" и переходом между уроками
        self.HINT_BUDGET = 10
        self.hints_used = 0

        # Счетчик неудачных попыток для текущего урока
        self.failed_attempts = 0
        self.hint_shown = False
        self.lesson_completed = False
        self.lesson_failed = False

        # Для многошаговых заданий
        self.step_counter = 0
        self.required_steps = []
        self.completed_steps = []

        # Уроки с расширенными заданиями
        self.lessons = [
            {
                'id': 'whoami',
                'title': 'Кто ты в системе',
                'description': '''📖 Показывает, под каким именем пользователя сейчас открыта эта консоль.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает имя учётной записи, под которой запущен
    терминал, вместе с именем компьютера.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Проверить, под какой учётной записью идёт работа
    • Отладка скриптов, которые ведут себя по-разному
      в зависимости от пользователя''',
                'task': '1. Узнай имя текущего пользователя',
                'steps': _steps('IAEBBQIe'),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'cd_show',
                'title': 'Где ты сейчас находишься',
                'description': '''📖 Показывает полный путь до папки, в которой ты сейчас работаешь в терминале.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает абсолютный путь текущей рабочей папки,
    если ввести команду без каких-либо аргументов.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Быстро понять, в какой папке ты находишься
    • Проверить путь перед запуском скрипта''',
                'task': '1. Покажи текущую рабочую папку',
                'steps': _steps('NA0='),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'dir_basic',
                'title': 'Что лежит в папке (базовый просмотр)',
                'description': '''📖 Показывает список файлов и подпапок внутри текущей папки.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает имена файлов и папок с датой изменения и
    размером. Можно ограничить список только файлами,
    подходящими под шаблон имени или расширения.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Посмотреть содержимое папки
    • Найти файлы конкретного типа среди прочих''',
                'task': '1. Покажи содержимое текущей папки\n2. Покажи только файлы с расширением .txt',
                'steps': _steps('MwAc', 'MwAcREVZBywG'),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'dir_advanced',
                'title': 'Что лежит в папке (расширенный просмотр)',
                'description': '''📖 Тот же просмотр содержимого папки, но с дополнительной сортировкой и охватом вложенных папок.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Умеет показывать объекты, обычно скрытые от глаз,
    сортировать вывод по дате изменения и заглядывать
    сразу во все вложенные папки.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Найти файл, который специально спрятан
    • Найти самый недавно изменённый файл
    • Посмотреть содержимое всех вложенных папок сразу''',
                'task': '1. Покажи все объекты текущей папки, включая скрытые\n2. Покажи содержимое текущей папки, отсортированное по дате изменения (сначала самые старые)\n3. Покажи содержимое текущей папки и всех вложенных папок',
                'steps': _steps('MwAcREAW', 'MwAcREAYSTBtBQAcRV0wVg==', 'MwAcREAE'),
                'check': lambda self, output: True,
                'points': 25
            },
            {
                'id': 'md',
                'title': 'Создание новых папок',
                'description': '''📖 Создаёт новую папку с указанным именем.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Создаёт папку. Если путь состоит из нескольких
    вложенных уровней и часть из них ещё не существует,
    создаёт сразу всю цепочку за одну команду.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Подготовить структуру папок для проекта
    • Создать вложенную иерархию за одно действие''',
                'task': '1. Создай папку NewProject\n2. Создай одной командой цепочку вложенных папок NewProject\\Src\\Utils',
                'steps': _steps('Og1OKgoAIyYdCwwNEW0yWVRbRn8qCig+HRs1FQYR', 'Og1OKgoAIyYdCwwNES4MQFNuYSsNAyxxAh87GRdFJUQgORwLBRIQIC4yGw05JytbXEE='),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'rd',
                'title': 'Удаление папок',
                'description': '''📖 Удаляет папку целиком.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Пустую папку удаляет сразу. Для папки, в которой
    что-то лежит, нужен отдельный режим, который сотрёт
    её вместе со всем содержимым без лишних вопросов.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Очистка временных папок с данными
    • Наведение порядка в рабочей области''',
                'task': '1. Создай пустую папку EmptyFolder\n2. Удали папку EmptyFolder\n3. Создай папку FullFolder\n4. Создай в папке FullFolder пустой файл item.txt\n5. Удали папку FullFolder вместе со всем содержимым без запроса подтверждения',
                'steps': _steps('Og1OIQIHBy00DgUKAABAX1tWXS1EKjIeGw0ZHwkBDlM=', 'JQ1OIQIHBy00DgUKAABAQF1WXS1EKjIeGw0ZHwkBDlM=', 'Og1OIhobHxIdDQ0LF20yWVRbRn8iGjMCKRszFAAX', 'NAYeHU8ZBjhSJxwCCTQwXlRXRgMNGzoDQQAnBHoRElEySQARA1dNdDQUBQIjHTNWVUBoNhAKMkAbDCs=', 'JQ1OSxxXXCVSJxwCCTQwXlRXRkAWAjsHHVRwA0VKGgERHAIIKRgfMBcT'),
                'check': lambda self, output: True,
                'points': 25
            },
            {
                'id': 'copy_empty',
                'title': 'Создание пустых файлов',
                'description': '''📖 Быстро создаёт новый пустой файл без какого-либо содержимого.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Создаёт файл нулевого размера, не открывая никакой
    редактор — удобная заготовка для дальнейшего
    наполнения содержимым.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Быстро создать файл для дальнейшего редактирования
    • Подготовить набор пустых файлов для теста''',
                'task': '1. Создай пустой файл draft.txt\n2. Создай ещё один пустой файл draft2.txt',
                'steps': _steps('NAYeHU8ZBjhSBRsPAwZxRkhGKysdHzpOAQEzUFtFD1M2DxpKGw8H', 'NAYeHU8ZBjhSBRsPAwZtHERKQEAQFi8LTxoqHEVbS0UlCAgQXVkHLAY='),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'echo',
                'title': 'Вывод текста и запись в файл',
                'description': '''📖 Выводит на экран переданный текст или значение системной переменной.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает текст в терминал. Умеет подставлять вместо
    специального имени в процентах значение системной
    переменной. Если после текста указать специальный
    символ перенаправления и имя файла, вывод вместо
    экрана попадёт прямо в файл.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Быстро создать файл с текстом без редактора
    • Проверить значение системной переменной''',
                'task': '1. Выведи на экран текст: Hello, Windows!\n2. Выведи имя текущего пользователя через переменную среды\n3. Запиши текст Hello в файл greeting.txt',
                'steps': _steps('MgoGC08/FjgeDkVOMhsxVl9FR34=', 'MgoGC09SJgc3MycvKDd6', 'MgoGC08/FjgeDklQRRUtV1VGXTEDQSsWG2s6Ew0KS2kyBQILURABMRcVAAACXCtKRA=='),
                'check': lambda self, output: True,
                'points': 25
            },
            {
                'id': 'cd_navigate',
                'title': 'Перемещение между папками',
                'description': '''📖 Переключает текущую рабочую папку терминала на другую папку.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Переходит в указанную вложенную папку. Есть удобные
    сокращения: подняться на уровень выше или мгновенно
    вернуться в корень диска.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Навигация по файловой системе
    • Быстро вернуться в нужную рабочую папку''',
                'task': '1. Перейди в папку Documents\n2. Вернись на уровень выше\n3. Перейди в корень диска C:',
                'steps': _steps('NA1OIAAUBjkXDx0d', 'NA1OSkE=', 'NA1OOHAUF3QxWzVxBhZ/HVQSd2U4'),
                'check': lambda self, output: True,
                'points': 25
            },
            {
                'id': 'type_view',
                'title': 'Просмотр содержимого файла',
                'description': '''📖 Выводит на экран всё содержимое текстового файла целиком.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает текст файла на экран без изменений. Работает
    и с файлами, лежащими внутри вложенных папок.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Быстро заглянуть в содержимое текстового файла
    • Проверить, что записалось в файл''',
                'task': '1. Посмотри содержимое notes.txt\n2. Посмотри содержимое file1.txt внутри папки Documents',
                'steps': _steps('IxAeAU8ZHCAXEkcaHQY=', 'IxAeAU8zHDcHDAwAEQEDVFleUW5KGyca'),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'del',
                'title': 'Удаление файлов',
                'description': '''📖 Безвозвратно стирает указанный файл.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Удаляет один файл или сразу несколько файлов,
    подходящих под общий шаблон имени, без подтверждения
    на каждый.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Очистка временных файлов
    • Автоматизация очистки в сценариях

⚠️ Удалённое таким способом обычно не попадает в корзину.''',
                'task': '1. Создай пустой файл oldfile.txt\n2. Удали файл oldfile.txt\n3. Создай пустой файл temp1.tmp\n4. Создай пустой файл temp2.tmp\n5. Удали оба .tmp-файла одной командой, указав шаблон имени',
                'steps': _steps('NAYeHU8ZBjhSDgUKAxszVx5GTCt7GyYeClQxBQlFVQE4BQoCBhsWegYZHQ==', 'MwwCRAAbFzIbDQxAEQorLVVAVSwBTzACCxI2HABLH1kj', 'NAYeHU8ZBjhSFQwDFUNxRl1CKysdHzpOAQEzUFtFH0Q6GV9KGxoD', 'NAYeHU8ZBjhSFQwDFUBxRl1CKysdHzpOAQEzUFtFH0Q6GVxKGxoD', 'MwwCREVZBzkCfg0LCVJwQxAYGisJH0ALHRUsFUVPRVU6GQ=='),
                'check': lambda self, output: True,
                'points': 25
            },
            {
                'id': 'copy_files',
                'title': 'Копирование файлов',
                'description': '''📖 Создаёт копию файла под новым именем или в другом месте, оставляя оригинал нетронутым.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Копирует содержимое файла в файл с другим именем или
    в другую папку.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Сделать резервную копию файла перед правкой
    • Перенести файл в другое место, сохранив оригинал''',
                'task': '1. Создай пустой файл original.txt\n2. Скопируй файл original.txt в файл backup.txt\n3. Скопируй файл report.txt в папку Downloads',
                'steps': _steps('NAYeHU8ZBjhSDhsHAhsxU1wcQCcQcCsXHxF/HhAJSx93BhwNCB4dNR5PHRYR', 'NAYeHU8YAT0VCAcPCVwrSkQSVj4HBCoeQQAnBA==', 'NAYeHU8FFiQdEx1AEQorEnRdQzEIAD4KHCg='),
                'check': lambda self, output: True,
                'points': 25
            },
            {
                'id': 'move_files',
                'title': 'Перемещение файлов между папками',
                'description': '''📖 Переносит файл в другую папку, при этом на старом месте он больше не остаётся.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    В отличие от копирования, оригинал не остаётся на
    старом месте — файл просто «переезжает» в указанную
    папку.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Разложить файлы по папкам
    • Навести порядок в структуре рабочей области''',
                'task': '1. Создай пустой файл package.txt\n2. Перемести файл package.txt в папку Downloads',
                'steps': _steps('NAYeHU8ZBjhSEQgNDhM4Vx5GTCt7GyYeClQxBQlFVQEnCA0PDhAWegYZHQ==', 'OgYYAU8HEjcZAA4LSwYnRhB2WygKAzAPCwcD'),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'rename',
                'title': 'Переименование файлов',
                'description': '''📖 Меняет имя файла, оставляя его содержимое и расположение без изменений.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Присваивает файлу новое имя в той же папке, где он
    находится.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Дать файлу более понятное имя
    • Массовая подготовка файлов к архивации''',
                'task': '1. Создай пустой файл oldname.txt\n2. Переименуй файл oldname.txt в newname.txt',
                'steps': _steps('NAYeHU8ZBjhSDgUKCxMyVx5GTCt7GyYeClQxBQlFVQE4BQoKDhoWegYZHQ==', 'JQwARAAbFzoTDAxAEQorEl5XQzEFAjpAGwwrbxcABUA6DE4LAxMdNR8ERxodBn9cVUVaPgkKcRoXAA=='),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'findstr',
                'title': 'Поиск текста внутри файлов',
                'description': '''📖 Ищет строки, содержащие заданный текст, внутри файла.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Просматривает файл построчно и печатает только те
    строки, где встречается искомый фрагмент. Умеет
    искать без учёта регистра и показывать номера
    найденных строк.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Найти нужные записи в большом лог-файле
    • Проверить, встречается ли слово в документе''',
                'task': '1. Найди строки со словом ERROR в файле events.log\n2. Найди в файле events.log слово error без учёта регистра\n3. Найди строки со словом ERROR в файле events.log и покажи номера строк',
                'steps': _steps('MQAAABwDAXQ3MzshN1I6RFVcQCxKAzAJ', 'MQAAABwDAXRdCEkLFwAwQBBXQjoKGyxAAxs4bwMMBUUkHRxEQB5TESAzJjxFFylXXkZHcQgAOA==', 'MQAAABwDAXRdD0krNyAQYBBXQjoKGyxAAxs4'),
                'check': lambda self, output: True,
                'points': 25
            },
            {
                'id': 'find_text',
                'title': 'Подсчёт строк с текстом',
                'description': '''📖 Ищет заданный фрагмент текста в файле и умеет просто посчитать число совпадений.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Показывает строки, где встречается искомый текст,
    либо, в специальном режиме, только их количество —
    без самих строк.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Быстро оценить, сколько раз что-то встречается в файле
    • Проверить наличие записи в журнале событий''',
                'task': '1. Найди строки со словом INFO в файле events.log\n2. Посчитай, сколько строк файла events.log содержат слово INFO',
                'steps': _steps('MQAAAE9VOho0LktOAAQ6XERBGjMLCA==', 'MQAAAE9YEHRQKCcoKlB/V0ZXWisXQTMBCA=='),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'sort_lines',
                'title': 'Сортировка строк файла',
                'description': '''📖 Выводит содержимое файла с его строками, расставленными по порядку.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает строки файла в алфавитном порядке. Есть
    режим сортировки в обратном порядке.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Упорядочить список имён или значений
    • Подготовить данные перед дальнейшей обработкой''',
                'task': '1. Отсортируй строки файла names.txt по алфавиту\n2. Отсортируй строки файла names.txt в обратном порядке',
                'steps': _steps('JAYcEE8ZEjkXEkcaHQY=', 'JAYcEE9YAXQcAAQLFlwrSkQ='),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'more_paging',
                'title': 'Постраничный просмотр файла',
                'description': '''📖 Показывает содержимое длинного файла по частям, а не всё сразу.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Выводит текст файла постранично — удобно, когда
    текста больше, чем помещается на экране целиком.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Изучить длинный лог-файл частями''',
                'task': '1. Открой файл events.log для постраничного просмотра',
                'steps': _steps('OgYcAU8SBTEcFRpACR04'),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'fc_compare',
                'title': 'Построчное сравнение двух файлов',
                'description': '''📖 Сравнивает содержимое двух текстовых файлов и показывает, в каких строках они расходятся.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Читает оба файла построчно и выводит те места, где
    строки в них не совпадают.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Понять, чем отличаются две версии одного текста
    • Проверить результат правки файла''',
                'task': '1. Сравни построчно файлы file_a.txt и file_b.txt',
                'steps': _steps('MQpOAgYbFgsTTx0WEVI5W1xXaz1KGyca'),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'comp_compare',
                'title': 'Побайтовое сравнение двух файлов',
                'description': '''📖 Сравнивает содержимое двух файлов побайтово и сообщает, идентичны они или нет.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Сверяет два файла байт за байтом, без построчных
    подробностей — только итоговый вывод: совпадают или нет.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Быстро проверить, идентичны ли два файла''',
                'task': '1. Сравни побайтово файлы file_a.txt и file_b.txt',
                'steps': _steps('NAYDFE8RGjgXPghAEQorElZbWDo7DXEaFwA='),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'dir_search',
                'title': 'Поиск файлов по имени во вложенных папках',
                'description': '''📖 Обходит текущую папку и все вложенные в неё, выводя пути файлов, подходящих под шаблон имени.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Ищет файлы по шаблону имени сразу во всех вложенных
    папках и печатает только их пути, без лишних деталей.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Найти все файлы определённого типа в большом дереве папок''',
                'task': '1. Найди во всех вложенных папках файлы с расширением .txt и выведи только их полные пути',
                'steps': _steps('MwAcREAEU3sQQUNAEQor'),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'where_locate',
                'title': 'Поиск расположения команды',
                'description': '''📖 Показывает полный путь к исполняемому файлу, который запускается при вводе имени команды.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Находит, какая именно программа отзывается на
    введённое короткое имя, и печатает путь к ней.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Проверить, какая версия программы будет запущена''',
                'task': '1. Узнай, где расположен исполняемый файл программы Блокнот (notepad)',
                'steps': _steps('IAELFgpXHTsGBBkPAW0oWlVAUX8KACsLHxU7XgAdDg=='),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'tree_view',
                'title': 'Структура папок в виде дерева',
                'description': '''📖 Строит наглядную древовидную схему вложенных папок, начиная с текущей.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Показывает всю иерархию вложенных папок целиком —
    сразу видно, что куда вложено.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Быстро разобраться в структуре незнакомого проекта''',
                'task': '1. Покажи дерево вложенных папок текущей папки',
                'steps': _steps('IxsLAQ=='),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'attrib',
                'title': 'Скрытые и защищённые от записи файлы',
                'description': '''📖 Показывает и меняет специальные пометки файла.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Может сделать файл скрытым (он не будет показываться
    в обычном списке) или защищённым от случайной записи,
    а также снять эти пометки обратно.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Спрятать служебный файл от посторонних глаз
    • Защитить важный файл от случайного изменения''',
                'task': '1. Создай пустой файл secret.txt\n2. Установи для файла secret.txt защиту от записи (только чтение)\n3. Сними с файла secret.txt защиту от записи\n4. Сделай файл secret.txt скрытым',
                'steps': _steps('NAYeHU8ZBjhSEgwNFxcrHERKQEAQFi8LTxoqHEVbS1IyChwBG1kHLAY=', 'Nh0aFgYVU38AQRoLBgA6Rh5GTCs=', 'Nh0aFgYVU3kAQRoLBgA6Rh5GTCs=', 'Nh0aFgYVU38aQRoLBgA6Rh5GTCs='),
                'check': lambda self, output: True,
                'points': 25
            },
            {
                'id': 'icacls_perm',
                'title': 'Просмотр и изменение прав доступа к файлу',
                'description': '''📖 Показывает список прав доступа, выданных разным пользователям на файл, и позволяет выдать новое право.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает текущий список прав доступа к файлу и умеет
    выдавать конкретному пользователю новое право,
    например на чтение.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Проверить, кто и что может делать с файлом
    • Открыть доступ к файлу для другого пользователя''',
                'task': '1. Создай пустой файл shared.txt\n2. Посмотри текущие права доступа к файлу shared.txt\n3. Выдай группе Users право на чтение (R) файла shared.txt',
                'steps': _steps('NAYeHU8ZBjhSEgEPFxc7HERKQEAQFi8LTxoqHEVbS1I/CBwBC1kHLAY=', 'PgoPBwMEUycaABsLAVwrSkQ=', 'PgoPBwMEUycaABsLAVwrSkQSGzgWDjEaTyEsFRcWUXNIAA0FDBsAdAEJCBwAFnFGSEYUcAMdPgAbVAoDABcYG387Rw=='),
                'check': lambda self, output: True,
                'points': 25
            },
            {
                'id': 'takeown_owner',
                'title': 'Смена владельца файла',
                'description': '''📖 Назначает текущего пользователя владельцем указанного файла.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Переоформляет владение файлом на текущего
    пользователя — пригождается, когда доступ к файлу
    нужно вернуть себе.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Файл достался «ничейным» после переноса с другого компьютера
    • Нужно снова получить полный контроль над файлом''',
                'task': '1. Создай пустой файл ownerless.txt\n2. Стань владельцем файла ownerless.txt',
                'steps': _steps('NAYeHU8ZBjhSDh4AAAAzV0NBGiscG0AaFgQ6UAsQBwFpSQETARIBOBcSGkARCis=', 'IwgFAQAAHXRdB0kBEhw6QFxXRyxKGyca'),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'hostname_cmd',
                'title': 'Имя компьютера в сети',
                'description': '''📖 Показывает сетевое имя текущего компьютера.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает имя, под которым компьютер виден в локальной
    сети.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Найти этот компьютер среди других в сети
    • Указать точное имя узла при удалённом подключении''',
                'task': '1. Узнай сетевое имя этого компьютера',
                'steps': _steps('PwYdEAEWHjE='),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'ver_cmd',
                'title': 'Версия операционной системы',
                'description': '''📖 Показывает версию установленной операционной системы одной короткой строкой.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает номер версии системы без лишних подробностей.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Быстро проверить версию перед установкой программы''',
                'task': '1. Узнай версию установленной операционной системы',
                'steps': _steps('IQwc'),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'systeminfo_cmd',
                'title': 'Подробная информация о системе',
                'description': '''📖 Выводит развёрнутый отчёт о характеристиках компьютера одной командой.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Показывает производителя, тип системы, объём памяти
    и другие технические сведения сразу в одном отчёте.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Собрать сведения о компьютере для техподдержки''',
                'task': '1. Получи развёрнутый отчёт о характеристиках системы',
                'steps': _steps('JBAdEAoaGjoUDg=='),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'date_cmd',
                'title': 'Текущая дата',
                'description': '''📖 Показывает текущую системную дату.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает сегодняшнюю дату по системным часам.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Использование в отчётах и сценариях резервного копирования''',
                'task': '1. Узнай текущую дату так, чтобы терминал не предлагал ввести новую',
                'steps': _steps('MwgaAU9YBw=='),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'time_cmd',
                'title': 'Текущее время',
                'description': '''📖 Показывает текущее системное время.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает текущее время по системным часам.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Проверить синхронизацию времени на компьютере''',
                'task': '1. Узнай текущее время так, чтобы терминал не предлагал ввести новое',
                'steps': _steps('IwADAU9YBw=='),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'vol_cmd',
                'title': 'Метка и серийный номер диска',
                'description': '''📖 Показывает метку тома и серийный номер текущего диска.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает название (метку) и уникальный серийный номер
    диска, на котором сейчас идёт работа.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Быстро отличить один накопитель от другого''',
                'task': '1. Узнай метку и серийный номер текущего диска',
                'steps': _steps('IQYC'),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'set_env',
                'title': 'Переменные окружения сессии',
                'description': '''📖 Создаёт временную переменную, доступную только в текущем окне терминала, и показывает её значение.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Сохраняет пару «имя = значение» в текущей сессии
    терминала и позволяет посмотреть значение по имени.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Настройка временных параметров перед запуском сценария''',
                'task': '1. Создай переменную MYVAR со значением Trainer\n2. Посмотри значение переменной MYVAR',
                'steps': _steps('JAwaRCIuJRUgXD0cBBsxV0I=', 'JAwaRCIuJRUgfgwNDR1/F31rYh42Sg=='),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'path_var',
                'title': 'Список папок для поиска программ',
                'description': '''📖 Показывает перечень папок, в которых система ищет исполняемые файлы при запуске команд.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает текущий список папок, а также позволяет
    дополнить его новой папкой, не стирая прежний список.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Разрешить запускать программу из любой папки по короткому имени''',
                'task': '1. Покажи текущий список папок для поиска программ\n2. Добавь в конец этого списка папку C:\\Tools, сохранив прежние папки',
                'steps': _steps('JwgaDA==', 'JwgaDE9SAzUGCUxVJkgDZl9dWCx7Hz4aB1R6ICQxIwRsKlQ4OxgcOAF+GgsRUi9TRFoJehQOKwZKTxxKOTEETjsacRcKA1MEMzUhU0AiHmZ4Fw8cXjMLAQAYLA=='),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'tasklist_basic',
                'title': 'Список работающих процессов',
                'description': '''📖 Показывает перечень всех программ, которые сейчас выполняются в системе.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает список запущенных процессов вместе с их
    числовым идентификатором.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Проверить, запущена ли нужная программа''',
                'task': '1. Покажи список всех работающих процессов',
                'steps': _steps('IwgdDwMeACA='),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'tasklist_advanced',
                'title': 'Подробности о процессах и их службах',
                'description': '''📖 Помимо самого списка процессов, показывает дополнительные технические детали.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Может показать использование памяти каждым процессом
    либо перечислить службы, связанные с конкретным
    процессом.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Понять, какой процесс расходует больше всего памяти
    • Выяснить, какая служба стоит за конкретным процессом''',
                'task': '1. Покажи подробный список процессов: с состоянием, именем пользователя и заголовком окна\n2. Покажи, какие службы работают внутри каждого процесса',
                'steps': _steps('IwgdDwMeACBSTh8=', 'IwgdDwMeACBSThoYBg=='),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'taskkill_cmd',
                'title': 'Завершение процесса',
                'description': '''📖 Принудительно останавливает работающую программу.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Останавливает процесс по его числовому идентификатору
    или по имени исполняемого файла, при необходимости —
    принудительно.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Завершить зависшую программу, которая не отвечает''',
                'task': '1. Останови процесс с идентификатором (PID) 1234\n2. Принудительно останови процесс notepad.exe по имени его файла',
                'steps': _steps('IwgdDwQeHzhSThkHAVJuAAMG', 'IwgdDwQeHzhSTgADRRwwRlVCVTtKCicLT1s5'),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'shutdown_cmd',
                'title': 'Завершение работы компьютера',
                'description': '''📖 Планирует перезагрузку компьютера и умеет отменить уже запланированное действие.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Ставит в очередь перезагрузку через заданное число
    секунд. Пока действие не наступило, его можно отменить
    отдельной командой.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Запланировать перезапуск после установки обновлений
    • Отменить перезапуск, если он больше не нужен

⚠️ В этом тренажере команда ничего не перезагружает
   по-настоящему — это учебная симуляция.''',
                'task': '1. Запланируй перезагрузку компьютера через 60 секунд\n2. Отмени запланированную перезагрузку',
                'steps': _steps('JAEbEAsYBDpSThtOSgZ/BAAtRzcRGzsBGBp/XxFFXRF3Rhw=', 'JAEbEAsYBDpSTgg='),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'ipconfig_cmd',
                'title': 'Настройки сети компьютера',
                'description': '''📖 Показывает текущие сетевые настройки компьютера.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает выданный компьютеру сетевой адрес, маску
    подсети и адрес основного шлюза.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Диагностика проблем с подключением к сети''',
                'task': '1. Покажи текущие сетевые настройки компьютера',
                'steps': _steps('PhkNCwERGjM='),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'ping_cmd',
                'title': 'Проверка связи с узлом сети',
                'description': '''📖 Отправляет несколько тестовых пакетов на указанный адрес и показывает, отвечает ли узел.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Проверяет, доступен ли указанный узел сети, и
    показывает время отклика.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Быстро проверить, работает ли интернет-соединение''',
                'task': '1. Проверь связь с узлом 8.8.8.8',
                'steps': _steps('JwAAA09PXWxcWUdW'),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'netstat_cmd',
                'title': 'Активные сетевые соединения',
                'description': '''📖 Показывает список текущих сетевых соединений и используемых портов.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает таблицу открытых сетевых соединений: какая
    программа с кем и на каком порту сейчас общается.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Проверить, какие соединения открыты прямо сейчас''',
                'task': '1. Покажи список активных сетевых соединений',
                'steps': _steps('OQwaFxsWBw=='),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'nslookup_cmd',
                'title': 'Определение IP-адреса по доменному имени',
                'description': '''📖 Обращается к службе доменных имён и показывает числовой адрес, соответствующий имени сайта.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Переводит доменное имя в числовой сетевой адрес.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Диагностика проблем с открытием конкретного сайта''',
                'task': '1. Узнай IP-адрес, соответствующий example.com',
                'steps': _steps('ORoCCwAcBiRSBBEPCAIzVx5RWzI='),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'tracert_cmd',
                'title': 'Путь пакета до узла сети',
                'description': '''📖 Показывает все промежуточные узлы, через которые проходит запрос по пути к указанному адресу.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает каждый промежуточный маршрутизатор на пути
    к узлу вместе со временем отклика на нём.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Понять, на каком участке сети возникает задержка''',
                'task': '1. Проследи маршрут до узла example.com',
                'steps': _steps('IxsPBwoFB3QXGQgDFR46HFNdWQ=='),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'whoami_groups',
                'title': 'Группы и привилегии текущего пользователя',
                'description': '''📖 Показывает, в какие группы входит текущий пользователь и какими особыми привилегиями он обладает.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает список групп текущей учётной записи, а
    отдельно — список её особых прав в системе.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Проверить уровень прав перед выполнением административных действий''',
                'task': '1. Покажи, в какие группы входит текущий пользователь\n2. Покажи список его привилегий',
                'steps': _steps('IAEBBQIeU3sVEwYbFQE=', 'IAEBBQIeU3sCEwAY'),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'net_user',
                'title': 'Учётные записи пользователей компьютера',
                'description': '''📖 Показывает список локальных учётных записей на компьютере и позволяет создать новую.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает список всех учётных записей на компьютере, а
    также умеет создать новую учётную запись с паролем.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Завести отдельную учётную запись для нового человека''',
                'task': '1. Покажи список локальных учётных записей\n2. Создай учётную запись NewStudent с паролем Pass1234',
                'steps': _steps('OQwaRBoEFiY=', 'OQwaRBoEFiZSLwwZNgYqVlVcQH80DiwdXkZsREVKCkUz'),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'net_localgroup',
                'title': 'Локальные группы пользователей',
                'description': '''📖 Показывает список локальных групп на компьютере, умеет создать новую группу и добавить в группу существующего пользователя.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает список локальных групп, создаёт новые группы
    и добавляет в группу уже существующих пользователей.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Выдать пользователю права сразу целой группы
    • Собрать учётные записи одного класса в отдельную группу''',
                'task': '1. Покажи список локальных групп\n2. Создай локальную группу Students\n3. Добавь в группу Students встроенную учётную запись Guest',
                'steps': _steps('OQwaRAMYEDUeBhsBEAI=', 'OQwaRAMYEDUeBhsBEAJ/YURHUDoKGyxOQBU7FA==', 'OQwaRAMYEDUeBhsBEAJ/YURHUDoKGyxOKAE6AxFFREAzDQ=='),
                'check': lambda self, output: True,
                'points': 20
            },
            {
                'id': 'query_user',
                'title': 'Кто сейчас работает в системе',
                'description': '''📖 Показывает список пользователей, чьи сеансы сейчас активны на этом компьютере.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает таблицу активных сеансов с именем
    пользователя и временем входа.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Проверить, кто ещё сейчас работает на этом компьютере''',
                'task': '1. Покажи список активных сеансов пользователей',
                'steps': _steps('JhwLFhZXBicXE3YfEAE6QA=='),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'doskey_history',
                'title': 'История введённых команд',
                'description': '''📖 Показывает список всех команд, которые были набраны в этом окне терминала ранее.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Печатает пронумерованный список ранее введённых
    команд — удобно вспомнить или повторить нужную строку.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Вспомнить длинную команду, которую печатал раньше''',
                'task': '1. Покажи историю введённых в этом окне команд',
                'steps': _steps('MwYdDwoOU3saCBoaCgAm'),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'title_cmd',
                'title': 'Заголовок окна терминала',
                'description': '''📖 Меняет текст, который отображается в заголовке окна терминала.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Заменяет надпись в верхней части окна на указанный
    текст.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Подписать окно, когда открыто сразу несколько терминалов''',
                'task': '1. Установи для этого окна терминала заголовок: Учебная сессия',
                'steps': _steps('IwAaCApXo/ej5rnbtcOPj+CC5dBEvt6+2qXeoeS10/DY'),
                'check': lambda self, output: True,
                'points': 15
            },
            {
                'id': 'color_cmd',
                'title': 'Цвета текста и фона терминала',
                'description': '''📖 Меняет цвет текста и фона окна терминала на один из предустановленных вариантов.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **ЧТО ДЕЛАЕТ:**
    Перекрашивает окно терминала по двухсимвольному коду
    цвета — просто для удобства или чтобы визуально
    выделить рабочую сессию.

📌 **КОГДА ПРИГОДИТСЯ:**
    • Визуально отличить окна разных задач друг от друга''',
                'task': '1. Установи для окна терминала цветовую схему с кодом 0A (зелёный текст на чёрном фоне)',
                'steps': _steps('NAYCCx1XQxVtAgYCCgB/AlE='),
                'check': lambda self, output: True,
                'points': 15
            }
        ]

        # Перемешиваем порядок уроков, чтобы при каждом запуске
        # программы последовательность заданий была разной
        random.shuffle(self.lessons)

        # Общее количество баллов
        self.total_points = sum(lesson['points'] for lesson in self.lessons)
        self.earned_points = 0

        # Обработка закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Сначала показываем теорию, тест начинается только после нее
        self.create_intro_screen()

    def create_test_files(self):
        """Создает тестовые файлы для уроков в домашней папке пользователя"""
        self.hidden_files = set()
        self.readonly_files = set()
        home = self.home_dir

        files = {
            'notes.txt': 'Заметки к учебному занятию.\n',
            'report.txt': 'Отчёт за месяц готов к отправке.\n',
            'readme.txt': 'Этот файл описывает содержимое рабочей папки.\n',
            'desktop.ini': '[.ShellClassInfo]\nIconResource=%SystemRoot%\\system32\\imageres.dll,-117\n',
            'budget.csv': 'Категория,Сумма\nЕда,1200\nТранспорт,300\n',
            'numbers.txt': '\n'.join(['5', '3', '9', '1', '7', '2', '8', '4', '6', '0']) + '\n',
            'names.txt': '\n'.join(['Виктор', 'Анна', 'Сергей', 'Ольга', 'Дмитрий']) + '\n',
            'file_a.txt': "Первая строка\nВторая строка\nТретья строка\n",
            'file_b.txt': "Первая строка\nИзменённая вторая строка\nТретья строка\n",
        }
        for name, content in files.items():
            with open(os.path.join(home, name), 'w', encoding='utf-8') as f:
                f.write(content)
        # desktop.ini в настоящих папках пользователя скрыт - на нём видна разница dir и dir /a
        self.hidden_files.add(self._attr_key(os.path.join(home, 'desktop.ini')))

        for d in ('Documents', 'Downloads', 'Projects'):
            dpath = os.path.join(home, d)
            os.makedirs(dpath, exist_ok=True)
            for i in (1, 2):
                with open(os.path.join(dpath, f'file{i}.txt'), 'w', encoding='utf-8') as f:
                    f.write(f"Содержимое {d}\\file{i}.txt\n")

        with open(os.path.join(home, 'events.log'), 'w', encoding='utf-8') as f:
            for i in range(1, 13):
                f.write(f"2026-09-{i:02d} 10:{i:02d} INFO Событие номер {i}\n")
            f.write("2026-09-13 10:13 WARNING Задержка ответа сервера\n")
            f.write("2026-09-14 10:14 ERROR Не удалось подключиться к базе\n")
            f.write("2026-09-15 10:15 ERROR Тайм-аут операции\n")

        # Разные даты изменения, чтобы сортировка по дате заметно отличалась от сортировки по имени
        now = datetime.now().timestamp()
        order = ['report.txt', 'Projects', 'names.txt', 'events.log', 'desktop.ini', 'budget.csv',
                 'Downloads', 'file_a.txt', 'numbers.txt', 'readme.txt', 'Documents', 'file_b.txt', 'notes.txt']
        for i, name in enumerate(order):
            t = now - (len(order) - i) * 86400 - 3600 * (i % 5)
            try:
                os.utime(os.path.join(home, name), (t, t))
            except OSError:
                pass

    def create_intro_screen(self):
        """Показывает вводный экран с теорией по всем командам перед тестом"""
        self.intro_frame = tk.Frame(self.root, bg='#1e1e2e')
        self.intro_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        title_label = tk.Label(
            self.intro_frame,
            text="🪟 Тренажер командной строки Windows — теория",
            font=('Arial', 18, 'bold'),
            bg='#1e1e2e',
            fg='#f8f8f2'
        )
        title_label.pack(anchor=tk.W)

        subtitle_label = tk.Label(
            self.intro_frame,
            text="Прочитай материал по всем командам ниже, а затем переходи к тесту.",
            font=('Arial', 11),
            bg='#1e1e2e',
            fg='#8be9fd'
        )
        subtitle_label.pack(anchor=tk.W, pady=(2, 10))

        theory_text = scrolledtext.ScrolledText(
            self.intro_frame,
            wrap=tk.WORD,
            font=('Courier New', 10),
            bg='#282a36',
            fg='#f8f8f2',
            insertbackground='white',
            relief=tk.FLAT
        )
        theory_text.pack(fill=tk.BOTH, expand=True)
        theory_text.insert(tk.END, self.build_theory_text())

        theory_text.insert(tk.END, "\n\n")
        end_label = tk.Label(
            theory_text,
            text="Это был весь материал. Готов проверить себя?",
            font=('Arial', 11, 'bold'),
            bg='#282a36',
            fg='#8be9fd'
        )
        theory_text.window_create(tk.END, window=end_label)
        theory_text.insert(tk.END, "\n\n")

        start_btn = RoundedButton(
            theory_text,
            text="Перейти к тесту ➡",
            command=self.start_test,
            bg='#50fa7b',
            fg='#1e1e2e',
            font=('Arial', 12, 'bold'),
            radius=14,
            padx=20,
            pady=10
        )
        theory_text.window_create(tk.END, window=start_btn)
        theory_text.insert(tk.END, "\n\n")

        theory_text.config(state=tk.DISABLED)

    def build_theory_text(self):
        """Собирает единый текст теории по всем командам тренажера"""
        parts = [
            "═" * 70,
            "ТЕОРИЯ: ОСНОВНЫЕ КОМАНДЫ КОМАНДНОЙ СТРОКИ WINDOWS",
            "═" * 70,
            "",
        ]
        for i, (title, description) in enumerate(THEORY_LESSONS, 1):
            parts.append(f"{i}. {title}")
            parts.append("─" * 70)
            parts.append(description)
            parts.append("")
            parts.append("")
        return "\n".join(parts)

    def start_test(self):
        """Скрывает теорию и запускает тест"""
        self.intro_frame.destroy()
        self.create_widgets()
        self.load_lesson()

    def create_widgets(self):
        """Создает виджеты интерфейса"""
        main_frame = tk.Frame(self.root, bg='#1e1e2e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        header_frame = tk.Frame(main_frame, bg='#1e1e2e')
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = tk.Label(
            header_frame,
            text="🪟 Тренажер командной строки Windows",
            font=('Arial', 18, 'bold'),
            bg='#1e1e2e',
            fg='#f8f8f2'
        )
        title_label.pack(side=tk.LEFT)

        self.stats_label = tk.Label(
            header_frame,
            text="Команд: 0 | Успехов: 0 | Баллы: 0",
            font=('Arial', 10),
            bg='#1e1e2e',
            fg='#50fa7b'
        )
        self.stats_label.pack(side=tk.RIGHT)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            header_frame,
            variable=self.progress_var,
            maximum=len(self.lessons),
            length=200
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=10)

        content_frame = tk.Frame(main_frame, bg='#1e1e2e')
        content_frame.pack(fill=tk.BOTH, expand=True)

        _left_panel = RoundedPanel(content_frame, bg='#282a36', radius=16)
        _left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        left_frame = _left_panel.inner

        self.lesson_title = tk.Label(
            left_frame,
            text="Урок 1",
            font=('Arial', 14, 'bold'),
            bg='#282a36',
            fg='#50fa7b'
        )
        self.lesson_title.pack(anchor=tk.W, pady=(10, 5), padx=10)

        self.description_text = scrolledtext.ScrolledText(
            left_frame,
            wrap=tk.WORD,
            font=('Courier New', 10),
            height=16,
            bg='#1e1e2e',
            fg='#f8f8f2',
            insertbackground='white',
            relief=tk.FLAT
        )
        self.description_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10), padx=10)
        self.description_text.config(state=tk.DISABLED)

        _task_panel = RoundedPanel(left_frame, bg='#44475a', radius=12)
        _task_panel.pack(fill=tk.X, pady=(0, 10), padx=10)
        task_frame = _task_panel.inner

        task_label = tk.Label(
            task_frame,
            text="📝 ЗАДАНИЕ",
            font=('Arial', 11, 'bold'),
            bg='#44475a',
            fg='#ffb86c'
        )
        task_label.pack(anchor=tk.W, padx=10, pady=(5, 0))

        self.task_label = tk.Label(
            task_frame,
            text="Задание",
            font=('Arial', 11),
            bg='#44475a',
            fg='#f8f8f2',
            wraplength=550,
            justify=tk.LEFT
        )
        self.task_label.pack(padx=10, pady=(5, 10))

        self.attempts_info = tk.Label(
            left_frame,
            text="Попыток: 0/5",
            font=('Arial', 10),
            bg='#282a36',
            fg='#8be9fd'
        )
        self.attempts_info.pack(anchor=tk.W, padx=10, pady=(0, 5))

        self.steps_info = tk.Label(
            left_frame,
            text="Шаг: 0 из 0",
            font=('Arial', 10),
            bg='#282a36',
            fg='#ffb86c'
        )
        self.steps_info.pack(anchor=tk.W, padx=10, pady=(0, 5))

        right_frame = tk.Frame(content_frame, bg='#1e1e2e')
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        _terminal_panel = RoundedPanel(right_frame, bg='#0b0b16', radius=16)
        _terminal_panel.pack(fill=tk.BOTH, expand=True)
        terminal_frame = _terminal_panel.inner

        terminal_title = tk.Label(
            terminal_frame,
            text="💻 ТЕРМИНАЛ",
            font=('Arial', 10, 'bold'),
            bg='#0b0b16',
            fg='#8be9fd'
        )
        terminal_title.pack(anchor=tk.W, padx=10, pady=(10, 5))

        self.prompt_label = tk.Label(
            terminal_frame,
            text="C:\\Users\\Student> ",
            font=('Courier New', 10, 'bold'),
            bg='#0b0b16',
            fg='#50fa7b'
        )
        self.prompt_label.pack(anchor=tk.W, padx=10)

        _entry_panel = RoundedPanel(terminal_frame, bg='#1e1e2e', radius=10)
        _entry_panel.pack(fill=tk.X, pady=(5, 10), padx=10)
        self.command_entry = tk.Entry(
            _entry_panel.inner,
            font=('Courier New', 11),
            bg='#1e1e2e',
            fg='#f8f8f2',
            insertbackground='#50fa7b',
            relief=tk.FLAT,
            highlightthickness=0,
            bd=0
        )
        self.command_entry.pack(fill=tk.X, padx=12, pady=8)
        self.command_entry.bind('<Return>', self.execute_command)
        self.command_entry.focus()

        self.output_text = scrolledtext.ScrolledText(
            terminal_frame,
            wrap=tk.WORD,
            font=('Courier New', 10),
            height=15,
            bg='#0b0b16',
            fg='#f8f8f2',
            insertbackground='white',
            relief=tk.FLAT
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        # Окно вывода - только для чтения: пользователь печатает команды в
        # command_entry, а не прямо в этом окне. Программные .insert() из кода
        # ниже это не затрагивают - blockируются только реальные нажатия клавиш.
        self.output_text.bind('<Key>', lambda e: 'break')

        button_frame = tk.Frame(right_frame, bg='#1e1e2e')
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # "Очистить" убрана - то же самое делает команда cls прямо в
        # терминале, отдельная кнопка была лишней.
        buttons = [
            ("▶ Выполнить", self.execute_command, '#50fa7b', '#1e1e2e'),
            ("💡 Подсказка", self.show_hint, '#ffb86c', '#1e1e2e'),
            ("⏭ Следующий", self.next_lesson, '#8be9fd', '#1e1e2e'),
            ("🔄 Сброс", self.reset_workspace, '#ff5555', '#1e1e2e')
        ]

        self._action_buttons = []
        for text, command, bg, fg in buttons:
            btn = RoundedButton(
                button_frame,
                text=text,
                command=command,
                bg=bg,
                fg=fg,
                radius=10,
                font=('Arial', 9, 'bold'),
                padx=15,
                pady=8
            )
            btn.pack(side=tk.LEFT, padx=4)
            self._action_buttons.append(btn)

        self.next_btn = self._action_buttons[-2]
        self.next_btn.config(state=tk.DISABLED)

        # Кнопка "Подсказка" - общий лимит на весь тест, гаснет насовсем при исчерпании
        self.hint_btn = self._action_buttons[1]
        if self.hints_used >= self.HINT_BUDGET:
            self.hint_btn.config(state=tk.DISABLED)

        # Кнопка "Сброс" - отключается вместе с полем ввода после того, как урок
        # уже засчитан или провален, иначе через нее можно пересдавать один и тот
        # же урок и бесконечно копить баллы/успехи
        self.reset_btn = self._action_buttons[-1]

    def load_lesson(self):
        """Загружает текущий урок"""
        if self.current_lesson >= len(self.lessons):
            self.show_completion()
            return

        # Каждый урок начинается на свежих учебных файлах в домашней папке:
        # иначе незавершённый прошлый урок (например, брошенный во вложенной
        # папке или с удалёнными файлами) ломал следующий
        self._new_workspace()

        self.failed_attempts = 0
        self.hint_shown = False
        self.lesson_completed = False
        self.lesson_failed = False
        self.step_counter = 0
        self.completed_steps = []

        self.command_entry.config(state=tk.NORMAL)

        lesson = self.lessons[self.current_lesson]

        self.lesson_title.config(
            text=f"Урок {self.current_lesson + 1}/{len(self.lessons)}: {lesson['title']} (⭐ {lesson['points']} баллов)"
        )

        self.description_text.config(state=tk.NORMAL)
        self.description_text.delete(1.0, tk.END)
        self.description_text.insert(1.0, lesson['description'])
        self.description_text.config(state=tk.DISABLED)

        self.task_label.config(text=f"📌 {self._task_display(lesson)}")

        self.update_steps_info()
        self.update_attempts_info()

        self.progress_var.set(self.current_lesson)
        self.update_stats()

        self.clear_output()
        self.update_prompt()

        self.next_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.NORMAL)
        if self.hints_used >= self.HINT_BUDGET:
            self.hint_btn.config(state=tk.DISABLED)
        self.command_entry.focus()
        self.root.update_idletasks()

    def update_steps_info(self):
        """Обновляет информацию о шагах"""
        lesson = self.lessons[self.current_lesson]
        total_steps = len(lesson['steps'])

        if total_steps > 1:
            # Показываем именно количество ВЫПОЛНЕННЫХ шагов (self.step_counter
            # само по себе, без +1) - раньше здесь было "текущий шаг" с
            # искусственным потолком в total_steps, из-за чего текст "Шаг: N из N"
            # выглядел одинаково и на последнем шаге, и после полного завершения,
            # то есть счётчик визуально "не двигался" после предпоследнего шага
            self.steps_info.config(
                text=f"📋 Выполнено шагов: {self.step_counter} из {total_steps}",
                fg='#ffb86c'
            )
            self.steps_info.pack(anchor=tk.W, padx=10, pady=(0, 5))
        else:
            self.steps_info.pack_forget()

    def update_attempts_info(self):
        """Обновляет информацию о попытках"""
        remaining = 5 - self.failed_attempts
        if remaining > 0:
            self.attempts_info.config(
                text=f"Попыток: {self.failed_attempts}/5 (осталось: {remaining})",
                fg='#8be9fd'
            )
        else:
            self.attempts_info.config(
                text="❌ Задание провалено! Нажми 'Следующий'",
                fg='#ff5555'
            )

    def _display_path(self, real_path):
        """Превращает реальный путь внутри песочницы в путь вида C:\\Users\\<имя>\\..."""
        try:
            rel = os.path.relpath(real_path, self.workspace)
        except ValueError:
            return 'C:\\'
        if rel in ('', '.') or rel.startswith('..'):
            return 'C:\\'
        return 'C:\\' + rel.replace(os.sep, '\\')

    def _resolve_path(self, p, wildcard=False):
        """Превращает введенный пользователем Windows-путь в реальный путь на диске,
        независимо от ОС, на которой запущен тренажер.

        Результат всегда остаётся внутри self.workspace (он играет роль диска C:\\):
        '..' не поднимает выше корня, 'C:\\...' и '\\...' отсчитываются от корня
        песочницы, другие диски считаются отсутствующими. Недопустимое для Windows
        имя вызывает _PathError с текстом настоящей ошибки cmd."""
        root = self.workspace
        p = self._unq(p)
        if not p:
            return self.current_dir
        m = re.match(r'^([A-Za-z]):(.*)$', p, re.S)
        if m:
            if m.group(1).upper() != 'C':
                raise _PathError("Системе не удается найти указанный путь.")
            p = m.group(2)
            if not p:
                return self.current_dir
        path = root if p[0] in '\\/' else self.current_dir
        segments = [s for s in re.split(r'[\\/]+', p) if s not in ('', '.')]
        for i, seg in enumerate(segments):
            if seg == '..':
                if os.path.normcase(path) != os.path.normcase(root):
                    path = os.path.dirname(path)
                continue
            is_last = i == len(segments) - 1
            if any(c in seg for c in '<>:"|') or any(ord(c) < 32 for c in seg) or (
                    self._has_wildcard(seg) and not (wildcard and is_last)):
                raise _PathError("Синтаксическая ошибка в имени файла, имени папки или метке тома.")
            seg = seg.rstrip(' .') or seg
            if seg in ('.', '..') or not seg.strip(' .'):
                continue
            if seg.split('.')[0].strip().upper() in self.RESERVED_NAMES:
                raise _PathError("Синтаксическая ошибка в имени файла, имени папки или метке тома.")
            path = os.path.join(path, seg if self._has_wildcard(seg) else self._match_case(path, seg))
        real = os.path.normcase(os.path.abspath(path))
        base = os.path.normcase(root)
        if real != base and not real.startswith(base.rstrip(os.sep) + os.sep):
            raise _PathError("Отказано в доступе.")
        return path

    def _expand_vars(self, text):
        """Подставляет значения переменных вида %ИМЯ% (имя без учёта регистра, как в cmd).
        Неизвестные переменные остаются как есть - так ведёт себя интерактивный cmd."""
        env = {k.upper(): v for k, v in self._env().items()}
        now = datetime.now()
        env.setdefault('CD', self._display_path(self.current_dir))
        env.setdefault('DATE', now.strftime('%d.%m.%Y'))
        env.setdefault('TIME', now.strftime('%H:%M:%S,') + f"{now.microsecond // 10000:02d}")
        return re.sub(r'%([^%\n]+)%', lambda m: env.get(m.group(1).upper(), m.group(0)), text)

    def update_prompt(self):
        """Обновляет промпт"""
        self.prompt_label.config(text=f"{self._display_path(self.current_dir)}> ")

    def update_stats(self):
        """Обновляет статистику"""
        self.stats_label.config(
            text=f"Команд: {self.stats['attempts']} | Успехов: {self.stats['successes']} | "
                 f"Баллы: {self.earned_points}/{self.total_points} | "
                 f"Подсказок: {self.hints_used}/{self.HINT_BUDGET}"
        )

    def clear_output(self, event=None):
        """Очищает вывод"""
        self.output_text.delete(1.0, tk.END)

    def _task_display(self, lesson):
        """Текст задания для показа пользователю: для многошаговых уроков
        добавляет напоминание вводить пункты по одной команде за раз, а не
        объединять их в одну строку (частая путаница у новичков)."""
        text = lesson['task']
        if len(lesson['steps']) > 1:
            text += "\n(Каждый пункт - отдельная команда. Вводи их по очереди, одну за другой.)"
        return text

    def show_hint(self):
        """Показывает подсказку"""
        if self.current_lesson < len(self.lessons):
            lesson = self.lessons[self.current_lesson]

            if self.hints_used >= self.HINT_BUDGET:
                messagebox.showwarning(
                    "Подсказки закончились",
                    f"Ты уже использовал все {self.HINT_BUDGET} подсказок, доступных на весь тест.\n"
                    f"Осталось рассчитывать только на память и оставшиеся попытки."
                )
                return

            if self.failed_attempts < 3:
                messagebox.showwarning(
                    "Подсказка недоступна",
                    f"Подсказка станет доступна после 3 неудачных попыток.\n"
                    f"Текущее количество попыток: {self.failed_attempts}/5"
                )
                return

            self.hints_used += 1
            self.update_stats()
            if self.hints_used >= self.HINT_BUDGET:
                self.hint_btn.config(state=tk.DISABLED)

            hint_text = f"""💡 **ПОДСКАЗКА** (использовано {self.hints_used} из {self.HINT_BUDGET} за весь тест)

📌 **Задание:** {self._task_display(lesson)}

📌 **Пошаговая инструкция:**

"""
            for i, step in enumerate(lesson['steps'], 1):
                hint_text += f"{i}. Введи: `{_primary_step(step)}`\n"

            if len(lesson['steps']) > 1:
                hint_text += f"\n📌 Всего шагов: {len(lesson['steps'])}"

            if self.hints_used >= self.HINT_BUDGET:
                hint_text += "\n\n⚠️ Это была последняя доступная подсказка на весь тест."

            messagebox.showinfo("Подсказка", hint_text, icon='info')

    # === МЕТОДЫ ДЛЯ КОМАНД ===

    def _new_workspace(self):
        """Пересоздаёт песочницу. Реальная временная папка играет роль диска C:\\,
        внутри неё C:\\Users\\<пользователь> с учебными файлами - так приглашение,
        cd \\ и сообщения выглядят как в настоящем cmd, а не показывают временную папку.
        Симулируемое состояние системы (переменные, учётные записи, атрибуты...) у
        каждого урока своё, чтобы прошлый урок не влиял на следующий."""
        if getattr(self, 'workspace', None):
            shutil.rmtree(self.workspace, ignore_errors=True)
        self.workspace = os.path.realpath(tempfile.mkdtemp(prefix="windows_trainer_"))
        for d in ('Program Files', 'Windows'):
            os.makedirs(os.path.join(self.workspace, d))
        self.home_dir = os.path.join(self.workspace, 'Users', self.username)
        os.makedirs(self.home_dir)
        self.current_dir = self.home_dir
        self.last_dir = None
        self.custom_env = {}
        self.custom_path = 'C:\\Windows\\system32;C:\\Windows;C:\\Windows\\System32\\Wbem'
        self.win_users = ['Administrator', 'DefaultAccount', 'Guest', self.username]
        self.win_groups = {
            'Administrators': ['Administrator', self.username],
            'Guests': ['Guest'],
            'Users': [self.username],
        }
        self.acl_grants = {}
        self.shutdown_pending = None
        try:
            self.root.title("🪟 Тренажер командной строки Windows")
        except Exception:
            pass
        self.create_test_files()

    def _attr_key(self, path):
        """Ключ файла для симулируемых атрибутов: в Windows имена не зависят от регистра"""
        return os.path.normpath(path).lower()

    @staticmethod
    def _unq(text):
        return (text or '').replace('"', '')

    @staticmethod
    def _has_wildcard(text):
        return '*' in text or '?' in text

    def _match_case(self, parent, name):
        """Находит существующий элемент папки без учёта регистра (как в Windows)"""
        try:
            entries = os.listdir(parent)
        except OSError:
            return name
        if name in entries:
            return name
        low = name.lower()
        for e in entries:
            if e.lower() == low:
                return e
        return name

    def _hide_real_paths(self, text):
        """Заменяет в выводе реальный путь временной папки на путь вида C:\\... -
        например, в текстах системных ошибок Python."""
        if not text or not self.workspace:
            return text
        variants = {self.workspace, self.workspace.replace('\\', '\\\\'), self.workspace.replace('\\', '/')}
        if self.workspace.startswith('/private/'):
            variants.add(self.workspace[len('/private'):])

        def repl(m):
            parts = [p for p in re.split(r'\\\\|[\\/]', m.group(1)) if p]
            return 'C:\\' + '\\'.join(parts)

        for v in sorted(variants, key=len, reverse=True):
            text = re.sub(re.escape(v) + r"((?:(?:\\\\|[\\/])[^\\/'\"\n]+)*)", repl, text, flags=re.I)
        return text

    def _env(self):
        """Переменные среды сеанса: системные плюс созданные пользователем командой set"""
        env = {
            'ALLUSERSPROFILE': 'C:\\ProgramData',
            'COMPUTERNAME': self.hostname,
            'ComSpec': 'C:\\Windows\\system32\\cmd.exe',
            'HOMEDRIVE': 'C:',
            'HOMEPATH': '\\Users\\' + self.username,
            'NUMBER_OF_PROCESSORS': '8',
            'OS': 'Windows_NT',
            'Path': self.custom_path,
            'PATHEXT': '.COM;.EXE;.BAT;.CMD;.VBS;.JS;.WSH;.MSC',
            'PROMPT': '$P$G',
            'SystemDrive': 'C:',
            'SystemRoot': 'C:\\Windows',
            'USERDOMAIN': self.hostname,
            'USERNAME': self.username,
            'USERPROFILE': 'C:\\Users\\' + self.username,
            'windir': 'C:\\Windows',
        }
        for up, (name, value) in self.custom_env.items():
            for k in [k for k in env if k.upper() == up]:
                del env[k]
            env[name] = value
        return env

    def _split_line(self, line):
        """Отделяет имя команды от остатка строки так, как это делает cmd.exe:
        имя встроенной команды может быть приклеено к аргументу (cd.., cd\\, dir/a, echo.).
        Возвращает (имя команды в нижнем регистре, остаток строки)."""
        s = line.lstrip()
        m = re.match(r'[^\s"\\/,;=+(<>|&]+', s)
        word = m.group(0) if m else ''
        rest = s[len(word):]
        low = word.lower()
        known = self.KNOWN_COMMANDS
        if low not in known:
            if low.endswith('.exe') and low[:-4] in known:
                low = low[:-4]
            elif '.' in low and low.split('.', 1)[0] in known:
                head = word.split('.', 1)[0]
                rest = s[len(head):]
                low = head.lower()
        return low, rest

    def _tokenize(self, rest, split_switches=True):
        """Делит остаток строки на аргументы и операторы (> >> | & <) с учётом кавычек.
        Кавычки остаются внутри аргумента, как в cmd. Возвращает список
        (текст, вид, начало, конец), где вид - 'arg' или 'op'."""
        toks = []
        cur, start, inq = '', None, False
        i, n = 0, len(rest)

        def flush(end):
            nonlocal cur, start
            if cur:
                toks.append((cur, 'arg', start, end))
            cur, start = '', None

        while i < n:
            c = rest[i]
            if c == '"':
                if start is None:
                    start = i
                inq = not inq
                cur += c
            elif not inq and c in ' \t,;=' and not (c in ',;=' and cur):
                flush(i)
            elif not inq and c in '<>|&':
                op_start = i
                if c == '>' and cur in ('1', '2') and start == i - 1:
                    op = cur + '>'
                    cur, start = '', None
                    op_start = i - 1
                else:
                    flush(i)
                    op = c
                if rest[i + 1:i + 2] == c and c in '>|&':
                    op += c
                    i += 1
                toks.append((op.replace('1>', '>'), 'op', op_start, i + 1))
            elif not inq and c == '/' and split_switches and cur and cur[-1] != ':':
                flush(i)
                start = i
                cur = c
            else:
                if start is None:
                    start = i
                cur += c
            i += 1
        flush(n)
        return toks

    def _parse_line(self, cmd, rest):
        """Разбирает остаток строки: аргументы, перенаправления вывода и "сырой" текст
        без перенаправлений (нужен echo/title/set/path/cd, которые берут строку целиком).
        Возвращает (args, redirects, raw, error)."""
        toks = self._tokenize(rest, split_switches=cmd not in self.RAW_COMMANDS)
        args, redirects, cut = [], [], []
        i = 0
        while i < len(toks):
            text, kind, s, e = toks[i]
            if kind == 'op':
                if text in ('>', '>>', '2>', '2>>'):
                    if i + 1 >= len(toks) or toks[i + 1][1] != 'arg':
                        return None, None, None, "❌ Синтаксическая ошибка в команде."
                    redirects.append((text, toks[i + 1][0]))
                    cut.append((s, toks[i + 1][3]))
                    i += 2
                    continue
                return None, None, None, ("❌ Конвейеры (|), несколько команд в одной строке (&) и "
                                          "перенаправление ввода (<) в тренажёре не поддерживаются - "
                                          "вводи команды по одной")
            args.append(text)
            i += 1
        raw = rest
        for s, e in reversed(cut):
            raw = raw[:s] + raw[e:]
        return args, redirects, raw, None

    def _parse_args(self, cmd, args):
        """Делит аргументы на ключи (/x) и позиционные. Ключ хранится без '/' в нижнем
        регистре (часть после ':' - как введена); для ключей со значением
        (taskkill /pid 1234) значение забирается из следующего аргумента.
        Возвращает (ключи, позиционные аргументы, значения ключей)."""
        value_switches = self.VALUE_SWITCHES.get(cmd, set())
        switches, positional, values = [], [], {}
        i = 0
        while i < len(args):
            a = args[i]
            if cmd == 'shutdown' and re.fullmatch(r'-[A-Za-z?]+', a):
                a = '/' + a[1:]
            if a.startswith('/') and len(a) > 1:
                head, sep, tail = a[1:].partition(':')
                name = head.lower()
                switches.append(name + sep + tail)
                if name in value_switches and (not sep or cmd == 'icacls'):
                    if i + 1 < len(args) and not args[i + 1].startswith('/'):
                        values[name] = args[i + 1]
                        i += 1
                    else:
                        values[name] = None
            else:
                positional.append(a)
            i += 1
        return switches, positional, values

    def _bad_switch(self, cmd, switches, args=()):
        """Возвращает текст ошибки cmd для неизвестного ключа или None"""
        allowed = self.ALLOWED_SWITCHES.get(cmd)
        if allowed is None:
            return None
        for sw in switches:
            if sw == '?':
                continue
            base = sw.lower()
            pattern = self.SWITCH_PATTERNS.get(cmd)
            if pattern and re.fullmatch(pattern, base):
                continue
            if base in allowed or base.split(':')[0] in allowed or base.split('=')[0] in allowed:
                continue
            typed = next((a[1:] for a in args if a[1:].lower() == sw.lower()), sw)
            return f'❌ Неверный ключ - "{typed}".'
        return None

    def _normalize_for_match(self, command):
        """Приводит команду к виду, в котором равные для cmd записи совпадают:
        регистр имён команд, ключей и путей не важен (в Windows он не важен), порядок ключей
        тоже, кавычки вокруг путей и завершающий '\\' у папки не важны, синонимы
        команд (mkdir = md) равны. Регистр важен только там, где он меняет результат:
        выводимый текст, значения переменных, пароль, строка поиска без /i.
        Переменные НЕ подставляются: 'echo %USERNAME%' и 'echo Student' - разные ответы."""
        cmd, rest = self._split_line(command)
        if not cmd or cmd not in self.KNOWN_COMMANDS:
            return None
        cmd = self.COMMAND_ALIASES.get(cmd, cmd)
        args, redirects, raw, error = self._parse_line(cmd, rest)
        if error:
            return None

        def norm_path(t):
            t = self._unq(t).lower()
            if t.startswith('c:\\') or t.startswith('c:/'):
                t = t[2:]
            while t.startswith('.\\'):
                t = t[2:]
            if len(t) > 1 and t.endswith('\\') and not t.endswith(':\\'):
                t = t.rstrip('\\') or '\\'
            return t

        def lower_vars(t):
            return re.sub(r'%[^%]+%', lambda m: m.group(0).lower(), t)

        redirs = tuple(sorted((op, norm_path(t)) for op, t in redirects))
        if cmd in ('echo', 'title'):
            text = raw[1:] if raw[:1] and raw[0] in self.ECHO_DELIMS else raw
            return (cmd, ' '.join(lower_vars(text).split()), redirs)
        if cmd == 'set':
            text = raw.lstrip()
            if '=' in text:
                name, value = text.split('=', 1)
                if name.strip().lower() == 'path':
                    value = value.lower()
                return (cmd, name.lower(), '=', lower_vars(value).rstrip(), redirs)
            return (cmd, text.strip().lower(), redirs)
        if cmd == 'path':
            text = raw.strip()
            if text.startswith('='):
                text = text[1:].strip()
            return (cmd, text.lower(), redirs)
        if cmd == 'cd':
            text = raw.strip()
            text = re.sub(r'^/d(\s+|$)', '', text, flags=re.I).strip()
            return (cmd, norm_path(text.replace('/', '\\')), redirs)

        switches, positional, values = self._parse_args(cmd, args)
        sw_items = []
        for sw in switches:
            name, sep, tail = sw.partition(':')
            if cmd == 'dir':
                item = sw.replace(':', '')
            elif cmd == 'findstr' and sep:
                item = name + ':' + (self._unq(tail).lower() if 'i' in switches else self._unq(tail))
            else:
                item = sw.lower()
            if name in values:
                val = values[name]
                val = '' if val is None else self._unq(val).lower()
                if cmd == 'icacls':
                    val = re.sub(r'\(([a-z,]+)\)$', r'\1', val)
                item = (item, val)
            else:
                item = (item, '')
            sw_items.append(item)
        pos = []
        for idx, p in enumerate(positional):
            if cmd == 'find' and idx == 0:
                pos.append(p.lower() if 'i' in switches else p)
            elif cmd == 'findstr' and idx == 0:
                pos.append(self._unq(p).lower() if 'i' in switches else self._unq(p))
            elif cmd == 'net' and idx == 2 and positional[0].lower() in ('user', 'users'):
                pos.append(self._unq(p))
            else:
                pos.append(norm_path(p))
        return (cmd, tuple(sorted(sw_items)), tuple(pos), redirs)

    def _step_matches(self, command, step):
        got = self._normalize_for_match(command)
        return got is not None and any(
            got == self._normalize_for_match(variant) for variant in step.split(STEP_ALT_SEP))

    @staticmethod
    def _fmt_num(n):
        return f"{n:,}".replace(',', ' ')

    def _dir_entries(self, base, pattern, attr, order):
        """Элементы папки для dir: [(имя, полный путь, это папка)] с учётом шаблона,
        атрибутов (/a) и сортировки (/o)"""
        pat = pattern.lower()
        if pat in ('*.*', '*'):
            pat = '*'
        result = []
        for name in os.listdir(base):
            full = os.path.join(base, name)
            if not fnmatch.fnmatchcase(name.lower(), pat):
                continue
            is_dir = os.path.isdir(full)
            hidden = self._attr_key(full) in self.hidden_files
            readonly = self._attr_key(full) in self.readonly_files
            if attr is None:
                if hidden:
                    continue
            else:
                wanted = re.findall(r'-?[a-z]', attr[1:].replace(':', ''))
                ok = True
                for w in wanted:
                    neg, letter = w.startswith('-'), w[-1]
                    has = {'d': is_dir, 'h': hidden, 'r': readonly, 'a': not is_dir, 's': False}.get(letter, True)
                    if has == neg:
                        ok = False
                if not ok:
                    continue
            result.append((name, full, is_dir))

        spec = (order or '')[1:].replace(':', '')
        if order is not None and not spec:
            spec = 'gn'
        keys = re.findall(r'-?[a-z]', spec)
        result.sort(key=lambda e: e[0].lower())
        for k in reversed(keys):
            rev, letter = k.startswith('-'), k[-1]
            if letter == 'n':
                result.sort(key=lambda e: e[0].lower(), reverse=rev)
            elif letter == 'd':
                result.sort(key=lambda e: os.path.getmtime(e[1]), reverse=rev)
            elif letter == 's':
                result.sort(key=lambda e: 0 if e[2] else os.path.getsize(e[1]), reverse=rev)
            elif letter == 'e':
                result.sort(key=lambda e: os.path.splitext(e[0])[1].lower(), reverse=rev)
            elif letter == 'g':
                result.sort(key=lambda e: not e[2], reverse=rev)
        return result

    def _is_protected_dir(self, path):
        """Папки, которые нельзя удалить или переместить: корень диска, системные папки,
        папка пользователя, а также текущая папка и все папки на пути к ней."""
        p = os.path.normcase(os.path.abspath(path))
        protected = [self.workspace, os.path.join(self.workspace, 'Users'), self.home_dir,
                     os.path.join(self.workspace, 'Windows'), os.path.join(self.workspace, 'Program Files')]
        if p in (os.path.normcase(x) for x in protected):
            return "❌ Отказано в доступе."
        cur = os.path.normcase(os.path.abspath(self.current_dir))
        if cur == p or cur.startswith(p.rstrip(os.sep) + os.sep):
            return "❌ Процесс не может получить доступ к файлу, так как этот файл занят другим процессом."
        return None

    def _forget_attrs(self, path, new_path=None):
        """Убирает (или переносит на новый путь) симулируемые атрибуты файла или папки"""
        key = self._attr_key(path)
        for store in (self.hidden_files, self.readonly_files):
            for k in [k for k in store if k == key or k.startswith(key + os.sep)]:
                store.discard(k)
                if new_path is not None:
                    store.add(self._attr_key(new_path) + k[len(key):])

    def _expand_sources(self, name, include_dirs=False):
        """Файлы (и при include_dirs - папки), соответствующие имени или шаблону. Скрытые
        файлы по шаблону не выбираются, как в cmd. Возвращает (список путей, папка поиска)."""
        path = self._resolve_path(name, wildcard=True)
        base, pattern = os.path.dirname(path), os.path.basename(path)
        if self._has_wildcard(pattern):
            if not os.path.isdir(base):
                return [], base
            found = []
            for e in sorted(os.listdir(base), key=str.lower):
                full = os.path.join(base, e)
                if not fnmatch.fnmatchcase(e.lower(), pattern.lower()):
                    continue
                if os.path.isdir(full) and not include_dirs:
                    continue
                if self._attr_key(full) in self.hidden_files:
                    continue
                found.append(full)
            return found, base
        return ([path] if os.path.exists(path) else []), base

    def _target_blocked(self, target, shown):
        """Проверяет, можно ли записать файл target. Возвращает текст ошибки или None."""
        if os.path.isdir(target):
            return "❌ Отказано в доступе."
        if not os.path.isdir(os.path.dirname(target)):
            return "❌ Системе не удается найти указанный путь."
        if self._attr_key(target) in self.readonly_files or self._attr_key(target) in self.hidden_files:
            return "❌ Отказано в доступе."
        return None

    def _read_text_file(self, path):
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read().splitlines()

    @staticmethod
    def _find_ci(items, name):
        return next((x for x in items if x.lower() == name.lower()), None)

    def execute_quser(self, args):
        return self.execute_query(['user'] + list(args))

    def execute_exit(self, args):
        return "ℹ️ В настоящем терминале эта команда закрыла бы окно. В тренажёре окно не закрывается."

    def _run_line(self, cmd, rest):
        """Выполняет разобранную строку с учётом перенаправления вывода (> >> 2>).
        Возвращает (текст для терминала, известна ли команда)."""
        if re.fullmatch(r'[a-z]:', cmd) and not rest.strip():
            return ("", True) if cmd == 'c:' else ("❌ Системе не удается найти указанный диск.", True)
        if cmd not in self.KNOWN_COMMANDS:
            if not cmd:
                return "❌ Синтаксическая ошибка в команде.", False
            return (f"❌ \"{cmd}\" не является внутренней или внешней командой, исполняемой "
                    f"программой или пакетным файлом.", False)
        name = self.COMMAND_ALIASES.get(cmd, cmd)
        args, redirects, raw, error = self._parse_line(name, rest)
        if error:
            return error, True
        self._raw_args = raw

        if name not in self.RAW_COMMANDS:
            switches, _, _ = self._parse_args(name, args)
            if '?' in switches:
                return "ℹ️ Встроенная справка по ключам в тренажёре не выводится - загляни в теорию перед тестом", True
            bad = self._bad_switch(name, switches, args)
            if bad:
                return bad, True

        handler = getattr(self, f'execute_{name}')
        # Как и настоящий cmd, файлы для перенаправления открываются ДО запуска команды
        outputs, errors_to = [], None
        try:
            for op, target in redirects:
                shown = self._unq(target)
                if shown.lower() in ('con', 'con:'):
                    continue
                if shown.lower() in ('nul', 'nul:'):
                    if op.startswith('2'):
                        errors_to = 'nul'
                    else:
                        outputs.append((op, shown, None, False))
                    continue
                path = self._resolve_path(target)
                blocked = self._target_blocked(path, shown)
                if blocked:
                    return blocked, True
                existed = os.path.exists(path)
                with open(path, 'a' if op.endswith('>>') else 'w', encoding='utf-8'):
                    pass
                if op.startswith('2'):
                    errors_to = path
                else:
                    outputs.append((op, shown, path, existed))
        except _PathError as e:
            return f"❌ {e}", True

        try:
            output = handler(args)
        except _PathError as e:
            output = f"❌ {e}"
        except Exception as e:
            output = f"❌ Ошибка: {e}"

        if not outputs and errors_to is None:
            return output, True

        screen, data = [], []
        for line in output.split('\n') if output else []:
            (screen if line.startswith(('❌', 'ℹ️', '✅')) else data).append(line)
        if errors_to is not None:
            errors = [l for l in screen if l.startswith('❌')]
            screen = [l for l in screen if not l.startswith('❌')]
            if errors_to != 'nul':
                with open(errors_to, 'a', encoding='utf-8') as f:
                    f.write(''.join(l[2:] + '\n' for l in errors))
        if not outputs:
            return '\n'.join(screen), True

        op, shown, path, existed = outputs[-1]
        if path is None:
            return '\n'.join(screen), True
        text = '\n'.join(data)
        if text or (name == 'echo' and data):
            text += '\n'
        with open(path, 'a' if op == '>>' else 'w', encoding='utf-8') as f:
            f.write(text)
        if screen and any(l.startswith('❌') for l in screen) and not text:
            return '\n'.join(screen), True
        if not text:
            if op == '>>':
                note = f"✅ Файл '{shown}' не изменился: команда ничего не вывела"
            elif existed:
                note = f"✅ Файл '{shown}' очищен: команда ничего не вывела"
            else:
                note = f"✅ Создан пустой файл '{shown}'"
        else:
            what = 'Текст' if name == 'echo' else 'Вывод команды'
            verb = 'дописан в конец файла' if op == '>>' else 'записан в файл'
            note = f"✅ {what} {verb} '{shown}'"
        return '\n'.join(screen + [note]), True

    def execute_whoami(self, args):
        sw, pos, _ = self._parse_args('whoami', args)
        if pos:
            return f'❌ ОШИБКА: Недопустимый аргумент/параметр - "{pos[0]}".\nВведите "WHOAMI /?" для получения справки.'
        if 'groups' in sw:
            groups = [g for g, members in self.win_groups.items()
                      if self.username.lower() in (m.lower() for m in members)]
            lines = [
                "СВЕДЕНИЯ О ГРУППАХ",
                "------------------",
                "",
                "Группа                                 Тип                 SID          Атрибуты",
                "====================================== =================== ============ ==================================",
                "Все                                    Хорошо известная    S-1-1-0      Обязательная группа, Включены",
            ]
            sids = {'Administrators': 'S-1-5-32-544', 'Users': 'S-1-5-32-545', 'Guests': 'S-1-5-32-546'}
            for g in groups:
                name = f"BUILTIN\\{g}"
                lines.append(f"{name:<38} Псевдоним           {sids.get(g, 'S-1-5-21-1001'):<12} Обязательная группа, Включены")
            lines.append("NT AUTHORITY\\Прошедшие проверку        Хорошо известная    S-1-5-11     Обязательная группа, Включены")
            return '\n'.join(lines)
        if 'priv' in sw:
            return (
                "СВЕДЕНИЯ О ПРИВИЛЕГИЯХ\n"
                "----------------------\n\n"
                "Имя привилегии                Описание                                    Состояние\n"
                "============================= =========================================== ==========\n"
                "SeShutdownPrivilege           Завершение работы системы                   Отключен\n"
                "SeChangeNotifyPrivilege       Обход перекрестной проверки                 Включен\n"
                "SeUndockPrivilege             Отключение компьютера от стыковочной станции Отключен\n"
                "SeTimeZonePrivilege           Изменение часового пояса                    Отключен"
            )
        who = f"{self.hostname}\\{self.username}".lower()
        if 'user' in sw or 'all' in sw:
            return ("СВЕДЕНИЯ О ПОЛЬЗОВАТЕЛЕ\n-----------------------\n\n"
                    f"{'Пользователь':<25} SID\n{'=' * 25} {'=' * 45}\n"
                    f"{who:<25} S-1-5-21-1004336348-1177238915-682003330-1001")
        return who

    def execute_cd(self, args):
        text = self._raw_args.strip()
        text = re.sub(r'^/d(\s+|$)', '', text, flags=re.I).strip()
        text = self._unq(text).rstrip()
        if not text:
            return self._display_path(self.current_dir)
        if re.fullmatch(r'[A-Za-z]:', text):
            if text.upper() == 'C:':
                return self._display_path(self.current_dir)
            return "❌ Системе не удается найти указанный путь."
        target = self._resolve_path(text)
        if os.path.isdir(target):
            self.current_dir = target
            self.update_prompt()
            return ""
        if os.path.exists(target):
            return "❌ Неверно задано имя папки."
        return "❌ Системе не удается найти указанный путь."

    def execute_dir(self, args):
        sw, names, _ = self._parse_args('dir', args)
        attr = next((s.lower() for s in sw if s.lower().startswith('a')), None)
        order = next((s.lower() for s in sw if s.lower().startswith('o')), None)
        recursive = 's' in sw
        bare = 'b' in sw

        target = self._unq(names[0]) if names else ''
        path = self._resolve_path(target, wildcard=True) if target else self.current_dir
        if os.path.isdir(path):
            base, pattern = path, '*'
        else:
            base, pattern = os.path.dirname(path), os.path.basename(path)
        if not os.path.isdir(base):
            return "❌ Системе не удается найти указанный путь."

        header = [" Том в устройстве C не имеет метки.", " Серийный номер тома: 1A2B-3C4D", ""]
        free = "48 213 049 344"

        def line_for(name, full, is_dir):
            mtime = datetime.fromtimestamp(os.path.getmtime(full)).strftime('%d.%m.%Y  %H:%M')
            if is_dir:
                return f"{mtime}    <DIR>          {name}"
            return f"{mtime}    {self._fmt_num(os.path.getsize(full)):>14} {name}"

        dots_visible = pattern in ('*', '*.*') and attr is None or (attr == 'a' and pattern in ('*', '*.*'))

        if not recursive:
            entries = self._dir_entries(base, pattern, attr, order)
            if bare:
                if not entries:
                    return "Файл не найден"
                return '\n'.join(e[0] for e in entries)
            lines = header + [f" Содержимое папки {self._display_path(base)}", ""]
            shown = list(entries)
            if dots_visible and os.path.normcase(base) != os.path.normcase(self.workspace):
                shown = [('.', base, True), ('..', os.path.dirname(base), True)] + shown
            if not shown:
                return '\n'.join(lines + ["Файл не найден"])
            lines += [line_for(*e) for e in shown]
            files = [e for e in shown if not e[2]]
            dirs = [e for e in shown if e[2]]
            total = sum(os.path.getsize(e[1]) for e in files)
            lines.append(f"{len(files):>16} файлов {self._fmt_num(total):>14} байт")
            lines.append(f"{len(dirs):>16} папок {free:>15} байт свободно")
            return '\n'.join(lines)

        blocks, all_files, all_dirs, total = [], 0, 0, 0
        bare_lines = []
        for root, dirs, _files in os.walk(base):
            dirs[:] = sorted((d for d in dirs if attr is not None
                              or self._attr_key(os.path.join(root, d)) not in self.hidden_files),
                             key=str.lower)
            entries = self._dir_entries(root, pattern, attr, order)
            if bare:
                bare_lines += [self._display_path(e[1]) for e in entries]
                continue
            if not entries:
                continue
            shown = list(entries)
            if dots_visible and os.path.normcase(root) != os.path.normcase(self.workspace):
                shown = [('.', root, True), ('..', os.path.dirname(root), True)] + shown
            files = [e for e in shown if not e[2]]
            size = sum(os.path.getsize(e[1]) for e in files)
            all_files += len(files)
            all_dirs += len(shown) - len(files)
            total += size
            blocks += [f" Содержимое папки {self._display_path(root)}", ""]
            blocks += [line_for(*e) for e in shown]
            blocks += [f"{len(files):>16} файлов {self._fmt_num(size):>14} байт", ""]
        if bare:
            return '\n'.join(bare_lines) if bare_lines else "Файл не найден"
        if not blocks:
            return '\n'.join(header + ["Файл не найден"])
        return '\n'.join(header + blocks + [
            "     Всего файлов:",
            f"{all_files:>16} файлов {self._fmt_num(total):>14} байт",
            f"{all_dirs:>16} папок {free:>15} байт свободно",
        ])

    def execute_md(self, args):
        _, names, _ = self._parse_args('md', args)
        if not names:
            return "❌ Синтаксическая ошибка в команде."
        results = []
        for name in names:
            shown = self._unq(name)
            try:
                path = self._resolve_path(name)
            except _PathError as e:
                results.append(f"❌ {e}")
                continue
            if os.path.exists(path):
                results.append(f"❌ Подпапка или файл {shown} уже существует.")
                continue
            parent = os.path.dirname(path)
            while parent and not os.path.exists(parent):
                parent = os.path.dirname(parent)
            if parent and not os.path.isdir(parent):
                results.append("❌ Системе не удается найти указанный путь.")
                continue
            os.makedirs(path)
            results.append(f"✅ Папка '{shown}' создана")
        return '\n'.join(results)

    def execute_rd(self, args):
        sw, names, _ = self._parse_args('rd', args)
        if not names:
            return "❌ Синтаксическая ошибка в команде."
        results = []
        for name in names:
            shown = self._unq(name)
            try:
                path = self._resolve_path(name)
            except _PathError as e:
                results.append(f"❌ {e}")
                continue
            if not os.path.exists(path):
                results.append("❌ Системе не удается найти указанный файл.")
                continue
            if not os.path.isdir(path):
                results.append("❌ Неверно задано имя папки.")
                continue
            protected = self._is_protected_dir(path)
            if protected:
                results.append(protected)
                continue
            if 's' in sw:
                if 'q' not in sw:
                    results.append(
                        f"{shown}, вы уверены (Y/N)? \n"
                        "ℹ️ В настоящем терминале здесь нужно подтвердить удаление, нажав Y. "
                        "Тренажёр ввод с клавиатуры не поддерживает, поэтому папка НЕ удалена."
                    )
                    continue
                shutil.rmtree(path)
                self._forget_attrs(path)
                results.append(f"✅ Папка '{shown}' удалена вместе со всем содержимым")
            elif os.listdir(path):
                results.append("❌ Папка не пуста.")
            else:
                os.rmdir(path)
                self._forget_attrs(path)
                results.append(f"✅ Папка '{shown}' удалена")
        return '\n'.join(results)

    def execute_copy(self, args):
        sw, names, _ = self._parse_args('copy', args)
        names = [n for n in names if n != '+']
        if not names:
            return "❌ Синтаксическая ошибка в команде."
        if len(names) > 2:
            return "❌ Синтаксическая ошибка в команде."
        src_name = self._unq(names[0])
        dst_name = self._unq(names[1]) if len(names) > 1 else None
        none = "Скопировано файлов:         0."

        if src_name.lower() in ('nul', 'nul:', 'con', 'con:'):
            if not dst_name:
                return "❌ Синтаксическая ошибка в команде."
            target = self._resolve_path(dst_name)
            blocked = self._target_blocked(target, dst_name)
            if blocked:
                return f"{blocked}\n{none}"
            with open(target, 'w', encoding='utf-8'):
                pass
            if src_name.lower().startswith('con'):
                return ("ℹ️ В настоящем терминале после этой команды можно было бы набирать текст "
                        "построчно и закончить ввод сочетанием Ctrl+Z и Enter. Тренажёр ввод с "
                        "клавиатуры не поддерживает, поэтому файл создан пустым.\n"
                        "Скопировано файлов:         1.")
            return "Скопировано файлов:         1."

        src_path = self._resolve_path(src_name, wildcard=True)
        if os.path.isdir(src_path):
            sources = [os.path.join(src_path, e) for e in sorted(os.listdir(src_path), key=str.lower)
                       if os.path.isfile(os.path.join(src_path, e))]
            listed = True
        else:
            sources, _ = self._expand_sources(src_name)
            listed = self._has_wildcard(src_name)
        sources = [s for s in sources if os.path.isfile(s)]
        if not sources:
            return f"❌ Не удается найти указанный файл.\n{none}"

        dest = self._resolve_path(dst_name) if dst_name else self.current_dir
        if dst_name and not os.path.isdir(dest) and re.search(r'[\\/]$', dst_name):
            return f"❌ Системе не удается найти указанный путь.\n{none}"
        lines = [os.path.basename(s) for s in sources] if listed else []

        if not os.path.isdir(dest) and len(sources) > 1:
            blocked = self._target_blocked(dest, dst_name)
            if blocked:
                return f"{blocked}\n{none}"
            with open(dest, 'wb') as out:
                for s in sources:
                    with open(s, 'rb') as f:
                        out.write(f.read())
            return '\n'.join(lines + ["Скопировано файлов:         1."])

        copied = 0
        for s in sources:
            target = os.path.join(dest, os.path.basename(s)) if os.path.isdir(dest) else dest
            if os.path.normcase(os.path.abspath(target)) == os.path.normcase(os.path.abspath(s)):
                lines.append("❌ Файл не может быть скопирован сам в себя.")
                continue
            blocked = self._target_blocked(target, dst_name)
            if blocked:
                lines.append(blocked)
                continue
            if os.path.exists(target) and 'y' not in sw:
                lines.append(
                    f"Заменить {self._display_path(target)} [Yes (да)/No (нет)/All (все)]: \n"
                    "ℹ️ В настоящем терминале здесь нужно ответить на вопрос. Тренажёр ввод с "
                    "клавиатуры не поддерживает, поэтому файл НЕ заменён."
                )
                continue
            shutil.copyfile(s, target)
            shutil.copystat(s, target)
            copied += 1
        lines.append(f"Скопировано файлов: {copied:>9}.")
        return '\n'.join(lines)

    def execute_echo(self, args):
        raw = self._raw_args
        if not raw.strip() and not (raw[:1] and raw[0] in self.ECHO_DELIMS and raw[0] not in ' \t'):
            return "Режим вывода команд на экран (ECHO) включен."
        text = raw[1:] if raw[:1] and raw[0] in self.ECHO_DELIMS else raw
        if raw[:1] in (' ', '\t') and text.strip().lower() in ('on', 'off'):
            return "ℹ️ В тренажёре режим показа вводимых команд не переключается"
        return text

    def execute_type(self, args):
        _, names, _ = self._parse_args('type', args)
        if not names:
            return "❌ Синтаксическая ошибка в команде."
        several = len(names) > 1 or any(self._has_wildcard(n) for n in names)
        out = []
        for name in names:
            shown = self._unq(name)
            if shown.lower() in ('nul', 'nul:'):
                continue
            path = self._resolve_path(name, wildcard=True)
            if os.path.isdir(path):
                out.append("❌ Отказано в доступе.")
                continue
            files, _ = self._expand_sources(name)
            if not files:
                out.append("❌ Не удается найти указанный файл.")
                if several:
                    out.append(f"❌ Ошибка во время обработки: {shown}.")
                continue
            for f_path in files:
                with open(f_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                if several:
                    out.append(f"\n{os.path.basename(f_path)}\n\n")
                out.append(content[:-1] if content.endswith('\n') else content)
        return '\n'.join(out)

    def execute_del(self, args):
        sw, names, _ = self._parse_args('del', args)
        if not names:
            return "❌ Синтаксическая ошибка в команде."
        quiet = 'q' in sw
        force = 'f' in sw
        recursive = 's' in sw
        results = []
        for name in names:
            shown = self._unq(name)
            path = self._resolve_path(name, wildcard=True)
            if os.path.isdir(path):
                base, pattern = path, '*'
            else:
                base, pattern = os.path.dirname(path), os.path.basename(path)
            if not os.path.isdir(base):
                results.append("❌ Системе не удается найти указанный путь.")
                continue
            if (pattern in ('*', '*.*') or os.path.isdir(path)) and not quiet:
                results.append(
                    f"{self._display_path(os.path.join(base, '*'))}, вы уверены (Y/N)? \n"
                    "ℹ️ В настоящем терминале здесь нужно подтвердить удаление, нажав Y. "
                    "Тренажёр ввод с клавиатуры не поддерживает, поэтому файлы НЕ удалены."
                )
                continue
            dirs = [base]
            if recursive:
                dirs = [r for r, _, _ in os.walk(base)]
            removed, problems = 0, []
            for d in dirs:
                for e in sorted(os.listdir(d), key=str.lower):
                    full = os.path.join(d, e)
                    if os.path.isdir(full) or not fnmatch.fnmatchcase(e.lower(), pattern.lower()):
                        continue
                    key = self._attr_key(full)
                    if key in self.hidden_files:
                        continue
                    if key in self.readonly_files and not force:
                        problems.append(f"❌ Отказано в доступе - {self._display_path(full)}")
                        continue
                    os.remove(full)
                    self._forget_attrs(full)
                    removed += 1
                    if recursive:
                        results.append(f"Удален файл - {self._display_path(full)}")
            results += problems
            if removed and not recursive:
                results.append(f"✅ Удалено: {shown}")
            elif not removed and not problems:
                results.append(f"❌ Не удается найти {self._display_path(os.path.join(base, pattern))}")
        return '\n'.join(results)

    def execute_move(self, args):
        sw, names, _ = self._parse_args('move', args)
        if len(names) != 2:
            return "❌ Синтаксическая ошибка в команде."
        src_name, dst_name = self._unq(names[0]), self._unq(names[1])
        sources, _ = self._expand_sources(src_name, include_dirs=True)
        if not sources:
            return "❌ Не удается найти указанный файл."
        dest = self._resolve_path(dst_name)
        if len(sources) > 1 and not os.path.isdir(dest):
            return "❌ Невозможно переместить несколько файлов в один файл."
        files = dirs = 0
        lines = []
        for s in sources:
            is_dir = os.path.isdir(s)
            if is_dir:
                protected = self._is_protected_dir(s)
                if protected:
                    lines.append(protected)
                    continue
            target = os.path.join(dest, os.path.basename(s)) if os.path.isdir(dest) else dest
            same = os.path.normcase(os.path.abspath(target)) == os.path.normcase(os.path.abspath(s))
            if same:
                lines.append("❌ Файл не может быть перемещён сам в себя.")
                continue
            if is_dir and os.path.normcase(os.path.abspath(target)).startswith(
                    os.path.normcase(os.path.abspath(s)) + os.sep):
                lines.append("❌ Процесс не может получить доступ к файлу, так как этот файл занят другим процессом.")
                continue
            if not os.path.isdir(os.path.dirname(target)):
                lines.append("❌ Системе не удается найти указанный путь.")
                continue
            if os.path.exists(target):
                if is_dir or os.path.isdir(target):
                    lines.append("❌ Отказано в доступе.")
                    continue
                if 'y' not in sw:
                    lines.append(
                        f"Заменить {self._display_path(target)} [Yes (да)/No (нет)/All (все)]: \n"
                        "ℹ️ В настоящем терминале здесь нужно ответить на вопрос. Тренажёр ввод с "
                        "клавиатуры не поддерживает, поэтому файл НЕ перемещён."
                    )
                    continue
                os.remove(target)
                self._forget_attrs(target)
            shutil.move(s, target)
            self._forget_attrs(s, target)
            if is_dir:
                dirs += 1
            else:
                files += 1
        if dirs:
            lines.append(f"Перемещено папок: {dirs:>10}.")
        if files or not dirs:
            lines.append(f"Перемещено файлов: {files:>9}.")
        return '\n'.join(lines)

    def execute_ren(self, args):
        _, names, _ = self._parse_args('ren', args)
        if len(names) != 2:
            return "❌ Синтаксическая ошибка в команде."
        src_name, new_name = self._unq(names[0]), self._unq(names[1])
        if re.search(r'[\\/:]', new_name):
            return "❌ Синтаксическая ошибка в команде."
        if any(c in new_name for c in '<>"|') or (self._has_wildcard(new_name) and not self._has_wildcard(src_name)):
            return "❌ Синтаксическая ошибка в имени файла, имени папки или метке тома."
        sources, _ = self._expand_sources(src_name, include_dirs=True)
        if not sources:
            return "❌ Не удается найти указанный файл."
        results = []
        for s in sources:
            if self._has_wildcard(new_name):
                m = re.fullmatch(r'\*(\.[^*?]*)?', new_name)
                if not m:
                    results.append("❌ Дублирующееся имя файла или файл не найден.")
                    continue
                final = os.path.splitext(os.path.basename(s))[0] + (m.group(1) or '')
            else:
                final = new_name.rstrip(' .')
            if final.split('.')[0].strip().upper() in self.RESERVED_NAMES or not final:
                results.append("❌ Синтаксическая ошибка в имени файла, имени папки или метке тома.")
                continue
            if os.path.isdir(s):
                protected = self._is_protected_dir(s)
                if protected:
                    results.append(protected)
                    continue
            target = os.path.join(os.path.dirname(s), final)
            if os.path.exists(target) and final.lower() != os.path.basename(s).lower():
                results.append("❌ Дублирующееся имя файла или файл не найден.")
                continue
            tmp = target + '.~ren'
            os.rename(s, tmp)
            os.rename(tmp, target)
            self._forget_attrs(s, target)
            results.append(f"✅ '{os.path.basename(s)}' переименован в '{final}'")
        return '\n'.join(results)

    def execute_findstr(self, args):
        sw, pos, _ = self._parse_args('findstr', args)
        ignore_case = 'i' in sw
        show_numbers = 'n' in sw
        invert = 'v' in sw
        names_only = 'm' in sw
        literal_parts = [s[2:] for s in sw if s[:2].lower() == 'c:']
        if literal_parts:
            patterns = [self._unq(p) for p in literal_parts]
            files = pos
        else:
            if not pos:
                return "❌ FINDSTR: неверное число аргументов"
            patterns = self._unq(pos[0]).split()
            files = pos[1:]
        if not files:
            return "❌ Чтение с клавиатуры в тренажёре не поддерживается - укажи файл, в котором искать"
        if 's' in sw:
            found_files = []
            for name in files:
                path = self._resolve_path(name, wildcard=True)
                base, pattern = os.path.dirname(path), os.path.basename(path)
                for root, _, fs in os.walk(base):
                    for f in sorted(fs, key=str.lower):
                        if fnmatch.fnmatchcase(f.lower(), pattern.lower()):
                            found_files.append(os.path.join(root, f))
            targets = [(p, os.path.relpath(p, self.current_dir).replace(os.sep, '\\')) for p in found_files]
            prefix_names = True
        else:
            targets, prefix_names = [], len(files) > 1 or any(self._has_wildcard(f) for f in files)
            for name in files:
                matches, _ = self._expand_sources(name)
                matches = [m for m in matches if os.path.isfile(m)]
                if not matches:
                    return f"❌ FINDSTR: не удается открыть {self._unq(name)}"
                targets += [(m, os.path.basename(m) if self._has_wildcard(name) else self._unq(name)) for m in matches]
        needles = [p.lower() if ignore_case else p for p in patterns if p]
        results = []
        for path, shown in targets:
            hit_in_file = False
            for i, line in enumerate(self._read_text_file(path), 1):
                hay = line.lower() if ignore_case else line
                found = any(n in hay for n in needles)
                if found != invert:
                    hit_in_file = True
                    if names_only:
                        break
                    prefix = (f"{shown}:" if prefix_names else "") + (f"{i}:" if show_numbers else "")
                    results.append(prefix + line)
            if names_only and hit_in_file:
                results.append(shown)
        return '\n'.join(results) if results else "ℹ️ совпадений не найдено"

    def execute_find(self, args):
        sw, pos, _ = self._parse_args('find', args)
        if not pos or not (pos[0].startswith('"') and pos[0].endswith('"') and len(pos[0]) >= 2):
            return "❌ FIND: Неправильный формат параметра"
        needle = pos[0][1:-1]
        files = pos[1:]
        if not files:
            return "❌ Чтение с клавиатуры в тренажёре не поддерживается - укажи файл, в котором искать"
        ignore_case = 'i' in sw
        count_only = 'c' in sw
        invert = 'v' in sw
        numbers = 'n' in sw
        out = []
        for name in files:
            matches, _ = self._expand_sources(name)
            matches = [m for m in matches if os.path.isfile(m)]
            if not matches:
                out.append(f"❌ Файл не найден - {self._unq(name).upper()}")
                continue
            for path in matches:
                shown = (os.path.basename(path) if self._has_wildcard(name) else self._unq(name)).upper()
                hits = []
                for i, line in enumerate(self._read_text_file(path), 1):
                    found = (needle.lower() in line.lower()) if ignore_case else (needle in line)
                    if found != invert:
                        hits.append(f"[{i}]{line}" if numbers else line)
                if count_only:
                    out.append(f"\n---------- {shown}: {len(hits)}")
                else:
                    out.append(f"\n---------- {shown}")
                    out += hits
        return '\n'.join(out)

    def execute_sort(self, args):
        sw, names, values = self._parse_args('sort', args)
        reverse = 'r' in sw
        if not names:
            return "❌ Чтение с клавиатуры в тренажёре не поддерживается - укажи файл для сортировки"
        if len(names) > 1:
            return "❌ Неверный параметр"
        path = self._resolve_path(names[0])
        if not os.path.isfile(path):
            return "❌ Системе не удается найти указанный файл."
        lines = sorted(self._read_text_file(path), key=lambda s: s.lower(), reverse=reverse)
        output = values.get('o')
        if 'o' in sw:
            if not output:
                return "❌ Неверный параметр"
            target = self._resolve_path(output)
            blocked = self._target_blocked(target, output)
            if blocked:
                return blocked
            with open(target, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
            return f"✅ Отсортированные строки записаны в файл '{self._unq(output)}'"
        return '\n'.join(lines)

    def execute_more(self, args):
        _, names, _ = self._parse_args('more', args)
        if not names:
            return "❌ Чтение с клавиатуры в тренажёре не поддерживается - укажи файл для просмотра"
        out = []
        for name in names:
            path = self._resolve_path(name)
            if not os.path.isfile(path):
                return f"❌ Не удается получить доступ к файлу {self._display_path(path)}"
            out += self._read_text_file(path)
        return '\n'.join(out)

    def execute_fc(self, args):
        sw, names, _ = self._parse_args('fc', args)
        if len(names) < 2:
            return "❌ FC: недостаточно имён файлов"
        n1, n2 = self._unq(names[0]), self._unq(names[1])
        p1, p2 = self._resolve_path(n1), self._resolve_path(n2)
        for p, n in ((p1, n1), (p2, n2)):
            if not os.path.isfile(p):
                return f"❌ FC: не удается открыть {n.upper()} - нет такого файла или папки"
        header = f"Сравнение файлов {n1} и {n2.upper()}"
        if 'b' in sw:
            with open(p1, 'rb') as f:
                b1 = f.read()
            with open(p2, 'rb') as f:
                b2 = f.read()
            if b1 == b2:
                return f"{header}\nFC: различия не найдены"
            lines = [header]
            for i, (x, y) in enumerate(zip(b1, b2)):
                if x != y:
                    lines.append(f"{i:08X}: {x:02X} {y:02X}")
            if len(b1) != len(b2):
                longer = n1 if len(b1) > len(b2) else n2
                lines.append(f"FC: {longer.upper()} длиннее, чем {(n2 if longer == n1 else n1).upper()}")
            return '\n'.join(lines)

        a, b = self._read_text_file(p1), self._read_text_file(p2)
        ca = [x.lower() for x in a] if 'c' in sw else a
        cb = [x.lower() for x in b] if 'c' in sw else b
        blocks = [op for op in difflib.SequenceMatcher(None, ca, cb, autojunk=False).get_opcodes() if op[0] != 'equal']
        if not blocks:
            return f"{header}\nFC: различия не найдены"

        def fmt(lines, start, end, name):
            out = [f"***** {name}"]
            for i in range(max(0, start - 1), min(len(lines), end + 1)):
                out.append(f"{i + 1:>5}:  {lines[i]}" if 'n' in sw else lines[i])
            return out

        out = [header]
        for _, i1, i2, j1, j2 in blocks:
            out += fmt(a, i1, i2, n1) + fmt(b, j1, j2, n2.upper()) + ["*****", ""]
        return '\n'.join(out).rstrip('\n')

    def execute_comp(self, args):
        sw, names, _ = self._parse_args('comp', args)
        if len(names) < 2:
            return "❌ Чтение имён файлов с клавиатуры в тренажёре не поддерживается - укажи два файла"
        n1, n2 = self._unq(names[0]), self._unq(names[1])
        p1, p2 = self._resolve_path(n1), self._resolve_path(n2)
        for p, n in ((p1, n1), (p2, n2)):
            if not os.path.isfile(p):
                return f"❌ Не удается найти или открыть {n}"
        with open(p1, 'rb') as f:
            b1 = f.read()
        with open(p2, 'rb') as f:
            b2 = f.read()
        lines = [f"Сравнение {n1} и {n2}..."]
        if len(b1) != len(b2):
            lines.append("Файлы имеют разные размеры.")
        else:
            diffs = [i for i, (x, y) in enumerate(zip(b1, b2)) if x != y]
            if not diffs:
                lines.append("Сравнение файлов завершено: файлы совпадают")
            for i in diffs[:10]:
                lines += [f"Несовпадение в СМЕЩЕНИИ {i:X}", f"файл1 = {b1[i]:X}", f"файл2 = {b2[i]:X}"]
            if len(diffs) > 10:
                lines.append("10 несовпадений - сравнение прекращено")
        if 'm' not in sw:
            lines += ["", "Сравнить другие файлы (Y/N) ? ",
                      "ℹ️ В настоящем терминале здесь нужно ответить N. Тренажёр ввод с клавиатуры "
                      "не поддерживает, поэтому сравнение просто завершено."]
        return '\n'.join(lines)

    def execute_where(self, args):
        sw, names, _ = self._parse_args('where', args)
        if not names:
            return "❌ ОШИБКА: Неверный синтаксис. Требуется указать шаблон для поиска.\nВведите \"WHERE /?\" для получения справки."
        found = []
        for name in names:
            pattern = self._unq(name).lower()
            exts = [''] if '.' in pattern or self._has_wildcard(pattern) else ['.com', '.exe', '.bat', '.cmd']
            for e in sorted(os.listdir(self.current_dir), key=str.lower):
                full = os.path.join(self.current_dir, e)
                if os.path.isfile(full) and any(fnmatch.fnmatchcase(e.lower(), pattern + x) for x in exts):
                    found.append(self._display_path(full))
            for prog, paths in self.WHERE_PROGRAMS.items():
                if any(fnmatch.fnmatchcase(prog, pattern + x) for x in exts):
                    found += paths
        if not found:
            return "ℹ️ ИНФОРМАЦИЯ: не удается найти файлы по заданным шаблонам."
        return '\n'.join(found)

    def execute_tree(self, args):
        sw, names, _ = self._parse_args('tree', args)
        start = self._resolve_path(names[0]) if names else self.current_dir
        if not os.path.isdir(start):
            return f"❌ Недопустимый путь - {self._display_path(start)[2:].upper()}"
        show_files = 'f' in sw
        ascii_mode = 'a' in sw
        tee, last, pipe = ('+---', '\\---', '|   ') if ascii_mode else ('├───', '└───', '│   ')
        lines = ["Структура папок", "Серийный номер тома: 1A2B-3C4D",
                 self._display_path(start).upper() if names else "C:."]
        has_subdirs = False

        def walk(path, prefix):
            nonlocal has_subdirs
            entries = sorted(os.listdir(path), key=str.lower)
            subdirs = [e for e in entries if os.path.isdir(os.path.join(path, e))
                       and self._attr_key(os.path.join(path, e)) not in self.hidden_files]
            if show_files:
                files = [e for e in entries if os.path.isfile(os.path.join(path, e))
                         and self._attr_key(os.path.join(path, e)) not in self.hidden_files]
                for f in files:
                    lines.append(f"{prefix}{pipe if subdirs else '    '}{f}")
                if files:
                    lines.append(f"{prefix}{pipe if subdirs else '    '}".rstrip())
            for i, d in enumerate(subdirs):
                has_subdirs = True
                is_last = i == len(subdirs) - 1
                lines.append(f"{prefix}{last if is_last else tee}{d}")
                walk(os.path.join(path, d), prefix + ('    ' if is_last else pipe))

        walk(start, '')
        if not has_subdirs:
            lines.append("Вложенные папки отсутствуют")
        return '\n'.join(lines)

    def execute_attrib(self, args):
        flags = [a.lower() for a in args if re.fullmatch(r'[+-][rahsi]', a, re.I)]
        rest = [a for a in args if not re.fullmatch(r'[+-][rahsi]', a, re.I)]
        sw, names, _ = self._parse_args('attrib', rest)
        bad = [a for a in names if a[:1] in '+-']
        if bad:
            return f"❌ Недопустимый параметр - {bad[0]}"

        def line_for(full):
            key = self._attr_key(full)
            h = 'H' if key in self.hidden_files else ' '
            r = 'R' if key in self.readonly_files else ' '
            a = ' ' if os.path.isdir(full) else 'A'
            return f"{a}    {h}{r}       {self._display_path(full)}"

        if not names:
            if flags:
                return "❌ Требуется указать имя файла"
            entries = sorted(os.listdir(self.current_dir), key=str.lower)
            return '\n'.join(line_for(os.path.join(self.current_dir, e)) for e in entries
                             if os.path.isfile(os.path.join(self.current_dir, e)))
        results = []
        for name in names:
            shown = self._unq(name)
            path = self._resolve_path(name, wildcard=True)
            if self._has_wildcard(os.path.basename(path)):
                base, pattern = os.path.dirname(path), os.path.basename(path).lower()
                matches = [os.path.join(base, e) for e in sorted(os.listdir(base), key=str.lower)
                           if fnmatch.fnmatchcase(e.lower(), pattern)
                           and (os.path.isfile(os.path.join(base, e)) or 'd' in sw)] if os.path.isdir(base) else []
            else:
                matches = [path] if os.path.exists(path) else []
            if not matches:
                results.append(f"❌ Файл не найден - {shown}")
                continue
            for full in matches:
                key = self._attr_key(full)
                if not flags:
                    results.append(line_for(full))
                    continue
                touches_hs = any(f[1] in 'hs' for f in flags)
                if key in self.hidden_files and not touches_hs:
                    results.append(f"❌ Не сброшен атрибут скрытого файла - {self._display_path(full)}")
                    continue
                for f in flags:
                    store = {'h': self.hidden_files, 'r': self.readonly_files}.get(f[1])
                    if store is None:
                        continue
                    if f[0] == '+':
                        store.add(key)
                    else:
                        store.discard(key)
                results.append(f"✅ Атрибуты '{os.path.basename(full)}' изменены: {' '.join(flags)}")
        return '\n'.join(results)

    def execute_icacls(self, args):
        sw, names, values = self._parse_args('icacls', args)
        if not names:
            return "❌ Не указано имя файла или папки"
        shown = self._unq(names[0])
        path = self._resolve_path(names[0], wildcard=True)
        if not os.path.exists(path):
            return (f"❌ {shown}: Не удается найти указанный файл.\n"
                    "Успешно обработано 0 файлов; не удалось обработать 1 файлов")
        key = self._attr_key(path)
        grant_key = next((s.split(':')[0] for s in sw if s.split(':')[0].lower() == 'grant'), None)
        if grant_key:
            value = self._unq(values.get('grant') or '')
            m = re.fullmatch(r'([^:]+):((?:\((?:OI|CI|IO|NP|I)\))*)\(?((?:F|M|RX|R|W|D|N)(?:,(?:F|M|RX|R|W|D|N))*)\)?',
                             value, re.I)
            if not m:
                return f"❌ Недопустимый параметр \"{value}\""
            user, perm = m.group(1), m.group(3).upper()
            known = {'users', 'administrators', 'guests', 'everyone', 'все', 'system', 'authenticated users'}
            known |= {u.lower() for u in self.win_users} | {g.lower() for g in self.win_groups}
            if user.lower() not in known:
                return (f"❌ {user}: Сопоставление между именами учетных записей и идентификаторами "
                        "безопасности не было произведено.\n"
                        "Успешно обработано 0 файлов; не удалось обработать 1 файлов")
            self.acl_grants.setdefault(key, []).append((user, m.group(2).upper() + f"({perm})"))
            return f"обработанный файл: {shown}\nУспешно обработано 1 файлов; не удалось обработать 0 файлов"
        if sw and not all(s.lower() in ('t', 'c', 'l', 'q') for s in sw):
            return "ℹ️ Этот ключ в тренажёре не поддерживается - доступны просмотр прав и выдача права"
        entries = ["NT AUTHORITY\\SYSTEM:(I)(F)", "BUILTIN\\Administrators:(I)(F)",
                   f"{self.hostname}\\{self.username}:(I)(F)"]
        for user, perm in self.acl_grants.get(key, []):
            prefix = 'BUILTIN\\' if user.lower() in ('users', 'administrators', 'guests') else ''
            entries.insert(0, f"{prefix}{user}:{perm}")
        pad = ' ' * (len(shown) + 1)
        lines = [f"{shown} {entries[0]}"] + [pad + e for e in entries[1:]]
        return '\n'.join(lines) + "\n\nУспешно обработано 1 файлов; не удалось обработать 0 файлов"

    def execute_takeown(self, args):
        sw, pos, values = self._parse_args('takeown', args)
        help_line = 'Введите "TAKEOWN /?" для получения справки.'
        if pos:
            return f"❌ ОШИБКА: Недопустимый аргумент/параметр - '{pos[0]}'.\n{help_line}"
        if 'f' not in values:
            return f"❌ ОШИБКА: Неверный синтаксис. Отсутствует обязательный параметр '/F'.\n{help_line}"
        if not values['f']:
            return f"❌ ОШИБКА: Неверный синтаксис. Для параметра '/F' требуется значение.\n{help_line}"
        path = self._resolve_path(values['f'], wildcard=True)
        if not os.path.exists(path):
            return "❌ ОШИБКА: Системе не удается найти указанный файл."
        return (f'УСПЕХ: Файл (или папка): "{self._display_path(path)}" теперь принадлежит '
                f'пользователю "{self.hostname}\\{self.username}".')

    def execute_hostname(self, args):
        return self.hostname

    def execute_ver(self, args):
        return "Microsoft Windows [Version 10.0.19045.4046]"

    def execute_systeminfo(self, args):
        return (
            f"Имя узла:                    {self.hostname}\n"
            f"Имя ОС:                      Microsoft Windows 10 Pro\n"
            f"Версия ОС:                   10.0.19045\n"
            f"Изготовитель ОС:             Microsoft Corporation\n"
            f"Тип системы:                 x64-based PC\n"
            f"Объем физической памяти:     16 384 МБ\n"
            f"Доступно физической памяти:  9 216 МБ\n"
            f"Часовой пояс:                (UTC+03:00)"
        )

    def execute_date(self, args):
        sw, pos, _ = self._parse_args('date', args)
        now = datetime.now()
        if 't' in sw:
            return now.strftime('%d.%m.%Y')
        if pos:
            return "❌ Клиент не обладает требуемыми правами."
        return (f"Текущая дата: {now.strftime('%d.%m.%Y')}\n"
                "Введите новую дату (дд-мм-гг): \n"
                "ℹ️ В настоящем терминале здесь можно ввести новую дату или нажать Enter, чтобы "
                "оставить прежнюю. Тренажёр ввод с клавиатуры не поддерживает - дата не изменена.")

    def execute_time(self, args):
        sw, pos, _ = self._parse_args('time', args)
        now = datetime.now()
        if 't' in sw:
            return now.strftime('%H:%M')
        if pos:
            return "❌ Клиент не обладает требуемыми правами."
        return (f"Текущее время: {now.strftime('%H:%M:%S')},{now.microsecond // 10000:02d}\n"
                "Введите новое время: \n"
                "ℹ️ В настоящем терминале здесь можно ввести новое время или нажать Enter, чтобы "
                "оставить прежнее. Тренажёр ввод с клавиатуры не поддерживает - время не изменено.")

    def execute_vol(self, args):
        return " Том в устройстве C не имеет метки.\n Серийный номер тома: 1A2B-3C4D"

    def execute_set(self, args):
        text = self._raw_args
        if text[:1] in (' ', '\t'):
            text = text[1:]
        text = text.lstrip()
        if re.match(r'/[ap]\b', text, re.I):
            return "ℹ️ Ключи этой команды в тренажёре не поддерживаются"
        env = self._env()
        if not text.strip():
            return '\n'.join(f"{k}={v}" for k, v in sorted(env.items(), key=lambda kv: kv[0].upper()))
        if '=' in text:
            name, value = text.split('=', 1)
            if not name.strip():
                return "❌ Синтаксическая ошибка в команде."
            if name.upper() == 'PATH':
                self.custom_path = value
                return f"✅ Переменная Path = {value}"
            if value == '':
                if not any(k.upper() == name.upper() for k in env):
                    return f"❌ Переменная среды {name} не определена"
                self.custom_env.pop(name.upper(), None)
                return f"✅ Переменная {name} удалена"
            self.custom_env[name.upper()] = (name, value)
            if name != name.rstrip() or value != value.lstrip():
                return (f"✅ Создана переменная «{name}» со значением «{value}»\n"
                        "ℹ️ Пробелы вокруг знака = cmd считает частью имени и значения, поэтому "
                        f"это НЕ переменная {name.strip()}")
            return f"✅ Переменная {name} = {value}"
        prefix = text.rstrip()
        matches = [(k, v) for k, v in sorted(env.items(), key=lambda kv: kv[0].upper())
                   if k.upper().startswith(prefix.upper())]
        if not matches:
            return f"❌ Переменная среды {prefix} не определена"
        return '\n'.join(f"{k}={v}" for k, v in matches)

    def execute_path(self, args):
        text = self._raw_args.strip()
        if text.startswith('='):
            text = text[1:].strip()
        if not text:
            return f"PATH={self.custom_path}" if self.custom_path else "Нет пути"
        if text == ';':
            self.custom_path = ''
            return "✅ Список папок для поиска программ очищен"
        self.custom_path = text
        return f"✅ PATH={self.custom_path}"

    def execute_tasklist(self, args):
        sw, _, _ = self._parse_args('tasklist', args)
        if 'svc' in sw:
            return (
                "\nИмя образа                     PID Службы\n"
                "========================= ======== ============================================\n"
                "System Idle Process              0 Н/Д\n"
                "svchost.exe                   1044 Dhcp, Dnscache\n"
                "notepad.exe                   1234 Н/Д\n"
                "explorer.exe                  2312 Н/Д\n"
                "trainer.exe                   3456 Н/Д"
            )
        if 'v' in sw:
            user = f"{self.hostname}\\{self.username}"
            rows = [
                ("System Idle Process", 0, "Services", 0, "8 КБ", "Unknown", "NT AUTHORITY\\SYSTEM", "12:31:07", "Н/Д"),
                ("notepad.exe", 1234, "Console", 1, "14 208 КБ", "Running", user, "0:00:01", "Безымянный — Блокнот"),
                ("explorer.exe", 2312, "Console", 1, "45 236 КБ", "Running", user, "0:01:12", "Н/Д"),
                ("trainer.exe", 3456, "Console", 1, "28 112 КБ", "Running", user, "0:00:09", "Тренажер командной строки Windows"),
            ]
            lines = ["", f"{'Имя образа':<25} {'PID':>8} {'Имя сессии':<16} {'№ сеанса':>11} {'Память':>12} "
                         f"{'Состояние':<15} {'Пользователь':<30} {'Время ЦП':>9} Заголовок окна",
                     f"{'=' * 25} {'=' * 8} {'=' * 16} {'=' * 11} {'=' * 12} {'=' * 15} {'=' * 30} {'=' * 9} {'=' * 20}"]
            for r in rows:
                lines.append(f"{r[0]:<25} {r[1]:>8} {r[2]:<16} {r[3]:>11} {r[4]:>12} {r[5]:<15} {r[6]:<30} {r[7]:>9} {r[8]}")
            return '\n'.join(lines)
        return (
            "\nИмя образа                     PID Имя сессии         № сеанса       Память\n"
            "========================= ======== ================ =========== ============\n"
            "System Idle Process              0 Services                   0         8 КБ\n"
            "svchost.exe                   1044 Services                   0    22 480 КБ\n"
            "notepad.exe                   1234 Console                    1    14 208 КБ\n"
            "explorer.exe                  2312 Console                    1    45 236 КБ\n"
            "trainer.exe                   3456 Console                    1    28 112 КБ"
        )

    def execute_taskkill(self, args):
        sw, pos, values = self._parse_args('taskkill', args)
        help_line = 'Введите "TASKKILL /?" для получения справки.'
        if pos:
            return f"❌ ОШИБКА: Недопустимый аргумент/параметр - '{pos[0]}'.\n{help_line}"
        force = 'f' in sw
        results = []
        if 'pid' in values:
            pid = values['pid']
            if not pid:
                return f"❌ ОШИБКА: Неверный синтаксис. Для параметра '/pid' требуется значение.\n{help_line}"
            if not pid.isdigit():
                return f"❌ ОШИБКА: Процесс \"{pid}\" не найден."
            if force:
                results.append(f"УСПЕХ: Процесс с идентификатором {pid} был завершен.")
            else:
                results.append(f"УСПЕХ: Отправлен сигнал завершения процессу с идентификатором {pid}.")
        if 'im' in values:
            name = self._unq(values['im'] or '')
            if not name:
                return f"❌ ОШИБКА: Неверный синтаксис. Для параметра '/im' требуется значение.\n{help_line}"
            if force:
                results.append(f"УСПЕХ: Процесс \"{name}\", с идентификатором 1234, был завершен.")
            else:
                results.append(f"УСПЕХ: Отправлен сигнал завершения процессу \"{name}\" с идентификатором 1234.")
        if not results:
            return f"❌ ОШИБКА: Неверный синтаксис. Не указан ни один из параметров /PID или /IM.\n{help_line}"
        return '\n'.join(results)

    def execute_shutdown(self, args):
        sw, pos, values = self._parse_args('shutdown', args)
        if 'a' in sw:
            if not self.shutdown_pending:
                return "❌ Не удается прервать завершение работы системы, так как оно не выполнялось.(1116)"
            self.shutdown_pending = None
            return "✅ Запланированное завершение работы отменено (Выход из системы отменен)."
        action = next((a for a in ('r', 's', 'l', 'h') if a in sw), None)
        if not action:
            return "❌ Не указано действие: перезагрузка, выключение, выход из системы или отмена"
        delay = values.get('t', '30' if action in ('r', 's') else '0')
        if delay is None or not str(delay).isdigit():
            return "❌ Недопустимый параметр.(87)"
        what = {'r': 'перезагрузка', 's': 'выключение', 'l': 'выход из системы', 'h': 'переход в спящий режим'}[action]
        if self.shutdown_pending:
            return "❌ Завершение работы системы уже запланировано.(1190)"
        note = "ℹ️ Это учебная симуляция - по-настоящему компьютер ничего не делает."
        if int(delay) == 0:
            return f"✅ {what.capitalize()} выполняется немедленно - отменить её уже нельзя.\n{note}"
        self.shutdown_pending = action
        return f"✅ Запланирована {what} через {int(delay)} с. До этого момента действие можно отменить.\n{note}"

    def execute_ipconfig(self, args):
        return (
            "Настройка IP для Windows\n\n"
            "Адаптер Ethernet Ethernet:\n\n"
            "   IPv4-адрес. . . . . . . . . . . : 192.168.1.42\n"
            "   Маска подсети . . . . . . . . . : 255.255.255.0\n"
            "   Основной шлюз . . . . . . . . . : 192.168.1.1"
        )

    def execute_ping(self, args):
        hosts = [a for a in args if not a.startswith('-') and not a.startswith('/')]
        if not hosts:
            return "❌ Необходимо указать IP-адрес."
        host = hosts[0]
        ip = host if re.fullmatch(r'\d+\.\d+\.\d+\.\d+', host) else '93.184.216.34'
        shown = host if host == ip else f"{host} [{ip}]"
        lines = [f"Обмен пакетами с {shown} с 32 байтами данных:"]
        for t in (12, 14, 11, 13):
            lines.append(f"Ответ от {ip}: число байт=32 время={t}мс TTL=117")
        lines += ["", f"Статистика Ping для {ip}:",
                  "    Пакетов: отправлено = 4, получено = 4, потеряно = 0",
                  "    (0% потерь)",
                  "Приблизительное время приема-передачи в мс:",
                  "    Минимальное = 11мсек, Максимальное = 14 мсек, Среднее = 12 мсек"]
        return '\n'.join(lines)

    def execute_netstat(self, args):
        return (
            "Активные подключения\n\n"
            "  Имя   Локальный адрес      Внешний адрес        Состояние\n"
            "  TCP   192.168.1.42:51032   140.82.121.4:443     ESTABLISHED\n"
            "  TCP   192.168.1.42:51044   192.168.1.1:80       TIME_WAIT\n"
            "  TCP   127.0.0.1:3306       127.0.0.1:51050      LISTENING"
        )

    def execute_nslookup(self, args):
        if not args:
            return "❌ nslookup: не указано имя узла"
        host = args[0]
        return (
            "Сервер:  resolver1.trainer.local\n"
            "Address:  192.168.1.1\n\n"
            "Non-authoritative answer:\n"
            f"Имя:    {host}\n"
            "Address:  93.184.216.34"
        )

    def execute_tracert(self, args):
        hosts = [a for a in args if not a.startswith('-') and not a.startswith('/')]
        if not hosts:
            return "❌ Не указан узел назначения"
        host = hosts[0]
        ip = host if re.fullmatch(r'\d+\.\d+\.\d+\.\d+', host) else '93.184.216.34'
        shown = host if host == ip else f"{host} [{ip}]"
        lines = [f"Трассировка маршрута к {shown}", "с максимальным числом прыжков 30:", ""]
        for i, h in enumerate(["192.168.1.1", "10.10.0.1", "172.16.5.9", ip], 1):
            lines.append(f"  {i}    {2 * i} ms    {2 * i + 1} ms    {2 * i} ms  {h}")
        lines += ["", "Трассировка завершена."]
        return '\n'.join(lines)

    def execute_net(self, args):
        sw, pos, _ = self._parse_args('net', args)
        if not pos:
            return "❌ Синтаксис данной команды:\n\nNET\n    [ ACCOUNTS | COMPUTER | CONFIG | CONTINUE | FILE | GROUP | HELP |\n      HELPMSG | LOCALGROUP | PAUSE | SESSION | SHARE | START |\n      STATISTICS | STOP | TIME | USE | USER | VIEW ]"
        sub = pos[0].lower()
        rest = [self._unq(p) for p in pos[1:]]
        ok = "Команда выполнена успешно."
        add, delete = 'add' in sw, 'delete' in sw
        line = '-' * 79
        if sub in ('user', 'users'):
            if not rest:
                names = sorted(self.win_users, key=str.lower)
                rows = [''.join(f"{n:<25}" for n in names[i:i + 3]).rstrip() for i in range(0, len(names), 3)]
                return '\n'.join([f"\nУчетные записи пользователей для \\\\{self.hostname}", "", line] + rows + [ok])
            name = rest[0]
            existing = self._find_ci(self.win_users, name)
            if add:
                if len(rest) > 2:
                    return "❌ Синтаксическая ошибка в команде."
                if existing:
                    return "❌ Учетная запись уже существует.\n\nДля вызова дополнительной справки наберите NET HELPMSG 2224."
                if re.search(r'[\\/\[\]:;|=,+*?<>"@]', name):
                    return "❌ Недопустимое имя пользователя."
                self.win_users.append(name)
                self.win_groups['Users'].append(name)
                return ok
            if not existing:
                return "❌ Не найдено имя пользователя.\n\nДля вызова дополнительной справки наберите NET HELPMSG 2221."
            if delete:
                if existing.lower() == self.username.lower():
                    return "❌ Нельзя удалить учётную запись, под которой выполнен вход."
                self.win_users.remove(existing)
                for members in self.win_groups.values():
                    if existing in members:
                        members.remove(existing)
                return ok
            if len(rest) >= 2:
                return ok
            groups = [g for g, m in self.win_groups.items() if existing in m]
            return (f"Имя пользователя                  {existing}\n"
                    f"Учетная запись активна            {'Нет' if existing in ('Guest', 'DefaultAccount') else 'Да'}\n"
                    f"Членство в локальных группах      {'  '.join('*' + g for g in groups) or '*Нет'}\n{ok}")
        if sub == 'localgroup':
            if not rest:
                rows = [f"*{g}" for g in sorted(self.win_groups, key=str.lower)]
                return '\n'.join([f"\nПсевдонимы для \\\\{self.hostname}", "", line] + rows + [ok])
            group = self._find_ci(self.win_groups, rest[0])
            if (add or delete) and len(rest) == 1:
                if add:
                    if group:
                        return "❌ Указанная локальная группа уже существует.\n\nДля вызова дополнительной справки наберите NET HELPMSG 1379."
                    self.win_groups[rest[0]] = []
                    return ok
                if not group:
                    return "❌ Указанная локальная группа не существует.\n\nДля вызова дополнительной справки наберите NET HELPMSG 1376."
                if group in ('Administrators', 'Users', 'Guests'):
                    return "❌ Системная ошибка 1320.\n\nВстроенную группу удалить нельзя."
                del self.win_groups[group]
                return ok
            if not group:
                return "❌ Указанная локальная группа не существует.\n\nДля вызова дополнительной справки наберите NET HELPMSG 1376."
            if add or delete:
                for user_name in rest[1:]:
                    user = self._find_ci(self.win_users, user_name)
                    if not user:
                        return ("❌ Системная ошибка 1332.\n\nСопоставление между именами учетных записей "
                                "и идентификаторами безопасности не было произведено.")
                    members = self.win_groups[group]
                    if add and user in members:
                        return "❌ Системная ошибка 1378.\n\nУказанная учетная запись уже является членом группы."
                    if delete and user not in members:
                        return "❌ Системная ошибка 1377.\n\nУказанная учетная запись не является членом группы."
                    if add:
                        members.append(user)
                    else:
                        members.remove(user)
                return ok
            members = self.win_groups[group]
            return '\n'.join([f"Псевдоним     {group}", "Комментарий", "", "Члены", "", line] + members + [ok])
        return f"❌ Синтаксическая ошибка в команде: неизвестная подкоманда {pos[0]}"

    def execute_query(self, args):
        if not args or args[0].lower() != 'user':
            return "❌ Недопустимый параметр.\nQUERY { PROCESS | SESSION | TERMSERVER | USER }"
        return (
            " ПОЛЬЗОВАТЕЛЬ          СЕАНС              ID  СТАТУС  БЕЗДЕЙСТВ. ВРЕМЯ ВХОДА\n"
            f">{self.username.lower():<21} console             1  Активно      нет   "
            f"{datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

    def execute_doskey(self, args):
        sw, _, _ = self._parse_args('doskey', args)
        if 'history' not in sw:
            return "ℹ️ В тренажёре эта команда умеет только показывать историю введённых команд"
        return '\n'.join(self.history)

    def execute_title(self, args):
        raw = self._raw_args
        text = (raw[1:] if raw[:1] and raw[0] in self.ECHO_DELIMS else raw).rstrip()
        try:
            self.root.title(text if text else "🪟 Тренажер командной строки Windows")
        except Exception:
            pass
        return f"✅ Заголовок окна изменён на: {text}"

    def execute_color(self, args):
        _, pos, _ = self._parse_args('color', args)
        if not pos:
            return "✅ Цвета консоли возвращены к стандартным"
        code = pos[0]
        if not re.fullmatch(r'[0-9a-fA-F]{1,2}', code) or len(pos) > 1:
            return "❌ Неверный код цвета: нужна одна или две шестнадцатеричные цифры (0-9, A-F)"
        if len(code) == 2 and code[0].lower() == code[1].lower():
            return "❌ Цвет текста и цвет фона совпадают - цвета не изменены"
        return f"✅ Цветовая схема консоли изменена на {code.upper()}"

    def execute_command(self, event=None):
        """Выполняет команду"""
        if self.lesson_completed or self.lesson_failed:
            return

        command = self.command_entry.get().strip()
        if not command:
            return

        self.command_entry.delete(0, tk.END)
        self.history.append(command)

        self.output_text.insert(tk.END, f"\n{self._display_path(self.current_dir)}> {command}\n")
        self.output_text.see(tk.END)

        cmd, rest = self._split_line(self._expand_vars(command))

        if cmd == 'cls':
            self.clear_output()
            return

        if cmd == 'help':
            self.show_help()
            return

        result, is_known_command = self._run_line(cmd, rest)
        result = self._hide_real_paths(result)

        if result:
            self.output_text.insert(tk.END, f"{result}\n")

        self.output_text.see(tk.END)

        self.stats['attempts'] += 1
        self.update_stats()

        if is_known_command:
            self.check_lesson_completion(command, result)
        else:
            self.handle_failed_attempt(command)

        # Принудительно дорисовываем интерфейс сразу - без этого на некоторых
        # системах виджеты вроде steps_info иногда визуально не успевали
        # обновиться сразу после .config(), хотя значение уже было верным
        self.root.update_idletasks()

    def check_lesson_completion(self, command, result):
        """Проверяет выполнение задания"""
        if self.current_lesson >= len(self.lessons):
            return

        if self.lesson_completed or self.lesson_failed:
            return

        lesson = self.lessons[self.current_lesson]
        steps = lesson['steps']

        if self.step_counter < len(steps):
            expected_step = steps[self.step_counter]

            if self._step_matches(command, expected_step):
                if result and '❌' in result:
                    # Команда верная, но выполнилась с ошибкой (обычно из-за того, что
                    # раньше что-то сделали не по порядку). Засчитывать шаг, когда
                    # терминал показывает ошибку, нельзя - это сбивает с толку.
                    self.output_text.insert(
                        tk.END,
                        "\nℹ️ Команда введена верно, но выполнилась с ошибкой (см. сообщение выше) - "
                        "скорее всего, из-за предыдущих команд. Шаг не засчитан, попытка не потрачена. "
                        "Нажми «Сброс», чтобы вернуть учебные файлы и начать задание заново.\n")
                    self.output_text.see(tk.END)
                    return
                self.completed_steps.append(command)
                self.step_counter += 1

                self.update_steps_info()

                if self.step_counter >= len(steps):
                    self.lesson_completed = True

                    max_points = lesson['points']
                    penalty_ratio = min(self.failed_attempts * 0.1, 0.5)
                    points = round(max_points * (1 - penalty_ratio))
                    self.earned_points += points
                    self.stats['successes'] += 1
                    self.update_stats()

                    self.output_text.insert(tk.END, "\n" + "=" * 60 + "\n")
                    if points < max_points:
                        self.output_text.insert(tk.END, f"🎉 ОТЛИЧНО! Задание выполнено! +{points} баллов из {max_points}\n")
                        self.output_text.insert(tk.END, f"   (снято за {self.failed_attempts} неверн. попыток(-ку))\n")
                    else:
                        self.output_text.insert(tk.END, f"🎉 ОТЛИЧНО! Задание выполнено с первой попытки! +{points} баллов!\n")
                    self.output_text.insert(tk.END, f"📌 {self._task_display(lesson)}\n")
                    self.output_text.insert(tk.END, "=" * 60 + "\n")
                    self.output_text.see(tk.END)

                    self.next_btn.config(state=tk.NORMAL)
                    self.command_entry.config(state=tk.DISABLED)
                    self.reset_btn.config(state=tk.DISABLED)
            else:
                self.handle_failed_attempt(command)
        else:
            self.lesson_completed = True

    def handle_failed_attempt(self, command):
        """Обрабатывает неудачную попытку"""
        if self.current_lesson >= len(self.lessons):
            return

        if self.lesson_completed or self.lesson_failed:
            return

        lesson = self.lessons[self.current_lesson]

        self.failed_attempts += 1

        if self.failed_attempts >= 5:
            self.lesson_failed = True
            self.stats['failed'] += 1

            total_steps = len(lesson['steps'])
            completed = len(self.completed_steps)
            partial_points = round(lesson['points'] * 0.5 * (completed / total_steps)) if completed else 0
            self.earned_points += partial_points
            self.update_stats()

            self.output_text.insert(tk.END, "\n" + "=" * 60 + "\n")
            self.output_text.insert(tk.END, "❌ ЗАДАНИЕ ПРОВАЛЕНО!\n")
            self.output_text.insert(tk.END, f"📌 {self._task_display(lesson)}\n")
            if partial_points > 0:
                self.output_text.insert(tk.END, f"💡 Частично засчитано: +{partial_points} баллов за {completed}/{total_steps} верных шагов\n")
            if self.hints_used < self.HINT_BUDGET:
                self.output_text.insert(tk.END, "💡 Используй кнопку 'Подсказка' для помощи\n")
            self.output_text.insert(tk.END, "=" * 60 + "\n")
            self.output_text.see(tk.END)

            self.next_btn.config(state=tk.NORMAL)
            self.command_entry.config(state=tk.DISABLED)
            self.reset_btn.config(state=tk.DISABLED)

            self.update_attempts_info()
        else:
            remaining = 5 - self.failed_attempts
            self.output_text.insert(tk.END, f"\n⚠️ Попытка {self.failed_attempts}/5. Осталось попыток: {remaining}\n")

            if self.failed_attempts == 3 and self.hints_used < self.HINT_BUDGET:
                self.output_text.insert(tk.END, "💡 Теперь можешь воспользоваться подсказкой!\n")

            self.output_text.see(tk.END)

            self.update_attempts_info()

            if remaining <= 2:
                self.output_text.insert(tk.END, f"⚠️ ВНИМАНИЕ! Осталось всего {remaining} попыток!\n")
                self.output_text.see(tk.END)

    def next_lesson(self):
        """Переход к следующему уроку"""
        self.current_lesson += 1
        if self.current_lesson < len(self.lessons):
            self.load_lesson()
        else:
            self.show_completion()

    def show_completion(self):
        """Показывает завершение обучения"""
        self.clear_output()

        completion_percent = (self.earned_points / self.total_points) * 100 if self.total_points > 0 else 0

        # Шкала 2-3-4-5 по абсолютным баллам (пересчитана под сумму баллов
        # этого тренажера — 935 — пропорционально шкале Linux-тренажера):
        # до 415 - 2, 415-610 - 3, 610-795 - 4, более 795 - 5
        if self.earned_points > 795:
            points_grade_num = 5
        elif self.earned_points >= 610:
            points_grade_num = 4
        elif self.earned_points >= 415:
            points_grade_num = 3
        else:
            points_grade_num = 2

        # Отдельный потолок оценки по количеству использованных подсказок
        # (кнопка "Подсказка", лимит self.HINT_BUDGET на весь тест):
        # 0-2 подсказки не влияют, 3-5 - потолок 4, 6-8 - потолок 3, 9-10 - потолок 2
        if self.hints_used >= 9:
            hint_cap_num = 2
        elif self.hints_used >= 6:
            hint_cap_num = 3
        elif self.hints_used >= 3:
            hint_cap_num = 4
        else:
            hint_cap_num = 5

        grade_num = min(points_grade_num, hint_cap_num)
        grade_labels = {
            5: ("5 (отлично)", "🏆"),
            4: ("4 (хорошо)", "🌟"),
            3: ("3 (удовлетворительно)", "📚"),
            2: ("2 (неудовлетворительно)", "🔄"),
        }
        grade, emoji = grade_labels[grade_num]

        hint_note = ""
        if hint_cap_num < points_grade_num:
            hint_note = (
                f"   ⚠️ Оценка ограничена использованными подсказками "
                f"({self.hints_used}/{self.HINT_BUDGET}): по баллам была бы "
                f"{grade_labels[points_grade_num][0]}\n"
            )

        self.output_text.insert(tk.END, f"""
╔═══════════════════════════════════════════════════════════════╗
║                                                              ║
║           {emoji} ПОЗДРАВЛЯЮ! ТЫ ПРОШЕЛ ВСЕ УРОКИ!              ║
║                                                              ║
╚═══════════════════════════════════════════════════════════════╝

📊 **ИТОГОВАЯ СТАТИСТИКА:**
   ✅ Успешно выполнено: {self.stats['successes']} заданий
   ❌ Провалено заданий: {self.stats['failed']}
   📝 Всего введено команд: {self.stats['attempts']}
   💡 Использовано подсказок: {self.hints_used} из {self.HINT_BUDGET}
   📚 Пройдено уроков: {len(self.lessons)}

🏆 **РЕЗУЛЬТАТЫ:**
   ⭐ Заработано баллов: {self.earned_points} из {self.total_points}
   📈 Процент выполнения: {completion_percent:.1f}%
   🎓 Оценка: {grade}
{hint_note}
📌 **СТАТИСТИКА ПО УРОКАМ:**
""")

        for i, lesson in enumerate(self.lessons, 1):
            status = "✅ Выполнено" if i <= self.stats['successes'] else "❌ Провалено" if i <= self.stats['successes'] + self.stats['failed'] else "⏳ Не пройдено"
            self.output_text.insert(tk.END, f"   {i:2d}. {lesson['title'][:30]:<30} {status}\n")

        self.output_text.insert(tk.END, f"""
💪 **ЧТО ДАЛЬШЕ?**
   • Продолжай практиковаться в реальном терминале Windows
   • Изучай более сложные сценарии (.bat/.cmd файлы)
   • Попробуй освоить PowerShell
   • Пройди тренажер заново для лучшего результата

{emoji} **ИТОГОВАЯ ОЦЕНКА: {grade}**

Для выхода нажмите X в углу окна.
""")

        self.command_entry.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.DISABLED)

    def show_help(self):
        """Показывает справку"""
        help_text = f"""
╔═══════════════════════════════════════════════════════════════╗
║                    СПРАВКА ПО КОМАНДАМ                        ║
╚═══════════════════════════════════════════════════════════════╝

📌 **НАВИГАЦИЯ И ФАЙЛЫ:**
   whoami   - показать имя пользователя
   cd       - текущая папка / смена папки
   dir      - список файлов (с ключами /a, /o:d, /s, /b)
   md       - создать папку
   rd       - удалить папку (с ключом /s)
   copy     - копировать файл (copy nul - создать пустой файл)
   echo     - вывести текст / записать в файл
   type     - просмотр файла
   del      - удалить файл
   move     - переместить файл
   ren      - переименовать файл

📌 **ПОИСК И ТЕКСТ:**
   findstr  - поиск текста в файле (/i, /n, /v)
   find     - простой поиск и подсчёт строк (/c)
   sort     - сортировка строк (/r)
   more     - постраничный просмотр
   fc       - построчное сравнение файлов
   comp     - побайтовое сравнение файлов
   where    - расположение команды
   tree     - дерево папок

📌 **ПРАВА И АТРИБУТЫ:**
   attrib   - скрытые/защищённые файлы (+h, +r)
   icacls   - права доступа
   takeown  - смена владельца файла

📌 **СИСТЕМА И СЕТЬ:**
   hostname, ver, systeminfo, date, time, vol
   set, path
   tasklist, taskkill
   shutdown
   ipconfig, ping, netstat, nslookup, tracert

📌 **ПОЛЬЗОВАТЕЛИ:**
   whoami /groups, whoami /priv
   net user, net localgroup
   query user

📌 **СПЕЦИАЛЬНЫЕ КОМАНДЫ ТРЕНАЖЕРА:**
   cls      - очистить терминал
   help     - показать справку
   doskey /history - история команд
   title, color - оформление окна

💡 **СИСТЕМА ОЦЕНИВАНИЯ:**
   • Каждое задание оценивается в баллах (15-25)
   • Максимальный балл: {self.total_points}
   • Подсказка доступна после 5 неудачных попыток
   • После 5 неудачных попыток задание считается проваленным

📋 **МНОГОШАГОВЫЕ ЗАДАНИЯ:**
   • Некоторые задания требуют выполнения нескольких шагов
   • Каждый шаг нужно выполнять по порядку
   • Все шаги должны быть выполнены для получения баллов
"""
        self.output_text.insert(tk.END, help_text)
        self.output_text.see(tk.END)

    def reset_workspace(self):
        """Начинает текущее задание заново на свежих учебных файлах.

        Неверные попытки при этом НЕ обнуляются: иначе "Сброс" позволял бы
        бесконечно уходить от провала на 5-й ошибке и от штрафа за ошибки."""
        if self.lesson_completed or self.lesson_failed:
            return
        self._new_workspace()
        self.step_counter = 0
        self.completed_steps = []
        self.update_steps_info()
        self.update_prompt()
        self.clear_output()
        self.output_text.insert(tk.END, "🔄 Учебные файлы восстановлены, задание начато заново "
                                        "(счётчик неверных попыток сохраняется)\n")

    def on_closing(self):
        """Обработка закрытия окна"""
        try:
            shutil.rmtree(self.workspace)
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = WindowsTrainerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
