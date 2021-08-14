# xml_to_json_flat
Преобразование xml в плоский вид json

В проекте используется BeautifulSoup4  
Установка:   
```sh
pip install beautifulsoup4
```

### Описание xml_to_json_flat.py
Ф-ция xml_to_json_flat принимает 3 параметра:   
* inxml: str - XML в текстовом виде   
* intagname: str - Наименование тега или путь к тегу tag1/tag2.   
* inmaxlevel: int - Кол-во уровней обрабатываемых рекурсией. 0 - без ограничений.
* infields: list - Список полей, которые попадут в результирующий json

### Использование
```python
import json
from xml_to_json_flat import xml_to_json_flat
xml = """<?xml version="1.0" encoding="utf-8"?>
<tag1>
    <tag2>
        <item1>1</item1>
        <item2>2</item2>
        <itemlist> 
            <item3>3</item3>
            <item4>4</item4>
        </itemlist>
    </tag2>
    <tag2>
        <item1>11</item1>
        <item2>22</item2>
        <itemlist> 
            <item3>33</item3>
            <item4>44</item4>
        </itemlist>
    </tag2>
</tag1>"""
res = xml_to_json_flat(xml, 'tag1/tag2')
json = json.dumps(res, ensure_ascii=False, indent=4, sort_keys=True)
print(json)
 
```
Результат:
```
[{'tag2_item1': '1',
  'tag2_item2': '2',
  'tag2_itemlist_item3': '3',
  'tag2_itemlist_item4': '4'},
 {'tag2_item1': '11',
  'tag2_item2': '22',
  'tag2_itemlist_item3': '33',
  'tag2_itemlist_item4': '44'}]
```


### Ф-ция для PostgreSQL

Если в PostgreSQL установлено расширение plpython3u, можно создать функцию xml_to_json_flat (из скрипта xml_to_json_flat.sql)

Использование в PostgreSQL:  

```sql
SELECT value->>'tag2_item1' AS item1
     , value->>'tag2_item2' AS item2
     , value->>'tag2_itemlist_item4' AS itemlist4
FROM jsonb_array_elements(btk_sys_xml_to_json_flat_by_tagname('
<?xml version="1.0" encoding="utf-8"?>
    <tag1>
        <tag2>
            <item1>1</item1>
            <item2>2</item2>
            <itemlist> 
                <item3>3</item3>
                <item4>4</item4>
            </itemlist>
        </tag2>
        <tag2>
            <item1>11</item1>
            <item2>22</item2>
            <itemlist> 
                <item3>33</item3>
                <item4>44</item4>
            </itemlist>
        </tag2>
    </tag1>', 'tag2')
)
```
Результат:
| item1 | item2 | itemlist4 |
| ------ | ------ | ------ |
| 1 | 2 | 4 |
| 11 | 22 | 44 |