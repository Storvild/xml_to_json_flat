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
        # Простой xml:
        res1 = xml_to_json_flat('<tag>1</tag>', 'tag')
        self.assertEqual(res1[0]['tag'], '1')

        # Поиск tag2
        res2 = xml_to_json_flat(self.xml, 'tag2')
        self.assertEqual(res2[0]['tag2_item1'], '1')
        self.assertIn('tag2_itemlist_item3', res2[0])
        self.assertEqual(res2[0]['tag2_itemlist_item3'], '3')
        self.assertEqual(res2[1]['tag2_itemlist_Элемент4'], '44')

        # Поиск tag2 входящего в tag1
        res3 = xml_to_json_flat(self.xml, 'tag1/tag2')
        self.assertEqual(res3[0]['tag1_tag2_item2'], '2')
        self.assertEqual(res3[1]['tag1_tag2_itemlist_item3'], '33')
        self.assertEqual(res3[1]['tag1_tag2_itemlist_Элемент4'], '44')

        # Поиск tag2. Получаем только 1й уровень
        res4 = xml_to_json_flat(self.xml, 'tag2', inmaxlevel=1)
        self.assertNotIn('tag2_itemlist_item3', res4[0])


        print('SOURCE XML:')
        print(self.xml)
        print('RESULT JSON:')
        print(json.dumps(res3, ensure_ascii=False, indent=4, sort_keys=True))

    def test_check_parent(self):
        from xml_to_json_flat import check_parent
        xml = '''
        <parent1>
            <parent2>
                <mytag1>1</mytag1>
            </parent2>
        </parent1>'''
        soup = BeautifulSoup(xml, 'xml')
        tag = soup.find_all('mytag1')
        res = check_parent(tag[0], '[document]/parent1/parent2')   # mytag1 входит в parent2, который входит в parent1, который находится в начале документа [document]
        self.assertTrue(res)
        res = check_parent(tag[0], ['[document]', 'parent1', 'parent2'])  # Задание родительских элементов в виде списка
        self.assertTrue(res)

        tag = soup.find_all('parent1')
        res = check_parent(tag[0], '[document]')  # parent1 является основным тегом данного XML
        self.assertTrue(res)

        tag = soup.find_all('parent2')
        res = check_parent(tag[0], 'parent1')  # parent1 является родительским тегом parent2
        self.assertTrue(res)
        res = check_parent(tag[0], 'othertag')  # othertag не является родительским тегом parent2
        self.assertFalse(res)


    def test_sql_function(self):
        # CREATE OR REPLACE FUNCTION public.xml_to_json_flat(
        #     inxml text,
        #     intagname character varying,
        #     inmaxlevel integer DEFAULT 0,
        #     infields jsonb DEFAULT '[]'::jsonb)
        #   RETURNS jsonb AS
        # $BODY$
        def sql_function(inxml, intagname, inmaxlevel=0, infields='[]'):  # for test
            # --- BEGIN BODY FUNCTION --- #
            import json
            from bs4 import BeautifulSoup
            

            def xmlobj_to_json_flat(inxmlobj, inpreffix='', inmaxlevel=0, infields=[]):
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
                            if not infields or inpreffix in infields:  # Добавлять только если поле есть в infields
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

            def get_records(xml_item_list, inparenttags=[], inmaxlevel=0, infields=[]):
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
                        rec = xmlobj_to_json_flat(item, preffix, inmaxlevel, infields=infields)
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

            def xml_to_json_flat(inxml, intagname, inmaxlevel=0, infields=[]):
                soup = BeautifulSoup(inxml, 'xml')
                # Разделяем parent-тег
                tagnamesplit = intagname.split('/')
                tagname = tagnamesplit[-1]
                parenttags = tagnamesplit[:-1]
                tags = soup.find_all(tagname)  # Список тегов
                
                json_list = get_records(tags, inparenttags=parenttags, inmaxlevel=inmaxlevel, infields=infields)
                json_list = json_fields_sync(json_list)
                return json_list

            fields = json.loads(infields)
            res = xml_to_json_flat(inxml, intagname, inmaxlevel, fields)

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
            print('RESULT SQL FUNCTION #2:')
            print(res_json)
        
        # Проверка параметра infiels. Получаем только колонки "tag2_itemlist_Элемент4" и "tag2_item2"
        res_json = sql_function(self.xml, 'tag2', 0, '["tag2_itemlist_Элемент4","tag2_item2"]')
        self.assertIsNotNone(res_json)
        if res_json:
            obj = json.loads(res_json)
            self.assertEqual(obj[0]['tag2_itemlist_Элемент4'], '4')
            self.assertNotIn('tag2_item1', obj[0])

        # Проверка параметра inmaxlevel. Получаем только 1 уровень
        res_json = sql_function(self.xml, 'tag2', 1)
        self.assertIsNotNone(res_json)
        if res_json:
            obj = json.loads(res_json)
            self.assertEqual(obj[0]['tag2_item1'], '1')
            self.assertNotIn('tag2_itemlist_Элемент4', obj[0])


if __name__ == '__main__':
    unittest.main()



