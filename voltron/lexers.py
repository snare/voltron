import re

from pygments.lexer import RegexLexer, include, bygroups, using, DelegatingLexer
from pygments.token import *


class LLDBIntelLexer(RegexLexer):
    """
    For Nasm (Intel) disassembly from LLDB.

    Based on the NasmLexer included with Pygments
    """
    name = 'LLDBIntel'
    aliases = ['lldb_intel']
    filenames = []
    mimetypes = []

    identifier = r'[<a-z$._?][\w$.?#@~\+>]*'
    hexn = r'(?:0[xX][0-9a-f]+|$0[0-9a-f]*|[0-9]+[0-9a-f]*h)'
    octn = r'[0-7]+q'
    binn = r'[01]+b'
    decn = r'[0-9]+'
    floatn = decn + r'\.e?' + decn
    string = r'"(\\"|[^"\n])*"|' + r"'(\\'|[^'\n])*'|" + r"`(\\`|[^`\n])*`"
    declkw = r'(?:res|d)[bwdqt]|times'
    register = (r'r[0-9]+?[bwd]{0,1}|'
                r'[a-d][lh]|[er]?[a-d]x|[er]?[sbi]p|[er]?[sd]i|[c-gs]s|st[0-7]|'
                r'mm[0-7]|cr[0-4]|dr[0-367]|tr[3-7]|.mm\d*')
    wordop = r'seg|wrt|strict'
    type = r'byte|[dq]?word|ptr'


    flags = re.IGNORECASE | re.MULTILINE
    tokens = {
        'root': [
            include('whitespace'),
            (r'^\s*%', Comment.Preproc, 'preproc'),
            (identifier + ':', Name.Label),
            (r'(%s)(\s+)(equ)' % identifier,
                bygroups(Name.Constant, Keyword.Declaration, Keyword.Declaration),
                'instruction-args'),
            (declkw, Keyword.Declaration, 'instruction-args'),
            (identifier, Name.Function, 'instruction-args'),
            (hexn, Number.Hex),
            (r'[:]', Text),
            (r'^->', Error),
            (r'[\r\n]+', Text)
        ],
        'instruction-args': [
            (string, String),
            (hexn, Number.Hex),
            (octn, Number.Oct),
            (binn, Number.Bin),
            (floatn, Number.Float),
            (decn, Number.Integer),
            include('punctuation'),
            (register, Name.Builtin),
            (identifier, Name.Variable),
            (r'[\r\n]+', Text, '#pop'),
            include('whitespace')
        ],
        'preproc': [
            (r'[^;\n]+', Comment.Preproc),
            (r';.*?\n', Comment.Single, '#pop'),
            (r'\n', Comment.Preproc, '#pop'),
        ],
        'whitespace': [
            (r'\n', Text),
            (r'[ \t]+', Text),
            (r';.*', Comment.Single),
            (r'#.*', Comment.Single)
        ],
        'punctuation': [
            (r'[,():\[\]]+', Punctuation),
            (r'[&|^<>+*/%~-]+', Operator),
            (r'[$]+', Keyword.Constant),
            (wordop, Operator.Word),
            (type, Keyword.Type)
        ],
    }


all_lexers = {
    'lldb_intel': LLDBIntelLexer,
    'gdb_intel': LLDBIntelLexer
}
