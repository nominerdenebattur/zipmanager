from django import forms
from .models import ZipFile


class ZipFileForm(forms.ModelForm):
    class Meta:
        model = ZipFile
        fields = ['file', 'version']
