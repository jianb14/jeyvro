"""Automatic content rules (Phase 20.2 slice v1 — ROADMAP §20.2).

Pure functions, no database, no settings lookup at import time. Everything here
is a **heuristic that decides whether to ask a human to look** — never a
verdict, and never a reason to delete. Keeping the rules pure is what makes
them cheap to test exhaustively and impossible to couple to a write path.

Two deliberate omissions, both load-bearing:

* **No profanity or slur list.** Word blocklists are language-specific; a
  Filipino/Tagalog corpus is full of words an English-derived list calls
  abusive and vice versa. A false positive here mutes a real customer's
  review, which is a worse failure than a few extra rows in a staff queue.
* **No language model, no third-party service.** A rule that calls out to a
  network service turns a local decision into an availability dependency, and
  it would ship customer text to a third party. The documented rules are
  *structural* — properties of the text — not lexical.
"""
import re

# Characters that break up words to dodge a naive substring match
# ("s.h.o.p", "f r e e"). We are not building an evasion-resistant filter;
# this only keeps the obvious ones from scoring a clean 0.
_WORD_SPLIT = re.compile(r'[\s._\-·•|/\\_]+')

# A link: scheme-prefixed, bare `www.`, or a registrable-looking host with a
# path. Required a dot plus a 2+ letter TLD so "2.5kg" and "v1.2" do not match.
_URL = re.compile(
    r"""(?ix)
    (?: https? :// | www\. )            # explicit scheme or www prefix
    [^\s<>"']{3,}
    |
    \b [a-z0-9][a-z0-9\-]{1,62}         # host label
      \. (?: [a-z]{2,24} )              # TLD
      (?: / [^\s<>"']* )?               # optional path
    """
)

# Domains owned by the platform itself are not "the review links somewhere".
_PLATFORM_HOST_HINTS = ('jeyvro',)

_EMAIL = re.compile(r'\b[\w.+-]+\s?@\s?[\w-]+(?:\.[\w-]+)+\b')

# A phone number is found by *counting digits*, not by one clever pattern.
#
# The obvious single regex — `(?:[\s\-.]*\d[\s\-.]*){6,14}\d` — was tried and
# silently never matched, because the separators between digits are optional
# and the quantifier has no reason to stop where we want it to. Rather than
# tune an unreadable pattern, this finds a candidate run and then counts the
# digits in it, which states the actual rule: **7–15 digits, bounded by
# non-word characters**. The bounds are what keep `JV-20260926-ABCD2345` out —
# a 4-digit block is not a phone number, and a reviewer quoting their own
# order is not spam.
_PHONE_CANDIDATE = re.compile(r'(?<![\w-])\+?[0-9][0-9\s\-().]{5,24}')
_PHONE_MIN_DIGITS = 7
_PHONE_MAX_DIGITS = 15


def find_phone_numbers(text):
    """Every phone-shaped digit run in `text` (7–15 digits, word-bounded).

    The candidate regex is greedy across separators, so `0917 123 4567 for
    bulk` matches up to `0917 123 4567 ` (the `[0-9\s\-().]` class stops at
    the letters). The digit count is then taken from each candidate, and a
    candidate that runs past its digits into trailing prose is simply
    shortened to the digit groups it actually contains.
    """
    found = []
    for match in _PHONE_CANDIDATE.finditer(text or ''):
        raw_token = match.group()
        token = raw_token.strip()
        if not token:
            continue
        # The candidate class ends with separators, so the raw token often ends
        # on a space ("0917 123 4567 " before "for bulk"). The "glued to a
        # word" check below must look at what follows the *last digit*, not
        # what follows the last separator — otherwise every spaced phone
        # number in a sentence is rejected for touching the next word.
        end = match.start() + len(token)
        # Keep only the leading run of digit groups: "0917 123 4567" out of
        # "0917 123 4567 (0918) 222 3333" -> first number only, which is what
        # a reviewer writing one contact means.
        groups = re.findall(r'\+?\d[\d\-().]*', token)
        if not groups:
            continue
        digits_so_far = 0
        kept = []
        for group in groups:
            count = sum(1 for c in group if c.isdigit())
            if digits_so_far + count > _PHONE_MAX_DIGITS:
                break
            kept.append(group)
            digits_so_far += count
            if digits_so_far >= _PHONE_MIN_DIGITS:
                break
        if _PHONE_MIN_DIGITS <= digits_so_far <= _PHONE_MAX_DIGITS:
            # Reject a run glued to a word on either side ("v1.2.3" style).
            start = match.start()
            if start and (text[start - 1].isalnum() or text[start - 1] in '-_'):
                continue
            tail = text[end:end + 1]
            if tail and (tail.isalnum() or tail in '-_'):
                continue
            found.append(''.join(kept).strip())
    return found


# Words that make an otherwise-ambiguous number a contact detail.
_CONTACT_INTENT = re.compile(
    r'(?i)\b(?:call|text|contact|reach|ring|phone|cell|mobile|telegram|whatsapp|'
    r'inbox|email|e-mail|dm|message me|msg me|msg|bes)\b'
)

# A run of the same character long enough to be visual noise, not typography.
_REPEATED_CHAR = re.compile(r'(.)\1{9,}')


