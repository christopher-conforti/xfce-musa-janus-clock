#!/usr/bin/env python3
"""
Janus (balanced dozenal) notation in plain Unicode -- no Musa font needed,
since the negative-digit glyphs (①-⑥) are ordinary circled-digit
characters (U+2460-U+2465), not part of the Musa script itself. Suitable
anywhere UTF-8 renders correctly, including an Xfce genmon panel.

Balanced dozenal: base 12, digits run -6..6 instead of 0..9, written with
circled numerals for the negative half exactly as the source material
does. This is how the Civilization writes every number, not just
continuous measurements -- so this module covers two distinct cases:

  - Continuous, Chronit-based values (Orit, Solit, any fractional
    Chronit count) use janus_notation(), which windows to a chosen
    number of significant digits and appends a ^N magnitude marker, the
    same role e+N plays in decimal scientific notation.
  - Whole-count values (Annit, Dattit, or any other plain integer) use
    janus_integer(), which converts EXACTLY -- no truncation, no
    significant-digit budget -- and has no decimal point or magnitude
    marker, since a count has no fractional part and no need to signal
    scale. Both paths share the same underlying rule-of-six carry logic;
    they differ only in whether the input is a continuous measurement
    that needs windowing, or an exact count that doesn't.
"""
import math

DIGIT_CHARS = "0123456" # 0..6, negative digits get a backtick prefix

def to_balanced_dozenal_digits(value, sig_digits=4):
    """
    Convert a positive float to a list of balanced-dozenal digits
    (-6..6) plus an integer magnitude, such that
        value == sum(d * 12**(magnitude - i) for i, d in enumerate(digits))
    approximately, to sig_digits of precision.
    Returns (digits, magnitude).
    """
    if value == 0:
        return [0] * sig_digits, 0

    sign = 1
    if value < 0:
        sign = -1
        value = -value

    # Work in a fixed-point integer domain to avoid float drift: scale
    # value up so the digits we actually intend to show land on integer
    # boundaries, round to the nearest integer at that scale, then do
    # exact integer balanced-dozenal digit extraction across exactly
    # sig_digits places -- no more. The rule-of-six carry decision must
    # be made only against digits inside this window: whether a visible
    # 6 carries depends on whether anything nonzero follows it *within
    # what's being displayed*, not against the true infinite-precision
    # tail of the value, which is almost never all zero and would make
    # nearly every 6 carry regardless of how far away the nonzero part
    # sits. This matters concretely: 30.06 and 30.0 both round to the
    # same 4 significant digits, and both must therefore make the same
    # carry decision and print the same leading digit -- the invisible
    # difference in their tails past the display window is not allowed
    # to change what's shown.
    est_magnitude = math.floor(math.log(value, 12)) if value >= 1 else math.floor(math.log(value, 12))
    scale_pow = est_magnitude - sig_digits + 1
    scaled = round(value / (12.0 ** scale_pow))

    # Standard (unbalanced) base-12 digit extraction of `scaled`, most
    # significant first. Because `scaled` was rounded at exactly the
    # sig_digits boundary, this already reflects the rounding decision
    # for anything past the window -- there is no separate "extra"
    # precision hiding in these digits.
    raw_digits = []
    n = int(scaled)
    if n == 0:
        raw_digits = [0]
    while n > 0:
        raw_digits.append(n % 12)
        n //= 12
    raw_digits.reverse()

    # Convert unbalanced (0..11) digits to balanced (-6..6), evaluating
    # the rule of six against only these visible digits. Digits 7-11
    # always carry (digit-12, +1 to the left) since they have no balanced
    # representative otherwise. Digit 6 carries (becomes -6, +1 left) if
    # a nonzero digit follows it anywhere WITHIN THIS WINDOW; it stays
    # plain +6 if it's the final nonzero digit in the window, even if the
    # true value has more precision beyond what's being shown. Resolved
    # right-to-left, since "is anything nonzero after me" depends on
    # digits to my right, and a resolved digit can itself change what's
    # "after" the digit to its left.
    raw_digits = [0] + raw_digits  # headroom for a carry into a new leading digit
    anything_nonzero_after = False
    for i in range(len(raw_digits) - 1, 0, -1):
        d = raw_digits[i]
        carries = d > 6 or (d == 6 and anything_nonzero_after)
        if carries:
            raw_digits[i] = d - 12
            raw_digits[i - 1] += 1
        if raw_digits[i] != 0:
            anything_nonzero_after = True
    balanced = raw_digits

    # magnitude of the most significant digit, in powers of 12, relative
    # to the units place implied by scale_pow
    top_place = scale_pow + len(balanced) - 1
    # trim leading zero digits to find the true leading digit / magnitude
    first_nonzero = 0
    while first_nonzero < len(balanced) - 1 and balanced[first_nonzero] == 0:
        first_nonzero += 1
        top_place -= 1
    balanced = balanced[first_nonzero:]

    digits = balanced[:sig_digits]
    while len(digits) < sig_digits:
        digits.append(0)
    magnitude = top_place

    return digits, magnitude, sign

