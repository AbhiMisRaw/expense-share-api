from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404


class UserManager(BaseUserManager):
    def get_object_by_id(self, id):
        try:
            instance = self.get(id=id)
            return instance
        except (ObjectDoesNotExist, ValueError, TypeError):
            return Http404

    def create_user(self, username, email, mobile_number, password=None, **kwargs):
        """
        Creating and returning User with an email, mobile_no, password and username
        """

        if username is None:
            raise TypeError("Users must have a username")

        if email is None:
            raise TypeError("Users must have an email")

        if password is None:
            raise TypeError("Users must have a Password")

        if mobile_number is None:
            raise TypeError("Users must have a Mobile Number")

        user = self.model(
            username=username,
            email=self.normalize_email(email),
            mobile_number=mobile_number,
            **kwargs,
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, mobile_number, password, **kwargs):
        if username is None:
            raise TypeError("Superusers must have a username")

        if email is None:
            raise TypeError("Superusers must have an email")

        if password is None:
            raise TypeError("Superusers must have a Password")

        if mobile_number is None:
            raise TypeError("Superusers must have a Mobile Number")

        user = self.create_user(username, email, mobile_number, password, **kwargs)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(db_index=True, max_length=255, unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(db_index=True, unique=True)
    # Here we assuming all the mobile number have 10 digits and from india
    mobile_number = models.CharField(db_index=True, max_length=10)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now=True)
    updated = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "mobile_number", "first_name", "last_name"]

    # default user-manager
    objects = UserManager()

    def __str__(self) -> str:
        return f"{self.email}"
