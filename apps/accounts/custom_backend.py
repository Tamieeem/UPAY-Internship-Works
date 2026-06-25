from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        # SimpleJWT will call authenticate(email=..., password=...) once we set
        # username_field="email" below. The fallback catches anything still
        # passing the credential under "username".
        if email is None:
            email = kwargs.get("username")
        if email is None or password is None:
            return None

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            return None 
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None