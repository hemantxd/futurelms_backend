from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from core import models as core_models
from profiles.models import Profile
from django.conf import settings

User = get_user_model()

@receiver(post_save, sender=User)
def create_related_profile(sender, instance, created, *args, **kwargs):
    # Notice that we're checking for `created` here. We only want to do this
    # the first time the `User` instance is created. If the save that caused
    # this signal to be run was an update action, we know the user already
    # has a profile.
    user_group = core_models.UserGroup.objects.get_or_create(name="student")[0]
    if instance and created:
        fullname = instance.fullname.split(' ')
        if len(fullname) > 1:
            fname = None
            lname = fullname[-1]
            count = 0
            for name in fullname:
                if count < (len(fullname) - 1):
                    if not fname:
                        fname = name
                    else:
                        fname = fname + ' ' + name
                count += 1
            instance.profile = Profile.objects.create(user=instance, user_group=user_group, first_name=fname, last_name=lname)
        elif len(fullname) == 1:
            instance.profile = Profile.objects.create(user=instance, user_group=user_group, first_name=fullname[0])
        else:
            instance.profile = Profile.objects.create(user=instance, user_group=user_group)
        instance.profile.save()
