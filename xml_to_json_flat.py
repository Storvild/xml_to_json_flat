from json import encoder
import os
from pprint import pprint

import json
from typing import Optional
#import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from bs4.element import ResultSet


def xmlobj_to_json_flat(inxmlobj, inpreffix='', inmaxlevel=0):
    """
    Получение одной плоской записи из тега
    Пример XML: <parent1><parent2><item1>123</item1></parent2><parent21>456</parent21></parent1>
    Результат при передаче тега parent1: {"parent1_parent2_item1": "123", "parent1_parent21": "456"}
    :param inxmlobj: XML-тег
    :type inxmlobj: bs4.element.Tag
    :param inpreffix: Строка префикса для json поля
    :type inpreffix: str
    :param inmaxlevel: Максимальное кол-во погружения в xml
    :type inmaxlevel: int
    :return: Плоский словарь с полями из имен тегов через _
    :rtype: dict
    """

    # Получаем json из одного тега в плоском виде
    data = {}
    def get_json_rec(inxmlobj, inpreffix, level):
        if inxmlobj.findChildren(recursive=False):
            if inmaxlevel == 0 or inmaxlevel >= level:
                for item in inxmlobj.findChildren(recursive=False):
                    get_json_rec(item, inpreffix+'_'+item.name, level+1)
        else:
            if inpreffix not in data:  # Добавлять только если данных нет
                data[inpreffix] = inxmlobj.text
    get_json_rec(inxmlobj, inpreffix + inxmlobj.name, 1)
    return data

def check_parent(inxmlobj, inparenttags):
    """
    Проверка что тег inxmlobj вложен в родительские теги inparenttags
    Пример XML: <parent1><parent2><item1>123</item1></parent2><parent21>456</parent21></parent1>
    Результат при передаче тега item1, inparenttags='parent1/parent2': True
    :param inxmlobj: XML-тег
    :type inxmlobj: bs4.element.Tag
    :param inparenttags: Родительские теги в виде списка или текста разделенного слэшами /
    :type inparenttags: str|list
    :return: Тег inxmlobj вложен в родительские теги inparenttags
    :rtype: bool
    """

    if type(inparenttags) == str:
        inparenttags = inparenttags.split('/') # Приводим inparenttags к списку, если передана строка
    parenttag = inxmlobj.parent
    for parenttagname in inparenttags[::-1]:
        if parenttag and parenttag.name == parenttagname:
            parenttag = parenttag.parent
        else:
            return False
    return True

def test_check_parent():
    """ Тест ф-ции check_parent """
    inxml = '<parent1><parent2><mytag1>1</mytag1></parent2></parent1>'
    soup = BeautifulSoup(inxml, 'xml')
    tag = soup.find_all('mytag1')
    #res = check_parent(tag[0], ['[document]', 'parent1','parent2'])
    res = check_parent(tag[0], '[document]/parent1/parent2')
    print(res)


def get_records(xml_item_list, inparenttags=[], inmaxlevel=0):
    """ Получение записей """
    res = []
    if type(inparenttags) == str:
        inparenttags = inparenttags.split('/')
    for item in xml_item_list:
        # Проверяем соответствуют ли родительские теги переданным
        if check_parent(item, inparenttags):
            preffix = ''
            if inparenttags:
                preffix = '_'.join(inparenttags) + '_'
            rec = xmlobj_to_json_flat(item, preffix, inmaxlevel)
            res.append(rec)
    return res

def json_fields_sync(inlist):
    """ Синхронизация колонок (приведение к одинаковому количеству во всех строках) """
    res = []
    fields = set()
    for rec in inlist:
        fields.update(rec.keys())
    for rec in inlist:
        new_rec = {}
        for fieldname in fields:
            if fieldname in rec:
                new_rec[fieldname] = rec[fieldname]
            else:
                new_rec[fieldname] = None
        res.append(new_rec)
    return res

def xml_to_json_flat(inxml, intagname, inmaxlevel=0):
    soup = BeautifulSoup(inxml, 'xml')
    # Разделяем parent-тег
    tagnamesplit = intagname.split('/')
    tagname = tagnamesplit[-1]
    parenttags = tagnamesplit[:-1]
    tags: ResultSet = soup.find_all(tagname)  # Список тегов

    json_list = get_records(tags, inparenttags=parenttags, inmaxlevel=inmaxlevel)
    json_list = json_fields_sync(json_list)
    return json_list


def main():
    os.chdir(os.path.dirname(__file__))
    #intagname = 'tag2'  # Ищем все теги tag2 независимо в какие родительские теги он входит
    intagname: str = 'tag1/tag2'  # Ищем теги с именем tag2, который вложен в тег tag1
    infields: Optional[str] = None
    inxml: Optional[str] = None

    with open(r'xml_examples/example01.xml', 'r', encoding='utf-8') as f:
        inxml = f.read()

    json_list = xml_to_json_flat(inxml, intagname)

    pprint(json_list)
    
    with open(r'xml_examples/example01.json', 'w') as fw:
        json.dump(json_list, fw, ensure_ascii=False, indent=4, sort_keys=True)


if __name__ == '__main__':
    #test_check_parent()
    main()