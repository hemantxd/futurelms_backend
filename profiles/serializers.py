from calendar import prmonth
from authentication.models import User
from courses.serializers import DomainSerializer, LearnerExamSerializer
from rest_framework import serializers

from profiles import models as profiles_models
from core import models as core_models
from content import models as content_models

from countrystatecity import models as countrystatecity_models
from courses import models as courses_models
import uuid

class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    email = serializers.CharField(source='user.email')
    contactNumber = serializers.CharField(source='user.phonenumber')
    first_name = serializers.CharField(allow_blank=True, required=False)
    last_name = serializers.CharField(allow_blank=True, required=False)
    address = serializers.CharField(allow_blank=True, required=False)
    user_group = serializers.PrimaryKeyRelatedField(
        queryset=core_models.UserGroup.objects.all(), allow_null=True)
    studentClass = serializers.PrimaryKeyRelatedField(
        queryset=core_models.UserClass.objects.all(), allow_null=True)
    studentBoard = serializers.PrimaryKeyRelatedField(
        queryset=core_models.UserBoard.objects.all(), allow_null=True)
    student_class_name = serializers.SerializerMethodField()
    rollno = serializers.CharField(allow_blank=True, required=False)
    city = serializers.PrimaryKeyRelatedField(
        queryset=profiles_models.City.objects.all(), required=False, allow_null=True)
    state = serializers.PrimaryKeyRelatedField(
        queryset=profiles_models.State.objects.all(), required=False, allow_null=True)
    city_name = serializers.SerializerMethodField()
    state_name = serializers.SerializerMethodField()
    user_group_name = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()
    pincode = serializers.IntegerField(allow_null=True)
    # interested_domains = serializers.SerializerMethodField()
    
    class Meta:
        model = profiles_models.Profile
        fields = ('username', 'user_id', 'email', 'contactNumber', 'gender', 'qualification', 'image', 'institute', 'first_name', 'last_name', 'user_group', 'user_group_name', 'address', 'studentClass', 'studentBoard', 'student_class_name', 'rollno', 'city', 'state', 'city_name', 'state_name', 'pincode', 'contact_verified', 'interested_domains', 'created_at')
        read_only_fields = ('username','email')


    def get_user_id(self, instance):
        return instance.user.id

    def get_city_name(self, instance):
        return instance.city.name if instance.city else None

    def get_state_name(self, instance):
        return instance.state.name if instance.state else None

    def get_user_group_name(self, instance):
        return instance.user_group.name if instance.user_group else None

    def get_student_class_name(self, instance):
        return instance.studentClass.name if instance.studentClass else None
    
    # def get_interested_domains(self, instance):
    #     try:
    #         interested_domains = DomainSerializer(instance.interested_domains, many=True).data
    #     except:
    #         interested_domains = None
    #     return interested_domains
    
class EditProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    email = serializers.CharField(allow_blank=True, required=False, allow_null=True)
    first_name = serializers.CharField(allow_blank=True, required=False)
    last_name = serializers.CharField(allow_blank=True, required=False, allow_null=True)
    address = serializers.CharField(allow_blank=True, required=False)
    studentClass = serializers.PrimaryKeyRelatedField(
        queryset=core_models.UserClass.objects.all(), allow_null=True)
    studentBoard = serializers.PrimaryKeyRelatedField(
        queryset=core_models.UserBoard.objects.all(), allow_null=True)
    student_class_name = serializers.SerializerMethodField()
    rollno = serializers.CharField(allow_blank=True, required=False)
    city = serializers.PrimaryKeyRelatedField(
        queryset=profiles_models.City.objects.all(), required=False, allow_null=True)
    state = serializers.PrimaryKeyRelatedField(
        queryset=profiles_models.State.objects.all(), required=False, allow_null=True)
    city_name = serializers.SerializerMethodField()
    state_name = serializers.SerializerMethodField()
    pincode = serializers.IntegerField(allow_null=True)
    institute = serializers.PrimaryKeyRelatedField(
        queryset=profiles_models.State.objects.all(), required=False, allow_null=True)
    interested_domains = serializers.PrimaryKeyRelatedField(
        queryset=courses_models.ExamDomain.objects.all(), many=True, required=False, default=[])
    gender = serializers.CharField(allow_blank=True, required=False)
    qualification = serializers.CharField(allow_blank=True, required=False)
    
    class Meta:
        model = profiles_models.Profile
        fields = ('username', 'email', 'first_name', 'last_name', 'institute', 'address', 'studentClass', 'studentBoard', 'student_class_name', 'rollno', 'city', 'state', 'city_name', 'state_name', 'pincode', 'contact_verified', 'interested_domains', 'gender', 'qualification')
        read_only_fields = ('username','email')

    def get_city_name(self, instance):
        return instance.user.profile.city.name if instance.user.profile.city else None

    def get_state_name(self, instance):
        return instance.user.profile.state.name if instance.user.profile.state else None

    def get_student_class_name(self, instance):
        return instance.user.profile.studentClass.name if instance.user.profile.studentClass else None
    
    def update(self, instance, validated_data):
        first_name = validated_data.get('first_name')
        last_name = validated_data.get('last_name')
        email = validated_data.get('email')
        city = validated_data.get('city')
        state = validated_data.get('state')
        gender = validated_data.get('gender')
        qualification = validated_data.get('qualification')
        interested_domains = validated_data.get('interested_domains')
        # if email:
        instance.user.email = email
        instance.user.save()
        if first_name:
            instance.first_name = first_name
        # if last_name:
        instance.last_name = last_name
        # if city:
        instance.city = city
        # if state:
        instance.state = state
        instance.gender = gender
        instance.qualification = qualification
        if interested_domains:
            instance.interested_domains.add(*interested_domains)
        instance.save()
        return instance

class ShortProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    user_id = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = profiles_models.Profile
        fields = ('user_id', 'full_name', 'image',
                  'username', 'logout_updated_on')
        read_only_fields = ('username', 'user_id')

    def get_user_id(self, instance):
        return instance.user.id

    def get_full_name(self, instance):
        try:
            return instance.first_name + ' ' + instance.last_name
        except:
            return instance.first_name

    def get_image(self, instance):
        try:
            url = instance.image.url
        except:
            url = ""
        return url

class ProfileImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = profiles_models.Profile
        fields = ('image',)

class UserGroupChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = profiles_models.Profile
        fields = ('user_group',)
        
class UserBoardSerializer(serializers.ModelSerializer):

    class Meta:
        model = core_models.UserBoard
        fields = '__all__'

class UserClassSerializer(serializers.ModelSerializer):

    class Meta:
        model = core_models.UserClass
        fields = '__all__'


class StudentSerializer(serializers.ModelSerializer):
    """Serializers registration requests and creates a new user."""

    # Ensure passwords are at least 8 characters long, no longer than 128
    # characters, and can not be read by the client.
    password = serializers.CharField(
        max_length=128,
        min_length=8,
        write_only=True
    )

    phonenumber = serializers.CharField(max_length=10)
    username = serializers.CharField(allow_blank=True, required=False)
    enrolledexams = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    institute = serializers.PrimaryKeyRelatedField(queryset=profiles_models.Institute.objects.all(), required=True)
    studentClass = serializers.PrimaryKeyRelatedField(queryset=core_models.UserClass.objects.all(), required=True)

    class Meta:
        model = User
        
        # List all of the fields that could possibly be included in a request
        # or response, including fields specified explicitly above.
        fields = ['email', 'username', 'password', 'institute', 'studentClass', 'phonenumber', 'enrolledexams', 'first_name', 'last_name']

    def get_first_name(self, instance):
        return instance.profile.first_name

    def get_last_name(self, instance):
        return instance.profile.last_name
    
    def get_enrolledexams(self, instance):
        return LearnerExamSerializer(courses_models.LearnerExams.objects.filter(user=instance), many=True).data
    
    def get_institute(self, instance):
        return instance.profile.institute

    def get_studentClass(self, instance):
        return instance.profile.studentClass

    # def validate_phonenumber(self, phonenumber):
    #     if profiles_models.Profile.objects.filter(contact_info=phonenumber).exists():
    #         raise serializers.ValidationError('Phone no. already exists.')
    #     return phonenumber

    def create(self, validated_data):
        # Use the `create_user` method we wrote earlier to create a new user.
        self.phonenumber = validated_data.get('phonenumber')
        user = User.objects.create_user(**validated_data)
        user.is_individual = False
        user.save()
        institute = validated_data.get('institute')
        studentClass = validated_data.get('studentClass')
        instituteobj = profiles_models.Institute.objects.get(id=institute.id)
        studentClassobj = core_models.UserClass.objects.get(id=studentClass.id)
        profile = profiles_models.Profile.objects.get(user=user)
        # profile.contact_info = self.phonenumber
        profile.institute = instituteobj
        profile.studentClass = studentClassobj
        profile.save()

        return user

