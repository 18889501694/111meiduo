from meiduo_mall import settings
from itsdangerous import TimedSerializer as Serializer


# 加密
def generic_openid(openid):
    s = Serializer(secret_key=settings.SECRET_KEY, expires_in=3600)
    access_token = s.dumps({'openid': openid})

    return access_token.decode()


# 解密
def check_access_token(token):
    s = Serializer(secret_key=settings.SECRET_KEY, expires_in=3600)
    try:
        result = s.loads(token)
    except Exception:
        return None
    else:
        return result.get('openid')
