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

    An 0 Da 223 Or 30.06

to:

    An 0 Da 2⑤⑤ Or 1*3⑥1③④④0

(The same `janus_notation()` call used for Orit applies identically to
Solit wherever it's surfaced in the panel or tooltip. See the "Second
correction" section below for the current magnitude-first format and
default precision — the example above reflects that current format, not
the earlier mantissa-first draft.)

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
only in whether the result gets windowed to significant digits with
magnitude notation, or kept as an exact integer with none.

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
   worked examples, shown here as (magnitude, mantissa) pairs:
   - 9 → magnitude 1, mantissa `1③`: 12 - 3.
   - 18 → magnitude 1, mantissa `16`: 12 + 6, no carry, since nothing
     nonzero follows the 6.
   - 19 → magnitude 1, mantissa `2⑤`: 24 - 5.
   - 73 → magnitude 2, mantissa `1⑥1`: 144 - 72 + 1. This is the case
     that most clearly demonstrates the balanced-rounding cascade — 73
     in flat base-12 is a two-digit number (6,1), but the trailing
     nonzero digit forces the leading 6 to carry into a new leading
     digit as -6, producing a three-digit, magnitude-2 result.

   Whole-count values don't have a "magnitude break point" in this
   sense — an exact integer just has however many digits it has, with
   no windowing or rounding involved.
4. **The "rule of six":** digit value 6 is the one ambiguous case, and
   it applies identically whether the surrounding value is continuous
   or a whole count. It carries (becomes the balanced digit -6, with +1
   carried into the place to its left) if any nonzero digit follows it
   anywhere to its right **within whatever is actually being shown** —
   not against invisible precision beyond the display window. It stays
   as a plain +6 if it's the final nonzero digit within that window.
   This must be resolved right-to-left, since whether something
   "follows" a given 6 depends on digits further right that may
   themselves have just been resolved. (See "Correction: the rule-of-six
   carry window bug" below for why the window-scoping matters and what
   broke before it was added.)
5. **Magnitude notation format (continuous values only):** written as
   `<magnitude>*<mantissa>`, magnitude FIRST, then `*` (the plain-Unicode
   stand-in for the Musa Break character), then the mantissa digits —
   e.g. `1*3⑥1③④④`. This ordering was confirmed against the actual
   Musa Academy reference implementation, `jalibrary.js`: its
   `janusReal()` function returns `exponent + Break + mantissa`, magnitude
   before mantissa, and the same order is visible in the Latinized
   convention on the Janus social units page ("So 2*11538" reads as
   magnitude 2, mantissa 11538). There is no decimal point anywhere in
   this format — magnitude notation replaces the need for one, the same
   way decimal scientific notation (`3e5`) has no decimal point sitting
   inside the digit string either. Whole-count values never carry
   magnitude notation at all — no `*`, no magnitude prefix of any kind —
   since a count has no fractional part and gains nothing from the
   scale-signaling magnitude notation exists to provide.
6. **Sign placement:** a negative overall value gets a leading `-` before
   the magnitude. A *negative magnitude* (a value smaller than the
   reference scale, e.g. a sub-Chronit fraction) needs no separate sign
   marker of its own — the magnitude is just a signed Janus integer, so
   a magnitude of -3 renders exactly as `janus_integer(-3)` would.
   Verified: the value `0.0006` renders as `-3*1054⑤1`, matching
   `jalibrary.js`'s own exponent computation for that value exactly.

## What's already validated

`janus_notation.py` (attached, also at
`/mnt/skills/user/janus-units/` once merged in) reproduces all four
worked examples from the source numbers page exactly, on both paths,
and has additionally been checked digit-for-digit against `jalibrary.js`
directly (run under Node, output diffed against this module's Python
output) rather than relying on hand-derivation from the reference pages
alone:

- Continuous form (magnitude*mantissa, default 6 significant digits):
  9 → `1*1③0000`, 18 → `1*160000`, 19 → `1*2⑤0000`, 73 → `2*1⑥1000`.
- Whole-count form (same four values, treated as exact integers instead
  of magnitude-windowed measurements, no magnitude notation at all):
  9 → `1③`, 18 → `16`, 19 → `2⑤`, 73 → `1⑥1` — identical leading digit
  sequences to the continuous form, just without magnitude notation or
  trailing-zero padding, exactly as expected since both paths share the
  same carry logic.

