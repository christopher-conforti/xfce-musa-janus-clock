#!/usr/bin/env python3
"""
Civil Clock -- a genmon script for the Xfce panel's Generic Monitor plugin.

Displays the Civilization's own time units instead of host-nation Gregorian
date/time: Annit (whole years), Hemerit (the zodiac/element/Olympian civil
calendar day), Solit (time since true local solar noon), and Orit (raw
elapsed Chronits, available but no longer the default headline figure since
a bare Orit count isn't a useful thing for a human to read at a glance).

EPOCH is the Dec 21, 2025 solstice, 15:02:51.231129 UTC -- Orit/Dattit/Annit
zero -- carried over verbatim from the janus-units skill rather than
re-derived. CHRONIT_SECONDS is likewise the exact constant from that skill.

Annit, Hemerit, and Solit all require real solstice/equinox/solar-transit
data, so all three depend on the `ephem` package. If ephem isn't installed,
the script still shows Dattit and Orit (pure arithmetic) and fills in
placeholders for the rest rather than crashing. Install with:
    pip install ephem --break-system-packages
(or whatever your distro prefers for externally-managed environments).

HONEST LIMITATION ON THE HEMERIT CALENDAR: the civil calendar's four
holiday blocks (Year End, Easter, Midyear, Harfest) are pinned to real
solstice/equinox instants, but each season's three 30-day months are a
fixed 90-day block laid down right after the holiday. Real astronomical
seasons don't all divide evenly into exactly "90 days of months + a fixed
holiday count," so in a season that runs unusually long or short relative
to that budget, the last day or two near a season boundary gets clamped
into the final weekday rather than spilling into a 13th month. This
matches how the source calendar is specified (fixed 30-day months, holiday
counts pinned to a leap rule rather than to the day-by-day real gap), but
it means the month/week/weekday figures right at the edge of a season are
an approximation, not a live astronomical reading the way the holiday
boundaries themselves are.

FORMAT STRINGS: --format controls the panel text, --tooltip-format controls
the hover tooltip. Both use Python str.format() with these tokens:

    {annit}         Annit in exact Janus balanced-dozenal notation, or ? if
                    ephem is unavailable (see janus_notation.py)
    {annit_short}   "An <janus notation>" (the official abbreviation, per
                    musa.bet)
    {annit_full}    "<janus notation> Annit"
    {dattit}        Dattit (days since epoch) in exact Janus notation
    {dattit_short}  "Da <janus notation>"
    {dattit_full}   "<janus notation> Dattit"
    {hemerit}       raw Hemerit acronym, e.g. "Aquita" (month stem + week's
                    element vowel + weekday's consonant + this specific
                    day's own element vowel -- see musa.bet/social.htm)
    {hemerit_short} "He Aquita"
    {hemerit_full}  "Aquita Hemerit"
    {orit}          Orit in Janus balanced-dozenal notation (see janus_notation.py)
    {orit_short}    "Or <janus notation>"
    {orit_full}     "<janus notation> Orit"
    {holiday}       holiday name (with day count if multi-day), or "" if
                    today isn't a holiday
    {month}         zodiac month name, or "" during a holiday
    {week}          element week name ("Stoneweek" etc.), or ""
    {weekday}       Olympian day name ("Apollo" etc.), or ""
    {day_of_month}  1-30, or "" during a holiday (not part of the formal
                    Hemerit unit itself -- musa.bet's calendar is entirely
                    name-based -- just a convenience number)
    {day_element}   the element this specific day counts as within its
                    week's rotation ("Fire", "Water", etc.), or "" during
                    a holiday -- this is where {hemerit}'s final vowel and
                    {date_label}'s "-day" prefix both come from
    {date_label}    holiday name, or musa.bet's own spoken phrasing:
                    "Dayelementday, Weekday of Week of Month", e.g.
                    "Fireday, Aphrodite of Earthweek of Leo"
    {solit}         signed Solit in Janus balanced-dozenal notation
    {solit_short}   "So+ <janus notation>" or "So- <janus notation>"
    {solit_full}    "+<janus notation> Solit" or "-<janus notation> Solit"

Short forms use the unit's official abbreviation (An, Da, He, Or, So) the
way musa.bet itself writes them. Full forms spell the unit name out, with
the number leading the way you'd say it aloud ("30 Dattit", not "Dattit
30") -- except Hemerit, which isn't a number at all, so its full form is
just the acronym followed by the unit name. {date_label} is a composed
calendar sentence rather than a single unit reading, so it doesn't have
its own abbreviated form.

Example:
    python3 civil_clock_genmon.py --format "{annit_full} - {date_label}"
    python3 civil_clock_genmon.py --format "{month} {day_of_month}" \\
        --tooltip-format "{date_label}\\n{solit_full}\\n{orit_full}"

Location matters for Solit specifically (true local solar noon depends on
longitude, and slightly on latitude). --lat and --lon default to
Philadelphia; pass your own coordinates for an accurate reading elsewhere.
"""

