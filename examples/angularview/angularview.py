import logging
import pygments
from voltron.plugin import *
from voltron.lexers import *

from flask import *

log = logging.getLogger('api')

app = Flask(__name__)

lexers = {
    'lldb_intel': LLDBIntelLexer
}

@app.route('/')
def root():
    return redirect("static", code=302)


@app.route("/api/request", methods=['POST'])
def handle_post():
    res = app.server.handle_request(str(request.data))
    res.formatted = format_disasm(res)
    return Response(str(res), status=200, mimetype='application/json')


def format_disasm(response):
    """
    Format
    """
    formatted = None

    try:
        lexer_id = '{}_{}'.format(response.host, response.flavor)
        log.debug("lexer: {}".format(lexer_id))
        lexer = lexers[lexer_id]()
    except:
        lexer = None

    if lexer:
        formatted = pygments.highlight(response.disassembly.strip(), lexer, pygments.formatters.HtmlFormatter())

    log.debug(formatted)

    return formatted


class AngularViewPlugin(WebPlugin):
    name = 'angularview'
    app = app
