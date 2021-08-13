# xml_to_json_flat
Преобразование xml в плоский вид json

В проекте используется BeautifulSoup4  
Установка:   
```
pip install bs4
```

Использование в PostgreSQL:  

```
SELECT value->>'item1' AS item1    
     , value->>'item2' AS item2 
FROM jsonb_array_elements(xml_to_json_flat('<?xml version="1.0" encoding="utf-8"?>
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