import argparse
from datetime import datetime, timezone, timedelta

from janus_notation import janus_notation, janus_integer

EPOCH = datetime(2025, 12, 21, 15, 2, 51, 231129, tzinfo=timezone.utc)
CHRONIT_SECONDS = 643391.816709006

# Reduced from the module's own default of 4: at 4 sig digits, a
# constantly-advancing fractional Chronit remainder makes the rule-of-six
# carry (e.g. "3⑥.1③^1") the common case rather than the exception, which
# is more precision than a glance-level clock display wants. Applies to
# both continuous values Orit and Solit. See janus_clock_notation_spec.md's
# rule-of-six carry window correction.
CONTINUOUS_SIG_DIGITS = 2

DEFAULT_LAT = 39.9526
DEFAULT_LON = -75.1652

MONTHS = ["Capricorn", "Aquarius", "Pisces", "Aries", "Taurus", "Gemini",
          "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius"]
WEEKS = ["Stoneweek", "Earthweek", "Waterweek", "Airweek", "Fireweek"]
WEEK_ELEMENTS = ["Stone", "Earth", "Water", "Air", "Fire"]  # same order as WEEKS
DAYS = ["Apollo", "Artemis", "Ares", "Hermes", "Athena", "Aphrodite"]

# The combining stem each month uses when building a Hemerit acronym. Mostly
# the bolded root musa.bet prints next to each month name, but not always:
# Leo becomes "Ley" (not "Le") once a vowel follows it, and Virgo drops its
# "o" entirely rather than double up on a vowel, per the worked dual
# calendar table on https://musa.bet/social.htm.
MONTH_STEMS = {
    "Capricorn": "Capr", "Aquarius": "Aqu", "Pisces": "Pisc",
    "Aries": "Ar", "Taurus": "Taur", "Gemini": "Gem",
    "Cancer": "Can", "Leo": "Ley", "Virgo": "Virg",
    "Libra": "Libr", "Scorpio": "Scorp", "Sagittarius": "Sagitt",
}

# Each of the five elements gets one vowel, used both for the week (right
# after the month stem) and for a day's individually-assigned element
# (at the very end of the acronym). Derived directly from musa.bet's worked
# table rather than guessed: Water=a, Air=e, Fire=i, Stone=u, Earth=o.
ELEMENT_VOWEL = {"Water": "a", "Air": "e", "Fire": "i", "Stone": "u", "Earth": "o"}

# One consonant per Olympian day, per musa.bet's own bolded letters
# (A-p-ollo, Ar-t-emis, A-r-es, Her-m-es, A-th-ena, A-ph-rodite -> f).
DAY_CONSONANT = {"Apollo": "p", "Artemis": "t", "Ares": "r",
                 "Hermes": "m", "Athena": "th", "Aphrodite": "f"}

# For a given week and a given person's weekday slot within it, which
# element that specific day counts as (this is what actually determines
# who gets that day off, and it's also the source of the acronym's final
# vowel). Table transcribed directly from musa.bet's schedule; each row is
# in DAYS order (Apollo, Artemis, Ares, Hermes, Athena, Aphrodite).
DAY_ELEMENT_TABLE = {
    "Stone": ["Water", "Air", "Earth", "Fire", "Water", "Air"],
    "Earth": ["Air", "Fire", "Water", "Stone", "Air", "Fire"],
    "Water": ["Fire", "Stone", "Air", "Earth", "Fire", "Stone"],
    "Air":   ["Stone", "Earth", "Fire", "Water", "Stone", "Earth"],
    "Fire":  ["Earth", "Water", "Stone", "Air", "Earth", "Water"],
}

# The four holidays are their own "month" and "week" (Holiweek), so their
# Hemerit codes aren't generated by the month/week/day formula above --
# they're fixed labels, transcribed directly from musa.bet's dual calendar.
HOLIDAY_HEMERIT = {
    ("Year End", 1): "Holithi",
    ("Year End", 2): "Holifi",
    ("Easter", 1): "Holipu",
    ("Midyear", 1): "Holito",
    ("Midyear", 2): "Holira",
    ("Harfest", 1): "Holime",
}

try:
    import ephem
    HAVE_EPHEM = True
except ImportError:
    HAVE_EPHEM = False


def _to_utc(ephem_date):
    return ephem_date.datetime().replace(tzinfo=timezone.utc)


