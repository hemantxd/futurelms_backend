from ast import mod
from courses.models import ExamDomain
import uuid
from django.db import models
from countrystatecity import models as countrystatecity_models
from core import models as core_models

gender = (
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other')
)

qualification_type = (
    ('10th', '10th'),
    ('12th', '12th'),
    ('graduation', 'Graduation'),
    ('postgraduation', 'Post Graduation'),
    ('other', 'Other'),
)

def image_upload_to(instance, filename):
    uid = str(uuid.uuid4())
    ext = filename.split(".")[-1].lower()
    return "profile-images/{}/{}.{}".format(instance.pk, uid, ext)

class State(core_models.TimestampedModel):
    name = models.CharField(max_length=100, blank=True, null=True)
    total_cities = models.IntegerField(blank=False,null=False,default=0)
    identifier = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}".format(self.name)

class City(core_models.TimestampedModel):
    state = models.ForeignKey(State, on_delete = models.CASCADE, blank = True)
    name = models.CharField(max_length=100, blank=True, null=True)
    identifier = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}-{}".format(self.name, self.state.name)

class Institute(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    website = models.CharField(max_length=100, blank=True, null=True)
    head = models.CharField(max_length=100, blank=True, null=True)
    head_contact_no = models.CharField(max_length=12, null=True, blank=True)
    is_verified = models.BooleanField(default=True)
    registered = models.BooleanField(default=0, help_text='field to identify institutes which are '
                                                          'registered by institute manager')
    school_code = models.CharField(max_length=150, null=True, blank=True, unique=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE, blank=True, null=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, blank=True, null=True)
    street = models.CharField(max_length=200, blank=True, null=True)
    pin = models.CharField(max_length=100, blank=True, null=True)
    created_on = models.DateField(auto_now_add=True)
    updated_on = models.DateField(auto_now=True)    

    def __str__(self):
        return self.name

    def is_registered(self):
        return self.registered

class Profile(core_models.TimestampedModel):
    user = models.OneToOneField('authentication.User', on_delete=models.CASCADE, related_name="profile")
    
    first_name = models.TextField(blank=True)

    last_name = models.TextField(blank=True, null=True)

    designation = models.CharField(max_length=200, blank=True, null=True)

    father_name=models.CharField(max_length=200,blank=True ,null=True)
    whats_app=models.CharField(max_length=200,blank=True ,null=True)
    dob=models.CharField(max_length=200,blank=True ,null=True)
    adhar_no=models.CharField(max_length=200,blank=True ,null=True)
    address=models.CharField(max_length=200,blank=True ,null=True)
    sr_number=models.CharField(max_length=200,blank=True,null=True)
    #branch_id=models.CharField(max_length=50,blank=True,null=True)

    user_group = models.ForeignKey(core_models.UserGroup, on_delete=models.CASCADE, null=True, blank=True)

    #address = models.TextField(blank=True)

    image = models.ImageField(upload_to=image_upload_to, blank=True)

    contact_verified = models.BooleanField(default=False)

    account_verified = models.BooleanField(default=False)

    studentClass = models.ForeignKey(core_models.UserClass, on_delete=models.CASCADE, null=True, blank=True)

    studentBoard = models.ForeignKey(core_models.UserBoard, on_delete=models.CASCADE, null=True, blank=True)

    rollno = models.TextField(blank=True)

    pincode = models.IntegerField(blank=True, null=True)

    complete_profile = models.BooleanField(default=False)
    interested_domains = models.ManyToManyField(ExamDomain, blank=True, null=True)
    state = models.ForeignKey(State, on_delete = models.CASCADE, null=True, blank = True)
    city = models.ForeignKey(City, on_delete = models.CASCADE, null=True, blank = True)
    institute = models.ForeignKey(Institute, related_name='institute', on_delete=models.CASCADE, null=True, blank=True)
    logout_updated_on = models.DateTimeField(auto_now=True)
    gender = models.CharField(max_length=10, choices = gender, blank=True, null=True)
    qualification = models.CharField(max_length=50, choices = qualification_type, blank=True, null=True)
    

    # def __str__(self):
    #     return self.user.email

    # def full_name(self):
    #     return ("{} {}".format(self.first_name, self.last_name))