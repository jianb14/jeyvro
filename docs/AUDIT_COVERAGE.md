# Audit coverage (§20.3)

The honest answer to one question: **for a given sensitive operation, does
anything record that it happened, who did it, and what changed?** This file is
that answer, kept next to the code so it can be checked against it — Phase 20.3
exists because the honest state was "we had an audit log and no idea what was
missing from it".

`backend/tests/test_audit_coverage.py` is the machine-checked half of this
document: it drives the operations below and asserts the action names written
here, so this page cannot quietly rot into fiction.

## The rules behind the table

1. **One write path.** Every audit row goes through
   `apps.audit.services.log_event`. Domain services call it inside the
   transaction that performs the work, so a rolled-back operation leaves no
   claim that it happened.
2. **`actor=None` means the system did it** — a gateway webhook, the payment
   expiry cron, a status aggregation — and the row says so. It is never dressed
   up as a person.
3. **An event with no domain object must name its subject.** `log_event` takes
   `object_type`/`object_id` when there is no `obj`, and **raises** if it gets
   neither: a blank-subject row is a trail that proves nothing.
4. **Money terms are recorded before/after, not as "changed".** A price edit
   that only says *something moved* cannot answer "what did it cost when I
   ordered?".
5. **Audit detail is staff-only.** `detail` never crosses to a customer
   endpoint; the order timeline maps actions through an allow-list
   (`orders/services.py::_TIMELINE_STEPS`) instead of serving raw rows.

## Coverage

Actions are named exactly as they appear in the `action` column.

### Money

| Operation | Action | Actor | Proven by |
| --- | --- | --- | --- |
| Order placed | `order.placed` | customer | `test_checkout.py` |
| Order cancelled (pending payment voided) | `order.cancelled` | customer | `test_account_orders.py` |
| **Stale COD reservation released (§20.2 v2)** | `order.cod_reservation_released` | support / operations / administrator | `test_abuse_controls.py` |
| Payment captured (COD at delivery, or gateway webhook) | `payment.captured` | seller / system | `test_payments.py`, `test_payments_webhooks.py` |
| Payment cancelled with its order | `payment.cancelled` | system | `test_payments.py` |
| Payment expired unpaid | `payment.expired` | system (cron) | `test_payments.py` |
| Refund settled | `refund.settled` | finance (or the return flow) | `test_staff_orders.py` |
| Refund failed | `refund.failed` | system (gateway) | `test_payments_webhooks.py` |
| Commission rate / platform settings changed | `platform_settings_update` | administrator | `test_platform_settings.py` |
| Return refund issued / settled / failed | `return.refund_issued`, `return.refunded`, `return.refund_failed` | staff or system | `test_returns.py` |
| **CSV report exported (§20.3)** | `analytics.exported` | finance / administrator / oversight group | `test_audit_coverage.py` |

### Seller money terms (§20.3 additions)

| Operation | Action | Actor | Proven by |
| --- | --- | --- | --- |
| Product base/compare-at price changed | `product_price_changed` (with `from`/`to`) | seller | `test_audit_coverage.py` |
| Variant price changed | `variant_price_changed` (with `from`/`to`) | seller | `test_audit_coverage.py` |
| Store profile edited (shipping fee, free-shipping threshold) | `store_profile_updated` (fee before/after) | seller | `test_audit_coverage.py` |

A **retitle or a policy reword is not audited** — it moves no money, and a
trail of every copy edit is noise. Only the money fields produce a row; the
same row names the copy fields it carried along.

### Fulfillment

| Operation | Action | Actor | Proven by |
| --- | --- | --- | --- |
| Seller order being prepared / packed | `seller_order.processing`, `seller_order.packed` | seller | `test_fulfillment.py` |
| Shipment created | `shipment.created` | seller (or staff) | `test_fulfillment.py` |
| Shipment status transition (incl. `delivered`, which triggers COD capture) | `shipment.status_updated` | seller / staff / carrier webhook | `test_fulfillment.py`, `test_audit_coverage.py` |
| Parent order status aggregated from slices | `order.status_aggregated` | system | `test_account_orders.py` |
| Customer request filed / withdrawn / resolved | `order.request_created`, `order.request_withdrawn`, `order.request_resolved` | customer / staff | `test_account_orders.py`, `test_returns.py` |

The shipment transition was **already** audited before Phase 20.3 — the audit
row sits inside the same atomic block as the status write, so the COD capture
triggered by `delivered` and the record of the transition commit together.




### Access, roles and account standing

