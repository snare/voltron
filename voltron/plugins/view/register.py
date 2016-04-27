import six
import struct

from numbers import Number
from voltron.core import STRTYPES
from voltron.view import *
from voltron.plugin import *
from voltron.api import *


class RegisterView (TerminalView):
    FORMAT_INFO = {
        'x86_64': [
            {
                'regs':             ['rax','rbx','rcx','rdx','rbp','rsp','rdi','rsi','rip',
                                     'r8','r9','r10','r11','r12','r13','r14','r15'],
                'label_format':     '{0:3s}',
                'category':         'general',
            },
            {
                'regs':             ['cs','ds','es','fs','gs','ss'],
                'value_format':     SHORT_ADDR_FORMAT_16,
                'category':         'general',
            },
            {
                'regs':             ['rflags'],
                'value_format':     '{}',
                'value_func':       'format_flags',
                'value_colour_en':  False,
                'category':         'general',
            },
            {
                'regs':             ['rflags'],
                'value_format':     '{}',
                'value_func':       'format_jump',
                'value_colour_en':  False,
                'category':         'general',
                'format_name':      'jump'
            },
            {
                'regs':             ['xmm0','xmm1','xmm2','xmm3','xmm4','xmm5','xmm6','xmm7','xmm8',
                                     'xmm9','xmm10','xmm11','xmm12','xmm13','xmm14','xmm15'],
                'value_format':     SHORT_ADDR_FORMAT_128,
                'value_func':       'format_xmm',
                'category':         'sse',
            },
            {
                'regs':             ['st0','st1','st2','st3','st4','st5','st6','st7'],
                'value_format':     '{0:0=20X}',
                'value_func':       'format_fpu',
                'category':         'fpu',
            },
        ],
        'x86': [
            {
                'regs':             ['eax','ebx','ecx','edx','ebp','esp','edi','esi','eip'],
                'label_format':     '{0:3s}',
                'value_format':     SHORT_ADDR_FORMAT_32,
                'category':         'general',
            },
            {
                'regs':             ['cs','ds','es','fs','gs','ss'],
                'value_format':     SHORT_ADDR_FORMAT_16,
                'category':         'general',
            },
            {
                'regs':             ['eflags'],
                'value_format':     '{}',
                'value_func':       'format_flags',
                'value_colour_en':  False,
                'category':         'general',
            },
            {
                'regs':             ['eflags'],
                'value_format':     '{}',
                'value_func':       'format_jump',
                'value_colour_en':  False,
                'category':         'general',
                'format_name':      'jump'
            },
            {
                'regs':             ['xmm0','xmm1','xmm2','xmm3','xmm4','xmm5','xmm6','xmm7'],
                'value_format':     SHORT_ADDR_FORMAT_128,
                'value_func':       'format_xmm',
                'category':         'sse',
            },
            {
                'regs':             ['st0','st1','st2','st3','st4','st5','st6','st7'],
                'value_format':     '{0:0=20X}',
                'value_func':       'format_fpu',
                'category':         'fpu',
            },
        ],
        'arm': [
            {
                'regs':             ['pc','sp','lr','cpsr','r0','r1','r2','r3','r4','r5','r6',
                                    'r7','r8','r9','r10','r11','r12'],
                'label_format':     '{0:>3s}',
                'value_format':     SHORT_ADDR_FORMAT_32,
                'category':         'general',
            }
        ],
        'arm64': [
            {
                'regs':             ['pc', 'sp', 'x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'x8', 'x9', 'x10',
                                    'x11', 'x12', 'x13', 'x14', 'x15', 'x16', 'x17', 'x18', 'x19', 'x20',
                                    'x21', 'x22', 'x23', 'x24', 'x25', 'x26', 'x27', 'x28', 'x29', 'x30'],
                'label_format':     '{0:3s}',
                'value_format':     SHORT_ADDR_FORMAT_64,
                'category':         'general',
            },
        ],
        'powerpc': [
            {
                'regs':             ['pc','msr','cr','lr', 'ctr',
                                     'r0','r1','r2','r3','r4','r5','r6', 'r7',
                                     'r8','r9','r10','r11','r12','r13','r14', 'r15',
                                     'r16','r17','r18','r19','r20','r21','r22', 'r23',
                                     'r24','r25','r26','r27','r28','r29','r30', 'r31'],
                'label_format':     '{0:>3s}',
                'value_format':     SHORT_ADDR_FORMAT_32,
                'category':         'general',
            }
        ],
    }
    TEMPLATES = {
        'x86_64': {
            'horizontal': {
                'general': (
                    "{raxl} {rax}  {rbxl} {rbx}  {rbpl} {rbp}  {rspl} {rsp}  {rflags}\n"
                    "{rdil} {rdi}  {rsil} {rsi}  {rdxl} {rdx}  {rcxl} {rcx}  {ripl} {rip}\n"
                    "{r8l} {r8}  {r9l} {r9}  {r10l} {r10}  {r11l} {r11}  {r12l} {r12}\n"
                    "{r13l} {r13}  {r14l} {r14}  {r15l} {r15}\n"
                    "{csl} {cs}  {dsl} {ds}  {esl} {es}  {fsl} {fs}  {gsl} {gs}  {ssl} {ss} {jump}"
                ),
                'sse': (
                    "{xmm0l}  {xmm0} {xmm1l}  {xmm1} {xmm2l}  {xmm2}\n"
                    "{xmm3l}  {xmm3} {xmm4l}  {xmm4} {xmm5l}  {xmm5}\n"
                    "{xmm6l}  {xmm6} {xmm7l}  {xmm7} {xmm8l}  {xmm8}\n"
                    "{xmm9l}  {xmm9} {xmm10l} {xmm10} {xmm11l} {xmm11}\n"
                    "{xmm12l} {xmm12} {xmm13l} {xmm13} {xmm14l} {xmm14}\n"
                    "{xmm15l} {xmm15}\n"
                ),
                'fpu': (
                    "{st0l} {st0} {st1l} {st1} {st2l} {st2} {st3l} {st2}\n"
                    "{st4l} {st4} {st5l} {st5} {st6l} {st6} {st7l} {st7}\n"
                )
            },
            'vertical': {
                'general': (
                    "{rflags}\n{jump}\n"
                    "{ripl} {rip}{ripinfo}\n"
                    "{raxl} {rax}{raxinfo}\n"
                    "{rbxl} {rbx}{rbxinfo}\n"
                    "{rbpl} {rbp}{rbpinfo}\n"
                    "{rspl} {rsp}{rspinfo}\n"
                    "{rdil} {rdi}{rdiinfo}\n"
                    "{rsil} {rsi}{rsiinfo}\n"
                    "{rdxl} {rdx}{rdxinfo}\n"
                    "{rcxl} {rcx}{rcxinfo}\n"
                    "{r8l} {r8}{r8info}\n"
                    "{r9l} {r9}{r9info}\n"
                    "{r10l} {r10}{r10info}\n"
                    "{r11l} {r11}{r11info}\n"
                    "{r12l} {r12}{r12info}\n"
                    "{r13l} {r13}{r13info}\n"
                    "{r14l} {r14}{r14info}\n"
                    "{r15l} {r15}{r15info}\n"
                    "{csl}  {cs}  {dsl}  {ds}\n{esl}  {es}  {fsl}  {fs}\n{gsl}  {gs}  {ssl}  {ss}"
                ),
                'sse': (
                    "{xmm0l}  {xmm0}\n{xmm1l}  {xmm1}\n{xmm2l}  {xmm2}\n{xmm3l}  {xmm3}\n"
                    "{xmm4l}  {xmm4}\n{xmm5l}  {xmm5}\n{xmm6l}  {xmm6}\n{xmm7l}  {xmm7}\n"
                    "{xmm8l}  {xmm8}\n{xmm9l}  {xmm9}\n{xmm10l} {xmm10}\n{xmm11l} {xmm11}\n"
                    "{xmm12l} {xmm12}\n{xmm13l} {xmm13}\n{xmm14l} {xmm14}\n{xmm15l} {xmm15}"
                ),
                'fpu': (
                    "{st0l} {st0}\n{st1l} {st1}\n{st2l} {st2}\n{st3l} {st2}\n"
                    "{st4l} {st4}\n{st5l} {st5}\n{st6l} {st6}\n{st7l} {st7}\n"
                )
            }
        },
        'x86': {
            'horizontal': {
                'general': (
                    "{eaxl} {eax}  {ebxl} {ebx}  {ebpl} {ebp}  {espl} {esp}  {eflags}\n"
                    "{edil} {edi}  {esil} {esi}  {edxl} {edx}  {ecxl} {ecx}  {eipl} {eip}\n"
                    "{csl} {cs}  {dsl} {ds}  {esl} {es}  {fsl} {fs}  {gsl} {gs}  {ssl} {ss} {jump}"
                ),
                'sse': (
                    "{xmm0l}  {xmm0} {xmm1l}  {xmm1} {xmm2l}  {xmm2}\n"
                    "{xmm3l}  {xmm3} {xmm4l}  {xmm4} {xmm5l}  {xmm5}\n"
                    "{xmm6l}  {xmm6} {xmm7l}"
                ),
                'fpu': (
                    "{st0l} {st0} {st1l} {st1} {st2l} {st2} {st3l} {st2}\n"
                    "{st4l} {st4} {st5l} {st5} {st6l} {st6} {st7l} {st7}\n"
                )
            },
            'vertical': {
                'general': (
                    "{eflags}\n{jump}\n"
                    "{eipl} {eip}{eipinfo}\n"
                    "{eaxl} {eax}{eaxinfo}\n"
                    "{ebxl} {ebx}{ebxinfo}\n"
                    "{ebpl} {ebp}{ebpinfo}\n"
                    "{espl} {esp}{espinfo}\n"
                    "{edil} {edi}{ediinfo}\n"
                    "{esil} {esi}{esiinfo}\n"
                    "{edxl} {edx}{edxinfo}\n"
                    "{ecxl} {ecx}{ecxinfo}\n"
                    "{csl}  {cs}\n{dsl}  {ds}\n{esl}  {es}\n{fsl}  {fs}\n{gsl}  {gs}\n{ssl}  {ss}"
                ),
                'sse': (
                    "{xmm0l}  {xmm0}\n{xmm1l}  {xmm1}\n{xmm2l}  {xmm2}\n{xmm3l}  {xmm3}\n"
                    "{xmm4l}  {xmm4}\n{xmm5l}  {xmm5}\n{xmm6l}  {xmm6}\n{xmm7l}  {xmm7}\n"
                ),
                'fpu': (
                    "{st0l} {st0}\n{st1l} {st1}\n{st2l} {st2}\n{st3l} {st2}\n"
                    "{st4l} {st4}\n{st5l} {st5}\n{st6l} {st6}\n{st7l} {st7}\n"
                )
            }
        },
        'arm': {
            'horizontal': {
                'general': (
                    "{pcl} {pc} {spl} {sp} {lrl} {lr} {cpsrl} {cpsr}\n"
                    "{r0l} {r0} {r1l} {r1} {r2l} {r2} {r3l} {r3} {r4l} {r4} {r5l} {r5} {r6l} {r6}\n"
                    "{r7l} {r7} {r8l} {r8} {r9l} {r9} {r10l} {r10} {r11l} {r11} {r12l} {r12}"
                ),
            },
            'vertical': {
                'general': (
                    "{pcl} {pc}{pcinfo}\n"
                    "{spl} {sp}{spinfo}\n"
                    "{lrl} {lr}{lrinfo}\n"
                    "{r0l} {r0}{r0info}\n"
                    "{r1l} {r1}{r1info}\n"
                    "{r2l} {r2}{r2info}\n"
                    "{r3l} {r3}{r3info}\n"
                    "{r4l} {r4}{r4info}\n"
                    "{r5l} {r5}{r5info}\n"
                    "{r6l} {r6}{r6info}\n"
                    "{r7l} {r7}{r7info}\n"
                    "{r8l} {r8}{r8info}\n"
                    "{r9l} {r9}{r9info}\n"
                    "{r10l} {r10}{r10info}\n"
                    "{r11l} {r11}{r11info}\n"
                    "{r12l} {r12}{r12info}\n"
                    "{cpsrl}{cpsr}"
                ),
            }
        },
        'powerpc': {
            'horizontal': {
                'general': (
                    "{pcl} {pc} {crl} {cr} {lrl} {lr} {msrl} {msr} {ctrl} {ctr}\n"
                    "{r0l} {r0} {r1l} {r1} {r2l} {r2} {r3l} {r3}\n"
                    "{r4l} {r4} {r5l} {r5} {r6l} {r6} {r7l} {r7}\n"
                    "{r8l} {r8} {r9l} {r9} {r10l} {r10} {r11l} {r11}\n"
                    "{r12l} {r12} {r13l} {r13} {r14l} {r14} {r15l} {r15}\n"
                    "{r16l} {r16} {r17l} {r17} {r18l} {r18} {r19l} {r19}\n"
                    "{r20l} {r20} {r21l} {r21} {r22l} {r22} {r23l} {r23}\n"
                    "{r24l} {r24} {r25l} {r25} {r26l} {r26} {r27l} {r27}\n"
                    "{r28l} {r28} {r29l} {r29} {r30l} {r30} {r31l} {r31}"
                ),
            },
            'vertical': {
                'general': (
                    "{pcl} {pc}{pcinfo}\n"
                    "{crl} {cr}{crinfo}\n"
                    "{lrl} {lr}{lrinfo}\n"
                    "{msrl} {msr}{msrinfo}\n"
                    "{ctrl} {ctr}{ctrinfo}\n"
                    "{r0l} {r0}{r0info}\n"
                    "{r1l} {r1}{r1info}\n"
                    "{r2l} {r2}{r2info}\n"
                    "{r3l} {r3}{r3info}\n"
                    "{r4l} {r4}{r4info}\n"
                    "{r5l} {r5}{r5info}\n"
                    "{r6l} {r6}{r6info}\n"
                    "{r7l} {r7}{r7info}\n"
                    "{r8l} {r8}{r8info}\n"
                    "{r9l} {r9}{r9info}\n"
                    "{r10l} {r10}{r10info}\n"
                    "{r11l} {r11}{r11info}\n"
                    "{r12l} {r12}{r12info}\n"
                    "{r13l} {r13}{r13info}\n"
                    "{r14l} {r14}{r14info}\n"
                    "{r15l} {r15}{r15info}\n"
                    "{r16l} {r16}{r16info}\n"
                    "{r17l} {r17}{r17info}\n"
                    "{r18l} {r18}{r18info}\n"
                    "{r19l} {r19}{r19info}\n"
                    "{r20l} {r20}{r20info}\n"
                    "{r21l} {r21}{r21info}\n"
                    "{r22l} {r22}{r22info}\n"
                    "{r23l} {r23}{r23info}\n"
                    "{r24l} {r24}{r24info}\n"
                    "{r25l} {r25}{r25info}\n"
                    "{r26l} {r26}{r26info}\n"
                    "{r27l} {r27}{r27info}\n"
                    "{r28l} {r28}{r28info}\n"
                    "{r29l} {r29}{r29info}\n"
                    "{r30l} {r30}{r30info}\n"
                    "{r31l} {r31}{r31info}"
                ),
            }
        },
        'arm64': {
            'horizontal': {
                'general': (
                    "{pcl} {pc}{pcinfo}\n"
                    "{spl} {sp}{spinfo}\n"
                    "{x0l} {x0}{x0info}\n"
                    "{x1l} {x1}{x1info}\n"
                    "{x2l} {x2}{x2info}\n"
                    "{x3l} {x3}{x3info}\n"
                    "{x4l} {x4}{x4info}\n"
                    "{x5l} {x5}{x5info}\n"
                    "{x6l} {x6}{x6info}\n"
                    "{x7l} {x7}{x7info}\n"
                    "{x8l} {x8}{x8info}\n"
                    "{x9l} {x9}{x9info}\n"
                    "{x10l} {x10}{x10info}\n"
                    "{x11l} {x11}{x11info}\n"
                    "{x12l} {x12}{x12info}\n"
                    "{x13l} {x13}{x13info}\n"
                    "{x14l} {x14}{x14info}\n"
                    "{x15l} {x15}{x15info}\n"
                    "{x16l} {x16}{x16info}\n"
                    "{x17l} {x17}{x17info}\n"
                    "{x18l} {x18}{x18info}\n"
                    "{x19l} {x19}{x19info}\n"
                    "{x20l} {x20}{x20info}\n"
                    "{x21l} {x21}{x21info}\n"
                    "{x22l} {x22}{x22info}\n"
                    "{x23l} {x23}{x23info}\n"
                    "{x24l} {x24}{x24info}\n"
                    "{x25l} {x25}{x25info}\n"
                    "{x26l} {x26}{x26info}\n"
                    "{x27l} {x27}{x27info}\n"
                    "{x28l} {x28}{x28info}\n"
                    "{x29l} {x29}{x29info}\n"
                    "{x30l} {x30}{x30info}\n"
                ),
            },
            'vertical': {
                'general': (
                    "{pcl} {pc}{pcinfo}\n"
                    "{spl} {sp}{spinfo}\n"
                    "{x0l} {x0}{x0info}\n"
                    "{x1l} {x1}{x1info}\n"
                    "{x2l} {x2}{x2info}\n"
                    "{x3l} {x3}{x3info}\n"
                    "{x4l} {x4}{x4info}\n"
                    "{x5l} {x5}{x5info}\n"
                    "{x6l} {x6}{x6info}\n"
                    "{x7l} {x7}{x7info}\n"
                    "{x8l} {x8}{x8info}\n"
                    "{x9l} {x9}{x9info}\n"
                    "{x10l} {x10}{x10info}\n"
                    "{x11l} {x11}{x11info}\n"
                    "{x12l} {x12}{x12info}\n"
                    "{x13l} {x13}{x13info}\n"
                    "{x14l} {x14}{x14info}\n"
                    "{x15l} {x15}{x15info}\n"
                    "{x16l} {x16}{x16info}\n"
                    "{x17l} {x17}{x17info}\n"
                    "{x18l} {x18}{x18info}\n"
                    "{x19l} {x19}{x19info}\n"
                    "{x20l} {x20}{x20info}\n"
                    "{x21l} {x21}{x21info}\n"
                    "{x22l} {x22}{x22info}\n"
                    "{x23l} {x23}{x23info}\n"
                    "{x24l} {x24}{x24info}\n"
                    "{x25l} {x25}{x25info}\n"
                    "{x26l} {x26}{x26info}\n"
                    "{x27l} {x27}{x27info}\n"
                    "{x28l} {x28}{x28info}\n"
                    "{x29l} {x29}{x29info}\n"
                    "{x30l} {x30}{x30info}\n"
                ),
            }
        }
    }
    FLAG_BITS = {'c': 0, 'p': 2, 'a': 4, 'z': 6, 's': 7, 't': 8, 'i': 9, 'd': 10, 'o': 11}
    FLAG_TEMPLATE = "[ {o} {d} {i} {t} {s} {z} {a} {p} {c} ]"
    XMM_INDENT = 7
    last_regs = None
    last_flags = None

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('register', help='register values', aliases=('r', 'reg'))
        VoltronView.add_generic_arguments(sp)
        sp.set_defaults(func=RegisterView)
        g = sp.add_mutually_exclusive_group()
        g.add_argument('--horizontal', '-o', dest="orientation", action='store_const', const="horizontal",
                       help='horizontal orientation')
        g.add_argument('--vertical', '-v', dest="orientation", action='store_const', const="vertical",
                       help='vertical orientation (default)')
        sp.add_argument('--general', '-g', dest="sections", action='append_const', const="general",
                        help='show general registers')
        sp.add_argument('--no-general', '-G', dest="sections", action='append_const', const="no_general",
                        help='show general registers')
        sp.add_argument('--sse', '-s', dest="sections", action='append_const', const="sse", help='show sse registers')
        sp.add_argument('--no-sse', '-S', dest="sections", action='append_const', const="no_sse",
                        help='show sse registers')
        sp.add_argument('--fpu', '-p', dest="sections", action='append_const', const="fpu", help='show fpu registers')
        sp.add_argument('--no-fpu', '-P', dest="sections", action='append_const', const="no_fpu",
                        help='show fpu registers')
        sp.add_argument('--info', '-i', action='store_true', help='show info (pointer derefs, ascii) for registers',
                        default=False)

    def __init__(self, *args, **kwargs):
        super(RegisterView, self).__init__(*args, **kwargs)
        self.str_upper = str.upper

    def apply_cli_config(self):
        super(RegisterView, self).apply_cli_config()
        if self.args.orientation is not None:
            self.config.orientation = self.args.orientation
        if self.args.sections is not None:
            a = filter(lambda x: 'no_' + x not in self.args.sections and not x.startswith('no_'), list(self.config.sections) + self.args.sections)
            config_sections = []
            for sec in a:
                if sec not in config_sections:
                    config_sections.append(sec)
            self.config.sections = config_sections

    def render(self):
        error = None

        # get target info (ie. arch)
        t_res, d_res, r_res = self.client.send_requests(api_request('targets', block=self.block),
                                                        api_request('disassemble', count=1, block=self.block),
                                                        api_request('registers', block=self.block))

        # don't render if it timed out, probably haven't stepped the debugger again
        if t_res.timed_out:
            return

        if t_res and t_res.is_error:
            error = t_res.message
        elif t_res is None or t_res and len(t_res.targets) == 0:
            error = "No such target"
        else:
            arch = t_res.targets[0]['arch']
            self.curr_arch = arch

            # ensure the architecture is supported
            if arch not in self.FORMAT_INFO:
                error = "Architecture '{}' not supported".format(arch)
            else:
                # get next instruction
                try:
                    self.curr_inst = d_res.disassembly.strip().split('\n')[-1].split(':')[1].strip()
                except:
                    self.curr_inst = None

                # get registers for target
                if r_res.is_error:
                    error = r_res.message

        # if everything is ok, render the view
        if not error:
            # Build template
            template = '\n'.join(map(lambda x: self.TEMPLATES[arch][self.config.orientation][x], self.config.sections))

            # Process formatting settings
            data = defaultdict(lambda: 'n/a')
            data.update(r_res.registers)
            formats = self.FORMAT_INFO[arch]
            formatted = {}
            for fmt in formats:
                # Apply defaults where they're missing
                fmt = dict(list(self.config.format.items()) + list(fmt.items()))

                # Format the data for each register
                for reg in fmt['regs']:
                    # Format the label
                    label = fmt['label_format'].format(reg)
                    if fmt['label_func'] != None:
                        formatted[reg + 'l'] = getattr(self, fmt['label_func'])(str(label))
                    if fmt['label_colour_en']:
                        formatted[reg + 'l'] = self.colour(formatted[reg + 'l'], fmt['label_colour'])

                    # Format the value
                    val = data[reg]
                    if isinstance(val, STRTYPES):
                        temp = fmt['value_format'].format(0)
                        if len(val) < len(temp):
                            val += (len(temp) - len(val)) * ' '
                        formatted_reg = self.colour(val, fmt['value_colour'])
                    else:
                        colour = fmt['value_colour']
                        if self.last_regs is None or self.last_regs is not None and val != self.last_regs[reg]:
                            colour = fmt['value_colour_mod']
                        formatted_reg = val
                        if fmt['value_format'] != None and isinstance(formatted_reg, Number):
                            formatted_reg = fmt['value_format'].format(formatted_reg)
                        if fmt['value_func'] != None:
                            if isinstance(fmt['value_func'], STRTYPES):
                                formatted_reg = getattr(self, fmt['value_func'])(formatted_reg)
                            else:
                                formatted_reg = fmt['value_func'](formatted_reg)
                        if fmt['value_colour_en']:
                            formatted_reg = self.colour(formatted_reg, colour)
                    if fmt['format_name'] == None:
                        formatted[reg] = formatted_reg
                    else:
                        formatted[fmt['format_name']] = formatted_reg

                    # Format the info
                    if self.args.info:
                        arrow = self.colour(' => ', self.config.format.divider_colour)
                        info = ""
                        try:
                            l = {2: 'H', 4: 'L', 8: 'Q'}[t_res.targets[0]['addr_size']]
                            f = '{}{}'.format(('<' if t_res.targets[0]['byte_order'] == 'little' else '>'), l)
                            chunk = struct.pack(f, data[reg])
                            printable_filter = ''.join([(len(repr(chr(x))) == 3) and chr(x) or '.' for x in range(256)])
                            ascii_str = ''.join(["%s" % ((x <= 127 and printable_filter[x]) or '.') for x in six.iterbytes(chunk)])
                            pipe = self.colour('|', self.config.format.divider_colour)
                            info += ' ' + pipe + ' ' + ascii_str + ' ' + pipe
                        except:
                            pass
                        try:
                            d = self.format_deref(r_res.deref[reg][1:])
                            if d:
                                info += arrow + d
                        except KeyError:
                            pass
                        except IndexError:
                            pass
                    else:
                        info = ''
                    formatted[reg + 'info'] = info

            # Prepare output
            log.debug('Formatted: ' + str(formatted))
            self.body = template.format(**formatted)

            # Store the regs
            self.last_regs = data
        else:
            # Set body to error message if appropriate
            self.body = self.colour(error, 'red')

        # Prepare headers and footers
        height, width = self.window_size()
        self.title = '[regs:{}]'.format('|'.join(self.config.sections))
        if len(self.title) > width:
            self.title = '[regs]'

        # Call parent's render method
        super(RegisterView, self).render()

    def format_address(self, address, size=8, pad=True, prefix='0x'):
        fmt = '{:' + ('0=' + str(size * 2) if pad else '') + 'X}'
        addr_str = fmt.format(address)
        if prefix:
            addr_str = prefix + addr_str
        return addr_str

    def format_deref(self, deref, size=8):
        fmtd = []
        for t, item in deref:
            if t == "pointer":
                fmtd.append(self.format_address(item, size=size, pad=False))
            elif t == "string":
                item = item.replace('\n', '\\n')
                fmtd.append(self.colour('"' + item + '"', self.config.format.string_colour))
            elif t == "unicode":
                item = item.replace('\n', '\\n')
                fmtd.append(self.colour('u"' + item + '"', self.config.format.string_colour))
            elif t == "symbol":
                fmtd.append(self.colour('`' + item + '`', self.config.format.symbol_colour))
            elif t == "circular":
                fmtd.append(self.colour('(circular)', self.config.format.divider_colour))
        return self.colour(' => ', self.config.format.divider_colour).join(fmtd)

    def format_flags(self, val):
        values = {}

        # Get formatting info for flags
        if self.curr_arch == 'x86_64':
            reg = 'rflags'
        elif self.curr_arch == 'x86':
            reg = 'eflags'
        fmt = dict(list(self.config.format.items()) + list(list(filter(lambda x: reg in x['regs'], self.FORMAT_INFO[self.curr_arch]))[0].items()))

        # Handle each flag bit
        val = int(val, 10)
        formatted = {}
        for flag in self.FLAG_BITS.keys():
            values[flag] = (val & (1 << self.FLAG_BITS[flag]) > 0)
            log.debug("Flag {} value {} (for flags 0x{})".format(flag, values[flag], val))
            formatted[flag] = str.upper(flag) if values[flag] else flag
            if self.last_flags is not None and self.last_flags[flag] != values[flag]:
                colour = fmt['value_colour_mod']
            else:
                colour = fmt['value_colour']
            formatted[flag] = self.colour(formatted[flag], colour)

        # Store the flag values for comparison
        self.last_flags = values

        # Format with template
        flags = self.FLAG_TEMPLATE.format(**formatted)

        return flags

    def format_jump(self, val):
        # Grab flag bits
        val = int(val, 10)
        values = {}
        for flag in self.FLAG_BITS.keys():
            values[flag] = (val & (1 << self.FLAG_BITS[flag]) > 0)

        # If this is a jump instruction, see if it will be taken
        j = None
        if self.curr_inst:
            inst = self.curr_inst.split()[0]
            if inst in ['ja', 'jnbe']:
                if not values['c'] and not values['z']:
                    j = (True, '!c && !z')
                else:
                    j = (False, 'c || z')
            elif inst in ['jae', 'jnb', 'jnc']:
                if not values['c']:
                    j = (True, '!c')
                else:
                    j = (False, 'c')
            elif inst in ['jb', 'jc', 'jnae']:
                if values['c']:
                    j = (True, 'c')
                else:
                    j = (False, '!c')
            elif inst in ['jbe', 'jna']:
                if values['c'] or values['z']:
                    j = (True, 'c || z')
                else:
                    j = (False, '!c && !z')
            elif inst in ['jcxz', 'jecxz', 'jrcxz']:
                if self.get_arch() == 'x64':
                    cx = regs['rcx']
                elif self.get_arch() == 'x86':
                    cx = regs['ecx']
                if cx == 0:
                    j = (True, cx + '==0')
                else:
                    j = (False, cx + '!=0')
            elif inst in ['je', 'jz']:
                if values['z']:
                    j = (True, 'z')
                else:
                    j = (False, '!z')
            elif inst in ['jnle', 'jg']:
                if not values['z'] and values['s'] == values['o']:
                    j = (True, '!z && s==o')
                else:
                    j = (False, 'z || s!=o')
            elif inst in ['jge', 'jnl']:
                if values['s'] == values['o']:
                    j = (True, 's==o')
                else:
                    j = (False, 's!=o')
            elif inst in ['jl', 'jnge']:
                if values['s'] == values['o']:
                    j = (False, 's==o')
                else:
                    j = (True, 's!=o')
            elif inst in ['jle', 'jng']:
                if values['z'] or values['s'] == values['o']:
                    j = (True, 'z || s==o')
                else:
                    j = (False, '!z && s!=o')
            elif inst in ['jne', 'jnz']:
                if not values['z']:
                    j = (True, '!z')
                else:
                    j = (False, 'z')
            elif inst in ['jno']:
                if not values['o']:
                    j = (True, '!o')
                else:
                    j = (False, 'o')
            elif inst in ['jnp', 'jpo']:
                if not values['p']:
                    j = (True, '!p')
                else:
                    j = (False, 'p')
            elif inst in ['jns']:
                if not values['s']:
                    j = (True, '!s')
                else:
                    j = (False, 's')
            elif inst in ['jo']:
                if values['o']:
                    j = (True, 'o')
                else:
                    j = (False, '!o')
            elif inst in ['jp', 'jpe']:
                if values['p']:
                    j = (True, 'p')
                else:
                    j = (False, '!p')
            elif inst in ['js']:
                if values['s']:
                    j = (True, 's')
                else:
                    j = (False, '!s')

        # Construct message
        if j is not None:
            taken, reason = j
            if taken:
                jump = 'Jump ({})'.format(reason)
            else:
                jump = '!Jump ({})'.format(reason)
        else:
            jump = ''

        # Pad out
        jump = '{:^19}'.format(jump)

        # Colour
        if j is not None:
            jump = self.colour(jump, self.config.format.value_colour_mod)
        else:
            jump = self.colour(jump, self.config.format.value_colour)

        return '[' + jump + ']'

    def format_xmm(self, val):
        if self.config.orientation == 'vertical':
            height, width = self.window_size()
            if width < len(SHORT_ADDR_FORMAT_128.format(0)) + self.XMM_INDENT:
                return val[:16] + '\n' + ' ' * self.XMM_INDENT + val[16:]
            else:
                return val[:16] + ':' + val[16:]
        else:
            return val

    def format_fpu(self, val):
        if self.config.orientation == 'vertical':
            return val
        else:
            return val


class RegisterViewPlugin(ViewPlugin):
    plugin_type = 'view'
    name = 'register'
    view_class = RegisterView
