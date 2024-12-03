
import uuid
from authentication.models import User
from ckeditor_uploader.fields import RichTextUploadingField
from core import models as core_models
from django.conf import settings
from django.db import models
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _


# Types Of Question
question_type = (
    ('mcq', 'Single Correct Choice'),
    ('mcc', 'Multiple Correct Choice'),
    ('fillup', 'Fill In The Blanks'),
    ('subjective', 'Subjective type'),
    ('numerical', 'Numerical'),
    ('assertion', 'Assertion'),
    ('boolean', 'True False'),
    ('fillup_option', 'Fill With Option'),
)

selfassess_question_type = (
    ('mcq', 'Single Correct Choice'),
    ('mcc', 'Multiple Correct Choice'),
    ('fillup', 'Fill In The Blanks'),
)

# bloom_level = (
#     ('memory', 'Memory Based'),
#     ('conceptual', 'Conceptual'),
#     ('application', 'Application'),
# )

#############################
# Helper Functions
#############################

def image_upload_to(instance, filename):
    uid = str(uuid.uuid4())
    ext = filename.split(".")[-1].lower()
    return "course-images/{}/{}.{}".format(instance.pk, uid, ext)

def course_image_upload_to(instance, filename):
    uid = str(uuid.uuid4())
    ext = filename.split(".")[-1].lower()
    return "course-images/{}/{}.{}".format(instance.pk, uid, ext)

def f():
    d = uuid.uuid4()
    str = d.hex
    return str[0:5]

#############################
# Create your models here.
#############################

class Topic(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return (self.title)

class Subject(core_models.TimestampedModel):
    title = models.CharField(max_length=200)
    order = models.IntegerField(default=1)
    show = models.BooleanField(default=True)

    def __str__(self):
        return ("{}".format(self.title))


class ExamCategory(core_models.TimestampedModel):
    title = models.CharField(max_length=50)
    order = models.IntegerField(default=1)

    def __str__(self):
        return ("{}".format(self.title))

class ExamLevel(core_models.TimestampedModel):
    label = models.CharField(max_length=50)

    def __str__(self):
        return ("{}".format(self.label))

class Exam(core_models.TimestampedModel):
    subjects = models.ManyToManyField(Subject, blank = True)
    userclass = models.ManyToManyField(core_models.UserClass, blank = True)
    userboard = models.ManyToManyField(core_models.UserBoard, blank = True)
    level = models.ForeignKey(ExamLevel, on_delete = models.CASCADE, blank = True, null=True)
    is_active = models.BooleanField(default=True)
    allow_goal = models.BooleanField(default=False)
    title = models.CharField(max_length=200)
    short_description = models.CharField(max_length=100, blank=True, null=True)
    description = RichTextUploadingField(_('description'))
    image = models.ImageField(upload_to=course_image_upload_to, blank=True)
    user_guidelines = RichTextUploadingField(_('user_guidelines'), blank=True, null=True)
    update_date = models.DateField(null=True, blank=True)
    excellent_low = models.IntegerField(blank = True, null=True, default=0)
    excellent_high = models.IntegerField(blank = True, null=True, default=0)
    average_low = models.IntegerField(blank = True, null=True, default=0)
    average_high = models.IntegerField(blank = True, null=True, default=0)
    poor = models.IntegerField(blank = True, null=True, default=0)

    def __str__(self):
        return ("{}".format(self.title))


class SelfAssessQuestion(core_models.TimestampedModel):
    is_active = models.BooleanField(default=False)
    text = RichTextUploadingField(_('text'))
    ideal_time =  models.IntegerField(blank=False,null=False,default=0)
    type_of_question = models.CharField(max_length=50, choices = selfassess_question_type, blank=True, null=True)
    order = models.IntegerField(default=1)
    is_numeric = models.BooleanField(default=False)

    def __str__(self):
        return "Text: {}  ID: {}".format(self.text, self.id)
    
class SelfAssessQuestionBank(core_models.TimestampedModel):
    text = RichTextUploadingField(_('text'))
    type_of_question = models.CharField(max_length=50, choices = selfassess_question_type, blank=True, null=True)

    def __str__(self):
        return "Text: {}  ID: {}".format(self.text, self.id)

class SelfAssessMcqOptions(core_models.TimestampedModel):
    questioncontent = models.ForeignKey(SelfAssessQuestion, on_delete = models.CASCADE, blank=True, null=True)
    text = RichTextUploadingField(_('text'), blank=True, null=True)

    def get_field_value(self):
        return {"test_case_type": "mcqoptions",
                "text": self.text}

    def __str__(self):
        return u'MCQ Testcase | Text: {0}'.format( \
             self.text)

class SelfAssessExamQuestions(models.Model):
    exam = models.ForeignKey(Exam, on_delete = models.CASCADE, related_name="exam")
    question = models.ForeignKey(SelfAssessQuestion, on_delete = models.CASCADE, related_name="question")
    order = models.IntegerField(default=1)
    is_compulsory = models.BooleanField(default=True)

    def __str__(self):
        return "Exam: {}  Question: {}".format(self.exam, self.question)

class BloomLevel(models.Model):
    title = models.CharField(max_length=100)

    def __str__(self):
        return (self.title)

class ChapterHintConcepts(models.Model):
    title = models.CharField(max_length=100)

    def __str__(self):
        return (self.title)

class ChapterHints(models.Model):
    title = models.CharField(max_length=100)
    concepts = models.ManyToManyField(ChapterHintConcepts, blank = True)
    bloom_level = models.ManyToManyField(BloomLevel, blank = True)
    difficulty = models.IntegerField(default=0)
    importance = models.IntegerField(default=0)
    learning_time =  models.IntegerField(blank=False,null=False,default=0)
    practice_time =  models.IntegerField(blank=False,null=False,default=0)
    revision_importance = models.IntegerField(default=0)
    show = models.BooleanField(default=True)

    def __str__(self):
        return (self.title)

class Chapter(core_models.TimestampedModel):
    subject = models.ForeignKey(Subject, on_delete = models.CASCADE, related_name="chapters")
    topics = models.ManyToManyField(Topic, blank = True, related_name="chapters")
    hints = models.ManyToManyField(ChapterHints, blank = True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    order = models.IntegerField(default=1)
    show = models.BooleanField(default=True)

    def __str__(self):
        return  ("{}".format(self.title))
    
    @property
    def videos(self):
        return ChapterVideo.objects.select_related("chapter").filter(chapter=self, is_active=True)

class QuestionType(core_models.TimestampedModel):
    exam = models.ForeignKey(Exam, on_delete = models.CASCADE)
    is_active = models.BooleanField(default=True)
    type_of_question = models.CharField(max_length=50, choices = question_type, blank=True, null=True)
    marks = models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)
    negative_marks = models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)

    def __str__(self):
        return "{}".format(self.type_of_question)

