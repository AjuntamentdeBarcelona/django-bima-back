# -*- coding: utf-8 -*-
import serpy


class AutocompleteSerializer(serpy.DictSerializer):
    id = serpy.MethodField()
    text = serpy.MethodField()

    def __init__(self, instance=None, many=False, data=None, context=None, text_field=None, id_field=None, **kwargs):
        """
        Set the instance fields used as id and text
        """
        self.text_field = text_field or 'text'
        self.id_field = id_field or 'id'
        super().__init__(instance, many, data, context, **kwargs)

    def get_text(self, instance):
        return instance.get(self.text_field, '')

    def get_id(self, instance):
        return instance.get(self.id_field, '')