These four were chosen originally because the source page calls out 9,
18/19, and 73 specifically as the non-obvious cases (the ones where
naive rounding gets the wrong magnitude), so passing all four on both
paths — and against the reference implementation directly — is the bar
for correctness before wiring this into anything user-facing. The
whole-count path was additionally checked against the source page's own
0-to-100 counting sequence (spot-checked 0 through 30), confirming the
dozens-place digit flips to 1 starting at 7 and to 2 starting at 19,
matching the page's description exactly.

The module exposes two functions that matter for integration:

    janus_notation(value, sig_digits=6, trim_trailing_zeros=False) -> str

Use for continuous, Chronit-based values: Orit, Solit, any fractional
Chronit count. `value` is any real number — the function handles
magnitude placement and digit balancing internally, and returns the
full `<magnitude>*<mantissa>` string. Default precision is 6 significant
digits, matching the resolution the temporal dashboard actually runs at
(it updates every 0.000001 Chronit, roughly a 0.643-second visual
"heartbeat" tick, and needs that much precision to show the correlation
meaningfully). `trim_trailing_zeros` defaults to `False`, matching
`jalibrary.js`'s own behavior: when a caller asks for a specific
`sig_digits`, they get exactly that many mantissa digits, genuine zeros
included, since trimming would silently return less precision than
requested. Pass `trim_trailing_zeros=True` for the reference library's
separate "compact/auto" behavior instead.

    janus_integer(n) -> str

Use for whole counts: Annit, Dattit, or any other plain integer. `n` is
any integer (positive, negative, or zero) — the function converts it
exactly, with no windowing and no magnitude notation of any kind.

## Integration point

In `civil_clock_genmon.py`, every field currently formatted as plain
decimal should switch to the matching function above: Orit and Solit
(wherever Solit appears in the panel or tooltip) go through
`janus_notation()`, Annit and Dattit go through `janus_integer()`. This
is a full swap, not a partial one — every number the panel displays
should be in Janus notation, since that's how the Civilization itself
writes numbers, not a special case reserved for one field. A single
space separates every unit abbreviation from its value (`An 0`, not
`An0`), per Chris's direct instruction — this applies throughout the
panel and tooltip, not just to one field.

The module's own default of 6 significant digits reflects the temporal
dashboard's precision need, not a display convenience, so the Xfce
panel — which only wants whole-Orit-level glance resolution — should
pass a lower `sig_digits` explicitly at its own call site rather than
relying on the module default. `civil_clock_genmon.py` should call
`janus_notation(orit_value, sig_digits=2)` for panel brevity; the
temporal dashboard should call `janus_notation(orit_value)` with no
override and take the full 6-digit default. `janus_integer()` calls
need no such tuning, since they render exactly however many digits the
count actually has, with no precision knob to set.

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
  any Chronit-fraction value in decimal, or in the earlier, now-superseded
  magnitude-notation format (outside the genmon panel), are a separate
  follow-up, not covered by this spec. A note has been left on the
  bulletin board flagging that follow-up.

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
significant digits (later raised to 6 — see the correction below) is
more precision than a glance-level clock display wants, since it will
legitimately show the ⑥-carry behavior for any Orit value with a
nonzero fractional Chronit remainder — which is most of the time, since
Orit is constantly advancing. For `civil_clock_genmon.py`, call
`janus_notation(orit_value, sig_digits=2)` explicitly rather than
relying on the module default, so the panel shows a clean whole-Orit
reading rather than a jarring carry-heavy one. This is a call-site
choice, not a module default change.

## Second correction: format verified against the actual reference implementation

The prior two revisions of this spec were built from reasoning about the
Janus numbers page's worked examples, without a reference implementation
to check against. Chris subsequently provided the real one:
`jalibrary.js`, the Musa Academy's own JavaScript library for Janus
numbers. Checking against it surfaced two real format mistakes and
resolved one open question:

**Mantissa/magnitude order was backwards.** `janusReal()` in the
reference library returns `raise(exponent) + Break + mantissa` --
magnitude first, then a separator, then the mantissa. Earlier drafts of
this module put the magnitude marker *after* the mantissa (`3⑥.1③^1`
style), which is the reverse of the actual convention. This is now
corrected: `janus_notation()` renders `<magnitude>*<mantissa>`, e.g.
`1*3⑥1③④④`, with `*` used as the plain-Unicode stand-in for the Musa
Break character. This also matches the Latinized convention visible on
the Janus social units page ("So 2*11538": magnitude 2, mantissa 11538).

