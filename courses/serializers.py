from django.db.models.fields import DateField, DateTimeField
from rest_framework import serializers

from notification.models import NotificationType, Notifications
from . import models
from core import models as core_models
from django.db.models import Q
from content import models as content_models

class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Topic
        fields = ["id", "title", "description"]

    def create(self, validated_data):
        try:
            title = validated_data.get('title')
            description = validated_data.get('description')
        except:
             raise serializers.ValidationError(
                    "Please enter ftag title")
        try:
            checkFtag = models.Topic.objects.filter(title=title).last()
        except:
            checkFtag = None
        if checkFtag:
            raise serializers.ValidationError(
                    "Ftag already exists")
        ftagObj = models.Topic.objects.create(title=title, description=description)
        return ftagObj

class BloomLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BloomLevel
        fields = ["id", "title"]

class ChapterHintSerializer(serializers.ModelSerializer):
    bloom_level = serializers.PrimaryKeyRelatedField(
        queryset=models.BloomLevel.objects.all(), many=True, required=False, default=[])

    class Meta:
        model = models.ChapterHints
        fields = ["id", "title", "show", "bloom_level", "importance", "difficulty", "learning_time", "practice_time", "revision_importance", "show"]

    def create(self, validated_data):
        try:
            chapter = self._context.get("request").data['chapter']
        except:
            chapter = None
        try:
            title = validated_data.get('title')
        except:
            title = None
        difficulty = validated_data.get('difficulty', None)
        importance = validated_data.get('importance', None)
        learning_time = validated_data.get('learning_time', None)
        practice_time = validated_data.get('practice_time', None)
        revision_importance = validated_data.get('revision_importance', None)
        show = validated_data.get('show', None)
        try:
            chapter_obj = models.Chapter.objects.get(id=chapter)
        except:
            raise serializers.ValidationError(
                    "Please select valid chapter")
        
        hint_obj = models.ChapterHints.objects.create(title=title,  difficulty=difficulty, importance=importance, learning_time=learning_time, practice_time=practice_time, revision_importance=revision_importance, show=show)
        if validated_data.get('bloom_level'):
            hint_obj.bloom_level.add(*validated_data.get('bloom_level'))
        hint_obj.save()
        chapter_obj.hints.add(hint_obj)
        chapter_obj.save()
        return hint_obj

class ChapterHintConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ChapterHintConcepts
        fields = ["id", "title"]

    def create(self, validated_data):
        try:
            hint = self._context.get("request").data['hint']
        except:
            hint = None
        try:
            title = validated_data.get('title')
        except:
            title = None
        try:
            hint_obj = models.ChapterHints.objects.get(id=hint)
        except:
            raise serializers.ValidationError(
                    "Please select valid chapter")
        
        concept_obj = models.ChapterHintConcepts.objects.create(title=title)
        hint_obj.concepts.add(concept_obj)
        hint_obj.save()
        return concept_obj

class DetailViewChapterHintSerializer(serializers.ModelSerializer):
    concepts = ChapterHintConceptSerializer(many=True, required=False)
    class Meta:
        model = models.ChapterHints
        fields = ["id", "title", "show", "bloom_level", "concepts", "difficulty", "importance", "learning_time", "practice_time", "revision_importance"]

    def create(self, validated_data):
        try:
            chapter = self._context.get("request").data['chapter']
        except:
            chapter = None
        try:
            title = validated_data.get('title')
        except:
            title = None
        try:
            chapter_obj = models.Chapter.objects.get(id=chapter)
        except:
            raise serializers.ValidationError(
                    "Please select valid chapter")
        
        hint_obj = models.ChapterHints.objects.create(title=title)
        chapter_obj.hints.add(hint_obj)
        chapter_obj.save()
        return hint_obj

class ChapterVideoSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.ChapterVideo
        exclude = ["created_at", "updated_at", "chapter"]

class ChapterSerializer(serializers.ModelSerializer):
    topics = TopicSerializer(many=True, required=False)
    subject = serializers.SerializerMethodField()
    hints = ChapterHintSerializer(many=True, required=False)
    videos_available = serializers.SerializerMethodField()

    class Meta:
        model = models.Chapter
        fields = ('id', 'title', 'description', 'subject', 'topics', 'hints', 'order', 'show', 'videos_available')

    def get_subject(self, obj):
        return SubjectSerializer(obj.subject).data
    
    def get_videos_available(self, obj):
        return obj.videos.count() != 0

