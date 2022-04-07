from django.test import TestCase

# Create your tests here.

data = {
    '1': {'code': 400, 'errmsg': 'ok'},
    '2': {'code': 500, 'errmsg': '55ok'}
}
import pickle

b = pickle.dumps(data)
print(b)

import base64

encode = base64.b64encode(b)
print(encode)
# ************************************************
decode_bytes = base64.b64decode(encode)
print(decode_bytes)

b1 = pickle.loads(decode_bytes)
print(b1)
