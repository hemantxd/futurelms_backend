import datetime
import hashlib
import os

from django.db import models
from django.conf import settings
from courses.models import Exam
from notification import utils as notification_utils
from core import models as core_models
from authentication.models import User
from profiles.models import Institute
import uuid
from content.models import Batch, MentorPapers, Question

def image_upload_to(instance, filename):
    uid = str(uuid.uuid4())
    ext = filename.split(".")[-1].lower()
    return "course-images/{}/{}.{}".format(instance.pk, uid, ext)

class MobileValidation(models.Model):
    phone_number = models.CharField(max_length=15, blank=True)
    otp = models.CharField(max_length=40)
    timestamp = models.DateTimeField(auto_now_add=True)
    attempts = models.IntegerField(default=0)
    used = models.BooleanField(default=False)


    def __str__(self):
        return "{} - {}".format(self.phone_number, self.otp)

    @classmethod
    def create_otp_for_number(cls, number):
        # The max otps generated for a number in a day are only 10.
        # Any more than 10 attempts returns False for the day.
        # today_min = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        # today_max = datetime.datetime.combine(datetime.date.today(), datetime.time.max)
        # otps = cls.objects.filter(phone_number=number, timestamp__range=(today_min, today_max))
        # if otps.count() <= getattr(settings, 'PHONE_LOGIN_ATTEMPTS', 10):
        #     otp = cls.generate_otp(length=getattr(settings, 'PHONE_LOGIN_OTP_LENGTH', 6))
        #     phone_token = MobileValidation(phone_number=number, otp=otp)
        #     phone_token.save()
        #     message = "{0} is the Onetime password (OTP) for Account verification. This is usable only once. Please DO NOT SHARE WITH ANYONE.".format(otp)
        #     success, errors  = notification_utils.SmsMessage(number, message)
        #     if number not in success:
        #         return False
        #     return phone_token
        # else:
        #     return False
        old_token = MobileValidation.objects.filter(phone_number=number)
        if old_token:
            otp = old_token[0].otp
        else:
            otp = cls.generate_otp(length=getattr(settings, 'PHONE_LOGIN_OTP_LENGTH', 6))
        phone_token = MobileValidation(phone_number=number, otp=otp)
        phone_token.save()


        # need to integrate SMS provider

        message = "{0} is the Onetime password (OTP) for login. This is usable only once. Please DO NOT SHARE WITH ANYONE. ERDRCL ".format(otp)
        
        success  = notification_utils.SmsMessage(number, 'ERDRCL',message, '2factor')
        count = 0
        # if str(number) not in success:
        #     return False
        for val in success:
            if (len(val) > 0) and (number == val[0]):
                count += 1
        if count == 0:
            return False
        return phone_token

    @classmethod
    def generate_otp(cls, length=6):
        hash_algorithm = getattr(settings, 'PHONE_LOGIN_OTP_HASH_ALGORITHM', 'sha256')
        m = getattr(hashlib, hash_algorithm)()
        m.update(getattr(settings, 'SECRET_KEY', None).encode('utf-8'))
        m.update(os.urandom(16))
        otp = str(int(m.hexdigest(), 16))[-length:]
        return otp

class NotificationType(core_models.TimestampedModel):
    name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return "{}-{}".format(self.name, self.description)

class Notifications(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, blank=True, null=True)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, blank=True, null=True)
    mentor_paper = models.ForeignKey(MentorPapers, on_delete=models.CASCADE, blank=True, null=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, blank=True, null=True)
    subject = models.CharField(max_length=150, blank=True, null=True)
    notification = models.TextField()
    type = models.ForeignKey(NotificationType, on_delete=models.CASCADE, default=None)
    is_read = models.BooleanField(default=False)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, null=True, blank=True)
    image = models.ImageField(upload_to=image_upload_to, blank=True, null=True)

    def __str__(self):
        return "{}-{}".format(self.user, self.notification)

    class Meta:
        ordering = ['-created_at']

