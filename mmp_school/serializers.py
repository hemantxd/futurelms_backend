from email.policy import default
import imp
from logging.config import valid_ident

from requests import request

import content
from .models import *
from rest_framework import fields
from rest_framework.serializers import ModelSerializer, FloatField,Serializer, CharField, ImageField, SerializerMethodField,EmailField,DateField
import random
from rest_framework.fields import EmailField, Field, IntegerField
from rest_framework.exceptions import APIException
from django.core.exceptions import ValidationError
from core.models import *
from profiles.models import *
from rest_framework import serializers
from content import models as content_models
from courses import models as courses_models
from courses import serializers as course_seri


class SchoolSerializer(ModelSerializer):
    class Meta:
        model = Institute
        fields = ['id','name']

class SchoolBranchSerializer(ModelSerializer):
    class Meta:
        model=content_models.BranchSchool
        fields='__all__'

class SchoolSeassonSerializer(ModelSerializer):
    school_name=SerializerMethodField()
    seassion_name = SerializerMethodField()
    #schoolbranch = SerializerMethodField()
    def get_school_name(self,instance):
        return instance.schoolbranch.school.name
    
    def get_seassion_name(self,instance):
        return instance.get_seassion_name_display()
    
    # def get_schoolbranch(self,instance):
    #     return instance.get_schoolbranch_display()

    class Meta:
        model=content_models.SchoolSeasson
        fields=['id','school_name','seassion_name','schoolbranch']

class SeassonClassSerializer(ModelSerializer):
    class Meta:
        model=UserSeasson
        fields='__all__'

class SchoolUserClassSerializer(ModelSerializer):
    # school_name=SerializerMethodField()
    # total_student_school=SerializerMethodField()
    total_student_class=SerializerMethodField()
    total_section=SerializerMethodField()

    # def get_school_name(self,instance):
    #     try:
    #         x=content_models.BranchSchool.objects.filter(user=self.context['request'].user)
    #         print(x,"hello")
    #         if x.exists():
    #             return x.name
    #         else:
    #             return "False"
    #     except Exception as e:
    #         return str(e)

    def get_total_student_class(self,instance):
        return "15"

    def get_total_section(self,instance):
        return "3"
   
    class Meta:
        model=UserClass
        fields='__all__'
        include=['total_student_class','total_section']

class StudentListSearchSerializer(ModelSerializer):
    class Meta:
        model=User
        fields=['fullname','phonenumber']


class MentorListSearchSerializer(ModelSerializer):
    fullname=SerializerMethodField()
    phonenumber=SerializerMethodField()
    username=SerializerMethodField()

    def get_fullname(self,instance):
        return instance.user.fullname
    def get_username(self,instance):
        return instance.user.username
    def get_phonenumber(self,instance):
        return instance.user.phonenumber

    class Meta:
        model=Profile
        fields='__all__'
        include=['fullname','phonenumber','username']

class StudentListSearchSerializerProfile(ModelSerializer):
    fullname=SerializerMethodField()
    phonenumber=SerializerMethodField()

    def get_fullname(self,instance):
        return instance.user.fullname
    
    def get_phonenumber(self,instance):
        return instance.user.phonenumber

    class Meta:
        model=Profile
        fields=['user','fullname','phonenumber']


class StudentListSearchSerializerProfile1(ModelSerializer):

    class Meta:
        model = content_models.Batch
        fields = ('id','is_active','name', 'batch_code', 'institute_room', 'students')


class CreateInstituteRoomSerializer(serializers.ModelSerializer):
    #institute = serializers.PrimaryKeyRelatedField(
        #queryset=SchoolInstitute.objects.all(), required=False)
    grade = serializers.PrimaryKeyRelatedField(
        queryset=UserClass.objects.all(), required=False)
    branch = serializers.PrimaryKeyRelatedField(
        queryset=content_models.BranchSchool.objects.all(), required=False)

    class Meta:
        model = content_models.InstituteClassRoom
        fields = [#"institute",
                  "grade",
                  "name",
                  "branch"
                  ]

    def create(self, validated_data):
        #institute = validated_data.get('institute')
        grade = validated_data.get('grade')
        name = validated_data.get('name')
        branch = validated_data.get('branch')

        try:
            room_obj = content_models.InstituteClassRoom.objects.get(
               # institute=institute,
                grade=grade,
                name=name,
                branch=branch
            )
        except:
            room_obj = None

        if not room_obj:
            room_obj = content_models.InstituteClassRoom.objects.create(
           # institute=institute,
            grade=grade,
            name=name,
            branch=branch
        )
        else:
            raise serializers.ValidationError(
                    "Room already present from this name")

        return room_obj

