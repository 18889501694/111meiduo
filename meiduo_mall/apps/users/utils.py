from itsdangerous import TimedSerializer as Serializer
from meiduo_mall import settings


def generic_email_verify_token(user_id):
    s = Serializer(secret_key=settings.SECRET_KEY, expires_in=3600 * 24)
    data = s.dumps({'user_id': user_id})

    return data.decode()


def check_verify_token(token):
    s = Serializer(secret_key=settings.SECRET_KEY, expires_in=3600 * 24)
    try:
        result = s.loads(token)
    except Exception as err:
        return None

    return result.get('user_id')
