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


class VDBIntelLexer(RegexLexer):
    """
    For Nasm (Intel) disassembly from VDB.

    Based on the LLDBIntelLexer above.
    major difference is the raw instruction hex after the instruction address.

    example:
      rip     0x000000000056eb4f: 4885ff            test rdi,rdi ;0x7f4f8740ca50,0x7f4f8740ca50
              0x000000000056eb52: 740f              jz 0x0056eb63
    """
    name = 'VDBIntel'
    aliases = ['vdb_intel']
    filenames = []
    mimetypes = []

    space = r'[ \t]+'
    identifier = r'[<a-z$._?][\w$.?#@~\+>]*'
    hexn = r'(?:0[xX][0-9a-f]+|$0[0-9a-f]*|[0-9]+[0-9a-f]*h)'  # hex number
    hexr = r'(?:[0-9a-f]+)'  # hex raw (no leader/trailer)
    octn = r'[0-7]+q'
    binn = r'[01]+b'
    decn = r'[0-9]+'
    floatn = decn + r'\.e?' + decn
    string = r'"(\\"|[^"\n])*"|' + r"'(\\'|[^'\n])*'|" + r"`(\\`|[^`\n])*`"
    register = (r'r[0-9]+[bwd]{0,1}|'
                r'[a-d][lh]|[er]?[a-d]x|[er]?[sbi]p|[er]?[sd]i|[c-gs]s|st[0-7]|'
                r'mm[0-7]|cr[0-4]|dr[0-367]|tr[3-7]|.mm\d*')
    wordop = r'seg|wrt|strict'
    type = r'byte|[dq]?word|ptr'

    flags = re.IGNORECASE | re.MULTILINE
    tokens = {
        'root': [
            (r'^(%s)(%s)(%s)(: )(%s)(%s)' % (register, space, hexn, hexr, space),
             bygroups(Name.Builtin, Text, Name.Label, Text, Number.Hex, Text),
             "instruction"),
            (r'^(%s)(%s)(: )(%s)(%s)' % (space, hexn, hexr, space),
             bygroups(Text, Name.Label, Text, Number.Hex, Text),
             "instruction")
        ],
        'instruction': [
            (space, Text),
            (r"(rep[a-z]*)( )", bygroups(Name.Function, Text)),
            (r"(%s)" % identifier, Name.Function, ("#pop", "instruction-args")),
        ],
        'instruction-args': [
            (space, Text),
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
            (r';', Text, ("#pop", 'comment')),
        ],
        'comment': [
            (space, Text),
            (string, Comment.Single),
            (hexn, Number.Hex),
            (octn, Number.Oct),
            (binn, Number.Bin),
            (floatn, Number.Float),
            (decn, Number.Integer),
            include('punctuation'),
            (register, Name.Builtin),
            (identifier, Name.Variable),
            (r'[\r\n]+', Text, '#pop'),
        ],
        'punctuation': [
            (r'[,():\[\]]+', Punctuation),
            (r'[&|^<>+*/%~-]+', Operator),
            (r'[$]+', Keyword.Constant),
            (wordop, Operator.Word),
            (type, Keyword.Type)
        ],
    }


class WinDbgIntelLexer(VDBIntelLexer):
    name = 'WinDbgIntel'
    aliases = ['windbg_intel']



all_lexers = {
    'lldb_intel': LLDBIntelLexer,
    'gdb_intel': LLDBIntelLexer,
    'vdb_intel': VDBIntelLexer,
    # 'windbg_intel': WinDbgIntelLexer,
    'capstone_intel': LLDBIntelLexer
}
