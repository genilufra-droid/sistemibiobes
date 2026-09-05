"""Logjika e biznesit: audit, lëvizje stoku, konfirmim dokumentesh."""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import AuditLog, StockMovement, WeightTicket, BusinessDocument


def audit(user, action, entity_type='', entity_id='', company=None, metadata=None, ip=None):
    """Regjistron një veprim në Audit Log."""
    AuditLog.objects.create(
        tenant=user.tenant if user else None,
        user=user,
        company=company,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else '',
        metadata=metadata or {},
        ip=ip,
    )


def record_stock_movement(user, company, warehouse, product, movement_type,
                          quantity_base, unit_cost=0, reference_type='', reference_id=None,
                          reference_no=''):
    """Krijon një lëvizje stoku."""
    return StockMovement.objects.create(
        tenant=user.tenant,
        company=company,
        warehouse=warehouse,
        product=product,
        movement_type=movement_type,
        quantity_base=quantity_base,
        unit_cost=unit_cost,
        reference_type=reference_type,
        reference_id=reference_id,
        reference_no=reference_no,
        created_by=user,
    )


@transaction.atomic
def confirm_weight_ticket(ticket, user):
    """Konfirmon një formulë peshe dhe krijon lëvizje stoku (WEIGHT_RECEIPT)."""
    if ticket.status != 'DRAFT':
        raise ValueError('Dokumenti nuk është në status Draft.')
    record_stock_movement(
        user, ticket.company, ticket.warehouse, ticket.product,
        'WEIGHT_RECEIPT', ticket.accepted_weight, ticket.unit_price,
        reference_type='weight_ticket', reference_id=ticket.id, reference_no=ticket.document_no,
    )
    ticket.status = 'CONFIRMED'
    ticket.confirmed_at = timezone.now()
    ticket.save(update_fields=['status', 'confirmed_at', 'updated_at'])
    audit(user, 'WEIGHT_CONFIRM', 'weight_ticket', ticket.id, ticket.company,
          {'documentNo': ticket.document_no})


@transaction.atomic
def confirm_document(doc, user):
    """Konfirmon një dokument biznesi dhe regjistron lëvizje stoku sipas llojit."""
    if doc.status != 'DRAFT':
        raise ValueError('Dokumenti nuk është në status Draft.')

    # Llojet që rrisin stokun (hyrje)
    stock_in = ('PURCHASE_RECEIPT', 'PURCHASE_INVOICE', 'SALES_RETURN', 'SUPPLIER_RETURN')
    # Llojet që ulin stokun (dalje)
    stock_out = ('DELIVERY_NOTE', 'SALES_INVOICE', 'PURCHASE_RETURN')

    for item in doc.items.all():
        qty = item.quantity * item.coefficient
        if doc.doc_type in stock_in:
            mtype = 'PURCHASE_RECEIPT' if doc.doc_type in ('PURCHASE_RECEIPT', 'PURCHASE_INVOICE') else 'SALES_RETURN'
            record_stock_movement(user, doc.company, doc.warehouse, item.product, mtype,
                                  qty, item.unit_price, 'business_document', doc.id, doc.document_no)
        elif doc.doc_type in stock_out:
            mtype = 'DELIVERY_NOTE' if doc.doc_type in ('DELIVERY_NOTE', 'SALES_INVOICE') else 'PURCHASE_RETURN'
            record_stock_movement(user, doc.company, doc.warehouse, item.product, mtype,
                                  -qty, item.unit_price, 'business_document', doc.id, doc.document_no)

    doc.status = 'CONFIRMED'
    doc.confirmed_at = timezone.now()
    doc.save(update_fields=['status', 'confirmed_at', 'updated_at'])
    audit(user, f'DOCUMENT_CONFIRM_{doc.doc_type}', 'business_document', doc.id, doc.company,
          {'documentNo': doc.document_no})


@transaction.atomic
def cancel_document(doc, user):
    if doc.status != 'DRAFT':
        raise ValueError('Dokumenti nuk është në status Draft.')
    doc.status = 'CANCELLED'
    doc.cancelled_at = timezone.now()
    doc.save(update_fields=['status', 'cancelled_at', 'updated_at'])
    audit(user, f'DOCUMENT_CANCEL_{doc.doc_type}', 'business_document', doc.id, doc.company,
          {'documentNo': doc.document_no})


def compute_document_totals(doc):
    """Rillogarit totalet e dokumentit nga rreshtat."""
    total_net = sum((i.line_net for i in doc.items.all()), Decimal('0'))
    total_vat = sum((i.line_vat for i in doc.items.all()), Decimal('0'))
    doc.total_net = total_net
    doc.total_vat = total_vat
    doc.total_amount = total_net + total_vat
    doc.save(update_fields=['total_net', 'total_vat', 'total_amount', 'updated_at'])
    return doc


def compute_item_totals(item):
    """Rillogarit totalet e një rreshti."""
    qty = item.quantity
    item.line_net = (qty * item.unit_price).quantize(Decimal('0.0001'))
    item.line_vat = (item.line_net * item.vat_rate / Decimal('100')).quantize(Decimal('0.0001'))
    item.line_total = item.line_net + item.line_vat
    item.save(update_fields=['line_net', 'line_vat', 'line_total'])
    return item