CREATE OR REPLACE FUNCTION public.btk_sys_xml_to_json_flat(
    inxml text,
    intagname character varying,
    infields jsonb DEFAULT NULL::jsonb)
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


    soup = BeautifulSoup(inxml, 'xml')
    item_list = soup.find_all(intagname)

    def get_fields():
        """ Получение всех полей по первой записи, если они не переданы 
            Примеч.: Если считывать поля со всех записей, то их кол-во может не совпадать
        """
        res = []
        if len(item_list)>0:
            for tagobj in item_list[0].findChildren(recursive=False):
                if tagobj.findChildren(recursive=False):
                    if tagobj.find('Ссылка', reversed=False):
                        res.append(tagobj.name)
                else:
                    res.append(tagobj.name)
        #plpy.info(res)
        return res


    def get_records(xml_item_list, fields):
        """ Получение записей """
        res = []
        for item in xml_item_list:
            rec = {}
            # Если переданы поля
            for fieldname in fields:
                rec[fieldname] = None
                fieldobj = item.find(fieldname, recursive=False)
                if fieldobj:
                    if fieldobj.findChildren(recursive=False):
                        if fieldobj.find('Ссылка', recursive=False):
                            rec[fieldname+'_Ссылка'] = fieldobj.find('Ссылка', recursive=False).text

                        if fieldobj.find('Код', recursive=False):
                            rec[fieldname+'_Код'] = fieldobj.find('Код', recursive=False).text
                    else:
                        rec[fieldname] = fieldobj.text
            res.append(rec)
        return res


    # Если тег не нашелся, возвращаем NULL
    if not item_list:
        return None

    if infields and json.loads(infields):
        fields = json.loads(infields)
    else:
        fields = get_fields()

    res = get_records(xml_item_list=item_list, fields=fields)
    res = json.dumps(res)
    return res
$BODY$
  LANGUAGE plpython3u VOLATILE
  COST 100;