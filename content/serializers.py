from core import models
from rest_framework import serializers
from content import models as content_models
from courses import models as courses_models
from courses import serializers as course_serializer
import re
import uuid
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import timedelta
from authentication import models as auth_models
from profiles.models import Institute, Profile
import datetime

from profiles.serializers import ShortProfileSerializer

class Base64ImageField(serializers.ImageField):
    """
    A Django REST framework field for handling image-uploads through raw post data.
    It uses base64 for encoding and decoding the contents of the file.

    Heavily based on
    https://github.com/tomchristie/django-rest-framework/pull/1268

    Updated for Django REST framework 3.
    """

    def to_internal_value(self, data):
        from django.core.files.base import ContentFile
        import base64
        import six
        import uuid

        # Check if this is a base64 string
        if isinstance(data, six.string_types):
            # Check if the base64 string is in the "data:" format
            if 'data:' in data and ';base64,' in data:
                # Break out the header from the base64 content
                header, data = data.split(';base64,')

            # Try to decode the file. Return validation error if it fails.
            try:
                decoded_file = base64.b64decode(data)
            except TypeError:
                self.fail('invalid_image')

            # Generate file name:
            file_name = str(uuid.uuid4())[:12] # 12 characters are more than enough.
            # Get the file name extension:
            file_extension = self.get_file_extension(file_name, decoded_file)

            complete_file_name = "%s.%s" % (file_name, file_extension, )

            data = ContentFile(decoded_file, name=complete_file_name)

        return super(Base64ImageField, self).to_internal_value(data)

    def get_file_extension(self, file_name, decoded_file):
        import imghdr

        extension = imghdr.what(file_name, decoded_file)
        extension = "jpg" if extension == "jpeg" else extension

        return extension


class QuestionTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = content_models.QuestionTag
        fields = ["id", "text", ]


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = courses_models.Topic
        fields = ["id", "title", "description"]


class QuestionLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = content_models.QuestionLanguage
        fields = ["id", "text", ]


class ComprehensionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = content_models.Comprehensions
        fields = ["html_txt", "linked_questions"]


class QuestionContentSerializer(serializers.ModelSerializer):
    language = serializers.SerializerMethodField()
    comprehension = serializers.SerializerMethodField()

    class Meta:
        model = content_models.QuestionContent
        fields = ["id", "text", "language", "comprehension"]

    def get_language(self, obj):
        return QuestionLanguageSerializer(obj.language).data

    def get_comprehension(self, obj):
        return ComprehensionsSerializer(obj.comprehension).data


class CreateQuestionContentSerializer(serializers.ModelSerializer):
    text = serializers.CharField()
    language = serializers.PrimaryKeyRelatedField(
        queryset=content_models.QuestionLanguage.objects.all(), required=False)
    comprehension = serializers.PrimaryKeyRelatedField(
        queryset=content_models.Comprehensions.objects.all(), required=False)

    class Meta:
        model = content_models.QuestionContent
        fields = ["id", "text", "language", "comprehension"]

    def create(self, validated_data):
        text = validated_data.get('text')
        language = validated_data.get('language')
        comprehension = validated_data.get('comprehension')
        questioncontent_obj = content_models.QuestionContent.objects.create(
            text=text, language=language)
        # if language:
        #     lang_obj = content_models.QuestionLanguage.objects.get(id=int(language.id))
        #     questioncontent_obj.language = lang_obj
        if comprehension:
            questioncontent_obj.comprehension = comprehension
        questioncontent_obj.save()
        return questioncontent_obj


class EditQuestionContentSerializer(serializers.ModelSerializer):
    text = serializers.CharField()
    language = serializers.PrimaryKeyRelatedField(
        queryset=content_models.QuestionLanguage.objects.all(), required=False)
    comprehension = serializers.PrimaryKeyRelatedField(
        queryset=content_models.Comprehensions.objects.all(), required=False)

    class Meta:
        model = content_models.QuestionContent
        fields = ["id", "text", "language", "comprehension"]

    def update(self, instance, validated_data):
        text = validated_data.get('text')
        language = validated_data.get('language')
        comprehension = validated_data.get('comprehension')
        if text:
            instance.text = text
        if language:
            instance.language = language
        if comprehension:
            instance.comprehension = comprehension
        instance.save()
        return instance


class QuestionSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    linked_topics = serializers.SerializerMethodField()
    contents = serializers.SerializerMethodField()

    class Meta:
        model = content_models.Question
        fields = ["id",
                  "tags",
                  "linked_topics",
                  "difficulty",
                  "is_active",
                  "contents",
                  "type_of_question",
                  "question_identifier",
                  "ideal_time"
                  ]

    def get_tags(self, obj):
        return QuestionTagSerializer(obj.tags.all(), many=True).data

    def get_linked_topics(self, obj):
        return TopicSerializer(obj.linked_topics.all(), many=True).data

    def get_contents(self, obj):
        return QuestionContentSerializer(obj.contents.all(), many=True).data

class ShortQuestionSerializer(serializers.ModelSerializer):
    contents = serializers.SerializerMethodField()

    class Meta:
        model = content_models.Question
        fields = ["id",
                  "difficulty",
                  "is_active",
                  "contents",
                  "type_of_question",
                  "ideal_time"
                  ]

    def get_contents(self, obj):
        return QuestionContentSerializer(obj.contents.all(), many=True).data

class QuestionInPaperSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    linked_topics = serializers.SerializerMethodField()
    contents = serializers.SerializerMethodField()
    options = serializers.SerializerMethodField()
    fillupoptions = serializers.SerializerMethodField()

    class Meta:
        model = content_models.Question
        fields = ["id",
                  "tags",
                  "linked_topics",
                  "difficulty",
                  "is_active",
                  "contents",
                  "type_of_question",
                  "question_identifier",
                  "ideal_time",
                  "options",
                  "fillupoptions"
                  ]

    def get_tags(self, obj):
        return QuestionTagSerializer(obj.tags.all(), many=True).data

    def get_linked_topics(self, obj):
        return TopicSerializer(obj.linked_topics.all(), many=True).data

    def get_contents(self, obj):
        return QuestionContentSerializer(obj.contents.all(), many=True).data

    def get_options(self, instance):
        if instance.type_of_question in ['mcq', 'mcc', 'assertion']:
            contentids = [tag.id for tag in instance.contents.all()]
            content = content_models.QuestionContent.objects.filter(id__in=contentids, language__text='English').last()
            return MCQTestCaseSerializer(content_models.McqTestCase.objects.filter(questioncontent=content), many=True).data
        else:
            return []

    def get_fillupoptions(self, instance):
        if instance.type_of_question == 'fillup_option':
            contentids = [tag.id for tag in instance.contents.all()]
            content = content_models.QuestionContent.objects.filter(id__in=contentids, language__text='English').last()
            return FillWithOptionCaseSerializer(content_models.FillUpWithOption.objects.filter(questioncontent=content), many=True).data
        else:
            return []

class CreateQuestionSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=content_models.QuestionTag.objects.all(), required=False)
    linked_topics = serializers.PrimaryKeyRelatedField(
        many=True, queryset=courses_models.Topic.objects.all(), required=False)
    contents = serializers.PrimaryKeyRelatedField(
        many=True, queryset=content_models.QuestionContent.objects.all(), required=False)

    class Meta:
        model = content_models.Question
        fields = ["tags",
                  "linked_topics",
                  "difficulty",
                  "contents",
                  "type_of_question",
                  "question_identifier",
                  "is_active",
                  "ideal_time"
                  ]

    def create(self, validated_data):
        tags = validated_data.get('tags')
        linked_topics = validated_data.get('linked_topics')
        difficulty = validated_data.get('difficulty')
        contents = validated_data.get('contents')
        type_of_question = validated_data.get('type_of_question')
        question_identifier = validated_data.get('question_identifier')
        is_active = validated_data.get('is_active')
        ideal_time = validated_data.get('ideal_time')

        question_obj = content_models.Question.objects.create(
            difficulty=difficulty,
            type_of_question=type_of_question,
            is_active=is_active,
        )

        if tags:
            question_obj.tags.add(*tags)
        if linked_topics:
            question_obj.linked_topics.add(*linked_topics)
        if contents:
            question_obj.contents.add(*contents)
            for content in contents:
                lang_obj = content_models.QuestionLanguage.objects.get(id=int(content.language.id))
                question_obj.languages.add(lang_obj)
                question_obj.save()
        if question_identifier:
            question_obj.question_identifier = question_identifier
        if ideal_time:
            question_obj.ideal_time = ideal_time

        question_obj.save()

        return question_obj


class EditQuestionSerializer(serializers.ModelSerializer):
    difficulty = serializers.CharField(max_length=255, required=False)
    question_identifier = serializers.CharField(max_length=255, required=False)
    type_of_question = serializers.CharField(max_length=255, required=False)
    ideal_time = serializers.IntegerField()
    is_active = serializers.BooleanField(required=False)
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=content_models.QuestionTag.objects.all(), required=False)
    linked_topics = serializers.PrimaryKeyRelatedField(
        many=True, queryset=courses_models.Topic.objects.all(), required=False)
    contents = serializers.PrimaryKeyRelatedField(
        many=True, queryset=content_models.QuestionContent.objects.all(), required=False)

    class Meta:
        model = content_models.Question
        fields = ["id",
                  "tags",
                  "linked_topics",
                  "difficulty",
                  "contents",
                  "type_of_question",
                  "question_identifier",
                  "is_active",
                  "ideal_time"
                  ]

    def update(self, instance, validated_data):
        tags = validated_data.get('tags')
        linked_topics = validated_data.get('linked_topics')
        difficulty = validated_data.get('difficulty')
        contents = validated_data.get('contents')
        type_of_question = validated_data.get('type_of_question')
        question_identifier = validated_data.get('question_identifier')
        is_active = validated_data.get('is_active')
        ideal_time = validated_data.get('ideal_time')

        instance.tags.clear()
        instance.linked_topics.clear()
        if tags:
            instance.tags.add(*tags)
        if linked_topics:
            instance.linked_topics.add(*linked_topics)
        if contents:
            instance.contents.add(*contents)
        if difficulty:
            instance.difficulty = difficulty
        if question_identifier:
            instance.question_identifier = question_identifier
        if ideal_time:
            instance.ideal_time = int(ideal_time)
        instance.is_active = is_active
        instance.save()

        return instance

class SolutionSerializer(serializers.ModelSerializer):
    questioncontent = serializers.SerializerMethodField()

    class Meta:
        model = content_models.Solution
        fields = ["id",
                  "text",
                  "questioncontent",
                  ]

    def get_questioncontent(self, obj):
        return QuestionContentSerializer(obj.questioncontent).data


class CreateSolutionSerializer(serializers.ModelSerializer):
    text = serializers.CharField()
    # questioncontent = serializers.SerializerMethodField()
    questioncontent = serializers.PrimaryKeyRelatedField(
        queryset=content_models.QuestionContent.objects.all(), required=False)
    

    class Meta:
        model = content_models.Solution
        fields = ["text",
                  "questioncontent",
                  ]
    
    # def get_questioncontent(self, obj):
    #     return QuestionContentSerializer(obj.questioncontent).data

    def create(self, validated_data):
        text = validated_data.get('text')

        # questioncontent = self._context.get("request").data['questioncontent']

        questioncontent = validated_data.get('questioncontent')

        solution_obj = content_models.Solution.objects.create(
            text=text)

        if questioncontent:
            # content_obj = content_models.QuestionContent.objects.get(id=questioncontent)
            # print ("questioncontent", questioncontent)
            solution_obj.questioncontent = questioncontent

        solution_obj.save()

        return solution_obj

class EditSolutionSerializer(serializers.ModelSerializer):
    text = serializers.CharField()

    class Meta:
        model = content_models.Solution
        fields = ["id", "text"]

    def update(self, instance, validated_data):
        text = validated_data.get('text')
        if text:
            instance.text = text
        instance.save()
        return instance

class FillUpSolutionSerializer(serializers.ModelSerializer):
    questioncontent = serializers.SerializerMethodField()

    class Meta:
        model = content_models.FillUpSolution
        fields = ["id",
                  "text",
                  "questioncontent",
                  ]

    def get_questioncontent(self, obj):
        return QuestionContentSerializer(obj.questioncontent).data

class CreateFillUpSolutionSerializer(serializers.ModelSerializer):
    text = serializers.CharField()
    # questioncontent = serializers.SerializerMethodField()
    questioncontent = serializers.PrimaryKeyRelatedField(
        queryset=content_models.QuestionContent.objects.all(), required=False)
    

    class Meta:
        model = content_models.FillUpSolution
        fields = ["text",
                  "questioncontent",
                  ]

    def create(self, validated_data):
        text = validated_data.get('text')

        questioncontent = validated_data.get('questioncontent')

        solution_obj = content_models.FillUpSolution.objects.create(
            text=text)

        if questioncontent:
            solution_obj.questioncontent = questioncontent

        solution_obj.save()

        return solution_obj

class EditFillUpSolutionSerializer(serializers.ModelSerializer):
    text = serializers.CharField()

    class Meta:
        model = content_models.FillUpSolution
        fields = ["id", "text"]

    def update(self, instance, validated_data):
        text = validated_data.get('text')
        if text:
            instance.text = text
        instance.save()
        return instance

class StringTestCaseSerializer(serializers.ModelSerializer):
    questioncontent = serializers.SerializerMethodField()

    class Meta:
        model = content_models.StringTestCase
        fields = ["id",
                  "text",
                  "questioncontent",
                  ]

    def get_questioncontent(self, obj):
        return QuestionContentSerializer(obj.questioncontent).data

