import logging

from blessed import Terminal

from voltron.view import *
from voltron.plugin import *
from voltron.api import *

log = logging.getLogger('view')


class BreakpointsView (TerminalView):
    def build_requests(self):
        return [
            api_request('registers', registers=['pc']),
            api_request('breakpoints', block=self.block)
        ]

    def render(self, results):
        self.title = '[breakpoints]'

        r_res, b_res = results

        # get PC first so we can highlight a breakpoint we're at
        if r_res and r_res.is_success and len(r_res.registers) > 0:
            pc = r_res.registers[list(r_res.registers.keys())[0]]
        else:
            pc = -1

        if b_res and b_res.is_success:
            fmtd = []
            term = Terminal()
            for bp in b_res.breakpoints:
                # prepare formatting dictionary for the breakpoint
                d = bp.copy()
                d['locations'] = None
                d['t'] = term
                d['id'] = '#{:<2}'.format(d['id'])
                if d['one_shot']:
                    d['one_shot'] = self.config.format.one_shot.format(t=term)
                else:
                    d['one_shot'] = ''
                if d['enabled']:
                    d['disabled'] = ''
                else:
                    d['disabled'] = self.config.format.disabled.format(t=term)

                # add a row for each location
                for location in bp['locations']:
                    # add location data to formatting dict and format the row
                    d.update(location)
                    if pc == d['address']:
                        d['hit'] = self.config.format.hit.format(t=term)
                    else:
                        d['hit'] = ''
                    f = self.config.format.row.format(**d)
                    fmtd.append(f)
                    d['id'] = '   '

            self.body = '\n'.join(fmtd)
        else:
            log.error("Error getting breakpoints: {}".format(b_res.message))
            self.body = self.colour(b_res.message, 'red')

        super(BreakpointsView, self).render(results)


class BreakpointsViewPlugin(ViewPlugin):
    plugin_type = 'view'
    name = 'breakpoints'
    aliases = ('b', 'bp', 'break')
    view_class = BreakpointsView
