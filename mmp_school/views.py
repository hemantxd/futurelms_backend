from django.shortcuts import render

# Create your views here.

from django.shortcuts import render
from requests import request
from rest_framework.views import APIView
from rest_framework.response import Response

from profiles.views import studentsList
from .models import *
from .serializers import *
from rest_framework.status import (
                                        HTTP_200_OK,
                                    	HTTP_400_BAD_REQUEST,
                                    	HTTP_204_NO_CONTENT,
                                    	HTTP_201_CREATED,
                                    	HTTP_500_INTERNAL_SERVER_ERROR,
                                        HTTP_404_NOT_FOUND,
                                        HTTP_429_TOO_MANY_REQUESTS,
                                    ) 
from rest_framework.permissions import AllowAny,IsAuthenticated,IsAdminUser,IsAuthenticatedOrReadOnly
from rest_framework.generics import ListAPIView,CreateAPIView,RetrieveAPIView,UpdateAPIView,RetrieveUpdateAPIView

from rest_framework.exceptions import ParseError,ValidationError

from rest_framework.parsers import MultiPartParser, FormParser, FileUploadParser
from content import models as content_models
from courses import models as courses_models
from courses import serializers as serializer
from notification import models as notification_models
from core import permissions
#profile import 
from profiles.renderers import ProfileJSONRenderer
from profiles.serializers import ProfileSerializer
from profiles.exceptions import ProfileDoesNotExist

from core.models import *
from core import paginations as core_paginations
from profiles.models import *
from django.http import JsonResponse

import pandas as pd
from django.conf import settings
import uuid
from datetime import datetime
from content import serializers as serializers
from content import utils as content_utils
from django.http import HttpResponse


def check_blank_or_null(data):
    status=True
    for x in data:
        if x=="" or x==None:
            status=False
            break
        else:
            pass                    
    return status

# Create your views here.