def equinox_solstice_year(gregorian_year):
    """March equinox, June solstice, September equinox, December solstice
    of the given Gregorian year, in that chronological order."""
    d = ephem.Date(f'{gregorian_year}/1/1')
    mar_eq = ephem.next_equinox(d)
    jun_sol = ephem.next_solstice(mar_eq)
    sep_eq = ephem.next_equinox(jun_sol)
    dec_sol = ephem.next_solstice(sep_eq)
    return _to_utc(mar_eq), _to_utc(jun_sol), _to_utc(sep_eq), _to_utc(dec_sol)


def year_boundaries(dt):
    """Returns (dec_sol_prev, mar_eq, jun_sol, sep_eq, dec_sol_next) such
    that dec_sol_prev <= dt < dec_sol_next."""
    y = dt.year
    mar_eq, jun_sol, sep_eq, dec_sol = equinox_solstice_year(y)
    if dec_sol <= dt:
        mar_eq2, jun_sol2, sep_eq2, dec_sol_next = equinox_solstice_year(y + 1)
        return dec_sol, mar_eq2, jun_sol2, sep_eq2, dec_sol_next
    else:
        _, _, _, dec_sol_prev = equinox_solstice_year(y - 1)
        return dec_sol_prev, mar_eq, jun_sol, sep_eq, dec_sol


def year_end_holiday_days(annit_year):
    """Second Year End day every fourth year, except years divisible by 128."""
    if annit_year % 4 == 0 and annit_year % 128 != 0:
        return 2
    return 1


def hemerit_acronym(month, week_name, weekday):
    """Builds the real Hemerit acronym: month stem + this week's element
    vowel + this weekday's consonant + the element vowel this specific
    (week, weekday) slot counts as. Verified against musa.bet's own
    worked example: Aquarius + Fireweek + Artemis = "Aquita", which is
    exactly what this produces."""
    week_index = WEEKS.index(week_name)
    week_element = WEEK_ELEMENTS[week_index]
    day_index = DAYS.index(weekday)
    day_element = DAY_ELEMENT_TABLE[week_element][day_index]

    stem = MONTH_STEMS[month]
    if month == "Aquarius" and week_name == "Stoneweek":
        stem = "Aq\u00fc"  # Aqu + u would double the letter; musa.bet writes Aq\u00fc + u

    acronym = stem + ELEMENT_VOWEL[week_element] + DAY_CONSONANT[weekday] + ELEMENT_VOWEL[day_element]
    return acronym, day_element


