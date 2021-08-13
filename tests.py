import unittest
import json
from bs4 import BeautifulSoup
from xml_to_json_flat import xml_to_json_flat
from xml_to_json_flat import check_parent

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
            </tag2>
        </tag1>"""

    def test_xml_to_json_flat(self):
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


if __name__ == '__main__':
    unittest.main()



