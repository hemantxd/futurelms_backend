import profile
import jwt
import random
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)
from django.db import models

from core.models import TimestampedModel
from django.core.exceptions import ObjectDoesNotExist

def create_username(username):
    check_count = 1
    while check_username(username):
        if check_count >= 2:
            username = username + str(check_count)
        if len(username) < 6:
            username = username + \
            "".join(map(str, random.sample(range(1, 10), 6-len(username))))
        check_count += 1
    return username


def check_username(username):
    try:
        User.objects.get(username=username)
    except ObjectDoesNotExist:
        return False
    return True


class UserManager(BaseUserManager):
    """
    Django requires that custom users define their own Manager class. By
    inheriting from `BaseUserManager`, we get a lot of the same code used by
    Django to create a `User` for free.
    All we have to do is override the `create_user` function which we will use
    to create `User` objects.
    """

    def create_user(self, username=None, email=None, phonenumber=None, password=None, fullname=None):
        """Create and return a `User` with an email, username and password."""
        
        if fullname is None:
            raise TypeError("user must have fullname.")

        user = User.objects.filter(phonenumber=phonenumber).first()
        if not user:
            if username is None:
                last_user_created_id = User.objects.all().last().id
                username = create_username(str(10000 + last_user_created_id))

            if email is None:
                # email = username + '@noemail.com'
                email = None
            if password is None:
                password = username
            
            if email:
                user = self.model(username=username, email=self.normalize_email(email))
            else:
                user = self.model(username=username, email=None)
            user.set_password(password)
        else:
            if email:
                user.email=self.normalize_email(email)
                user.save()
        user.phonenumber = phonenumber
        user.fullname = fullname
        user.save()

        return user

    def create_superuser(self, username, email, phonenumber, password, fullname):
        """
        Create and return a `User` with superuser powers.
        Superuser powers means that this use is an admin that can do anything
        they want.
        """

        if password is None:
            raise TypeError('Superusers must have a password.')

        user = self.create_user(username, email, phonenumber, password, fullname)
        user.is_superuser = True
        user.is_staff = True
        user.phonenumber = phonenumber
        user.save()

        return user


class User(AbstractBaseUser, PermissionsMixin, TimestampedModel):
    # Each `User` needs a human-readable unique identifier that we can use to
    # represent the `User` in the UI. We want to index this column in the
    # database to improve lookup performance.
    username = models.CharField(db_index=True, max_length=50, unique=True)

    # We also need a way to contact the user and a way for the user to identify
    # themselves when logging in. Since we need an email address for contacting
    # the user anyways, we will also use the email for logging in because it is
    # the most common form of login credential at the time of writing.
    email = models.EmailField(db_index=True, max_length=50, unique=True, blank=True, null=True)

    # When a user no longer wishes to use our platform, they may try to delete
    # there account. That's a problem for us because the data we collect is
    # valuable to us and we don't want to delete it. To solve this problem, we
    # will simply offer users a way to deactivate their account instead of
    # letting them delete it. That way they won't show up on the site anymore,
    # but we can still analyze the data.
    is_active = models.BooleanField(default=True)

    # The `is_staff` flag is expected by Django to determine who can and cannot
    # log into the Django admin site. For most users, this flag will always be
    # falsed.
    is_staff = models.BooleanField(default=False)

    is_individual = models.BooleanField(default=True)

    phonenumber = models.CharField(null=True, blank=True, max_length=15)

    fullname = models.CharField(null=True, blank=True, max_length=50)

    registrationtype = models.CharField(
        blank=True, default='self', max_length=15)

    # More fields required by Django when specifying a custom user model.

    # The `USERNAME_FIELD` property tells us which field we will use to log in.
    # In this case, we want that to be the email field.
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phonenumber', 'fullname']

    # Tells Django that the UserManager class defined above should manage
    # objects of this type.
    objects = UserManager()

    def __str__(self):
        """
        Returns a string representation of this `User`.
        This string is used when a `User` is printed in the console.
        """
        return self.username

    @property
    def token(self):
        """
        Allows us to get a user's token by calling `user.token` instead of
        `user.generate_jwt_token().
        The `@property` decorator above makes this possible. `token` is called
        a "dynamic property".
        """
        return self._generate_jwt_token()

    def get_full_name(self):
        """
        This method is required by Django for things like handling emails.
        Typically, this would be the user's first and last name. Since we do
        not store the user's real name, we return their username instead.
        """
        return self.username

    def get_short_name(self):
        """
        This method is required by Django for things like handling emails.
        Typically, this would be the user's first name. Since we do not store
        the user's real name, we return their username instead.
        """
        return self.username

    def _generate_jwt_token(self):
        """
        Generates a JSON Web Token that stores this user's ID and has an expiry
        date set to 60 days into the future.
        """
        dt = datetime.now() + timedelta(days=60)
        token = jwt.encode({
            'id': self.pk,
            # 'exp': int(dt.strftime('%s')),
            # 'exp': 999999999,
            'exp': dt.utcfromtimestamp(dt.timestamp()),
            'is_staff': self.is_staff,
            'user_group': self.profile.user_group.name if self.profile.user_group else None,
            'logged_on': str(datetime.now())
        }, settings.SECRET_KEY, algorithm='HS256')

        return token.decode('utf-8')
