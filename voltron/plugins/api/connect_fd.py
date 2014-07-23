import voltron
from voltron.api import APIRequest, APIResponse, APIDispatcher

class APIConnectFDRequest(APIRequest):
    request = "connect_fd"