class CreateStringTestCaseSerializer(serializers.ModelSerializer):
    text = serializers.CharField()
    # questioncontent = serializers.SerializerMethodField()
    questioncontent = serializers.PrimaryKeyRelatedField(
        queryset=content_models.QuestionContent.objects.all(), required=False)
    

    class Meta:
        model = content_models.StringTestCase
        fields = ["text",
                  "questioncontent",
                  ]

    def create(self, validated_data):
        text = validated_data.get('text')

        questioncontent = validated_data.get('questioncontent')

        solution_obj = content_models.StringTestCase.objects.create(
            text=text)

        if questioncontent:
            solution_obj.questioncontent = questioncontent

        solution_obj.save()

        return solution_obj

class EditStringTestCaseSerializer(serializers.ModelSerializer):
    text = serializers.CharField()

    class Meta:
        model = content_models.StringTestCase
        fields = ["id", "text"]

    def update(self, instance, validated_data):
        text = validated_data.get('text')
        if text:
            instance.text = text
        instance.save()
        return instance

class BooleanTypeSerializer(serializers.ModelSerializer):
    questioncontent = serializers.SerializerMethodField()

    class Meta:
        model = content_models.TrueFalseSolution
        fields = ["id",
                  "option",
                  "questioncontent",
                  ]

    def get_questioncontent(self, obj):
        return QuestionContentSerializer(obj.questioncontent).data

class CreateBooleanTypeSerializer(serializers.ModelSerializer):
    option = serializers.BooleanField()
    # questioncontent = serializers.SerializerMethodField()
    questioncontent = serializers.PrimaryKeyRelatedField(
        queryset=content_models.QuestionContent.objects.all(), required=False)
    

    class Meta:
        model = content_models.TrueFalseSolution
        fields = ["option",
                  "questioncontent",
                  ]

    def create(self, validated_data):
        option = validated_data.get('option')

        questioncontent = validated_data.get('questioncontent')

        solution_obj = content_models.TrueFalseSolution.objects.create(
            option=option)

        if questioncontent:
            solution_obj.questioncontent = questioncontent

        solution_obj.save()

        return solution_obj

# class EditFillUpSolutionSerializer(serializers.ModelSerializer):
#     option = serializers.CharField()

#     class Meta:
#         model = content_models.TrueFalseSolution
#         fields = ["id", "option"]

#     def update(self, instance, validated_data):
#         option = validated_data.get('option')
#         instance.option = option
#         instance.save()
#         return instance

class MCQTestCaseSerializer(serializers.ModelSerializer):
    questioncontent = serializers.SerializerMethodField()

    class Meta:
        model = content_models.McqTestCase
        fields = ["id",
                  "text",
                  "questioncontent",
                  "correct"
                  ]

    def get_questioncontent(self, obj):
        return QuestionContentSerializer(obj.questioncontent).data

class CreateMCQTestCaseSerializer(serializers.ModelSerializer):
    text = serializers.CharField()
    # questioncontent = serializers.SerializerMethodField()
    questioncontent = serializers.PrimaryKeyRelatedField(
        queryset=content_models.QuestionContent.objects.all(), required=False)
    

    class Meta:
        model = content_models.McqTestCase
        fields = ["text",
                  "questioncontent",
                  "correct"
                  ]
    
    def create(self, validated_data):
        text = validated_data.get('text')
        correct = validated_data.get('correct')

        questioncontent = validated_data.get('questioncontent')

        mcq_obj = content_models.McqTestCase.objects.create(
            text=text, correct=correct)

        if questioncontent:
            mcq_obj.questioncontent = questioncontent

        mcq_obj.save()
        return mcq_obj

class EditMCQSerializer(serializers.ModelSerializer):
    text = serializers.CharField()
    correct = serializers.BooleanField()

    class Meta:
        model = content_models.McqTestCase
        fields = ["id", "text", "correct"]

    def update(self, instance, validated_data):
        text = validated_data.get('text')
        correct = validated_data.get('correct')
        if text:
            instance.text = text
        # if correct:
        instance.correct = correct
        instance.save()
        return instance

class LearnerHistorySerializer(serializers.ModelSerializer):
    # username = serializers.SerializerMethodField()
    # userid = serializers.SerializerMethodField()
    # email = serializers.SerializerMethodField()
    # full_name = serializers.SerializerMethodField()
    # questions = serializers.SerializerMethodField()
    learner_exam = serializers.SerializerMethodField()
    # papers = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerHistory
        fields = ('id', 'user', 'learner_exam', 'questions', 'total_practice_time', 'total_paper_time', 'papers', 'total_questions')

    # def get_username(self, instance):
    #     return instance.user.username
    
    # def get_userid(self, instance):
    #     return instance.user.id

    # def get_email(self, instance):
    #     return instance.user.email

    # def get_full_name(self, instance):
    #     return instance.user.get_full_name()
    
    def get_learner_exam(self, instance):
        try:
            learner_exam = course_serializer.LearnerExamSerializer(instance.learner_exam, many=True).data
        except:
            learner_exam = None
        return learner_exam

    # def get_papers(self, instance):
    #     try:
    #         papers = LearnerPaperSerializer(instance.papers, many=True).data
    #     except:
    #         papers = None
    #     return papers

    # def get_questions(self, instance):
    #     try:
    #         questions = QuestionSerializer(instance.questions, many=True).data
    #     except:
    #         questions = None
    #     return questions

class ViewLearnerHistorySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = content_models.LearnerHistory
        fields = ('id', 'user', 'total_practice_time', 'total_paper_time', 'total_questions')


class LearnerExamHistorySerializer(serializers.ModelSerializer):
    # questions = serializers.SerializerMethodField()
    exam = serializers.SerializerMethodField()
    # papers = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerExamHistory
        fields = ('id', 'user', 'exam', 'questions', 'total_practice_time', 'total_paper_time', 'papers')
    
    def get_exam(self, instance):
        try:
            exam = course_serializer.LearnerExamSerializer(instance.exam).data
        except:
            exam = None
        return exam

    # def get_papers(self, instance):
    #     try:
    #         papers = LearnerPaperSerializer(instance.papers, many=True).data
    #     except:
    #         papers = None
    #     return papers

    # def get_questions(self, instance):
    #     try:
    #         questions = QuestionSerializer(instance.questions, many=True).data
    #     except:
    #         questions = None
    #     return questions

class ReAttemptPaperSerializer(serializers.ModelSerializer):
    class Meta:
        model = content_models.LearnerPapers
        fields = ('id', 'marks', 'score', 'learner_exam', 'paper_type', 'created_at', 'paper_count', 'actual_paper', 'submitted')

class LearnerPaperSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    userid = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    questions = serializers.SerializerMethodField()
    learner_exam = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()
    chapters = serializers.SerializerMethodField()
    bookmarks = serializers.SerializerMethodField()
    reattempt_papers = ReAttemptPaperSerializer(many=True, required=False)
    actual_paper = ReAttemptPaperSerializer()

    class Meta:
        model = content_models.LearnerPapers
        fields = ('id', 'username', 'userid', 'email', 'full_name', 'pause_count', 'is_linked_goal', 'goal_id', 'path_id', 'chapters', 'learner_exam', 'subjects', 'show_time', 'questions', 'bookmarks', 'marks', 'score', 'total_time', 'paper_type', 'paper_count', 'time_taken', 'created_at', 'actual_paper', 'reattempt_papers', 'submitted', 'remaining_time')

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
    
    def get_learner_exam(self, instance):
        try:
            learner_exam = course_serializer.LearnerExamSerializer(instance.learner_exam).data
        except:
            learner_exam = None
        return learner_exam

    def get_questions(self, instance):
        try:
            questions = QuestionSerializer(instance.questions, many=True).data
        except:
            questions = None
        return questions
    
    def get_bookmarks(self, instance):
        try:
            bookmarks = BookmarksSerializer(instance.bookmarks, many=True).data
        except:
            bookmarks = None
        return bookmarks
    
    def get_subjects(self, instance):
        try:
            subjects = course_serializer.SubjectSerializer(instance.subjects.all().order_by('id'), many=True).data
        except:
            subjects = None
        return subjects

    def get_chapters(self, instance):
        try:
            chapters = course_serializer.ChapterSerializer(instance.chapters.all().order_by('id'), many=True).data
        except:
            chapters = None
        return chapters

class CardViewLearnerPaperSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    learner_exam = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()
    chapters = serializers.SerializerMethodField()
    reattempt_papers = ReAttemptPaperSerializer(many=True, required=False)
    actual_paper = ReAttemptPaperSerializer()

    class Meta:
        model = content_models.LearnerPapers
        fields = ('id', 'username', 'learner_exam', 'pause_count', 'subjects', 'chapters', 'is_linked_goal', 'goal_id', 'path_id', 'show_time', 'questions', 'bookmarks', 'marks', 'score', 'total_time', 'paper_type', 'paper_count', 'time_taken', 'created_at', 'actual_paper', 'reattempt_papers', 'submitted', 'remaining_time')

    def get_username(self, instance):
        return instance.user.username
    
    def get_learner_exam(self, instance):
        try:
            learner_exam = course_serializer.LearnerExamSerializer(instance.learner_exam).data
        except:
            learner_exam = None
        return learner_exam

    def get_subjects(self, instance):
        try:
            subjects = course_serializer.SubjectSerializer(instance.subjects, many=True).data
        except:
            subjects = None
        return subjects
    
    def get_chapters(self, instance):
        try:
            chapters = course_serializer.ChapterSerializer(instance.chapters, many=True).data
        except:
            chapters = None
        return chapters

class SharedPaperViewLearnerPaperSerializer(serializers.ModelSerializer):

    class Meta:
        model = content_models.LearnerPapers
        fields = ('id', 'learner_exam', 'subjects', 'show_time', 'questions', 'bookmarks', 'marks', 'score', 'total_time', 'paper_type', 'paper_count', 'time_taken', 'created_at', 'actual_paper', 'reattempt_papers', 'submitted', 'remaining_time')

class LearnerExamChapterSerializer(serializers.ModelSerializer):
    learner_exam = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    chapter = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerExamChapters
        fields = ('id', 'learner_exam', 'subject', 'chapter', 'score', 'total_marks', 'percentage', 'time_taken', 'total_time', 'total_questions', 'attempted', 'created_at', 'correct', 'incorrect', 'unchecked', 'total_bookmarks')

    
    def get_learner_exam(self, instance):
        try:
            learner_exam = course_serializer.LearnerExamSerializer(instance.learner_exam).data
        except:
            learner_exam = None
        return learner_exam

    def get_subject(self, instance):
        try:
            subject = course_serializer.SubjectSerializer(instance.subject).data
        except:
            subject = None
        return subject
    
    def get_chapter(self, instance):
        try:
            chapter = course_serializer.ChapterSerializer(instance.chapter).data
        except:
            chapter = None
        return chapter

class LearnerExamSubjectSerializer(serializers.ModelSerializer):
    learner_exam = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerExamSubjects
        fields = ('id', 'learner_exam', 'subject', 'chapters', 'score', 'total_marks', 'percentage', 'time_taken', 'total_time', 'total_questions', 'attempted', 'created_at', 'correct', 'incorrect', 'unchecked', 'total_bookmarks')

    
    def get_learner_exam(self, instance):
        try:
            learner_exam = course_serializer.LearnerExamSerializer(instance.learner_exam).data
        except:
            learner_exam = None
        return learner_exam

    def get_subject(self, instance):
        try:
            subject = course_serializer.SubjectSerializer(instance.subject).data
        except:
            subject = None
        return subject


class SharedPaperSerializer(serializers.ModelSerializer):
    # shared_by_username = serializers.SerializerMethodField()
    # shared_by_userid = serializers.SerializerMethodField()
    # shared_by_email = serializers.SerializerMethodField()
    shared_by_full_name = serializers.SerializerMethodField()
    # shared_to_username = serializers.SerializerMethodField()
    # shared_to_userid = serializers.SerializerMethodField()
    # shared_to_email = serializers.SerializerMethodField()
    shared_to_full_name = serializers.SerializerMethodField()
    shared_paper = serializers.SerializerMethodField()
    newly_created_submitted = serializers.SerializerMethodField()
    newly_created_paper_count = serializers.SerializerMethodField()

    class Meta:
        model = content_models.SharedPapers
        fields = ('id', 'shared_by_full_name', 'shared_to_full_name', 'shared_paper', 'newly_created_paper', 'newly_created_paper_count', 'newly_created_submitted', 'shared_by_me_paper_count', 'shared_to_me_paper_count', 'created_at')

    # def get_shared_by_username(self, instance):
    #     return instance.sharer.username
    
    # def get_shared_by_userid(self, instance):
    #     return instance.sharer.id

    # def get_shared_by_email(self, instance):
    #     return instance.sharer.email

    def get_shared_by_full_name(self, instance):
        try:
            return instance.sharer.profile.first_name + ' ' + instance.sharer.profile.last_name
        except:
            return instance.sharer.profile.first_name
    
    # def get_shared_to_username(self, instance):
    #     return instance.shared_to.username
    
    # def get_shared_to_userid(self, instance):
    #     return instance.shared_to.id

    # def get_shared_to_email(self, instance):
    #     return instance.shared_to.email

    def get_shared_to_full_name(self, instance):
        try:
            return instance.shared_to.profile.first_name + ' ' + instance.shared_to.profile.last_name
        except:
            return instance.shared_to.profile.first_name
    
    def get_shared_paper(self, instance):
        try:
            shared_paper = CardViewLearnerPaperSerializer(instance.shared_paper).data
        except:
            shared_paper = None
        return shared_paper
    
    def get_newly_created_paper_count(self, instance):
        try:
            newly_created_paper_count = instance.newly_created_paper.paper_count
        except:
            newly_created_paper_count = None
        return newly_created_paper_count
    
    def get_newly_created_submitted(self, instance):
        try:
            newly_created_submitted = instance.newly_created_paper.submitted
        except:
            newly_created_submitted = None
        return newly_created_submitted

class PaperInstructionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = content_models.PaperInstructions
        fields = ["id", "paper", "instruction"]

class MentorPaperInstructionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = content_models.MentorPaperInstructions
        fields = ["id", "paper", "instruction"]

class GoalPaperInstructionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = content_models.GoalAssessmentExamPaperInstructions
        fields = ["id", "paper", "instruction"]

class FillWithOptionCaseSerializer(serializers.ModelSerializer):
    questioncontent = serializers.SerializerMethodField()

    class Meta:
        model = content_models.FillUpWithOption
        fields = ["id",
                  "text",
                  "questioncontent",
                  "correct"
                  ]

    def get_questioncontent(self, obj):
        return QuestionContentSerializer(obj.questioncontent).data

class CreateFillWithOptionSerializer(serializers.ModelSerializer):
    text = serializers.CharField()
    # questioncontent = serializers.SerializerMethodField()
    questioncontent = serializers.PrimaryKeyRelatedField(
        queryset=content_models.QuestionContent.objects.all(), required=False)
    

    class Meta:
        model = content_models.FillUpWithOption
        fields = ["text",
                  "questioncontent",
                  "correct"
                  ]
    
    def create(self, validated_data):
        text = validated_data.get('text')
        correct = validated_data.get('correct')

        questioncontent = validated_data.get('questioncontent')

        fillup_obj = content_models.FillUpWithOption.objects.create(
            text=text, correct=correct)

        if questioncontent:
            fillup_obj.questioncontent = questioncontent

        fillup_obj.save()
        return fillup_obj

class EditFillWithOptionSerializer(serializers.ModelSerializer):
    text = serializers.CharField()
    correct = serializers.BooleanField()

    class Meta:
        model = content_models.FillUpWithOption
        fields = ["id", "text", "correct"]

    def update(self, instance, validated_data):
        text = validated_data.get('text')
        correct = validated_data.get('correct')
        if text:
            instance.text = text
        instance.correct = correct
        instance.save()
        return instance

class UserSubjectiveAnswerImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = content_models.UserSubjectiveAnswerImage
        fields = ('id','user_subjective_answer_image')

class PostUserSubjectiveAnswerImageSerializer(serializers.Serializer):
    user_subjective_answer_image = Base64ImageField(max_length=None, use_url=True)

    def create(self, validated_data):
        return content_models.UserSubjectiveAnswerImage.objects.create(user_subjective_answer_image=validated_data.get('user_subjective_answer_image'))

class UserAnswerSerializer(serializers.ModelSerializer):
    answer_paper = serializers.SerializerMethodField()
    question = serializers.SerializerMethodField()
    type_of_paper = serializers.SerializerMethodField()
    user_subjective_answer_image = serializers.SerializerMethodField()
    user_subjective_answer_images = serializers.SerializerMethodField()

    class Meta:
        model = content_models.UserAnswer
        fields = ('answer_paper','question', 'user_subjective_answer_image', 'user_subjective_answer_images', 'user_fillup_option_answer', 'type_of_answer', 'type_of_paper', 'attempt_order', 'user_mcq_answer', 'user_boolean_answer', 'user_string_answer', 'user_subjective_answer','timespent')

    def get_answer_paper(self, instance):
        return instance.answer_paper.id

    def get_question(self, instance):
        return instance.question.id

    def get_type_of_paper(self, instance):
        if instance.answer_paper.assessment_paper:
            return 'assessment'
        else:
            return 'mock'

    def get_user_subjective_answer_image(self, instance):
        return instance.user_subjective_answer_image.url if instance.user_subjective_answer_image else None
    
    def get_user_subjective_answer_images(self, instance):
        return UserSubjectiveAnswerImageSerializer(instance.user_subjective_answer_images, many=True).data

class UserAnswerMentorPaperSerializer(serializers.ModelSerializer):
    answer_paper = serializers.SerializerMethodField()
    question = serializers.SerializerMethodField()
    type_of_paper = serializers.SerializerMethodField()
    user_subjective_answer_image = serializers.SerializerMethodField()
    user_subjective_answer_images = serializers.SerializerMethodField()

    class Meta:
        model = content_models.UserAnswerMentorPaper
        fields = ('answer_paper','question', 'user_subjective_answer_image', 'user_subjective_answer_images', 'user_fillup_option_answer', 'type_of_answer', 'type_of_paper', 'attempt_order', 'user_mcq_answer', 'user_boolean_answer', 'user_string_answer', 'user_subjective_answer','timespent')

    def get_answer_paper(self, instance):
        return instance.answer_paper.id

    def get_question(self, instance):
        return instance.question.id

    def get_type_of_paper(self, instance):
        if instance.answer_paper.mentor_paper:
            return 'assessment'
        else:
            return 'mock'

    def get_user_subjective_answer_image(self, instance):
        return instance.user_subjective_answer_image.url if instance.user_subjective_answer_image else None
    
    def get_user_subjective_answer_images(self, instance):
        return UserSubjectiveAnswerImageSerializer(instance.user_subjective_answer_images, many=True).data

class PostAnswerSerializer(serializers.Serializer):
    answer_paper = serializers.PrimaryKeyRelatedField(queryset=content_models.AnswerPaper.objects.all())
    question = serializers.PrimaryKeyRelatedField(queryset=content_models.Question.objects.all())
    questioncontent = serializers.PrimaryKeyRelatedField(queryset=content_models.QuestionContent.objects.all())
    type_of_answer = serializers.CharField()
    type_of_paper = serializers.CharField()
    attempt_order = serializers.IntegerField()
    user_mcq_answer = serializers.PrimaryKeyRelatedField(queryset=content_models.McqTestCase.objects.all(), many=True, required=False, default=[])
    # user_mcq_answer = serializers.CharField(default='')
    user_string_answer = serializers.CharField(default='')
    user_boolean_answer = serializers.BooleanField(required=False, default=None)
    user_subjective_answer = serializers.CharField(default='')
    # user_subjective_answer_image = serializers.ImageField(required=False)
    user_subjective_answer_image = Base64ImageField(max_length=None, use_url=True, required=False)
    user_subjective_answer_images = serializers.PrimaryKeyRelatedField(queryset=content_models.UserSubjectiveAnswerImage.objects.all(), many=True, required=False, default=[])
    timespent = serializers.IntegerField(default=0)
    user_fillup_option_answer = serializers.PrimaryKeyRelatedField(queryset=content_models.FillUpWithOption.objects.all(), required=False, default=None)

    def validate(self, attrs):
        answer_paper = content_models.AnswerPaper.objects.get(id=attrs['answer_paper'].id)
        if answer_paper.paper_complete:
            raise serializers.ValidationError("Question already answered: id: [{}]".format(attrs['question'].id))
        question_list = map(int, re.sub("[^0-9,]", "", answer_paper.question_order).split(','))
        if attrs['question'].id not in question_list:
            raise serializers.ValidationError('Invalid question id- [{}]'.format(attrs['question'].id))
        return attrs

    def create(self, validated_data):
        question_response_obj, created = content_models.UserAnswer.objects.get_or_create(user=self.context.get('request').user,
            answer_paper=validated_data.get('answer_paper'),
            question=validated_data.get('question'),
            type_of_answer=validated_data.get('type_of_answer')
        )
        question_response_obj.attempt_order = validated_data.get('attempt_order')
        if validated_data.get('timespent'):
            question_response_obj.timespent = validated_data.get('timespent')
        if validated_data.get('type_of_answer') in ['mcq', 'mcc', 'assertion']:
            if validated_data.get('user_mcq_answer'):
                # user_mcq_answer_objs = models.McqTestCase.objects.filter(id__in=validated_data.get('user_mcq_answer').split(','))
                question_response_obj.user_mcq_answer.clear()
                # question_response_obj.user_mcq_answer.add(*user_mcq_answer_objs)
                question_response_obj.user_mcq_answer.add(*validated_data.get('user_mcq_answer'))
                question_response_obj.correct_mcq_answer.add(*list(content_models.McqTestCase.objects.filter(questioncontent=validated_data.get('questioncontent'), correct=True)))
        elif validated_data.get('type_of_answer') in ['fillup']:
            question_response_obj.user_string_answer = validated_data.get('user_string_answer')
            # print ("questioncontentaaa", validated_data.get('questioncontent'))
            correct_answer = content_models.FillUpSolution.objects.get(questioncontent=validated_data.get('questioncontent'))
            # print ("correct_answeraaa", correct_answer)
            question_response_obj.correct_fillup_answer = correct_answer
            # print ("correct_string_answeraa", question_response_obj.correct_string_answer)
        elif validated_data.get('type_of_answer') in ['boolean']:
            # if validated_data.get('user_boolean_answer'):
            question_response_obj.user_boolean_answer = validated_data.get('user_boolean_answer')
            # print ("questioncontentaaaboolean", validated_data.get('questioncontent'))
            boolean_obj = content_models.TrueFalseSolution.objects.get(questioncontent=validated_data.get('questioncontent'))
            # print ("boolean_obj", boolean_obj)
            question_response_obj.correct_boolean_answer = boolean_obj
            # print ("correct_boolean_answeraa", question_response_obj.correct_boolean_answer)
        elif validated_data.get('type_of_answer') in ['fillup_option']:
            question_response_obj.user_fillup_option_answer = validated_data.get('user_fillup_option_answer')
            # print ("questioncontentaaaoption", validated_data.get('questioncontent'))
            correct_answer = content_models.FillUpWithOption.objects.get(questioncontent=validated_data.get('questioncontent'), correct=True)
            # print ("correct_answeraaoption", correct_answer)
            question_response_obj.correct_fillup_option_answer = correct_answer
            # print ("correct_string_answeraa", question_response_obj.correct_string_answer)
        elif validated_data.get('type_of_answer') in ['numerical']:
            question_response_obj.user_string_answer = validated_data.get('user_string_answer')
            question_response_obj.correct_string_answer = content_models.StringTestCase.objects.get(questioncontent=validated_data.get('questioncontent'))
        elif validated_data.get('type_of_answer') in ['subjective', 'subjective_medium', 'subjective_short', 'subjective_very_short']:
            question_response_obj.user_subjective_answer = validated_data.get('user_subjective_answer')
            if validated_data.get('user_subjective_answer_image'):
                question_response_obj.user_subjective_answer_image = validated_data.get('user_subjective_answer_image')
            if validated_data.get('user_subjective_answer_images'):
                question_response_obj.user_subjective_answer_images.add(*validated_data.get('user_subjective_answer_images'))
        question_response_obj.save()
        assessment_paper_obj = validated_data.get('answer_paper').assessment_paper
        exam_obj = courses_models.Exam.objects.get(id=int(assessment_paper_obj.learner_exam.exam.id))
        # print ("examobj", exam_obj)
        try:
            mcq_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='mcq')
        except:
            mcq_linked_obj = None
        # print ("mcq_linked_obj", mcq_linked_obj)
        try:
            mcc_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='mcc')
        except:
            mcc_linked_obj = None
        try:
            fillup_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='fillup')
        except:
            fillup_linked_obj = None
        try:
            numerical_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='numerical')
        except:
            numerical_linked_obj = None
        try:
            boolean_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='boolean')
        except:
            boolean_linked_obj = None
        try:
            fillupoption_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='fillup_option')
        except:
            fillupoption_linked_obj = None
        try:
            assertion_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='assertion')
        except:
            assertion_linked_obj = None
        try:
            subjective_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='subjective')
        except:
            subjective_linked_obj = None
        if validated_data.get('type_of_answer') in ['mcq']:
            user_mcq_answer = question_response_obj.user_mcq_answer.all()
            correct_mcq_answer = question_response_obj.correct_mcq_answer.all()
            if set(user_mcq_answer.values_list('id')) == set(correct_mcq_answer.values_list('id')):
                question_response_obj.status = True
                question_response_obj.score = mcq_linked_obj.marks
            else:
                if mcq_linked_obj.negative_marks:
                    question_response_obj.score = mcq_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['mcc']:
            user_mcc_answer = question_response_obj.user_mcq_answer.all()
            correct_mcc_answer = question_response_obj.correct_mcq_answer.all()
            if set(user_mcc_answer.values_list('id')) == set(correct_mcc_answer.values_list('id')):
                question_response_obj.status = True
                question_response_obj.score = mcc_linked_obj.marks
            else:
                if mcc_linked_obj.negative_marks:
                    question_response_obj.score = mcc_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['assertion']:
            user_mcc_answer = question_response_obj.user_mcq_answer.all()
            correct_mcc_answer = question_response_obj.correct_mcq_answer.all()
            if set(user_mcc_answer.values_list('id')) == set(correct_mcc_answer.values_list('id')):
                question_response_obj.status = True
                question_response_obj.score = assertion_linked_obj.marks
            else:
                if assertion_linked_obj.negative_marks:
                    question_response_obj.score = assertion_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['fillup']:
            user_string_answer_flup = str(question_response_obj.user_string_answer.strip())
            correct_string_answer_flup = str(strip_tags(question_response_obj.correct_fillup_answer.text).strip())
            if user_string_answer_flup.lower() == correct_string_answer_flup.lower():
                question_response_obj.status = True
                question_response_obj.score = fillup_linked_obj.marks
            else:
                if fillup_linked_obj.negative_marks:
                    question_response_obj.score = fillup_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['fillup_option']:
            user_fillup_option_answer = question_response_obj.user_fillup_option_answer
            correct_string_answer_flup = question_response_obj.correct_fillup_option_answer
            if user_fillup_option_answer:
                if user_fillup_option_answer.id == correct_string_answer_flup.id:
                    question_response_obj.status = True
                    question_response_obj.score = fillupoption_linked_obj.marks
                else:
                    if fillupoption_linked_obj.negative_marks:
                        question_response_obj.score = fillupoption_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['boolean']:
            user_answer_boolean = str(question_response_obj.user_boolean_answer)
            correct_answer_boolean = str(question_response_obj.correct_boolean_answer.option)
            # print ("user_answer_boolean", user_answer_boolean, correct_answer_boolean)
            if user_answer_boolean == correct_answer_boolean:
                question_response_obj.status = True
                question_response_obj.score = boolean_linked_obj.marks
            else:
                if boolean_linked_obj.negative_marks:
                    question_response_obj.score = boolean_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['numerical']:
            user_string_answer_numerical = str(question_response_obj.user_string_answer.strip())
            correct_string_answer_numerical = str(question_response_obj.correct_string_answer.text)
            if user_string_answer_numerical.lower() == correct_string_answer_numerical.lower():
                question_response_obj.status = True
                question_response_obj.score = numerical_linked_obj.marks
            else:
                if numerical_linked_obj.negative_marks:
                    question_response_obj.score = numerical_linked_obj.negative_marks
        question_response_obj.save()
        return validated_data

