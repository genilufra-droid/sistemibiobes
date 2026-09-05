"""
Modelet e Sistemi Genit Cloud (versioni Django).

Riprodhojnë skemën PostgreSQL të sistemit origjinal Node/Express:
tenants, companies, warehouses, users, user_companies, user_warehouses,
audit_logs, product_categories, products, business_partners, weight_tickets,
stock_movements, business_documents, business_document_items.
"""

import uuid
from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


def new_uuid():
    return uuid.uuid4()


# ─────────────────────────────────────────────────────────────
# Cloud Core
# ─────────────────────────────────────────────────────────────

class Tenant(models.Model):
    """Organizata (multi-tenant)."""
    id = models.UUIDField(primary_key=True, default=new_uuid, editable=False)
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=40, unique=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Company(models.Model):
    """Kompania brenda organizatës (multi-company)."""
    id = models.UUIDField(primary_key=True, default=new_uuid, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='companies')
    name = models.CharField(max_length=180)
    nipt = models.CharField(max_length=40, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=60, blank=True, null=True)
    email = models.EmailField(max_length=160, blank=True, null=True)
    currency = models.CharField(max_length=8, default='ALL')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = [('tenant', 'name')]

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    """Magazina brenda kompanisë."""
    id = models.UUIDField(primary_key=True, default=new_uuid, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='warehouses')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='warehouses')
    name = models.CharField(max_length=180)
    code = models.CharField(max_length=40)
    address = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = [('tenant', 'company', 'code')]

    def __str__(self):
        return f'{self.name} ({self.company.name})'


class User(AbstractUser):
    """Përdorues i personalizuar me rol dhe tenant."""
    ROLE_CHOICES = [
        ('SUPER_ADMIN', 'Super Administrator'),
        ('COMPANY_ADMIN', 'Administrator Kompanie'),
        ('MANAGER', 'Menaxher'),
        ('FINANCIER', 'Financier'),
        ('MAGAZINIER', 'Magazinier'),
        ('OPERATOR_PESHORE', 'Operator Peshore'),
        ('SHITES', 'Shitës'),
        ('ARKETAR', 'Arketar'),
        ('AUDITOR', 'Auditor'),
        ('READ_ONLY', 'Vetëm Lexim'),
    ]
    id = models.UUIDField(primary_key=True, default=new_uuid, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    full_name = models.CharField(max_length=180, blank=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='READ_ONLY')
    companies = models.ManyToManyField(Company, related_name='users', blank=True)
    warehouses = models.ManyToManyField(Warehouse, related_name='users', blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['username']

    def __str__(self):
        return self.username

    @property
    def is_super_admin(self):
        return self.role == 'SUPER_ADMIN'

    @property
    def is_admin(self):
        return self.role in ('SUPER_ADMIN', 'COMPANY_ADMIN')

    @property
    def is_write(self):
        return self.role in ('SUPER_ADMIN', 'COMPANY_ADMIN', 'MANAGER', 'FINANCIER',
                             'MAGAZINIER', 'OPERATOR_PESHORE', 'SHITES')


class AuditLog(models.Model):
    """Historik i pandryshueshëm i veprimeve."""
    id = models.UUIDField(primary_key=True, default=new_uuid, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='audit_logs', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=80)
    entity_type = models.CharField(max_length=60, blank=True)
    entity_id = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action} @ {self.created_at:%Y-%m-%d %H:%M}'


# ─────────────────────────────────────────────────────────────
# Regjistra (Faza 2)
# ─────────────────────────────────────────────────────────────

class ProductCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=new_uuid, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='categories')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=50, blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = [('tenant', 'company', 'name')]

    def __str__(self):
        return self.name


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=new_uuid, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='products')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    code = models.CharField(max_length=80)
    barcode = models.CharField(max_length=120, blank=True, null=True)
    name = models.CharField(max_length=220)
    base_unit = models.CharField(max_length=30, default='copë')
    pack_unit = models.CharField(max_length=30, default='koli')
    pallet_unit = models.CharField(max_length=30, default='paletë')
    pack_coefficient = models.DecimalField(max_digits=18, decimal_places=6, default=1)
    pallet_coefficient = models.DecimalField(max_digits=18, decimal_places=6, default=1)
    purchase_price = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    sale_price = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    vat_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = [('tenant', 'company', 'code')]

    def __str__(self):
        return f'{self.code} — {self.name}'


class BusinessPartner(models.Model):
    PARTNER_TYPES = [
        ('CUSTOMER', 'Klient'),
        ('SUPPLIER', 'Furnitor'),
        ('BOTH', 'Të dyja'),
    ]
    id = models.UUIDField(primary_key=True, default=new_uuid, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='partners')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='partners')
    partner_type = models.CharField(max_length=20, choices=PARTNER_TYPES, default='CUSTOMER')
    code = models.CharField(max_length=80, blank=True, null=True)
    name = models.CharField(max_length=220)
    nipt = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=120, blank=True, null=True)
    phone = models.CharField(max_length=80, blank=True, null=True)
    email = models.EmailField(max_length=180, blank=True, null=True)
    credit_limit = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = [('tenant', 'company', 'name')]

    def __str__(self):
        return self.name


