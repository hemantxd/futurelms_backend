from email.policy import default
from django.db import models
# Create your models here.
from authentication.models import *
from core.models import *
from profiles.models import *
import uuid
from content import models as content_models
from courses import models as courses_models

#https://backend.makemypath.app/api/updateprofile/  **test url for development branch**


class Communication(models.Model):
    #user=models.ForeignKey(User,on_delete=models.CASCADE,null=True,blank=True)
    profile = models.ForeignKey(Profile,on_delete=models.CASCADE,null=True,blank=True)
    batch = models.ForeignKey(content_models.Batch,on_delete=models.CASCADE,blank=True,null=True)
    message = models.CharField(max_length=500,blank=True,null=True)
    is_visible = models.BooleanField(default=False)
    sent_time = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return self.message


class BatchThird(models.Model):
    teacher = models.ManyToManyField(User, blank=True, null=True,related_name="teacher_name")
    name = models.CharField(max_length=100, blank=True, null=True)
    batch_code = models.CharField(max_length=20, blank=True, null=True, unique=True)
    students = models.ManyToManyField(User, related_name="thirdstudents", blank=True)
    is_active = models.BooleanField(default=True)
    grade = models.ForeignKey(UserClass, on_delete = models.CASCADE, blank = True,null=True)
    unique_id = models.CharField(max_length=20, blank=True, null=True)
    institute_room = models.ForeignKey(content_models.InstituteClassRoom, on_delete = models.CASCADE, blank = True, null=True)

    def __str__(self):
        return str(self.unique_id)

class APIKeysForVerify(models.Model):
    keyvalues=models.CharField(max_length=500,blank=True,null=True)
    is_active=models.BooleanField(default=True)

    def __str__(self):
        return str(self.keyvalues)


class BarBloomLevel(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,blank=True,null=True)
    title = models.ForeignKey(courses_models.BloomLevel,on_delete=models.CASCADE,blank=True,null=True)
    bloom_level = models.IntegerField(default=0,blank=True,null=True)
    #bloom_name = models.CharField(max_length=20,blank=True,null=True)


    def __str__(self):
         return (self.title.title)


class BloomLevelValues(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,blank=True,null=True)
    exam = models.ForeignKey(courses_models.Exam, on_delete = models.CASCADE, blank = True, null=True)
    papers =  models.ManyToManyField(content_models.LearnerPapers, blank=True, null=True)
    memory_based = models.IntegerField(default=0,blank=True,null=True)
    conceptual = models.IntegerField(default=0,blank=True,null=True)
    application = models.IntegerField(default=0,blank=True,null=True)
    analyze = models.IntegerField(default=0,blank=True,null=True)
    evaluate = models.IntegerField(default=0,blank=True,null=True)
    unique_values = models.CharField(max_length=20,null=True,blank=True)
    total_question = models.IntegerField(default=0,null=True,blank=True)

    def __str__(self):
        return (self.user.username)

class OverAllBloomLevelValues(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,blank=True,null=True)
    memory_based = models.IntegerField(default=0,blank=True,null=True)
    conceptual = models.IntegerField(default=0,blank=True,null=True)
    application = models.IntegerField(default=0,blank=True,null=True)
    analyze = models.IntegerField(default=0,blank=True,null=True)
    evaluate = models.IntegerField(default=0,blank=True,null=True)
    unique_values = models.CharField(max_length=20,null=True,blank=True)
    total_question = models.IntegerField(default=0,null=True,blank=True)

    def __str__(self):
        return (self.unique_values)


# class LearnerExamPaperHistory(core_models.TimestampedModel):
#     user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
#     questions = models.ManyToManyField(Question, blank=True)
#     exam = models.ForeignKey(courses_models.Exam, on_delete = models.CASCADE, blank = True, null=True)
#     papers =  models.ManyToManyField(LearnerPapers, blank=True, null=True)
#     score =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
#     total_marks =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
#     percentage = models.IntegerField(blank=False,null=False,default=0)
#     total_time = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
#     time_taken = models.IntegerField(blank=False,null=False,default=0)
#     total_questions = models.IntegerField(blank=False,null=False,default=0)
#     attempted = models.IntegerField(blank=False,null=False,default=0)
#     skipped = models.IntegerField(blank=False,null=False,default=0)
#     correct = models.IntegerField(blank=False,null=False,default=0)
#     unchecked = models.IntegerField(blank=False,null=False,default=0)
#     incorrect = models.IntegerField(blank=False,null=False,default=0)

#     def __str__(self):
#         return "{}-{}".format(self.user.username, self.exam.title)

# class UserClassRoom(models.Model):
#     user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True,related_name="userclass")
#     institute_rooms = models.ManyToManyField(content_models.InstituteClassRoom, blank=True, null=True)
#     branch = models.ForeignKey(content_models.BranchSchool,on_delete = models.CASCADE,blank =True ,null =True)

#     def __str__(self):
#         return str(self.institute_rooms)
       


#unused models beacuse of checking data flow  and also define to content models


# SEASSON_CHOICES=(
	

# ('1' ,'2021-2022'),
# ('2' ,'2022-2023'),
# ('3' ,'2023-2024'),
# ('4' ,'2024-2025'),
# )

