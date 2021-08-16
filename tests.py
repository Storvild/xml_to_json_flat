import unittest
import json
from bs4 import BeautifulSoup

class TestXmlToJsonFlat(unittest.TestCase):
    def setUp(self):
        self.xml = """<?xml version="1.0" encoding="utf-8"?>
        <tag1>
            <tag2>
                <item1>1</item1>
                <item2>2</item2>
                <item3 Свойство1="Значение1" prop2="Property2" />
                <itemlist> 
                    <item3>3</item3>
                    <Элемент4>4</Элемент4>
                </itemlist>
            </tag2>
            <tag2>
                <item1>11</item1>
                <item2>22</item2>
                <itemlist> 
                    <item3>33</item3>
                    <Элемент4>44</Элемент4>
                </itemlist>
                <tag2>
                    <item>tag2 in tag2</item>
                </tag2>
            </tag2>
        </tag1>"""

    def test_xml_to_json_flat(self):
        from xml_to_json_flat import xml_to_json_flat

        print('SOURCE XML:')
        print(self.xml)

        # Простой xml:
        res1 = xml_to_json_flat('<tag>1</tag>', 'tag')
        self.assertEqual(res1[0]['tag'], '1')

        # Поиск tag2
        res2 = xml_to_json_flat(self.xml, 'tag2')
        self.assertEqual(res2[0]['tag2_item1'], '1')
        self.assertIn('tag2_itemlist_item3', res2[0])
        self.assertEqual(res2[0]['tag2_itemlist_item3'], '3')
        self.assertEqual(res2[1]['tag2_itemlist_Элемент4'], '44')
        self.assertEqual(res2[0]['tag2_item3_attr_Свойство1'], 'Значение1')

        # Поиск tag2 входящего в tag1
        res3 = xml_to_json_flat(self.xml, 'tag1/tag2')
        self.assertEqual(res3[0]['tag1_tag2_item2'], '2')
        self.assertEqual(res3[1]['tag1_tag2_itemlist_item3'], '33')
        self.assertEqual(res3[1]['tag1_tag2_itemlist_Элемент4'], '44')

        print('RESULT JSON:')
        print(json.dumps(res3, ensure_ascii=False, indent=4, sort_keys=True))

        # Поиск tag2. Получаем только 1й уровень
        res4 = xml_to_json_flat(self.xml, 'tag2', inmaxlevel=1)
        self.assertNotIn('tag2_itemlist_item3', res4[0])

        # Получаем весь XML
        res5 = xml_to_json_flat(self.xml, '')
        self.assertEqual(len(res5), 1)
        self.assertEqual(res5[0]['tag1_tag2_item1'], '1')


    def test_check_parent(self):
        from xml_to_json_flat import _check_parent
        xml = '''
        <parent1>
            <parent2>
                <mytag1>1</mytag1>
            </parent2>
        </parent1>'''
        soup = BeautifulSoup(xml, 'xml')
        tag = soup.find_all('mytag1')
        res = _check_parent(tag[0], '[document]/parent1/parent2')   # mytag1 входит в parent2, который входит в parent1, который находится в начале документа [document]
        self.assertTrue(res)
        res = _check_parent(tag[0], ['[document]', 'parent1', 'parent2'])  # Задание родительских элементов в виде списка
        self.assertTrue(res)

        tag = soup.find_all('parent1')
        res = _check_parent(tag[0], '[document]')  # parent1 является основным тегом данного XML
        self.assertTrue(res)

        tag = soup.find_all('parent2')
        res = _check_parent(tag[0], 'parent1')  # parent1 является родительским тегом parent2
        self.assertTrue(res)
        res = _check_parent(tag[0], 'othertag')  # othertag не является родительским тегом parent2
        self.assertFalse(res)


    def test_sql_function(self):
        # CREATE OR REPLACE FUNCTION public.xml_to_json_flat(
        #     inxml text,
        #     intagname character varying,
        #     inmaxlevel integer DEFAULT 0,
        #     infields jsonb DEFAULT '[]'::jsonb)
        #     inuseattrs - Добавлять данные из атрибутов тега
        #     inskipfirsttag - Исключить из ключа словаря имя искомого тега
        #   RETURNS jsonb AS
        # $BODY$
        def sql_function(inxml, intagname, inmaxlevel=0, infields='[]', inuseattrs=True, inskipfirsttag=False):  # for test
            # --- BEGIN BODY FUNCTION --- #
            import json
            from bs4 import BeautifulSoup

            def _xmlobj_to_jsonobj_flat(inxmlobj, inpreffix='', infields=[], inmaxlevel=0, inuseattrs=True,
                                        inskipfirsttag=False):
                """
                Получение одной плоской записи из тега
                Пример XML: <parent1><parent2><item1>123</item1></parent2><parent21>456</parent21></parent1>
                Результат при передаче тега parent1: {"parent1_parent2_item1": "123", "parent1_parent21": "456"}
                :param inxmlobj: XML-тег
                :type inxmlobj: bs4.element.Tag
                :param inpreffix: Строка префикса для json поля
                :type inpreffix: str
                :param infields: Список наименований полей которые должны быть в результате. Пустой список - все поля
                :type infields: list
                :param inmaxlevel: Максимальное кол-во погружения в xml
                :type inmaxlevel: int
                :param inuseattrs: Выводить аттрибуты или нет
                :type inuseattrs: bool
                :param inskipfirsttag: Убрать из начала ключа словаря имя искомого тега
                :type inskipfirsttag: bool
                :return: Плоский словарь с полями из имен тегов через _
                :rtype: dict
                """
                # Получаем json из одного тега в плоском виде
                data = {}

                def get_json_rec(inxmlobj, inpreffix, level):
                    if inxmlobj.findChildren(recursive=False):
                        if inmaxlevel == 0 or inmaxlevel >= level:
                            for item in inxmlobj.findChildren(recursive=False):
                                get_json_rec(item, inpreffix + '_' + item.name, level + 1)
                    else:
                        if inpreffix not in data:  # Добавлять только если данных нет
                            if not infields or inpreffix in infields:  # Добавлять только если поле есть в infields
                                key = inpreffix.lstrip(' _')
                                data[key] = inxmlobj.text
                    if inuseattrs and inxmlobj.attrs:
                        for attr in inxmlobj.attrs:
                            key = '{}_attr_{}'.format(inpreffix, attr).lstrip(' _')
                            data[key] = inxmlobj.attrs[attr]

                if inskipfirsttag:
                    get_json_rec(inxmlobj, '', 1)
                else:
                    get_json_rec(inxmlobj, inpreffix + inxmlobj.name, 1)
                return data

            def _check_parent(inxmlobj, inparenttags):
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
                    if inparenttags:
                        inparenttags = inparenttags.split('/')  # Приводим inparenttags к списку, если передана строка
                    else:
                        inparenttags = []
                parenttag = inxmlobj.parent
                for parenttagname in inparenttags[::-1]:
                    if parenttag and parenttag.name == parenttagname:
                        parenttag = parenttag.parent
                    else:
                        return False
                return True

            def _get_records(xml_item_list, inparenttags=[], infields=[], inmaxlevel=0, inuseattrs=True,
                             inskipfirsttag=False):
                """
                Получение записей c проверкой на соответствие переданным родительским тегам
                :param xml_item_list: Список XML-объектов, которые необходимо преобразовать в JSON
                :param inparenttags: Список родительских тегов которые должен иметь рассматриваемый тег
                :param infields: Список имен полей, которые должны попасть в результат
                :param inmaxlevel: Максимальный уровень погружения. 0 - без ограничений
                :param inuseattrs: Добавлять данные из атрибутов
                :param inskipfirsttag: Убрать из начала ключа словаря имя искомого тега
                :return: Список плоских словарей с данными
                :type xml_item_list: list
                :type inparenttags: list
                :type infields: list
                :type inmaxlevel: int
                :type inuseattrs: bool
                :type inskipfirsttag: bool
                :rtype: list
                """
                res = []
                for item in xml_item_list:
                    # Проверяем соответствуют ли родительские теги переданным
                    if _check_parent(item, inparenttags):
                        preffix = ''
                        if inparenttags:
                            preffix = '_'.join(inparenttags) + '_'
                        rec = _xmlobj_to_jsonobj_flat(item, preffix, infields=infields, inmaxlevel=inmaxlevel,
                                                      inuseattrs=inuseattrs, inskipfirsttag=inskipfirsttag)
                        res.append(rec)
                return res

            def _json_fields_sync(inlist):
                """
                Синхронизация колонок (приведение к одинаковому количеству во всех строках)
                :param inlist: Список словарей
                :return: Список словарей с одинаковым кол-вом ключей
                :type inlist: list
                :rtype: list
                """

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

            def xml_to_json_flat(inxml, intagname, infields=[], inmaxlevel=0, inuseattrs=True, inskipfirsttag=False):
                """
                Основная функция принимает XML в виде текста. Ищет теги с именем intagname и выводит список
                    найденного в виде плоского словаря
                Внимание: Если внутри тега есть несколько рядом стоящих одинаковых тегов, то будет использован только первый
                :param inxm: XML текст
                :param intagname: Наименование тега, список которых необходимо найти в xml. Если значение пустое, использовать
                    тег верхнего уровня
                :param infields: Список полей, которые должны быть выведены в результате. Пустой список - все поля
                :param inmaxlevel: Максимальный уровень погружения. 0 - без ограничений
                :param inuseattrs: Выводить аттрибуты или нет
                :param inskipfirsttag: Убрать из начала ключа словаря имя искомого тега
                :return: Список json строк
                :type intagname: str
                :type infields: list
                :type inmaxlevel: int
                :type inuseattrs: bool
                :type inxm: str
                :type inskipfirsttag: bool
                :rtype: list
                """
                soup = BeautifulSoup(inxml, 'xml')
                if intagname:
                    # Разделяем parent-тег
                    tagnamesplit = intagname.split('/')
                    tagname = tagnamesplit[-1]
                    parenttags = tagnamesplit[:-1]
                    tags = soup.find_all(tagname)  # Список тегов
                else:
                    tags = soup.contents
                    parenttags = []

                json_list = _get_records(tags, inparenttags=parenttags, infields=infields, inmaxlevel=inmaxlevel,
                                         inuseattrs=inuseattrs, inskipfirsttag=inskipfirsttag)
                json_list = _json_fields_sync(json_list)
                return json_list


            fields = json.loads(infields)
            res = xml_to_json_flat(inxml, intagname, infields=fields, inmaxlevel=inmaxlevel, inuseattrs=inuseattrs,
                                   inskipfirsttag=inskipfirsttag)

            # Если тег не нашелся, возвращаем NULL
            if not res:
                return None

            res = json.dumps(res, ensure_ascii=False, sort_keys=True)
            #plpy.info(res)

            return res
            # --- END BODY FUNCTION --- #
        # $BODY$
        # LANGUAGE plpython3u VOLATILE
        # COST 100;
        
        # Проверка нахождения tag2
        res_json = sql_function(self.xml, 'tag2')
        self.assertIsNotNone(res_json)
        if res_json:
            obj = json.loads(res_json)
            self.assertEqual(obj[0]['tag2_itemlist_Элемент4'], '4')
            self.assertEqual(obj[1]['tag2_item1'], '11')
            print('RESULT SQL FUNCTION:')
            print(res_json)

        # Проверка нахождения tag1/tag2. Тег tag2 должен находиться в теге tag1
        res_json = sql_function(self.xml, 'tag1/tag2')
        self.assertIsNotNone(res_json)
        if res_json:
            obj = json.loads(res_json)
            self.assertEqual(obj[0]['tag1_tag2_itemlist_Элемент4'], '4')
            self.assertEqual(obj[1]['tag1_tag2_item1'], '11')
            #print('RESULT SQL FUNCTION #2:')
            #print(res_json)
        
        # Проверка параметра infiels. Получаем только колонки "tag2_itemlist_Элемент4" и "tag2_item2"
        res_json = sql_function(self.xml, 'tag2', infields='["tag2_itemlist_Элемент4","tag2_item2"]', inmaxlevel=0, inuseattrs=True)
        self.assertIsNotNone(res_json)
        if res_json:
            obj = json.loads(res_json)
            self.assertEqual(obj[0]['tag2_itemlist_Элемент4'], '4')
            self.assertNotIn('tag2_item1', obj[0])

        # Проверка параметра inmaxlevel. Получаем только 1 уровень
        res_json = sql_function(self.xml, 'tag2', inmaxlevel=1)
        self.assertIsNotNone(res_json)
        if res_json:
            obj = json.loads(res_json)
            self.assertEqual(obj[0]['tag2_item1'], '1')
            self.assertNotIn('tag2_itemlist_Элемент4', obj[0])

        # Проверка параметра inmaxlevel. Получаем только 1 уровень
        res_json = sql_function(self.xml, 'tag2', inuseattrs=True, inskipfirsttag=True)
        self.assertIsNotNone(res_json)
        if res_json:
            obj = json.loads(res_json)
            #print('RESULT SQL FUNCTION #4:')
            #print(res_json)
            self.assertEqual(obj[0]['item1'], '1')
            self.assertEqual(obj[1]['item2'], '22')


if __name__ == '__main__':
    unittest.main()