class ExamAverageTimePerQuestion(core_models.TimestampedModel):
    exam = models.ForeignKey(Exam, on_delete = models.CASCADE)
    time = models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)

    def __str__(self):
        return "{}-{}".format(self.exam.title, self.time)

class ExamMakePathQuestions(core_models.TimestampedModel):
    exam = models.ForeignKey(Exam, on_delete = models.CASCADE)
    is_active = models.BooleanField(default=True)
    title = models.CharField(max_length=150)
    content = RichTextUploadingField(_('content'), blank=True, null=True)
    order = models.IntegerField(default=1)

    def __str__(self):
        return ("{}".format(self.title))


class ExamDomain(core_models.TimestampedModel):
    exam_category = models.ManyToManyField(ExamCategory, blank = True)
    exams = models.ManyToManyField(Exam, blank=True)
    is_active = models.BooleanField(default=False)
    show_home = models.BooleanField(default=False)
    title = models.CharField(max_length=50)
    short_description = models.CharField(max_length=100, blank=True, null=True)
    description = RichTextUploadingField(_('description'))
    image = models.ImageField(upload_to=course_image_upload_to, blank=True)
    order = models.IntegerField(default=1)
    consider_node_order = models.BooleanField(default=False)

    def __str__(self):
        return ("{}".format(self.title))

class JourneyNode(models.Model):
    title = models.CharField(max_length=100, blank = True, null=True)
    node = models.IntegerField(blank = True, null=True)

    def __str__(self):
        return ("{}".format(self.title))

class PathNodes(core_models.TimestampedModel):
    domain = models.ForeignKey(ExamDomain, on_delete = models.CASCADE, blank = True, null=True)
    text = models.CharField(max_length=100)
    question_text = models.CharField(max_length=100, blank=True, null=True)
    successive_nodes = models.ManyToManyField('self', symmetrical=False, blank=True)
    journey_nodes = models.ManyToManyField(JourneyNode, blank=True)
    linked_exam = models.ForeignKey(Exam, on_delete = models.CASCADE, blank=True, null=True)
    order = models.IntegerField(default=1)

    def __str__(self):
        return "{}-{}".format(self.text, self.domain)