# class BranchSchool(models.Model):
#     user=models.ForeignKey(User,on_delete=models.CASCADE)
#     school=models.ForeignKey(Institute,on_delete=models.CASCADE,related_name="schoolbranch")
#     branch_name=models.CharField(default="",max_length=100)

#     def __str__(self):
#         return self.branch_name

# class SchoolSeasson(models.Model):
#     schoolbranch=models.ForeignKey(BranchSchool,on_delete=models.CASCADE)
#     seassion_name=models.CharField(choices=SEASSON_CHOICES,max_length=50,default='1')

#     def __str__(self):
#         return self.seassion_name
    
#     # @property
#     # def seassion_name(self):
#     #     return self.get_seassion_name_display()


# class InstituteClassRoom(models.Model):
#     """
#     Model to store name of the classes
#     """
#     #institute = models.ForeignKey(SchoolInstitute, on_delete = models.CASCADE, blank = True)
#     branch=models.ForeignKey(BranchSchool,on_delete=models.CASCADE ,blank = True,null = True)
#     grade = models.ForeignKey(UserClass, on_delete = models.CASCADE, blank = True,related_name="userclass")
#     name = models.CharField(max_length=50)
#     blocked_students = models.ManyToManyField(User, related_name="blocked_students_by_school", blank=True)
#     room_teacher = models.ForeignKey(User, on_delete = models.CASCADE, blank=True, null=True, related_name="room_teacher")

#     def __str__(self):
#         return  ("{} - {}".format(self.branch.school.name, self.name))


# class UserClassRoom(models.Model):
#     user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True,related_name="userclass")
#     institute_rooms = models.ManyToManyField(InstituteClassRoom, blank=True, null=True)

#     def __str__(self):
#         return str(self.institute_rooms)
#        # return  ("{} - {}".format(self.institute.name, self.name))

# class LearnerBatches(models.Model):
#     user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True,related_name="learner")
#     batch = models.ForeignKey(Batch, on_delete = models.CASCADE, blank=True, null=True)
#     is_active = models.BooleanField(default=True)

#     def __str__(self):
#         return "{}-{}".format(self.user.username, self.batch.name)


# class StudentInstituteChangeInvitation(models.Model):
#     user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True,related_name="change")
#     inviting_institute_room = models.ForeignKey(InstituteClassRoom, on_delete = models.CASCADE, blank=True, null=True)

#     def __str__(self):
#         return "User: {}  Room: {}".format(self.user, self.inviting_institute_room)




# class Profile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="schoolprofile")
    
#     first_name = models.TextField(blank=True)

#     last_name = models.TextField(blank=True, null=True)

#     designation = models.CharField(max_length=200, blank=True, null=True)
#     father_name=models.CharField(max_length=200,blank=True ,null=True)
#     whats_app=models.CharField(max_length=200,blank=True ,null=True)
#     dob=models.CharField(max_length=200,blank=True ,null=True)
#     adhar_no=models.CharField(max_length=200,blank=True ,null=True)
#     address=models.CharField(max_length=200,blank=True ,null=True)
#     sr_number=models.CharField(max_length=200,blank=True,null=True)
#     section=models.ForeignKey(InstituteClassRoom,on_delete=models.CASCADE,null=True,blank=True)

#     user_group = models.ForeignKey(UserGroup, on_delete=models.CASCADE, null=True, blank=True)

#     image = models.ImageField(upload_to=image_upload_to, blank=True)

#     contact_verified = models.BooleanField(default=False)

#     account_verified = models.BooleanField(default=False)

#     studentClass = models.ForeignKey(UserClass, on_delete=models.CASCADE, null=True, blank=True)

#     studentBoard = models.ForeignKey(UserBoard, on_delete=models.CASCADE, null=True, blank=True)

#     rollno = models.TextField(blank=True)

#     pincode = models.IntegerField(blank=True, null=True)

#     complete_profile = models.BooleanField(default=False)
#    # interested_domains = models.ManyToManyField(ExamDomain, blank=True, null=True)
#     state = models.ForeignKey(State, on_delete = models.CASCADE, null=True, blank = True)
#     city = models.ForeignKey(City, on_delete = models.CASCADE, null=True, blank = True)
#     institute = models.ForeignKey(Institute, related_name='schoolinstitute', on_delete=models.CASCADE, null=True, blank=True)
#     logout_updated_on = models.DateTimeField(auto_now=True)
#     gender = models.CharField(max_length=10, choices = gender, blank=True, null=True)
#     qualification = models.CharField(max_length=50, choices = qualification_type, blank=True, null=True)


#     def __str__(self):
#         return self.father_name

    # def full_name(self):
    #     return ("{} {}".format(self.first_name, self.last_name))


# class UploadFile(models.Model):
#     file=models.FileField(upload_to='file')

#     def __str__(self):
#         return str(self.file)


# class SchoolClassSection(models.Model):
#     schoolclass=models.ForeignKey(UserClass, on_delete=models.CASCADE, null=True, blank=True)
#     section_name=models.CharField(max_length=20,blank=True,null=True)
#     schoolseasson=models.ForeignKey(SchoolSeasson,on_delete=models.CASCADE)

#     def __str__(self):
#         return self.section_name


# class School(models.Model):
#     school_name=models.CharField(default="",max_length=100)

#     def __str__(self):
#         return self.school_name