class AdminViewChapterSerializer(serializers.ModelSerializer):
    subject = serializers.SerializerMethodField()
    hints = ChapterHintSerializer(many=True, required=False)

    class Meta:
        model = models.Chapter
        fields = ('id', 'title', 'description', 'subject', 'hints', 'order', 'show')

    def get_subject(self, obj):
        return SubjectSerializer(obj.subject).data

class ViewChapterSerializer(serializers.ModelSerializer):
    subject = serializers.SerializerMethodField()

    class Meta:
        model = models.Chapter
        fields = ('id', 'title', 'description', 'subject', 'order', 'show')

    def get_subject(self, obj):
        return SubjectSerializer(obj.subject).data

class CreateChapterSerializer(serializers.ModelSerializer):
    topics = TopicSerializer(many=True, required=False)
    hints = ChapterHintSerializer(many=True, required=False)
    videos = ChapterVideoSerializer(many=True, required=False)

    class Meta:
        model = models.Chapter
        fields = ('id', 'title', 'description', 'subject', 'topics', 'hints', 'order', 'show', "videos")
    
    
class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Subject
        fields = ('id', 'title', 'order', 'show')

    def create(self, validated_data):
        try:
            title = validated_data.get('title')
            order = validated_data.get('order')
            show = validated_data.get('show')
        except:
             raise serializers.ValidationError(
                    "Please enter subject title")
        subject_obj = models.Subject.objects.create(title=title, order=order, show=show)
        return subject_obj

class ExamCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ExamCategory
        fields = ('id', 'title', 'order')

    def create(self, validated_data):
        try:
            title = validated_data.get('title')
        except:
             raise serializers.ValidationError(
                    "Please enter category title")
        category_obj = models.ExamCategory.objects.create(title=title)
        return category_obj

class ExamLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ExamLevel
        fields = ('id', 'label',)

    def create(self, validated_data):
        try:
            label = validated_data.get('label')
        except:
             raise serializers.ValidationError(
                    "Please enter level title")
        level_obj = models.ExamLevel.objects.create(label=label)
        return level_obj

class DomainSerializer(serializers.ModelSerializer):
    title = serializers.CharField()
    short_description = serializers.CharField()
    description = serializers.CharField()
    is_active = serializers.BooleanField()
    show_home = serializers.BooleanField()
    image = serializers.ImageField(required=False)
    exam_category = serializers.PrimaryKeyRelatedField(
        queryset=models.ExamCategory.objects.all(), many=True, required=False, default=[])

    class Meta:
        model = models.ExamDomain
        fields = ('id', 'exam_category', 'show_home', 'title', 'order', 'short_description',
                  'description', 'is_active', 'image', 'exams', 'consider_node_order')

    def create(self, validated_data):
        title = validated_data.get('title')
        description = validated_data.get('description')
        is_active = validated_data.get('is_active')
        show_home = validated_data.get('show_home')
        short_description = validated_data.get('short_description')
        order = validated_data.get('order')
        consider_node_order = validated_data.get('consider_node_order')
        if validated_data.get('image'):
            domain_obj = models.ExamDomain.objects.create(
                title=title, description=description, order=order, consider_node_order=consider_node_order, show_home=show_home, image=validated_data['image'], short_description=short_description, is_active=is_active)
        else:
            domain_obj = models.ExamDomain.objects.create(
                title=title, description=description, order=order, consider_node_order=consider_node_order, show_home=show_home, short_description=short_description, is_active=is_active)
        if validated_data.get('exam_category'):
            domain_obj.exam_category.add(*validated_data.get('exam_category'))
        return domain_obj

    def update(self, instance, validated_data):
        title = validated_data.get('title')
        description = validated_data.get('description')
        is_active = validated_data.get('is_active')
        show_home = validated_data.get('show_home')
        short_description = validated_data.get('short_description')
        order = validated_data.get('order')
        consider_node_order = validated_data.get('consider_node_order')
        instance.is_active = is_active
        instance.show_home = show_home
        instance.consider_node_order = consider_node_order
        if order:
            instance.order = order
        if title:
            instance.title = title
        if description:
            instance.description = description
        if short_description:
            instance.short_description = short_description
        if validated_data.get('exam_category'):
            instance.exam_category.add(*validated_data.get('exam_category'))
        if validated_data.get('image'):
            instance.image = validated_data['image']
        instance.save()
        return instance