class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = profiles_models.State
        fields = ["id", "name", "total_cities", "identifier"]

class CitySerializer(serializers.ModelSerializer):
    state = serializers.PrimaryKeyRelatedField(queryset=profiles_models.State.objects.all(), required=True)
    class Meta:
        model = profiles_models.City
        fields = ["id", "state", "name", "identifier"]

    def create(self, validated_data):
        state = validated_data.get('state')
        name = validated_data.get('name')
        identifier = validated_data.get('identifier')
        stateobj = profiles_models.State.objects.get(id=state.id)
        # try: 
        #     lastCityObj = profiles_models.City.objects.last()
        # except:
        #     lastCityObj = None
        # if lastCityObj:
        #     identifier = lastCityObj.identifier + 1
        # else:
        #     identifier = 1
        city = profiles_models.City.objects.create(name=name, state=state, identifier=identifier)
        stateobj.total_cities += 1
        stateobj.save()
        # city.identifier=identifier
        # city.save()
        return city

class CreateInstituteSerializer(serializers.Serializer):
    city = serializers.PrimaryKeyRelatedField(
        queryset=profiles_models.City.objects.all())
    name = serializers.CharField()
    website = serializers.CharField(required=False, allow_null=True)
    head = serializers.CharField(required=False, allow_null=True)
    head_contact_no = serializers.CharField(required=False, allow_null=True)
    email = serializers.CharField(required=False, allow_null=True)
    street = serializers.CharField()
    pin = serializers.CharField()
    school_code = serializers.CharField(required=False, allow_null=True)
    is_verified = serializers.BooleanField(required=False)
    registered = serializers.BooleanField(required=False)

    class Meta:
        fields = ('id', 'name', 'email', 'website', 'head', 'is_verified', 'registered'
                  'head_contact_no', 'street', 'pin', 'school_code')

    def create(self, validated_data):
        institute = profiles_models.Institute.objects.create(name=validated_data.get('name'), email=validated_data.get(
            'email'), is_verified=validated_data.get('is_verified'), website=validated_data.get('website'), head=validated_data.get('head'), head_contact_no=validated_data.get('head_contact_no'))
        city = validated_data.get('city')
        state = city.state
        street = validated_data.get('street')
        institute.state = state
        institute.registered = validated_data.get('registered')
        institute.city = city
        institute.street = street
        institute.pin = validated_data.get('pin')
        if validated_data.get('school_code'):
            institute.school_code = validated_data.get('school_code')
        else:
            institute.school_code = uuid.uuid4().hex[:6].upper()
        institute.save()
        # profiles_models.InstituteAddress.objects.create(
        #     institute=institute, state=state, city=city, street=street)
        return institute

class InstituteSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    city_details = serializers.SerializerMethodField()

    class Meta:
        model = profiles_models.Institute
        fields = ('id', 'name', 'email', 'website', 'head', 'head_contact_no', 'state', 'street',
                  'pin', 'is_verified', 'city_details', 'registered')
        lookup_field = 'id'

    def get_city_details(self, instance):
        return CitySerializer(instance.city).data


class ShortInstituteSerializer(serializers.ModelSerializer):
    class Meta:
        model = profiles_models.Institute
        fields = ('id', 'name', 'registered')

