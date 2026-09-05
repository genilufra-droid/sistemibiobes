from .models import Tenant


def global_context(request):
    """Kontekst global për të gjitha templates: setup status + tenant."""
    setup_done = Tenant.objects.exists()
    return {
        'setup_done': setup_done,
        'APP_NAME': 'Sistemi Genit',
        'APP_SUBTITLE': 'Cloud ERP',
    }