class ViewDomainSerializer(serializers.ModelSerializer):
    title = serializers.CharField()
    short_description = serializers.CharField()
    description = serializers.CharField()
    is_active = serializers.BooleanField()
    show_home = serializers.BooleanField()
    image = serializers.ImageField(required=False)
    exam_category = serializers.SerializerMethodField()

    class Meta:
        model = models.ExamDomain
        fields = ('id', 'exam_category', 'title', 'show_home', 'order', 'short_description',
                  'description', 'is_active', 'image', 'exams', 'consider_node_order')

    def get_exam_category(self, instance):
        try:
            exam_category = ExamCategorySerializer(instance.exam_category, many=True).data
        except:
            exam_category = None
        return exam_category

class ViewExamSerializer(serializers.ModelSerializer):
    title = serializers.CharField()
    short_description = serializers.CharField()
    description = serializers.CharField()
    user_guidelines = serializers.CharField()
    excellent_low = serializers.IntegerField(required=False)
    excellent_high = serializers.IntegerField(required=False)
    average_low = serializers.IntegerField(required=False)
    average_high = serializers.IntegerField(required=False)
    poor = serializers.IntegerField(required=False)
    is_active = serializers.BooleanField()
    image = serializers.ImageField(required=False)
    subjects = serializers.SerializerMethodField()
    userclass = serializers.PrimaryKeyRelatedField(
        queryset=core_models.UserClass.objects.all(), many=True, required=False, default=[])
    userboard = serializers.PrimaryKeyRelatedField(
        queryset=core_models.UserBoard.objects.all(), many=True, required=False, default=[])

    class Meta:
        model = models.Exam
        fields = ('id', 'subjects', 'title', 'short_description', 'allow_goal',
                  'description', 'is_active', 'image', 'user_guidelines', 'subjects', 'userclass', 'userboard', 'excellent_low', 'excellent_high', 'average_low', 'average_high', 'poor', 'level', 'update_date')

    def get_subjects(self, instance):
        try:
            subjects = SubjectSerializer(instance.subjects, many=True).data
        except:
            subjects = None
        return subjects

class ExamSerializer(serializers.ModelSerializer):
    title = serializers.CharField()
    short_description = serializers.CharField()
    description = serializers.CharField()
    user_guidelines = serializers.CharField()
    excellent_low = serializers.IntegerField(required=False)
    excellent_high = serializers.IntegerField(required=False)
    average_low = serializers.IntegerField(required=False)
    average_high = serializers.IntegerField(required=False)
    poor = serializers.IntegerField(required=False)
    is_active = serializers.BooleanField()
    image = serializers.ImageField(required=False)
    subjects = serializers.PrimaryKeyRelatedField(
        queryset=models.Subject.objects.all(), many=True, required=False, default=[])
    userclass = serializers.PrimaryKeyRelatedField(
        queryset=core_models.UserClass.objects.all(), many=True, required=False, default=[])
    userboard = serializers.PrimaryKeyRelatedField(
        queryset=core_models.UserBoard.objects.all(), many=True, required=False, default=[])

    class Meta:
        model = models.Exam
        fields = ('id', 'subjects', 'title', 'short_description', 'allow_goal',
                  'description', 'is_active', 'image', 'user_guidelines', 'subjects', 'userclass', 'userboard', 'excellent_low', 'excellent_high', 'average_low', 'average_high', 'poor', 'level', 'update_date')

    def create(self, validated_data):
        title = validated_data.get('title')
        description = validated_data.get('description')
        is_active = validated_data.get('is_active')
        short_description = validated_data.get('short_description')
        user_guidelines = validated_data.get('user_guidelines')
        level = validated_data.get('level')
        if validated_data.get('image'):
            course_obj = models.Exam.objects.create(
                title=title, description=description, image=validated_data['image'], short_description=short_description, is_active=is_active, user_guidelines=user_guidelines, level=level)
        else:
            course_obj = models.Exam.objects.create(
                title=title, description=description, short_description=short_description, is_active=is_active, user_guidelines=user_guidelines, level=level)
        if validated_data.get('subjects'):
            course_obj.subjects.add(*validated_data.get('subjects'))
        if validated_data.get('userclass'):
            course_obj.userclass.add(*validated_data.get('userclass'))
        if validated_data.get('userboard'):
            course_obj.userboard.add(*validated_data.get('userboard'))

        return course_obj
    
    def update(self, instance, validated_data):
        title = validated_data.get('title')
        description = validated_data.get('description')
        is_active = validated_data.get('is_active')
        allow_goal = validated_data.get('allow_goal')
        short_description = validated_data.get('short_description')
        user_guidelines = validated_data.get('user_guidelines')
        level = validated_data.get('level')
        update_date = validated_data.get('update_date')
        excellent_low = validated_data.get('excellent_low')
        excellent_high = validated_data.get('excellent_high')
        average_low = validated_data.get('average_low')
        average_high = validated_data.get('average_high')
        poor = validated_data.get('poor')
        instance.is_active = is_active
        instance.allow_goal = allow_goal
        if title:
            instance.title = title
        if excellent_low:
            instance.excellent_low = excellent_low
        if excellent_high:
            instance.excellent_high = excellent_high
        if average_low:
            instance.average_low = average_low
        if average_high:
            instance.average_high = average_high
        if poor:
            instance.poor = poor
        if description:
            instance.description = description
        if short_description:
            instance.short_description = short_description
        if user_guidelines:
            instance.user_guidelines = user_guidelines
        if level:
            instance.level = level
        if update_date:
            instance.update_date = update_date
        instance.save()
        return instance