class PostAnswerMentorPaperSerializer(serializers.Serializer):
    answer_paper = serializers.PrimaryKeyRelatedField(queryset=content_models.MentorPaperAnswerPaper.objects.all())
    question = serializers.PrimaryKeyRelatedField(queryset=content_models.Question.objects.all())
    questioncontent = serializers.PrimaryKeyRelatedField(queryset=content_models.QuestionContent.objects.all())
    type_of_answer = serializers.CharField()
    type_of_paper = serializers.CharField()
    attempt_order = serializers.IntegerField()
    user_mcq_answer = serializers.PrimaryKeyRelatedField(queryset=content_models.McqTestCase.objects.all(), many=True, required=False, default=[])
    # user_mcq_answer = serializers.CharField(default='')
    user_string_answer = serializers.CharField(default='')
    user_boolean_answer = serializers.BooleanField(required=False, default=None)
    user_subjective_answer = serializers.CharField(default='')
    # user_subjective_answer_image = serializers.ImageField(required=False)
    user_subjective_answer_image = Base64ImageField(max_length=None, use_url=True, required=False)
    user_subjective_answer_images = serializers.PrimaryKeyRelatedField(queryset=content_models.UserSubjectiveAnswerImage.objects.all(), many=True, required=False, default=[])
    timespent = serializers.IntegerField()
    user_fillup_option_answer = serializers.PrimaryKeyRelatedField(queryset=content_models.FillUpWithOption.objects.all(), required=False, default=None)

    def validate(self, attrs):
        answer_paper = content_models.MentorPaperAnswerPaper.objects.get(id=attrs['answer_paper'].id)
        if answer_paper.paper_complete:
            raise serializers.ValidationError("Question already answered: id: [{}]".format(attrs['question'].id))
        question_list = map(int, re.sub("[^0-9,]", "", answer_paper.question_order).split(','))
        if attrs['question'].id not in question_list:
            raise serializers.ValidationError('Invalid question id- [{}]'.format(attrs['question'].id))
        return attrs

    def create(self, validated_data):
        question_response_obj, created = content_models.UserAnswerMentorPaper.objects.get_or_create(user=self.context.get('request').user,
            answer_paper=validated_data.get('answer_paper'),
            question=validated_data.get('question'),
            type_of_answer=validated_data.get('type_of_answer')
        )
        question_response_obj.attempt_order = validated_data.get('attempt_order')
        if validated_data.get('timespent'):
            question_response_obj.timespent = validated_data.get('timespent')
        if validated_data.get('type_of_answer') in ['mcq', 'mcc', 'assertion']:
            if validated_data.get('user_mcq_answer'):
                # user_mcq_answer_objs = models.McqTestCase.objects.filter(id__in=validated_data.get('user_mcq_answer').split(','))
                question_response_obj.user_mcq_answer.clear()
                # question_response_obj.user_mcq_answer.add(*user_mcq_answer_objs)
                question_response_obj.user_mcq_answer.add(*validated_data.get('user_mcq_answer'))
                question_response_obj.correct_mcq_answer.add(*list(content_models.McqTestCase.objects.filter(questioncontent=validated_data.get('questioncontent'), correct=True)))
        elif validated_data.get('type_of_answer') in ['fillup']:
            question_response_obj.user_string_answer = validated_data.get('user_string_answer')
            # print ("questioncontentaaa", validated_data.get('questioncontent'))
            correct_answer = content_models.FillUpSolution.objects.get(questioncontent=validated_data.get('questioncontent'))
            # print ("correct_answeraaa", correct_answer)
            question_response_obj.correct_fillup_answer = correct_answer
            # print ("correct_string_answeraa", question_response_obj.correct_string_answer)
        elif validated_data.get('type_of_answer') in ['boolean']:
            # if validated_data.get('user_boolean_answer'):
            question_response_obj.user_boolean_answer = validated_data.get('user_boolean_answer')
            # print ("questioncontentaaaboolean", validated_data.get('questioncontent'))
            boolean_obj = content_models.TrueFalseSolution.objects.get(questioncontent=validated_data.get('questioncontent'))
            # print ("boolean_obj", boolean_obj)
            question_response_obj.correct_boolean_answer = boolean_obj
            # print ("correct_boolean_answeraa", question_response_obj.correct_boolean_answer)
        elif validated_data.get('type_of_answer') in ['fillup_option']:
            question_response_obj.user_fillup_option_answer = validated_data.get('user_fillup_option_answer')
            # print ("questioncontentaaaoption", validated_data.get('questioncontent'))
            correct_answer = content_models.FillUpWithOption.objects.get(questioncontent=validated_data.get('questioncontent'), correct=True)
            # print ("correct_answeraaoption", correct_answer)
            question_response_obj.correct_fillup_option_answer = correct_answer
            # print ("correct_string_answeraa", question_response_obj.correct_string_answer)
        elif validated_data.get('type_of_answer') in ['numerical']:
            question_response_obj.user_string_answer = validated_data.get('user_string_answer')
            question_response_obj.correct_string_answer = content_models.StringTestCase.objects.get(questioncontent=validated_data.get('questioncontent'))
        elif validated_data.get('type_of_answer') in ['subjective', 'subjective_medium', 'subjective_short', 'subjective_very_short']:
            question_response_obj.user_subjective_answer = validated_data.get('user_subjective_answer')
            if validated_data.get('user_subjective_answer_image'):
                question_response_obj.user_subjective_answer_image = validated_data.get('user_subjective_answer_image')
            if validated_data.get('user_subjective_answer_images'):
                question_response_obj.user_subjective_answer_images.add(*validated_data.get('user_subjective_answer_images'))
        question_response_obj.save()
        assessment_paper_obj = validated_data.get('answer_paper').mentor_paper
        exam_obj = courses_models.Exam.objects.get(id=int(assessment_paper_obj.exam.id))
        # print ("examobj", exam_obj)
        try:
            mcq_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='mcq')
        except:
            mcq_linked_obj = None
        # print ("mcq_linked_obj", mcq_linked_obj)
        try:
            mcc_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='mcc')
        except:
            mcc_linked_obj = None
        try:
            fillup_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='fillup')
        except:
            fillup_linked_obj = None
        try:
            numerical_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='numerical')
        except:
            numerical_linked_obj = None
        try:
            boolean_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='boolean')
        except:
            boolean_linked_obj = None
        try:
            fillupoption_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='fillup_option')
        except:
            fillupoption_linked_obj = None
        try:
            assertion_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='assertion')
        except:
            assertion_linked_obj = None
        try:
            subjective_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='subjective')
        except:
            subjective_linked_obj = None
        if validated_data.get('type_of_answer') in ['mcq']:
            user_mcq_answer = question_response_obj.user_mcq_answer.all()
            correct_mcq_answer = question_response_obj.correct_mcq_answer.all()
            if set(user_mcq_answer.values_list('id')) == set(correct_mcq_answer.values_list('id')):
                question_response_obj.status = True
                question_response_obj.score = mcq_linked_obj.marks
            else:
                if mcq_linked_obj.negative_marks:
                    question_response_obj.score = mcq_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['mcc']:
            user_mcc_answer = question_response_obj.user_mcq_answer.all()
            correct_mcc_answer = question_response_obj.correct_mcq_answer.all()
            if set(user_mcc_answer.values_list('id')) == set(correct_mcc_answer.values_list('id')):
                question_response_obj.status = True
                question_response_obj.score = mcc_linked_obj.marks
            else:
                if mcc_linked_obj.negative_marks:
                    question_response_obj.score = mcc_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['assertion']:
            user_mcc_answer = question_response_obj.user_mcq_answer.all()
            correct_mcc_answer = question_response_obj.correct_mcq_answer.all()
            if set(user_mcc_answer.values_list('id')) == set(correct_mcc_answer.values_list('id')):
                question_response_obj.status = True
                question_response_obj.score = assertion_linked_obj.marks
            else:
                if assertion_linked_obj.negative_marks:
                    question_response_obj.score = assertion_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['fillup']:
            user_string_answer_flup = str(question_response_obj.user_string_answer.strip())
            correct_string_answer_flup = str(strip_tags(question_response_obj.correct_fillup_answer.text).strip())
            if user_string_answer_flup.lower() == correct_string_answer_flup.lower():
                question_response_obj.status = True
                question_response_obj.score = fillup_linked_obj.marks
            else:
                if fillup_linked_obj.negative_marks:
                    question_response_obj.score = fillup_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['fillup_option']:
            user_fillup_option_answer = question_response_obj.user_fillup_option_answer
            correct_string_answer_flup = question_response_obj.correct_fillup_option_answer
            if user_fillup_option_answer:
                if user_fillup_option_answer.id == correct_string_answer_flup.id:
                    question_response_obj.status = True
                    question_response_obj.score = fillupoption_linked_obj.marks
                else:
                    if fillupoption_linked_obj.negative_marks:
                        question_response_obj.score = fillupoption_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['boolean']:
            user_answer_boolean = str(question_response_obj.user_boolean_answer)
            correct_answer_boolean = str(question_response_obj.correct_boolean_answer.option)
            # print ("user_answer_boolean", user_answer_boolean, correct_answer_boolean)
            if user_answer_boolean == correct_answer_boolean:
                question_response_obj.status = True
                question_response_obj.score = boolean_linked_obj.marks
            else:
                if boolean_linked_obj.negative_marks:
                    question_response_obj.score = boolean_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['numerical']:
            user_string_answer_numerical = str(question_response_obj.user_string_answer.strip())
            correct_string_answer_numerical = str(question_response_obj.correct_string_answer.text)
            if user_string_answer_numerical.lower() == correct_string_answer_numerical.lower():
                question_response_obj.status = True
                question_response_obj.score = numerical_linked_obj.marks
            else:
                if numerical_linked_obj.negative_marks:
                    question_response_obj.score = numerical_linked_obj.negative_marks
        question_response_obj.save()
        return validated_data

class AnswerPaperSerializer(serializers.ModelSerializer):
    assessment_paper = ReAttemptPaperSerializer()

    class Meta:
        model = content_models.AnswerPaper
        fields = ('assessment_paper', 'percentage','time_taken', 'paper_complete', 'attempted_date', 'start_time', 'total_time', 'total_questions', 'attempted', 'correct', 'unchecked', 'incorrect')

    # def get_assessment_paper(self, instance):
    #     return instance.assessment_paper.id

class MentorLearnerAnswerPaperSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = content_models.MentorPaperAnswerPaper
        fields = ('id', 'mentor_paper', 'username', 'full_name', 'percentage', 'time_taken', 'paper_complete', 'remaining_time', 'attempted_date', 'start_time', 'question_unanswered', 'question_answered','question_markforreview', 'question_save_markforreview', 'question_order', 'total_time', 'total_questions', 'attempted', 'correct', 'unchecked', 'incorrect', 'submitted', 'score', 'marks', 'remarks')
    
    def get_username(self, instance):
        return instance.user.username
    
    # def get_contact(self, instance):
    #     return instance.user.phonenumber

    def get_full_name(self, instance):
        try:
            return instance.user.profile.first_name + ' ' + instance.user.profile.last_name
        except:
            return instance.user.profile.first_name

class BookmarksSerializer(serializers.ModelSerializer):
    # username = serializers.SerializerMethodField()
    # userid = serializers.SerializerMethodField()
    # email = serializers.SerializerMethodField()
    # full_name = serializers.SerializerMethodField()
    question = serializers.SerializerMethodField()
    learner_exam = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    chapter = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerBookmarks
        fields = ('id', 'learner_exam', 'subject', 'chapter', 'question', 'created_at')
    
    def get_learner_exam(self, instance):
        try:
            learner_exam = course_serializer.LearnerExamSerializer(instance.learner_exam).data
        except:
            learner_exam = None
        return learner_exam

    def get_question(self, instance):
        try:
            question = QuestionSerializer(instance.question).data
        except:
            question = None
        return question
    
    def get_subject(self, instance):
        try:
            subject = course_serializer.SubjectSerializer(instance.subject).data
        except:
            subject = None
        return subject

    def get_chapter(self, instance):
        try:
            chapter = course_serializer.ChapterSerializer(instance.chapter).data
        except:
            chapter = None
        return chapter