class ViewInstituteClassRoomSerializer(serializers.ModelSerializer):
    institute_name = serializers.SerializerMethodField()
    grade_name = serializers.SerializerMethodField()
    branch = serializers.SerializerMethodField()
    branch_id=serializers.SerializerMethodField()
    #blocked_students = serializers.SerializerMethodField()
    #room_teacher_name = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()
    mentors_count = serializers.SerializerMethodField()

    class Meta:
        model = content_models.InstituteClassRoom
        
        #fields = ('id', 'institute_name', 'grade_name', 'name', 'blocked_students', 'students_count', 'mentors_count', 'room_teacher_name', 'room_teacher', 'created_at')
        fields=('id','institute_name','grade_name','name','branch','branch_id','students_count','mentors_count','is_active','created_at')

    def get_institute_name(self, instance):
        try:
            return instance.branch.school.name
        except:
            return None
    def get_branch(self,instance):
        try:
            return instance.branch.branch_name
        except:
            return None

    def get_branch_id(self,instance):
        try:
            return instance.branch.id
        except:
            return None

    # def get_room_teacher_name(self, instance):
    #     if instance.room_teacher:
    #         try:
    #             return instance.room_teacher.profile.first_name + ' ' + instance.room_teacher.profile.last_name
    #         except:
    #             return instance.room_teacher.profile.first_name
    #     else:
    #         None

    def get_grade_name(self, instance):
        return instance.grade.name

    def get_mentors_count(self, instance):
        return content_models.Batch.objects.filter(institute_room__id=instance.id).count()

    def get_students_count(self, instance):
        return content_models.UserClassRoom.objects.filter(institute_rooms=instance).count()

    # def get_blocked_students(self, instance):
    #     try:
    #         userIds = []
    #         userIds = [user.id for user in instance.blocked_students.all()]
    #         blocked_students = ShortProfileSerializer(Profile.objects.filter(user__in=userIds), many=True).data
    #     except:
    #         blocked_students = []
    #     return blocked_students


class ViewBatchClassSectionSerializer(serializers.ModelSerializer):
    teacher_username = serializers.SerializerMethodField()
    teacherid = serializers.SerializerMethodField()
    teacher_email = serializers.SerializerMethodField()
    teacher_full_name = serializers.SerializerMethodField()
    profile_pic = serializers.SerializerMethodField()
    institute_room = serializers.SerializerMethodField()
    batch_id = serializers.SerializerMethodField()

    class Meta:
        model = content_models.Batch
        fields = ('batch_id', 'teacher_username', 'profile_pic', 'teacherid', 'is_active', 'teacher_email', 'teacher_full_name', 'name', 'batch_code', 'institute_room',)
    
    def get_batch_id(self, instance):
        try:
            return instance.id
        except:
            return None

    def get_profile_pic(self, instance):
        try:
            return instance.teacher.profile.image.url
        except:
            return None

    def get_teacher_username(self, instance):
        return instance.teacher.username
    
    def get_teacherid(self, instance):
        return instance.teacher.id

    def get_teacher_email(self, instance):
        return instance.teacher.email

    def get_teacher_full_name(self, instance):
        try:
            return instance.teacher.profile.first_name + ' ' + instance.teacher.profile.last_name
        except:
            return instance.teacher.profile.first_name

    def get_institute_room(self, instance):
        try:
            institute_room = ViewInstituteClassRoomSerializer(instance.institute_room).data
        except:
            institute_room = None
        return institute_room