| Operation | Action | Actor | Proven by |
| --- | --- | --- | --- |
| Staff group granted / revoked | `staff_group_assigned`, `staff_group_removed` | administrator | `test_staff_management.py` |
| Account suspended / reinstated | `user_suspended`, `user_reactivated` | administrator | `test_staff_management.py` |
| Seller application approved / rejected | `seller_application_approved`, `seller_application_rejected` | staff | `test_stores.py` |
| Store suspended / reactivated | `store_suspended`, `store_activated` | staff | `test_stores.py` |

### Catalog and taxonomy moderation

| Operation | Action | Actor | Proven by |
| --- | --- | --- | --- |
| Product published / rejected in review | `product_review_published`, `product_review_rejected` | operations / administrator | `test_staff_catalog.py` |
| Product unpublished by staff | `product_unpublished` | staff | `test_staff_catalog.py` |
| Category created / updated / deleted | `category_created`, `category_updated`, `category_deleted` | operations / administrator | `test_staff_catalog.py` |
| Brand created / updated / deleted | `brand_created`, `brand_updated`, `brand_deleted` | operations / administrator | `test_staff_catalog.py` |

### Promotions, reviews, messaging, returns and disputes

| Operation | Action | Actor | Proven by |
| --- | --- | --- | --- |
| Promotion applied at checkout | `promotion.applied` | customer | `test_promotions.py` |
| Voucher redeemed | `voucher.redeemed` | customer | `test_vouchers.py` |
| Campaign / promotion created, toggled, deactivated | `campaign.created`, `promotion.created`, `promotion.toggled`, `promotion.deactivated` | staff | `test_promotions.py` |
| Review hidden / restored | `review_hidden`, `review_restored` | moderator | `test_reviews.py` |
| Review reports resolved | `review_reports_resolved` | moderator | `test_reviews.py` |
| Conversation reported | `conversation_reported` | customer | `test_messaging.py` |
| Content flagged by an automatic rule (Phase 20.2) | `content_flagged`, `content_flag_reopened` | the author (system action on their content) | `test_abuse_controls.py` |
| Flag dismissed / confirmed by staff (§20.2) | `content_flag_dismissed`, `content_flag_confirmed` | moderator | `test_abuse_controls.py` |
| User blocked / unblocked (§20.2) | `conversation_blocked`, `conversation_unblocked` | the blocker | `test_abuse_controls.py` |
| Return lifecycle | `return.requested`, `return.shipped`, `return.received`, `return.restocked`, `return.cancelled`, `return.closed`, `return.approved`, `return.rejected`, `return.admin_decision` | customer / seller / staff | `test_returns.py` |
| Dispute lifecycle | `dispute.created`, `dispute.statement_added`, `dispute.evidence_added`, `dispute.review`, `dispute.resolved`, `dispute.cancelled` | customer / seller / support | `test_returns.py` |

## Deliberately **not** audited

Writing these down is the point of the phase; a silent gap is a gap.

| Operation | Why not |
| --- | --- |
| Every catalog/store read | Reads are not state changes. The trail answers "what did they do?", not "what did they look at" — with one deliberate exception, the **export** (§19.4), which moves aggregate figures out of the building in bulk. |
| Cart mutations | Session-scoped and self-owned; nothing leaves. |
| Product/variant creation and deletion by the seller | Owner-scoped, and the review trail already records the moderation decision that makes a listing public. |
| Login, logout, token refresh | Auth events belong to a security log, not this one; the throttle state (Phase 20.1) is the current home. |
| Notification delivery | Has its own read/unread surface; delivery is a side effect of an already-audited action. |
| Reading the audit log itself | An oversight read of staff-only rows; auditing oversight reads is a Phase 23 concern (retention/export), not a per-view write. |

## Known limits

- **No retention, export or immutability policy yet.** The table grows
  forever and staff can read it but not take it away. Retention, a signed
  export and alerting on money actions belong with the deployment phase.
- **Detail is free-form JSON.** The matrix above is the contract; nothing
  validates that a new action's `detail` keeps the shape its readers expect.
- **The audit viewer is a read-only staff UI** — filtering by action/actor
  lives in `apps/audit/views.py` and `/staff/audit`.
- **Suspicious-pattern alerting** (many exports in a row, a burst of refunds)
  is §20.2's job, not this phase's.

## What Phase 20.3 changed

- `log_event` accepts an object-less event with an explicit subject, and
  refuses one with neither.
- `analytics.exported` — every served CSV, with actor, report, range and row
  count; refused and malformed exports write nothing.
- `product_price_changed` / `variant_price_changed` — seller price edits with
  before/after.
- `store_profile_updated` — the store PATCH became a service
  (`stores.services.update_own_profile`) so the shipping fee and
  free-shipping threshold keep their before/after, and a seller still cannot
  touch another store.
- No migrations: the audit model is unchanged.
