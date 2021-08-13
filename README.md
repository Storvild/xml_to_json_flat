# xml_to_json_flat
Преобразование xml в плоский вид json

В проекте используется BeautifulSoup4  
Установка:   
```sh
pip install bs4
```

### Выполнение
Результат конвертации из xml_examples/example01.xml:
```json
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
SELECT value->>'item1' AS item1    
     , value->>'item2' AS item2 
FROM jsonb_array_elements(xml_to_json_flat('
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
| item1 | item2 |
| ------ | ------ |
| 1 | 2 |
| 11 | 22 |