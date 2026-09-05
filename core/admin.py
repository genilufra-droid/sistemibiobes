from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Tenant, Company, Warehouse, User, AuditLog,
    ProductCategory, Product, BusinessPartner, WeightTicket, StockMovement,
    BusinessDocument, BusinessDocumentItem,
)


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('username', 'full_name', 'role', 'tenant', 'active', 'is_staff')
    list_filter = ('role', 'active', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Genit', {'fields': ('tenant', 'full_name', 'role', 'companies', 'warehouses', 'active')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Genit', {'fields': ('tenant', 'full_name', 'role', 'companies', 'warehouses', 'active')}),
    )


admin.site.register(User, CustomUserAdmin)
admin.site.register(Tenant)
admin.site.register(Company)
admin.site.register(Warehouse)
admin.site.register(AuditLog)
admin.site.register(ProductCategory)
admin.site.register(Product)
admin.site.register(BusinessPartner)
admin.site.register(WeightTicket)
admin.site.register(StockMovement)
admin.site.register(BusinessDocument)
admin.site.register(BusinessDocumentItem)