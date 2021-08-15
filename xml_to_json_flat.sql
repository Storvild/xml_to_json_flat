CREATE OR REPLACE FUNCTION public.xml_to_json_flat(
    inxml text,
    intagname character varying,
    inmaxlevel integer DEFAULT 0)
  RETURNS jsonb AS
$BODY$
    """ Получение из xml списка элементов по тегу tagname в виде json 
        inxml - Текст XML
        intagname - Тег, который необходимо найти в XML
        infields - Поля в виде json. Если передан NULL, то возвращаются все найденные поля
        Возвращаемое значение - Список словарей json
    Использование:
    SELECT value->>'item1' AS item1, value->>'item2' AS item2 FROM jsonb_array_elements(
        btk_sys_xml_to_json_by_tagname(inxml, 'tag2', '["item1","item2"]'::jsonb) 
    ) 
    SELECT value->>'item1' AS item1, value->>'item2' AS item2 FROM jsonb_array_elements(
        btk_sys_xml_to_json_by_tagname(inxml, 'tag2') 
    ) 

    """
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
$BODY$
  LANGUAGE plpython3u VOLATILE
  COST 100;