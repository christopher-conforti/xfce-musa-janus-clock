# Spec: Janus Notation for the Civil Clock Panel

## What this changes

`civil_clock_genmon.py` currently prints Annit, Dattit, and Orit in plain
decimal. This update switches **all three, plus Solit wherever it's
displayed**, to true Janus balanced-dozenal notation, using ordinary
circled-digit Unicode characters for the negative half of the digit set.
This is not a display quirk scoped to one field — balanced dozenal is how
the Civilization writes numbers, full stop, so every value the clock
shows should use it.

There are two distinct forms in play, not one:

- **Orit and Solit** are continuous, Chronit-based measurements. They use
  full Janus notation: balanced digits, a decimal point at the units
  place, and a trailing `^N` magnitude marker, windowed to a chosen
  number of significant digits.
- **Annit and Dattit** are whole counts — completed years, completed
  days. They use the same balanced-dozenal digit alphabet and the same
  rule-of-six carry logic, but as **exact integers**: no decimal point,
  no magnitude marker, no significant-digit windowing. A count doesn't
  need to signal scale the way a measurement does; it just needs to be
  written correctly, in full.

Panel text goes from:

    An0 Da223 Or30.06

to:

    An0 Da2⑤⑤ Or3⑥.1③^1

(The same `janus_notation()` call used for Orit applies identically to
Solit wherever it's surfaced in the panel or tooltip.)

## Why

Chronit is the base unit of elapsed time and it's large — about a week
and a half. Anything smaller than a Chronit isn't a new named unit, it's
a fractional Chronit expressed in Janus magnitude notation, which is why
Orit and Solit both need the full continuous-value treatment. Annit and
Dattit are a different kind of number — counts, not measurements — but
they're still numbers the Civilization writes in its own numeral system,
which is balanced dozenal. Displaying them in plain decimal was a gap in
the original draft of this work, not a deliberate choice; balanced
dozenal applies to counting the same way it applies to measuring, it
just doesn't need the magnitude-notation machinery on top since a count
has no fractional part to window down.

**Note on the addendum:** the addendum's identifier section specifies
that the Annit field inside a CID or RID is written as a plain decimal
number, with no alphabet restriction and no transcription rules. That
rule is scoped specifically to the identifier's Y field — it's about
transcription safety for an alphanumeric string that gets read aloud and
typed character-by-character, not a general statement that Annit-the-
concept is always decimal everywhere it appears. The clock panel isn't
transcribing an identifier; it's displaying a number the way the
Civilization's citizens would actually read it. Those are different
contexts, and this update treats them as such. (The addendum's own
language conflates the two more than it should; that's a separate,
lower-priority cleanup and doesn't block this update.)

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
anyone re-implementing this in another language or auditing the logic.
They're shared between the continuous-value and whole-count paths —
both use the same digit alphabet and the same carry logic, differing
only in whether the result gets windowed to significant digits with a
magnitude marker, or kept as an exact integer with neither.

1. **Base:** 12 (dozenal). Each place represents a power of 12, same as
   decimal places represent powers of 10.
2. **Digit range:** -6 to +6 (balanced), not 0 to 11. Every value in that
   range has a single-character representation: 0-6 as themselves, -1
   through -6 as the circled equivalents above.
3. **Magnitude break point (continuous values only):** unlike decimal
   scientific notation, where the exponent only increments at an exact
   power of ten (so 900 stays 9×10² even though it's obviously closer to
   10³), Janus increments the magnitude at the true midpoint of the next
   magnitude up. This is a direct consequence of balanced rounding, not
   a separate rule bolted on. Verified against the source page's own
   worked examples:
   - 9 → `1③` (magnitude 1): 12 - 3.
   - 18 → `16` (magnitude 1): 12 + 6, no carry, since nothing nonzero
     follows the 6.
   - 19 → `2⑤` (magnitude 1): 24 - 5.
   - 73 → `1⑥1` (magnitude 2): 144 - 72 + 1. This is the case that most
     clearly demonstrates the balanced-rounding cascade — 73 in flat
     base-12 is a two-digit number (6,1), but the trailing nonzero digit
     forces the leading 6 to carry into a new leading digit as -6,
     producing a three-digit, magnitude-2 result.

   Whole-count values don't have a "magnitude break point" in this
   sense — an exact integer just has however many digits it has, with
   no windowing or rounding involved.
4. **The "rule of six":** digit value 6 is the one ambiguous case, and
   it applies identically whether the surrounding value is continuous
   or a whole count. It carries (becomes the balanced digit -6, with +1
   carried into the place to its left) if any nonzero digit follows it
   anywhere to its right. It stays as a plain +6 if it's the final
   nonzero digit (nothing but zeros after it). This must be resolved
   right-to-left, since whether something "follows" a given 6 depends
   on digits further right that may themselves have just been resolved.
5. **Magnitude marker (continuous values only):** written as `^N`, the
   same role `e+N` plays in decimal scientific notation, e.g.
   `Or3⑥.1③^1`. Janus doesn't need a separate reciprocal or sign marker
   for the exponent — a negative leading digit in the mantissa already
   handles values less than the reference scale. Whole-count values
   never carry this marker.
6. **Decimal point placement (continuous values only):** sits
   immediately after the digit occupying the units place (place value
   12^0), same convention as ordinary decimal. Whole-count values never
   carry a decimal point, since they have no fractional part.

## What's already validated

`janus_notation.py` (attached, also at
`/mnt/skills/user/janus-units/` once merged in) reproduces all four
worked examples from the source numbers page exactly, on both paths:

- Continuous form: 9 → `1③^1`, 18 → `16^1`, 19 → `2⑤^1`, 73 → `1⑥1^2`.
- Whole-count form (same four values, treated as exact integers instead
  of magnitude-windowed measurements): 9 → `1③`, 18 → `16`, 19 → `2⑤`,
  73 → `1⑥1` — identical digit sequences to the continuous form, just
  without the decimal point or magnitude marker, exactly as expected
  since both paths share the same carry logic.

These four were chosen originally because the source page calls out 9,
18/19, and 73 specifically as the non-obvious cases (the ones where
naive rounding gets the wrong magnitude), so passing all four on both
paths is a reasonable bar for correctness before wiring this into
anything user-facing. The whole-count path was additionally checked
against the source page's own 0-to-100 counting sequence (spot-checked
0 through 30), confirming the dozens-place digit flips to 1 starting at
7 and to 2 starting at 19, matching the page's description exactly.

The module exposes two functions that matter for integration:

    janus_notation(value, sig_digits=4, show_magnitude=True, trim_trailing_zeros=True) -> str

Use for continuous, Chronit-based values: Orit, Solit, any fractional
Chronit count. `value` is any positive real number — the function
handles magnitude placement and digit balancing internally.

    janus_integer(n) -> str

Use for whole counts: Annit, Dattit, or any other plain integer. `n` is
any integer (positive, negative, or zero) — the function converts it
exactly, with no windowing.

## Integration point

In `civil_clock_genmon.py`, every field currently formatted as plain
decimal should switch to the matching function above: Orit and Solit
(wherever Solit appears in the panel or tooltip) go through
`janus_notation()`, Annit and Dattit go through `janus_integer()`. This
is a full swap, not a partial one — every number the panel displays
should be in Janus notation, since that's how the Civilization itself
writes numbers, not a special case reserved for one field.

Suggested significant-digit count for `janus_notation()` calls on the
panel: 4, matching what's used in the worked examples above and in the
`30.06`-style Orit figures this project has been using informally.
Adjust if panel width becomes an issue; the circled glyphs are roughly
the same width as ASCII digits in most monospace UI fonts, so this
shouldn't need much tuning. `janus_integer()` calls need no such
tuning, since they render exactly however many digits the count
actually has.

## Not in scope for this update

- No change to the underlying Orit/Chronit/Annit/Dattit computation
  itself — this is purely a display-formatting change downstream of
  whatever numeric values the clock already computes.
- The addendum's own language around Annit's decimal-only treatment in
  the CID/RID context is broader than it needs to be and could use a
  tightening pass to make clear it's scoped to the identifier field
  specifically, not to Annit-the-concept generally. That's a documentation
  cleanup, not a functional blocker, and is being tracked separately
  from this spec.
- Other tools in this project that print Orit, Annit, Dattit, Solit, or
  any Chronit-fraction value in decimal (outside the genmon panel) are a
  separate follow-up, not covered by this spec. A note has been left on
  the bulletin board flagging that follow-up.

## Correction: the rule-of-six carry window bug (post-initial-draft)

An early version of `janus_notation()` evaluated the rule-of-six carry
decision against the value's true, effectively infinite-precision
fractional tail, rather than against only the digits actually being
displayed within the requested `sig_digits` window. Since almost any
non-round value has *some* nonzero content somewhere past the visible
digits, this made a visible trailing 6 carry into ⑥ far more often than
it should have — for example, `janus_notation(30.06)` produced
`3⑥.1③^1` while `janus_notation(30.0)` produced `26^1`, even though both
round to the same value at a coarser precision. That divergence looked
like a bug (and was reported as one) because two numbers indistinguishable
at a glance were rendering with different leading digits, purely due to
precision the display wasn't even showing.

**Fix:** the carry decision is now scoped strictly to the digits inside
the requested significant-digit window. `scale_pow` sizes the fixed-point
extraction to exactly `sig_digits` places (previously it over-extracted
by 6 extra places specifically to feed the old, wrong carry check), and
the rule-of-six's "does anything nonzero follow this 6" question is
answered only by looking at digits that will actually print. A value's
invisible tail past the display window can no longer change what's shown.

This does mean two values that are genuinely distinguishable within the
requested precision (e.g. `30.06` at 4 significant digits, where the
fractional part really does land inside the visible window) will
correctly still diverge from a clean `30`. That's not a bug — at 4 sig
digits there's enough precision on the page to show that 30.06 isn't
exactly 30. The bug was specifically that this divergence used to happen
even when the extra precision was invisible to begin with.

**Practical consequence for the panel:** the module's own default of 4
significant digits is more precision than a glance-level clock display
wants, since it will legitimately show the ⑥-carry behavior for any Orit
value with a nonzero fractional Chronit remainder — which is most of the
time, since Orit is constantly advancing. For `civil_clock_genmon.py`,
call `janus_notation(orit_value, sig_digits=2)` explicitly rather than
relying on the module default, so the panel shows a clean whole-Orit
reading (e.g. `26^1`) rather than a jarring carry-heavy one. This is a
call-site choice, not a module default change — `janus_notation()`'s
default of 4 significant digits stays as-is, since that's what the
worked-example correctness checks (including 73's full carry cascade)
are verified against, and lowering the module default to 2 would make
`janus_notation(73)` round away the very digit that demonstrates the
carry logic works.