class ViewBatchSerializer(serializers.ModelSerializer):
    teacher_username = serializers.SerializerMethodField()
    teacherid = serializers.SerializerMethodField()
    teacher_email = serializers.SerializerMethodField()
    teacher_full_name = serializers.SerializerMethodField()
    profile_pic = serializers.SerializerMethodField()
    institute_room = serializers.SerializerMethodField()
    teacher_phonenumber = serializers.SerializerMethodField()

    class Meta:
        model = content_models.Batch
        fields = ('id', 'teacher_username','teacher_phonenumber', 'profile_pic', 'teacherid', 'is_active', 'teacher_email', 'teacher_full_name', 'name', 'batch_code', 'institute_room', 'students')

    def get_profile_pic(self, instance):
        try:
            return instance.teacher.profile.image.url
        except:
            return None

    def get_teacher_username(self, instance):
        return instance.teacher.username
    
    def get_teacher_phonenumber(self, instance):
        try:
            return instance.teacher.phonenumber
        except:
            return None
    
    def get_teacherid(self, instance):
        return instance.teacher.id

    def get_teacher_email(self, instance):
        return instance.teacher.email

    def get_teacher_full_name(self, instance):
        try:
            return instance.teacher.profile.first_name + ' ' + instance.teacher.profile.last_name
        except:
            return instance.teacher.profile.first_name

    def get_institute_room(self, instance):
        try:
            institute_room = ViewInstituteClassRoomSerializer(instance.institute_room).data
        except:
            institute_room = None
        return institute_room

class CreateBatchSerializer(serializers.ModelSerializer):

    class Meta:
        model = content_models.Batch
        fields = ('id', 'teacher', 'name', 'batch_code', 'students')

    def create(self, validated_data):
        teacher = self.context.get(
                'request').user
        name = validated_data.get('name')

        batch_obj = content_models.Batch.objects.create(
            teacher=teacher,
            name=name,
            is_active=True
        )
        batch_obj.batch_code = uuid.uuid4().hex[:6].upper()
        batch_obj.save()
     
        return batch_obj


class LearnerBatchSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    userid = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    batch = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerBatches
        fields = ('id', 'username', 'userid', 'email', 'is_active', 'full_name', 'batch', 'created_at', 'updated_at')

    def get_username(self, instance):
        return instance.user.username
    
    def get_userid(self, instance):
        return instance.user.id

    def get_email(self, instance):
        return instance.user.email

    def get_full_name(self, instance):
        try:
            return instance.user.profile.first_name + ' ' + instance.user.profile.last_name
        except:
            return instance.user.profile.first_name
    
    def get_batch(self, instance):
        try:
            batch = ViewBatchSerializer(instance.batch).data
        except:
            batch = None
        return batch

    def create(self, validated_data):
        user = self.context.get(
                'request').user
        try:
            batch = self._context.get("request").data['batch']
        except:
            batch = None

        try:
            batch_obj = content_models.Batch.objects.get(id=batch)
        except:
            raise serializers.ValidationError(
                    "Please select valid batch")
        if len(batch_obj.students.all()) >= 250:
            raise serializers.ValidationError(
                    "Maximum 250 students are allowed in a batch")
        try:
            blocked_obj = content_models.LearnerBlockedBatches.objects.get(user=user, batch=batch_obj)
        except:
            blocked_obj = None
        if blocked_obj:
            raise serializers.ValidationError(
                    "You have been blocked from this batch")
        try:
            content_models.LearnerBatchHistory.objects.get(user=user, batch=batch_obj)
        except:
            content_models.LearnerBatchHistory.objects.create(user=user, batch=batch_obj)

        try:
            learner_batch_obj = content_models.LearnerBatches.objects.get(user=user, batch=batch_obj)
        except:
            learner_batch_obj = None
        
        if not learner_batch_obj:
            learner_batch_obj = content_models.LearnerBatches.objects.create(user=user, batch=batch_obj)
        else:
            raise serializers.ValidationError(
                    "Batch already joined")
        batch_obj.students.add(user)
        batch_obj.save()
        return learner_batch_obj


class LearnerBlockedBatchSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    userid = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    batch = serializers.SerializerMethodField()
    father_name = serializers.SerializerMethodField()
    dob = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerBlockedBatches
        fields = ('id', 'username', 'userid', 'contact', 'email', 'full_name','father_name','dob','batch')

    def get_username(self, instance):
        return instance.user.username

    def get_contact(self, instance):
        return instance.user.phonenumber
    
    def get_userid(self, instance):
        return instance.user.id

    def get_email(self, instance):
        return instance.user.email

    def get_full_name(self, instance):
        try:
            return instance.user.profile.first_name + ' ' + instance.user.profile.last_name
        except:
            return instance.user.profile.first_name

    def get_father_name(self, instance):
        try:
            return instance.user.profile.father_name 
        except:
            return None

    def get_dob(self, instance):
        try:
            return instance.user.profile.dob
        except:
            return None
    
    def get_batch(self, instance):
        try:
            batch = ViewBatchSerializer(instance.batch).data
        except:
            batch = None
        return batch


class ViewUserClassRoomSerializer(serializers.ModelSerializer):
    institute_rooms = ViewInstituteClassRoomSerializer(many=True, required=False)
    full_name = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    father_name = serializers.SerializerMethodField()
    dob = serializers.SerializerMethodField()

    class Meta:
        model = content_models.UserClassRoom
        fields = ('id', 'institute_rooms', 'user', 'full_name', 'username','father_name','dob')

    def get_full_name(self, instance):
        try:
            return instance.user.profile.first_name + ' ' + instance.user.profile.last_name
        except:
            return instance.user.profile.first_name

    def get_father_name(self, instance):
        try:
            return instance.user.profile.father_name 
        except:
            return None

    def get_dob(self, instance):
        try:
            return instance.user.profile.dob
        except:
            return None
    
    def get_username(self, instance):
        return instance.user.username

class StudentRegisterSerializer(Serializer):
    stu_name = CharField(error_messages={'required':'student name  is required', 'blank':'student name  is required'},max_length=400)
    phonenumber = CharField(error_messages={'required':'phonenumber is required', 'blank':'phonenumber is required'},max_length=400)
    father_name = CharField(error_messages={'required':'father_name is required', 'blank':'father_name  is required'},max_length=20)
   # whats_app = CharField(error_messages={'required':'whats_app number is required', 'blank':'whats_app number is required'},max_length=400)
    whats_app=serializers.CharField(required=False,allow_blank=True)
    dob = CharField(error_messages={'required':'dob is required', 'blank':'dob is required'},max_length=100)
    adhar_no=CharField(error_messages={'required':'adhar_no is required', 'blank':'adhar_no is required'})
   # address=CharField(error_messages={'required':'address is required', 'blank':'address is required'},max_length=5000)
    whats_app=serializers.CharField(required=False,allow_blank=True)
    sr_number=CharField(error_messages={'required':'sr_number is required', 'blank':'sr_number is required'},max_length=10)
    
    userclass_id=CharField(error_messages={'required':'userclass is required','blank':'userclass is required'},max_length=100)
    section_id=CharField(error_messages={'required':'section is required','blank':'section is required'},max_length=100)
    branch_id=CharField(error_messages={'required':'branch_id is required','blank':'branch_id is required'},max_length=100)


    def validate(self, data):
        phonenumber = data.get('phonenumber')
        adhar_no=data.get('adhar_no')
        if User.objects.filter(phonenumber=phonenumber).exists():
            raise ValidationError('phonenumber allready exists')
        if Profile.objects.filter(adhar_no=adhar_no).exists():
            raise ValidationError('adhar_no allready exists')

        return data

    def create(self,validated_data):
        dob=self.validated_data['dob']
        # dob=dob.split("/")
        # dobO1=dob[2]+"-"+dob[1]+"-"+dob[0]
        # dobO=datetime.strptime(dobO1,'%Y-%m-%d')
        last_user_created_id = User.objects.all().last().id
        username = create_username(str(10000 + last_user_created_id))
        stu_name=self.validated_data['stu_name']
        phonenumber=self.validated_data['phonenumber']

        father_name = self.validated_data['father_name']
        whats_app='1234567890'
        adhar_no = self.validated_data['adhar_no']
        address = 'kanpur'
        branch_id=self.validated_data['branch_id']
        sr_number = self.validated_data['sr_number']
        userclass_id = self.validated_data['userclass_id']
        section_id = self.validated_data['section_id']
        #institute_id=self.validated_data['institute_id']
        clsss=UserClass.objects.get(id=userclass_id)
        section=content_models.InstituteClassRoom.objects.get(id=section_id)
        user_group=UserGroup.objects.get(name='student')
        print("&&&&&&&",user_group)
        #institute=SchoolInstitute.objects.get(id=institute_id)

        user_obj = User.objects.create(username=username,phonenumber=phonenumber,fullname=stu_name)
        user_obj.set_password(username)
        user_obj.save()
        print("*********************",user_obj)
        print("*********************",user_obj.id)
        profileO=Profile.objects.get(user=user_obj)
        print(profileO,"BBBBBBBB************NNNNNNNNNNN")
        profileO.father_name=father_name
        profileO.whats_app=whats_app
        profileO.adhar_no=adhar_no
        profileO.address=address
        profileO.sr_number=sr_number
        profileO.dob=dob
        profileO.contact_verified=True
        profileO.account_verified=True
        profileO.studentClass=clsss
        profileO.designation=branch_id
        profileO.user_group=user_group
        #profile_obj.institute = section.branch
       # profileO.institute=institute
        profileO.save()
        userroom_obj, _ = content_models.UserClassRoom.objects.get_or_create(user=user_obj)
        userroom_obj.institute_rooms.add(section)
        userroom_obj.save()
        print("naseem**************",userroom_obj)
        batch_obj=content_models.Batch.objects.filter(grade=clsss,institute_room=section,is_active=True)
        for batch in batch_obj:
            if len(batch.students.all()) < 250:
                try:
                    learner_batch_obj = content_models.LearnerBatches.objects.get(user=user_obj, batch=batch)
                except:
                    learner_batch_obj = None
                if not learner_batch_obj:
                    learner_batch_obj = content_models.LearnerBatches.objects.create(user=user_obj, batch=batch)
                batch.students.add(user_obj)
                batch.save()
        
        return validated_data