class AverageMarksSerializer(serializers.ModelSerializer):
    exam = serializers.SerializerMethodField()

    class Meta:
        model = models.ExamAverageTimePerQuestion
        fields = ('id', 'exam', 'time')

    def get_exam(self, instance):
        try:
            exams = ViewExamSerializer(instance.exam).data
        except:
            exams = None
        return exams

    def create(self, validated_data):
        try:
            exam = self._context.get("request").data['exam']
        except:
            exam = None
        time = validated_data.get('time', None)
        try:
            exam_obj = models.Exam.objects.get(id=exam)
        except:
            raise serializers.ValidationError(
                    "Please select valid exam")
        
        avg_obj = models.ExamAverageTimePerQuestion.objects.create(exam=exam_obj, time=time)
        return avg_obj

    def update(self, instance, validated_data):
        time = validated_data.get('time')
        if time:
            instance.time = time
        instance.save()
        return instance

class ExamQuestionTypeSerializer(serializers.ModelSerializer):
    exam = serializers.SerializerMethodField()

    class Meta:
        model = models.QuestionType
        fields = ('id', 'exam', 'marks', 'negative_marks', 'is_active', 'type_of_question')

    def get_exam(self, instance):
        try:
            exams = ViewExamSerializer(instance.exam).data
        except:
            exams = None
        return exams

    def create(self, validated_data):
        try:
            exam = self._context.get("request").data['exam']
        except:
            exam = None
        
        try:
            exam_obj = models.Exam.objects.get(id=exam)
        except:
            raise serializers.ValidationError(
                    "Please select valid exam")
        
        marks = validated_data.get('marks', 0)
        negative_marks = validated_data.get('negative_marks', 0)
        is_active = validated_data.get('is_active', None)
        type_of_question = validated_data.get('type_of_question', None)
        
        if models.QuestionType.objects.filter(exam=exam_obj, type_of_question=type_of_question).exists():
            raise serializers.ValidationError("Type already linked")
        
        type_obj = models.QuestionType.objects.create(
            exam=exam_obj, marks=marks, negative_marks = negative_marks, 
            is_active = is_active, type_of_question = type_of_question
        )
        return type_obj

    def update(self, instance, validated_data):
        marks = validated_data.get('marks')
        negative_marks = validated_data.get('negative_marks')
        is_active = validated_data.get('is_active')
        type_of_question = validated_data.get('type_of_question')
        # if marks:
        instance.marks = marks
        # if negative_marks:
        instance.negative_marks = negative_marks
        # if is_active:
        instance.is_active = is_active
        if type_of_question:
            instance.type_of_question = type_of_question
        instance.save()
        return instance


class ExamMakePathQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ExamMakePathQuestions
        fields = ('id', 'title', 'is_active', 'content', 'exam', 'order')

class JourneyNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.JourneyNode
        fields = ('id', 'title', 'node')

class SuccessiveNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PathNodes
        fields = ('id', 'domain', 'text', 'question_text', 'order', 'journey_nodes', 'linked_exam')

