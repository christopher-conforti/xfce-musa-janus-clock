# Spec: Janus Notation for the Civil Clock Panel

## What this changes

`civil_clock_genmon.py` currently prints Annit, Dattit, and Orit in plain
decimal. This update switches the Orit figure — the only one of the three
that moves fast enough to matter at panel granularity — to true Janus
balanced-dozenal notation, using ordinary circled-digit Unicode characters
for the negative half of the digit set. Annit and Dattit stay in plain
decimal, since they're whole-count units that barely change (Annit ticks
once a year, Dattit once a day) and gain nothing from dozenal notation.

Panel text goes from:

    An0 Da223 Or30.06

to:

    An0 Da223 Or3⑥.1③^1

## Why

Chronit is the base unit of elapsed time and it's large — about a week and
a half. Anything smaller than a Chronit isn't a new named unit, it's a
fractional Chronit expressed in Janus magnitude notation. Orit is a
running Chronit count, so displaying it in true Janus notation rather than
decimal is more than cosmetic: it's the only reading that actually reflects
how the Civilization's own clock is supposed to work, per the numbers page
this project is built against.

## The negative-digit glyph problem, and how it's resolved

Balanced dozenal uses digits from -6 to +6 instead of 0 to 9. Musa's own
notation marks a negative digit by circling it. An earlier draft of this
spec used a backtick prefix (`` `6 `` for -6) as an ASCII-safe stand-in,
on the assumption that circled digits might not render reliably. That
assumption was wrong and the backtick approach is dropped.

The correct rendering uses the actual Unicode circled-digit characters,
U+2460 through U+2465:

| Digit | Character | Codepoint |
|---|---|---|
| -1 | ① | U+2460 |
| -2 | ② | U+2461 |
| -3 | ③ | U+2462 |
| -4 | ④ | U+2463 |
| -5 | ⑤ | U+2464 |
| -6 | ⑥ | U+2465 |

These are ordinary Unicode, not part of the Musa font — any UTF-8-aware
renderer displays them correctly, including Xfce's Generic Monitor panel
text and tooltip. No custom font or fallback glyph is needed. Positive
digits 0 through 6 print as plain ASCII digits.

**Do not use backticks, a leading minus sign per digit, or any other
ASCII stand-in.** The circled-digit form is the actual notation, not an
approximation of it, and it's what should ship.

## Notation rules (for implementation, not just display)

These are the rules `janus_notation.py` (below) implements, restated for
anyone re-implementing this in another language or auditing the logic:

1. **Base:** 12 (dozenal). Each place represents a power of 12, same as
   decimal places represent powers of 10.
2. **Digit range:** -6 to +6 (balanced), not 0 to 11. Every value in that
   range has a single-character representation: 0-6 as themselves, -1
   through -6 as the circled equivalents above.
3. **Magnitude break point:** unlike decimal scientific notation, where
   the exponent only increments at an exact power of ten (so 900 stays
   9×10² even though it's obviously closer to 10³), Janus increments the
   magnitude at the true midpoint of the next magnitude up. This is a
   direct consequence of balanced rounding, not a separate rule bolted
   on. Verified against the source page's own worked examples:
   - 9 → `1③` (magnitude 1): 12 - 3.
   - 18 → `16` (magnitude 1): 12 + 6, no carry, since nothing nonzero
     follows the 6.
   - 19 → `2⑤` (magnitude 1): 24 - 5.
   - 73 → `1⑥1` (magnitude 2): 144 - 72 + 1. This is the case that most
     clearly demonstrates the balanced-rounding cascade — 73 in flat
     base-12 is a two-digit number (6,1), but the trailing nonzero digit
     forces the leading 6 to carry into a new leading digit as -6,
     producing a three-digit, magnitude-2 result.
4. **The "rule of six":** digit value 6 is the one ambiguous case. It
   carries (becomes the balanced digit -6, with +1 carried into the
   place to its left) if any nonzero digit follows it anywhere to its
   right. It stays as a plain +6 if it's the final nonzero digit (nothing
   but zeros after it). This must be resolved right-to-left, since
   whether something "follows" a given 6 depends on digits further right
   that may themselves have just been resolved.
5. **Magnitude marker:** written as `^N`, the same role `e+N` plays in
   decimal scientific notation, e.g. `Or3⑥.1③^1`. Janus doesn't need a
   separate reciprocal or sign marker for the exponent — a negative
   leading digit in the mantissa already handles values less than the
   reference scale.
6. **Decimal point placement:** sits immediately after the digit
   occupying the units place (place value 12^0), same convention as
   ordinary decimal.

## What's already validated

`janus_notation.py` (attached, also at
`/mnt/skills/user/janus-units/` once merged in) reproduces all four
worked examples from the source numbers page exactly: 9 → `1③^1`,
18 → `16^1`, 19 → `2⑤^1`, 73 → `1⑥1^2`. These four were chosen originally
because the source page calls out 9, 18/19, and 73 specifically as the
non-obvious cases (the ones where naive rounding gets the wrong
magnitude), so passing all four is a reasonable bar for correctness
before wiring this into anything user-facing.

The module exposes one function that matters for integration:

    janus_notation(value, sig_digits=4, show_magnitude=True, trim_trailing_zeros=True) -> str

`value` is any positive real number (an Orit figure, a fractional
Chronit, etc.) — the function handles the full magnitude placement and
digit balancing internally; callers don't need to pre-scale anything.

## Integration point

In `civil_clock_genmon.py`, wherever the Orit figure is currently
formatted for panel or tooltip text, swap the plain decimal formatting
for a call to `janus_notation()`. Annit and Dattit formatting is
unaffected — leave those as plain decimal.

Suggested significant-digit count for the panel: 4, matching what's used
in the worked examples above and in the `30.06`-style Orit figures this
project has been using informally. Adjust if panel width becomes an
issue; the circled glyphs are roughly the same width as ASCII digits in
most monospace UI fonts, so this shouldn't need much tuning.

## Not in scope for this update

- Annit/Dattit stay decimal — they're whole-count units and Janus
  notation doesn't apply to them (see the Addendum's identifier section:
  Annit is a plain decimal number by design, not drawn from any
  restricted alphabet).
- No change to the underlying Orit/Chronit computation itself — this is
  purely a display-formatting change downstream of whatever numeric Orit
  value the clock already computes.
- Other tools in this project that print Orit, Chronit-fraction, or
  similar values in decimal (outside the genmon panel) are a separate
  follow-up, not covered by this spec. A note has been left on the
  bulletin board flagging that follow-up.
