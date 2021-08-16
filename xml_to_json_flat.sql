CREATE OR REPLACE FUNCTION public.xml_to_json_flat(
    inxml text,
    intagname character varying,
    infields jsonb DEFAULT '[]'::jsonb,
    inmaxlevel integer DEFAULT 0,
    inuseattrs boolean DEFAULT true)
  RETURNS jsonb AS

$BODY$
    """ Получение из xml списка элементов по тегу tagname в виде json 
        inxml - Текст XML
        intagname - Тег, который необходимо найти в XML
        infields - Поля в виде json. Если передан NULL, то возвращаются все найденные поля
        Возвращаемое значение - Список словарей json
    Использование:
    SELECT value->>'tag2_item1' AS item1, value->>'tag2_item2' AS item2 FROM jsonb_array_elements(
        xml_to_json_flat(inxml, 'tag2', '["tag2_item1","tag2_item2"]'::jsonb, 0)
    ) 
    SELECT value->>'tag2_item1' AS item1, value->>'tag2_item2' AS item2 FROM jsonb_array_elements(
        xml_to_json_flat(inxml, 'tag2')
    ) 

    """
    import json
    from bs4 import BeautifulSoup
    
    def _xmlobj_to_jsonobj_flat(inxmlobj, inpreffix='', infields=[], inmaxlevel=0, inuseattrs=True):
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
            if inuseattrs and inxmlobj.attrs:
                for attr in inxmlobj.attrs:
                    data[inpreffix + '_attr_' + attr] = inxmlobj.attrs[attr]
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
                inparenttags = inparenttags.split('/') # Приводим inparenttags к списку, если передана строка
            else:
                inparenttags = []
        parenttag = inxmlobj.parent
        for parenttagname in inparenttags[::-1]:
            if parenttag and parenttag.name == parenttagname:
                parenttag = parenttag.parent
            else:
                return False
        return True


    def _get_records(xml_item_list, inparenttags=[], infields=[], inmaxlevel=0, inuseattrs=True):
        """
        Получение записей c проверкой на соответствие переданным родительским тегам
        :param xml_item_list: Список XML-объектов, которые необходимо преобразовать в JSON
        :param inparenttags: Список родительских тегов которые должен иметь рассматриваемый тег
        :param infields: Список имен полей, которые должны попасть в результат
        :param inmaxlevel: Максимальный уровень погружения. 0 - без ограничений
        :param inuseattrs: Добавлять данные из атрибутов
        :return: Список плоских словарей с данными
        :type xml_item_list: list
        :type inparenttags: list
        :type infields: list
        :type inmaxlevel: int
        :type inuseattrs: bool
        :rtype: list
        """
        res = []
        for item in xml_item_list:
            # Проверяем соответствуют ли родительские теги переданным
            if _check_parent(item, inparenttags):
                preffix = ''
                if inparenttags:
                    preffix = '_'.join(inparenttags) + '_'
                rec = _xmlobj_to_jsonobj_flat(item, preffix, infields=infields, inmaxlevel=inmaxlevel, inuseattrs=inuseattrs)
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


    def xml_to_json_flat(inxml, intagname, infields=[], inmaxlevel=0, inuseattrs=True):
        """
        Основная функция принимает XML в виде текста. Ищет теги с именем intagname и выводит список
            найденного в виде плоского словаря
        :param inxm: XML текст
        :param intagname: Наименование тега, список которых необходимо найти в xml. Если значение пустое, использовать
            тег верхнего уровня
        :param infields: Список полей, которые должны быть выведены в результате. Пустой список - все поля
        :param inmaxlevel: Максимальный уровень погружения. 0 - без ограничений
        :param inuseattrs: Выводить аттрибуты или нет
        :type inxm: str
        :type intagname: str
        :type infields: list
        :type inmaxlevel: int
        :type inuseattrs: bool
        :return: Список json строк
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

        json_list = _get_records(tags, inparenttags=parenttags, infields=infields, inmaxlevel=inmaxlevel, inuseattrs=inuseattrs)
        json_list = _json_fields_sync(json_list)
        return json_list


    fields = json.loads(infields)
    res = xml_to_json_flat(inxml, intagname, infields=fields, inmaxlevel=inmaxlevel, inuseattrs=inuseattrs)

    # Если тег не нашелся, возвращаем NULL
    if not res:
        return None

    res = json.dumps(res, ensure_ascii=False, sort_keys=True)
    #plpy.info(res)

    return res
$BODY$
  LANGUAGE plpython3u VOLATILE
  COST 100;