class DomainNodeSerializer(serializers.ModelSerializer):
    domain = serializers.SerializerMethodField()
    successive_nodes = SuccessiveNodeSerializer(many=True, required=False)
    journey_nodes = serializers.SerializerMethodField()
    linked_exam = serializers.SerializerMethodField()

    class Meta:
        model = models.PathNodes
        fields = ('id', 'domain', 'text', 'question_text', 'journey_nodes', 'successive_nodes', 'order', 'linked_exam')

    def get_domain(self, instance):
        try:
            domain = DomainSerializer(instance.domain).data
        except:
            domain = None
        return domain
    
    def get_journey_nodes(self, instance):
        try:
            journey_nodes = JourneyNodeSerializer(instance.journey_nodes, many=True).data
        except:
            journey_nodes = None
        return journey_nodes
    
    def get_linked_exam(self, instance):
        if instance.linked_exam:
            try:
                linked_exam = ExamSerializer(instance.linked_exam).data
            except:
                linked_exam = None
        else:
            linked_exam = None
        return linked_exam

    def create(self, validated_data):
        try:
            text = validated_data.get('text')
        except:
             raise serializers.ValidationError(
                    "Please enter node text")
        try:
            question_text = validated_data.get('question_text')
        except:
            question_text = None

        try:
            order = validated_data.get('order')
        except:
            order = 1
        
        node_obj = models.PathNodes.objects.create(text=text, question_text=question_text, order=order)
        try:
            domain = self._context.get("request").data['domain']
        except:
            domain = None
        if domain:
            domain_obj = models.ExamDomain.objects.get(id=domain)
            node_obj.domain = domain_obj
            node_obj.save()
        try:
            current_node = self._context.get("request").data['current_node']
        except:
            current_node = None
        if current_node:
            currentnode_obj = models.PathNodes.objects.get(id=current_node)
            journey_node_obj = models.JourneyNode.objects.get_or_create(title=currentnode_obj.text, node=currentnode_obj.id)
            for pathnode in currentnode_obj.journey_nodes.all():
                pathnode_obj = models.JourneyNode.objects.get(id=pathnode.id)
                node_obj.journey_nodes.add(pathnode_obj.id)
                node_obj.save()
            node_obj.journey_nodes.add(journey_node_obj[0].id)
            node_obj.save()
        
        return node_obj

class LearnerExamSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    userid = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    # full_name = serializers.SerializerMethodField()
    exam = serializers.SerializerMethodField()

    class Meta:
        model = models.LearnerExams
        fields = ('id', 'username', 'userid', 'email', 'exam', 'created_at', 'updated_at', 'is_active')

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
            exams = ViewExamSerializer(instance.exam).data
        except:
            exams = None
        return exams

    def create(self, validated_data):
        user = self.context.get('request').user
        exam = self.context.get("request").data.get('exam', None)
        if not exam:
            raise serializers.ValidationError("Please select valid exam")

        try:
            exam_obj = models.Exam.objects.get(id=exam)
        except:
            raise serializers.ValidationError("Please select valid exam")
        learner_history_obj, _ = content_models.LearnerHistory.objects.get_or_create(user=user)
        try:
            learner_obj = models.LearnerExams.objects.get(user=user, exam=exam_obj)
        except:
            learner_obj = None
        learner_obj, _ = models.LearnerExams.objects.get_or_create(
            exam=exam_obj, user=user, defaults={"is_active": True})
    
        if not exam_obj.is_active:
            learner_obj.is_active=False
            learner_obj.save()
            raise serializers.ValidationError(
                    "Oops! Exam has been deactivated by admin")
        
        currentdate= DateTimeField()
        learner_obj.is_active=True
        learner_obj.updated_at = currentdate
        learner_obj.save()
        learner_history_obj.learner_exam.add(learner_obj)
        learner_history_obj.save()
     
        return learner_obj

class DomainAnnouncementSerializer(serializers.ModelSerializer):
    linked_exam = serializers.SerializerMethodField()
    domain = serializers.SerializerMethodField()

    class Meta:
        model = models.DomainAnnouncement
        fields = ('id', 'linked_exam', 'text', 'order', 'domain', 'is_active', 'last_date')

    def get_linked_exam(self, instance):
        try:
            linked_exam = ViewExamSerializer(instance.linked_exam).data
        except:
            linked_exam = None
        return linked_exam
    
    def get_domain(self, instance):
        try:
            domain = DomainSerializer(instance.domain).data
        except:
            domain = None
        return domain

    def create(self, validated_data):
        try:
            linked_exam = self._context.get("request").data['linked_exam']
        except:
            linked_exam = None
        try:
            exam_obj = models.Exam.objects.get(id=linked_exam)
        except:
            raise serializers.ValidationError(
                    "Please select valid exam")
        try:
            domain = self._context.get("request").data['domain']
        except:
            domain = None
        try:
            domain_obj = models.ExamDomain.objects.get(id=domain)
        except:
            raise serializers.ValidationError(
                    "Please select valid domain")
        try:
            text = validated_data.get('text')
        except:
            text = 0
        try:
            is_active = validated_data.get('is_active')
        except:
            is_active = None
        try:
            last_date = validated_data.get('last_date')
        except:
            last_date = None
        order = validated_data.get('order')
        type_obj = models.DomainAnnouncement.objects.create(linked_exam=exam_obj, domain=domain_obj)
        type_obj.text = text
        type_obj.is_active = is_active
        type_obj.last_date = last_date
        type_obj.order = order
        type_obj.save()

        return type_obj

