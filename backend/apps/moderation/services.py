"""Moderation services — flag, then let a human decide (§20.2).

The whole slice rests on one rule: **the system queues, it does not censor.**
`flag_content` records that an automatic rule fired; it never edits the text,
never hides it from its author, and never tells the author it was censored. A
flagged *review* is pulled out of the public list exactly as a review with
three customer reports already is (§14.3), and a flagged *conversation* moves
to the existing `reported` status. The author's own copy stays readable to
them, so a false positive costs a queue row and a few staff minutes — never a
customer's right to speak.

Everything is audit-logged through `apps.audit.services.log_event` (§9), which
is the only write path for audit rows.
"""
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.services import log_event

from . import rules
from .models import ContentFlag


class ModerationError(ValueError):
    """Customer-safe rejection — code + message, never a stack."""

    def __init__(self, message, *, code='moderation_rejected'):
        super().__init__(message)
        self.code = code


def _subject_kwargs(review=None, conversation=None):
    if bool(review) == bool(conversation):
        raise ModerationError(
            'A flag needs exactly one subject.', code='invalid_subject'
        )
    if review is not None:
        return {'review': review}
    return {'conversation': conversation}


@transaction.atomic
def flag_content(*, author, kind, review=None, conversation=None, rule_codes=(),
                 detail=''):
    """Record (or re-open) the one flag row for a subject.

    One row per subject is a DB constraint, not a convention: a user who edits
    their review three times must not manufacture a queue of duplicates for
    staff to re-triage. A second hit on an already-resolved row **reopens** it,
    because content that was dismissed once and has now acquired a link is
    genuinely new information, not a stale notification.
    """
    subject = _subject_kwargs(review=review, conversation=conversation)

    existing = ContentFlag.objects.filter(**subject).first()
    if existing is not None:
        merged = sorted(set(existing.rules or []) | set(rule_codes))
        reopened = existing.status != ContentFlag.Status.OPEN
        existing.rules = merged
        existing.rule_detail = detail or existing.rule_detail
        if reopened:
            existing.status = ContentFlag.Status.OPEN
            existing.resolved_by = None
            existing.resolved_at = None
            existing.resolution_note = ''
        existing.save(update_fields=[
            'rules', 'rule_detail', 'status', 'resolved_by', 'resolved_at',
            'resolution_note', 'updated_at',
        ])
        if reopened:
            log_event(
                author, 'content_flag_reopened', existing,
                detail={'kind': kind, 'rules': merged},
            )
        return existing, False

    flag = ContentFlag.objects.create(
        kind=kind,
        author=author,
        rules=sorted(set(rule_codes)),
        rule_detail=(detail or '')[:255],
        **subject,
    )
    log_event(
        author, 'content_flagged', flag,
        detail={'kind': kind, 'rules': flag.rules, 'detail': flag.rule_detail},
    )
    return flag, True


def screen_review(*, review, text):
    """Screen a review body. Returns the `ContentFlag` if one was raised."""
    verdict = rules.evaluate(text, kind='review')
    if not verdict['flagged']:
        return None
    flag, _created = flag_content(
        author=review.user,
        kind=ContentFlag.Kind.REVIEW,
        review=review,
        rule_codes=verdict['rules'],
        detail=verdict['detail'],
    )
    return flag


def screen_conversation(*, conversation, text, author):
    """Screen a message body. Returns the `ContentFlag` if one was raised."""
    verdict = rules.evaluate(text, kind='message')
    if not verdict['flagged']:
        return None
    flag, _created = flag_content(
        author=author,
        kind=ContentFlag.Kind.CONVERSATION,
        conversation=conversation,
        rule_codes=verdict['rules'],
        detail=verdict['detail'],
    )
    return flag



# --------------------------------------------------------------------------------------
# Staff queue — the human decision the flag exists to reach
# --------------------------------------------------------------------------------------

def queue(*, status=ContentFlag.Status.OPEN, kind=''):
    """The staff worklist, newest first.

    Reads the flags themselves, never the text: a moderator opens the review
    or conversation from here and reads it where it already lives, so this
    listing never becomes a second copy of customer content (§10.1).
    """
    qs = ContentFlag.objects.select_related(
        'author', 'review__product', 'conversation__store', 'resolved_by',
    )
    if status:
        qs = qs.filter(status=status)
    if kind:
        qs = qs.filter(kind=kind)
    return qs


def open_flag_count():
    """How much work is waiting — drives the staff console badge."""
    return ContentFlag.objects.filter(status=ContentFlag.Status.OPEN).count()


def _restore_subject(flag, *, actor, note):
    """Put the subject back in the clear after a dismissal.

    A review returns through the **reviews** service rather than a status
    write here: only that path recomputes the product and store rating
    aggregates (§6 rule 3), so a restored review cannot come back with a
    rating that silently disagrees with the rows behind it.
    """
    from apps.reviews import services as review_services

    if flag.review_id is None:
        return None
    review = flag.review
    if review.status in (review_services.ReviewStatus.HIDDEN,
                         review_services.ReviewStatus.FLAGGED):
        return review_services.moderate_review(
            actor, review=review, action='restore', reason=note or 'Flag dismissed.',
        )
    return review


@transaction.atomic
def resolve_flag(actor, flag, *, action, note=''):
    """Staff dismisses or confirms a flag — staff-only, always audited.

    `dismiss` means the rule misfired: the content returns to the public list
    and the reason is recorded so a repeatedly-misfiring rule can be found and
    tuned. `confirm` means it was abuse: the review is hidden through the
    reviews service (so its aggregates follow) and a conversation stays
    `reported` for the support team.
    """
    if action not in ('dismiss', 'confirm'):
        raise ModerationError('Unknown moderation action.', code='invalid_action')
    if flag.status != ContentFlag.Status.OPEN:
        raise ModerationError('This flag is already resolved.', code='already_resolved')
    note = (note or '').strip()
    if action == 'confirm' and not note:
        raise ModerationError(
            'A reason is required to confirm a flag as abuse.', code='reason_required'
        )

    audit_action = 'content_flag_dismissed' if action == 'dismiss' else 'content_flag_confirmed'
    if action == 'dismiss':
        _restore_subject(flag, actor=actor, note=note)
    else:
        from apps.reviews import services as review_services

        if flag.review_id is not None:
            review = flag.review
            if review.status != review_services.ReviewStatus.HIDDEN:
                review_services.moderate_review(
                    actor, review=review, action='hide', reason=note,
                )

    flag.status = (
        ContentFlag.Status.DISMISSED if action == 'dismiss'
        else ContentFlag.Status.CONFIRMED
    )
    flag.resolved_by = actor
    flag.resolved_at = timezone.now()
    flag.resolution_note = note[:255]
    flag.save(update_fields=[
        'status', 'resolved_by', 'resolved_at', 'resolution_note', 'updated_at',
    ])

    log_event(
        actor, audit_action, flag,
        detail={
            'kind': flag.kind,
            'rules': flag.rules,
            'note': note,
            'review': flag.review_id,
            'conversation': flag.conversation_id,
        },
    )
    return flag
