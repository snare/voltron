import time

from nose.tools import *

import voltron
from voltron.core import *
from voltron.api import *
from voltron.plugin import *

log = logging.getLogger('tests')


class APITestRequest(APIRequest):
    _fields = {'target_id': False, 'address': False, 'count': True}
    _types = {'target_id': int, 'address': int, 'count': int}

    target_id = 0
    address = None
    count = None


class APITestResponse(APISuccessResponse):
    _fields = {'disassembly': True}


class APITestPlugin(APIPlugin):
    request = 'test'
    request_class = APITestRequest
    response_class = APITestResponse


def setup():
    voltron.setup_env()


def teardown():
    time.sleep(2)


def test_parent_message_validation_fail():
    msg = APIMessage()
    exception = False
    try:
        msg.validate()
    except MissingFieldError:
        exception = True
    assert exception


def test_parent_request_validation_fail():
    msg = APIRequest()
    exception = False
    try:
        msg.validate()
    except MissingFieldError:
        exception = True
    assert exception


def test_parent_request_type():
    msg = APIRequest()
    assert msg.type == 'request'


def test_parent_request_request():
    msg = APIRequest()
    assert msg.request is None


def test_parent_response_validation_fail():
    msg = APIResponse()
    exception = False
    try:
        msg.validate()
    except MissingFieldError:
        exception = True
    assert exception


def test_parent_response_type():
    msg = APIResponse()
    assert msg.type == 'response'


def test_parent_response_status():
    msg = APIResponse()
    assert msg.status is None


def test_success_response_validation_succeed():
    msg = APISuccessResponse()
    exception = False
    try:
        msg.validate()
    except MissingFieldError:
        exception = True
    assert not exception


def test_success_response_type():
    msg = APISuccessResponse()
    assert msg.type == 'response'


def test_success_response_status():
    msg = APISuccessResponse()
    assert msg.status == 'success'


def test_error_response_validation_fail():
    msg = APIErrorResponse()
    exception = False
    try:
        msg.validate()
    except MissingFieldError:
        exception = True
    assert exception


def test_error_response_type():
    msg = APIErrorResponse()
    assert msg.type == 'response'


def test_error_response_status():
    msg = APIErrorResponse()
    assert msg.status == 'error'


def test_invalid_request_error_response_validation_succeed():
    msg = APIInvalidRequestErrorResponse()
    exception = False
    try:
        msg.validate()
    except MissingFieldError:
        exception = True
    assert not exception


def test_invalid_request_error_response_type():
    msg = APIInvalidRequestErrorResponse()
    assert msg.type == 'response'


def test_invalid_request_error_response_status():
    msg = APIInvalidRequestErrorResponse()
    assert msg.status == 'error'


def test_test_request_validation_fail():
    msg = APITestRequest()
    exception = False
    try:
        msg.validate()
    except MissingFieldError:
        exception = True
    assert exception


def test_test_request_validation_fail_with_param():
    msg = APITestRequest(target_id=0)
    exception = False
    try:
        msg.validate()
    except MissingFieldError:
        exception = True
    assert exception


def test_test_request_validation_succeed_with_param():
    msg = api_request('test', count=16)
    exception = False
    try:
        msg.validate()
    except MissingFieldError:
        exception = True
    assert not exception
    assert msg.count == 16


def test_test_request_validation_succeed_with_data():
    msg = APITestRequest('{"data":{"count":16}}')
    exception = False
    try:
        msg.validate()
    except MissingFieldError as e:
        exception = True
    assert not exception
    assert msg.count == 16


def test_test_request_validation_succeed_by_assign():
    msg = APITestRequest()
    msg.count = 16
    exception = False
    try:
        msg.validate()
    except MissingFieldError as e:
        exception = True
    assert not exception
    assert msg.count == 16


def test_test_request_string():
    msg = APITestRequest(count=16)
    assert json.loads(str(msg)) == {"request": "test", "type": "request", "block": False, "timeout": 10,
                                    "data": {"count": 16, "target_id": 0, "address": None}}


def test_test_response_validation_fail():
    msg = APITestResponse()
    exception = False
    try:
        msg.validate()
    except MissingFieldError as e:
        exception = True
    assert exception


def test_test_response_validation_fail_with_param():
    msg = APITestResponse(thing=1)
    exception = False
    try:
        msg.validate()
    except MissingFieldError as e:
        exception = True
    assert exception


def test_test_response_validation_succeed_with_param():
    msg = APITestResponse(disassembly="xxx")
    exception = False
    try:
        msg.validate()
    except MissingFieldError as e:
        exception = True
    assert not exception


def test_test_response_validation_succeed_with_data():
    msg = APITestResponse('{"data":{"disassembly":"xxx"}}')
    exception = False
    try:
        msg.validate()
    except MissingFieldError as e:
        exception = True
    assert not exception


def test_test_response_validation_succeed_by_assign():
    msg = APITestResponse()
    msg.disassembly = "xxx"
    exception = False
    try:
        msg.validate()
    except MissingFieldError as e:
        print(str(e))
        exception = True
    assert not exception


def test_test_response_string():
    msg = APITestResponse(disassembly='xxx')
    assert json.loads(str(msg)) == {"status": "success", "type": "response", "data": {"disassembly": "xxx"}}


class APIEncodeMsg(APIMessage):
    _fields = {'enc': False}
    _encode_fields = ['enc']


def test_encode_fields():
    msg = APIEncodeMsg()
    msg.enc = six.b('').join([six.int2byte(x) for x in range(0x0, 0xff)])
    assert msg.to_dict()['data']['enc'] == six.text_type('AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0+P0BBQkNERUZHSElKS0xNTk9QUVJTVFVWV1hZWltcXV5fYGFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6e3x9fn+AgYKDhIWGh4iJiouMjY6PkJGSk5SVlpeYmZqbnJ2en6ChoqOkpaanqKmqq6ytrq+wsbKztLW2t7i5uru8vb6/wMHCw8TFxsfIycrLzM3Oz9DR0tPU1dbX2Nna29zd3t/g4eLj5OXm5+jp6uvs7e7v8PHy8/T19vf4+fr7/P3+')
    assert msg.to_json() == '{"data": {"enc": "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0+P0BBQkNERUZHSElKS0xNTk9QUVJTVFVWV1hZWltcXV5fYGFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6e3x9fn+AgYKDhIWGh4iJiouMjY6PkJGSk5SVlpeYmZqbnJ2en6ChoqOkpaanqKmqq6ytrq+wsbKztLW2t7i5uru8vb6/wMHCw8TFxsfIycrLzM3Oz9DR0tPU1dbX2Nna29zd3t/g4eLj5OXm5+jp6uvs7e7v8PHy8/T19vf4+fr7/P3+"}, "type": null}'

    msg2 = APIEncodeMsg(data=msg.to_json())
    assert msg.to_dict() == msg2.to_dict()
    assert msg.to_json() == msg2.to_json()
    assert msg2.enc == msg.enc

    msg3 = APIEncodeMsg()
    msg3.enc = six.u('xxxx')
    assert msg3.to_dict() == {'data': {'enc': 'eHh4eA=='}, 'type': None}
    msg3.enc = six.b('xxxx')
    assert msg3.to_dict() == {'data': {'enc': 'eHh4eA=='}, 'type': None}

    msg4 = APIEncodeMsg()
    msg4.from_dict(msg.to_dict())
    assert msg4.to_dict() == msg.to_dict()
