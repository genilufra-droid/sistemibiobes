from django.urls import path, re_path

from . import views

urlpatterns = [
    # Auth & Setup
    path('', views.dashboard, name='dashboard'),
    path('setup/', views.setup, name='setup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Cloud Core
    path('companies/', views.company_list, name='company_list'),
    path('companies/new/', views.company_create, name='company_create'),
    path('warehouses/', views.warehouse_list, name='warehouse_list'),
    path('warehouses/new/', views.warehouse_create, name='warehouse_create'),
    path('users/', views.user_list, name='user_list'),
    path('users/new/', views.user_create, name='user_create'),
    path('audit/', views.audit_list, name='audit_list'),

    # Regjistra
    path('products/', views.product_list, name='product_list'),
    path('products/new/', views.product_create, name='product_create'),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/new/', views.supplier_create, name='supplier_create'),
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/new/', views.customer_create, name='customer_create'),

    # Blerje & Peshim
    path('weights/', views.weight_list, name='weight_list'),
    path('weights/new/', views.weight_create, name='weight_create'),
    path('weights/<str:pk>/confirm/', views.weight_confirm, name='weight_confirm'),

    # Shitje & Magazinë
    path('stock/', views.stock_list, name='stock_list'),

    # Dokumentet e biznesit
    re_path(r'^documents/(?P<pk>[0-9a-f-]{36})/confirm/$', views.document_confirm, name='document_confirm'),
    re_path(r'^documents/(?P<pk>[0-9a-f-]{36})/cancel/$', views.document_cancel, name='document_cancel'),
    re_path(r'^documents/(?P<pk>[0-9a-f-]{36})/add-item/$', views.document_add_item, name='document_add_item'),
    re_path(r'^documents/(?P<pk>[0-9a-f-]{36})/$', views.document_detail, name='document_detail'),
    path('documents/<str:doc_type>/', views.document_list, name='document_list'),
    path('documents/<str:doc_type>/new/', views.document_create, name='document_create'),
]