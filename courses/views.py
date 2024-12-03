from io import BytesIO


import pandas as pd
from authentication import models as auth_models
from content.models import Batch
from core import permissions
from core.paginations import CustomPagination
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.db.models import Q
from django.forms import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError
from rest_framework.generics import (CreateAPIView, ListAPIView,
                                     RetrieveAPIView, RetrieveUpdateAPIView,
                                     UpdateAPIView)
from rest_framework.parsers import (FileUploadParser, FormParser,
                                    MultiPartParser)
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from courses.helpers import chapter_helper
from courses.utils import get_subject_chapters

from . import models, serializers


class ChapterViewSet(ListAPIView, CreateAPIView):
    serializer_class = serializers.AdminViewChapterSerializer
    create_serializer_class = serializers.CreateChapterSerializer
    # permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        subject_id = self.request.query_params.get('subject')
        if subject_id:
            subject_obj = models.Subject.objects.get(
                id=int(subject_id))
            if subject_obj:
                chapters = models.Chapter.objects.filter(
                subject=subject_obj).order_by('order')
                return chapters
            else:
                raise ParseError("Subject with this id DoesNotExist")
        return models.Chapter.objects.all().order_by('order')

    def create(self, request, *args, **kwargs):
        serializer = self.create_serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class EditChapterViewSet(RetrieveUpdateAPIView):
    queryset = models.Chapter.objects.select_related("subject").prefetch_related("hints", "topics").all()
    serializer_class = serializers.CreateChapterSerializer
    lookup_field = 'pk'
    # permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        chapter_obj = models.Chapter.objects.select_related("subject").prefetch_related("hints", "topics").filter(pk=self.kwargs.get('pk')).order_by('order')
        if not chapter_obj:
            raise ParseError("Chapter with this id DoesNotExist")
        return chapter_obj

