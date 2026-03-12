from django import forms


class InvoiceUploadForm(forms.Form):
    source_name = forms.CharField(max_length=255)
    file = forms.FileField()