class WeightTicket(models.Model):
    """Formulari i peshave (pranim lëndë e parë)."""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('CONFIRMED', 'Konfirmuar'),
        ('CANCELLED', 'Anuluar'),
    ]
    id = models.UUIDField(primary_key=True, default=new_uuid, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='weight_tickets')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='weight_tickets')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.RESTRICT, related_name='weight_tickets')
    supplier = models.ForeignKey(BusinessPartner, on_delete=models.RESTRICT, null=True, blank=True, related_name='weight_tickets')
    product = models.ForeignKey(Product, on_delete=models.RESTRICT, related_name='weight_tickets')
    document_no = models.CharField(max_length=60)
    document_date = models.DateField(default=timezone.localdate)
    bags_count = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    gross_weight = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    packaging_weight = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    net_weight = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    discount_percent = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    accepted_weight = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    unit_price = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    total_value = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    vehicle_plate = models.CharField(max_length=40, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='weight_tickets')
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-document_date', '-created_at']
        unique_together = [('tenant', 'company', 'document_no')]

    def __str__(self):
        return self.document_no


class StockMovement(models.Model):
    """Lëvizje stoku (baza e gjendjes)."""
    id = models.UUIDField(primary_key=True, default=new_uuid, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='stock_movements')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='stock_movements')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.RESTRICT, related_name='stock_movements')
    product = models.ForeignKey(Product, on_delete=models.RESTRICT, related_name='stock_movements')
    movement_type = models.CharField(max_length=30)
    quantity_base = models.DecimalField(max_digits=18, decimal_places=6)
    unit_cost = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    reference_type = models.CharField(max_length=50, blank=True, null=True)
    reference_id = models.UUIDField(null=True, blank=True)
    reference_no = models.CharField(max_length=80, blank=True, null=True)
    movement_date = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-movement_date']

    def __str__(self):
        return f'{self.movement_type} {self.quantity_base} {self.product_id}'


# ─────────────────────────────────────────────────────────────
# Dokumentet e biznesit (Blerje & Shitje)
# ─────────────────────────────────────────────────────────────

class BusinessDocument(models.Model):
    DOC_TYPE_CHOICES = [
        ('PURCHASE_RFQ', 'Kërkesë për Ofertë'),
        ('PURCHASE_ORDER', 'Porosi Blerjeje'),
        ('PURCHASE_RECEIPT', 'Pranim'),
        ('PURCHASE_INVOICE', 'Faturë Blerjeje'),
        ('SUPPLIER_RETURN', 'Kthim Furnitori'),
        ('PURCHASE_RETURN', 'Kthim Blerjeje'),
        ('SALES_QUOTE', 'Ofertë Shitjeje'),
        ('SALES_ORDER', 'Porosi Shitjeje'),
        ('DELIVERY_NOTE', 'Fletë-Dalje'),
        ('SALES_INVOICE', 'Faturë Shitjeje'),
        ('SALES_RETURN', 'Kthim Shitjeje'),
    ]
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('CONFIRMED', 'Konfirmuar'),
        ('CANCELLED', 'Anuluar'),
    ]
    id = models.UUIDField(primary_key=True, default=new_uuid, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='documents')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='documents')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.RESTRICT, null=True, blank=True, related_name='documents')
    partner = models.ForeignKey(BusinessPartner, on_delete=models.RESTRICT, null=True, blank=True, related_name='documents')
    doc_type = models.CharField(max_length=40, choices=DOC_TYPE_CHOICES)
    document_no = models.CharField(max_length=80)
    document_date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    notes = models.TextField(blank=True, null=True)
    total_net = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    total_vat = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    total_amount = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    source_document = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='derived_documents')
    source_document_type = models.CharField(max_length=40, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-document_date', '-created_at']
        unique_together = [('tenant', 'company', 'doc_type', 'document_no')]

    def __str__(self):
        return f'{self.get_doc_type_display()} {self.document_no}'

    @property
    def is_purchase(self):
        return self.doc_type in ('PURCHASE_RFQ', 'PURCHASE_ORDER', 'PURCHASE_RECEIPT',
                                 'PURCHASE_INVOICE', 'SUPPLIER_RETURN', 'PURCHASE_RETURN')

    @property
    def is_sales(self):
        return self.doc_type in ('SALES_QUOTE', 'SALES_ORDER', 'DELIVERY_NOTE',
                                 'SALES_INVOICE', 'SALES_RETURN')


class BusinessDocumentItem(models.Model):
    id = models.UUIDField(primary_key=True, default=new_uuid, editable=False)
    document = models.ForeignKey(BusinessDocument, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.RESTRICT, related_name='document_items')
    description = models.CharField(max_length=240)
    unit = models.CharField(max_length=30)
    coefficient = models.DecimalField(max_digits=18, decimal_places=6, default=1)
    quantity = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    free_quantity = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    unit_price = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    vat_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    line_net = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    line_vat = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    line_total = models.DecimalField(max_digits=18, decimal_places=4, default=0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.description} x {self.quantity}'
