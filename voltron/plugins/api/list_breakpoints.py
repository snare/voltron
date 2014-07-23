import voltron
from voltron.api import APIRequest, APIResponse, APIDispatcher


class APIListBreakpointsRequest(APIRequest):
    request = "list_breakpoints"