class CommunicationSerializer(ModelSerializer):
    class Meta:
        model = Communication
        fields = ['id','message','is_visible','sent_time']



################################# Third Party Api Integration(serializers) dont use this side of api ##################################
    
class AllExamIdAndExamNameSerializer(ModelSerializer):
    exam_id = serializers.SerializerMethodField()
    exam_name = serializers.SerializerMethodField()

    def get_exam_id(self,instance):
        return instance.id

    def get_exam_name(self,instance):
        return instance.title

    class Meta:
        model=courses_models.Exam
        fields= ['exam_id','exam_name']

   
class AllExamNameDetailsSerializer(ModelSerializer):
    class Meta:
        model=courses_models.Exam
        fields= '__all__'

class ViewBatchSerializer1(serializers.ModelSerializer):
    teacher_username = serializers.SerializerMethodField()
    teacherid = serializers.SerializerMethodField()
    teacher_email = serializers.SerializerMethodField()
    teacher_full_name = serializers.SerializerMethodField()
    profile_pic = serializers.SerializerMethodField()
    institute_room = serializers.SerializerMethodField()

    class Meta:
        model = content_models.Batch
        fields = ('id', 'teacher_username', 'profile_pic', 'teacherid', 'is_active', 'teacher_email', 'teacher_full_name', 'name', 'batch_code', 'institute_room', 'students', 'created_at')

    def get_profile_pic(self, instance):
        try:
            return instance.teacher.profile.image.url
        except:
            return None

    def get_teacher_username(self, instance):
        return instance.teacher.username
    
    def get_teacherid(self, instance):
        return instance.teacher.id

    def get_teacher_email(self, instance):
        return instance.teacher.email

    def get_teacher_full_name(self, instance):
        try:
            return instance.teacher.profile.first_name + ' ' + instance.teacher.profile.last_name
        except:
            return instance.teacher.profile.first_name

    def get_institute_room(self, instance):
        try:
            institute_room = ViewInstituteClassRoomSerializer(instance.institute_room).data
        except:
            institute_room = None
        return institute_room