class EditDomainAnnouncementSerializer(serializers.ModelSerializer):
    linked_exam = serializers.PrimaryKeyRelatedField(
        queryset=models.Exam.objects.all(), required=False)
    domain = serializers.SerializerMethodField()

    class Meta:
        model = models.DomainAnnouncement
        fields = ('id', 'linked_exam', 'text', 'order', 'domain', 'is_active', 'last_date')
    
    def get_domain(self, instance):
        try:
            domain = DomainSerializer(instance.domain).data
        except:
            domain = None
        return domain

    def update(self, instance, validated_data):
        text = validated_data.get('text')
        linked_exam = validated_data.get('linked_exam')
        last_date = validated_data.get('last_date')
        order = validated_data.get('order')
        if linked_exam:
            instance.linked_exam = linked_exam
        is_active = validated_data.get('is_active')
        if text:
            instance.text = text
        if last_date:
            instance.last_date = last_date
        # if is_active:
        instance.is_active = is_active
        instance.order = order
        instance.save()
        return instance

class ExamBookSerializer(serializers.ModelSerializer):
    title = serializers.CharField()
    about = serializers.CharField()
    author = serializers.CharField()
    publication = serializers.CharField()
    amazon_link = serializers.CharField()
    flipkart_link = serializers.CharField()
    is_active = serializers.BooleanField()
    image = serializers.ImageField(required=False)
    file = serializers.FileField(required=False)
    exam = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()

    class Meta:
        model = models.ExamSuggestedBooks
        fields = ('id', 'title', 'author', 'about', 'publication', 'amazon_link', 
                  'flipkart_link', 'is_active', 'image', 'exam', 'subject', 'file')

    def get_exam(self, instance):
        try:
            exam = ViewExamSerializer(instance.exam).data
        except:
            exams = None
        return exam
    
    def get_subject(self, instance):
        try:
            subject = SubjectSerializer(instance.subject, many=True).data
        except:
            subject = None
        return subject

class CreateExamBookSerializer(serializers.ModelSerializer):
    title = serializers.CharField()
    about = serializers.CharField()
    author = serializers.CharField()
    publication = serializers.CharField()
    amazon_link = serializers.CharField()
    flipkart_link = serializers.CharField()
    file = serializers.FileField(required=False)
    is_active = serializers.BooleanField()
    image = serializers.ImageField(required=False)
    exam = serializers.PrimaryKeyRelatedField(
        queryset=models.Exam.objects.all(), required=False)
    subject = serializers.SerializerMethodField()
    # subject = serializers.PrimaryKeyRelatedField(
    #     queryset=models.Subject.objects.all(), many=True, required=False, default=[])

    class Meta:
        model = models.ExamSuggestedBooks
        fields = ('id', 'title', 'author', 'about', 'publication', 'amazon_link', 
                  'flipkart_link', 'is_active', 'image', 'exam', 'subject', 'file')

    def get_subject(self, instance):
        try:
            subject = SubjectSerializer(instance.subject, many=True).data
        except:
            subject = None
        return subject

    def create(self, validated_data):
        title = validated_data.get('title')
        author = validated_data.get('author')
        is_active = validated_data.get('is_active')
        about = validated_data.get('about')
        publication = validated_data.get('publication')
        amazon_link = validated_data.get('amazon_link')
        flipkart_link = validated_data.get('flipkart_link')
        exam = validated_data.get('exam')
        subject = self._context.get("request").data['subject']
        if not subject == 'undefined':
            allsubjects = subject.split(',')
        else:
            allsubjects = None
        if validated_data.get('image'):
            book_obj = models.ExamSuggestedBooks.objects.create(
                title=title, author=author, image=validated_data['image'], about=about, is_active=is_active,
                publication=publication, amazon_link=amazon_link, flipkart_link=flipkart_link, exam=exam)
        else:
            book_obj = models.ExamSuggestedBooks.objects.create(
                title=title, author=author, about=about, is_active=is_active,
                publication=publication, amazon_link=amazon_link, flipkart_link=flipkart_link, exam=exam)
        if allsubjects:
            for subject in allsubjects:
                subjectobj = models.Subject.objects.get(id=int(subject))
                book_obj.subject.add(subjectobj)
                book_obj.save()
        if validated_data.get('file'):
            book_obj.file = validated_data['file']
            book_obj.save()
        return book_obj