**Trailing zeros should NOT be trimmed by default when an explicit
precision is requested.** An earlier draft trimmed trailing zero digits
from the mantissa on the theory that they were visual noise. Checking
`janusReal()`'s own source shows it only trims trailing zeros in its
"auto" mode (an unspecified or zero place count, meaning "up to 6
places, but don't pad with meaningless zeros"). When a caller passes an
explicit place count, the reference always returns exactly that many
mantissa digits, genuine zeros included -- trimming would silently
return less precision than requested. `janus_notation()` now defaults
`trim_trailing_zeros=False` to match; the compact/auto behavior is still
available by passing `trim_trailing_zeros=True` explicitly.

**Negative magnitude values do not get a separate sign marker on the
magnitude.** This resolves Chris's open question about how negative
values render. The magnitude itself is just a signed Janus integer
(rendered via `janus_integer()`, which already handles negative values
via the ordinary balanced-digit carry logic) -- there's no separate `-`
prefix or alternate marker; a magnitude of -3 simply renders as whatever
`janus_integer(-3)` produces. Verified: `janus_notation(0.0006)` gives
`-3*1054⑤1`, matching the reference library's exponent computation for
that value exactly.

**The earlier "regression" wasn't actually a bug in the carry logic
itself** -- cross-checking against `janusReal()` directly confirms that
30.0 and 30.06 legitimately produce different mantissas at high
precision (6 places: `3,-6,0,0,0,0` vs `3,-6,1,-3,-4,...`) because at
that resolution there really is more of 30.06 to show, and identical
mantissas at low precision (2 places: both `2,6`) because at that
resolution the difference is invisible. The fix made in the prior
revision -- scoping the rule-of-six carry decision to only the digits
inside the requested significant-digit window -- was correct and is
retained unchanged; what was wrong was an assumption layered on top of
it (that trimming trailing zeros was the right default), which is now
also corrected.

## Format changes from this correction (apply to `civil_clock_genmon.py`)

1. **Magnitude before mantissa**, separated by `*`: `janus_notation()`
   now returns e.g. `1*3⑥1③④④`, not the old `3⑥.1③^1`-style output.
   Any code consuming this module's output needs to be updated for the
   new format, not just re-pointed at a patched function.
2. **Space between unit abbreviation and number.** Per Chris's direct
   instruction, `An0` becomes `An 0`, `Da223` becomes `Da 2⑤⑤`, `Or...`
   becomes `Or ...`. This applies throughout the panel and tooltip, not
   just to one field.
3. **Whole counts (Annit, Dattit) use `janus_integer()` with no
   magnitude notation at all** -- not even a `*0` or similar placeholder.
   Magnitude notation exists to signal scale for numbers too large or
   small to write digit-by-digit; a count like a day-index has no such
   need, and per Chris's direct instruction should render as plain
   Janus digits only.
4. **Default precision raised to 6 significant digits** for
   `janus_notation()`, up from 4. This matches the actual precision the
   temporal dashboard operates at (it updates every 0.000001 Chronit,
   roughly a 0.643-second visual "heartbeat" tick, and needs enough
   digits to show that resolution meaningfully). The Xfce panel, which
   only needs whole-Orit-level glance precision, should pass a lower
   `sig_digits` explicitly at its own call site (2 was the earlier
   suggestion) rather than relying on the module default -- the module
   default now reflects the project's most demanding precision need,
   not a display convenience, so every call site that wants something
   coarser must say so explicitly.

Updated panel line, all four values in corrected Janus notation, unit
abbreviations space-separated from their values, Orit at the new default
precision:

    An 0 Da 2⑤⑤ Or 1*3⑥1③④④0

(Six mantissa digits shown for Orit here since that's the module
default; the Xfce panel specifically should still request a lower
`sig_digits` explicitly, e.g. `janus_notation(orit_value, sig_digits=2)`,
to keep panel text short -- the dashboard, which needs the full
six-digit heartbeat-correlated precision, should call with no
`sig_digits` override and take the default.)

All example digit sequences above were verified against `jalibrary.js`
directly (attached alongside this spec) by running its own `janusReal()`
and `janusInt()` functions under Node and comparing output digit-by-digit
against this module's Python output, not by re-deriving the convention
from the numbers page alone.
