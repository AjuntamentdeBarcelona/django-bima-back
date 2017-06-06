from bima_back.models import PhotoFilter
from django import forms


class AddFilterForm(forms.ModelForm):
    class Meta:
        model = PhotoFilter
        fields = ['username', 'name', 'filter']