class ExamPreviousYearsPaperSerializer(serializers.ModelSerializer):
    title = serializers.CharField()
    is_active = serializers.BooleanField()
    file = serializers.FileField(required=False)
    exam = serializers.SerializerMethodField()

    class Meta:
        model = models.ExamPreviousYearsPapers
        fields = ('id', 'title', 'is_active', 'file', 'exam')

    def get_exam(self, instance):
        try:
            exam = ViewExamSerializer(instance.exam).data
        except:
            exams = None
        return exam

class CreateExamPreviousYearsPaperSerializer(serializers.ModelSerializer):
    title = serializers.CharField()
    is_active = serializers.BooleanField()
    file = serializers.FileField(required=False)
    exam = serializers.PrimaryKeyRelatedField(
        queryset=models.Exam.objects.all(), required=False)

    class Meta:
        model = models.ExamPreviousYearsPapers
        fields = ('id', 'title', 'is_active', 'file', 'exam')

    def create(self, validated_data):
        title = validated_data.get('title')
        is_active = validated_data.get('is_active')
        exam = validated_data.get('exam')
        if validated_data.get('file'):
            pdf_obj = models.ExamPreviousYearsPapers.objects.create(
                title=title, file=validated_data['file'], is_active=is_active, exam=exam)
        else:
            raise serializers.ValidationError(
                    "Please upload file")
        return pdf_obj

class MentorExamSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    userid = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    exam = serializers.SerializerMethodField()

    class Meta:
        model = models.MentorExams
        fields = ('id', 'username', 'userid', 'email', 'full_name', 'exam', 'created_at', 'updated_at', 'is_active')

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
    
    def get_exam(self, instance):
        try:
            exams = ViewExamSerializer(instance.exam).data
        except:
            exams = None
        return exams

    def create(self, validated_data):
        user = self.context.get(
                'request').user
        try:
            exam = self._context.get("request").data['exam']
        except:
            exam = None

        try:
            exam_obj = models.Exam.objects.get(id=exam)
        except:
            raise serializers.ValidationError(
                    "Please select valid exam")
   
        try:
            mentorexam_obj = models.MentorExams.objects.get(user=user, exam=exam_obj)
        except:
            mentorexam_obj = None
        
        if not mentorexam_obj:
            mentorexam_obj = models.MentorExams.objects.create(user=user, exam=exam_obj, is_active=True)
        else:
            currentdate= DateTimeField()
            mentorexam_obj.updated_at = currentdate
            mentorexam_obj.save()
     
        return mentorexam_obj

class ExamTotalStudentsSerializer(serializers.ModelSerializer):
    exam = serializers.SerializerMethodField()

    class Meta:
        model = models.ExamTotalStudents
        fields = ('id', 'exam', 'total_students')

    def get_exam(self, instance):
        try:
            exams = ViewExamSerializer(instance.exam).data
        except:
            exams = None
        return exams

    def create(self, validated_data):
        try:
            exam = self._context.get("request").data['exam']
        except:
            exam = None
        try:
            total_students = validated_data.get('total_students')
        except:
            total_students = None
        try:
            exam_obj = models.Exam.objects.get(id=exam)
        except:
            raise serializers.ValidationError(
                    "Please select valid exam")
        try:
            exam_student_tmp_obj = models.ExamTotalStudents.objects.get(exam=exam)
        except:
            exam_student_tmp_obj = None
        if exam_student_tmp_obj:
            raise serializers.ValidationError(
                    "Count already linked")
        total_obj = models.ExamTotalStudents.objects.create(exam=exam_obj, total_students=total_students)
        return total_obj

    def update(self, instance, validated_data):
        total_students = validated_data.get('total_students')
        if total_students:
            instance.total_students = total_students
        instance.save()
        return instance

class ExamStudentNotifictionSerializer(serializers.ModelSerializer):
    exam = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    userid = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()

    class Meta:
        model = models.ExamStudentNotification
        fields = ('id', 'username', 'userid', 'email', 'full_name', 'contact', 'exam', 'user', 'created_at', 'updated_at',)

    def get_exam(self, instance):
        try:
            exams = ViewExamSerializer(instance.exam).data
        except:
            exams = None
        return exams
    
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

    def get_contact(self, instance):
        return instance.user.phonenumber

    def create(self, validated_data):
        user = self.context.get(
                'request').user
        try:
            exam = self._context.get("request").data['exam']
        except:
            exam = None
        try:
            exam_obj = models.Exam.objects.get(id=exam)
        except:
            raise serializers.ValidationError(
                    "Please select valid exam")
        try:
            exam_student_alert_obj = models.ExamStudentNotification.objects.get(exam=exam, user=user)
        except:
            exam_student_alert_obj = None
        if exam_student_alert_obj:
            raise serializers.ValidationError(
                    "Request already sent")
        alert_obj = models.ExamStudentNotification.objects.create(exam=exam_obj, user=user)
        notification_type = NotificationType.objects.get(name="admin")
        notification_text  = "Successfully subscribed to get notifications for exam: " + exam_obj.title
        Notifications.objects.create(user=user, exam=exam_obj, notification=notification_text, subject="Exam Notification Subscription", type=notification_type)
        return alert_obj