class ProfileRetrieveAPIView(RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = (ProfileJSONRenderer,)
    serializer_class = ProfileSerializer

    def retrieve(self, request, *args, **kwargs):
        
        # Try to retrieve the requested profile and throw an exception if the
        # profile could not be found.
        try:
            # We use the `select_related` method to avoid making unnecessary
            # database calls.
            x=content_models.BranchSchool.objects.filter(user=request.user)
            print(x)
            for course in x:
                print("School Name is ")
            profile = Profile.objects.select_related('user', 'state', 'city', 'studentClass').get(
                        user__id=request.user.id)
        except Profile.DoesNotExist:
            raise ProfileDoesNotExist
        
        serializer = self.serializer_class(profile)

        return Response({'school_name':course.school.name,"data":serializer.data}, status=HTTP_200_OK)



class CreateSchoolAndSeassonApi(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        qs=Institute.objects.all().order_by('id')
        data=SchoolSerializer(qs, many=True, context={'request':request}).data
        return Response({'message':'School list','data':data},status=HTTP_200_OK)

    def post(self,request):
        user=request.user
        school_name=request.data.get('school_name')
        branch_name=request.data.get('branch_name')
        seassion_name=request.data.get('seassion_name')
        if content_models.BranchSchool.objects.filter(branch_name=branch_name).exists():
            return Response({'message':'branch name already exists'},status=HTTP_400_BAD_REQUEST)
        if check_blank_or_null(school_name) and Institute.objects.filter(name=school_name).exists():
            qs=Institute.objects.get(name=school_name)
            print(qs,'**************')
            branch=content_models.BranchSchool.objects.create(user=user,school=qs,branch_name=branch_name)
            branch.save()
            seassion=content_models.SchoolSeasson.objects.create(schoolbranch=branch,seassion_name=seassion_name)
            seassion.save()
            data={
            'school_name':school_name,
            'seassion_name':seassion_name,
            'branch_name':branch_name,
            }
            return Response({'message':'Branch And Seasson has been successfully Created','data':data},status=HTTP_200_OK)
        return Response({'message':'school_name is required'})



class CreateSeassonOnExistsBranchApi(APIView):
    permission_classes = (IsAuthenticated,)
    def post(self,request):
        branch_name=request.data.get('branch_name')
        seassion_name=request.data.get('seassion_name')
        qs=content_models.BranchSchool.objects.get(branch_name=branch_name)
        print(qs,'**************')
        if content_models.SchoolSeasson.objects.filter(schoolbranch=qs,seassion_name=seassion_name).exists():
            return Response({'message':'seassion name already exists on selected branch '},status=HTTP_400_BAD_REQUEST)

        if check_blank_or_null(seassion_name) and content_models.BranchSchool.objects.filter(branch_name=branch_name).exists():
            seassion=content_models.SchoolSeasson.objects.create(schoolbranch=qs,seassion_name=seassion_name)
            seassion.save()
            data={
            'seassion_name':seassion_name,
            'branch_name':branch_name
            }
            return Response({'message':'Branch And Seasson has been successfully Created','data':data},status=HTTP_200_OK)
        return Response({'message':'school_name is required'})


class SchoolBranchApiView(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        addr=content_models.BranchSchool.objects.filter(user=request.user).order_by("-id")
        serializer=SchoolBranchSerializer(addr,many=True)
        return Response({'data':serializer.data},status=HTTP_200_OK)

class SeassonViewApi(APIView):
    def get(self,request):
        pk = request.GET['id']
        if content_models.BranchSchool.objects.filter(pk=pk).exists():
            c=content_models.BranchSchool.objects.get(pk=pk)
            addr=content_models.SchoolSeasson.objects.filter(schoolbranch=c).order_by("-id")
            serializer=SchoolSeassonSerializer(addr,many=True)
            return Response({'data':serializer.data},status=HTTP_200_OK)
        else:
            return Response({'error':'Branch Id is not exists'},status=HTTP_400_BAD_REQUEST)   

class GetSeassonViewApi(APIView):
    def get(self,request):
        qs=UserSeasson.objects.all().order_by('id')
        data=SeassonClassSerializer(qs, many=True, context={'request':request}).data
        return Response({'message':'Seasson list','data':data},status=HTTP_200_OK)

from django.db.models import Count
class SchoolClassApiView(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        institute_id = self.request.query_params.get('branch_id', None)
        if not institute_id:
            raise ParseError("Please enter branch_id Id")
        institute_id = int(institute_id)
        qss=UserGroup.objects.get(name='student')
        students_count = Profile.objects.filter(user_group=qss,designation=institute_id).count()

        section=content_models.InstituteClassRoom.objects.filter(is_active=True,branch=institute_id)
        student1 = 0
        for student1 in section:
            print(student1)
        queryset = content_models.Batch.objects.filter(grade=1,institute_room=student1).annotate(count=Count("students")).values_list("students")
        print((queryset))
        print(len(queryset))
        qss=content_models.Batch.objects.filter(grade=1,institute_room=student1)
        print(qss)
       
        data=[
             {
            'id':"1",
            "total_student_class": len(content_models.Batch.objects.filter(grade=1,institute_room=student1).annotate(count=Count("students")).values_list("students")),
            "total_section": content_models.InstituteClassRoom.objects.filter(grade=1,branch=institute_id,is_active=True).count(),
            "name": "Class 1",
            #"image":"https://erdrstoragedev.s3.amazonaws.com/media/course-images/44/e4ec56da-3a54-4611-92a7-0d6de0855677.png"
            "image":"https://mmpprodstorageaccount.blob.core.windows.net/makemypathfiles/media/course-images/44/e4ec56da-3a54-4611-92a7-0d6de0855677.png"
           },
            {
            "id": "2",
            "total_student_class": len(content_models.Batch.objects.filter(grade=2,institute_room=student1).annotate(count=Count("students")).values_list("students")),
            "total_section": content_models.InstituteClassRoom.objects.filter(grade=2,branch=institute_id,is_active=True).count(),
            "name": "Class 2",
           # "image":"https://erdrstoragedev.s3.amazonaws.com/media/course-images/43/981fd17e-ae89-4b70-ab5f-2f2bfcde1804.png"
            "image":"https://mmpprodstorageaccount.blob.core.windows.net/makemypathfiles/media/course-images/43/981fd17e-ae89-4b70-ab5f-2f2bfcde1804.png"
        },
        {
            "id": "3",
            "total_student_class": len(content_models.Batch.objects.filter(grade=3,institute_room=student1).annotate(count=Count("students")).values_list("students")),
            "total_section": content_models.InstituteClassRoom.objects.filter(grade=3,branch=institute_id,is_active=True).count(),
            "name": "Class 3",
            #"image":"https://erdrstoragedev.s3.amazonaws.com/media/course-images/42/571252f8-7c3a-4805-bdd2-c7a993db9c45.png"
            "image":"https://mmpprodstorageaccount.blob.core.windows.net/makemypathfiles/media/course-images/42/571252f8-7c3a-4805-bdd2-c7a993db9c45.png"
        },
        {
            "id": "4",
            "total_student_class": len(content_models.Batch.objects.filter(grade=4,institute_room=student1).annotate(count=Count("students")).values_list("students")),
            "total_section": content_models.InstituteClassRoom.objects.filter(grade=4,branch=institute_id,is_active=True).count(),
            "name": "Class 4",
           # "image":"https://erdrstoragedev.s3.amazonaws.com/media/course-images/45/6d85a2bb-a5dd-4c2c-802d-153988999927.png"
            "image":"https://mmpprodstorageaccount.blob.core.windows.net/makemypathfiles/media/course-images/45/6d85a2bb-a5dd-4c2c-802d-153988999927.png"
        },
        {
            "id": "5",
            "total_student_class": len(content_models.Batch.objects.filter(grade=5,institute_room=student1).annotate(count=Count("students")).values_list("students")),
            "total_section": content_models.InstituteClassRoom.objects.filter(grade=5,branch=institute_id,is_active=True).count(),
            "name": "Class 5",
            #"image":"https://erdrstoragedev.s3.amazonaws.com/media/course-images/41/2c4ebe38-10e5-4719-a471-38b5959de3ee.png"
            "image":"https://mmpprodstorageaccount.blob.core.windows.net/makemypathfiles/media/course-images/41/2c4ebe38-10e5-4719-a471-38b5959de3ee.png"
        },
        {
            "id": "6",
            "total_student_class": len(content_models.Batch.objects.filter(grade=6,institute_room=student1).annotate(count=Count("students")).values_list("students")),
            "total_section": content_models.InstituteClassRoom.objects.filter(grade=6,branch=institute_id,is_active=True).count(),
            "name": "Class 6",
           # "image":"https://erdrstoragedev.s3.amazonaws.com/media/course-images/40/4c7fb531-1683-4a3a-85ef-2692c8be8205.png"
            "image":"https://mmpprodstorageaccount.blob.core.windows.net/makemypathfiles/media/course-images/40/4c7fb531-1683-4a3a-85ef-2692c8be8205.png"
        },
        {
            "id": "7",
            "total_student_class": len(content_models.Batch.objects.filter(grade=7,institute_room=student1).annotate(count=Count("students")).values_list("students")),
            "total_section": content_models.InstituteClassRoom.objects.filter(grade=7,branch=institute_id,is_active=True).count(),
            "name": "Class 7",
           # "image":"https://erdrstoragedev.s3.amazonaws.com/media/course-images/39/26ebda6f-7c72-4ca5-88d4-f0b49f4559d7.png"
            "image":"https://mmpprodstorageaccount.blob.core.windows.net/makemypathfiles/media/course-images/39/26ebda6f-7c72-4ca5-88d4-f0b49f4559d7.png"
        },
        {
            "id": "8",
            "total_student_class": len(content_models.Batch.objects.filter(grade=8,institute_room=student1).annotate(count=Count("students")).values_list("students")),
            "total_section": content_models.InstituteClassRoom.objects.filter(grade=8,branch=institute_id,is_active=True).count(),
            "name": "Class 8",
           # "image":"https://erdrstoragedev.s3.amazonaws.com/media/course-images/38/ad4c4142-d109-4146-b007-ef22e916634b.png"
            "image":"https://mmpprodstorageaccount.blob.core.windows.net/makemypathfiles/media/course-images/38/ad4c4142-d109-4146-b007-ef22e916634b.png"
        },
        {
            "id": "9",
            "total_student_class": len(content_models.Batch.objects.filter(grade=9,institute_room=student1).annotate(count=Count("students")).values_list("students")),
            "total_section": content_models.InstituteClassRoom.objects.filter(grade=9,branch=institute_id,is_active=True).count(),
            "name": "Class 9",
           # "image":"https://erdrstoragedev.s3.amazonaws.com/media/course-images/37/8231e82b-7902-49ef-998f-97a362e16661.png"
            "image":"https://mmpprodstorageaccount.blob.core.windows.net/makemypathfiles/media/course-images/37/8231e82b-7902-49ef-998f-97a362e16661.png"
        },
        {
            "id": "10",
            "total_student_class": len(content_models.Batch.objects.filter(grade=10,institute_room=student1).annotate(count=Count("students")).values_list("students")),
            "total_section": content_models.InstituteClassRoom.objects.filter(grade=10,branch=institute_id,is_active=True).count(),
            "name": "Class 10",
            #"image":"https://erdrstoragedev.s3.amazonaws.com/media/course-images/32/256cf5b9-744d-46f7-89c2-bc98fc5d5cdb.png"
            "image":"https://mmpprodstorageaccount.blob.core.windows.net/makemypathfiles/media/course-images/32/256cf5b9-744d-46f7-89c2-bc98fc5d5cdb.png"
        },
        {
            "id": "11",
            "total_student_class": len(content_models.Batch.objects.filter(grade=11,institute_room=student1).annotate(count=Count("students")).values_list("students")),
            "total_section": content_models.InstituteClassRoom.objects.filter(grade=11,branch=institute_id,is_active=True).count(),
            "name": "Class 11",
            #"image":"https://erdrstoragedev.s3.amazonaws.com/media/course-images/36/bd831b33-55d2-432b-b9e4-bc1821754524.png"
            "image":"https://mmpprodstorageaccount.blob.core.windows.net/makemypathfiles/media/course-images/36/bd831b33-55d2-432b-b9e4-bc1821754524.png"
        },
        {
            "id": "12",
            "total_student_class": len(content_models.Batch.objects.filter(grade=12,institute_room=student1).annotate(count=Count("students")).values_list("students")),
            "total_section": content_models.InstituteClassRoom.objects.filter(grade=12,branch=institute_id,is_active=True).count(),
            "name": "Class 12",
           # "image":"https://erdrstoragedev.s3.amazonaws.com/media/course-images/33/c1b0ddca-1839-4f8c-a351-f05b7910a3ce.png"
            "image":"https://mmpprodstorageaccount.blob.core.windows.net/makemypathfiles/media/course-images/33/c1b0ddca-1839-4f8c-a351-f05b7910a3ce.png"
        },

        ]
        return Response({'message':'School Class list','total_student':students_count,'data':data},status=HTTP_200_OK)

class FetchTotalStudentsCountInSchoolViewSet1(ListAPIView,):
   # permission_classes = [IsAuthenticatedOrReadOnly, ]

    def get_queryset(self):
        institute_id = self.request.query_params.get('branch_id', None)
        
        if not institute_id:
            raise ParseError("Please enter branch_id Id")
        
        institute_id = int(institute_id)
        
        students_count = Profile.objects.filter(designation=institute_id).count()
        return students_count

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        try:
            return Response({
                'TotalStudents':queryset,
            })
        except:
            return Response({'error': 'Error.'}, status=HTTP_429_TOO_MANY_REQUESTS)



class ShowSectionOfClass(ListAPIView):
    #permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = ViewInstituteClassRoomSerializer
    
    def get_queryset(self):
        institute = self.request.query_params.get('class_id')
        if institute:
            rooms = content_models.InstituteClassRoom.objects.filter(grade__id=institute)
        else:
            rooms = content_models.InstituteClassRoom.objects.all()
        return rooms

class InstituteClassRoomViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = ViewInstituteClassRoomSerializer
    create_class = CreateInstituteRoomSerializer

    def get(self,request):
        institute = self.request.query_params.get('class_id')
        branch = self.request.query_params.get('branch')
        qs=content_models.InstituteClassRoom.objects.filter(branch__id=branch,grade__id=institute)
        data=ViewInstituteClassRoomSerializer(qs, many=True, context={'request':request}).data
        return Response({'class_name':institute,'data':data},status=HTTP_200_OK)


    def create(self, request, *args, **kwargs):
        serializer = self.create_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=HTTP_201_CREATED)


class DeLeteSectionView(RetrieveUpdateAPIView):
    queryset = content_models.InstituteClassRoom.objects.all()
    serializer_class = ViewInstituteClassRoomSerializer
    lookup_field = 'pk'
    #permission_classes = (IsAuthenticated,)

    # def get_queryset(self):
        
    #     batch_obj = content_models.InstituteClassRoom.objects.select_related("institute", "branch" ,"room_teacher", "grade"
    #     ).filter(pk=self.kwargs.get('pk')).order_by('id')
    #     if not batch_obj:
    #         raise ParseError("Section data with this id DoesNotExist")
    #     return batch_obj

    def post(self, request, *args, **kwargs):
        id = request.data.get('id')
        try:
            section_obj = content_models.InstituteClassRoom.objects.get(id=id)
            print(section_obj)
        except:
            return Response({"message": "Please enter valid id"}, status=HTTP_400_BAD_REQUEST)
        try:
            section_obj.is_active = False
            section_obj.save()
            # print(section_obj,"try block doest not work")
            # section_obj.delete()
            # print(section_obj,"try block does work")
        except:
            return Response({"message": "error in delete the section"}, status=HTTP_400_BAD_REQUEST)
        return Response({"message": "section delete successfully"}, status=201)


class InstituteClassRoomByIdViewSet(RetrieveAPIView):
    queryset = content_models.InstituteClassRoom.objects.all()
    serializer_class = ViewInstituteClassRoomSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        room = content_models.InstituteClassRoom.objects.filter(pk=self.kwargs.get('pk'))
        if not room:
            raise ValidationError("Room with this id DoesNotExist")
        return room


class FetchClassSectionViewSet(ListAPIView):
    permission_classes = [IsAuthenticated, ]
    serializer_class = ViewBatchClassSectionSerializer
    def get(self,request):
        room = self.request.query_params.get('room')
        qs=content_models.Batch.objects.filter(institute_room=room)[:1]
        data=ViewBatchClassSectionSerializer(qs, many=True, context={'request':request}).data
        return Response({'data':data},status=HTTP_200_OK)

class FetchRoomBatchesViewSet(ListAPIView,CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = ViewBatchSerializer
    create_class = CreateBatchSerializer

    def get_queryset(self):
        room = self.request.query_params.get('room')
        batches = content_models.Batch.objects.filter(institute_room__id=room)
        if batches:
            return batches
        else:
            return []

    def create(self, request, *args, **kwargs):
        serializer = self.create_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=HTTP_201_CREATED)


class EditBatchViewSet1(RetrieveUpdateAPIView):
    queryset = content_models.Batch.objects.all()
    serializer_class = ViewBatchSerializer
    update_serializer_class = CreateBatchSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        batch = content_models.Batch.objects.filter(pk=self.kwargs.get('pk'))
        if not batch:
            raise ParseError("Batch with this id DoesNotExist")
        return batch

    def update(self, request, *args, **kwargs):
        batch = content_models.Batch.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            batch, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(batch).data, status=HTTP_200_OK)


class FetchStudentsInRoomViewSet(ListAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = ViewUserClassRoomSerializer

    def get_queryset(self):
        room = self.request.query_params.get('room')
        institute_room = content_models.InstituteClassRoom.objects.get(id=room)
        studentrooms = content_models.UserClassRoom.objects.filter(institute_rooms=institute_room)
        if studentrooms:
            return studentrooms
        else:
            return []

class DeactivateBatchView(RetrieveUpdateAPIView):
    queryset = content_models.Batch.objects.all()
    serializer_class = ViewBatchSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        
        batch_obj = content_models.Batch.objects.select_related("teacher", "name", "teacher__profile", "batch_code", "students"
        ).filter(pk=self.kwargs.get('pk')).order_by('id')
        if not batch_obj:
            raise ParseError("Batch data with this id DoesNotExist")
        return batch_obj

    def put(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            batch_obj = content_models.Batch.objects.get(pk=int(id))
        except:
            return Response({"message": "Please enter valid id"}, status=HTTP_400_BAD_REQUEST)
        try:
            batch_obj.is_active = False
            batch_obj.save()
        except:
            return Response({"message": "error in deactivating the batch"}, status=HTTP_400_BAD_REQUEST)
        return Response({"message": "batch deactivated successfully"}, status=201)


class ActivateBatchView(RetrieveUpdateAPIView):
    queryset = content_models.Batch.objects.all()
    serializer_class = ViewBatchSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        
        batch_obj = content_models.Batch.objects.select_related("teacher", "name", "teacher__profile", "batch_code", "students"
        ).filter(pk=self.kwargs.get('pk')).order_by('id')
        if not batch_obj:
            raise ParseError("Batch data with this id DoesNotExist")
        return batch_obj

    def put(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            batch_obj = content_models.Batch.objects.get(pk=int(id))
        except:
            return Response({"message": "Please enter valid id"}, status=HTTP_400_BAD_REQUEST)
        try:
            batch_obj.is_active = True
            batch_obj.save()
        except:
            return Response({"message": "error in activating the batch"}, status=HTTP_400_BAD_REQUEST)
        return Response({"message": "batch activated successfully"}, status=201)


class RemoveAndBlockUserFromBatchView(UpdateAPIView):
    serializer_class = ViewBatchSerializer

    def put(self, request, *args, **kwargs):
        try:
            username = request.data.get('user')
            user_obj = User.objects.get(username=username)
        except:
            user_obj = None
        if not user_obj:
            return Response({"message": "user with this username does not exist"}, status=HTTP_400_BAD_REQUEST)
        try:
            batchid = request.data.get('batch')
            batch_obj = content_models.Batch.objects.get(id=int(batchid))
        except:
            batch_obj = None
        if not batch_obj:
            return Response({"message": "batch with this id does not exist"}, status=HTTP_400_BAD_REQUEST)
        else:
            try:
                history_obj = content_models.LearnerBatchHistory.objects.get(batch=batch_obj, user=user_obj)
            except:
                history_obj = None
            if history_obj:
                history_obj.is_blocked = True
                history_obj.save()
            if batch_obj.institute_room:
                userroomobj = content_models.UserClassRoom.objects.filter(user=user_obj).last()
                userroomobj.institute_rooms.remove(batch_obj.institute_room)
                userroomobj.save()
                room_obj = content_models.InstituteClassRoom.objects.get(id=batch_obj.institute_room.id)
                room_obj.blocked_students.add(user_obj)
                room_obj.save()
            content_models.LearnerBlockedBatches.objects.create(user=user_obj, batch=batch_obj)
            content_models.LearnerBatches.objects.filter(user=user_obj, batch=batch_obj).delete()
            teacher_profile = Profile.objects.get(user=batch_obj.teacher)
            notification_type = notification_models.NotificationType.objects.get(name="admin")
            if batch_obj.institute_room:
                notification_text  = "Blocked from batch: " + batch_obj.institute_room.grade.name + " - " + batch_obj.institute_room.name
                message = "Mentor " + teacher_profile.first_name + " has blocked you from batch " + batch_obj.institute_room.grade.name + " - " + batch_obj.institute_room.name
            else:
                notification_text  = "Blocked from batch: " + batch_obj.name
                message = "Mentor " + teacher_profile.first_name + " has blocked you from batch " + batch_obj.name
            notification_models.Notifications.objects.create(user=user_obj, batch=batch_obj, notification=message, subject=notification_text, type=notification_type)

        return Response(self.serializer_class(batch_obj).data, status=201)

class CheckIfBlockedViewSet(ListAPIView):
    queryset = content_models.LearnerBatches.objects.all()
    serializer_class = LearnerBatchSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user=self.request.user
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            batch_obj = content_models.Batch.objects.get(id=int(batch_id))
            if batch_obj:
                try:
                    blocked_obj = content_models.LearnerBlockedBatches.objects.filter(user=user, batch=batch_obj)
                except:
                    blocked_obj = None
                if blocked_obj:
                    raise ParseError("You are blocked from this batch")
                try:
                    learner_batch_obj = content_models.LearnerBatches.objects.filter(user=user, batch=batch_obj)
                except:
                    return Response({"message": "not in this batch"}, status=HTTP_400_BAD_REQUEST)
            if not batch_obj:
                raise ParseError("Batch with this id DoesNotExist")
        if not batch_id:
            raise ParseError("Please enter batch id")
        if learner_batch_obj:
            return learner_batch_obj
        else:

            return []
  

class FetchBlockedUserInBatchViewSet(ListAPIView):
    queryset = content_models.LearnerBlockedBatches.objects.all()
    serializer_class = LearnerBlockedBatchSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        user=self.request.user
        batchid = self.request.query_params.get('batch')
        if batchid:
            batch_obj = content_models.Batch.objects.get(id=int(batchid))
            blocked_obj = content_models.LearnerBlockedBatches.objects.filter(batch=batch_obj)
            if blocked_obj:
                return blocked_obj
            else:
                return []

class UnblockUserFromBatchViewSet(ListAPIView):
    queryset = content_models.LearnerBlockedBatches.objects.all()
    serializer_class = LearnerBlockedBatchSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        batchid = self.request.query_params.get('batch')
        username = self.request.query_params.get('user')
        if batchid:
            batch_obj = content_models.Batch.objects.get(id=int(batchid))
            user= User.objects.get(username=username)
            content_models.LearnerBlockedBatches.objects.filter(batch=batch_obj, user=user).delete()
            try:
                history_obj = content_models.LearnerBatchHistory.objects.get(batch=batch_obj, user=user)
            except:
                history_obj = None
            if history_obj:
                history_obj.is_blocked = False
                history_obj.save()
            if batch_obj.institute_room:
                userroomobj = content_models.UserClassRoom.objects.filter(user=user).last()
                userroomobj.institute_rooms.add(batch_obj.institute_room)
                userroomobj.save()
                room_obj = content_models.InstituteClassRoom.objects.get(id=batch_obj.institute_room.id)
                room_obj.blocked_students.remove(user)
                room_obj.save()
            teacher_profile = Profile.objects.get(user=batch_obj.teacher)
            notification_type = notification_models.NotificationType.objects.get(name="admin")
            if batch_obj.institute_room:
                notification_text  = "Unblocked from batch: " + batch_obj.institute_room.grade.name + " - " + batch_obj.institute_room.name
                message = "Mentor " + teacher_profile.first_name + " has unblocked you from batch " + batch_obj.institute_room.grade.name + " - " + batch_obj.institute_room.name
            else:
                notification_text  = "Unblocked from batch: " + batch_obj.name
                message = "Mentor " + teacher_profile.first_name + " has unblocked you from batch " + batch_obj.name
            notification_models.Notifications.objects.create(user=user, batch=batch_obj, notification=message, subject=notification_text, type=notification_type)

            blocked_obj = content_models.LearnerBlockedBatches.objects.filter(batch=batch_obj)
            if blocked_obj:
                return blocked_obj
            else:
                return []

class GetMentorListAPIView(APIView):
    def get(self,request):
        branch_id = self.request.query_params.get('branch_id')
        # branch=content_models.BranchSchool.objects.get(id=branch_id)
        # print(branch,"hello")
        qss=UserGroup.objects.get(name='teacher')
        qs=Profile.objects.filter(user_group=qss,designation=branch_id).order_by("-id")
        data=MentorListSearchSerializer(qs,many=True,context={'request':request}).data
        return Response({'message':'All Mentor List ','data':data})


class AddMentorWithUserIdAndNumber(APIView):
    def post(self,request):
        mobile_number = request.data["mobile_number"]
        branch_id = self.request.query_params.get('branch_id')
        print(branch_id,"hello")
       # fullname = request.data["fullname"]
        user_group=UserGroup.objects.get(name='teacher')
        if User.objects.filter(phonenumber=mobile_number).exists():
            raise ValidationError('Mobile Number allready exists')
        last_user_created_id = User.objects.all().last().id
        username = create_username(str(10000 + last_user_created_id))
        user_obj = User.objects.create(username=username,fullname="",phonenumber=mobile_number)
        user_obj.set_password(username)
        user_obj.save()
        print("*********************",user_obj)
        profileO=Profile.objects.get(user=user_obj)
        profileO.user_group=user_group
        profileO.contact_verified=True
        profileO.account_verified=True
        profileO.designation=branch_id
        profileO.save()
        user= User.objects.filter(phonenumber = mobile_number).last()
        print(user,"************************")
        # batch_obj = Batch.objects.create(teacher=user, batch_code=uuid.uuid4().hex[:6].upper())
        # print("################",batch_obj)
        # batch_obj.save()

        return Response({'message':'Mentor Add Successfully '})

class AssignMentorInClassAndBatch(APIView):
    def post(self,request):
        branch_id = self.request.query_params.get('branch_id')  
        userclass_id = request.data['userclass_id']
        section_id = request.data['section_id']
        phonenumber=request.data['phonenumber']
        clsss=UserClass.objects.get(id=userclass_id)
        section=content_models.InstituteClassRoom.objects.get(id=section_id)
        user= User.objects.filter(phonenumber=phonenumber).last()
        tem_batch_obj=content_models.Batch.objects.filter(teacher=user,grade=clsss ,institute_room=section)
        print("#####*********#####",tem_batch_obj)
        if tem_batch_obj:
            return Response({"message": "This Mentor Already Assign this Batch"}, status=HTTP_400_BAD_REQUEST)
        batch_obj = content_models.Batch.objects.create(teacher=user, batch_code=uuid.uuid4().hex[:6].upper(), institute_room=section,grade=clsss)
        print("**************************",batch_obj)
        if len(batch_obj.students.all()) >= 250:
            return Response({"message": "Maximum 250 students are allowed in a batch"}, status=HTTP_400_BAD_REQUEST)
        students = content_models.UserClassRoom.objects.prefetch_related("institute_rooms").filter(institute_rooms=section).values_list("user", flat=True)
        print("***********#####**",students)
        batch_obj.students.add(*students)
        batch_obj.save()
        return Response({ "message": "Mentor Assign Successfully and existing Room students have been added"})


class DeactivateMentorInBatchView(RetrieveUpdateAPIView):
    queryset = content_models.Batch.objects.all()
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        id = request.data['id']
        try:
            batch_obj = content_models.Batch.objects.get(pk=int(id))
        except:
            return Response({"message": "Please enter valid id"}, status=HTTP_400_BAD_REQUEST)
        try:
            batch_obj.is_active = False
            batch_obj.save()
        except:
            return Response({"message": "error in deactivating the mentor"}, status=HTTP_400_BAD_REQUEST)
        return Response({"message": "mentor deactivated successfully"}, status=201)


class ActivateMentorInBatchView(RetrieveUpdateAPIView):
    queryset = content_models.Batch.objects.all()
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        id = request.data['id']
        try:
            batch_obj = content_models.Batch.objects.get(pk=int(id))
        except:
            return Response({"message": "Please enter valid id"}, status=HTTP_400_BAD_REQUEST)
        try:
            batch_obj.is_active = True
            batch_obj.save()
        except:
            return Response({"message": "error in activating the mentor"}, status=HTTP_400_BAD_REQUEST)
        return Response({"message": "mentor activated successfully"}, status=201)


class CreateClassRoomBatchView(APIView):
    # serializer_class = serializers.ViewBatchSerializer

    def post(self, request, *args, **kwargs):
        #try:
        phonenumber = request.data.get('phonenumber')
        room = request.data.get('room')
        institute_room = content_models.InstituteClassRoom.objects.get(id=room)
        user=None
        user= User.objects.filter(phonenumber=phonenumber).last()
        if user:
            if user.profile.user_group.name == 'teacher':
                tmp_batch_obj = content_models.Batch.objects.filter(teacher=user, institute_room=institute_room)
                if tmp_batch_obj:
                    return Response({"message": "room batch already created for this mentor"}, status=HTTP_400_BAD_REQUEST)
                batch_obj = content_models.Batch.objects.create(teacher=user, batch_code=uuid.uuid4().hex[:6].upper(), institute_room=institute_room)
                
                # students = models.UserClassRoom.objects.filter(institute_rooms=institute_room)
                if len(batch_obj.students.all()) >= 250:
                    return Response({"message": "Maximum 250 students are allowed in a batch"}, status=HTTP_400_BAD_REQUEST)
                students = content_models.UserClassRoom.objects.prefetch_related("institute_rooms").filter(institute_rooms=institute_room).values_list("user", flat=True)
                batch_obj.students.add(*students)
                batch_obj.save()
                for student in students:
                    content_models.LearnerBatches.objects.create(user_id=student, batch=batch_obj)
                return Response({ "message": "Room Batch Successfully Created and existing Room students have been added"})
            else:
                return Response({"message": "not a mentor account"}, status=HTTP_400_BAD_REQUEST)
        else:
            # unreg_batch_obj = UnregisteredMentorBatch.objects.create(phonenumber=phonenumber, institute_room=institute_room)
            return Response({"message": "error in assigning the room"}, status=HTTP_400_BAD_REQUEST)
            #return Response({"message":"Room Assignment saved into buffer and will be created as soon as the mentor registers into MMP"}) @@sahi wala
        # except:
        #     return Response({"message": "error in assigning the room"}, status=HTTP_400_BAD_REQUEST)
        # return Response({"message": message}, status=201)



class StudentSearchApiView(APIView):
    permission_classes =(AllowAny,)
    def post(self,request):
        search=request.data.get('fullname',None)
        search1=request.data.get('phonenumber',None)
        search2=request.data.get('sr_number',None)
        class_id=request.data.get('class_id',None)
        section_id=request.data.get('section_id',None)

        if search and search1:
            qs=User.objects.filter(phonenumber__icontains=search1,fullname__icontains=search)
            data=StudentListSearchSerializer(qs,many=True,context={'request':request}).data
            return Response({'message':'Student Results List','data':data},status=HTTP_200_OK)
        
        if search1:
            qs=User.objects.filter(phonenumber__icontains=search1)
            data=StudentListSearchSerializer(qs,many=True,context={'request':request}).data
            return Response({'message':'Student Results List','data':data},status=HTTP_200_OK)

        if search2:
            qs=Profile.objects.filter(sr_number__icontains=search2)
            data=StudentListSearchSerializerProfile(qs,many=True,context={'request':request}).data
            return Response({'message':'Student Results List','data':data},status=HTTP_200_OK)

        if search:
            qs=User.objects.filter(fullname__icontains=search)
            data=StudentListSearchSerializer(qs,many=True,context={'request':request}).data
            return Response({'message':'Student Results List','data':data},status=HTTP_200_OK)
        
        if class_id and section_id:
            class_id1=UserClass.objects.get(id=class_id)
            section_id1=content_models.InstituteClassRoom.objects.get(id=section_id)
            qs=content_models.Batch.objects.filter(grade=class_id1,institute_room=section_id1)
            data=StudentListSearchSerializerProfile1(qs,many=True,context={'request':request}).data
            return Response({'message':'Student Results List','data':data},status=HTTP_200_OK)

        else:
            qs=[]
            return JsonResponse(qs,safe=False)

class StudentSearchMobileApiView(APIView):
    permission_classes =(AllowAny,)
    def post(self,request):
        search=request.data.get('phonenumber')
        if search:
            qs=User.objects.filter(phonenumber__icontains=search)
            data=StudentListSearchSerializer(qs,many=True,context={'request':request}).data
            return Response({'message':'Student Results List','data':data},status=HTTP_200_OK)
        else:
            qs=[]
            return JsonResponse(qs,safe=False)
        

class StudentSearchSchoolRegisterNumberApiView(APIView):
    permission_classes =(AllowAny,)
    def post(self,request):
        search=request.data.get('sr_number')
        if search:
            qs=Profile.objects.filter(sr_number__icontains=search)
            data=StudentListSearchSerializerProfile(qs,many=True,context={'request':request}).data
            return Response({'message':'Student Results List','data':data},status=HTTP_200_OK)
        else:
            qs=[]
            return JsonResponse(qs,safe=False)
    

class StudentSearchClassAndSectionApiView(APIView):
    permission_classes =(AllowAny,)
    def post(self,request):
        class_id=request.data.get('class_id')
        section_id=request.data.get('section_id')
        class_id1=UserClass.objects.get(id=class_id)
        section_id1=content_models.InstituteClassRoom.objects.get(id=section_id)
        qs=content_models.Batch.objects.filter(grade=class_id1,institute_room=section_id1)
        data=StudentListSearchSerializerProfile1(qs,many=True,context={'request':request}).data
        return Response({'message':'Student Results List','data':data},status=HTTP_200_OK)
      

class StudentRegisterApiView(APIView):
   # permission_classes = (IsAuthenticated,)
    def post(self,request):
        serializer=StudentRegisterSerializer(data=request.data,context={'request':request})
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({'message':'Student has been successfully Add For Selected Class'},status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

class EditStudentInBatchViewSet(APIView):
    # permission_classes = (IsAuthenticated,)
    def post(self,request):
        username = request.data['username']
        fullname = request.data['full_name']
        father_name = request.data['father_name']
        dob = request.data['dob']
        if check_blank_or_null([username]) and User.objects.filter(username=username).exists():
            user_obj = User.objects.filter(username=username).last()
            print(user_obj)
            profileO=Profile.objects.get(user=user_obj)
            profileO.father_name=father_name
            profileO.dob=dob
            name =fullname.split(" ")
            if len(name) >1:
                profileO.first_name = name[0]
                profileO.last_name =" ".join(name[1:])
            else:
                if len(name) == 1:
                    profileO.first_name = fullname
                    profileO.last_name =""
                else:
                    pass
            profileO.save()
            return Response({'message':'Student Detail Update Successfully '})
        return Response({'message':"Error in Update Student Details"},status=HTTP_400_BAD_REQUEST)

import logging
logger = logging.getLogger(__name__)

class AddStudentInBulk(APIView):
    def post(self,request):
        #excel = request.data['excel_file']
        excel = request.FILES.get('excel_file')
        logger.warning("****excel files *********")
        userclass_id = request.data['userclass_id']
        section_id = request.data['section_id']
        branch_id = self.request.query_params.get('branch_id')
        clsss=UserClass.objects.get(id=userclass_id)
        section=content_models.InstituteClassRoom.objects.get(id=section_id)
        user_group=UserGroup.objects.get(name='student')
        df = pd.io.excel.read_excel(excel)
        head_list = list(df.columns[0:])
        for index, row in df.iterrows():
            fullname = str(row["fullname"])
            print("*********************",fullname)
            logger.info('Information incoming! fullname')
            logger.warning("******Full Name Of Students *********")
            logger.error('Something went wrong! fullname')

            father_name = str(row["father_name"])
            print("*********************",father_name)
            logger.info('Information incoming! father_name')
            logger.error('Something went wrong! father_name')

            dob = str(row["dob"])
            print('*********************',dob)

            dob1=dob.split("/")
            dobO1=dob1[2]+"-"+dob1[1]+"-"+dob1[0]
            dobO=datetime.strptime(dobO1,'%Y-%m-%d')
            print("hello dob",dobO)
            last_user_created_id = User.objects.all().last().id
            username = create_username(str(10000 + last_user_created_id))
            user_obj = User.objects.create(username=username, fullname=fullname)
            user_obj.set_password(username)
            user_obj.save()
            logger.warning("*****user_obj warning ********")
            logger.debug("?????? debug of user_obj ???????")
            logger.info('Information incoming! on user_obj')
            logger.error('Something went wrong! on user_obj')
            print("*********************",user_obj)
            profileO=Profile.objects.get(user=user_obj)
            profileO.dob=dobO
            profileO.father_name=father_name
            profileO.user_group=user_group
            profileO.contact_verified=True
            profileO.account_verified=True
            profileO.designation=branch_id
            profileO.studentClass=clsss
            profileO.save()
            userroom_obj, _ = content_models.UserClassRoom.objects.get_or_create(user=user_obj)
            userroom_obj.institute_rooms.add(section)
            userroom_obj.save()
            batch_obj=content_models.Batch.objects.filter(grade=clsss,institute_room=section,is_active=True)
            print(batch_obj,"hello batch object ")
            logger.info('Information incoming! on batch_obj')
            logger.error('Something went wrong! on batch_obj')
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
        return Response({'message':"Student Data Upload Successfully "})
            

class AddSingleStudentInBatchViewSet(APIView):
    def post(self,request):
        try:
            phonenumber = request.data['phonenumber']
            userclass_id = request.data['userclass_id']
            section_id = request.data['section_id']
            branch_id = self.request.query_params.get('branch_id')
            clsss=UserClass.objects.get(id=userclass_id)
            section=content_models.InstituteClassRoom.objects.get(id=section_id)
            user_group=UserGroup.objects.get(name='student')
            user_obj = User.objects.filter(phonenumber=phonenumber).last()
            print(user_obj)
            if check_blank_or_null([phonenumber]) and Profile.objects.filter(user=user_obj,user_group=user_group).exists():
                    userroom_obj, _ = content_models.UserClassRoom.objects.get_or_create(user=user_obj)
                    userroom_obj.institute_rooms.add(section)
                    userroom_obj.save()
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
                            return Response({'message':"Student Add In the Batch Successfully"},status=HTTP_200_OK)
            else:
                last_user_created_id = User.objects.all().last().id
                username = create_username(str(10000 + last_user_created_id))
                user_obj = User.objects.create(username=username, phonenumber=phonenumber,fullname="")
                user_obj.set_password(username)
                user_obj.save()
                print("*********************",user_obj)
                profileO=Profile.objects.get(user=user_obj)
                profileO.user_group=user_group
                profileO.contact_verified=True
                profileO.account_verified=True
                profileO.designation=branch_id
                profileO.studentClass=clsss
                profileO.save()
                userroom_obj, _ = content_models.UserClassRoom.objects.get_or_create(user=user_obj)
                userroom_obj.institute_rooms.add(section)
                userroom_obj.save()
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
                        return Response({'message':"Student Added Successfully "})
        except:
            return Response({'message':"Error in adding student"},status=HTTP_400_BAD_REQUEST)

        

class StudentsViewMessageAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        user=request.user
        user_group=UserGroup.objects.get(name='student')
        profile=Profile.objects.filter(user=user,user_group=user_group,contact_verified=True).last()
        print(profile,'profile')
        qss=Communication.objects.filter(profile=profile).order_by("-id")[:10] 
        serializer=CommunicationSerializer(qss,many=True)
        return Response({'message':"All Message","data":serializer.data})


class SendMessageAllStudentsAPIView(APIView):
    def post(self,request):
        message=request.data.get('message')
        branch_id = self.request.query_params.get('branch_id')
        user_group=UserGroup.objects.get(name='student')
        qss=Profile.objects.filter(user_group=user_group,contact_verified=True,designation=branch_id)
        print(qss)
        for project in qss:
            com_obj=Communication.objects.create(profile=project,message=message)
            com_obj.save()
            print(qss,"hello hello frd ")
        return Response({'message':' Message Send Successfully '})


class SendMessageClassAndSectionWise(APIView):
    def post(self,request):
        branch_id = self.request.query_params.get('branch_id')
        userclass_id = request.data['userclass_id']
        section_id = request.data['section_id']
        message=request.data.get('message')
        user_group=UserGroup.objects.get(name='student')
        clsss=UserClass.objects.get(id=userclass_id)
        section=content_models.InstituteClassRoom.objects.get(id=section_id)

        batch_obj=content_models.Batch.objects.filter(grade=clsss,institute_room=section)
        for batch in batch_obj:
            qss=batch.students.all()
            for qs in qss:
                profile=Profile.objects.filter(user=qs,user_group=user_group,contact_verified=True,designation=branch_id).last()
                print("profile",profile)

                com_obj=Communication.objects.create(profile=profile,batch=batch,message=message)
                com_obj.save()
        return Response({'message':'Message Send Successfully'})


class SendMessageClassWise(APIView):
    def post(self,request):
        branch_id = self.request.query_params.get('branch_id')
        userclass_id = request.data['userclass_id']
        # section_id = request.data['section_id']
        message=request.data.get('message')
        user_group=UserGroup.objects.get(name='student')
        clsss=UserClass.objects.get(id=userclass_id)
       # section=content_models.InstituteClassRoom.objects.get(id=section_id)

        batch_obj=content_models.Batch.objects.filter(grade=clsss)
        for batch in batch_obj:
            qss=batch.students.all()
            for qs in qss:
                profile=Profile.objects.filter(user=qs,user_group=user_group,contact_verified=True,designation=branch_id).last()
                print("profile",profile)

                com_obj=Communication.objects.create(profile=profile,batch=batch,message=message)
                com_obj.save()
        return Response({'message':'Message Send Successfully'})



class SendMessageStudentWise(APIView):
    def post(self,request):
       # userclass_id = request.data['userclass_id']
       # section_id = request.data['section_id']
        branch_id = self.request.query_params.get('branch_id')
        sr_number = request.data['sr_number']
        message = request.data['message']
        student_name = request.data['student_name']
        user=User.objects.filter(fullname=student_name).last()
        print("user",user)
        user_group=UserGroup.objects.get(name='student')
        print("user_group",user_group)
        qss=Profile.objects.filter(user=user,user_group=user_group,contact_verified=True,sr_number=sr_number,designation=branch_id)
        print('qss',qss)
        for project in qss:
            com_obj=Communication.objects.create(profile=project,message=message)
            com_obj.save()
        return Response({'message':'Message Send Successfully '})


class SendMessageStudentUserIdWise(APIView):
    def post(self,request):
       # userclass_id = request.data['userclass_id']
       # section_id = request.data['section_id']
        branch_id = self.request.query_params.get('branch_id')
        sr_number = request.data['user_id']
        message = request.data['message']
        student_name = request.data['student_name']
        user=User.objects.filter(fullname=student_name,username=sr_number).last()
        print("user",user)
        user_group=UserGroup.objects.get(name='student')
        print("user_group",user_group)
        qss=Profile.objects.filter(user=user,user_group=user_group,contact_verified=True,designation=branch_id)
        print('qss',qss)
        for project in qss:
            com_obj=Communication.objects.create(profile=project,message=message)
            com_obj.save()
        return Response({'message':'Message Send Successfully '})

######################################### Mentor work report api start ########################################################

class FetchMentorPapersViewSetAPI(ListAPIView):
    queryset = content_models.MentorPapers.objects.all()
    serializer_class = serializers.CardViewMentorPaperSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = core_paginations.CustomPagination5

    def get_queryset(self):
        user = self.request.user
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            batch_obj = content_models.Batch.objects.get(id=int(batch_id))
            if batch_obj:
                learner_paper_obj = content_models.MentorPapers.objects.filter(batch=batch_obj)
            if not batch_obj:
                raise ParseError("Batch with this id DoesNotExist")
        if not batch_id:
            learner_paper_obj = content_models.MentorPapers.objects.filter(mentor=user)
        if learner_paper_obj:
            return learner_paper_obj
        else:
            return []


class EditBatchViewSetAPI(RetrieveUpdateAPIView):
    queryset = content_models.Batch.objects.all()
    serializer_class = serializers.ViewBatchSerializer
    update_serializer_class = serializers.CreateBatchSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        batch = content_models.Batch.objects.filter(pk=self.kwargs.get('pk'))
        if not batch:
            raise ParseError("Batch with this id DoesNotExist")
        return batch

    def update(self, request, *args, **kwargs):
        batch = content_models.Batch.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            batch, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(batch).data, status=HTTP_200_OK)


class FetchLearnerBatchHistoryViewSetAPI(ListAPIView):
    queryset = content_models.LearnerBatchHistory.objects.all()
    serializer_class = serializers.LearnerBatchHistorySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            batch_obj = content_models.Batch.objects.get(id=int(batch_id))
            if batch_obj:
                learner_batch_history_obj = content_models.LearnerBatchHistory.objects.filter(batch=batch_obj, is_blocked=False)
            if not batch_obj:
                raise ParseError("Batch with this id DoesNotExist")
        if not batch_id:
            raise ParseError("Please select at least one batch")
        if learner_batch_history_obj:
            return learner_batch_history_obj
        else:
            return []


class FetchAllAnswerPapersInTheMentorPaperViewSetAPI(ListAPIView):
    queryset = content_models.MentorPaperAnswerPaper.objects.all()
    serializer_class = serializers.MentorLearnerAnswerPaperSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        paper_id = self.request.query_params.get('paper')
        if paper_id:
            paper_obj = content_models.MentorPapers.objects.get(id=int(paper_id))
            if paper_obj:
                learner_paper_obj = content_models.MentorPaperAnswerPaper.objects.filter(mentor_paper=paper_obj).order_by('score')
            if not paper_obj:
                raise ParseError("Paper with this id DoesNotExist")
        if not paper_id:
            raise ParseError("Please enter paper id")
        if learner_paper_obj:
            return learner_paper_obj
        else:
            return []


class MentorAssessmentPaperAllUserReportViewAPI(ListAPIView):
    permission_classes = [IsAuthenticated,]

    def get_queryset(self):
        reports = content_utils.get_mentor_paper_all_student_assessment_report(self.kwargs.get('assessmentpaper_id'))

        if not reports:
            # return blank queryset if reports not received
            return None
        return reports
        

    def list(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            return Response({
                'report_data':queryset
            })
        else:
            return Response({
                'report_data':[]
            })
        return Response({'error': 'Error in Assessment Paper.'}, status=HTTP_429_TOO_MANY_REQUESTS)


class MentorAssessmentQuestionWiseAnalysisReportViewAPI(ListAPIView):
    permission_classes = [IsAuthenticated,]

    def get_queryset(self):
        reports = content_utils.MentorAssessmentTestQuestionwiseAnalysisReport(self.kwargs.get('assessmentpaper_id'))

        if not reports:
            # return blank queryset if reports not received
            return None
        return reports
        

    def list(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            return Response(queryset)
        return Response({'error': 'Error in Assessment Paper.'}, status=HTTP_429_TOO_MANY_REQUESTS)

class MentorAssessmentSingleQuestionAnalysisReportViewAPI(ListAPIView):
    permission_classes = [IsAuthenticated,]

    def get_queryset(self):
        questionid = self.request.query_params.get('question')
        reports = content_utils.MentorAssessmentIndividualQuestionAnalysisReport(self.kwargs.get('assessmentpaper_id'), questionid)

        if not reports:
            # return blank queryset if reports not received
            return None
        return reports
        

    def list(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            return Response(queryset)
        return Response({'error': 'Error in Assessment Paper.'}, status=HTTP_429_TOO_MANY_REQUESTS)

    

class DeleteMentorPaperTempQuesReplaceViewSetAPI(UpdateAPIView):
    queryset = content_models.TemporaryMentorPaperReplaceQuestions.objects.all()

    def put(self, request, *args, **kwargs):
        paperid = request.data.get('paper')
        if not paperid:
            raise ParseError("Please enter exam id")
        paperobj = content_models.MentorPapers.objects.get(id=int(paperid))
        if not paperobj:
            raise ParseError("Paper with this id DoesNotExist")
        try:
            hint_obj = content_models.TemporaryMentorPaperReplaceQuestions.objects.filter(paper=paperobj)
            hint_obj.delete()
        except:
            return Response({"message": "Some error while deletion"}, status=HTTP_400_BAD_REQUEST)
        return Response({"message": "Temporary replacement questions deleted successfully"}, status=201)



class FetchMentorPaperByIdViewSetAPI(RetrieveUpdateAPIView):
    queryset = content_models.MentorPapers.objects.all()
    serializer_class = serializers.MentorPaperSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        mentor_paper_obj = content_models.MentorPapers.objects.filter(pk=self.kwargs.get('pk'))
        if not mentor_paper_obj:
            raise ParseError("Mentor paper with this id DoesNotExist")
        return mentor_paper_obj

    def list(self, request, *args, **kwargs):
        paper_obj = content_models.MentorPapers.objects.get(id=self.kwargs.get('pk'))
        assessmentpaperdetails = serializers.MentorPaperSerializer(paper_obj, context={'request': request})
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            serializer = self.get_serializer(queryset[0], many=True)
            return Response({
                'paperdetails':assessmentpaperdetails.data,
                'question_data':queryset[1],
            })
        return Response({'error': 'Error in Paper.'}, status=HTTP_429_TOO_MANY_REQUESTS)



class EditQuestionViewSetAPI(RetrieveUpdateAPIView):
    queryset = content_models.Question.objects.all()
    serializer_class = serializers.QuestionSerializer
    update_serializer_class = serializers.EditQuestionSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        question = content_models.Question.objects.filter(pk=self.kwargs.get('pk'))
        if not question:
            raise ParseError("Question with this id DoesNotExist")
        return question

    def update(self, request, *args, **kwargs):
        question = content_models.Question.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            question, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(question).data, status=HTTP_200_OK)



class SolutionViewSetAPI(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.SolutionSerializer
    create_class = serializers.CreateSolutionSerializer

    def get_queryset(self):
        content_id = self.request.query_params.get('content')
        if content_id:
            content_obj = content_models.QuestionContent.objects.get(
                id=int(content_id))
            solution = content_models.Solution.objects.filter(
                questioncontent=content_obj)
            return solution
        return content_models.Solution.objects.all()

    def create(self, request, *args, **kwargs):
        if Profile.objects.get(user=request.user).user_group.name in ['admin']:
            serializer = self.create_class(
                data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=HTTP_201_CREATED)
        else:
            return Response({"message": "You do not have permission to create question"}, status=HTTP_400_BAD_REQUEST)



class MCQTestCaseViewSetAPI(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.MCQTestCaseSerializer
    create_class = serializers.CreateMCQTestCaseSerializer

    def get_queryset(self):
        content_id = self.request.query_params.get('content')
        if content_id:
            content_obj = content_models.QuestionContent.objects.get(
                id=int(content_id))
            solution = content_models.McqTestCase.objects.filter(
                questioncontent=content_obj).order_by('id')
            return solution
        return content_models.McqTestCase.objects.all().order_by('id')

    def create(self, request, *args, **kwargs):
        if Profile.objects.get(user=request.user).user_group.name in ['admin']:
            serializer = self.create_class(
                data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=HTTP_201_CREATED)
        else:
            return Response({"message": "You do not have permission to create question"}, status=HTTP_400_BAD_REQUEST)

from django.utils import timezone

class FindReplacementQuestionViewSetAPI(ListAPIView):
    queryset = content_models.Question.objects.all()
    serializer_class = serializers.QuestionSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        question_id = self.request.query_params.get('question')
        paper_id = self.request.query_params.get('paper')
        paper_obj = content_models.MentorPapers.objects.get(id=int(paper_id))
        if not paper_obj:
            raise ParseError("Paper with this id DoesNotExist")
        currenttime = timezone.now()
        if currenttime >= paper_obj.exam_start_date_time:
            raise ParseError("You cannot replace the question once the test has started")
        quesIds = []
        questions = paper_obj.questions.all()
        quesIds = [question.id for question in questions]
        tempques = None
        
        tempques, _ = content_models.TemporaryMentorPaperReplaceQuestions.objects.get_or_create(paper=paper_obj)
        tmpqueslist = tempques.questions.all()
        if len(tmpqueslist) > 0:
            for ques in tmpqueslist:
                quesIds.append(ques.id)
        if question_id:
            question_obj = content_models.Question.objects.get(id=int(question_id))
            if question_obj:
                tagIds = []
                ftags = question_obj.linked_topics.all()
                tagIds = [tag.id for tag in ftags]
                eng_obj = content_models.QuestionLanguage.objects.get(text='English')
                try:
                    new_ques_obj = content_models.Question.objects.filter(is_active=True, linked_topics__in=tagIds, languages=eng_obj, difficulty=question_obj.difficulty, type_of_question=question_obj.type_of_question).order_by('?').distinct().exclude(id__in=quesIds)[:1]
                    
                except:
                    return Response({"message": "no replacement question found"}, status=HTTP_400_BAD_REQUEST)
            if not question_obj:
                raise ParseError("Question with this id DoesNotExist")
        if not question_id:
            raise ParseError("Please select at least one question")
        if new_ques_obj:
            tempques.questions.add(new_ques_obj[0].id)
            tempques.save()
            return new_ques_obj
        else:
            return []


class ReplaceQuestionInMentorPaperViewAPI(UpdateAPIView):
    serializer_class = serializers.MentorPaperSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        try:
            questionid = request.data.get('question')
            ques_obj = content_models.Question.objects.get(id=int(questionid))
        except:
            ques_obj = None
        if not ques_obj:
            return Response({"message": "question with this id does not exist"}, status=HTTP_400_BAD_REQUEST)
        try:
            newquestionid = request.data.get('newquestion')
            newquestion_obj = content_models.Question.objects.get(id=int(newquestionid))
        except:
            newquestion_obj = None
        if not newquestion_obj:
            return Response({"message": "replacement question with this id does not exist"}, status=HTTP_400_BAD_REQUEST)
        try:
            paperid = request.data.get('paper')
            assessmentpaper_obj = content_models.MentorPapers.objects.get(id=int(paperid))
            currenttime = timezone.now()
            exam_end_date_time = assessmentpaper_obj.exam_end_date_time
            if currenttime >= exam_end_date_time:
                return Response({'message': 'you cannot change the questions now, you are ahead of exam start time..' }, status=HTTP_400_BAD_REQUEST)
        except:
            assessmentpaper_obj = None
        if not assessmentpaper_obj:
            return Response({"message": "error in fetching paper details"}, status=HTTP_400_BAD_REQUEST)
        else:
            assessmentpaper_obj.questions.remove(ques_obj)
            assessmentpaper_obj.save()
            assessmentpaper_obj.questions.add(newquestion_obj)
            assessmentpaper_obj.save()
            content_models.TemporaryMentorPaperReplaceQuestions.objects.filter(paper=assessmentpaper_obj).delete()
           
        return Response(self.serializer_class(assessmentpaper_obj).data, status=201)

class FillUpSolutionViewSetAPI(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.FillUpSolutionSerializer
    create_class = serializers.CreateFillUpSolutionSerializer

    def get_queryset(self):
        content_id = self.request.query_params.get('content')
        if content_id:
            content_obj = content_models.QuestionContent.objects.get(
                id=int(content_id))
            solution = content_models.FillUpSolution.objects.filter(
                questioncontent=content_obj)
            return solution
        return content_models.FillUpSolution.objects.all()

    def create(self, request, *args, **kwargs):
        if Profile.objects.get(user=request.user).user_group.name in ['admin']:
            serializer = self.create_class(
                data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=HTTP_201_CREATED)
        else:
            return Response({"message": "You do not have permission to create question"}, status=HTTP_400_BAD_REQUEST)


class EditFillUpViewSetAPI(RetrieveUpdateAPIView):
    queryset = content_models.FillUpSolution.objects.all()
    serializer_class = serializers.FillUpSolutionSerializer
    update_serializer_class = serializers.EditFillUpSolutionSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser,)

    def get_queryset(self):
        solution = content_models.FillUpSolution.objects.filter(
            pk=self.kwargs.get('pk'))
        if not solution:
            raise ParseError("Fill Up with this id DoesNotExist")
        return solution

    def update(self, request, *args, **kwargs):
        solution = content_models.FillUpSolution.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            solution, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(solution).data, status=HTTP_200_OK)
        


class FillUpWithOptionCaseViewSetAPI(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.FillWithOptionCaseSerializer
    create_class = serializers.CreateFillWithOptionSerializer

    def get_queryset(self):
        content_id = self.request.query_params.get('content')
        if content_id:
            content_obj = content_models.QuestionContent.objects.get(
                id=int(content_id))
            solution = content_models.FillUpWithOption.objects.filter(
                questioncontent=content_obj).order_by('id')
            return solution
        return content_models.FillUpWithOption.objects.all().order_by('id')

    def create(self, request, *args, **kwargs):
        if Profile.objects.get(user=request.user).user_group.name in ['admin']:
            serializer = self.create_class(
                data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=HTTP_201_CREATED)
        else:
            return Response({"message": "You do not have permission to create question"}, status=HTTP_400_BAD_REQUEST)


class EditFillUpWithOptionViewSetAPI(RetrieveUpdateAPIView):
    queryset = content_models.McqTestCase.objects.all()
    serializer_class = serializers.FillWithOptionCaseSerializer
    update_serializer_class = serializers.EditFillWithOptionSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser,)

    def get_queryset(self):
        solution = content_models.FillUpWithOption.objects.filter(pk=self.kwargs.get('pk'))
        if not solution:
            raise ParseError("McqTestCase with this id DoesNotExist")
        return solution

    def update(self, request, *args, **kwargs):
        solution = content_models.FillUpWithOption.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            solution, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(solution).data, status=HTTP_200_OK)

class BooleanTypeViewSetAPI(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.BooleanTypeSerializer
    create_class = serializers.CreateBooleanTypeSerializer

    def get_queryset(self):
        content_id = self.request.query_params.get('content')
        if content_id:
            content_obj = content_models.QuestionContent.objects.get(
                id=int(content_id))
            solution = content_models.TrueFalseSolution.objects.filter(
                questioncontent=content_obj)
            return solution
        return content_models.TrueFalseSolution.objects.all()

    def create(self, request, *args, **kwargs):
        if Profile.objects.get(user=request.user).user_group.name in ['admin']:
            serializer = self.create_class(
                data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=HTTP_201_CREATED)
        else:
            return Response({"message": "You do not have permission to create question"}, status=HTTP_400_BAD_REQUEST)


class EditBooleanTypeViewSetAPI(RetrieveUpdateAPIView):
    queryset = content_models.TrueFalseSolution.objects.all()
    serializer_class = serializers.BooleanTypeSerializer
    update_serializer_class = serializers.CreateBooleanTypeSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser,)

    def get_queryset(self):
        solution = content_models.TrueFalseSolution.objects.filter(
            pk=self.kwargs.get('pk'))
        if not solution:
            raise ParseError("Data with this id DoesNotExist")
        return solution

    def update(self, request, *args, **kwargs):
        solution = content_models.TrueFalseSolution.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            solution, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(solution).data, status=HTTP_200_OK)

class CourseViewSetAPI(ListAPIView, CreateAPIView):
    # permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializer.ExamSerializer
    parser_classes = (FormParser, MultiPartParser)
    queryset = courses_models.Exam.objects.select_related("level").prefetch_related("subjects", "userclass", "userboard")

    def get_queryset(self):
        level_id = self.request.query_params.get('level')
        if level_id:
            exam = self.queryset.filter(level__id=level_id)
            return exam
        return self.queryset.filter(is_active=True)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=HTTP_201_CREATED)

class AllCourseViewSetAPI(ListAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializer.ExamSerializer
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        level_id = self.request.query_params.get('level')
        if level_id:
            level_obj = courses_models.ExamLevel.objects.get(
                id=int(level_id))
            if level_obj:
                exam = courses_models.Exam.objects.filter(
                    level=level_obj)
                return exam
        return courses_models.Exam.objects.all()

class EditCourseViewAPI(RetrieveUpdateAPIView):
    queryset = courses_models.Exam.objects.all()
    serializer_class = serializer.ExamSerializer
    lookup_field = 'pk'
    # permission_classes = (IsAuthenticated,)
    parser_class = (FileUploadParser)

    def get_queryset(self):
        courseObj = courses_models.Exam.objects.filter(pk=self.kwargs.get('pk'))
        if not courseObj:
            raise ParseError("Exam with this id DoesNotExist")
        return courseObj


class BatchStudentPaperCountView(ListAPIView):
    serializer_class = serializers.MentorPaperSerializer
    permission_classes = [IsAuthenticated,]

    def get(self,request,*args, **kwargs):
        batch_id = self.kwargs.get('batch_id')
        batch_obj = content_models.Batch.objects.get(id=int(batch_id))
        currenttime = timezone.now()
        assessment_test_obj = content_models.MentorPapers.objects.filter(
        batch=batch_obj)
        paperIds = []
        paperIds = [paper.id for paper in assessment_test_obj]
        total_papers_generated = len(assessment_test_obj)
        return Response({'Total Practice/ Paper Assigned':total_papers_generated})

    # def get_queryset(self):
    #     try:*args, **kwargs
    #         user=None
    #         if self.request.query_params.get('user'):
    #             user= User.objects.get(username=self.request.query_params.get('user'))
    #         else:
    #             user = self.request.user
    #     except:
    #         user = self.request.user
    #     my_data = content_utils.get_user_papercount_in_batch(user, self.kwargs.get('batch_id'))
    #     if not my_data:
    #         return None
    #     else:
    #         return my_data

    # def list(self, request, *args, **kwargs):
    #     queryset = self.filter_queryset(self.get_queryset())
    #     if queryset:
    #         return Response({
    #             'paper_count_data': queryset[0]
    #         })
    #     return Response({'error': 'Error in Fetching Paper count Data.'}, status=HTTP_429_TOO_MANY_REQUESTS)



#################################### Third Party Api Integration dont use this side of api #########################################

class AllExamIdAndExamName(APIView):
    def get(self,request):
        qs = courses_models.Exam.objects.all().order_by('-id')
        data=AllExamIdAndExamNameSerializer(qs, many=True, context={'request':request}).data
        return Response({'message':"All Exam Id And Exam Name",'data':data})

class AllExamDetails(RetrieveUpdateAPIView):
    queryset = courses_models.Exam.objects.all()
    serializer_class = serializer.ExamSerializer
    lookup_field = 'pk'
    # permission_classes = (IsAuthenticated,)
    parser_class = (FileUploadParser)

    def get_queryset(self):
        courseObj = courses_models.Exam.objects.filter(pk=self.kwargs.get('pk'))
        if not courseObj:
            raise ParseError("Exam with this id DoesNotExist")
        return courseObj

# class AllExamDetails(APIView):
#     def post(self,request):
#         exam_id = request.data.get('exam_id')
#         qs = courses_models.Exam.objects.filter(id=exam_id)
#         data=AllExamNameDetailsSerializer(qs, many=True, context={'request':request}).data
#         return Response({'message':"All Exam Details By Exam Id",'data':data})


class RegisterMentorWitEmailAndPassword(APIView):
    def post(self,request):
        email = request.data["email"]
        password = request.data["password"]
        apikeys=request.data.get('apikeys')
        if not apikeys:
            return Response({"message": "Enter Valid API Keys "}, status=HTTP_400_BAD_REQUEST)
        if APIKeysForVerify.objects.filter(keyvalues=apikeys).exists():
            user_group=UserGroup.objects.get(name='teacher')
            if User.objects.filter(email=email).exists():
                raise ValidationError('Email allready exists')
            last_user_created_id = User.objects.all().last().id
            username = create_username(str(10000 + last_user_created_id))
            user_obj = User.objects.create(username=username,fullname="",email=email)
            user_obj.set_password(password)
            user_obj.save()
            print("*********************",user_obj)
            profileO=Profile.objects.get(user=user_obj)
            profileO.user_group=user_group
            profileO.contact_verified=True
            profileO.account_verified=True
            profileO.save()
            return Response({'message':'Mentor Register Successfully'})
        return Response({"message": "This API Key Not Valid Please contect MMP issue New API Keys"}, status=HTTP_400_BAD_REQUEST)



class RegisterUserWitEmailAndPassword(APIView):
    def post(self,request):
        email = request.data["email"]
        password = request.data["password"]
        apikeys=request.data.get('apikeys')
        if not apikeys:
            return Response({"message": "Enter Valid API Keys "}, status=HTTP_400_BAD_REQUEST)
        if APIKeysForVerify.objects.filter(keyvalues=apikeys).exists():
            user_group=UserGroup.objects.get(name='student')
            if User.objects.filter(email=email).exists():
                raise ValidationError('Email allready exists')
            last_user_created_id = User.objects.all().last().id
            username = create_username(str(10000 + last_user_created_id))
            user_obj = User.objects.create(username=username,fullname="",email=email)
            user_obj.set_password(password)
            user_obj.save()
            print("*********************",user_obj)
            profileO=Profile.objects.get(user=user_obj)
            profileO.user_group=user_group
            profileO.contact_verified=True
            profileO.account_verified=True
            profileO.save()
            return Response({'message':'User Register Successfully'})
        return Response({"message": "This API Key Not Valid Please contect MMP issue New API Keys"}, status=HTTP_400_BAD_REQUEST)

class StudentChangePassword(APIView):
    def post(self,request):
        email = request.data["email"]
        confirm_password = request.data["confirm_password"]
        apikeys=request.data.get('apikeys')
        if not apikeys:
            return Response({"message": "Enter Valid API Keys "}, status=HTTP_400_BAD_REQUEST)
        if APIKeysForVerify.objects.filter(keyvalues=apikeys).exists():
            user_group=UserGroup.objects.get(name='student')
            user_obj = User.objects.filter(email=email).last()
            if not user_obj:
                raise ValidationError('Student Not Register MakeMyPath Portal.. Please Register')
            if Profile.objects.filter(user=user_obj,user_group=user_group).exists():
                user_obj = User.objects.get(email=email)
                user_obj.set_password(confirm_password)
                user_obj.save()
                return Response({'message':'Password Change Successfully '})

            return Response({'message':"Student Not Register MakeMyPath Portal.. Please Register"},status=HTTP_400_BAD_REQUEST)
        return Response({"message": "This API Key Not Valid Please contect MMP issue New API Keys"}, status=HTTP_400_BAD_REQUEST)

class MentorChangePassword(APIView):
    def post(self,request):
        email = request.data["email"]
        confirm_password = request.data["confirm_password"]
        apikeys=request.data.get('apikeys')
        if not apikeys:
            return Response({"message": "Enter Valid API Keys "}, status=HTTP_400_BAD_REQUEST)
        if APIKeysForVerify.objects.filter(keyvalues=apikeys).exists():
            user_group=UserGroup.objects.get(name='teacher')
            user_obj = User.objects.filter(email=email).last()
            if not user_obj:
                raise ValidationError('Student Not Register MakeMyPath Portal.. Please Register')
            if Profile.objects.filter(user=user_obj,user_group=user_group).exists():
                user_obj = User.objects.get(email=email)
                user_obj.set_password(confirm_password)
                user_obj.save()
                return Response({'message':'Password Change Successfully '})

            return Response({'message':"Mentor Not Register MakeMyPath Portal.. Please Register"},status=HTTP_400_BAD_REQUEST)
        return Response({"message": "This API Key Not Valid Please contect MMP issue New API Keys"}, status=HTTP_400_BAD_REQUEST)


class DeactivateBatchView1(RetrieveUpdateAPIView):
    queryset = content_models.Batch.objects.all()
    serializer_class = ViewBatchSerializer1
    lookup_field = 'pk'
    #permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        
        batch_obj = content_models.Batch.objects.select_related("teacher", "name", "teacher__profile", "batch_code", "students"
        ).filter(pk=self.kwargs.get('pk')).order_by('id')
        if not batch_obj:
            raise ParseError("Batch data with this id DoesNotExist")
        return batch_obj

    def put(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        apikeys=request.data.get('apikeys')
        if not apikeys:
            return Response({"message": "Enter Valid API Keys "}, status=HTTP_400_BAD_REQUEST)
        if APIKeysForVerify.objects.filter(keyvalues=apikeys).exists():
            try:
                batch_obj = content_models.Batch.objects.get(pk=int(id))
            except:
                return Response({"message": "Please enter valid id"}, status=HTTP_400_BAD_REQUEST)
            try:
                batch_obj.is_active = False
                batch_obj.save()
            except:
                return Response({"message": "error in deactivating the batch"}, status=HTTP_400_BAD_REQUEST)
            return Response({"message": "batch deactivated successfully"}, status=201)
        return Response({"message": "This API Key Not Valid Please contect MMP issue New API Keys"}, status=HTTP_400_BAD_REQUEST)



class ActivateBatchView1(RetrieveUpdateAPIView):
    queryset = content_models.Batch.objects.all()
    serializer_class = ViewBatchSerializer1
    lookup_field = 'pk'
    #permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        
        batch_obj = content_models.Batch.objects.select_related("teacher", "name", "teacher__profile", "batch_code", "students"
        ).filter(pk=self.kwargs.get('pk')).order_by('id')
        if not batch_obj:
            raise ParseError("Batch data with this id DoesNotExist")
        return batch_obj

    def put(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        apikeys=request.data.get('apikeys')
        if not apikeys:
            return Response({"message": "Enter Valid API Keys "}, status=HTTP_400_BAD_REQUEST)
        if APIKeysForVerify.objects.filter(keyvalues=apikeys).exists():
            try:
                batch_obj = content_models.Batch.objects.get(pk=int(id))
            except:
                return Response({"message": "Please enter valid id"}, status=HTTP_400_BAD_REQUEST)
            try:
                batch_obj.is_active = True
                batch_obj.save()
            except:
                return Response({"message": "error in activating the batch"}, status=HTTP_400_BAD_REQUEST)
            return Response({"message": "batch activated successfully"}, status=201)

        return Response({"message": "This API Key Not Valid Please contect MMP issue New API Keys"}, status=HTTP_400_BAD_REQUEST)



class DeLeteBatchView(RetrieveUpdateAPIView):
    queryset = content_models.Batch.objects.all()
    serializer_class = ViewBatchSerializer1
    lookup_field = 'pk'
    #permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        
        batch_obj = content_models.Batch.objects.select_related("teacher", "name", "teacher__profile", "batch_code", "students"
        ).filter(pk=self.kwargs.get('pk')).order_by('id')
        if not batch_obj:
            raise ParseError("Batch data with this id DoesNotExist")
        return batch_obj

    def put(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        apikeys=request.data.get('apikeys')
        if not apikeys:
            return Response({"message": "Enter Valid API Keys"}, status=HTTP_400_BAD_REQUEST)
        if APIKeysForVerify.objects.filter(keyvalues=apikeys).exists():
            try:
                batch_obj = content_models.Batch.objects.get(pk=int(id))
                print(batch_obj)
            except:
                return Response({"message": "Please enter valid id"}, status=HTTP_400_BAD_REQUEST)
            try:
                # batch_obj.is_active = False
                # batch_obj.save()
                batch_obj.delete()
            except:
                return Response({"message": "error in deactivating the batch"}, status=HTTP_400_BAD_REQUEST)
            return Response({"message": "batch delete successfully"}, status=201)
        return Response({"message": "This API Key Not Valid Please contect MMP issue New API Keys"}, status=HTTP_400_BAD_REQUEST)



class FetchRoomBatchesViewSet2(APIView):
    #permission_classes = (IsAuthenticated,)
    def post(self,request):
        apikeys=request.data.get('apikeys')
        if not apikeys:
            return Response({"message": "Enter Valid API Keys"}, status=HTTP_400_BAD_REQUEST)
        if APIKeysForVerify.objects.filter(keyvalues=apikeys).exists():
            serializer=CreateBatchSerializer1(data=request.data,context={'request':request})
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response({'data':serializer.data},status=HTTP_200_OK)
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
        return Response({"message": "This API Key Not Valid Please contect MMP issue New API Keys"}, status=HTTP_400_BAD_REQUEST)




class InstituteClassRoomViewSet2(ListAPIView, CreateAPIView):
    #permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = ViewInstituteClassRoomSerializer12
    create_class = CreateInstituteRoomSerializer2

    def get_queryset(self):
        institute = self.request.query_params.get('institute')
        unique_id = self.request.query_params.get('unique_id')
        if unique_id:
            rooms = content_models.InstituteClassRoom.objects.filter(unique_id=unique_id)
        else:
            rooms = content_models.InstituteClassRoom.objects.all()
        return rooms
        # return models.LearnerQuery.objects.all().order_by('id')

    def create(self, request, *args, **kwargs):
        serializer = self.create_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=HTTP_201_CREATED)



class BatchViewSet1(ListAPIView, CreateAPIView):
    serializer_class = ViewBatchSerializer1

    def get_queryset(self):
        email = self.request.query_params.get('email')
        unique_id = self.request.query_params.get('unique_id')
        apikeys= self.request.query_params.get('apikeys')
        if not apikeys:
            raise ValidationError("Enter Valid API Keys")
        if APIKeysForVerify.objects.filter(keyvalues=apikeys).exists():

            rooms = content_models.InstituteClassRoom.objects.filter(unique_id=unique_id).last()
            print(rooms)
            user = User.objects.filter(email=email).last()
            print(user)
            batches = content_models.Batch.objects.filter(teacher=user, is_active=True,institute_room=rooms)
            if batches:
                return batches
            else:
                return []
        raise ValidationError('This API Key Not Valid Please contect MMP issue New API Keys')


class CreateClassRoomBatchView1(APIView):
    # serializer_class = serializers.ViewBatchSerializer

    def post(self, request, *args, **kwargs):
        #try:
        email = request.data.get('email')
        unique_id = request.data.get('unique_id')
        apikeys=request.data.get('apikeys')
        if not apikeys:
            return Response({"message": "Enter Valid API Keys"}, status=HTTP_400_BAD_REQUEST)
        if APIKeysForVerify.objects.filter(keyvalues=apikeys).exists():
            institute_room = content_models.InstituteClassRoom.objects.get(unique_id=unique_id)
            print(institute_room)
            user=None
            user= User.objects.filter(email=email).last()
            if user:
                if user.profile.user_group.name == 'teacher':
                    tmp_batch_obj = content_models.Batch.objects.filter(teacher=user, institute_room=institute_room)
                    if tmp_batch_obj:
                        return Response({"message": "room batch already created for this mentor"}, status=HTTP_400_BAD_REQUEST)
                    batch_obj = content_models.Batch.objects.create(teacher=user, batch_code=uuid.uuid4().hex[:6].upper(), institute_room=institute_room)
                    
                    # students = models.UserClassRoom.objects.filter(institute_rooms=institute_room)
                    if len(batch_obj.students.all()) >= 250:
                        return Response({"message": "Maximum 250 students are allowed in a batch"}, status=HTTP_400_BAD_REQUEST)
                    students = content_models.UserClassRoom.objects.prefetch_related("institute_rooms").filter(institute_rooms=institute_room).values_list("user", flat=True)
                    batch_obj.students.add(*students)
                    batch_obj.save()
                    for student in students:
                        content_models.LearnerBatches.objects.create(user_id=student, batch=batch_obj)
                    return Response({ "message": "Room Batch Successfully Created and existing Room students have been added"})
                else:
                    return Response({"message": "not a mentor account"}, status=HTTP_400_BAD_REQUEST)
            else:
                # unreg_batch_obj = UnregisteredMentorBatch.objects.create(phonenumber=phonenumber, institute_room=institute_room)
                return Response({"message":"Room Assignment saved into buffer and will be created as soon as the mentor registers into MMP"})
        # except:
        #     return Response({"message": "error in assigning the room"}, status=HTTP_400_BAD_REQUEST)
        # return Response({"message": message}, status=201)
        return Response({"message": "This API Key Not Valid Please contect MMP issue New API Keys"}, status=HTTP_400_BAD_REQUEST)





class AddStudentRoomBatchView(APIView):
    def post(self,request):
        email = request.data['email']
        unique_id = request.data['unique_id']
        apikeys=request.data.get('apikeys')
        if not apikeys:
            return Response({"message": "Enter Valid API Keys"}, status=HTTP_400_BAD_REQUEST)
        if APIKeysForVerify.objects.filter(keyvalues=apikeys).exists():
            user_group=UserGroup.objects.get(name='student')
            user_obj = User.objects.filter(email=email).last()
            print(user_obj)
            institute_room = content_models.InstituteClassRoom.objects.get(unique_id=unique_id)
            print(institute_room)
            if not user_obj:
                raise ValidationError('Student Not Register MakeMyPath Portal.. Please Register')

            if check_blank_or_null([email]) and Profile.objects.filter(user=user_obj,user_group=user_group).exists():
                batch_obj=content_models.Batch.objects.filter(is_active=True,institute_room=institute_room)
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
                        return Response({'message':"Student Add In the Batch Successfully"},status=HTTP_200_OK)

            return Response({'message':"Student Not Register MakeMyPath Portal.. Please Register"},status=HTTP_400_BAD_REQUEST)

        return Response({"message": "This API Key Not Valid Please contect MMP issue New API Keys"}, status=HTTP_400_BAD_REQUEST)
 


class FetchLearnerPapersViewSetAPI(ListAPIView):
    queryset = content_models.LearnerPapers.objects.all()
    serializer_class = serializers.LearnerPaperSerializer
    pagination_class = core_paginations.CustomPagination
    
    def get_queryset(self):
        #user = self.request.user
        user = self.request.query_params.get('user')
        apikeys=self.request.query_params.get('apikeys')
        if not apikeys:
            raise ValidationError("Enter Valid API Keys")
        if APIKeysForVerify.objects.filter(keyvalues=apikeys).exists():
            user_obj = User.objects.get(username=user)
            print(user_obj)
            learner_paper_obj = content_models.LearnerPapers.objects.select_related("user", "learner_exam"
            ).prefetch_related("questions", "bookmarks", "subjects").filter(user=user_obj)
            if learner_paper_obj:
                return learner_paper_obj
            else:
                return []
        raise ValidationError('This API Key Not Valid Please contect MMP issue New API Keys')


class FetchMentorPapersFourInAPageViewSetAPI(ListAPIView):
    queryset = content_models.MentorPapers.objects.all()
    serializer_class = serializers.CardViewMentorPaperSerializer
    pagination_class = core_paginations.CustomPagination4

    def get_queryset(self):
        user = self.request.user
        batch_id = self.request.query_params.get('batch')
        apikeys=self.request.query_params.get('apikeys')
        if not apikeys:
            raise ValidationError("Enter Valid API Keys")
        if APIKeysForVerify.objects.filter(keyvalues=apikeys).exists():
            if batch_id:
                batch_obj = content_models.Batch.objects.get(id=int(batch_id))
                if batch_obj:
                    learner_paper_obj = content_models.MentorPapers.objects.filter(batch=batch_obj)
                if not batch_obj:
                    raise ParseError("Batch with this id DoesNotExist")
            if not batch_id:
                learner_paper_obj = content_models.MentorPapers.objects.filter(mentor=user)
            if learner_paper_obj:
                return learner_paper_obj
            else:
                return []
        raise ValidationError('This API Key Not Valid Please contect MMP issue New API Keys')


class RegisterSchoolWitEmailAndPassword(APIView):
    def post(self,request):
        email = request.data["email"]
        mobile_number = request.data["mobile_number"]
        password = request.data["password"]
        fullname = request.data["fullname"]
        user_group=UserGroup.objects.get(name='school')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Email allready exists')
        last_user_created_id = User.objects.all().last().id
        username = create_username(str(10000 + last_user_created_id))
        user_obj = User.objects.create(username=username,fullname=fullname,email=email,phonenumber=mobile_number)
        user_obj.set_password(password)
        user_obj.save()
        print("*********************",user_obj)
        profileO=Profile.objects.get(user=user_obj)
        profileO.user_group=user_group
        profileO.contact_verified=True
        profileO.account_verified=True
        profileO.save()
        return Response({'message':'School Register Successfully'})


class RegisterSuperUser(APIView):
    def post(self,request):    
        username = request.data["username"]
        email = request.data["email"]
        password = request.data["password"]
        fullname = request.data["fullname"]
        mobile_number = request.data["mobile_number"]
        superuser = User.objects.create_superuser(username=username,email=email,password=password,phonenumber=mobile_number,fullname=fullname)
        superuser.save()
        return Response({'message':'Successfully Created SuperUser'})


########################################## Api For Bloom Level Question and Content  ################################################

# class BarBloomLevelView1(APIView):
#     permission_classes = [IsAuthenticated,]
#     def get(self,request):
#         if BarBloomLevel.objects.filter(user=request.user,bloom_level=1):
#             qs = BarBloomLevel.objects.filter(user=request.user)
#             data = BloomSerializer1(qs,many=True).data
#             return Response({'message':'All Bloom Level','data':data})
#         else:
#             qs1 = courses_models.BloomLevel.objects.all().order_by('-id')
#             data1=BloomSerializer(qs1,many=True).data
#             return Response({'message':'All Bloom Level','data':data1})


class OverAllBloomLevel(APIView):
    permission_classes = [IsAuthenticated,]
    def get(self,request):
        if OverAllBloomLevelValues.objects.filter(user=request.user,unique_values='mmp'):
            qs = OverAllBloomLevelValues.objects.filter(user=request.user)
            data = OverAllBloomSerializer(qs,many=True).data
            return Response({'message':'OverAll Bloom Level Data','data':data})
        else:
            qs1 = BarBloomLevel.objects.filter(bloom_level=1)
            data1=BloomSerializer1(qs1,many=True).data
            return Response({'message':'OverAll Bloom Level Data','data':data1})
        # qs = BarBloomLevel.objects.filter(bloom_level=1)
        # data=OverAllBloomSerializer(qs,many=True).data
        # return Response({'message':'OverAll Bloom Level Data','data':data})

class BloomLevelExamWiseViewSet(APIView):
    permission_classes = [IsAuthenticated,]
    def get(self,request):
        exam_id = self.request.query_params.get('exam')
        exam_obj = courses_models.Exam.objects.get(id=int(exam_id))
        if BloomLevelValues.objects.filter(user=request.user,exam=exam_obj,unique_values='mmp'):
            qs = BloomLevelValues.objects.filter(user=request.user,exam=exam_obj)
            data = BloomSerializer(qs,many=True).data
            return Response({'message':'All Bloom Level','data':data})
        else:
            qs1 = BarBloomLevel.objects.filter(bloom_level=1)
            data1=BloomSerializer1(qs1,many=True).data
            return Response({'message':'All Bloom Level','data':data1})


class AllBloomLevelLearnerExamViewSet(ListAPIView):
    serializer_class = BloomLearnerExamSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        # user = self.request.user
        try:
            user=None
            if self.request.query_params.get('user'):
                user= User.objects.get(username=self.request.query_params.get('user'))
            else:
                user = self.request.user
        except:
            user = self.request.user
        if user:
            learner_obj = BloomLevelValues.objects.select_related("exam").prefetch_related("exam__subjects"
            ).filter(user=user).order_by('-id')
            return learner_obj
        return BloomLevelValues.select_related("exam").prefetch_related("exam__subjects").objects.all()

class SaveBloomData(APIView):
    permission_classes = [IsAuthenticated,]
    def post(self,request):
        assessmentpaper_id = request.data.get('assessmentpaper_id')
        exam_id = self.request.query_params.get('exam')
        exam_obj = courses_models.Exam.objects.get(id=int(exam_id))
        assessmentpaper = content_models.LearnerPapers.objects.prefetch_related("subjects", "chapters", "questions").select_related("learner_exam").get(id=assessmentpaper_id)
        print('assessmentpaper',assessmentpaper)
        #subjects = assessmentpaper.subjects.all()
        #print('subjects',subjects)
        chapters = assessmentpaper.chapters.all()
        print('chapters',chapters)
        # allchapters_ids = chapters.values_list("topics", flat=True)
        # print(allchapters_ids,'allchapters_ids')
        # #cqs = courses_models.Chapter.objects.get(id=allchapters_ids)
        # #print('cqs',cqs)

        tagIds =  assessmentpaper.questions.values_list("bloom_level", flat=True).all()
        print(tagIds,'naseem khan')
        count = 0
        count1 = 0
        count2 = 0
        for ele in tagIds:
            if (ele == 'Rote Learning'):
                count = count + 1
            elif (ele == 'Comprehension'):
                count1 = count1 + 1
            elif (ele == 'Application'):
                count2 = count2 + 1
        print(count,count1,count2)
        score = tagIds.count()
        
        answer_paper = content_models.AnswerPaper.objects.filter(user=request.user, assessment_paper=assessmentpaper).last()

        user_answer = content_models.UserAnswer.objects.filter(answer_paper=answer_paper).select_related(
            "answer_paper", "user", "question",  "correct_fillup_answer", "correct_boolean_answer", 
            "correct_string_answer").prefetch_related("user_mcq_answer", "correct_mcq_answer", "question__linked_topics")

        OverAllBloomLevel, _ = OverAllBloomLevelValues.objects.get_or_create(user=request.user,unique_values='mmp')
        OverAllBloomLevel.memory_based += count
        OverAllBloomLevel.conceptual += count1
        OverAllBloomLevel.application += count2
        OverAllBloomLevel.total_question += score
        OverAllBloomLevel.save()

        learner_papercount_obj, _ = BloomLevelValues.objects.get_or_create(user=request.user,exam=exam_obj,unique_values='mmp')
        #exam_subject_obj.percentage = (exam_subject_obj.score * 100) / exam_subject_obj.total_marks
        #print(learner_papercount_obj)
        learner_papercount_obj.memory_based += count
        learner_papercount_obj.conceptual += count1
        learner_papercount_obj.application += count2
        learner_papercount_obj.total_question += score
        # #learner_papercount_obj.analyze += 1
        # #learner_papercount_obj.evaluate += 1
        # learner_papercount_obj.unique_values = 'mmp'
        # #learner_papercount_obj.exam = exam_obj
        learner_papercount_obj.save()

        return Response({'message':'Bloom Data Save Succesfully'})

        # correct_question_ids = []
        # for data in user_answer:
        #     ques_obj = data.question
        #     correct_question_ids.append(ques_obj)

            # correct_question_ids[0:3] = 1
            # correct_question_ids[3:6] = 1
            # correct_question_ids[6:9] = 1
            # print(correct_question_ids[0:3],correct_question_ids[3:6],correct_question_ids[6:9])

            # ques_dic = dict(id=ques_obj.id, type_of_question = ques_obj.type_of_question)
            # print(correct_question_ids)
            # print(ques_dic.correct_mcq_answer)

        #print(user_answer)
        # qssss=list(user_answer)
        # return HttpResponse(json.dumps(qssss))
        #return JsonResponse({"user_answer": user_answer})

class QuestionBloomText(APIView):
    def get(self,request):
        #qs=content_models.Question.objects.filter(bloom_level='Memory Based') #Rote Learning,Comprehension,Analysis,Application
        qs=content_models.Question.objects.all()[10100:20500]
        count_question = content_models.Question.objects.all().count()
        data1=jfdsfgsdfhsgfhfsui(qs,many=True).data
        return Response({'message':'All Bloom Level','count':count_question,'data':data1})


class QuestionBloomTextId(APIView):
    def post(self,request):
        id=request.data.get('id')
        bloom_level = request.data.get('bloom_level')
        my_list = [x for x in id.split(',')]
        print(my_list)
        for data in my_list:
            #qs=content_models.Question.objects.filter(bloom_level='Memory Based') #Rote Learning,Comprehension,Analysis,Application
            qs=content_models.Question.objects.get(id=data)
            print(qs)
            #bloom_level = 'Memory Based'
            #bloom_level = 'Conceptual'
            #bloom_level = 'Application'
            qs.bloom_level = bloom_level
            qs.save()
            print(qs.bloom_level)
        return Response({'message':'Bloom Level update successfully'})


class ShowQuestionData(APIView):
    def post(self,request):
        id=request.data.get('id')
        qs=content_models.Question.objects.get(id=id)
        data1=jfdsfgsdfhsgfhfsu(qs,many=False).data
        return Response({'message':'Question Data','data':data1})

from django.utils import timezone

class Count_Currently_logged(APIView):
    def post(self,request):
        ago20m = timezone.now() - timezone.timedelta(minutes=14400)
        count = User.objects.filter(is_authenticated=True).count()
        return Response(count,HTTP_200_OK)

class BloomLevelHistoryViewSet(ListAPIView):
    queryset = BloomLevelValues.objects.all()
    serializer_class = BloomSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        # user = self.request.user
        try:
            user=None
            if self.request.query_params.get('user'):
                user= User.objects.get(username=self.request.query_params.get('user'))
            else:
                user = self.request.user
        except:
            user = self.request.user
        exam_id = self.request.query_params.get('exam')
        exam_obj = courses_models.Exam.objects.get(id=int(exam_id))
        if not exam_obj:
            raise ParseError("Exam with this id DoesNotExist")
        learner_obj = BloomLevelValues.objects.filter(
            user=user, exam=exam_obj)
        if learner_obj:
            return learner_obj
        else:
            return []


from django.db.models import Sum
from utilities.question_distribution_utils import QuestionDistribution
from constants import ExamType, DifficultyRange, QuestionLanguage

class FetchQuestionsByFilterViewSetAPI(UpdateAPIView):
    serializer_class = serializers.CardViewLearnerPaperSerializer

    def put(self, request, *args, **kwargs):
        # topicIds = []
        user = self.request.user
        subjectIds = []
        
        exam = request.data.get('exam', None)
        if not exam:
            return Response({"message": "Invalid exam request"}, status=HTTP_400_BAD_REQUEST)
        
        exam_obj = courses_models.Exam.objects.get(id=int(exam))
        if not exam_obj.is_active:
            learnerexamtmpobj = courses_models.LearnerExams.objects.filter(user=user, exam=exam_obj)
            if learnerexamtmpobj:
                learnerexamtmpobj = learnerexamtmpobj.first()
                learnerexamtmpobj.is_active=False
                learnerexamtmpobj.save()
            return Response({"message": "Oops! Exam has been deactivated by admin"}, status=HTTP_400_BAD_REQUEST)
        
        question_types = request.data.get('quesTypes', None)
        difficulty = request.data.get('difficulty', 1)
        
        if len(question_types) == 0:
            return Response({"message": "Please select at least one question type"}, status=HTTP_400_BAD_REQUEST)

        chapters = request.data.get('chapters')
        bloom = request.data.get('bloom_level')
        paper_type = request.data.get('type')
        show_time = request.data.get('show_time')
        bloom_level = courses_models.BloomLevel.objects.get(title=bloom)
        chapterHints = courses_models.ChapterHints.objects.filter(bloom_level=bloom_level)
        print('chapterHints',chapterHints)
        chapters_obj = courses_models.Chapter.objects.filter(id__in=chapterHints)
        print("chapters_obj",chapters_obj)
        subjectIds.extend(chapters_obj.values_list("subject", flat=True))
        print('subjectIds',subjectIds)
        
        # topicIds.extend(chapters_obj.values_list("topics", flat=True).all())
        
        try:
            total_ques = int(request.data.get('totalQues'))
        except:
            total_ques = 0
        
        if paper_type == ExamType.PAPER:
            learner_papercount_obj, _ = content_models.LearnerTotalActualPapers.objects.get_or_create(user=user)
            total_time = request.data.get('totalTime')
            learner_papercount_obj.count += 1
            learner_papercount_obj.save()
            count = learner_papercount_obj.count
            
        else:
            learner_practicecount_obj, _ = content_models.LearnerTotalPracticePapers.objects.get_or_create(user=user)
            total_time = 1200
            learner_practicecount_obj.count += 1
            learner_practicecount_obj.save()
            count = learner_practicecount_obj.count
            
            
        
        learner_paper_obj = content_models.LearnerPapers.objects.create(
            user=user, paper_type=paper_type, paper_count=count, show_time=show_time)
        learner_paper_obj.subjects.add(*subjectIds)
        learner_paper_obj.save()
    
        if paper_type == ExamType.PRACTICE:
            learner_paper_obj.chapters.add(*chapters)
            learner_paper_obj.save()
        
        try:
            learner_exam = int(request.data.get('learnerExam'))
            learner_exam_obj = courses_models.LearnerExams.objects.get(id=int(learner_exam))
            learner_exam_obj.is_active=True
            learner_exam_obj.save()
            learner_paper_obj.learner_exam = learner_exam_obj
        except:
            learner_exam = 0
            
        
        selectedRange = []
        if difficulty in DifficultyRange.range1:
            selectedRange = DifficultyRange.range1
        elif difficulty in DifficultyRange.range2:
            selectedRange = DifficultyRange.range2
        else:
            selectedRange = DifficultyRange.range3

        try:
            if request.data.get('anydifficulty'):
                selectedRange = DifficultyRange.allRange
        except:
            selectedRange = selectedRange
        
        learner_history_obj, _ = content_models.LearnerHistory.objects.get_or_create(user=user)
        eng_obj = models.QuestionLanguage.objects.get(text=QuestionLanguage.ENGLISH)

        try:
            questions = QuestionDistribution.get_equally_distributed_subjectwise_questions(
                learner_paper_obj.id, 'learnerpaper', subjectIds, selectedRange, chapters,  total_ques, eng_obj, question_types
            )
            logger.info(f"Questions count {len(questions)}")
            
            if len(questions) == 0:
                if learner_paper_obj.paper_type == 'paper':
                    learner_papercount_obj.count -= 1
                    learner_papercount_obj.save()
                else:
                    learner_practicecount_obj.count -= 1
                    learner_practicecount_obj.save()
                learner_paper_obj.delete()
                return Response({"message": "No questions found"}, status=HTTP_400_BAD_REQUEST)
            learner_paper_obj.total_time = total_time
            learner_paper_obj.questions.add(*questions)
            learner_paper_obj.save()
            learner_history_obj.papers.add(learner_paper_obj)
            learner_history_obj.total_questions += len(questions)
            learner_history_obj.questions.add(*questions)
            learner_history_obj.save()
            total_marks = 0
          
            instruction_ques = "Total Questions: " + str(learner_paper_obj.questions.count())
            paper_instruction_obj3 = content_models.PaperInstructions.objects.create(paper=learner_paper_obj,instruction=instruction_ques)
            if learner_paper_obj.paper_type == 'paper':
                instruction_time = "Total Time (in Min): " + str(total_time)
                paper_instruction_obj = content_models.PaperInstructions.objects.create(paper=learner_paper_obj,instruction=instruction_time)
            if exam:
                learnerexam_history_obj, _ = content_models.LearnerExamHistory.objects.get_or_create(user=user, exam=exam_obj)
                
                if learner_paper_obj.paper_type == ExamType.PAPER:
                    learnerexam_practice_history_obj = None
                    learnerexam_paper_history_obj,_ = content_models.LearnerExamPaperHistory.objects.get_or_create(user=user, exam=exam_obj)
                else:
                    learnerexam_paper_history_obj = None
                    learnerexam_practice_history_obj, _ = content_models.LearnerExamPracticeHistory.objects.get_or_create(user=user, exam=exam_obj)
                    
                learnerexam_history_obj.total_questions += len(questions)
                learnerexam_history_obj.save()
                
                learnerexam_history_obj.questions.add(*questions)
                learnerexam_history_obj.papers.add(learner_paper_obj)
                learnerexam_history_obj.save()
                if learnerexam_practice_history_obj:
                    learnerexam_practice_history_obj.questions.add(*questions)
                    learnerexam_practice_history_obj.papers.add(learner_paper_obj)
                    learnerexam_practice_history_obj.save()
                else:
                    learnerexam_paper_history_obj.questions.add(*questions)
                    learnerexam_paper_history_obj.papers.add(learner_paper_obj)
                    learnerexam_paper_history_obj.save()

                paper_instruction_obj2 = content_models.PaperInstructions.objects.create(paper=learner_paper_obj)

                distribution_based_on_type = QuestionDistribution.distribute_based_on_type_of_questions(
                    learner_paper_obj.questions.all()
                )
                
                total_marks_grouped_by_exam_type_of_question = courses_models.QuestionType.objects.filter(
                    exam=exam_obj, 
                    type_of_question__in=[learner_paper_obj.questions.all().values_list("type_of_question", flat=True)],
                ).exclude(type_of_question="subjective").values("exam", "type_of_question"
                ).order_by("exam").annotate(total_marks=Sum("marks"))
                
                for marks in total_marks_grouped_by_exam_type_of_question:
                    multiplier = distribution_based_on_type.get(marks["type_of_question"], 0)    
                    total_marks += marks["total_marks"]*multiplier
                
                instruction_marks = "Max. Marks: " + str(total_marks)
                learner_paper_obj.marks = total_marks
                learner_paper_obj.save()
                paper_instruction_obj2.instruction = instruction_marks
                paper_instruction_obj2.save()
        except Exception as e:
            logger.info(f"Exception {e}")
            
            if learner_paper_obj.paper_type == 'paper':
                learner_papercount_obj.count -= 1
                learner_papercount_obj.save()
            else:
                learner_practicecount_obj.count -= 1
                learner_practicecount_obj.save()
            learner_paper_obj.delete()
            return Response({"message": "error in fetching questions"}, status=HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(learner_paper_obj).data, status=201)


class TestDeploy(APIView):
    def get(self,request):
        return Response({'message':'deploy successfully'})
