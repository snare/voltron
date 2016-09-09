import re

from pygments.lexer import RegexLexer, include, bygroups, using, DelegatingLexer
from pygments.lexers import get_lexer_by_name
from pygments.token import *


class DisassemblyLexer(RegexLexer):
    """
    For Nasm (Intel) disassembly from LLDB.

    Based on the NasmLexer included with Pygments
    """
    name = 'LLDB Intel syntax disassembly'
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
    register = (r'r[0-9]+[bwd]{0,1}|'
                r'[a-d][lh]|[er]?[a-d]x|[er]?[sbi]p|[er]?[sd]i|[c-gs]s|st[0-7]|'
                r'mm[0-7]|cr[0-4]|dr[0-367]|tr[3-7]|.mm\d+')
    wordop = r'seg|wrt|strict'
    type = r'byte|[dq]?word|ptr|xmmword|opaque'

    flags = re.IGNORECASE | re.MULTILINE
    tokens = {
        'root': [
            (identifier + '`' + identifier, Name.Function),
            ('->', Generic.Prompt),
            include('whitespace'),
            (r'^\s*%', Comment.Preproc, 'preproc'),
            (identifier + ':', Name.Label),
            (r'(%s)(\s+)(equ)' % identifier,
                bygroups(Name.Constant, Keyword.Declaration, Keyword.Declaration),
                'instruction-args'),
            (declkw, Keyword.Declaration, 'instruction-args'),
            (identifier, Keyword.Declaration, 'instruction-args'),
            (r' *' + hexn, Name.Label),
            (r'[:]', Text),
            (r'^->', Error),
            (r'[\r\n]+', Text)
        ],
        'instruction-args': [
            (register, Name.Builtin),
            (string, String),
            (hexn, Number.Hex),
            (octn, Number.Oct),
            (binn, Number.Bin),
            (floatn, Number.Float),
            (decn, Number.Integer),
            include('punctuation'),
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


class LLDBIntelLexer(DisassemblyLexer):
    name = 'LLDB Intel syntax disassembly'
    aliases = ['lldb_intel']


class LLDBATTLexer(DisassemblyLexer):
    name = 'LLDB AT&T syntax disassembly'
    aliases = ['lldb_att']


class GDBATTLexer(DisassemblyLexer):
    name = 'GDB AT&T syntax disassembly'
    aliases = ['gdb_att']


class GDBIntelLexer(DisassemblyLexer):
    name = 'GDB Intel syntax disassembly'
    aliases = ['gdb_intel']


class VDBATTLexer(DisassemblyLexer):
    name = 'VDB AT&T syntax disassembly'
    aliases = ['vdb_att']


class CapstoneIntelLexer(DisassemblyLexer):
    name = 'Capstone Intel syntax disassembly'
    aliases = ['capstone_intel']


class VDBIntelLexer(RegexLexer):
    """
    For Nasm (Intel) disassembly from VDB.

    Based on the LLDBIntelLexer above.
    major difference is the raw instruction hex after the instruction address.

    example:
      rip     0x000000000056eb4f: 4885ff            test rdi,rdi ;0x7f4f8740ca50,0x7f4f8740ca50
              0x000000000056eb52: 740f              jz 0x0056eb63
    """
    name = 'VDB Intel syntax disassembly'
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


class WinDbgIntelLexer(RegexLexer):
    name = 'WinDbg Intel syntax disassembly'
    aliases = ['windbg_intel']
    filenames = []
    mimetypes = []

    identifier = r'[<a-z$._?][\w$.?#@~>]*'
    hexn = r'(0[xX])?([0-9a-f]+|$0[0-9a-f`]*|[0-9]+[0-9a-f]*h)'
    addr = r'(0[xX])?([0-9a-f`]+|$0[0-9a-f`]*|[0-9]+[0-9a-f`]*h)'
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
    func = r'[a-zA-Z]*\!?'

    flags = re.IGNORECASE | re.MULTILINE
    tokens = {
        'root': [
            (addr, Number.Hex, 'instruction-line'),
            include('whitespace'),
            (identifier, Name.Class, 'label'),
            (r'[:]', Text),
            (r'[\r\n]+', Text)
        ],
        'instruction-line': [
            (r' ', Text),
            (hexn, Text, 'instruction'),
        ],
        'instruction': [
            include('whitespace'),
            (r'(%s)(\s+)(equ)' % identifier,
                bygroups(Name.Constant, Keyword.Declaration, Keyword.Declaration),
                'instruction-args'),
            (declkw, Keyword.Declaration, 'instruction-args'),
            (identifier, Name.Function, 'instruction-args'),
        ],
        'label': [
            (r'[!+]', Operator),
            (identifier, Name.Function),
            (hexn, Number.Hex),
            (r'[:]', Text, '#pop'),

        ],
        'instruction-args': [
            (string, String),
            include('punctuation'),
            (register, Name.Builtin),
            include('label'),
            (identifier, Name.Variable),
            (r'[\r\n]+', Text, '#pop:3'),
            include('whitespace'),
            (hexn, Number.Hex),
            (addr, Number.Hex),
            (octn, Number.Oct),
            (binn, Number.Bin),
            (floatn, Number.Float),
            (decn, Number.Integer),
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


class WinDbgATTLexer(WinDbgIntelLexer):
    name = 'WinDbg ATT syntax disassembly'
    aliases = ['windbg_att']