class SelfAssesQuestionSerializer(serializers.ModelSerializer):
    text = serializers.CharField()

    class Meta:
        model = models.SelfAssessQuestion
        fields = ["id", "is_active", "text", "type_of_question", "order", "is_numeric"]

    def create(self, validated_data):
        text = validated_data.get('text')
        type_of_question = validated_data.get('type_of_question')
        is_active = validated_data.get('is_active')
        is_numeric = validated_data.get('is_numeric')
        ques_obj = models.SelfAssessQuestion.objects.create(
            is_active=is_active, text=text, is_numeric=is_numeric, type_of_question=type_of_question)
        return ques_obj

class ViewSelfAssesQuestionSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.SelfAssessQuestion
        fields = ["id", "is_active", "text", "type_of_question", "order", "is_numeric"]

class SelfAssesExamQuestionSerializer(serializers.ModelSerializer):
    exam = serializers.PrimaryKeyRelatedField(
        queryset=models.Exam.objects.all(), required=False)
    question = serializers.PrimaryKeyRelatedField(
        queryset=models.SelfAssessQuestion.objects.all(), required=False)

    class Meta:
        model = models.SelfAssessExamQuestions
        fields = ["id", "exam", "question", "order", "is_compulsory"]

    def create(self, validated_data):
        exam = validated_data.get('exam')
        question = validated_data.get('question')
        order = validated_data.get('order')
        is_compulsory = validated_data.get('is_compulsory')
        ques_obj = models.SelfAssessExamQuestions.objects.create(
            exam=exam, question=question, order=order, is_compulsory=is_compulsory)
        return ques_obj

class ViewSelfAssesExamQuestionSerializer(serializers.ModelSerializer):
    question = ViewSelfAssesQuestionSerializer()

    class Meta:
        model = models.SelfAssessExamQuestions
        fields = ["id", "exam", "question", "order", "is_compulsory"]

class SelfAssesQuestionBankSerializer(serializers.ModelSerializer):
    text = serializers.CharField()

    class Meta:
        model = models.SelfAssessQuestionBank
        fields = ["id", "text", "type_of_question"]

    def create(self, validated_data):
        text = validated_data.get('text')
        type_of_question = validated_data.get('type_of_question')
        ques_obj = models.SelfAssessQuestionBank.objects.create(
            text=text, type_of_question=type_of_question)
        return ques_obj

class ViewSelfAssesQuestionBankSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.SelfAssessQuestionBank
        fields = ["id", "text", "type_of_question"]

class MCQTestCaseSerializer(serializers.ModelSerializer):
    questioncontent = serializers.SerializerMethodField()

    class Meta:
        model = models.SelfAssessMcqOptions
        fields = ["id",
                  "text",
                  "questioncontent"
                  ]

    def get_questioncontent(self, obj):
        return SelfAssesQuestionSerializer(obj.questioncontent).data

class CreateMCQTestCaseSerializer(serializers.ModelSerializer):
    text = serializers.CharField()
    # questioncontent = serializers.SerializerMethodField()
    questioncontent = serializers.PrimaryKeyRelatedField(
        queryset=models.SelfAssessQuestion.objects.all(), required=False)
    

    class Meta:
        model = models.SelfAssessMcqOptions
        fields = ["text",
                  "questioncontent"
                  ]
    
    def create(self, validated_data):
        text = validated_data.get('text')

        questioncontent = validated_data.get('questioncontent')

        mcq_obj = models.SelfAssessMcqOptions.objects.create(
            text=text)

        if questioncontent:
            mcq_obj.questioncontent = questioncontent

        mcq_obj.save()
        return mcq_obj

class EditMCQSerializer(serializers.ModelSerializer):
    text = serializers.CharField(allow_blank=True)

    class Meta:
        model = models.SelfAssessMcqOptions
        fields = ["id", "text"]

    def update(self, instance, validated_data):
        text = validated_data.get('text')
        if text == "":
            models.SelfAssessMcqOptions.objects.filter(id=instance.id).delete()
            return ''
        if text:
            instance.text = text
        instance.save()
        return instance