def to_balanced_dozenal_integer_digits(n):
    """
    Convert a non-negative integer to its EXACT balanced-dozenal digit
    representation -- no truncation, no significant-digit budget, no
    magnitude estimate. This is the right conversion for whole-count
    values (Annit, Dattit, any plain integer), as opposed to
    to_balanced_dozenal_digits() above, which is built for continuous
    Chronit-based measurements (Orit, Solit) and deliberately windows
    down to a chosen number of significant digits for magnitude notation.

    Returns a list of digits (-6..6), most significant first, with no
    leading zero (except the single digit [0] for n == 0).
    """
    if n < 0:
        raise ValueError("expects a non-negative integer; handle sign separately")
    if n == 0:
        return [0]

    # Standard (unbalanced) base-12 digit extraction, most significant
    # first -- exact, since n is an integer and 12 is an integer base.
    raw_digits = []
    m = n
    while m > 0:
        raw_digits.append(m % 12)
        m //= 12
    raw_digits.reverse()

    # Same rule-of-six carry logic as the continuous-value path: digit 6
    # carries (becomes -6, +1 to the left) if anything nonzero follows it;
    # digits 7-11 always carry. Headroom digit up front absorbs a carry
    # that overflows into a new leading place.
    raw_digits = [0] + raw_digits
    anything_nonzero_after = False
    for i in range(len(raw_digits) - 1, 0, -1):
        d = raw_digits[i]
        carries = d > 6 or (d == 6 and anything_nonzero_after)
        if carries:
            raw_digits[i] = d - 12
            raw_digits[i - 1] += 1
        if raw_digits[i] != 0:
            anything_nonzero_after = True

    # trim a leading zero left over from the headroom digit, unless the
    # whole value really is zero
    while len(raw_digits) > 1 and raw_digits[0] == 0:
        raw_digits.pop(0)

    return raw_digits



CIRCLED_DIGITS = {1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤", 6: "⑥"}

def render_digit(d):
    if d < 0:
        return CIRCLED_DIGITS[-d]
    return DIGIT_CHARS[d]

def janus_integer(n):
    """
    Render a whole number (Annit, Dattit, or any other plain count) as
    exact Janus balanced-dozenal digits -- circled numerals for the
    negative half, no decimal point, no magnitude marker, since a count
    has no fractional part and no need to signal scale the way a
    continuous measurement does. E.g. janus_integer(19) -> '2⑤'.
    """
    sign = "-" if n < 0 else ""
    digits = to_balanced_dozenal_integer_digits(abs(n))
    return sign + "".join(render_digit(d) for d in digits)


def janus_notation(value, sig_digits=4, show_magnitude=True, trim_trailing_zeros=True):
    """
    Render a positive real number in Janus balanced-dozenal notation:
    digits 0-6 print plain, a negative digit prints as its circled
    numeral (① means the balanced digit -1), a decimal point sits after
    the units-place digit if the magnitude is within the visible digit
    window, and a trailing ^N marks the magnitude the way e+N marks a
    decimal exponent.
    """
    if value == 0:
        return "0"

    digits, magnitude, sign = to_balanced_dozenal_digits(value, sig_digits)

    if trim_trailing_zeros:
        while len(digits) > 1 and digits[-1] == 0 and (magnitude - (len(digits) - 1)) < 0:
            digits = digits[:-1]

    out = "-" if sign < 0 else ""
    for i, d in enumerate(digits):
        out += render_digit(d)
        if magnitude - i == 0 and i != len(digits) - 1:
            out += "."
    if show_magnitude:
        out += f"^{magnitude}"
    return out

if __name__ == "__main__":
    import sys
    print("Continuous values (magnitude notation, default 4 sig digits):")
    tests = [30.06, 0.0006, 1.5542e-6, 900, 9, 73, 18, 19]
    for t in tests:
        print(f"{t!r:>14} -> {janus_notation(t)}")
    print()
    print("Whole-count values (exact digits, no magnitude marker):")
    int_tests = [0, 7, 9, 18, 19, 73, 223]
    for t in int_tests:
        print(f"{t!r:>14} -> {janus_integer(t)}")
    print()
    print("Precision-window regression check: same value, its true fractional")
    print("tail must not silently change the leading digit once that tail")
    print("falls outside the requested significant-digit window.")
    print(f"  30.0  at 2 sig digits -> {janus_notation(30.0, sig_digits=2)}")
    print(f"  30.06 at 2 sig digits -> {janus_notation(30.06, sig_digits=2)}  (must match the line above)")
    print(f"  30.06 at 4 sig digits -> {janus_notation(30.06, sig_digits=4)}  (more precision, legitimately different)")
    print()
    print("Panel line -- Orit rendered at reduced (2 sig digit) precision,")
    print("appropriate for a glance-level clock display rather than the")
    print("module's own full-precision default:")
    orit_now = 30.06
    annit_now = 0
    dattit_now = 223
    print(f"An{janus_integer(annit_now)} Da{janus_integer(dattit_now)} Or{janus_notation(orit_now, sig_digits=2)}")
