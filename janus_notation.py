#!/usr/bin/env python3
"""
Janus (balanced dozenal) notation in plain Unicode -- no Musa font needed,
since the negative-digit glyphs (①-⑥) are ordinary circled-digit
characters (U+2460-U+2465), not part of the Musa script itself. Suitable
anywhere UTF-8 renders correctly, including an Xfce genmon panel.

Balanced dozenal: base 12, digits run -6..6 instead of 0..9, written with
circled numerals for the negative half exactly as the source material
does. Magnitude notation uses ^ the way decimal scientific notation uses
e, matching the convention Janus itself borrows on the numbers page
(Janus doesn't need a separate reciprocal sign -- a negative first digit
already means "shift the point the other way").

This does NOT attempt full arbitrary-precision balanced-dozenal conversion
generally -- it's scoped to what a Chronit-based clock display needs:
a positive real number (an Orit or a fractional Chronit count), converted
to balanced dozenal with a chosen number of significant digits, using
Janus's round-at-the-midpoint rule rather than decimal's round only at
the power boundary.
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
    # value up by a healthy number of extra dozenal places, round to the
    # nearest integer at that fine scale, then do exact integer balanced-
    # dozenal digit extraction (which is where the actual carry/complement
    # logic needs to be exact, not the coarse magnitude estimate).
    extra = 6
    total_digits = sig_digits + extra
    # crude magnitude estimate just to size the fixed-point scale; exact
    # magnitude placement falls out naturally from the leading nonzero
    # digit after extraction, same as decimal scientific notation.
    est_magnitude = math.floor(math.log(value, 12)) if value >= 1 else math.floor(math.log(value, 12))
    scale_pow = est_magnitude - total_digits + 1
    scaled = round(value / (12.0 ** scale_pow))

    # Standard (unbalanced) base-12 digit extraction of `scaled`, most
    # significant first.
    raw_digits = []
    n = int(scaled)
    if n == 0:
        raw_digits = [0]
    while n > 0:
        raw_digits.append(n % 12)
        n //= 12
    raw_digits.reverse()

    # Convert unbalanced (0..11) digits to balanced (-6..6). Digits 7-11
    # always carry (digit-12, +1 to the left) since they have no balanced
    # representative otherwise. Digit 6 is the ambiguous "rule of six"
    # case described on the numbers page: it carries (becomes -6, +1 left)
    # if it is NOT the final significant digit -- i.e. something nonzero
    # follows it -- and stays plain +6 if it IS final (nothing but zeros
    # after it). This must be resolved right-to-left, since "is anything
    # nonzero after me" depends on digits to my right, and a resolved
    # digit can itself change what's "after" the digit to its left.
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

CIRCLED_DIGITS = {1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤", 6: "⑥"}

def render_digit(d):
    if d < 0:
        return CIRCLED_DIGITS[-d]
    return DIGIT_CHARS[d]

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
    tests = [30.06, 0.0006, 1.5542e-6, 900, 9, 73, 18, 19]
    for t in tests:
        print(f"{t!r:>14} -> {janus_notation(t)}")