class LearnerExamPracticeChapterSerializer(serializers.ModelSerializer):
    learner_exam = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    chapter = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerExamPracticeChapters
        fields = ('id', 'learner_exam', 'subject', 'chapter', 'score', 'total_marks', 'percentage', 'time_taken', 'total_time', 'total_questions', 'attempted', 'created_at', 'correct', 'unchecked', 'incorrect')

    
    def get_learner_exam(self, instance):
        try:
            learner_exam = course_serializer.LearnerExamSerializer(instance.learner_exam).data
        except:
            learner_exam = None
        return learner_exam

    def get_subject(self, instance):
        try:
            subject = course_serializer.SubjectSerializer(instance.subject).data
        except:
            subject = None
        return subject
    
    def get_chapter(self, instance):
        try:
            chapter = course_serializer.ChapterSerializer(instance.chapter).data
        except:
            chapter = None
        return chapter

class LearnerExamPracticeSubjectSerializer(serializers.ModelSerializer):
    learner_exam = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerExamPracticeSubjects
        fields = ('id', 'learner_exam', 'subject', 'chapters', 'score', 'total_marks', 'percentage', 'time_taken', 'total_time', 'total_questions', 'attempted', 'created_at', 'correct', 'unchecked', 'incorrect')

    
    def get_learner_exam(self, instance):
        try:
            learner_exam = course_serializer.LearnerExamSerializer(instance.learner_exam).data
        except:
            learner_exam = None
        return learner_exam

    def get_subject(self, instance):
        try:
            subject = course_serializer.SubjectSerializer(instance.subject).data
        except:
            subject = None
        return subject

class LearnerExamPaperChapterSerializer(serializers.ModelSerializer):
    learner_exam = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    chapter = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerExamPaperChapters
        fields = ('id', 'learner_exam', 'subject', 'chapter', 'score', 'total_marks', 'percentage', 'time_taken', 'total_time', 'total_questions', 'attempted', 'created_at', 'correct', 'unchecked', 'incorrect')

    
    def get_learner_exam(self, instance):
        try:
            learner_exam = course_serializer.LearnerExamSerializer(instance.learner_exam).data
        except:
            learner_exam = None
        return learner_exam

    def get_subject(self, instance):
        try:
            subject = course_serializer.SubjectSerializer(instance.subject).data
        except:
            subject = None
        return subject
    
    def get_chapter(self, instance):
        try:
            chapter = course_serializer.ViewChapterSerializer(instance.chapter).data
        except:
            chapter = None
        return chapter

class LearnerExamPaperSubjectSerializer(serializers.ModelSerializer):
    learner_exam = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerExamPaperSubjects
        fields = ('id', 'learner_exam', 'subject', 'chapters', 'score', 'total_marks', 'percentage', 'time_taken', 'total_time', 'total_questions', 'attempted', 'created_at', 'correct', 'unchecked', 'incorrect')

    
    def get_learner_exam(self, instance):
        try:
            learner_exam = course_serializer.LearnerExamSerializer(instance.learner_exam).data
        except:
            learner_exam = None
        return learner_exam

    def get_subject(self, instance):
        try:
            subject = course_serializer.SubjectSerializer(instance.subject).data
        except:
            subject = None
        return subject

class LearnerExamPracticeHistorySerializer(serializers.ModelSerializer):
    exam = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerExamPracticeHistory
        fields = ('id', 'user', 'exam', 'questions', 'papers', 'score', 'total_marks', 'percentage', 'time_taken', 'total_time', 'total_questions', 'attempted', 'created_at', 'correct', 'unchecked', 'incorrect')
    
    def get_exam(self, instance):
        try:
            exam = course_serializer.LearnerExamSerializer(instance.exam).data
        except:
            exam = None
        return exam

class LearnerExamPaperHistorySerializer(serializers.ModelSerializer):
    exam = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerExamPaperHistory
        fields = ('id', 'user', 'exam', 'questions', 'papers', 'score', 'total_marks', 'percentage', 'time_taken', 'total_time', 'total_questions', 'attempted', 'created_at', 'correct', 'unchecked', 'incorrect')
    
    def get_exam(self, instance):
        try:
            exam = course_serializer.LearnerExamSerializer(instance.exam).data
        except:
            exam = None
        return exam

class PostQueryQuestionsSerializer(serializers.ModelSerializer):

    class Meta:
        model = content_models.PostQuerySuggestiveQuestions
        fields = ('id', 'text', 'created_at')

    def create(self, validated_data):
        try:
            text = validated_data.get('text')
        except:
            raise serializers.ValidationError(
                    "Please enter query text")
        query_obj = content_models.PostQuerySuggestiveQuestions.objects.create(
            text=text)
        return query_obj

class LearnerQuerySerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    exam = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerQuery
        fields = ('id', 'user', 'username', 'exam', 'name', 'email', 'contact', 'reply', 'is_replied', 'query', 'created_at')

    def get_username(self, instance):
        if instance.user:
            return instance.user.username
        else:
            return None
    
    # def get_email(self, instance):
    #     return instance.user.email

    # def get_full_name(self, instance):
    #     return instance.user.get_full_name()
    
    def get_exam(self, instance):
        try:
            exam = course_serializer.ViewExamSerializer(instance.exam).data
        except:
            exam = None
        return exam

    def create(self, validated_data):
        name = validated_data.get('name')
        email = validated_data.get('email')
        contact = validated_data.get('contact')
        try:
            query = validated_data.get('query')
        except:
            raise serializers.ValidationError(
                    "Please enter your query")
        try:
            exam = self._context.get("request").data['exam']
        except:
            exam = None
        if exam:
            try:
                exam_obj = courses_models.Exam.objects.get(id=exam)
            except:
                raise serializers.ValidationError(
                    "Please select valid exam")
        if not self.context.get('request').user.is_anonymous:
            print ("aa", self.context.get('request').user)
            query_obj = content_models.LearnerQuery.objects.create(
                user=self.context.get('request').user, query=query)
        else:
            query_obj = content_models.LearnerQuery.objects.create(
                query=query)
        if name:
            query_obj.name = name
        if email:
            query_obj.email = email
        if contact:
            query_obj.contact = contact
        if exam:
            query_obj.exam = exam_obj
        query_obj.save()
        return query_obj

class ViewBatchSerializer(serializers.ModelSerializer):
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

class CreateBatchSerializer(serializers.ModelSerializer):

    class Meta:
        model = content_models.Batch
        fields = ('id', 'teacher', 'name', 'batch_code', 'students', 'created_at')

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

class MentorPaperSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    userid = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    questions = serializers.SerializerMethodField()
    exam = serializers.SerializerMethodField()
    batch = serializers.SerializerMethodField()
    chapters = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = content_models.MentorPapers
        fields = ('id', 'username', 'userid', 'email', 'exam_start_date_time', 'chapters', 'batch', 'full_name', 'exam', 'subjects', 'show_time', 'questions', 'marks', 'score', 'total_time', 'paper_type', 'time_taken', 'created_at', 'submitted', 'paper_count')

    def get_username(self, instance):
        return instance.mentor.username
    
    def get_userid(self, instance):
        return instance.mentor.id

    def get_email(self, instance):
        return instance.mentor.email

    def get_full_name(self, instance):
        return instance.mentor.get_full_name()
    
    def get_exam(self, instance):
        try:
            exam = course_serializer.ExamSerializer(instance.exam).data
        except:
            exam = None
        return exam

    def get_batch(self, instance):
        try:
            batch = ViewBatchSerializer(instance.batch).data
        except:
            batch = None
        return batch

    def get_questions(self, instance):
        try:
            questions = QuestionSerializer(instance.questions, many=True).data
        except:
            questions = None
        return questions
    
    def get_subjects(self, instance):
        try:
            subjects = course_serializer.SubjectSerializer(instance.subjects.all().order_by('id'), many=True).data
        except:
            subjects = None
        return subjects
    
    def get_chapters(self, instance):
        try:
            chapters = course_serializer.ChapterSerializer(instance.chapters.all().order_by('id'), many=True).data
        except:
            chapters = None
        return chapters

class CardViewMentorPaperSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    exam = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()
    chapters = serializers.SerializerMethodField()
    attempt_status = serializers.SerializerMethodField()

    class Meta:
        model = content_models.MentorPapers
        fields = ('id', 'username', 'batch', 'exam_start_date_time', 'exam_end_date_time', 'attempt_status', 'paper_count', 'exam', 'subjects', 'chapters', 'show_time', 'questions', 'marks', 'score', 'total_time', 'paper_type', 'time_taken', 'created_at', 'submitted')

    def get_username(self, instance):
        return instance.mentor.username
    
    def get_exam(self, instance):
        try:
            exam = course_serializer.ExamSerializer(instance.exam).data
        except:
            exam = None
        return exam

    def get_subjects(self, instance):
        try:
            subjects = course_serializer.SubjectSerializer(instance.subjects, many=True).data
        except:
            subjects = None
        return subjects
    
    def get_chapters(self, instance):
        try:
            chapters = course_serializer.ChapterSerializer(instance.chapters.all().order_by('id'), many=True).data
        except:
            chapters = None
        return chapters

    def get_current_user(self):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            return request.user
        return None
    
    def get_attempt_status(self, instance):
        user = self.get_current_user()
        try:
            if self.context.get("request").query_params.get('user'):
                user= auth_models.User.objects.get(username=self.context.get("request").query_params.get('user'))
        except:
            user = self.get_current_user()
        if not user.is_anonymous:
            answer_paper_obj = content_models.MentorPaperAnswerPaper.objects.filter(user=user, mentor_paper=instance)
            if answer_paper_obj:
                # print ("answerpaperobj", answer_paper_obj)
                starttime = answer_paper_obj.last().start_time
                currenttime = timezone.now()
                if answer_paper_obj.last().paper_complete:
                    time_remaining = False
                else:
                    if (currenttime >= (starttime + timedelta(minutes=int(instance.total_time)))):
                        time_remaining = False
                    else:
                        time_remaining = True
                return {"id": answer_paper_obj[0].id, "is_complete": answer_paper_obj[0].paper_complete, "attempted" : True, "time_remaining":time_remaining, "score": answer_paper_obj[0].score, "marks": instance.marks, "percentage": answer_paper_obj[0].percentage, "attempted_date": answer_paper_obj[0].attempted_date, "username": user.username, "remarks": answer_paper_obj[0].remarks}
            else:
                currenttime = timezone.now()
                try:
                    exam_start_date_time = instance.exam_start_date_time
                    exam_end_date_time = instance.exam_end_date_time
                    if currenttime < exam_start_date_time:
                        exam_start_date_time = exam_start_date_time + timezone.timedelta(hours=5, minutes=30)
                        return {"attempted" : False, "message":"Test will begin at {0} on {1}".format(exam_start_date_time.strftime("%I:%M %p"), exam_start_date_time.strftime("%d/%m/%Y"))}
                    elif currenttime > exam_start_date_time and currenttime < exam_end_date_time:
                        return {"attempted" : False, "start_status":True}
                    elif currenttime > exam_start_date_time and currenttime > exam_end_date_time:
                        return {"attempted" : False, "start_status":False}
                    else:
                        # return {"attempted" : False, "message":"You have not attempted this paper"}
                        return {"attempted" : False, "start_status":True}
                except:
                    if not exam_end_date_time:
                        return {"attempted" : False, "start_status":True}
                    return {"attempted" : False, "start_status":False}
        return False


class TemporaryBookmarksSerializer(serializers.ModelSerializer):
    question = serializers.SerializerMethodField()
    learner_exam = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    chapter = serializers.SerializerMethodField()

    class Meta:
        model = content_models.TemporaryLearnerBookmarks
        fields = ('id', 'learner_exam', 'paper', 'subject', 'chapter', 'question', 'created_at')
    
    def get_learner_exam(self, instance):
        try:
            learner_exam = course_serializer.LearnerExamSerializer(instance.learner_exam).data
        except:
            learner_exam = None
        return learner_exam

    def get_question(self, instance):
        try:
            question = QuestionSerializer(instance.question).data
        except:
            question = None
        return question
    
    def get_subject(self, instance):
        try:
            subject = course_serializer.SubjectSerializer(instance.subject).data
        except:
            subject = None
        return subject

    def get_chapter(self, instance):
        try:
            chapter = course_serializer.ChapterSerializer(instance.chapter).data
        except:
            chapter = None
        return chapter

class TemporaryMentorPaperBookmarksSerializer(serializers.ModelSerializer):
    question = serializers.SerializerMethodField()
    learner_exam = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    chapter = serializers.SerializerMethodField()

    class Meta:
        model = content_models.TemporaryMentorPaperLearnerBookmarks
        fields = ('id', 'learner_exam', 'paper', 'subject', 'chapter', 'question', 'created_at')
    
    def get_learner_exam(self, instance):
        try:
            learner_exam = course_serializer.LearnerExamSerializer(instance.learner_exam).data
        except:
            learner_exam = None
        return learner_exam

    def get_question(self, instance):
        try:
            question = QuestionSerializer(instance.question).data
        except:
            question = None
        return question
    
    def get_subject(self, instance):
        try:
            subject = course_serializer.SubjectSerializer(instance.subject).data
        except:
            subject = None
        return subject

    def get_chapter(self, instance):
        try:
            chapter = course_serializer.ChapterSerializer(instance.chapter).data
        except:
            chapter = None
        return chapter

class LearnerBatchHistorySerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    userid = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    batch = serializers.SerializerMethodField()
    profile_pic = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerBatchHistory
        fields = ('id', 'username', 'userid', 'email', 'contact', 'profile_pic', 'full_name', 'batch', 'is_blocked', 'questions', 'total_paper_count', 'total_practice_count', 'total_practice_time_taken', 'total_paper_time_taken', 'paper_score', 'total_paper_marks', 'practice_score', 'total_practice_marks', 'paper_percentage', 'practice_percentage', 'total_paper_time', 'total_practice_time', 'total_questions', 'total_attempted_paper')
    
    def get_profile_pic(self, instance):
        try:
            return instance.user.profile.image.url
        except:
            return None

    def get_username(self, instance):
        return instance.user.username
    
    def get_userid(self, instance):
        return instance.user.id

    def get_email(self, instance):
        return instance.user.email

    def get_contact(self, instance):
        return instance.user.phonenumber

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

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = content_models.FAQ
        fields = ('id', 'title', 'is_active', 'content')

class MentorFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = content_models.MentorFAQ
        fields = ('id', 'title', 'is_active', 'content')

class ReportedQuestionSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    exam = serializers.SerializerMethodField()
    question = serializers.SerializerMethodField()

    class Meta:
        model = content_models.ReportedErrorneousQuestion
        fields = ('id', 'user', 'username', 'contact', 'email', 'full_name', 'exam', 'question', 'created_at', 'query', 'reply', 'is_replied', 'issue_type')

    def get_username(self, instance):
        return instance.user.username
    
    def get_email(self, instance):
        return instance.user.email
    
    def get_contact(self, instance):
        return instance.user.phonenumber

    def get_full_name(self, instance):
        try:
            return instance.user.profile.first_name + ' ' + instance.user.profile.last_name
        except:
            return instance.user.profile.first_name
    
    def get_exam(self, instance):
        try:
            exam = course_serializer.ViewExamSerializer(instance.exam).data
        except:
            exam = None
        return exam

    def get_question(self, instance):
        try:
            question = QuestionSerializer(instance.question).data
        except:
            question = None
        return question

    def create(self, validated_data):
        try:
            question = self._context.get("request").data['question']
        except:
            raise serializers.ValidationError(
                    "Please select your question")
        try:
            exam = self._context.get("request").data['exam']
        except:
            exam = None
        try:
            issue_type = self._context.get("request").data['issue_type']
        except:
            issue_type = None
        try:
            query = self._context.get("request").data['query']
        except:
            query = None
        if question:
            try:
                ques_obj = content_models.Question.objects.get(id=question)
            except:
                raise serializers.ValidationError(
                    "Please select valid question")
        if exam:
            try:
                exam_obj = courses_models.Exam.objects.get(id=exam)
            except:
                raise serializers.ValidationError(
                    "Please select valid exam")
        try:
            reported_obj = content_models.ReportedErrorneousQuestion.objects.filter(user=self.context.get('request').user, exam=exam_obj, question=ques_obj)
        except:
            reported_obj = None
        if not reported_obj:
            query_obj = content_models.ReportedErrorneousQuestion.objects.create(
            user=self.context.get('request').user, exam=exam_obj, question=ques_obj, query=query, issue_type=issue_type)
        else:
            raise serializers.ValidationError(
                    "Already reported")
        return query_obj

class ContactUsSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = content_models.ContactUs
        fields = ('id', 'user', 'username', 'name', 'email', 'contact', 'query', 'created_at')

    def get_username(self, instance):
        if instance.user:
            return instance.user.username
        else:
            return None
    
    def create(self, validated_data):
        name = validated_data.get('name')
        email = validated_data.get('email')
        contact = validated_data.get('contact')
        try:
            query = validated_data.get('query')
        except:
            raise serializers.ValidationError(
                    "Please enter your query")
        if not self.context.get('request').user.is_anonymous:
            query_obj = content_models.ContactUs.objects.create(
                user=self.context.get('request').user, query=query)
        else:
            query_obj = content_models.ContactUs.objects.create(
            query=query)
        if name:
            query_obj.name = name
        if email:
            query_obj.email = email
        if contact:
            query_obj.contact = contact
        query_obj.save()
        return query_obj

class LearnerBlockedBatchSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    userid = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    batch = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerBlockedBatches
        fields = ('id', 'username', 'userid', 'contact', 'email', 'full_name', 'batch', 'created_at', 'updated_at')

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
    
    def get_batch(self, instance):
        try:
            batch = ViewBatchSerializer(instance.batch).data
        except:
            batch = None
        return batch

class MockPaperExamDetailsSerializer(serializers.ModelSerializer):
    exam = serializers.SerializerMethodField()
    chapters = serializers.SerializerMethodField()

    class Meta:
        model = content_models.MockPaperExamDetails
        fields = ('id', 'exam', 'difficulty_level', 'show_time', 'chapters')

    def get_exam(self, instance):
        try:
            exam = course_serializer.ExamSerializer(instance.exam).data
        except:
            exam = None
        return exam

    def get_chapters(self, instance):
        try:
            chapters = course_serializer.ChapterSerializer(instance.chapters, many=True).data
        except:
            chapters = None
        return chapters

class ViewMockPaperExamDetailsSerializer(serializers.ModelSerializer):
    exam = serializers.SerializerMethodField()

    class Meta:
        model = content_models.MockPaperExamDetails
        fields = ('id', 'exam', 'difficulty_level', 'show_time')

    def get_exam(self, instance):
        try:
            exam = course_serializer.ExamSerializer(instance.exam).data
        except:
            exam = None
        return exam

class MockPaperSubjectDetailsSerializer(serializers.ModelSerializer):
    exam = serializers.SerializerMethodField()
    chapters = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()

    class Meta:
        model = content_models.MockPaperSubjectDetails
        fields = ('id', 'exam', 'subject', 'chapters')

    def get_exam(self, instance):
        try:
            exam = course_serializer.ExamSerializer(instance.exam).data
        except:
            exam = None
        return exam
    
    def get_subject(self, instance):
        try:
            subject = course_serializer.SubjectSerializer(instance.subject).data
        except:
            subject = None
        return subject

    def get_chapters(self, instance):
        try:
            chapters = course_serializer.ChapterSerializer(instance.chapters, many=True).data
        except:
            chapters = None
        return chapters

class MockPaperSubjectQuestionTypeDetailsSerializer(serializers.ModelSerializer):
    exam = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()

    class Meta:
        model = content_models.MockPaperSubjectQuestionTypeDetails
        fields = ('id', 'exam', 'subject', 'type_of_question', 'total_questions', 'total_time')

    def get_exam(self, instance):
        try:
            exam = course_serializer.ExamSerializer(instance.exam).data
        except:
            exam = None
        return exam
    
    def get_subject(self, instance):
        try:
            subject = course_serializer.SubjectSerializer(instance.subject).data
        except:
            subject = None
        return subject

class BannerImagesSerializer(serializers.ModelSerializer):
    title = serializers.CharField()
    link = serializers.CharField()
    is_active = serializers.BooleanField()
    image = serializers.ImageField(required=False)

    class Meta:
        model = content_models.BannerSliderImages
        fields = ('id', 'title', 'link', 'is_active', 'image')

    def create(self, validated_data):
        title = validated_data.get('title')
        is_active = validated_data.get('is_active')
        link = validated_data.get('link')
        if validated_data.get('image'):
            book_obj = content_models.BannerSliderImages.objects.create(
                title=title, image=validated_data['image'], link=link, is_active=is_active)
        else:
            book_obj = content_models.BannerSliderImages.objects.create(
                title=title, link=link, is_active=is_active)
        return book_obj

class TemporaryMentorPracticeReplaceQuestionsSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    exam = serializers.SerializerMethodField()
    batch = serializers.SerializerMethodField()
    chapter = serializers.SerializerMethodField()

    class Meta:
        model = content_models.TemporaryMentorPracticeReplaceQuestions
        fields = ('id', 'chapter', 'batch', 'exam', 'exam_end_date_time', 'difficulty_level', 'questions', 'created_at')

    def get_exam(self, instance):
        try:
            exam = course_serializer.ExamSerializer(instance.exam).data
        except:
            exam = None
        return exam

    def get_batch(self, instance):
        try:
            batch = ViewBatchSerializer(instance.batch).data
        except:
            batch = None
        return batch

    def get_questions(self, instance):
        try:
            questions = QuestionSerializer(instance.questions, many=True).data
        except:
            questions = None
        return questions
    
    def get_chapter(self, instance):
        try:
            chapter = course_serializer.ChapterSerializer(instance.chapter).data
        except:
            chapter = None
        return chapter

class TemporaryMentorPaperReplaceQuestionsSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    exam = serializers.SerializerMethodField()
    batch = serializers.SerializerMethodField()
    chapters = serializers.SerializerMethodField()

    class Meta:
        model = content_models.TemporaryMentorActualPaperReplaceQuestions
        fields = ('id', 'chapters', 'batch', 'exam', 'exam_start_date_time', 'exam_end_date_time', 'difficulty_level', 'questions', 'created_at')

    def get_exam(self, instance):
        try:
            exam = course_serializer.ExamSerializer(instance.exam).data
        except:
            exam = None
        return exam

    def get_batch(self, instance):
        try:
            batch = ViewBatchSerializer(instance.batch).data
        except:
            batch = None
        return batch

    def get_questions(self, instance):
        try:
            questions = QuestionSerializer(instance.questions, many=True).data
        except:
            questions = None
        return questions
    
    def get_chapters(self, instance):
        try:
            chapters = course_serializer.ChapterSerializer(instance.chapters, many=True).data
        except:
            chapters = None
        return chapters

class ViewLearnerExamGoalSerializer(serializers.ModelSerializer):
    exam = serializers.SerializerMethodField()
    evaluation_paper_id = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerExamGoals
        fields = ('id', 'user', 'exam', 'is_active', 'chapters', 'count', 'subjects', 'level', 'subjects', 'syllabus', 'last_date', 'created_at', 'title', 'evaluation_done', 'evaluation_paper_id', 'assessment_done', 'assessment_skipped', 'learn_percentage', 'revise_percentage', 'practice_percentage')

    def get_exam(self, instance):
        try:
            exam = course_serializer.ViewExamSerializer(instance.exam).data
        except:
            exam = None
        return exam
    
    def get_evaluation_paper_id(self, instance):
        try:
            self_assess_obj = content_models.SelfAssessExamAnswerPaper.objects.filter(goal=instance).last()
            evaluation_paper_id = self_assess_obj.id
        except:
            evaluation_paper_id = None
        return evaluation_paper_id

    def get_subjects(self, instance):
        try:
            subjects = course_serializer.SubjectSerializer(instance.subjects, many=True).data
        except:
            subjects = None
        return subjects

class CreateLearnerExamGoalSerializer(serializers.ModelSerializer):
    exam = serializers.PrimaryKeyRelatedField(
        queryset=courses_models.Exam.objects.all(), required=False)
    chapters = serializers.PrimaryKeyRelatedField(
        many=True, queryset=courses_models.Chapter.objects.all(), required=False)
    subjects = serializers.PrimaryKeyRelatedField(
        many=True, queryset=courses_models.Subject.objects.all(), required=False)

    class Meta:
        model = content_models.LearnerExamGoals
        fields = ('id', 'user', 'exam', 'count', 'subjects', 'syllabus', 'level', 'chapters', 'last_date', 'created_at', 'title')


    def create(self, validated_data):
        exam = validated_data.get('exam')
        chapters = validated_data.get('chapters')
        subjects = validated_data.get('subjects')
        title = validated_data.get('title')
        syllabus = validated_data.get('syllabus')
        level = validated_data.get('level')
        last_date = validated_data.get('last_date')
        currenttime = timezone.now()
        print ("currentime", currenttime)
        if last_date < currenttime:
            raise serializers.ValidationError(
                    "End date cannot be in past")

        print ("aa", last_date)
        count = 1
        last_exam_goal = content_models.LearnerExamGoals.objects.filter(exam=exam, user=self.context.get('request').user).last()
        print('last_exam_goal',last_exam_goal)
        if last_exam_goal:
            count = last_exam_goal.count + 1
        goal_obj = content_models.LearnerExamGoals.objects.create(
        user=self.context.get('request').user, count=count, exam=exam, title=title, last_date=last_date, syllabus=syllabus, level=level)
        print ("goal_obj", goal_obj)
        if chapters:
            goal_obj.chapters.add(*chapters)
            goal_obj.save()
        if subjects:
            goal_obj.subjects.add(*subjects)
            goal_obj.save()
        return goal_obj

class SelfAssessAnswerPaperSerializer(serializers.ModelSerializer):

    class Meta:
        model = content_models.SelfAssessExamAnswerPaper
        fields = ('id', 'goal', 'questions', 'paper_complete', 'attempted_date', 'start_time', 'total_questions', 'attempted', 'question_unanswered', 'question_answered')
    

class SelfAssessUserAnswerSerializer(serializers.ModelSerializer):
    answer_paper = serializers.SerializerMethodField()
    question = serializers.SerializerMethodField()

    class Meta:
        model = content_models.SelfAssessUserAnswer
        fields = ('id', 'answer_paper','question', 'type_of_answer', 'attempt_order', 'user_mcq_answer', "user_string_answer")

    def get_answer_paper(self, instance):
        return instance.answer_paper.id

    def get_question(self, instance):
        return instance.question.id

