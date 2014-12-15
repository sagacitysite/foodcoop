from django import forms

from .models import Group, Order, Product


class GroupChooseForm(forms.Form):
    group = forms.ModelChoiceField(
        queryset=Group.objects.filter(enclosure=True))


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['amount']


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