class CreateBatchSerializer1(Serializer):
    name = CharField(error_messages={'required':'name is required', 'blank':'name is required'},max_length=400)
    unique_id = CharField(error_messages={'required':'name is required', 'blank':'name is required'},max_length=400)
    grade = CharField(error_messages={'required':'grade is required', 'blank':'grade is required'},max_length=400)

    # class Meta:
    #     model = BatchThird
    #     fields = ('id', 'teacher', 'name', 'batch_code', 'students')

    def validate(self, data):
       
        if data.get("name") == "":
            raise ValidationError("name can not be empty")
        if data.get("unique_id") == "":
            raise ValidationError("unique_id can not be empty")

        if content_models.InstituteClassRoom.objects.filter(unique_id=data.get("unique_id")).exists():
            raise ValidationError("This unique_id Allready Exists")
        return data

    def create(self, validated_data):
        #user=self.context['request'].user
        batch_code = uuid.uuid4().hex[:6].upper()
        name=self.validated_data['name']
        unique_id=self.validated_data['unique_id']
        grade = self.validated_data['grade']
        grade_id=UserClass.objects.get(id=grade)
        user=content_models.InstituteClassRoom.objects.create(unique_id=unique_id,name=name,grade=grade_id)
        user.save()
        return validated_data       


class ViewInstituteClassRoomSerializer12(serializers.ModelSerializer):
    #institute_name = serializers.SerializerMethodField()
    grade_name = serializers.SerializerMethodField()
    #branch = serializers.SerializerMethodField()
    #branch_id=serializers.SerializerMethodField()
    #blocked_students = serializers.SerializerMethodField()
    room_teacher_name = serializers.SerializerMethodField()
    #students_count = serializers.SerializerMethodField()
    #mentors_count = serializers.SerializerMethodField()

    class Meta:
        model = content_models.InstituteClassRoom
        
        #fields = ('id', 'institute_name', 'grade_name', 'name', 'blocked_students', 'students_count', 'mentors_count', 'room_teacher_name', 'room_teacher', 'created_at')
        fields=('id','grade_name','name','room_teacher_name','room_teacher','created_at')

    # def get_institute_name(self, instance):
    #     try:
    #         return instance.branch.school.name
    #     except:
    #         return None
    # def get_branch(self,instance):
    #     try:
    #         return instance.branch.branch_name
    #     except:
    #         return None

    # def get_branch_id(self,instance):
    #     try:
    #         return instance.branch.id
    #     except:
    #         return None

    def get_room_teacher_name(self, instance):
        if instance.room_teacher:
            try:
                return instance.room_teacher.profile.first_name + ' ' + instance.room_teacher.profile.last_name
            except:
                return instance.room_teacher.profile.first_name
        else:
            None

    def get_grade_name(self, instance):
        return instance.grade.name

    # def get_mentors_count(self, instance):
    #     return content_models.Batch.objects.filter(institute_room__id=instance.id).count()

    # def get_students_count(self, instance):
    #     return content_models.UserClassRoom.objects.filter(institute_rooms=instance).count()

    # def get_blocked_students(self, instance):
    #     try:
    #         userIds = []
    #         userIds = [user.id for user in instance.blocked_students.all()]
    #         blocked_students = ShortProfileSerializer(Profile.objects.filter(user__in=userIds), many=True).data
    #     except:
    #         blocked_students = []
    #     return blocked_students



class CreateInstituteRoomSerializer2(serializers.ModelSerializer):
    # institute = serializers.PrimaryKeyRelatedField(
    #     queryset=Institute.objects.all(), required=False)
    grade = serializers.PrimaryKeyRelatedField(
        queryset=UserClass.objects.all(), required=False)

    class Meta:
        model = content_models.InstituteClassRoom
        fields = ["unique_id",
                  "grade",
                  "name"
                  ]

    def create(self, validated_data):
        unique_id = validated_data.get('unique_id')
        grade = validated_data.get('grade')
        name = validated_data.get('name')

        try:
            room_obj = content_models.InstituteClassRoom.objects.get(
                unique_id=unique_id,
                grade=grade,
                name=name
            )
        except:
            room_obj = None

        if not room_obj:
            room_obj = content_models.InstituteClassRoom.objects.create(
            unique_id=unique_id,
            grade=grade,
            name=name
        )
        else:
            raise serializers.ValidationError(
                    "Room already present")

        return room_obj