def _strip_word_separators(text):
    """`"s.h.o.p  n.a.m.e"` → `"shop name"` so split-word tricks don't pass."""
    return _WORD_SPLIT.sub(' ', text or '')


def _squash(text):
    """Remove separators *inside* tokens to expose `sh.op` style evasions."""
    return re.sub(r'[\s._\-·•|]+', '', text or '')


def find_links(text, *, allow_platform_links=False):
    """Return every link-looking token in `text`.

    A domain that is the *tail of an email address* is not a link: a customer
    writing "my email is me@shop.com" to a seller is giving a contact detail,
    not advertising a site, and a *message* is exactly where that is normal.
    So a candidate immediately preceded by an `@` (or glued to a word, as in
    the local part of an address) is skipped — the bare-domain branch would
    otherwise match `shop.com` inside every address and flag ordinary
    correspondence.
    """
    found = []
    for match in _URL.finditer(text or ''):
        token = match.group().strip().strip('.,;:!?)]}\'"')
        if not token:
            continue
        start = match.start()
        preceding = text[start - 1] if start else ''
        if preceding == '@':
            continue
        if start and (preceding.isalnum() or preceding in '+-_.'):
            # Glued to a word: only the local part of an email address looks
            # like this. Check a short window behind for an `@` to be sure.
            if _EMAIL.search(text[max(0, start - 64):match.end()]):
                continue
        if allow_platform_links and _host_is_platform(token):
            continue
        found.append(token)
    return found


def has_link(text, *, allow_platform_links=False):
    """True when the text carries a link out — the commonest spam shape.

    `allow_platform_links` exists because a *message* legitimately quotes the
    seller's own storefront URL back to them, while a *public review* that
    links anywhere is off the product and belongs in a queue. Callers pass the
    context; the rule does not guess it.
    """
    return bool(find_links(text, allow_platform_links=allow_platform_links))


def has_contact_details(text):
    """True when the text offers a way to be reached off-platform.

    An email address is self-evidently a contact detail. A bare number is
    only one when the text also says it is a contact — otherwise a review
    that reads "arrived 3 days late, 4 stars" is not a phone number, and
    neither is a reviewer quoting `JV-20260926-ABCD2345`.

    Checked against both the raw text and the separator-stripped view, because
    `s.p.a.m@gmail.com` should not slip past by splitting its own domain.
    """
    raw = text or ''
    for view in (raw, _strip_word_separators(raw), _squash(raw)):
        if _EMAIL.search(view):
            return True
    if not _CONTACT_INTENT.search(raw):
        return False
    # Intent present: now any phone-shaped run counts, in either view.
    return bool(find_phone_numbers(raw) or find_phone_numbers(_squash(raw)))


def shouting_ratio(text):
    """Fraction of cased letters that are capitals, ignoring digits/space."""
    letters = [c for c in (text or '') if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)


def is_shouting(text, *, min_letters=20, max_ratio=0.7):
    """True for long all-caps passages.

    Both a length and a ratio floor are required, so `OK` and `LOL` — and
    every sentence containing one initialised acronym — pass. Reviews in caps
    are not a crime; long unbroken shouting usually is, and this is a prompt
    to look rather than a judgement.
    """
    body = text or ''
    letters = [c for c in body if c.isalpha()]
    if len(letters) < min_letters:
        return False
    return shouting_ratio(body) > max_ratio


def has_visual_noise(text):
    """True for runs of one repeated character (`!!!!!!!!!!`, `aaaaaaaaaa`)."""
    return bool(_REPEATED_CHAR.search(text or ''))


def evaluate(text, *, kind):
    """Run the ruleset for one piece of content.

    `kind` is `'review'` or `'message'` and it genuinely changes the outcome:
    a public review linking off-platform is a queue item, while a seller
    quoting a storefront URL to their own buyer is simply conversation. The
    caller states the context; the ruleset does not infer it.

    Returns a plain dict — no models, no exceptions — so it can be asserted
    on directly in a test:

        {'flagged': bool, 'rules': ['link', ...], 'detail': 'human summary'}
    """
    raw = text or ''
    # Two views of the same text, on purpose. `_strip_word_separators`
    # collapses `s.h.o.p` into `shop` so an evasion cannot dodge a lexical
    # check — but it also destroys `/` and `.`, which would turn
    # `https://shopee.ph/store` into four harmless words and hide the link.
    # So links are read from the raw text and the lexical rules read the
    # stripped one.
    scrubbed = _strip_word_separators(raw)
    rules_hit = []

    if has_link(raw, allow_platform_links=(kind == 'message')):
        rules_hit.append('link')
    if kind == 'review' and has_contact_details(raw):
        # Contact details are spam in a *public review* — it is the one place
        # they are addressed to strangers. The same text in a private message
        # is a customer telling a seller how to reach them, which is fine.
        # Read from the raw text: scrubbing collapses `gmail.com` into
        # `gmail com` and the address stops being an address.
        rules_hit.append('contact')
    if is_shouting(scrubbed):
        rules_hit.append('shouting')

    return {
        'flagged': bool(rules_hit),
        'rules': rules_hit,
        'detail': ', '.join(rules_hit),
    }

    return re.sub(r'[\s._\-·•|]+', '', text or '')


def _host_is_platform(url):
    lowered = url.lower()
    return any(hint in lowered for hint in _PLATFORM_HOST_HINTS)