class PostSelfAssessAnswerSerializer(serializers.Serializer):
    answer_paper = serializers.PrimaryKeyRelatedField(queryset=content_models.SelfAssessExamAnswerPaper.objects.all())
    question = serializers.PrimaryKeyRelatedField(queryset=courses_models.SelfAssessQuestion.objects.all())
    user_mcq_answer = serializers.PrimaryKeyRelatedField(queryset=courses_models.SelfAssessMcqOptions.objects.all(), many=True, required=False, default=[])
    type_of_answer = serializers.CharField()
    user_string_answer = serializers.CharField(default='')

    def validate(self, attrs):
        answer_paper = content_models.SelfAssessExamAnswerPaper.objects.get(id=attrs['answer_paper'].id)
        if answer_paper.paper_complete:
            raise serializers.ValidationError("Question already answered: id: [{}]".format(attrs['question'].id))
        question_list = map(int, re.sub("[^0-9,]", "", answer_paper.question_order).split(','))
        if attrs['question'].id not in question_list:
            raise serializers.ValidationError('Invalid question id- [{}]'.format(attrs['question'].id))
        return attrs

    def create(self, validated_data):
        question_response_obj, created = content_models.SelfAssessUserAnswer.objects.get_or_create(user=self.context.get('request').user,
            answer_paper=validated_data.get('answer_paper'),
            question=validated_data.get('question'),
            type_of_answer=validated_data.get('type_of_answer')
        )
        # if validated_data.get('user_mcq_answer'):
        #     question_response_obj.user_mcq_answer.clear()
        #     question_response_obj.user_mcq_answer.add(*validated_data.get('user_mcq_answer'))
        #     question_response_obj.status = True

        if validated_data.get('type_of_answer') in ['mcq', 'mcc']:
            if validated_data.get('user_mcq_answer'):
                question_response_obj.user_mcq_answer.clear()
                question_response_obj.user_mcq_answer.add(*validated_data.get('user_mcq_answer'))
                question_response_obj.status = True
        elif validated_data.get('type_of_answer') in ['fillup']:
            # print ("aahhd", validated_data.get('user_string_answer'))
            question_response_obj.user_string_answer = validated_data.get('user_string_answer')
            # print ("questioncontentaaa", validated_data.get('questioncontent'))
            question_response_obj.status = True
              
        question_response_obj.save()
        return validated_data

class CreateInstituteRoomSerializer(serializers.ModelSerializer):
    institute = serializers.PrimaryKeyRelatedField(
        queryset=Institute.objects.all(), required=False)
    grade = serializers.PrimaryKeyRelatedField(
        queryset=models.UserClass.objects.all(), required=False)

    class Meta:
        model = content_models.InstituteClassRoom
        fields = ["institute",
                  "grade",
                  "name"
                  ]

    def create(self, validated_data):
        institute = validated_data.get('institute')
        grade = validated_data.get('grade')
        name = validated_data.get('name')

        try:
            room_obj = content_models.InstituteClassRoom.objects.get(
                institute=institute,
                grade=grade,
                name=name
            )
        except:
            room_obj = None

        if not room_obj:
            room_obj = content_models.InstituteClassRoom.objects.create(
            institute=institute,
            grade=grade,
            name=name
        )
        else:
            raise serializers.ValidationError(
                    "Room already present")

        return room_obj

class ViewInstituteClassRoomSerializer(serializers.ModelSerializer):
    institute_name = serializers.SerializerMethodField()
    grade_name = serializers.SerializerMethodField()
    blocked_students = serializers.SerializerMethodField()
    room_teacher_name = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()
    mentors_count = serializers.SerializerMethodField()

    class Meta:
        model = content_models.InstituteClassRoom
        fields = ('id', 'institute_name', 'grade_name', 'name', 'blocked_students', 'students_count', 'mentors_count', 'room_teacher_name', 'room_teacher', 'created_at')

    def get_institute_name(self, instance):
        try:
            return instance.institute.name
        except:
            return None

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

    def get_mentors_count(self, instance):
        return content_models.Batch.objects.filter(institute_room__id=instance.id).count()

    def get_students_count(self, instance):
        return content_models.UserClassRoom.objects.filter(institute_rooms=instance).count()

    def get_blocked_students(self, instance):
        try:
            userIds = []
            userIds = [user.id for user in instance.blocked_students.all()]
            blocked_students = ShortProfileSerializer(Profile.objects.filter(user__in=userIds), many=True).data
        except:
            blocked_students = []
        return blocked_students

class CreateUserRoomSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=auth_models.User.objects.all(), required=False)
    institute_rooms = serializers.PrimaryKeyRelatedField(
        many=True, queryset=content_models.InstituteClassRoom.objects.all(), required=False)

    class Meta:
        model = content_models.UserClassRoom
        fields = ["user",
                  "institute_rooms"
                  ]

    def create(self, validated_data):
        user = validated_data.get('user')
        institute_rooms = validated_data.get('institute_rooms')
        
        try:
            user_room_obj = content_models.UserClassRoom.objects.get(user=user)
        except:
            user_room_obj = None
        
        if not user_room_obj:
            user_room_obj = content_models.UserClassRoom.objects.create(user=user)
       
        if institute_rooms:
            user_room_obj.institute_rooms.add(*institute_rooms)
        user_room_obj.save()

        return user_room_obj

class ViewUserClassRoomSerializer(serializers.ModelSerializer):
    institute_rooms = ViewInstituteClassRoomSerializer(many=True, required=False)
    full_name = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = content_models.UserClassRoom
        fields = ('id', 'institute_rooms', 'user', 'full_name', 'username', 'created_at')

    def get_full_name(self, instance):
        try:
            return instance.user.profile.first_name + ' ' + instance.user.profile.last_name
        except:
            return instance.user.profile.first_name
    
    def get_username(self, instance):
        return instance.user.username

class PostAnswerGoalAssessmentSerializer(serializers.Serializer):
    answer_paper = serializers.PrimaryKeyRelatedField(queryset=content_models.GoalAssessmentExamAnswerPaper.objects.all())
    question = serializers.PrimaryKeyRelatedField(queryset=content_models.Question.objects.all())
    questioncontent = serializers.PrimaryKeyRelatedField(queryset=content_models.QuestionContent.objects.all())
    type_of_answer = serializers.CharField()
    type_of_paper = serializers.CharField()
    attempt_order = serializers.IntegerField()
    user_mcq_answer = serializers.PrimaryKeyRelatedField(queryset=content_models.McqTestCase.objects.all(), many=True, required=False, default=[])
    # user_mcq_answer = serializers.CharField(default='')
    user_string_answer = serializers.CharField(default='')
    user_boolean_answer = serializers.BooleanField(required=False, default=None)
    user_subjective_answer = serializers.CharField(default='')
    # user_subjective_answer_image = serializers.ImageField(required=False)
    user_subjective_answer_image = Base64ImageField(max_length=None, use_url=True, required=False)
    user_subjective_answer_images = serializers.PrimaryKeyRelatedField(queryset=content_models.UserSubjectiveAnswerImage.objects.all(), many=True, required=False, default=[])
    timespent = serializers.IntegerField(default=0)
    user_fillup_option_answer = serializers.PrimaryKeyRelatedField(queryset=content_models.FillUpWithOption.objects.all(), required=False, default=None)

    def validate(self, attrs):
        answer_paper = content_models.GoalAssessmentExamAnswerPaper.objects.get(id=attrs['answer_paper'].id)
        if answer_paper.paper_complete:
            raise serializers.ValidationError("Question already answered: id: [{}]".format(attrs['question'].id))
        questions = answer_paper.questions.all()
        question_ids = questions.values_list("id", flat=True)
        question_list = map(int, question_ids)
        if attrs['question'].id not in question_list:
            raise serializers.ValidationError('Invalid question id- [{}]'.format(attrs['question'].id))
        return attrs

    def create(self, validated_data):
        question_response_obj, created = content_models.GoalAssessmentUserAnswer.objects.get_or_create(user=self.context.get('request').user,
            answer_paper=validated_data.get('answer_paper'),
            question=validated_data.get('question'),
            type_of_answer=validated_data.get('type_of_answer')
        )
        print ("question_response_obj", question_response_obj, created)
        question_response_obj.attempt_order = validated_data.get('attempt_order')
        if validated_data.get('timespent'):
            question_response_obj.timespent = validated_data.get('timespent')
        if validated_data.get('type_of_answer') in ['mcq', 'mcc', 'assertion']:
            if validated_data.get('user_mcq_answer'):
                # user_mcq_answer_objs = models.McqTestCase.objects.filter(id__in=validated_data.get('user_mcq_answer').split(','))
                question_response_obj.user_mcq_answer.clear()
                # question_response_obj.user_mcq_answer.add(*user_mcq_answer_objs)
                question_response_obj.user_mcq_answer.add(*validated_data.get('user_mcq_answer'))
                question_response_obj.correct_mcq_answer.add(*list(content_models.McqTestCase.objects.filter(questioncontent=validated_data.get('questioncontent'), correct=True)))
        elif validated_data.get('type_of_answer') in ['fillup']:
            question_response_obj.user_string_answer = validated_data.get('user_string_answer')
            # print ("questioncontentaaa", validated_data.get('questioncontent'))
            correct_answer = content_models.FillUpSolution.objects.get(questioncontent=validated_data.get('questioncontent'))
            # print ("correct_answeraaa", correct_answer)
            question_response_obj.correct_fillup_answer = correct_answer
            # print ("correct_string_answeraa", question_response_obj.correct_string_answer)
        elif validated_data.get('type_of_answer') in ['boolean']:
            # if validated_data.get('user_boolean_answer'):
            question_response_obj.user_boolean_answer = validated_data.get('user_boolean_answer')
            # print ("questioncontentaaaboolean", validated_data.get('questioncontent'))
            boolean_obj = content_models.TrueFalseSolution.objects.get(questioncontent=validated_data.get('questioncontent'))
            # print ("boolean_obj", boolean_obj)
            question_response_obj.correct_boolean_answer = boolean_obj
            # print ("correct_boolean_answeraa", question_response_obj.correct_boolean_answer)
        elif validated_data.get('type_of_answer') in ['fillup_option']:
            question_response_obj.user_fillup_option_answer = validated_data.get('user_fillup_option_answer')
            # print ("questioncontentaaaoption", validated_data.get('questioncontent'))
            correct_answer = content_models.FillUpWithOption.objects.get(questioncontent=validated_data.get('questioncontent'), correct=True)
            # print ("correct_answeraaoption", correct_answer)
            question_response_obj.correct_fillup_option_answer = correct_answer
            # print ("correct_string_answeraa", question_response_obj.correct_string_answer)
        elif validated_data.get('type_of_answer') in ['numerical']:
            question_response_obj.user_string_answer = validated_data.get('user_string_answer')
            question_response_obj.correct_string_answer = content_models.StringTestCase.objects.get(questioncontent=validated_data.get('questioncontent'))
        elif validated_data.get('type_of_answer') in ['subjective', 'subjective_medium', 'subjective_short', 'subjective_very_short']:
            question_response_obj.user_subjective_answer = validated_data.get('user_subjective_answer')
            if validated_data.get('user_subjective_answer_image'):
                question_response_obj.user_subjective_answer_image = validated_data.get('user_subjective_answer_image')
            if validated_data.get('user_subjective_answer_images'):
                question_response_obj.user_subjective_answer_images.add(*validated_data.get('user_subjective_answer_images'))
        question_response_obj.save()
        # assessment_paper_obj = content_models.GoalAssessmentExamAnswerPaper.objects.get(id=validated_data.get('answer_paper').id)
        exam_obj = courses_models.Exam.objects.get(id=int(validated_data.get('answer_paper').goal.exam.id))
        print ("examobj", exam_obj)
        try:
            mcq_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='mcq')
        except:
            mcq_linked_obj = None
        # print ("mcq_linked_obj", mcq_linked_obj)
        try:
            mcc_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='mcc')
        except:
            mcc_linked_obj = None
        try:
            fillup_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='fillup')
        except:
            fillup_linked_obj = None
        try:
            numerical_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='numerical')
        except:
            numerical_linked_obj = None
        try:
            boolean_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='boolean')
        except:
            boolean_linked_obj = None
        try:
            fillupoption_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='fillup_option')
        except:
            fillupoption_linked_obj = None
        try:
            assertion_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='assertion')
        except:
            assertion_linked_obj = None
        try:
            subjective_linked_obj = courses_models.QuestionType.objects.get(exam=exam_obj, type_of_question='subjective')
        except:
            subjective_linked_obj = None
        if validated_data.get('type_of_answer') in ['mcq']:
            user_mcq_answer = question_response_obj.user_mcq_answer.all()
            correct_mcq_answer = question_response_obj.correct_mcq_answer.all()
            if set(user_mcq_answer.values_list('id')) == set(correct_mcq_answer.values_list('id')):
                question_response_obj.status = True
                question_response_obj.score = mcq_linked_obj.marks
            else:
                if mcq_linked_obj.negative_marks:
                    question_response_obj.score = mcq_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['mcc']:
            user_mcc_answer = question_response_obj.user_mcq_answer.all()
            correct_mcc_answer = question_response_obj.correct_mcq_answer.all()
            if set(user_mcc_answer.values_list('id')) == set(correct_mcc_answer.values_list('id')):
                question_response_obj.status = True
                question_response_obj.score = mcc_linked_obj.marks
            else:
                if mcc_linked_obj.negative_marks:
                    question_response_obj.score = mcc_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['assertion']:
            user_mcc_answer = question_response_obj.user_mcq_answer.all()
            correct_mcc_answer = question_response_obj.correct_mcq_answer.all()
            if set(user_mcc_answer.values_list('id')) == set(correct_mcc_answer.values_list('id')):
                question_response_obj.status = True
                question_response_obj.score = assertion_linked_obj.marks
            else:
                if assertion_linked_obj.negative_marks:
                    question_response_obj.score = assertion_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['fillup']:
            user_string_answer_flup = str(question_response_obj.user_string_answer.strip())
            correct_string_answer_flup = str(strip_tags(question_response_obj.correct_fillup_answer.text).strip())
            if user_string_answer_flup.lower() == correct_string_answer_flup.lower():
                question_response_obj.status = True
                question_response_obj.score = fillup_linked_obj.marks
            else:
                if fillup_linked_obj.negative_marks:
                    question_response_obj.score = fillup_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['fillup_option']:
            user_fillup_option_answer = question_response_obj.user_fillup_option_answer
            correct_string_answer_flup = question_response_obj.correct_fillup_option_answer
            if user_fillup_option_answer:
                if user_fillup_option_answer.id == correct_string_answer_flup.id:
                    question_response_obj.status = True
                    question_response_obj.score = fillupoption_linked_obj.marks
                else:
                    if fillupoption_linked_obj.negative_marks:
                        question_response_obj.score = fillupoption_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['boolean']:
            user_answer_boolean = str(question_response_obj.user_boolean_answer)
            correct_answer_boolean = str(question_response_obj.correct_boolean_answer.option)
            # print ("user_answer_boolean", user_answer_boolean, correct_answer_boolean)
            if user_answer_boolean == correct_answer_boolean:
                question_response_obj.status = True
                question_response_obj.score = boolean_linked_obj.marks
            else:
                if boolean_linked_obj.negative_marks:
                    question_response_obj.score = boolean_linked_obj.negative_marks
        elif validated_data.get('type_of_answer') in ['numerical']:
            user_string_answer_numerical = str(question_response_obj.user_string_answer.strip())
            correct_string_answer_numerical = str(question_response_obj.correct_string_answer.text)
            if user_string_answer_numerical.lower() == correct_string_answer_numerical.lower():
                question_response_obj.status = True
                question_response_obj.score = numerical_linked_obj.marks
            else:
                if numerical_linked_obj.negative_marks:
                    question_response_obj.score = numerical_linked_obj.negative_marks
        question_response_obj.save()
        return validated_data

