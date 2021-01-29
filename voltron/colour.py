ESCAPES = {
    # reset
    'reset':        0,

    # colours
    'grey':         30,
    'red':          31,
    'green':        32,
    'yellow':       33,
    'blue':         34,
    'magenta':      35,
    'cyan':         36,
    'white':        37,

    # background
    'b_grey':       40,
    'b_red':        41,
    'b_green':      42,
    'b_yellow':     43,
    'b_blue':       44,
    'b_magenta':    45,
    'b_cyan':       46,
    'b_white':      47,

    # attributes
    'a_bold':       1,
    'a_dark':       2,
    'a_underline':  4,
    'a_blink':      5,
    'a_reverse':    7,
    'a_concealed':  8
}
ESC_TEMPLATE = '\033[{}m'

def escapes():
    return ESCAPES

def get_esc(name):
    return ESCAPES[name]

def fmt_esc(name):
    return ESC_TEMPLATE.format(escapes()[name])

FMT_ESCAPES = dict((k, fmt_esc(k)) for k in ESCAPES)


def uncolour(text):
    """
    Remove ANSI color/style sequences from a string. The set of all possible
    ANSI sequences is large, so does not try to strip every possible one. But
    does strip some outliers by other ANSI colorizers in the wild. Those
    include `\x1b[K` (aka EL or erase to end of line) and `\x1b[m`, a terse
    version of the more common `\x1b[0m`.

    Stolen from: https://github.com/jonathaneunice/colors/blob/master/colors/colors.py
    """
    text = re.sub('\x1b\\[(K|.*?m)', '', text)
    return text