def hemerit_info(dt):
    """Returns a dict describing the civil calendar position of dt:
    annit, the Hemerit acronym, holiday (or None), and month/week/weekday/
    day_of_month/day_element (or None during a holiday)."""
    dec_sol_prev, mar_eq, jun_sol, sep_eq, dec_sol_next = year_boundaries(dt)
    annit = dec_sol_prev.year - EPOCH.year

    segments = [
        (dec_sol_prev, mar_eq, "Year End", year_end_holiday_days(annit),
         [MONTHS[0], MONTHS[1], MONTHS[2]]),
        (mar_eq, jun_sol, "Easter", 1, [MONTHS[3], MONTHS[4], MONTHS[5]]),
        (jun_sol, sep_eq, "Midyear", 2, [MONTHS[6], MONTHS[7], MONTHS[8]]),
        (sep_eq, dec_sol_next, "Harfest", 1, [MONTHS[9], MONTHS[10], MONTHS[11]]),
    ]

    for start, end, holiday_name, holiday_days, season_months in segments:
        if start <= dt < end:
            day_index = int((dt - start).total_seconds() // 86400)
            if day_index < holiday_days:
                which_day = day_index + 1  # 1 or 2
                hemerit = HOLIDAY_HEMERIT[(holiday_name, which_day)]
                label = holiday_name
                if holiday_days > 1:
                    label += f" (Day {which_day} of {holiday_days})"
                return {"annit": annit, "hemerit": hemerit, "holiday": label,
                        "month": None, "week": None, "weekday": None,
                        "day_of_month": None, "day_element": None}
            month_day_index = min(day_index - holiday_days, 89)  # clamp; see module docstring
            month = season_months[month_day_index // 30]
            week = WEEKS[(month_day_index % 30) // 6]
            weekday = DAYS[month_day_index % 6]
            day_of_month = (month_day_index % 30) + 1
            hemerit, day_element = hemerit_acronym(month, week, weekday)
            return {"annit": annit, "hemerit": hemerit, "holiday": None,
                    "month": month, "week": week, "weekday": weekday,
                    "day_of_month": day_of_month, "day_element": day_element}

    raise RuntimeError("date fell outside all four season segments -- this is a bug")


def solit_for(dt, lat, lon):
    """Elapsed Chronits since true local solar noon; negative in the morning."""
    obs = ephem.Observer()
    obs.lat = str(lat)
    obs.lon = str(lon)
    obs.date = dt.strftime("%Y/%m/%d %H:%M:%S")
    sun = ephem.Sun()
    prev_transit = _to_utc(obs.previous_transit(sun))
    next_transit = _to_utc(obs.next_transit(sun))
    since_prev = (dt - prev_transit).total_seconds()
    until_next = (next_transit - dt).total_seconds()
    if since_prev <= until_next:
        seconds = since_prev
    else:
        seconds = -until_next
    return seconds / CHRONIT_SECONDS


def build_tokens(now, lat, lon):
    dattit = int((now - EPOCH).days)
    orit = (now - EPOCH).total_seconds() / CHRONIT_SECONDS

    dattit_str = janus_integer(dattit)
    orit_str = janus_notation(orit, sig_digits=CONTINUOUS_SIG_DIGITS)

    tokens = {
        "dattit": dattit_str,
        "dattit_short": f"Da {dattit_str}",
        "dattit_full": f"{dattit_str} Dattit",
        "orit": orit_str,
        "orit_short": f"Or {orit_str}",
        "orit_full": f"{orit_str} Orit",
        "annit": "?",
        "annit_short": "An ?",
        "annit_full": "? Annit",
        "hemerit": "?",
        "hemerit_short": "He ?",
        "hemerit_full": "? Hemerit",
        "holiday": "",
        "month": "",
        "week": "",
        "weekday": "",
        "day_of_month": "",
        "day_element": "",
        "date_label": "(needs ephem)",
        "solit": "?",
        "solit_short": "So ?",
        "solit_full": "? Solit",
    }

    if HAVE_EPHEM:
        info = hemerit_info(now)
        annit_str = janus_integer(info["annit"])
        tokens["annit"] = annit_str
        tokens["annit_short"] = f"An {annit_str}"
        tokens["annit_full"] = f"{annit_str} Annit"
        tokens["hemerit"] = info["hemerit"]
        tokens["hemerit_short"] = f"He {info['hemerit']}"
        tokens["hemerit_full"] = f"{info['hemerit']} Hemerit"
        if info["holiday"]:
            tokens["holiday"] = info["holiday"]
            tokens["date_label"] = info["holiday"]
        else:
            tokens["month"] = info["month"]
            tokens["week"] = info["week"]
            tokens["weekday"] = info["weekday"]
            tokens["day_of_month"] = info["day_of_month"]
            tokens["day_element"] = info["day_element"]
            tokens["date_label"] = (
                f"{info['day_element']}day, {info['weekday']} of "
                f"{info['week']} of {info['month']}"
            )

        solit = solit_for(now, lat, lon)
        sign = "+" if solit >= 0 else "-"
        solit_janus = janus_notation(abs(solit), sig_digits=CONTINUOUS_SIG_DIGITS)
        solit_str = f"{sign}{solit_janus}"
        tokens["solit"] = solit_str
        tokens["solit_short"] = f"So{sign} {solit_janus}"
        tokens["solit_full"] = f"{solit_str} Solit"

    return tokens


def render(fmt, tokens):
    try:
        return fmt.format(**tokens)
    except KeyError as e:
        valid = ", ".join(sorted(tokens.keys()))
        return f"[format error: unknown token {e}; valid tokens are: {valid}]"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--format", default="{hemerit_short}, {annit_short}, {solit_short}",
                         help="panel text format string")
    parser.add_argument("--tooltip-format",
                         default="{date_label}\n{annit_full}  ({dattit_full})\n"
                                 "{solit_full}\n{orit_full}",
                         help="tooltip format string ('\\n' becomes a real line break)")
    parser.add_argument("--lat", type=float, default=DEFAULT_LAT,
                         help=f"latitude for Solit (default {DEFAULT_LAT}, Philadelphia)")
    parser.add_argument("--lon", type=float, default=DEFAULT_LON,
                         help=f"longitude for Solit (default {DEFAULT_LON}, Philadelphia)")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    tokens = build_tokens(now, args.lat, args.lon)

    label = render(args.format, tokens)
    tooltip_text = render(args.tooltip_format, tokens)
    if not HAVE_EPHEM:
        tooltip_text += "\n(install the ephem package for Annit, Hemerit, and Solit)"
    tooltip = tooltip_text.replace("\n", "&#10;")

    print("<txt>" + label + "</txt>")
    print("<tool>" + tooltip + "</tool>")


if __name__ == "__main__":
    main()