class CardViewGoalAssessmentExamAnswerPaperSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    goal = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()
    # chapters = serializers.SerializerMethodField()

    class Meta:
        model = content_models.GoalAssessmentExamAnswerPaper
        fields = ('id', 'username', 'goal', 'subjects', 'chapters', 'show_time', 'questions', 'marks', 'score', 'total_time', 'paper_type', 'paper_count', 'time_taken', 'submitted', 'remaining_time')

    def get_username(self, instance):
        return instance.user.username
    
    def get_goal(self, instance):
        try:
            goal = ViewLearnerExamGoalSerializer(instance.goal).data
        except:
            goal = None
        return goal

    def get_subjects(self, instance):
        try:
            subjects = course_serializer.SubjectSerializer(instance.subjects, many=True).data
        except:
            subjects = None
        return subjects
    
    # def get_chapters(self, instance):
    #     try:
    #         chapters = course_serializer.ChapterSerializer(instance.chapters, many=True).data
    #     except:
    #         chapters = None
    #     return chapters

class GoalAssessmentExamAnswerPaperSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    userid = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    questions = serializers.SerializerMethodField()
    goal = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()
    chapters = serializers.SerializerMethodField()

    class Meta:
        model = content_models.GoalAssessmentExamAnswerPaper
        fields = ('id', 'username', 'userid', 'email', 'full_name', 'chapters', 'goal', 'subjects', 'show_time', 'questions', 'marks', 'score', 'total_time', 'paper_type', 'paper_count', 'time_taken', 'submitted', 'remaining_time')

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
    
    def get_goal(self, instance):
        try:
            goal = ViewLearnerExamGoalSerializer(instance.goal).data
        except:
            goal = None
        return goal

    def get_questions(self, instance):
        try:
            questions = QuestionSerializer(instance.questions, many=True).data
        except:
            questions = None
        return questions
    
    def get_subjects(self, instance):
        try:
            subjects = course_serializer.SubjectSerializer(instance.subjects.all().order_by('id'), many=True).data
        except:
            subjects = None
        return subjects

    def get_chapters(self, instance):
        try:
            chapters = course_serializer.ChapterSerializer(instance.chapters.all().order_by('id'), many=True).data
        except:
            chapters = None
        return chapters

# class GoalAssessmentExamAnswerPaperSerializer(serializers.ModelSerializer):

#     class Meta:
#         model = content_models.GoalAssessmentExamAnswerPaper
#         fields = ('id', 'percentage','time_taken', 'paper_complete', 'attempted_date', 'start_time', 'total_time', 'total_questions', 'attempted', 'correct', 'unchecked', 'incorrect')

class GoalAssessmentUserAnswerSerializer(serializers.ModelSerializer):
    answer_paper = serializers.SerializerMethodField()
    question = serializers.SerializerMethodField()
    type_of_paper = serializers.SerializerMethodField()
    user_subjective_answer_image = serializers.SerializerMethodField()
    user_subjective_answer_images = serializers.SerializerMethodField()

    class Meta:
        model = content_models.GoalAssessmentUserAnswer
        fields = ('answer_paper','question', 'user_subjective_answer_image', 'user_subjective_answer_images', 'user_fillup_option_answer', 'type_of_answer', 'type_of_paper', 'attempt_order', 'user_mcq_answer', 'user_boolean_answer', 'user_string_answer', 'user_subjective_answer','timespent')

    def get_answer_paper(self, instance):
        return instance.answer_paper.id

    def get_question(self, instance):
        return instance.question.id

    def get_type_of_paper(self, instance):
        return 'assessment'

    def get_user_subjective_answer_image(self, instance):
        return instance.user_subjective_answer_image.url if instance.user_subjective_answer_image else None
    
    def get_user_subjective_answer_images(self, instance):
        return UserSubjectiveAnswerImageSerializer(instance.user_subjective_answer_images, many=True).data

class ViewLearnerExamGoalPathSerializer(serializers.ModelSerializer):
    goal = serializers.SerializerMethodField()
    paper = serializers.SerializerMethodField()

    class Meta:
        model = content_models.LearnerExamGoalPath
        fields = ('id', 'goal', 'counter', 'previous_path_id', 'created_at', 'next_path_id', 'frozen_date', 'done_with_assessment', 'freeze', 'paper', 'learn_percentage', 'revise_percentage', 'practice_percentage')

    def get_goal(self, instance):
        try:
            goal = ViewLearnerExamGoalSerializer(instance.goal).data
        except:
            goal = None
        return goal

    def get_paper(self, instance):
        try:
            if instance.paper:
                paper = CardViewLearnerPaperSerializer(instance.paper).data
            else:
                paper = None
        except:
            paper = None
        return paper

class CreateLearnerExamGoalPathSerializer(serializers.ModelSerializer):
    goal = serializers.PrimaryKeyRelatedField(
        queryset=content_models.LearnerExamGoals.objects.all(), required=False)

    class Meta:
        model = content_models.LearnerExamGoalPath
        fields = ('id', 'goal', 'counter', 'previous_path_id', 'next_path_id', 'frozen_date', 'done_with_assessment', 'freeze', 'created_at')


    def create(self, validated_data):
        goal = validated_data.get('goal')
        previous_path = content_models.LearnerExamGoalPath.objects.filter(goal=goal).order_by('counter').last()
        path_obj = content_models.LearnerExamGoalPath.objects.create(
            goal=goal)
        if previous_path:
            counter = previous_path.counter + 1
            path_obj.counter=counter
            path_obj.previous_path_id=previous_path.id
            path_obj.save()
            previous_path.next_path_id = path_obj.id
            previous_path.frozen_date = path_obj.created_at
            previous_path.freeze = True
            previous_path.save()
        else:
            counter = 1
            path_obj.counter=counter
            path_obj.save()
        return path_obj

class ViewGoalPathLearnChapterHistorySerializer(serializers.ModelSerializer):
    # path = serializers.SerializerMethodField()
    chapter = serializers.SerializerMethodField()

    class Meta:
        model = content_models.GoalPathLearnChapterHistory
        fields = ('id', 'path', 'chapter', 'percentage', 'created_at', 'is_done')

    # def get_path(self, instance):
    #     try:
    #         path = ViewLearnerExamGoalPathSerializer(instance.path).data
    #     except:
    #         path = None
    #     return path

    def get_chapter(self, instance):
        try:
            chapter = course_serializer.ViewChapterSerializer(instance.chapter).data
        except:
            chapter = None
        return chapter

class ViewGoalPathLearnChapterHintHistorySerializer(serializers.ModelSerializer):
    # learn_chapter = serializers.SerializerMethodField()
    chapter_hint = serializers.SerializerMethodField()

    class Meta:
        model = content_models.GoalPathLearnChapterHintHistory
        fields = ('id', 'learn_chapter', 'chapter_hint', 'order', 'last_check_date', 'checked', 'created_at')

    # def get_learn_chapter(self, instance):
    #     try:
    #         learn_chapter = ViewGoalPathLearnChapterHistorySerializer(instance.learn_chapter).data
    #     except:
    #         learn_chapter = None
    #     return learn_chapter
    
    def get_chapter_hint(self, instance):
        try:
            chapter_hint = course_serializer.ChapterHintSerializer(instance.chapter_hint).data
        except:
            chapter_hint = None
        return chapter_hint

class ViewGoalPathReviseChapterHistorySerializer(serializers.ModelSerializer):
    # path = serializers.SerializerMethodField()
    chapter = serializers.SerializerMethodField()

    class Meta:
        model = content_models.GoalPathReviseChapterHistory
        fields = ('id', 'path', 'chapter', 'percentage', 'created_at', 'is_done')

    # def get_path(self, instance):
    #     try:
    #         path = ViewLearnerExamGoalPathSerializer(instance.path).data
    #     except:
    #         path = None
    #     return path

    def get_chapter(self, instance):
        try:
            chapter = course_serializer.ViewChapterSerializer(instance.chapter).data
        except:
            chapter = None
        return chapter

class ViewGoalPathReviseChapterHintHistorySerializer(serializers.ModelSerializer):
    # revise_chapter = serializers.SerializerMethodField()
    chapter_hint = serializers.SerializerMethodField()

    class Meta:
        model = content_models.GoalPathReviseChapterHintHistory
        fields = ('id', 'revise_chapter', 'chapter_hint', 'order', 'last_check_date', 'checked', 'created_at')

    # def get_revise_chapter(self, instance):
    #     try:
    #         revise_chapter = ViewGoalPathReviseChapterHistorySerializer(instance.revise_chapter).data
    #     except:
    #         revise_chapter = None
    #     return revise_chapter
    
    def get_chapter_hint(self, instance):
        try:
            chapter_hint = course_serializer.ChapterHintSerializer(instance.chapter_hint).data
        except:
            chapter_hint = None
        return chapter_hint

class StudentInstituteChangeInvitationSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    userid = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    inviting_institute_room = serializers.SerializerMethodField()

    class Meta:
        model = content_models.StudentInstituteChangeInvitation
        fields = ('id', 'username', 'userid', 'email', 'full_name', 'inviting_institute_room', 'created_at', 'updated_at')

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
    
    def get_inviting_institute_room(self, instance):
        try:
            inviting_institute_room = ViewInstituteClassRoomSerializer(instance.inviting_institute_room).data
        except:
            inviting_institute_room = None
        return inviting_institute_room

class MentorExamChapterSerializer(serializers.ModelSerializer):
    mentor_exam = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    chapter = serializers.SerializerMethodField()

    class Meta:
        model = content_models.MentorExamChapters
        fields = ('id', 'mentor_exam', 'subject', 'chapter', 'created_at', 'total_bookmarks')

    
    def get_mentor_exam(self, instance):
        try:
            mentor_exam = course_serializer.MentorExamSerializer(instance.mentor_exam).data
        except:
            mentor_exam = None
        return mentor_exam

    def get_subject(self, instance):
        try:
            subject = course_serializer.SubjectSerializer(instance.subject).data
        except:
            subject = None
        return subject
    
    def get_chapter(self, instance):
        try:
            chapter = course_serializer.ChapterSerializer(instance.chapter).data
        except:
            chapter = None
        return chapter

class MentorExamSubjectSerializer(serializers.ModelSerializer):
    mentor_exam = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()

    class Meta:
        model = content_models.MentorExamSubjects
        fields = ('id', 'mentor_exam', 'subject', 'chapters', 'created_at', 'total_bookmarks')

    
    def get_mentor_exam(self, instance):
        try:
            mentor_exam = course_serializer.MentorExamSerializer(instance.mentor_exam).data
        except:
            mentor_exam = None
        return mentor_exam

    def get_subject(self, instance):
        try:
            subject = course_serializer.SubjectSerializer(instance.subject).data
        except:
            subject = None
        return subject

class MentorBookmarksSerializer(serializers.ModelSerializer):
    question = serializers.SerializerMethodField()
    mentor_exam = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    chapter = serializers.SerializerMethodField()

    class Meta:
        model = content_models.MentorBookmarks
        fields = ('id', 'mentor_exam', 'subject', 'chapter', 'question', 'created_at')
    
    def get_mentor_exam(self, instance):
        try:
            mentor_exam = course_serializer.MentorExamSerializer(instance.mentor_exam).data
        except:
            mentor_exam = None
        return mentor_exam

    def get_question(self, instance):
        try:
            question = QuestionSerializer(instance.question).data
        except:
            question = None
        return question
    
    def get_subject(self, instance):
        try:
            subject = course_serializer.SubjectSerializer(instance.subject).data
        except:
            subject = None
        return subject

    def get_chapter(self, instance):
        try:
            chapter = course_serializer.ChapterSerializer(instance.chapter).data
        except:
            chapter = None
        return chapter