from pygments.style import Style
from pygments.token import Token, Comment, Name, Keyword, Generic, Number, Operator, String, Punctuation, Error

BASE03 = '#002b36'
BASE02 = '#073642'
BASE01 = '#586e75'
BASE00 = '#657b83'
BASE0 = '#839496'
BASE1 = '#93a1a1'
BASE2 = '#eee8d5'
BASE3 = '#fdf6e3'
YELLOW = '#b58900'
ORANGE = '#cb4b16'
RED = '#dc322f'
MAGENTA = '#d33682'
VIOLET = '#6c71c4'
BLUE = '#268bd2'
CYAN = '#2aa198'
GREEN = '#859900'


class VolarizedStyle(Style):
    background_color = BASE03
    styles = {
        Keyword: GREEN,
        Keyword.Constant: ORANGE,
        Keyword.Declaration: BASE1,
        Keyword.Namespace: ORANGE,
        # Keyword.Pseudo
        Keyword.Reserved: BLUE,
        Keyword.Type: VIOLET,

        Name: BASE1,
        Name.Attribute: BASE1,
        Name.Builtin: YELLOW,
        Name.Builtin.Pseudo: YELLOW,
        Name.Class: BLUE,
        Name.Constant: ORANGE,
        Name.Decorator: BLUE,
        Name.Entity: ORANGE,
        Name.Exception: YELLOW,
        Name.Function: BLUE,
        Name.Label: BASE01,
        # Name.Namespace
        # Name.Other
        Name.Tag: BLUE,
        Name.Variable: BLUE,
        # Name.Variable.Class
        # Name.Variable.Global
        # Name.Variable.Instance

        # Literal
        # Literal.Date
        String: BASE1,
        String.Backtick: BASE01,
        String.Char: BASE1,
        String.Doc: CYAN,
        # String.Double
        String.Escape: RED,
        String.Heredoc: CYAN,
        # String.Interpol
        # String.Other
        String.Regex: RED,
        # String.Single
        # String.Symbol
        Number: CYAN,
        # Number.Float
        # Number.Hex
        # Number.Integer
        # Number.Integer.Long
        # Number.Oct

        Operator: GREEN,
        Operator.Word: GREEN,

        Punctuation: BASE00,

        Comment: BASE00,
        # Comment.Multiline
        Comment.Preproc: GREEN,
        # Comment.Single
        Comment.Special: GREEN,

        # Generic
        Generic.Deleted: CYAN,
        Generic.Emph: 'italic',
        Generic.Error: RED,
        Generic.Heading: ORANGE,
        Generic.Inserted: GREEN,
        # Generic.Output
        Generic.Prompt: RED,
        Generic.Strong: 'bold',
        Generic.Subheading: ORANGE,
        # Generic.Traceback

        Token: BASE1,
        Token.Other: ORANGE,

        Error: RED
    }
