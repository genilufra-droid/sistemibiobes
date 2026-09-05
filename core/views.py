"""Views për Sistemi Genit Cloud (versioni Django)."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    BusinessDocumentForm, BusinessDocumentItemForm, CompanyForm, PartnerForm,
    ProductForm, SetupForm, UserForm, WarehouseForm, WeightTicketForm,
)
from .models import (
    AuditLog, BusinessDocument, BusinessDocumentItem, BusinessPartner, Company,
    Product, ProductCategory, StockMovement, Tenant, User, Warehouse, WeightTicket,
)
from .services import (
    audit, cancel_document, compute_document_totals, compute_item_totals,
    confirm_document, confirm_weight_ticket,
)

DOC_TYPE_LABELS = dict(BusinessDocument.DOC_TYPE_CHOICES)


# ─────────────────────────────────────────────────────────────
# Ndihmës
# ─────────────────────────────────────────────────────────────

def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return (xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR'))


def _scoped_companies(user):
    """Kompanitë e aksesueshme të përdoruesit."""
    if user.is_super_admin:
        return Company.objects.filter(tenant=user.tenant)
    return user.companies.all()


def _scoped_warehouses(user):
    if user.is_super_admin:
        return Warehouse.objects.filter(tenant=user.tenant)
    return user.warehouses.all()


def _company_ids(user):
    return _scoped_companies(user).values_list('id', flat=True)


# ─────────────────────────────────────────────────────────────
# Setup & Auth
# ─────────────────────────────────────────────────────────────

def setup(request):
    if Tenant.objects.exists():
        return redirect('login')
    if request.method == 'POST':
        form = SetupForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            tenant = Tenant.objects.create(
                name=d['organization_name'],
                code=d['organization_name'][:40].upper().replace(' ', '_'),
            )
            company = Company.objects.create(tenant=tenant, name=d['company_name'], nipt=d['company_nipt'])
            warehouse = Warehouse.objects.create(tenant=tenant, company=company, name=d['warehouse_name'], code='WH1')
            user = User.objects.create_user(
                username=d['username'], email=d['email'], password=d['password'],
                full_name=d['admin_name'], tenant=tenant, role='SUPER_ADMIN', is_staff=True,
            )
            user.companies.add(company)
            user.warehouses.add(warehouse)
            audit(user, 'SETUP_COMPANY', 'tenant', tenant.id, company, {'name': tenant.name}, _client_ip(request))
            login(request, user)
            return redirect('dashboard')
    else:
        form = SetupForm()
    return render(request, 'core/setup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            audit(user, 'LOGIN', 'user', user.id, None, {'ip': _ip(request)}, _ip(request))
            return redirect('dashboard')
        messages.error(request, 'Username ose fjalëkalim i gabuar.')
    return render(request, 'core/login.html')


@login_required
def logout_view(request):
    audit(request.user, 'LOGOUT', 'user', request.user.id, None, {}, _ip(request))
    logout(request)
    return redirect('login')


def _ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return (xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR'))


# ─────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    user = request.user
    companies = _scoped_companies(user)
    warehouses = _scoped_warehouses(user)
    active_users = User.objects.filter(tenant=user.tenant, active=True).count()
    actions_today = AuditLog.objects.filter(tenant=user.tenant, created_at__date=timezone.localdate()).count()
    products = Product.objects.filter(tenant=user.tenant, company_id__in=_company_ids(user)).count()
    stock_rows = _stock_rows(user)
    total_stock = sum((r['quantity_stock'] for r in stock_rows), Decimal('0'))
    recent_audit = AuditLog.objects.filter(tenant=user.tenant)[:10]
    return render(request, 'core/dashboard.html', {
        'companies': companies, 'warehouses': warehouses,
        'active_users': active_users, 'actions_today': actions_today,
        'products': products, 'total_stock': total_stock,
        'recent_audit': recent_audit, 'page_title': 'Dashboard',
    })


# ─────────────────────────────────────────────────────────────
# Cloud Core: Kompanitë, Magazinat, Përdoruesit, Audit
# ─────────────────────────────────────────────────────────────

@login_required
def company_list(request):
    companies = _scoped_companies(request.user)
    return render(request, 'core/company_list.html', {'companies': companies, 'page_title': 'Kompanitë'})


@login_required
def company_create(request):
    if not request.user.is_super_admin:
        messages.error(request, 'Vetëm Super Administratori mund të shtojë kompani.')
        return redirect('company_list')
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.tenant = request.user.tenant
            company.save()
            audit(request.user, 'COMPANY_CREATE', 'company', company.id, company, {'name': company.name}, _ip(request))
            messages.success(request, 'Kompania u krijua.')
            return redirect('company_list')
    else:
        form = CompanyForm()
    return render(request, 'core/form.html', {'form': form, 'page_title': 'Kompani e re', 'submit': 'Ruaj'})


@login_required
def warehouse_list(request):
    warehouses = _scoped_warehouses(request.user)
    return render(request, 'core/warehouse_list.html', {'warehouses': warehouses, 'page_title': 'Magazinat'})


@login_required
def warehouse_create(request):
    if not request.user.is_admin:
        messages.error(request, 'Nuk keni leje.')
        return redirect('warehouse_list')
    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            wh = form.save(commit=False)
            wh.tenant = request.user.tenant
            wh.save()
            audit(request.user, 'WAREHOUSE_CREATE', 'warehouse', wh.id, wh.company, {'name': wh.name}, _ip(request))
            messages.success(request, 'Magazina u krijua.')
            return redirect('warehouse_list')
    else:
        form = WarehouseForm()
    form.fields['company'].queryset = _scoped_companies(request.user)
    return render(request, 'core/form.html', {'form': form, 'page_title': 'Magazinë e re', 'submit': 'Ruaj'})


@login_required
def user_list(request):
    if not request.user.is_admin:
        messages.error(request, 'Nuk keni leje.')
        return redirect('dashboard')
    users = User.objects.filter(tenant=request.user.tenant)
    return render(request, 'core/user_list.html', {'users': users, 'page_title': 'Përdoruesit'})


@login_required
def user_create(request):
    if not request.user.is_admin:
        return redirect('user_list')
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            user = User.objects.create_user(
                username=d['username'], email=d['email'], password=d['password'] or 'changeme123',
                full_name=d['full_name'], tenant=request.user.tenant, role=d['role'], active=d['active'],
            )
            user.companies.set(d['companies'])
            user.warehouses.set(d['warehouses'])
            audit(request.user, 'USER_CREATE', 'user', user.id, None, {'username': user.username}, _ip(request))
            messages.success(request, 'Përdoruesi u krijua.')
            return redirect('user_list')
    else:
        form = UserForm()
    form.fields['companies'].queryset = _scoped_companies(request.user)
    form.fields['warehouses'].queryset = _scoped_warehouses(request.user)
    return render(request, 'core/form.html', {'form': form, 'page_title': 'Përdorues i ri', 'submit': 'Ruaj'})


@login_required
def audit_list(request):
    if not (request.user.is_admin or request.user.role == 'AUDITOR'):
        return redirect('dashboard')
    logs = AuditLog.objects.filter(tenant=request.user.tenant)
    q = request.GET.get('q', '')
    if q:
        logs = logs.filter(action__icontains=q) | logs.filter(user__username__icontains=q)
    return render(request, 'core/audit_list.html', {'logs': logs, 'page_title': 'Audit Log'})


# ─────────────────────────────────────────────────────────────
# Regjistra: Artikuj, Furnitorë, Klientë
# ─────────────────────────────────────────────────────────────

@login_required
def product_list(request):
    products = Product.objects.filter(tenant=request.user.tenant, company_id__in=_company_ids(request.user))
    return render(request, 'core/product_list.html', {'products': products, 'page_title': 'Artikujt'})


@login_required
def product_create(request):
    if not request.user.is_write:
        return redirect('product_list')
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            p = form.save(commit=False)
            p.tenant = request.user.tenant
            p.code = p.code.upper()
            p.save()
            audit(request.user, 'PRODUCT_CREATE', 'product', p.id, p.company, {'code': p.code, 'name': p.name}, _ip(request))
            messages.success(request, 'Artikulli u krijua.')
            return redirect('product_list')
    else:
        form = ProductForm()
    form.fields['company'].queryset = _scoped_companies(request.user)
    form.fields['category'].queryset = ProductCategory.objects.filter(tenant=request.user.tenant)
    return render(request, 'core/form.html', {'form': form, 'page_title': 'Artikull i ri', 'submit': 'Ruaj'})


def _partner_list(request, ptype):
    return BusinessPartner.objects.filter(
        tenant=request.user.tenant,
        company_id__in=_company_ids(request.user),
        partner_type__in=[ptype, 'BOTH'],
    )


@login_required
def supplier_list(request):
    partners = _partner_list(request, 'SUPPLIER')
    return render(request, 'core/partner_list.html', {'partners': partners, 'ptype': 'SUPPLIER', 'page_title': 'Furnitorët'})


@login_required
def customer_list(request):
    partners = _partner_list(request, 'CUSTOMER')
    return render(request, 'core/partner_list.html', {'partners': partners, 'ptype': 'CUSTOMER', 'page_title': 'Klientët'})


def _partner_create(request, ptype):
    if not request.user.is_write:
        return redirect('supplier_list' if ptype == 'SUPPLIER' else 'customer_list')
    if request.method == 'POST':
        form = PartnerForm(request.POST)
        if form.is_valid():
            bp = form.save(commit=False)
            bp.tenant = request.user.tenant
            bp.partner_type = ptype
            bp.save()
            audit(request.user, 'PARTNER_CREATE', 'business_partner', bp.id, bp.company, {'name': bp.name, 'type': ptype}, _ip(request))
            messages.success(request, 'Partneri u krijua.')
            return redirect('supplier_list' if ptype == 'SUPPLIER' else 'customer_list')
    else:
        form = PartnerForm()
    form.fields['company'].queryset = _scoped_companies(request.user)
    return render(request, 'core/form.html', {'form': form, 'page_title': 'Partner i ri', 'submit': 'Ruaj'})


@login_required
def supplier_create(request):
    return _partner_create(request, 'SUPPLIER')


@login_required
def customer_create(request):
    return _partner_create(request, 'CUSTOMER')


# ─────────────────────────────────────────────────────────────
# Peshimi
# ─────────────────────────────────────────────────────────────

@login_required
def weight_list(request):
    tickets = WeightTicket.objects.filter(tenant=request.user.tenant, company_id__in=_company_ids(request.user))
    return render(request, 'core/weight_list.html', {'tickets': tickets, 'page_title': 'Formulari i Peshave'})


@login_required
def weight_create(request):
    if not request.user.is_write:
        return redirect('weight_list')
    if request.method == 'POST':
        form = WeightTicketForm(request.POST)
        if form.is_valid():
            t = form.save(commit=False)
            t.tenant = request.user.tenant
            t.net_weight = max(Decimal('0'), t.gross_weight - t.packaging_weight)
            t.accepted_weight = t.net_weight * (Decimal('1') - t.discount_percent / Decimal('100'))
            t.total_value = t.accepted_weight * t.unit_price
            t.created_by = request.user
            t.save()
            audit(request.user, 'WEIGHT_CREATE', 'weight_ticket', t.id, t.company, {'documentNo': t.document_no}, _ip(request))
            messages.success(request, 'Formulari i peshës u krijua.')
            return redirect('weight_list')
    else:
        form = WeightTicketForm()
    form.fields['company'].queryset = _scoped_companies(request.user)
    form.fields['warehouse'].queryset = _scoped_warehouses(request.user)
    form.fields['supplier'].queryset = BusinessPartner.objects.filter(tenant=request.user.tenant, partner_type__in=['SUPPLIER', 'BOTH'])
    form.fields['product'].queryset = Product.objects.filter(tenant=request.user.tenant)
    return render(request, 'core/form.html', {'form': form, 'page_title': 'Formular i ri i Peshës', 'submit': 'Ruaj'})


@login_required
def weight_confirm(request, pk):
    ticket = get_object_or_404(WeightTicket, pk=pk, tenant=request.user.tenant)
    try:
        confirm_weight_ticket(ticket, request.user)
        messages.success(request, 'Formulari u konfirmua dhe stoku u përditësua.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('weight_list')


# ─────────────────────────────────────────────────────────────
# Stoku
# ─────────────────────────────────────────────────────────────

def _stock_rows(user):
    return (StockMovement.objects
            .filter(tenant=user.tenant, company_id__in=_company_ids(user))
            .values('company__name', 'warehouse__name', 'product__code', 'product__name', 'product__base_unit', 'product__pack_coefficient')
            .annotate(quantity_stock=Sum('quantity_base'))
            .order_by('company__name', 'warehouse__name', 'product__name'))


@login_required
def stock_list(request):
    rows = _stock_rows(request.user)
    return render(request, 'core/stock_list.html', {'rows': rows, 'page_title': 'Stoku'})


# ─────────────────────────────────────────────────────────────
# Dokumentet e biznesit
# ─────────────────────────────────────────────────────────────

@login_required
def document_list(request, doc_type):
    if doc_type not in DOC_TYPE_LABELS:
        return redirect('dashboard')
    docs = BusinessDocument.objects.filter(tenant=request.user.tenant, doc_type=doc_type,
                                           company_id__in=_company_ids(request.user))
    return render(request, 'core/document_list.html', {
        'docs': docs, 'doc_type': doc_type, 'doc_label': DOC_TYPE_LABELS[doc_type],
        'page_title': DOC_TYPE_LABELS[doc_type],
    })


@login_required
def document_create(request, doc_type):
    if doc_type not in DOC_TYPE_LABELS:
        return redirect('dashboard')
    if not request.user.is_write:
        return redirect('document_list', doc_type=doc_type)
    if request.method == 'POST':
        form = BusinessDocumentForm(request.POST)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.tenant = request.user.tenant
            doc.doc_type = doc_type
            doc.created_by = request.user
            doc.save()
            audit(request.user, f'DOCUMENT_CREATE_{doc_type}', 'business_document', doc.id, doc.company, {'documentNo': doc.document_no}, _ip(request))
            messages.success(request, 'Dokumenti u krijua. Shto rreshtat.')
            return redirect('document_detail', pk=doc.id)
    else:
        form = BusinessDocumentForm()
    form.fields['company'].queryset = _scoped_companies(request.user)
    form.fields['warehouse'].queryset = _scoped_warehouses(request.user)
    form.fields['partner'].queryset = BusinessPartner.objects.filter(tenant=request.user.tenant)
    return render(request, 'core/form.html', {'form': form, 'page_title': f'Dokument i ri — {DOC_TYPE_LABELS[doc_type]}', 'submit': 'Ruaj'})


@login_required
def document_detail(request, pk):
    doc = get_object_or_404(BusinessDocument, pk=pk, tenant=request.user.tenant)
    item_form = BusinessDocumentItemForm()
    item_form.fields['product'].queryset = Product.objects.filter(tenant=request.user.tenant, company=doc.company)
    return render(request, 'core/document_detail.html', {
        'doc': doc, 'item_form': item_form,
        'page_title': f'{doc.get_doc_type_display()} {doc.document_no}',
    })


@login_required
def document_add_item(request, pk):
    doc = get_object_or_404(BusinessDocument, pk=pk, tenant=request.user.tenant)
    if doc.status != 'DRAFT':
        messages.error(request, 'Dokumenti nuk është në status Draft.')
        return redirect('document_detail', pk=doc.id)
    if request.method == 'POST':
        form = BusinessDocumentItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.document = doc
            item.description = item.description or item.product.name
            item.unit = item.unit or item.product.base_unit
            item.coefficient = item.coefficient or item.product.pack_coefficient
            item.vat_rate = item.vat_rate or item.product.vat_rate
            item.save()
            compute_item_totals(item)
            compute_document_totals(doc)
            audit(request.user, 'DOCUMENT_ITEM_ADD', 'business_document_item', item.id, doc.company, {'documentNo': doc.document_no}, _ip(request))
            messages.success(request, 'Rreshti u shtua.')
    return redirect('document_detail', pk=doc.id)


@login_required
def document_confirm(request, pk):
    doc = get_object_or_404(BusinessDocument, pk=pk, tenant=request.user.tenant)
    try:
        confirm_document(doc, request.user)
        messages.success(request, 'Dokumenti u konfirmua dhe stoku u përditësua.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('document_detail', pk=doc.id)


@login_required
def document_cancel(request, pk):
    doc = get_object_or_404(BusinessDocument, pk=pk, tenant=request.user.tenant)
    try:
        cancel_document(doc, request.user)
        messages.success(request, 'Dokumenti u anulua.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('document_detail', pk=doc.id)