class LearnerExams(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    exam = models.ForeignKey(Exam, on_delete = models.CASCADE, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "{}-{}".format(self.user.username, self.exam.title)

class MentorExams(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    exam = models.ForeignKey(Exam, on_delete = models.CASCADE, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    batches = models.ManyToManyField('content.Batch', blank = True)

    def __str__(self):
        return "{}-{}".format(self.user.username, self.exam.title)


class DomainAnnouncement(core_models.TimestampedModel):
    domain = models.ForeignKey(ExamDomain, on_delete = models.CASCADE, blank = True, null=True)
    text = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    linked_exam = models.ForeignKey(Exam, on_delete = models.CASCADE, blank=True, null=True)
    last_date = models.DateField(null=True, blank=True)
    order = models.IntegerField(default=100)

    def __str__(self):
        return "{}-{}".format(self.text, self.domain)

class ExamSuggestedBooks(core_models.TimestampedModel):
    exam = models.ForeignKey(Exam, on_delete = models.CASCADE, blank=True, null=True)
    subject = models.ManyToManyField(Subject, blank=True)
    image = models.ImageField(upload_to=course_image_upload_to, blank=True)
    file = models.FileField(upload_to=course_image_upload_to, blank=True)
    title = models.CharField(max_length=200, blank = True, null=True)
    about = RichTextUploadingField(_('about'), blank=True, null=True)
    author = models.CharField(max_length=100, blank = True, null=True)
    publication = models.CharField(max_length=200, blank = True, null=True)
    amazon_link = models.CharField(max_length=700, blank = True, null=True)
    flipkart_link = models.CharField(max_length=700, blank = True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "{}-{}".format(self.about, self.exam.title)

class ExamPreviousYearsPapers(core_models.TimestampedModel):
    exam = models.ForeignKey(Exam, on_delete = models.CASCADE, blank=True, null=True)
    file = models.FileField(upload_to=course_image_upload_to, blank=True)
    title = models.CharField(max_length=200, blank = True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "{}-{}".format(self.exam.title)

class ExamTotalStudents(core_models.TimestampedModel):
    exam = models.OneToOneField(Exam, on_delete = models.CASCADE)
    total_students = models.IntegerField(blank = True, null=True, default=0)

    def __str__(self):
        return "{}-{}".format(self.exam.title, self.total_students)

class ExamStudentNotification(core_models.TimestampedModel):
    exam = models.ForeignKey(Exam, on_delete = models.CASCADE, blank=True, null=True)
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)

    def __str__(self):
        return "{}-{}".format(self.exam.title, self.user)


class ChapterVideo(core_models.TimestampedModel):
    """Generic model to store rating on Chapter metacontent
    like: Videos/Blogs etc

    Args:
        core_models (_type_): _description_
    """
    chapter = models.ForeignKey(Chapter, null=False, on_delete=models.CASCADE)
    url = models.URLField(null=False)
    description = models.TextField(null=True, blank=True)
    avg_rating = models.FloatField(default = settings.USER_RATING_SCALE)
    total_ratings = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs) -> None:
        if self.avg_rating > settings.USER_RATING_SCALE:
            raise ValidationError(f"Avg rating can not be greater than {settings.USER_RATING_SCALE}")
        return super().save(*args, **kwargs)
    class Meta:
        # a chapter can not have multiple objects with active/inactive url
        unique_together = (
            ("chapter", "url", "is_active")
        )


class UserRatingOnChapter(core_models.TimestampedModel):
    chapter_video = models.ForeignKey(ChapterVideo, null=False, on_delete=models.CASCADE)
    user = models.ForeignKey(User, null=False, on_delete=models.DO_NOTHING)
    rating = models.FloatField(null=False, help_text="rating given by user")
    

    def save(self, *args, **kwargs) -> None:
        if self.rating > settings.USER_RATING_SCALE:
            raise ValidationError(f"User rating can not be greater than {settings.USER_RATING_SCALE}")

        return super().save(*args, **kwargs)

    class Meta:
        # since one user can rate on a video at max once
        unique_together = (
            ("chapter_video", "user")
        )
    
    # TODO: Update this to a post_save signal
    def update_avg_rating(self):
        chapter_video = self.chapter_video
        new_avg_rating = ((chapter_video.avg_rating * chapter_video.total_ratings)  + self.rating )/(chapter_video.avg_rating + 1)
        chapter_video.avg_rating = new_avg_rating
        chapter_video.total_ratings += 1
        chapter_video.save()