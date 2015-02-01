from voltron.view import *
from voltron.plugin import *
from voltron.api import *


class RegisterView (TerminalView):
    FORMAT_INFO = {
        'x86_64': [
            {
                'regs':             ['rax','rbx','rcx','rdx','rbp','rsp','rdi','rsi','rip',
                                     'r8','r9','r10','r11','r12','r13','r14','r15'],
                'label_format':     '{0:3s}:',
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
                'value_func':       'self.format_flags',
                'value_colour_en':  False,
                'category':         'general',
            },
            {
                'regs':             ['rflags'],
                'value_format':     '{}',
                'value_func':       'self.format_jump',
                'value_colour_en':  False,
                'category':         'general',
                'format_name':      'jump'
            },
            {
                'regs':             ['xmm0','xmm1','xmm2','xmm3','xmm4','xmm5','xmm6','xmm7','xmm8',
                                     'xmm9','xmm10','xmm11','xmm12','xmm13','xmm14','xmm15'],
                'value_format':     SHORT_ADDR_FORMAT_128,
                'value_func':       'self.format_xmm',
                'category':         'sse',
            },
            {
                'regs':             ['st0','st1','st2','st3','st4','st5','st6','st7'],
                'value_format':     '{0:0=20X}',
                'value_func':       'self.format_fpu',
                'category':         'fpu',
            },
        ],
        'x86': [
            {
                'regs':             ['eax','ebx','ecx','edx','ebp','esp','edi','esi','eip'],
                'label_format':     '{0:3s}:',
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
                'value_func':       'self.format_flags',
                'value_colour_en':  False,
                'category':         'general',
            },
            {
                'regs':             ['eflags'],
                'value_format':     '{}',
                'value_func':       'self.format_jump',
                'value_colour_en':  False,
                'category':         'general',
                'format_name':      'jump'
            },
            {
                'regs':             ['xmm0','xmm1','xmm2','xmm3','xmm4','xmm5','xmm6','xmm7'],
                'value_format':     SHORT_ADDR_FORMAT_128,
                'value_func':       'self.format_xmm',
                'category':         'sse',
            },
            {
                'regs':             ['st0','st1','st2','st3','st4','st5','st6','st7'],
                'value_format':     '{0:0=20X}',
                'value_func':       'self.format_fpu',
                'category':         'fpu',
            },
        ],
        'arm': [
            {
                'regs':             ['pc','sp','lr','cpsr','r0','r1','r2','r3','r4','r5','r6',
                                    'r7','r8','r9','r10','r11','r12'],
                'label_format':     '{0:>3s}:',
                'value_format':     SHORT_ADDR_FORMAT_32,
                'category':         'general',
            }
        ],
        'arm64': [
            {
                'regs':             ['pc', 'sp', 'x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'x8', 'x9', 'x10',
                                    'x11', 'x12', 'x13', 'x14', 'x15', 'x16', 'x17', 'x18', 'x19', 'x20',
                                    'x21', 'x22', 'x23', 'x24', 'x25', 'x26', 'x27', 'x28', 'x29', 'x30'],
                'label_format':     '{0:3s}:',
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
                'label_format':     '{0:>3s}:',
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
                    "{ripl} {rip}\n"
                    "{raxl} {rax}\n{rbxl} {rbx}\n{rbpl} {rbp}\n{rspl} {rsp}\n"
                    "{rdil} {rdi}\n{rsil} {rsi}\n{rdxl} {rdx}\n{rcxl} {rcx}\n"
                    "{r8l} {r8}\n{r9l} {r9}\n{r10l} {r10}\n{r11l} {r11}\n{r12l} {r12}\n"
                    "{r13l} {r13}\n{r14l} {r14}\n{r15l} {r15}\n"
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
                    "{eipl} {eip}\n"
                    "{eaxl} {eax}\n{ebxl} {ebx}\n{ebpl} {ebp}\n{espl} {esp}\n"
                    "{edil} {edi}\n{esil} {esi}\n{edxl} {edx}\n{ecxl} {ecx}\n"
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
                    "{pcl} {pc}\n{spl} {sp}\n{lrl} {lr}\n"
                    "{r0l} {r0}\n{r1l} {r1}\n{r2l} {r2}\n{r3l} {r3}\n{r4l} {r4}\n{r5l} {r5}\n{r6l} {r6}\n{r7l} {r7}\n"
                    "{r8l} {r8}\n{r9l} {r9}\n{r10l} {r10}\n{r11l} {r11}\n{r12l} {r12}\n{cpsrl}{cpsr}"
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
                    "{pcl} {pc}\n{crl} {cr}\n{lrl} {lr}\n"
                    "{msrl} {msr}\n{ctrl} {ctr}\n"
                    "{r0l} {r0}\n{r1l} {r1}\n{r2l} {r2}\n{r3l} {r3}\n{r4l} {r4}\n{r5l} {r5}\n{r6l} {r6}\n{r7l} {r7}\n"
                    "{r8l} {r8}\n{r9l} {r9}\n{r10l} {r10}\n{r11l} {r11}\n{r12l} {r12}\n{r13l} {r13}\n{r14l} {r14}\n{r15l} {r15}\n"
                    "{r16l} {r16}\n{r17l} {r17}\n{r18l} {r18}\n{r19l} {r19}\n{r20l} {r20}\n{r21l} {r21}\n{r22l} {r22}\n{r23l} {r23}\n"
                    "{r24l} {r24}\n{r25l} {r25}\n{r26l} {r26}\n{r27l} {r27}\n{r28l} {r28}\n{r29l} {r29}\n{r30l} {r30}\n{r31l} {r31}"
                ),
            }
        },
        'arm64': {
            'horizontal': {
                'general': (
                    "{pcl} {pc}\n{spl} {sp}\n"
                    "{x0l} {x0}\n{x1l} {x1}\n{x2l} {x2}\n{x3l} {x3}\n{x4l} {x4}\n{x5l} {x5}\n{x6l} {x6}\n{x7l} {x7}\n"
                    "{x8l} {x8}\n{x9l} {x9}\n{x10l} {x10}\n{x11l} {x11}\n{x12l} {x12}\n{x13l} {x13}\n{x14l} {x14}\n"
                    "{x15l} {x15}\n{x16l} {x16}\n{x17l} {x17}\n{x18l} {x18}\n{x19l} {x19}\n{x20l} {x20}\n{x21l} {x21}\n"
                    "{x22l} {x22}\n{x23l} {x23}\n{x24l} {x24}\n{x25l} {x25}\n{x26l} {x26}\n{x27l} {x27}\n{x28l} {x28}\n"
                    "{x29l} {x29}\n{x30l} {x30}\n"
                ),
            },
            'vertical': {
                'general': (
                    "{pcl} {pc}\n{spl} {sp}\n"
                    "{x0l} {x0}\n{x1l} {x1}\n{x2l} {x2}\n{x3l} {x3}\n{x4l} {x4}\n{x5l} {x5}\n{x6l} {x6}\n{x7l} {x7}\n"
                    "{x8l} {x8}\n{x9l} {x9}\n{x10l} {x10}\n{x11l} {x11}\n{x12l} {x12}\n{x13l} {x13}\n{x14l} {x14}\n"
                    "{x15l} {x15}\n{x16l} {x16}\n{x17l} {x17}\n{x18l} {x18}\n{x19l} {x19}\n{x20l} {x20}\n{x21l} {x21}\n"
                    "{x22l} {x22}\n{x23l} {x23}\n{x24l} {x24}\n{x25l} {x25}\n{x26l} {x26}\n{x27l} {x27}\n{x28l} {x28}\n"
                    "{x29l} {x29}\n{x30l} {x30}"
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
        g.add_argument('--horizontal', '-o',    dest="orientation", action='store_const',   const="horizontal", help='horizontal orientation')
        g.add_argument('--vertical', '-v',      dest="orientation", action='store_const',   const="vertical",   help='vertical orientation (default)')
        sp.add_argument('--general', '-g',      dest="sections",    action='append_const',  const="general",    help='show general registers')
        sp.add_argument('--no-general', '-G',   dest="sections",    action='append_const',  const="no_general", help='show general registers')
        sp.add_argument('--sse', '-s',          dest="sections",    action='append_const',  const="sse",        help='show sse registers')
        sp.add_argument('--no-sse', '-S',       dest="sections",    action='append_const',  const="no_sse",     help='show sse registers')
        sp.add_argument('--fpu', '-p',          dest="sections",    action='append_const',  const="fpu",        help='show fpu registers')
        sp.add_argument('--no-fpu', '-P',       dest="sections",    action='append_const',  const="no_fpu",     help='show fpu registers')

    def apply_cli_config(self):
        super(RegisterView, self).apply_cli_config()
        if self.args.orientation != None:
            self.config.orientation = self.args.orientation
        if self.args.sections != None:
            a = filter(lambda x: 'no_'+x not in self.args.sections and not x.startswith('no_'), self.config.sections + self.args.sections)
            self.config.sections = []
            for sec in a:
                if sec not in self.config.sections:
                    self.config.sections.append(sec)

    def render(self):
        error = None

        # get target info (ie. arch)
        res = self.client.perform_request('targets')
        if res.is_error:
            error = "Failed getting targets: {}".format(res.message)
        else:
            if len(res.targets) == 0:
                error = "No targets in debugger"
            else:
                arch = res.targets[0]['arch']
                self.curr_arch = arch

                # ensure the architecture is supported
                if arch not in self.FORMAT_INFO:
                    error = "Archiecture '{}' not supported".format(arch)
                else:
                    # get next instruction
                    res = self.client.perform_request('disassemble', count=1)
                    try:
                        self.curr_inst = res.disassembly.strip().split('\n')[-1].split(':')[1].strip()
                    except:
                        self.curr_inst = None

                    # get registers for target
                    res = self.client.perform_request('registers')
                    if res.is_error:
                        error = "Failed getting registers: {}".format(res.message)

        # if everything is ok, render the view
        if not error:
            # Store current response
            self.curr_res = res

            # Build template
            template = '\n'.join(map(lambda x: self.TEMPLATES[arch][self.config.orientation][x], self.config.sections))

            # Process formatting settings
            data = defaultdict(lambda: 'n/a')
            data.update(res.registers)
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
                        formatted[reg+'l'] = eval(fmt['label_func'])(str(label))
                    if fmt['label_colour_en']:
                        formatted[reg+'l'] =  self.colour(formatted[reg+'l'], fmt['label_colour'])

                    # Format the value
                    val = data[reg]
                    if type(val) == str:
                        temp = fmt['value_format'].format(0)
                        if len(val) < len(temp):
                            val += (len(temp) - len(val))*' '
                        formatted_reg = self.colour(val, fmt['value_colour'])
                    else:
                        colour = fmt['value_colour']
                        if self.last_regs == None or self.last_regs != None and val != self.last_regs[reg]:
                            colour = fmt['value_colour_mod']
                        formatted_reg = val
                        if fmt['value_format'] != None and type(formatted_reg) not in [str, unicode]:
                            formatted_reg = fmt['value_format'].format(formatted_reg)
                        if fmt['value_func'] != None:
                            if type(fmt['value_func']) == str:
                                formatted_reg = eval(fmt['value_func'])(formatted_reg)
                            else:
                                formatted_reg = fmt['value_func'](formatted_reg)
                        if fmt['value_colour_en']:
                            formatted_reg = self.colour(formatted_reg, colour)
                    if fmt['format_name'] == None:
                        formatted[reg] = formatted_reg
                    else:
                        formatted[fmt['format_name']] = formatted_reg

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
            if self.last_flags != None and self.last_flags[flag] != values[flag]:
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
                    j = (True, cx+'==0')
                else:
                    j = (False, cx+'!=0')
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
        height, width = self.window_size()
        t = '{:^%d}' % (width - 2)
        jump = t.format(jump)

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
                return val[:16] + '\n' + ' '*self.XMM_INDENT + val[16:]
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
