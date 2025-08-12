import random
import string

def code_generator(size=25, chars=string.ascii_lowercase + string.digits):
    code = random.randint(0, 99999999)

    return str("#") + str(code)


def create_shortcode(instance, size=10):
    new_code = code_generator(size=size)
    Klass = instance.__class__
    qs_exists = Klass.objects.filter(account_number=new_code).exists()
    if qs_exists:
        return create_shortcode(size=size)
    return new_code