class AddFTagsinChapterView(RetrieveUpdateAPIView):
    serializer_class = serializers.CreateChapterSerializer
    lookup_field = 'pk'

    def get_object(self):
        id = self.kwargs["pk"]
        try:
            return models.Chapter.objects.get(pk=id)
        except:
            return models.Chapter.objects.get(id=None)

    def put(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            chapter_obj = models.Chapter.objects.get(pk=int(id))
        except:
            return Response({"message": "Please enter valid id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            topics = request.data.get('topics')
            chapter_obj.topics.add(*topics)
            chapter_obj.save()
        except:
            return Response({"message": "error in adding ftags"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "FTags added successfully"}, status=201)

class BulkDeleteFTagView(UpdateAPIView):
    serializer_class = serializers.TopicSerializer

    def put(self, request, *args, **kwargs):
        try:
            topics = request.data.get('topics')
            models.Topic.objects.filter(id__in=topics).delete()
        except:
            return Response({"message": "error in deleting ftags"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "FTags deleted successfully"}, status=201)

class RemoveFTagFromChapterView(RetrieveUpdateAPIView):
    serializer_class = serializers.CreateChapterSerializer
    lookup_field = 'pk'

    def get_object(self):
        id = self.kwargs["pk"]
        try:
            return models.Chapter.objects.get(pk=id)
        except:
            return models.Chapter.objects.get(id=None)

    def put(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            chapter_obj = models.Chapter.objects.get(pk=int(id))
        except:
            return Response({"message": "Please enter valid id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            topic_obj = models.Topic.objects.get(pk=int(request.data.get('topic')))
            chapter_obj.topics.remove(topic_obj)
            chapter_obj.save()
        except:
            return Response({"message": "error in removing ftag"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "FTag removed successfully"}, status=201)

class FTagViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.TopicSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        return models.Topic.objects.all().order_by('id')

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class EditFTagViewSetViewSet(RetrieveUpdateAPIView):
    queryset = models.Topic.objects.all()
    serializer_class = serializers.TopicSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        level_obj = models.Topic.objects.filter(pk=self.kwargs.get('pk'))
        if not level_obj:
            raise ParseError("F tag with this id DoesNotExist")
        return level_obj

class SearchFTagViewSetViewSet(ListAPIView):
    queryset = models.Topic.objects.all()
    serializer_class = serializers.TopicSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        searchtext = self.request.query_params.get('text')
        if searchtext:
            tag_obj = models.Topic.objects.filter(title__contains=searchtext).order_by('id')
            if tag_obj:
                return tag_obj
            else:
                return []

class SearchMultipleFTagsViewSetViewSet(UpdateAPIView):
    serializer_class = serializers.TopicSerializer

    def put(self, request, *args, **kwargs):
        try:
            ftags = request.data.get('ftags')
            tag_obj = models.Topic.objects.filter(title__in=ftags).order_by('id')
        except:
            return Response({"message": "error in fetching ftags"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(tag_obj, many=True).data, status=201)

class SearchExamViewSetViewSet(ListAPIView):
    queryset = models.Exam.objects.all()
    serializer_class = serializers.ExamSerializer
    # permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        searchtext = self.request.query_params.get('text')
        if searchtext:
            exam_obj = models.Exam.objects.filter(is_active=True).filter(Q(title__icontains=searchtext)).order_by('id')
            if exam_obj:
                return exam_obj
            else:
                return []

class SearchExamViewSet(ListAPIView):
    queryset = models.Exam.objects.all()
    serializer_class = serializers.ExamSerializer
    # permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        searchtext = self.request.query_params.get('text')
        level_id = self.request.query_params.get('level')
        if searchtext:
            if level_id:
                try:
                    level_obj = models.ExamLevel.objects.get(
                        id=int(level_id))
                    if level_obj:
                        exam = models.Exam.objects.filter(title__contains=searchtext,
                            level=level_obj).order_by('id')
                except:
                    exam = models.Exam.objects.filter(title__contains=searchtext).order_by('id')
            else:
                exam = models.Exam.objects.filter(title__contains=searchtext).order_by('id')
            if exam:
                return exam
            else:
                return []

class ExamCategoryViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.ExamCategorySerializer

    def get_queryset(self):
        return models.ExamCategory.objects.all().order_by('order')

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class EditExamCategoryViewSet(RetrieveUpdateAPIView):
    queryset = models.ExamCategory.objects.all()
    serializer_class = serializers.ExamCategorySerializer
    lookup_field = 'pk'
    # permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        category_obj = models.ExamCategory.objects.filter(pk=self.kwargs.get('pk')).order_by('order')
        if not category_obj:
            raise ParseError("Exam Category with this id DoesNotExist")
        return category_obj

class ExamLevelViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.ExamLevelSerializer

    def get_queryset(self):
        return models.ExamLevel.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class EditExamLevelViewSet(RetrieveUpdateAPIView):
    queryset = models.ExamLevel.objects.all()
    serializer_class = serializers.ExamLevelSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        level_obj = models.ExamLevel.objects.filter(pk=self.kwargs.get('pk'))
        if not level_obj:
            raise ParseError("Exam Level with this id DoesNotExist")
        return level_obj

class ExamMakePathQuestionsViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.ExamMakePathQuestionSerializer

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            exam_obj = models.Exam.objects.get(id=int(exam_id))
            examPathQuestion = models.ExamMakePathQuestions.objects.filter(
                exam=exam_obj, is_active=True).order_by('order')
            if examPathQuestion:
                return examPathQuestion
            else:
                return []
        return models.ExamMakePathQuestions.objects.filter(is_active=True).order_by('order')

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class EditExamMakePathQuestionsView(RetrieveUpdateAPIView):
    queryset = models.ExamMakePathQuestions.objects.all()
    serializer_class = serializers.ExamMakePathQuestionSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        ques_obj = models.ExamMakePathQuestions.objects.filter(pk=self.kwargs.get('pk')).order_by('order')
        if not ques_obj:
            raise ParseError("Exam Path Question with this id DoesNotExist")
        return ques_obj

    def delete(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            ques_obj = models.ExamMakePathQuestions.objects.get(pk=int(id))
            ques_obj.delete()
        except:
            return Response({"message": "Please enter valid question id"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "question deleted successfully"}, status=201)

class ExamDomainViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.DomainSerializer
    parser_classes = (FormParser, MultiPartParser)
    queryset = models.ExamDomain.objects.prefetch_related("exam_category", "exams").order_by('order')

    def get_queryset(self):
        category_id = self.request.query_params.get('category_id')
        if category_id:
            examDomain = self.queryset.filter(exam_category__id=int(category_id), is_active=True)
            return examDomain
        return self.queryset.filter(is_active=True)

class AllExamDomainViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.DomainSerializer
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        category_id = self.request.query_params.get('category_id')
        
        if category_id:
            category_obj = models.ExamCategory.objects.get(id=int(category_id))
            examDomain = models.ExamDomain.objects.filter(
                exam_category=category_obj).order_by('order')
            if examDomain:
                return examDomain
            else:
                return []
        return models.ExamDomain.objects.all().order_by('order')

class EditDomainView(RetrieveUpdateAPIView):
    queryset = models.ExamDomain.objects.all().order_by('order')
    serializer_class = serializers.DomainSerializer
    lookup_field = 'pk'
    # permission_classes = (IsAuthenticated,)
    parser_class = (FileUploadParser)

    def get_queryset(self):
        domain_obj = models.ExamDomain.objects.filter(pk=self.kwargs.get('pk')).order_by('order')
        if not domain_obj:
            raise ParseError("Exam Domain with this id DoesNotExist")
        return domain_obj

class FetchDomainExamsView(ListAPIView):
    queryset = models.ExamDomain.objects.all().order_by('order')
    serializer_class = serializers.ExamSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        domain_id = self.request.query_params.get('domain')
        if domain_id:
            domain_obj = models.ExamDomain.objects.get(
                id=int(domain_id))
            if domain_obj:
                data = serializers.DomainSerializer(
                domain_obj).data
                exam = models.Exam.objects.filter(
                    id__in=[exam for exam in data['exams']])
                return exam
        return models.Exam.objects.all()

class CourseViewSet(ListAPIView, CreateAPIView):
    # permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.ExamSerializer
    parser_classes = (FormParser, MultiPartParser)
    queryset = models.Exam.objects.select_related("level").prefetch_related("subjects", "userclass", "userboard")

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
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class AllCourseViewSet(ListAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.ExamSerializer
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        level_id = self.request.query_params.get('level')
        if level_id:
            level_obj = models.ExamLevel.objects.get(
                id=int(level_id))
            if level_obj:
                exam = models.Exam.objects.filter(
                    level=level_obj)
                return exam
        return models.Exam.objects.all()

class EditCourseView(RetrieveUpdateAPIView):
    queryset = models.Exam.objects.all()
    serializer_class = serializers.ExamSerializer
    lookup_field = 'pk'
    # permission_classes = (IsAuthenticated,)
    parser_class = (FileUploadParser)

    def get_queryset(self):
        courseObj = models.Exam.objects.filter(pk=self.kwargs.get('pk'))
        if not courseObj:
            raise ParseError("Exam with this id DoesNotExist")
        return courseObj

class SubjectViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.SubjectSerializer

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            course = models.Exam.objects.get(
                id=int(exam_id))
            data = serializers.ExamSerializer(
            course).data
            if course:
                subjects = models.Subject.objects.filter(
                id__in=[subject for subject in data['subjects']], show=True).order_by('order')
                return subjects
        return models.Subject.objects.all().order_by('order')

    def post(self, request):
        examId = request.data.get('examid')
        title = request.data.get("title")
        order = request.data.get("order")
        if not examId:
            raise ParseError("Please enter examid")
        try:
            examobj = models.Exam.objects.get(
                id=examId)
        except:
            raise ParseError("Invalid exam id")

        subject_obj = models.Subject.objects.create(title=title, order=order)
        examobj.subjects.add(subject_obj)

        data = serializers.ExamSerializer(
            examobj).data
        return Response(data, status=201)

class AllAdminSubjectViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.SubjectSerializer

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            course = models.Exam.objects.get(
                id=int(exam_id))
            data = serializers.ExamSerializer(
            course).data
            if course:
                subjects = models.Subject.objects.filter(
                id__in=[subject for subject in data['subjects']]).order_by('order')
                return subjects
        return models.Subject.objects.all().order_by('order')

    def post(self, request):
        examId = request.data.get('examid')
        title = request.data.get("title")
        order = request.data.get("order")
        if not examId:
            raise ParseError("Please enter examid")
        try:
            examobj = models.Exam.objects.get(
                id=examId)
        except:
            raise ParseError("Invalid exam id")

        subject_obj = models.Subject.objects.create(title=title, order=order)
        examobj.subjects.add(subject_obj)

        data = serializers.ExamSerializer(
            examobj).data
        return Response(data, status=201)

class EditSubjectView(RetrieveUpdateAPIView):
    queryset = models.Subject.objects.all()
    serializer_class = serializers.SubjectSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        courseObj = models.Subject.objects.filter(pk=self.kwargs.get('pk')).order_by('order')
        if not courseObj:
            raise ParseError("Subject with this id DoesNotExist")
        return courseObj


class DomainNodeViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.DomainNodeSerializer

    def get_queryset(self):
        domain_id = self.request.query_params.get('domain_id')
        if domain_id:
            domain = models.ExamDomain.objects.get(
                id=int(domain_id))
            if domain:
                nodes = models.PathNodes.objects.filter(domain=domain).order_by('order')
                return nodes
        return models.PathNodes.objects.all().order_by('order')

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class InitialDomainNodeView(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.DomainNodeSerializer
    queryset = models.PathNodes.objects.select_related("domain", "linked_exam").prefetch_related("successive_nodes", "journey_nodes")
    
    def get_queryset(self):
        domain_id = self.request.query_params.get('domain_id')
        if domain_id:
            node = self.queryset.filter(domain__id=domain_id).order_by('id')[:1]
            return node
        return self.queryset.order_by('id')

class LastExamDomainNodeView(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.DomainNodeSerializer
    queryset = models.PathNodes.objects.select_related("domain", "linked_exam").prefetch_related("successive_nodes", "journey_nodes")
    
    def get_queryset(self):
        domain_id = self.request.query_params.get('domain_id')
        exam_id = self.request.query_params.get('exam_id')
        if domain_id:
            node = self.queryset.filter(domain__id=domain_id, linked_exam__id=exam_id).order_by('-id')[:1]
            return node
        return self.queryset.order_by('-id')

class EditDomainNodeView(RetrieveUpdateAPIView):
    queryset = models.PathNodes.objects.select_related("domain", "linked_exam").prefetch_related("journey_nodes").all()
    serializer_class = serializers.DomainNodeSerializer
    lookup_field = 'pk'
    # permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        domain_obj = self.queryset.filter(pk=self.kwargs.get('pk'))
        if not domain_obj:
            raise ParseError("Path Node with this id DoesNotExist")
        return domain_obj

class AddSuccessiveNode(RetrieveUpdateAPIView):
    serializer_class = serializers.DomainNodeSerializer
    lookup_field = 'pk'
    # parser_classes = (FormParser, MultiPartParser)

    def get_object(self):
        id = self.kwargs["pk"]
        try:
            return models.PathNodes.objects.get(pk=id)
        except:
            return models.PathNodes.objects.get(id=None)

    def put(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            currentnodeObj = models.PathNodes.objects.get(pk=int(id))
        except:
            return Response({"message": "Please enter valid id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            successivenode_obj = models.PathNodes.objects.get(pk=int(request.data.get('newNode')))
            currentnodeObj.successive_nodes.add(successivenode_obj)
            currentnodeObj.save()
            if len(successivenode_obj.successive_nodes.all()) == 1:
                successivenode_obj.successive_nodes.remove(currentnodeObj)
                successivenode_obj.save()
        except:
            return Response({"message": "error in adding successive node"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "successive node added successfully"}, status=201)

class AddExamInDomainNodeView(RetrieveUpdateAPIView):
    serializer_class = serializers.DomainNodeSerializer
    lookup_field = 'pk'

    def get_object(self):
        id = self.kwargs["pk"]
        try:
            return models.PathNodes.objects.get(pk=id)
        except:
            return models.PathNodes.objects.get(id=None)

    def put(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            currentnodeObj = models.PathNodes.objects.get(pk=int(id))
        except:
            return Response({"message": "Please enter valid id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            exam_obj = models.Exam.objects.get(pk=int(request.data.get('exam')))
            domain_obj = models.ExamDomain.objects.get(pk=int(request.data.get('domain')))
            domain_obj.exams.add(exam_obj)
            domain_obj.save()
            currentnodeObj.linked_exam = exam_obj
            # currentnodeObj.successive_nodes = []
            currentnodeObj.save()
        except:
            return Response({"message": "error in linking exam"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "exam linked successfully"}, status=201)


class DeleteDomainNodeView(RetrieveUpdateAPIView):
    queryset = models.PathNodes.objects.all()
    serializer_class = serializers.DomainNodeSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        domain_obj = models.PathNodes.objects.filter(pk=self.kwargs.get('pk'))
        if not domain_obj:
            raise ParseError("Path Node with this id DoesNotExist")
        return domain_obj

    def put(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            currentnodeObj = models.PathNodes.objects.get(pk=int(id))
        except:
            return Response({"message": "Please enter valid id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            if currentnodeObj.linked_exam:
                exam_obj = models.Exam.objects.get(pk=int(currentnodeObj.linked_exam.id))
                domain_obj = models.ExamDomain.objects.get(pk=int(request.data.get('domain')))
                if len(domain_obj.exams.all()) == 1:
                    domain_obj.exams.remove(exam_obj)
                    domain_obj.save()
            currentnodeObj.delete()
        except:
            return Response({"message": "error in deleting junction"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "junction deleted successfully"}, status=201)

class LearnerExamViewSet(ListAPIView, CreateAPIView):
    serializer_class = serializers.LearnerExamSerializer
    create_serializer_class = serializers.LearnerExamSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        # user = self.request.user
        try:
            user=None
            if self.request.query_params.get('user'):
                user= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                user = self.request.user
        except:
            user = self.request.user
        if user:
            learner_obj = models.LearnerExams.objects.select_related("exam").prefetch_related("exam__subjects"
            ).filter(is_active=True, user=user).order_by('-updated_at')
            return learner_obj
        return models.LearnerExams.select_related("exam").prefetch_related("exam__subjects").objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.create_serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class AllLearnerExamViewSet(ListAPIView):
    serializer_class = serializers.LearnerExamSerializer
    create_serializer_class = serializers.LearnerExamSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        # user = self.request.user
        try:
            user=None
            if self.request.query_params.get('user'):
                user= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                user = self.request.user
        except:
            user = self.request.user
        if user:
            learner_obj = models.LearnerExams.objects.select_related("exam").prefetch_related("exam__subjects"
            ).filter(user=user).order_by('-updated_at')
            return learner_obj
        return models.LearnerExams.select_related("exam").prefetch_related("exam__subjects").objects.all()


class MentorExamViewSet(ListAPIView, CreateAPIView):
    serializer_class = serializers.MentorExamSerializer
    create_serializer_class = serializers.MentorExamSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            batch_obj = Batch.objects.get(id=int(batch_id))
            mentorexams_obj = models.MentorExams.objects.filter(
                user=user, is_active=True, batches=batch_obj)
            return mentorexams_obj
        else:
            mentorexams_obj = models.MentorExams.objects.filter(
                user=user, is_active=True)
            return mentorexams_obj
        return models.MentorExams.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.create_serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class EditLearnerExamDetailQuestionsView(RetrieveUpdateAPIView):
    queryset = models.LearnerExams.objects.all()
    serializer_class = serializers.LearnerExamSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        
        exam_obj = models.LearnerExams.objects.select_related("user", "exam", "user__profile"
        ).filter(pk=self.kwargs.get('pk')).order_by('id')
        if not exam_obj:
            raise ParseError("Learner Exam data with this id DoesNotExist")
        return exam_obj

    def put(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            exam_obj = models.LearnerExams.objects.get(pk=int(id))
        except:
            return Response({"message": "Please enter valid id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            exam_obj.is_active = False
            exam_obj.save()
        except:
            return Response({"message": "error in delinking the exam"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "exam delinked successfully"}, status=201)

class EditMentorExamDetailQuestionsView(RetrieveUpdateAPIView):
    queryset = models.LearnerExams.objects.all()
    serializer_class = serializers.MentorExamSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        exam_obj = models.MentorExams.objects.filter(pk=self.kwargs.get('pk')).order_by('id')
        if not exam_obj:
            raise ParseError("Mentor Exam data with this id DoesNotExist")
        return exam_obj

    def put(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            exam_obj = models.MentorExams.objects.get(pk=int(id))
        except:
            return Response({"message": "Please enter valid id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            exam_obj.is_active = False
            exam_obj.save()
        except:
            return Response({"message": "error in delinking the exam"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "exam delinked successfully"}, status=201)
    

class ExamAverageQuestionTimeViewSet(ListAPIView, CreateAPIView):
    serializer_class = serializers.AverageMarksSerializer
    create_serializer_class = serializers.AverageMarksSerializer
    # permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            exam_obj = models.Exam.objects.get(id=exam_id)
            if exam_obj:
                avg_obj = models.ExamAverageTimePerQuestion.objects.filter(
                exam=exam_obj)
                return avg_obj
            else:
                raise ParseError("Exam with this id DoesNotExist")
        return models.ExamAverageTimePerQuestion.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.create_serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class EditAverageViewSet(RetrieveUpdateAPIView):
    queryset = models.ExamAverageTimePerQuestion.objects.all()
    serializer_class = serializers.AverageMarksSerializer
    update_serializer_class = serializers.AverageMarksSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser, )

    def get_queryset(self):
        questionavg = models.ExamAverageTimePerQuestion.objects.select_related("exam").filter(
            pk=self.kwargs.get('pk'))
        if not questionavg:
            raise ParseError("Avg marks data DoesNotExist")
        return questionavg

    def update(self, request, *args, **kwargs):
        questionavg = models.ExamAverageTimePerQuestion.objects.get(
            pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            questionavg, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(questionavg).data, status=status.HTTP_200_OK)

class ExamQuestionTypeViewSet(ListAPIView, CreateAPIView):
    serializer_class = serializers.ExamQuestionTypeSerializer
    create_serializer_class = serializers.ExamQuestionTypeSerializer
    # permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            type_obj = models.QuestionType.objects.select_related("exam").prefetch_related(
                "exam__subjects", "exam__userclass", "exam__userboard").filter(
                exam__id=exam_id, is_active=True)
            return type_obj
            
        return models.QuestionType.objects.select_related("exam").prefetch_related(
                "exam__subjects", "exam__userclass", "exam__userboard").all()

    def create(self, request, *args, **kwargs):
        serializer = self.create_serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ShowAllExamQuestionTypeViewSet(ListAPIView, CreateAPIView):
    serializer_class = serializers.ExamQuestionTypeSerializer
    create_serializer_class = serializers.ExamQuestionTypeSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            exam_obj = models.Exam.objects.get(id=exam_id)
            if exam_obj:
                type_obj = models.QuestionType.objects.filter(
                exam=exam_obj)
                return type_obj
            else:
                raise ParseError("Exam with this id DoesNotExist")
        return models.QuestionType.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.create_serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EditExamQuestionTypeViewSet(RetrieveUpdateAPIView):
    queryset = models.QuestionType.objects.all()
    serializer_class = serializers.ExamQuestionTypeSerializer
    update_serializer_class = serializers.ExamQuestionTypeSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser, )

    def get_queryset(self):
        type_obj = models.QuestionType.objects.filter(
            pk=self.kwargs.get('pk'))
        if not type_obj:
            raise ParseError("data DoesNotExist")
        return type_obj

    def update(self, request, *args, **kwargs):
        type_obj = models.QuestionType.objects.get(
            pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            type_obj, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(type_obj).data, status=status.HTTP_200_OK)

class DomainAnnouncementViewSet(ListAPIView, CreateAPIView):
    serializer_class = serializers.DomainAnnouncementSerializer
    create_serializer_class = serializers.DomainAnnouncementSerializer
    # permission_classes = (IsAuthenticated,)
    pagination_class = CustomPagination
    queryset = models.DomainAnnouncement.objects.select_related("domain", "linked_exam").all()

    def get_queryset(self):
        domain_id = self.request.query_params.get('domain')
        # if domain_id:
        #     anncmnt_obj = get_object_or_404(models.DomainAnnouncement, domain__id=domain_id, is_active=True)
        #     return anncmnt_obj
        # return self.queryset.all()
        if domain_id:
            anncmnt_obj = models.DomainAnnouncement.objects.filter(
            domain__id=domain_id, is_active=True).order_by('order')
            return anncmnt_obj
        return models.DomainAnnouncement.objects.all().order_by('order')

        
    def create(self, request, *args, **kwargs):
        serializer = self.create_serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class AdminDomainAnnouncementViewSet(ListAPIView):
    serializer_class = serializers.DomainAnnouncementSerializer
    create_serializer_class = serializers.DomainAnnouncementSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        domain_id = self.request.query_params.get('domain')
        if domain_id:
            domain_obj = models.ExamDomain.objects.get(id=domain_id)
            if domain_obj:
                anncmnt_obj = models.DomainAnnouncement.objects.filter(
                domain=domain_obj).order_by('order')
                return anncmnt_obj
            else:
                raise ParseError("Domain Announcement with this id DoesNotExist")
        return models.DomainAnnouncement.objects.all().order_by('order')

class EditDomainAnnouncementViewSet(RetrieveUpdateAPIView):
    queryset = models.DomainAnnouncement.objects.all()
    serializer_class = serializers.DomainAnnouncementSerializer
    update_serializer_class = serializers.EditDomainAnnouncementSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser, )

    def get_queryset(self):
        type_obj = models.DomainAnnouncement.objects.filter(
            pk=self.kwargs.get('pk'))
        if not type_obj:
            raise ParseError("data DoesNotExist")
        return type_obj

    def update(self, request, *args, **kwargs):
        type_obj = models.DomainAnnouncement.objects.get(
            pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            type_obj, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(type_obj).data, status=status.HTTP_200_OK)

class FetchAnnouncementsForMultipleDomainsView(ListAPIView):
    serializer_class = serializers.DomainAnnouncementSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        domain_ids = self.request.query_params.get('domains')
        domains = list(map(int,domain_ids.split(',')))
        print ("domainsaa", domains)
        if domains:
            anncmnt_obj = models.DomainAnnouncement.objects.filter(
            domain__in=domains, is_active=True).order_by('order')
            return anncmnt_obj
        return models.DomainAnnouncement.objects.all().order_by('order')

    # def put(self, request, *args, **kwargs):
    #     try:
    #         domains = request.data.get('domains')
    #         link_obj = models.DomainAnnouncement.objects.filter(domain__in=domains, is_active=True).order_by('order')
    #     except:
    #         return Response({"message": "error in fetching announcements"}, status=status.HTTP_400_BAD_REQUEST)
    #     return Response(self.serializer_class(link_obj, many=True).data, status=201)

class ExamSubjectsWithChaptersView(ListAPIView):
    # permission_classes = [IsAuthenticated,]

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        subjects = get_subject_chapters(exam_id)

        if not subjects:
            # return blank queryset if subjects not received
            return None
        return subjects
    
    def list(self, request, *args, **kwargs):

        queryset = self.get_queryset()
        if queryset:
            return Response({
                'subjects':queryset
            })
        return Response({'error': 'Error in Fetching Subjects'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class CreateExamBookViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.CreateExamBookSerializer
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            exam_obj = models.Exam.objects.get(
                id=int(exam_id))
            if exam_obj:
                exam = models.ExamSuggestedBooks.objects.filter(
                    exam=exam_obj)
                return exam
        return models.ExamSuggestedBooks.objects.filter(is_active=True)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
class FetchExamBookViewSet(ListAPIView,):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.ExamBookSerializer

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            exam_obj = models.Exam.objects.get(
                id=int(exam_id))
            if exam_obj:
                exam = models.ExamSuggestedBooks.objects.filter(
                    exam=exam_obj)
                return exam
        return models.ExamSuggestedBooks.objects.filter(is_active=True)

class EditExamBookView(RetrieveUpdateAPIView):
    queryset = models.ExamSuggestedBooks.objects.all()
    serializer_class = serializers.CreateExamBookSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)
    parser_class = (FileUploadParser)

    def get_queryset(self):
        book_obj = models.ExamSuggestedBooks.objects.filter(pk=self.kwargs.get('pk'))
        if not book_obj:
            raise ParseError("Book with this id DoesNotExist")
        return book_obj

    def delete(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            ques_obj = models.ExamSuggestedBooks.objects.get(pk=int(id))
            ques_obj.delete()
        except:
            return Response({"message": "Please enter valid book id"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Book deleted successfully"}, status=201)

class FetchTotalExamLearnersCountViewSet(ListAPIView,):
    permission_classes = [IsAuthenticatedOrReadOnly, ]

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam', None)
        
        if not exam_id:
            raise ParseError("Please enter exam Id")
        
        exam_id = int(exam_id)
        total_students = 0
        
        learnerexams_count = models.LearnerExams.objects.filter(exam__id=exam_id).count()
        try:
            studentsobj = models.ExamTotalStudents.objects.select_related("exam").values("total_students").get(exam__id=exam_id)
            total_students = studentsobj["total_students"]
        except ObjectDoesNotExist:
            pass
        if not total_students:
            total_students = 0
        final_count = learnerexams_count + total_students
        return final_count

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        # if queryset:
            # serializer = self.get_serializer(queryset[0], many=True)
        try:
            return Response({
                'totalusers':queryset,
            })
        except:
            return Response({'error': 'Error.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class CreateExamPreviousYearsPapersViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.CreateExamPreviousYearsPaperSerializer
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            exam_obj = models.Exam.objects.get(
                id=int(exam_id))
            if exam_obj:
                exam = models.ExamPreviousYearsPapers.objects.filter(
                    exam=exam_obj)
                return exam
        return models.ExamPreviousYearsPapers.objects.filter(is_active=True)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
class FetchExamPreviousYearsPapersViewSet(ListAPIView,):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.ExamPreviousYearsPaperSerializer

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            exam_obj = models.Exam.objects.get(
                id=int(exam_id))
            if exam_obj:
                exam = models.ExamPreviousYearsPapers.objects.filter(
                    exam=exam_obj)
                return exam
        return models.ExamPreviousYearsPapers.objects.filter(is_active=True)

class EditExamPreviousYearsPaperView(RetrieveUpdateAPIView):
    queryset = models.ExamPreviousYearsPapers.objects.all()
    serializer_class = serializers.CreateExamPreviousYearsPaperSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)
    parser_class = (FileUploadParser)

    def get_queryset(self):
        book_obj = models.ExamPreviousYearsPapers.objects.filter(pk=self.kwargs.get('pk'))
        if not book_obj:
            raise ParseError("Paper with this id DoesNotExist")
        return book_obj

    def delete(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            ques_obj = models.ExamPreviousYearsPapers.objects.get(pk=int(id))
            ques_obj.delete()
        except:
            return Response({"message": "Please enter valid paper id"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Paper deleted successfully"}, status=201)

class HintViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.ChapterHintSerializer

    def get_queryset(self):
        return models.ChapterHints.objects.all().order_by('id')

    # def create(self, request, *args, **kwargs):
    #     serializer = self.serializer_class(
    #         data=request.data, context={'request': request})
    #     serializer.is_valid(raise_exception=True)
    #     self.perform_create(serializer)
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)

class EditChapterHintViewSetViewSet(RetrieveUpdateAPIView):
    queryset = models.ChapterHints.objects.all()
    serializer_class = serializers.ChapterHintSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        level_obj = models.ChapterHints.objects.filter(pk=self.kwargs.get('pk'))
        if not level_obj:
            raise ParseError("Chapter Hint with this id DoesNotExist")
        return level_obj
    
    def delete(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            hint_obj = models.ChapterHints.objects.get(pk=int(id))
            hint_obj.delete()
        except:
            return Response({"message": "Please enter valid hint id"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Hint deleted successfully"}, status=201)

class ExamTotalStudentsViewSet(ListAPIView, CreateAPIView):
    serializer_class = serializers.ExamTotalStudentsSerializer
    create_serializer_class = serializers.ExamTotalStudentsSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            exam_obj = models.Exam.objects.get(id=exam_id)
            if exam_obj:
                total_obj = models.ExamTotalStudents.objects.filter(
                exam=exam_obj)
                return total_obj
            else:
                raise ParseError("Exam with this id DoesNotExist")
        return models.ExamTotalStudents.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.create_serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class EditExamTotalStudentsViewSet(RetrieveUpdateAPIView):
    queryset = models.ExamTotalStudents.objects.all()
    serializer_class = serializers.ExamTotalStudentsSerializer
    update_serializer_class = serializers.ExamTotalStudentsSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser, )

    def get_queryset(self):
        examtotal = models.ExamTotalStudents.objects.filter(
            pk=self.kwargs.get('pk'))
        if not examtotal:
            raise ParseError("Count data DoesNotExist")
        return examtotal

    def update(self, request, *args, **kwargs):
        questionavg = models.ExamTotalStudents.objects.get(
            pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            questionavg, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(questionavg).data, status=status.HTTP_200_OK)

class ExamStudentNotificationViewSet(ListAPIView, CreateAPIView):
    serializer_class = serializers.ExamStudentNotifictionSerializer
    create_serializer_class = serializers.ExamStudentNotifictionSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomPagination

    def get_queryset(self):
        return models.ExamStudentNotification.objects.all().order_by('-id')

    def create(self, request, *args, **kwargs):
        serializer = self.create_serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class BulkFTagUpload(APIView):
    permission_classes = (IsAuthenticated,)

    def compress(self, image, name):
        im = image
        # create a BytesIO object
        im_io = BytesIO()
        # save image to BytesIO object
        im.save(im_io, 'PNG')
        # create a django-friendly Files object
        new_image = File(im_io, name=name)
        return new_image

    def post(self, request):
        try:
            excel = request.data["excel_file"]
            df = pd.io.excel.read_excel(excel)
            head_list = list(df.columns[0:])
            ftag_objs = []
            for index, row in df.iterrows():
                if "FTag" in head_list:
                    tag = str(row["FTag"])
                    if not (len(tag) > 0 and tag != 'nan'):
                        tag = None
                else:
                    tag = None
                if "Description" in head_list:
                    description = row['Description']
                    if not (len(description) and description != 'nan'):
                        description = None
                else:
                    description = None
                try:
                    if tag:
                        ftagObj = models.Topic.objects.filter(title=tag).last()
                        if ftagObj:
                            ftagObj.description = description
                            ftagObj.save()
                        else:
                            ftagObj = models.Topic.objects.create(title=tag, description=description)
                        ftag_objs.append(ftagObj)
                except:
                    pass
        except:
            return Response({"message": "Some error occured"}, status=status.HTTP_400_BAD_REQUEST)
        ftagdata = serializers.TopicSerializer(ftag_objs, many=True).data
        return Response({"message": "List succesfully updated ", "ftags": ftagdata}, status=200)
            
class RemoveLinkedExamFromDomainNodeView(RetrieveUpdateAPIView):
    serializer_class = serializers.DomainNodeSerializer
    lookup_field = 'pk'

    def get_object(self):
        id = self.kwargs["pk"]
        try:
            return models.PathNodes.objects.get(pk=id)
        except:
            return models.PathNodes.objects.get(id=None)

    def put(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            node_obj = models.PathNodes.objects.get(pk=int(id))
        except:
            return Response({"message": "Please enter valid id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # topic_obj = models.Topic.objects.get(pk=int(request.data.get('topic')))
            node_obj.linked_exam = None
            node_obj.save()
        except:
            return Response({"message": "error in delinking exam"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Exam delinked successfully"}, status=201)

class SelfAssessQuestionViewSet(ListAPIView, CreateAPIView):
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser, )
    serializer_class = serializers.SelfAssesQuestionSerializer

    def get_queryset(self):
        exam_id = self.request.query_params.get(
            'exam')
        if exam_id:
            question = models.SelfAssessQuestion.objects.filter(
                exam__id=int(exam_id)).order_by('order')
            return question
        return models.SelfAssessQuestion.objects.filter(is_active=True).order_by('order')

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class EditSelfAssessQuestionViewSet(RetrieveUpdateAPIView):
    queryset = models.SelfAssessQuestion.objects.all()
    serializer_class = serializers.SelfAssesQuestionSerializer
    update_serializer_class = serializers.SelfAssesQuestionSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        question = models.SelfAssessQuestion.objects.filter(pk=self.kwargs.get('pk')).order_by('order')
        if not question:
            raise ParseError("Question with this id DoesNotExist")
        return question

    def update(self, request, *args, **kwargs):
        question = models.SelfAssessQuestion.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            question, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(question).data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            ques_obj = models.SelfAssessQuestion.objects.get(pk=int(id))
            ques_obj.delete()
        except:
            return Response({"message": "Please enter valid Question id"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Question deleted successfully"}, status=201)

class SelfAssessExamQuestionViewSet(ListAPIView, CreateAPIView):
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser, )
    serializer_class = serializers.ViewSelfAssesExamQuestionSerializer
    createserializer_class = serializers.SelfAssesExamQuestionSerializer

    def get_queryset(self):
        exam_id = self.request.query_params.get(
            'exam')
        if exam_id:
            question = models.SelfAssessExamQuestions.objects.filter(
                exam__id=int(exam_id)).order_by('order')
            return question
        return models.SelfAssessExamQuestions.objects.filter(is_active=True).order_by('order')

    def create(self, request, *args, **kwargs):
        serializer = self.createserializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class EditSelfExamAssessQuestionViewSet(RetrieveUpdateAPIView):
    queryset = models.SelfAssessExamQuestions.objects.all()
    serializer_class = serializers.ViewSelfAssesExamQuestionSerializer
    update_serializer_class = serializers.SelfAssesExamQuestionSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        question = models.SelfAssessExamQuestions.objects.filter(pk=self.kwargs.get('pk')).order_by('order')
        if not question:
            raise ParseError("Question with this id DoesNotExist")
        return question

    def update(self, request, *args, **kwargs):
        question = models.SelfAssessExamQuestions.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            question, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(question).data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            ques_obj = models.SelfAssessExamQuestions.objects.get(pk=int(id))
            ques_obj.delete()
        except:
            return Response({"message": "Please enter valid Question id"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Question deleted successfully"}, status=201)

class SelfAssessQuestionBankViewSet(ListAPIView, CreateAPIView):
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser, )
    serializer_class = serializers.SelfAssesQuestionBankSerializer

    def get_queryset(self):
        return models.SelfAssessQuestionBank.objects.filter()

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class MCQOptionsViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    serializer_class = serializers.MCQTestCaseSerializer
    create_class = serializers.CreateMCQTestCaseSerializer

    def get_queryset(self):
        question_id = self.request.query_params.get('question')
        if question_id:
            solution = models.SelfAssessMcqOptions.objects.filter(
                questioncontent__id=question_id).order_by('id')
            return solution
        return models.SelfAssessMcqOptions.objects.all().order_by('id')

    def create(self, request, *args, **kwargs):
        serializer = self.create_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class EditMCQOptionsViewSet(RetrieveUpdateAPIView):
    queryset = models.SelfAssessMcqOptions.objects.all()
    serializer_class = serializers.MCQTestCaseSerializer
    update_serializer_class = serializers.EditMCQSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser,)

    def get_queryset(self):
        solution = models.SelfAssessMcqOptions.objects.filter(pk=self.kwargs.get('pk'))
        if not solution:
            raise ParseError("McqOption with this id DoesNotExist")
        return solution

    def update(self, request, *args, **kwargs):
        solution = models.SelfAssessMcqOptions.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            solution, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(solution).data, status=status.HTTP_200_OK)

class FetchChapterHintViewSet(ListAPIView, CreateAPIView):
    serializer_class = serializers.DetailViewChapterHintSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        chapter_id = self.request.query_params.get('chapter')
        hintIds = []
        if chapter_id:
            chapter_obj = models.Chapter.objects.get(
                id=int(chapter_id))
            hintIds = [tag.id for tag in chapter_obj.hints.all()]
            if chapter_obj:
                hints = models.ChapterHints.objects.filter(
                id__in=hintIds)
                return hints
            else:
                raise ParseError("Chapter with this id DoesNotExist")
        return models.Chapter.objects.all().order_by('order')

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class DetailViewChapterHintViewSetViewSet(RetrieveAPIView):
    queryset = models.ChapterHints.objects.all()
    serializer_class = serializers.DetailViewChapterHintSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        level_obj = models.ChapterHints.objects.filter(pk=self.kwargs.get('pk'))
        if not level_obj:
            raise ParseError("Chapter Hint with this id DoesNotExist")
        return level_obj

class HintConceptViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.ChapterHintConceptSerializer

    def get_queryset(self):
        return models.ChapterHintConcepts.objects.all().order_by('id')

class EditHintConceptViewSetViewSet(RetrieveUpdateAPIView):
    queryset = models.ChapterHintConcepts.objects.all()
    serializer_class = serializers.ChapterHintConceptSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        level_obj = models.ChapterHintConcepts.objects.filter(pk=self.kwargs.get('pk'))
        if not level_obj:
            raise ParseError("Hint Concept with this id DoesNotExist")
        return level_obj
    
    def delete(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            concept_obj = models.ChapterHintConcepts.objects.get(pk=int(id))
            concept_obj.delete()
        except:
            return Response({"message": "Please enter valid concept id"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Concept deleted successfully"}, status=201)

class BloomLevelViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.BloomLevelSerializer

    def get_queryset(self):
        return models.BloomLevel.objects.all().order_by('id')

class ExamDomainsForExamViewSet(ListAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.ViewDomainSerializer
    parser_classes = (FormParser, MultiPartParser)
    queryset = models.ExamDomain.objects.prefetch_related("exam_category", "exams").order_by('order')

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam_id')
        if exam_id:
            examDomain = self.queryset.filter(exams__id=int(exam_id), is_active=True)
            return examDomain
        return self.queryset.filter(is_active=True)

class DelinkLearnerExamsQuestionsView(UpdateAPIView):
    serializer_class = serializers.LearnerExamSerializer

    def put(self, request, *args, **kwargs):
        exam_obj = models.LearnerExams.objects.filter(user=self.request.user, is_active=True)
        try:
            for exam in exam_obj:
                exam.is_active = False
                exam.save()
        except:
            return Response({"message": "error in delinking the exams"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "exams delinked successfully"}, status=201)

class DelinkMentorExamsView(UpdateAPIView):
    serializer_class = serializers.MentorExamSerializer

    def put(self, request, *args, **kwargs):
        batch_id = request.data.get('batch')
        batch_obj = Batch.objects.get(id=int(batch_id))
        exam_obj = models.MentorExams.objects.filter(user=self.request.user, batches=batch_obj, is_active=True)
        try:
            for exam in exam_obj:
                exam.is_active = False
                exam.save()
        except:
            return Response({"message": "error in delinking the exams"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "exams delinked successfully"}, status=201)

class ChapterVideoView(ModelViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'], url_path="submit-rating")
    def submit_rating(self, request, pk):
        request_data = request.data
        rating = request_data.get("rating")
        if not rating:
            raise ValidationError("Rating can not be empty")
        
        chapter_helper.ChapterVideoHelper.submit_rating(pk, rating, request.user)

        return Response(status=200, data = {"message": "Thanks for rating."})

    @action(detail=False, methods=['post'], url_path="upload-file")
    def upload_file(self, request):
        file_data = request.FILES["file"]
        total_success, failed_rows = chapter_helper.ChapterVideoHelper.upload_bulk_file(file_data)
        return Response(
            status=200, 
            data = 
            {
            "message": "File has been uploaded",
            "total_success": total_success,
            "failed_rows": failed_rows
            }
        )