########################################## Api Serializer For Bloom Level Question  ################################################

class BloomSerializer1(ModelSerializer):
    memory_based = serializers.SerializerMethodField()
    memory_based_value = serializers.SerializerMethodField()
    conceptual = serializers.SerializerMethodField()
    conceptual_value = serializers.SerializerMethodField()
    application = serializers.SerializerMethodField()
    application_value = serializers.SerializerMethodField()
    analyze = serializers.SerializerMethodField()
    analyze_value = serializers.SerializerMethodField()
    evaluate = serializers.SerializerMethodField()
    evaluate_value = serializers.SerializerMethodField()


    def get_memory_based(self,instance):
        return 'Memory Based'

    def get_conceptual(self,instance):
        return 'Conceptual'

    def get_application(self,instance):
        return 'Application'

    def get_analyze(self,instance):
        return 'Analyze'
    
    def get_evaluate(self,instance):
        return 'Evaluate'
    
    def get_memory_based_value(self,instance):
        return 0
    
    def get_conceptual_value(self,instance):
        return 0
    
    def get_application_value(self,instance):
        return 0
    
    def get_analyze_value(self,instance):
        return 0
    
    def get_evaluate_value(self,instance):
        return 0

    class Meta:
        model=BarBloomLevel
        fields = ['memory_based','memory_based_value','conceptual','conceptual_value','application','application_value','analyze','analyze_value','evaluate','evaluate_value']
    

class OverAllBloomSerializer(ModelSerializer):
    memory_based = serializers.SerializerMethodField()
    memory_based_value = serializers.SerializerMethodField()
    conceptual = serializers.SerializerMethodField()
    conceptual_value = serializers.SerializerMethodField()
    application = serializers.SerializerMethodField()
    application_value = serializers.SerializerMethodField()
    analyze = serializers.SerializerMethodField()
    analyze_value = serializers.SerializerMethodField()
    evaluate = serializers.SerializerMethodField()
    evaluate_value = serializers.SerializerMethodField()


    def get_memory_based(self,instance):
        return 'Memory Based'

    def get_conceptual(self,instance):
        return 'Conceptual'

    def get_application(self,instance):
        return 'Application'

    def get_analyze(self,instance):
        return 'Analyze'
    
    def get_evaluate(self,instance):
        return 'Evaluate'
    
    def get_memory_based_value(self,instance):
        qs = instance.total_question
        return instance.memory_based*10/qs
        
    def get_conceptual_value(self,instance):
        qs = instance.total_question
        return instance.conceptual*10/qs
    
    def get_application_value(self,instance):
        qs = instance.total_question
        return instance.application*10/qs
    
    def get_analyze_value(self,instance):
        return 0
    
    def get_evaluate_value(self,instance):
        return 0

    class Meta:
        model=OverAllBloomLevelValues #BarBloomLevel
        fields = ['memory_based','memory_based_value','conceptual','conceptual_value','application','application_value','analyze','analyze_value','evaluate','evaluate_value']


