import logging
from mock import Mock

LOGGER_DEFAULT = {
    'handlers': ['file'],
    'level': 'DEBUG',
    'propagate': False
}

LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {'format': '[%(levelname)s] %(message)s'},
        'testing': {'format': "%(levelname)-7s %(filename)12s:%(lineno)-4s %(funcName)20s -- %(message)s"}
    },
    'handlers': {
        'default': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        'file': {
            'class': 'logging.FileHandler',
            'formatter': 'testing',
            'filename': 'tests/test.log',
            'delay': True
        }
    },
    'loggers': {
        '':         LOGGER_DEFAULT,
        'debugger': LOGGER_DEFAULT,
        'core':     LOGGER_DEFAULT,
        'main':     LOGGER_DEFAULT,
        'api':      LOGGER_DEFAULT,
        'view':     LOGGER_DEFAULT,
        'plugin':   LOGGER_DEFAULT,
    }
}

logging.config.dictConfig(LOG_CONFIG)

state_response = "stopped"
targets_response = [{
    "id":       0,
    "file":     "/bin/ls",
    "arch":     "x86_64",
    "state":     "stopped"
}]
read_registers_response = ({"gs": 0, "fooff": 0, "edi": 1, "edx": 1349115624, "r13w": 0, "r8l": 0, "fiseg": 0, "r8d": 0,
    "r13d": 0, "r13l": 0, "fstat": 0, "r8w": 0, "ymm9": "n/a", "ymm8": "n/a", "r14": 0, "r15": 0, "r12": 0, "r13": 0,
    "dh": 222, "di": 1, "ymm1": "n/a", "ymm0": "n/a", "ymm3": "n/a", "ymm2": "n/a", "ymm5": "n/a", "ymm4": "n/a",
    "ymm7": "n/a", "ymm6": "n/a", "dx": 57064, "dil": 1, "xmm6": "n/a", "r10l": 0, "bpl": 200, "r10d": 1349110784,
    "xmm10": "n/a", "xmm11": "n/a", "xmm12": "n/a", "xmm13": "n/a", "xmm14": "n/a", "xmm15": "n/a", "fioff": 0,
    "sil": 216, "r10w": 52224, "mxcsr": 8064, "ebp": 1349115592, "ebx": 0, "r15d": 0, "fop": 0, "esp": 1349115576,
    "r15l": 0, "r15w": 0, "ftag": 0, "esi": 1349115608, "bl": 0, "bh": 0, "xmm2": "n/a", "xmm3": "n/a", "xmm0": "n/a",
    "xmm1": "n/a", "bp": 57032, "xmm7": "n/a", "xmm4": "n/a", "xmm5": "n/a", "xmm8": "n/a", "xmm9": "n/a", "bx": 0,
    "ecx": 1349115632, "r9l": 0, "dl": 232, "r12w": 0, "r9d": 1349111808, "r8": 0, "rdx": 140734542503656, "r12d": 0,
    "r9w": 53248, "rdi": 1, "r12l": 0, "ch": 222, "cl": 240, "stmm4": "n/a", "stmm5": "n/a", "stmm6": "n/a", "stmm7":
    "n/a", "stmm0": "n/a", "stmm1": "n/a", "stmm2": "n/a", "stmm3": "n/a", "cx": 57072, "cs": 43,
    "rcx": 140734542503664, "rflags": 582, "rsi": 140734542503640, "mxcsrmask": 65535, "eax": 257305888,
    "rsp": 140734542503608, "trapno": 3, "r14d": 0, "faultvaddr": 4552486912, "err": 0, "rbx": 0, "r14l": 0,
    "rbp": 140734542503624, "r14w": 0, "ah": 45, "al": 32, "rip": 4552273184, "r9": 140734542499840, "spl": 184,
    "ax": 11552, "fctrl": 895, "rax": 4552273184, "r11l": 70, "r10": 140734542498816, "r11": 582, "r11d": 582,
    "foseg": 0, "r11w": 582, "fs": 0, "ymm11": "n/a", "ymm10": "n/a", "ymm13": "n/a", "ymm12": "n/a", "ymm15": "n/a",
    "ymm14": "n/a", "sp": 57016, "si": 57048})
read_memory_response = "\xff"*0x40
read_stack_response = "\xff"*0x40
wait_response = "stopped"
execute_command_response = "inferior`main:\n-> 0x100000d20:  pushq  %rbp\n   0x100000d21:  movq   %rsp, %rbp\n   0x100000d24:  subq   $0x40, %rsp\n   0x100000d28:  movl   $0x0, -0x4(%rbp)\n   0x100000d2f:  movl   %edi, -0x8(%rbp)\n   0x100000d32:  movq   %rsi, -0x10(%rbp)\n   0x100000d36:  movl   $0x0, -0x14(%rbp)\n   0x100000d3d:  movq   $0x0, -0x20(%rbp)\n   0x100000d45:  cmpl   $0x1, -0x8(%rbp)\n   0x100000d4c:  jle    0x100000d94               ; main + 116\n   0x100000d52:  movq   -0x10(%rbp), %rax\n   0x100000d56:  movq   0x8(%rax), %rdi\n   0x100000d5a:  leaq   0x18a(%rip), %rsi         ; \"sleep\"\n   0x100000d61:  callq  0x100000ea0               ; symbol stub for: strcmp\n   0x100000d66:  cmpl   $0x0, %eax\n   0x100000d6b:  jne    0x100000d94               ; main + 116\n   0x100000d71:  leaq   0x179(%rip), %rdi         ; \"*** Sleeping for 5 seconds\\n\"\n   0x100000d78:  movb   $0x0, %al\n   0x100000d7a:  callq  0x100000e94               ; symbol stub for: printf\n   0x100000d7f:  movl   $0x5, %edi\n   0x100000d84:  movl   %eax, -0x24(%rbp)\n   0x100000d87:  callq  0x100000e9a               ; symbol stub for: sleep\n   0x100000d8c:  movl   %eax, -0x28(%rbp)\n   0x100000d8f:  jmpq   0x100000e88               ; main + 360\n   0x100000d94:  cmpl   $0x1, -0x8(%rbp)\n   0x100000d9b:  jle    0x100000dd6               ; main + 182\n   0x100000da1:  movq   -0x10(%rbp), %rax\n   0x100000da5:  movq   0x8(%rax), %rdi\n   0x100000da9:  leaq   0x15d(%rip), %rsi         ; \"loop\"\n   0x100000db0:  callq  0x100000ea0               ; symbol stub for: strcmp\n   0x100000db5:  cmpl   $0x0, %eax\n   0x100000dba:  jne    0x100000dd6               ; main + 182"
disassemble_response = execute_command_response


def inject_mock(adaptor):
    adaptor.version = Mock(return_value='lldb-something')
    adaptor.state = Mock(return_value=state_response)
    adaptor.target = Mock(return_value=targets_response[0])
    adaptor._target = Mock(return_value=targets_response[0])
    adaptor.targets = Mock(return_value=targets_response)
    adaptor.read_registers = Mock(return_value=read_registers_response)
    adaptor.read_memory = Mock(return_value=read_memory_response)
    adaptor.read_stack = Mock(return_value=read_stack_response)
    adaptor.wait = Mock(return_value=wait_response)
    adaptor.execute_command = Mock(return_value=execute_command_response)
    adaptor.disassemble = Mock(return_value=disassemble_response)
