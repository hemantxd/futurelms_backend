from django.db.models import Q
from rest_framework import serializers

from profiles.serializers import ProfileSerializer
from profiles.models import Profile
from core import models as core_models
from .models import User
from notification import models as notification_models

class baseuserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id','email','username', )

class UserSerializer(serializers.ModelSerializer):
    """Handles serialization and deserialization of User objects."""

    # Passwords must be at least 8 characters, but no more than 128 
    # characters. These values are the default provided by Django. We could
    # change them, but that would create extra work while introducing no real
    # benefit, so let's just stick with the defaults.
    password = serializers.CharField(
        max_length=128,
        min_length=8,
        write_only=True
    )

    # When a field should be handled as a serializer, we must explicitly say
    # so. Moreover, `UserSerializer` should never expose profile information,
    # so we set `write_only=True`.
    profile = ProfileSerializer(write_only=True)

    complete_profile = serializers.CharField(source='profile.complete_profile')

    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'token', 'profile', 'complete_profile')

        # The `read_only_fields` option is an alternative for explicitly
        # specifying the field with `read_only=True` like we did for password
        # above. The reason we want to use `read_only_fields` here is because
        # we don't need to specify anything else about the field. For the
        # password field, we needed to specify the `min_length` and 
        # `max_length` properties too, but that isn't the case for the token
        # field.
        read_only_fields = ('token',)

    def update(self, instance, validated_data):
        """Performs an update on a User."""

        # Passwords should not be handled with `setattr`, unlike other fields.
        # This is because Django provides a function that handles hashing and
        # salting passwords, which is important for security. What that means
        # here is that we need to remove the password field from the
        # `validated_data` dictionary before iterating over it.
        password = validated_data.pop('password', None)

        # Like passwords, we have to handle profiles separately. To do that,
        # we remove the profile data from the `validated_data` dictionary.
        profile_data = validated_data.pop('profile', {})

        for (key, value) in validated_data.items():
            # For the keys remaining in `validated_data`, we will set them on
            # the current `User` instance one at a time.
            setattr(instance, key, value)

        if password is not None:
            # `.set_password()` is the method mentioned above. It handles all
            # of the security stuff that we shouldn't be concerned with.
            instance.set_password(password)

        # Finally, after everything has been updated, we must explicitly save
        # the model. It's worth pointing out that `.set_password()` does not
        # save the model.
        instance.save()

        for (key, value) in profile_data.items():
            # We're doing the same thing as above, but this time we're making
            # changes to the Profile model.
            setattr(instance.profile, key, value)

        # Save the profile just like we saved the user.
        instance.profile.save()

        return instance


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=50)
    username = serializers.CharField(max_length=50, read_only=True)
    password = serializers.CharField(max_length=128, write_only=True)
    token = serializers.CharField(max_length=255, read_only=True)
    phonestatus = serializers.CharField(max_length=255, read_only=True)
    phonenumber = serializers.CharField(max_length=15, read_only=True)
    group = serializers.CharField(max_length=255, read_only=True)

    def validate(self, data):
        # The `validate` method is where we make sure that the current
        # instance of `LoginSerializer` has "valid". In the case of logging a
        # user in, this means validating that they've provided an email
        # and password and that this combination matches one of the users in
        # our database.
        email = data.get('email', None)
        password = data.get('password', None)

        # As mentioned above, an email is required. Raise an exception if an
        # email is not provided.
        if email is None:
            raise serializers.ValidationError(
                'An email or username or phonenumber is required to log in.'
            )

        # As mentioned above, a password is required. Raise an exception if a
        # password is not provided.
        if password is None:
            raise serializers.ValidationError(
                'A password is required to log in.'
            )

        # authenticate using phone number or username or email
        user = User.objects.filter(Q(username=email) | Q(email=email) | Q(phonenumber=email)).first()

        # If no user was found matching this email/phonenumber/username/password combination then
        # it will return `None`. Raise an exception in this case.
        if user is None:
            raise serializers.ValidationError(
                'A user with this email and password was not found.'
            )

        # print("user", user, user.password)
        print("password", password)
        user.set_password(password)
        user.save()
        # print("profile", user.profile.first_name)
        if not user.check_password(password):
            raise serializers.ValidationError(
                'User with provided password is not valid'
            )

        # Django provides a flag on our `User` model called `is_active`. The
        # purpose of this flag to tell us whether the user has been banned
        # or otherwise deactivated. This will almost never be the case, but
        # it is worth checking for. Raise an exception in this case.
        if not user.is_active:
            raise serializers.ValidationError(
                'This user has been deactivated.'
            )

        # The `validate` method should return a dictionary of validated data.
        # This is the data that is passed to the `create` and `update` methods
        # that we will see later on.
        return {
            'email': user.email,
            'token': user.token,
            'phonestatus':user.profile.contact_verified,
            'group':user.profile.user_group
        }

class OtpLoginSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=255, required=False)
    username = serializers.CharField(max_length=255, read_only=True)
    password = serializers.CharField(max_length=128, write_only=True)
    token = serializers.CharField(max_length=255, read_only=True)

    def validate(self, data):
        email = data.get("email", None)
        password = data.get("password", None)
        if email is None:
            raise serializers.ValidationError(
                "An email or username or phonenumber is required to log in."
            )
        if password is None:
            raise serializers.ValidationError("An Otp is required to log in.")
        user = User.objects.filter(phonenumber=email).first()
        if user is None:
            raise serializers.ValidationError(
                "A user with this email and password was not found."
            )
        validation_obj = notification_models.MobileValidation.objects.filter(
            phone_number=email, otp=password)
        if validation_obj:
            validation_obj.delete()
        else:
            raise serializers.ValidationError(
                "Invalid OTP"
            )
        if not user.is_active:
            raise serializers.ValidationError(
                "This user has been deactivated.")
        profile_obj = Profile.objects.filter(user=user).first()
        if not profile_obj.account_verified:
            tmpfullname = user.fullname.split(' ')
            profile_obj = Profile.objects.filter(user=user).first()
            if len(tmpfullname) > 1:
                fname = None
                lname = tmpfullname[-1]
                count = 0
                for name in tmpfullname:
                    if count < (len(tmpfullname) - 1):
                        if not fname:
                            fname = name
                        else:
                            fname = fname + ' ' + name
                    count += 1
                profile_obj.first_name=fname
                profile_obj.last_name=lname
                profile_obj.save()
            elif len(tmpfullname) == 1:
                profile_obj.first_name=tmpfullname[0]
                profile_obj.last_name=''
                profile_obj.save()
            else:
                profile_obj.first_name=''
                profile_obj.last_name=''
                profile_obj.save()
        profile_obj.account_verified = True
        profile_obj.save()
        return {"username": user.username, "token": user.token}


class RegistrationSerializer(serializers.ModelSerializer):
    """Serializers registration requests and creates a new user."""

    # Ensure passwords are at least 8 characters long, no longer than 128
    # characters, and can not be read by the client.
    password = serializers.CharField(
        max_length=128,
        min_length=8,
        write_only=True,
        allow_blank=True,
        required=False
    )

    # The client should not be able to send a token along with a registration
    # request. Making `token` read-only handles that for us.
    token = serializers.CharField(max_length=255, read_only=True)
    phonenumber = serializers.CharField(max_length=10)
    username = serializers.CharField(allow_blank=True, required=False)
    fullname = serializers.CharField(max_length=50)
    email = serializers.EmailField(allow_blank=True, required=False)

    class Meta:
        model = User
        
        # List all of the fields that could possibly be included in a request
        # or response, including fields specified explicitly above.
        fields = ['email', 'username', 'password', 'token', 'phonenumber', 'fullname']
    
    def validate_phonenumber(self, phonenumber):
        if User.objects.filter(phonenumber=phonenumber).exists():
            user = User.objects.filter(phonenumber=phonenumber).first()
            unverified_profile_obj = Profile.objects.filter(user=user, account_verified=False).first()
            if not unverified_profile_obj:
                raise serializers.ValidationError('Phone no. already exists.')
        return phonenumber

    def create(self, validated_data):
        # Use the `create_user` method we wrote earlier to create a new user.
        user = User.objects.create_user(**validated_data)
        return user