class BloomSerializer(ModelSerializer):
    username = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    memory_based = serializers.SerializerMethodField()
    conceptual = serializers.SerializerMethodField()
    application = serializers.SerializerMethodField()
    analyze = serializers.SerializerMethodField()
    evaluate = serializers.SerializerMethodField()
    memory_based_value = serializers.SerializerMethodField()
    conceptual_value = serializers.SerializerMethodField()
    application_value = serializers.SerializerMethodField()
    evaluate_value = serializers.SerializerMethodField()
    analyze_value = serializers.SerializerMethodField()

    def get_full_name(self, instance):
        try:
            return instance.user.profile.first_name + ' ' + instance.user.profile.last_name
        except:
            return instance.user.profile.first_name

    def get_username(self,instance):
        return instance.user.username

    def get_memory_based(self,instance):
        return 'Memory Based'

    def get_conceptual(self,instance):
        return 'Conceptual'

    def get_application(self,instance):
        return 'Application'

    def get_analyze(self,instance):
        return 'Analyze'
    
    def get_evaluate(self,instance):
        return 'Evaluate'
    
    def get_memory_based_value(self,instance):
        qs = instance.memory_based + instance.application + instance.conceptual + instance.analyze + instance.evaluate
        return instance.memory_based*1.7/qs*10
    
    def get_conceptual_value(self,instance):
        qs = instance.memory_based + instance.application + instance.conceptual + instance.analyze + instance.evaluate
        return instance.conceptual*0.5/qs*10
    
    def get_application_value(self,instance):
        qs = instance.memory_based + instance.application + instance.conceptual + instance.analyze + instance.evaluate
        return instance.application*0.7/qs*10
    
    def get_analyze_value(self,instance):
        qs = instance.memory_based + instance.application + instance.conceptual +instance.analyze + instance.evaluate
        return instance.analyze/qs*10
    
    def get_evaluate_value(self,instance):
        qs = instance.memory_based + instance.application + instance.conceptual + instance.analyze + instance.evaluate
        return instance.evaluate/qs*10

    class Meta:
        model=BloomLevelValues
        fields= ['id','full_name','username','memory_based','memory_based_value','conceptual','conceptual_value','application','application_value','analyze','analyze_value','evaluate','evaluate_value']



class BloomLearnerExamSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    userid = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    # full_name = serializers.SerializerMethodField()
    exam = serializers.SerializerMethodField()

    class Meta:
        model = BloomLevelValues
        fields = ('id', 'username', 'userid', 'email', 'exam')

    def get_username(self, instance):
        return instance.user.username
    
    def get_userid(self, instance):
        return instance.user.id

    def get_email(self, instance):
        return instance.user.email

    # def get_full_name(self, instance):
    #     return instance.user.profile.first_name + ' ' + instance.user.profile.last_name
    
    def get_exam(self, instance):
        try:
            exams = course_seri.ViewExamSerializer(instance.exam).data
        except:
            exams = None
        return exams


class LearnerExamPaperHistorySerializer(serializers.ModelSerializer):
    #exam = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerExamPaperHistory
        fields = ('id', 'user', 'score', 'total_marks', 'percentage', 'time_taken', 'total_time', 'total_questions', 'attempted', 'created_at', 'correct', 'unchecked', 'incorrect')
    
        #fields = ('id', 'user', 'exam', 'questions', 'papers', 'score', 'total_marks', 'percentage', 'time_taken', 'total_time', 'total_questions', 'attempted', 'created_at', 'correct', 'unchecked', 'incorrect')
    
    # def get_exam(self, instance):
    #     try:
    #         exam = course_serializer.LearnerExamSerializer(instance.exam).data
    #     except:
    #         exam = None
    #     return exam


class BloomSerializer11(ModelSerializer):
    full_name = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    bloom_level_values = serializers.SerializerMethodField()
    bloom_name = serializers.SerializerMethodField()

    def get_full_name(self, instance):
        try:
            return instance.user.profile.first_name + ' ' + instance.user.profile.last_name
        except:
            return instance.user.profile.first_name

    def get_title(self, instance):
        try:
            qs = courses_models.BloomLevel.objects.all().order_by('-id')
            data=BloomSerializer(qs,many=True).data
        except:
            data = None
        return data
    
    def get_bloom_name(self,instance):
        return instance.title.title

    def get_bloom_level_values(self,instance):
        return instance.bloom_level

    class Meta:
        model=BarBloomLevel
        fields=['id','full_name','title','bloom_level_values','bloom_name']



class jfdsfgsdfhsgfhfsui(ModelSerializer):
    class Meta:
        model=content_models.Question
        fields=['id','bloom_level']


class jfdsfgsdfhsgfhfsu(ModelSerializer):
    class Meta:
        model=content_models.Question
        fields='__all__'

class MyDataSerializer(serializers.Serializer):
    data_list = serializers.ListField(child=serializers.CharField())
