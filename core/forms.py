from django import forms

from .models import (
    Company, Warehouse, User, ProductCategory, Product, BusinessPartner,
    WeightTicket, BusinessDocument, BusinessDocumentItem,
)


class SetupForm(forms.Form):
    organization_name = forms.CharField(label='Organizata', max_length=160)
    company_name = forms.CharField(label='Kompania', max_length=180)
    company_nipt = forms.CharField(label='NIPT', max_length=40, required=False)
    warehouse_name = forms.CharField(label='Magazina e parë', max_length=180)
    admin_name = forms.CharField(label='Emri i administratorit', max_length=180)
    username = forms.CharField(label='Username', max_length=150)
    email = forms.EmailField(label='Email', required=False)
    password = forms.CharField(label='Fjalëkalimi', widget=forms.PasswordInput, min_length=8)


class LoginForm(forms.Form):
    username = forms.CharField(label='Username ose email', max_length=150)
    password = forms.CharField(label='Fjalëkalimi', widget=forms.PasswordInput)


class SetupForm(forms.Form):
    organization_name = forms.CharField(label='Organizimi', max_length=160)
    company_name = forms.CharField(label='Kompania', max_length=180)
    company_nipt = forms.CharField(label='NIPT i kompanisë', max_length=40, required=False)
    warehouse_name = forms.CharField(label='Magazina e parë', max_length=180)
    admin_name = forms.CharField(label='Emri i administratorit', max_length=180)
    username = forms.CharField(label='Username', max_length=150)
    email = forms.EmailField(label='Email', required=False)
    password = forms.CharField(label='Fjalëkalimi', widget=forms.PasswordInput, min_length=8)


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'nipt', 'address', 'phone', 'email', 'currency', 'active']


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['company', 'name', 'code', 'address', 'active']


class UserForm(forms.ModelForm):
    password = forms.CharField(label='Fjalëkalimi', widget=forms.PasswordInput, required=False, min_length=8)

    class Meta:
        model = User
        fields = ['full_name', 'username', 'email', 'role', 'companies', 'warehouses', 'active']


class CategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['company', 'name', 'code', 'active']


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['company', 'category', 'code', 'barcode', 'name', 'base_unit', 'pack_unit',
                  'pallet_unit', 'pack_coefficient', 'pallet_coefficient',
                  'purchase_price', 'sale_price', 'vat_rate', 'active']


class PartnerForm(forms.ModelForm):
    class Meta:
        model = BusinessPartner
        fields = ['company', 'partner_type', 'code', 'name', 'nipt', 'address', 'city',
                  'phone', 'email', 'credit_limit', 'active']


class WeightTicketForm(forms.ModelForm):
    class Meta:
        model = WeightTicket
        fields = ['company', 'warehouse', 'supplier', 'product', 'document_no', 'document_date',
                  'bags_count', 'gross_weight', 'packaging_weight', 'discount_percent',
                  'unit_price', 'vehicle_plate', 'notes']
        widgets = {'document_date': forms.DateInput(attrs={'type': 'date'})}


class BusinessDocumentForm(forms.ModelForm):
    class Meta:
        model = BusinessDocument
        fields = ['company', 'warehouse', 'partner', 'document_no', 'document_date', 'notes']
        widgets = {'document_date': forms.DateInput(attrs={'type': 'date'})}


class BusinessDocumentItemForm(forms.ModelForm):
    class Meta:
        model = BusinessDocumentItem
        fields = ['product', 'description', 'unit', 'coefficient', 'quantity',
                  'free_quantity', 'unit_price', 'vat_rate']
        widgets = {
            'description': forms.TextInput(attrs={'placeholder': 'Opsionale — përdoret emri i produktit'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['free_quantity'].required = False
        self.fields['description'].required = False
        self.fields['unit'].required = False
        self.fields['coefficient'].required = False
        self.fields['vat_rate'].required = False
        self.fields['quantity'].required = True
        self.fields['unit_price'].required = True