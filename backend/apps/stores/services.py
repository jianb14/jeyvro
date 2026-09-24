"""Store services — every state transition lives here, never in views.

Rules honoured (PROJECT_CONTEXT §6 v1.2, marketplace-sellers):
- apply → application + store both pending; is_seller flips on approval only
- review/approve/reject and suspend/activate are staff-only, audit-logged
- sellers never self-approve; no transition happens by blind field writes
"""
from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_event

from .models import SellerApplication, Store


def apply_as_seller(user, *, store_name, store_description='', contact_phone=''):
    """A customer applies to become a seller. Creates the pending
    application + pending store atomically (marketplace-sellers rule)."""
    with transaction.atomic():
        application = SellerApplication.objects.create(
            user=user,
            store=Store.objects.create(
                user=user,
                name=store_name,
                description=store_description,
                contact_email=user.email,
                contact_phone=contact_phone,
                status=Store.Status.PENDING,
            ),
            store_name=store_name,
            store_description=store_description,
            contact_phone=contact_phone,
            status=SellerApplication.Status.PENDING,
        )
    return application


def review_application(staff_user, application, *, decision, reason=''):
    """Staff approves or rejects a pending application (audit-logged).

    approve → store goes active and the user's is_seller flag flips true;
    reject → a reason is mandatory and the store stays pending (reapply
    by editing the store profile and resubmitting).
    """
    if application.status != SellerApplication.Status.PENDING:
        raise ValueError('This application was already reviewed.')
    if application.user_id == staff_user.pk:
        raise ValueError('Staff cannot review their own application.')

    with transaction.atomic():
        application.status = decision
        application.reviewed_by = staff_user
        application.reviewed_at = timezone.now()
        if decision == SellerApplication.Status.REJECTED:
            if not reason.strip():
                raise ValueError('A rejection reason is required.')
            application.rejection_reason = reason
        application.save(update_fields=[
            'status', 'reviewed_by', 'reviewed_at',
            'rejection_reason', 'updated_at',
        ])

        store = application.store
        if decision == SellerApplication.Status.APPROVED:
            store.status = Store.Status.ACTIVE
            seller = application.user
            seller.is_seller = True
            seller.save(update_fields=['is_seller', 'updated_at'])
        else:
            store.status = Store.Status.PENDING
        store.save(update_fields=['status', 'updated_at'])

        log_event(
            staff_user,
            f'seller_application_{decision}',
            application,
            detail={
                'store_id': store.pk,
                'store_slug': store.slug,
                'applicant_id': application.user_id,
                'reason': reason,
            },
        )
    return application


def suspend_store(staff_user, store, *, reason=''):
    """Staff suspends an active store (audit-logged). Data is kept; the
    storefront just becomes invisible to the public (§6 v1.2)."""
    if store.status != Store.Status.ACTIVE:
        raise ValueError('Only active stores can be suspended.')

    with transaction.atomic():
        store.status = Store.Status.SUSPENDED
        store.suspended_at = timezone.now()
        store.save(update_fields=['status', 'suspended_at', 'updated_at'])
        log_event(staff_user, 'store_suspended', store, detail={'reason': reason})
    return store


def activate_store(staff_user, store, *, reason=''):
    """Staff re-activates a suspended store (audit-logged)."""
    if store.status != Store.Status.SUSPENDED:
        raise ValueError('Only suspended stores can be re-activated.')

    with transaction.atomic():
        store.status = Store.Status.ACTIVE
        store.suspended_at = None
        store.save(update_fields=['status', 'suspended_at', 'updated_at'])
        log_event(staff_user, 'store_activated', store, detail={'reason': reason})
    return store