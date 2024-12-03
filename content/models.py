from statistics import mode
import time
import pytz
import datetime
import uuid
from random import sample
from courses import models as courses_models
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from core import models as core_models
from ckeditor.fields import RichTextField
from ckeditor_uploader.fields import RichTextUploadingField
from authentication.models import User
from django.utils.translation import gettext_lazy as _

from profiles.models import Institute


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
    ('comprehension', 'Comprehension'),
)

paper_type = (
    ('practice', 'Practice'),
    ('paper', 'Paper'),
)

syllabus = (
    ('full', 'Full'),
    ('partial', 'Partial')
)

proficiency_level = (
    ('beginner', 'Beginner'),
    ('intermediate', 'Intermediate'),
    ('advanced', 'Advanced')
)

def user_subjective_answer_image(instance, filename):
    return "%s/%s" % ('user_subjective_answer_image', filename)

def banner_image_upload_to(instance, filename):
    uid = str(uuid.uuid4())
    ext = filename.split(".")[-1].lower()
    return "banner-images/{}/{}.{}".format(instance.pk, uid, ext)

#############################
# Helper Functions
#############################


#############################
# Create your models here.
#############################


SEASSON_CHOICES=(
	
('1' ,'2021-2022'),
('2' ,'2022-2023'),
('3' ,'2023-2024'),
('4' ,'2024-2025'),
)

class BranchSchool(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE, blank = True,null = True,related_name="branchuser")
    school=models.ForeignKey(Institute,on_delete=models.CASCADE, blank = True,null = True,related_name="branchschool")
    branch_name=models.CharField(default="",max_length=100)

    def __str__(self):
        return self.branch_name

class SchoolSeasson(models.Model):
    schoolbranch=models.ForeignKey(BranchSchool,on_delete=models.CASCADE ,blank = True,null = True)
    seassion_name=models.CharField(choices=SEASSON_CHOICES,max_length=50,default='1')
    session_name = models.ForeignKey(core_models.UserSeasson,on_delete=models.CASCADE ,blank=True, null=True)

    def __str__(self):
        return self.seassion_name

class QuestionTag(core_models.TimestampedModel):
    text = models.CharField(max_length=24)
    def __str__(self):
        return u'text: {0}'.format(self.text)

class QuestionLanguage(core_models.TimestampedModel):
    text = models.CharField(max_length=24)
    short_text = models.CharField(max_length=4, blank=True, null=True)
    def __str__(self):
        return u'text: {0}: short text: {1}'.format(self.text, self.short_text)

class Comprehensions(core_models.TimestampedModel):
    html_txt = RichTextUploadingField(_('html_txt'))
    linked_questions = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return ("{}".format(self.html_txt))

class QuestionContent(core_models.TimestampedModel):
    text = RichTextUploadingField(_('text'))
    language = models.ForeignKey(QuestionLanguage, on_delete=models.CASCADE)
    hint = models.TextField(blank=True, null=True)
    comprehension = models.ForeignKey(Comprehensions, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return u'text: {0}'.format(self.text)

class Question(core_models.TimestampedModel):
    tags = models.ManyToManyField(QuestionTag, blank = True)
    linked_topics = models.ManyToManyField(courses_models.Topic, blank = True)
    difficulty = models.IntegerField(default=0)
    is_active = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    contents = models.ManyToManyField(QuestionContent, blank = True)
    type_of_question = models.CharField(max_length=24, choices = question_type)
    question_identifier = models.CharField(max_length=100, blank=True, null=True)
    ideal_time =  models.IntegerField(blank=False,null=False,default=0)
    languages = models.ManyToManyField(QuestionLanguage, blank = True, null=True)
    assigned_code = models.CharField(max_length=1000, blank=True, null=True)
    question_id = models.CharField(max_length=1000, blank=True, null=True)
    author_code = models.CharField(max_length=1000, blank=True, null=True)
    tag_count =  models.IntegerField(blank=True,null=True)
    update_code =  models.CharField(max_length=500, blank=True, null=True)
    forwarded = models.BooleanField(default=False)
    status = models.CharField(max_length=1000, blank=True, null=True)
    perfetly = models.CharField(max_length=1000, blank=True, null=True)
    formatting_needed = models.CharField(max_length=1000, blank=True, null=True)
    waste_data = models.CharField(max_length=1000, blank=True, null=True)
    solution_missing = models.BooleanField(default=False)
    edit_after_password = models.BooleanField(default=False)
    primary_check = models.CharField(max_length=1000, blank=True, null=True)
    error_image = models.BooleanField(default=False)
    faculty_check = models.CharField(max_length=1000, blank=True, null=True)
    bloom_level = models.CharField(max_length=1000, blank=True, null=True)
    sub_type = models.CharField(max_length=1000, blank=True, null=True)
    total_language =  models.IntegerField(blank=True,null=True)
    question_info_id = models.CharField(max_length=1000, blank=True, null=True)
    skill = models.CharField(max_length=1000, blank=True, null=True)
    associated_questions = models.TextField(blank=True, null=True)

    def __str__(self):
        return "Type: {}  ID: {}".format(self.type_of_question, self.id)
    
    class Meta:
        index_together = [
            ["type_of_question", "difficulty"]
        ]

class McqTestCase(core_models.TimestampedModel):
    questioncontent = models.ForeignKey(QuestionContent, on_delete = models.CASCADE, blank=True, null=True)
    text = RichTextUploadingField(_('text'), blank=True, null=True)
    correct = models.BooleanField(default=False)

    def get_field_value(self):
        return {"test_case_type": "mcqtestcase",
                "text": self.text, "correct": self.correct}

    def __str__(self):
        return u'MCQ Testcase | Text: {0} | Correct: {1}'.format( \
             self.text, self.correct)

class StringTestCase(core_models.TimestampedModel):
    questioncontent = models.ForeignKey(QuestionContent, on_delete = models.CASCADE, blank=True, null=True)
    text = RichTextUploadingField(_('text'))

    def get_field_value(self):
        return {"test_case_type": "stringtestcase", "text": self.text}

    def __str__(self):
        return u'String Testcase | text: {0}'.format(self.text)

class FillUpSolution(core_models.TimestampedModel):
    questioncontent = models.ForeignKey(QuestionContent, on_delete = models.CASCADE, blank=True, null=True)
    text = models.CharField(max_length=100, blank=True, null=True)

    def get_field_value(self):
        return {"text": self.text}

    def __str__(self):
        return u'Fill Up Solution | text: {0}'.format(self.text)

class FillUpWithOption(core_models.TimestampedModel):
    questioncontent = models.ForeignKey(QuestionContent, on_delete = models.CASCADE, blank=True, null=True)
    text = RichTextUploadingField(_('text'), blank=True, null=True)
    correct = models.BooleanField(default=False)

    def get_field_value(self):
        return {"test_case_type": "fillup_option",
                "text": self.text, "correct": self.correct}

    def __str__(self):
        return u'Fill Up With Option | Text: {0} | Correct: {1}'.format( \
             self.text, self.correct)

class TrueFalseSolution(core_models.TimestampedModel):
    questioncontent = models.ForeignKey(QuestionContent, on_delete = models.CASCADE, blank=True, null=True)
    option = models.BooleanField(default=True)

    def get_field_value(self):
        return {"option": self.option}

    def __str__(self):
        return u'True/ False Solution | option: {0}'.format(self.option)

class Solution(core_models.TimestampedModel):
    questioncontent = models.ForeignKey(QuestionContent, on_delete = models.CASCADE, blank=True, null=True)
    text = RichTextUploadingField(_('text'))

    def get_field_value(self):
        return {"text": self.text}

    def __str__(self):
        return u'Question Solution | text: {0}'.format(self.text)

class LearnerBookmarks(core_models.TimestampedModel):
    learner_exam = models.ForeignKey(courses_models.LearnerExams, on_delete = models.CASCADE, blank=True, null=True)
    subject = models.ForeignKey(courses_models.Subject, on_delete = models.CASCADE, blank=True, null=True)
    chapter = models.ForeignKey(courses_models.Chapter, on_delete = models.CASCADE, blank=True, null=True)
    question = models.ForeignKey(Question, on_delete = models.CASCADE, blank=True, null=True)

    def __unicode__(self):
        return "{}-{}".format(self.learner_exam.exam.title, self.question)

class LearnerExamChapters(core_models.TimestampedModel):
    learner_exam = models.ForeignKey(courses_models.LearnerExams, on_delete = models.CASCADE, blank=True, null=True)
    subject = models.ForeignKey(courses_models.Subject, on_delete = models.CASCADE, blank=True, null=True)
    chapter = models.ForeignKey(courses_models.Chapter, on_delete = models.CASCADE, blank=True, null=True)
    score =  models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)
    total_marks =  models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)
    percentage = models.IntegerField(blank=False,null=False,default=0)
    total_time = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    time_taken = models.IntegerField(blank=False,null=False,default=0)
    total_questions =  models.IntegerField(blank=False,null=False,default=0)
    attempted = models.IntegerField(blank=False,null=False,default=0)
    correct = models.IntegerField(blank=False,null=False,default=0)
    unchecked = models.IntegerField(blank=False,null=False,default=0)
    incorrect = models.IntegerField(blank=False,null=False,default=0)
    total_bookmarks = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}-{} Attempted: {} Correct: {}".format(self.learner_exam.exam.title, self.chapter.title, self.attempted, self.correct)

class LearnerExamSubjects(core_models.TimestampedModel):
    learner_exam = models.ForeignKey(courses_models.LearnerExams, on_delete = models.CASCADE, blank=True, null=True)
    subject = models.ForeignKey(courses_models.Subject, on_delete = models.CASCADE, blank=True, null=True)
    chapters = models.ManyToManyField(LearnerExamChapters, blank=True, null=True)
    score =  models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)
    total_marks = models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)
    percentage = models.IntegerField(blank=False,null=False,default=0)
    total_time = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    time_taken = models.IntegerField(blank=False,null=False,default=0)
    total_questions =  models.IntegerField(blank=False,null=False,default=0)
    attempted = models.IntegerField(blank=False,null=False,default=0)
    correct = models.IntegerField(blank=False,null=False,default=0)
    unchecked = models.IntegerField(blank=False,null=False,default=0)
    incorrect = models.IntegerField(blank=False,null=False,default=0)
    total_bookmarks = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}-{} Attempted: {} Correct: {}".format(self.learner_exam, self.subject.title, self.attempted, self.correct)

class LearnerExamPracticeChapters(core_models.TimestampedModel):
    learner_exam = models.ForeignKey(courses_models.LearnerExams, on_delete = models.CASCADE, blank=True, null=True)
    subject = models.ForeignKey(courses_models.Subject, on_delete = models.CASCADE, blank=True, null=True)
    chapter = models.ForeignKey(courses_models.Chapter, on_delete = models.CASCADE, blank=True, null=True)
    score =  models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)
    total_marks =  models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)
    percentage = models.IntegerField(blank=False,null=False,default=0)
    total_time = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    time_taken = models.IntegerField(blank=False,null=False,default=0)
    total_questions =  models.IntegerField(blank=False,null=False,default=0)
    attempted = models.IntegerField(blank=False,null=False,default=0)
    correct = models.IntegerField(blank=False,null=False,default=0)
    unchecked = models.IntegerField(blank=False,null=False,default=0)
    incorrect = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}- Practice - {} Attempted: {} Correct: {}".format(self.learner_exam, self.chapter.title, self.attempted, self.correct)

class LearnerExamPracticeSubjects(core_models.TimestampedModel):
    learner_exam = models.ForeignKey(courses_models.LearnerExams, on_delete = models.CASCADE, blank=True, null=True)
    subject = models.ForeignKey(courses_models.Subject, on_delete = models.CASCADE, blank=True, null=True)
    chapters = models.ManyToManyField(LearnerExamPracticeChapters, blank=True, null=True)
    score =  models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)
    total_marks =  models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)
    percentage = models.IntegerField(blank=False,null=False,default=0)
    total_time = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    time_taken = models.IntegerField(blank=False,null=False,default=0)
    total_questions =  models.IntegerField(blank=False,null=False,default=0)
    attempted = models.IntegerField(blank=False,null=False,default=0)
    correct = models.IntegerField(blank=False,null=False,default=0)
    unchecked = models.IntegerField(blank=False,null=False,default=0)
    incorrect = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}- Practice - {} Attempted: {} Correct: {}".format(self.learner_exam, self.subject.title, self.attempted, self.correct)

class LearnerExamPaperChapters(core_models.TimestampedModel):
    learner_exam = models.ForeignKey(courses_models.LearnerExams, on_delete = models.CASCADE, blank=True, null=True)
    subject = models.ForeignKey(courses_models.Subject, on_delete = models.CASCADE, blank=True, null=True)
    chapter = models.ForeignKey(courses_models.Chapter, on_delete = models.CASCADE, blank=True, null=True)
    score =  models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)
    total_marks =  models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)
    percentage = models.IntegerField(blank=False,null=False,default=0)
    total_time = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    time_taken = models.IntegerField(blank=False,null=False,default=0)
    total_questions =  models.IntegerField(blank=False,null=False,default=0)
    attempted = models.IntegerField(blank=False,null=False,default=0)
    correct = models.IntegerField(blank=False,null=False,default=0)
    unchecked = models.IntegerField(blank=False,null=False,default=0)
    incorrect = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}- Paper - {} Attempted: {} Correct: {}".format(self.learner_exam, self.chapter.title, self.attempted, self.correct)

class LearnerExamPaperSubjects(core_models.TimestampedModel):
    learner_exam = models.ForeignKey(courses_models.LearnerExams, on_delete = models.CASCADE, blank=True, null=True)
    subject = models.ForeignKey(courses_models.Subject, on_delete = models.CASCADE, blank=True, null=True)
    chapters = models.ManyToManyField(LearnerExamPaperChapters, blank=True, null=True)
    score = models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)
    total_marks = models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)
    percentage = models.IntegerField(blank=False,null=False,default=0)
    total_time = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    time_taken = models.IntegerField(blank=False,null=False,default=0)
    total_questions =  models.IntegerField(blank=False,null=False,default=0)
    attempted = models.IntegerField(blank=False,null=False,default=0)
    correct = models.IntegerField(blank=False,null=False,default=0)
    unchecked = models.IntegerField(blank=False,null=False,default=0)
    incorrect = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}- Paper - {} Attempted: {} Correct: {}".format(self.learner_exam, self.subject.title, self.attempted, self.correct)

class LearnerPapers(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    learner_exam = models.ForeignKey(courses_models.LearnerExams, on_delete = models.CASCADE, blank=True, null=True)
    questions = models.ManyToManyField(Question, blank=True, null=True)
    bookmarks = models.ManyToManyField(LearnerBookmarks, related_name='bookmarks',
        blank = True, null=True)
    subjects = models.ManyToManyField(courses_models.Subject, blank=True, null=True)
    chapters = models.ManyToManyField(courses_models.Chapter, blank=True, null=True)
    score =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    marks =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    total_time = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    time_taken = models.IntegerField(blank=False,null=False,default=0)
    pause_count = models.IntegerField(blank=False,null=False,default=0)
    paper_count = models.IntegerField(blank=False,null=False,default=0)
    remaining_time = models.IntegerField(blank=True,null=True,default=0)
    paper_type = models.CharField(max_length=24, choices = paper_type, blank=False,null=False)
    show_time = models.BooleanField(default=True)
    submitted = models.BooleanField(default=False)
    actual_paper = models.ForeignKey('self', related_name='actual_learnerpaper', on_delete = models.CASCADE, blank = True, null=True)
    reattempt_papers = models.ManyToManyField('self', symmetrical=False, blank=True, null=True)
    is_linked_goal = models.BooleanField(default=False)
    goal_id = models.IntegerField(blank=True,null=True,default=0)
    path_id = models.IntegerField(blank=True,null=True,default=0)

    def __str__(self):
        return "{}-{}-{}".format(self.user.username, self.learner_exam, self.paper_type)

class LearnerTotalActualPapers(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    count = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}-{}".format(self.user.username, self.count)
    
class LearnerTotalPracticePapers(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    count = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}-{}".format(self.user.username, self.count)

class SharedPapers(core_models.TimestampedModel):
    sharer = models.ForeignKey(User, related_name='sharer', on_delete = models.CASCADE, blank = True)
    shared_to = models.ForeignKey(User, related_name='shared_to', on_delete = models.CASCADE, blank = True)
    shared_paper = models.ForeignKey(LearnerPapers, related_name='shared_paper', on_delete = models.CASCADE, blank=True, null=True)
    newly_created_paper = models.ForeignKey(LearnerPapers, related_name='newly_created_paper', on_delete = models.CASCADE, blank=True, null=True)
    shared_by_me_paper_count = models.IntegerField(blank=False,null=False,default=0)
    shared_to_me_paper_count = models.IntegerField(blank=False,null=False,default=0)

    def __unicode__(self):
        return "{}-{}-{}".format(self.sharer.username, self.shared_to.username, self.shared_paper)

class TemporaryLearnerBookmarks(core_models.TimestampedModel):
    learner_exam = models.ForeignKey(courses_models.LearnerExams, on_delete = models.CASCADE, blank=True, null=True)
    paper = models.ForeignKey(LearnerPapers, on_delete = models.CASCADE, blank=True, null=True)
    subject = models.ForeignKey(courses_models.Subject, on_delete = models.CASCADE, blank=True, null=True)
    chapter = models.ForeignKey(courses_models.Chapter, on_delete = models.CASCADE, blank=True, null=True)
    question = models.ForeignKey(Question, on_delete = models.CASCADE, blank=True, null=True)

    def __str__(self):
        return "{}-{}".format(self.learner_exam.exam.title, self.question.type_of_question)


class AnswerPaper(models.Model):
    user = models.ForeignKey(User, on_delete = models.CASCADE)
    assessment_paper = models.ForeignKey(LearnerPapers, on_delete = models.CASCADE, blank=True, null=True)
    # mock_paper = models.ForeignKey(MockPaper, on_delete = models.CASCADE, blank=True, null=True)
    start_time = models.DateTimeField("Start Date and Time of the qp", default = timezone.now)
    paper_complete = models.BooleanField(default=False)
    attempt_order = models.IntegerField("Number of Attempt paper",default=0)
    percentage = models.IntegerField("Total Percentage",default=0)
    time_taken = models.IntegerField("Number of minutes to finish paper",default=0)
    total_time = models.IntegerField(blank=False,null=False,default=0)
    total_questions =  models.IntegerField(blank=False,null=False,default=0)
    attempted = models.IntegerField(blank=False,null=False,default=0)
    correct = models.IntegerField(blank=False,null=False,default=0)
    unchecked = models.IntegerField(blank=False,null=False,default=0)
    incorrect = models.IntegerField(blank=False,null=False,default=0)
    attempted_date = models.DateTimeField(null=True, blank=True)
    question_unanswered = models.ManyToManyField(
        Question, related_name='question_unanswered',
        blank = True
    )
    question_answered = models.ManyToManyField(
        Question, related_name='question_answered',
        blank = True
    )
    question_markforreview = models.ManyToManyField(
        Question, related_name='question_markforreview',
        blank = True
    )
    question_save_markforreview = models.ManyToManyField(
        Question, related_name='question_save_markforreview',
        blank = True
    )
    question_order = models.TextField(blank=True, default='')

    def __str__(self):
        return("AnswerPaper of User {}".format(
                self.user.username
            )
        )
    
class UserSubjectiveAnswerImage(core_models.TimestampedModel):
    user_subjective_answer_image = models.FileField(_('user subjective answer image'), upload_to=user_subjective_answer_image, blank=True, null=True)

    def __str__(self):
        return self.user_subjective_answer_image.url if self.user_subjective_answer_image else None

class UserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete = models.CASCADE)
    answer_paper = models.ForeignKey(AnswerPaper, on_delete = models.CASCADE)
    attempt_order = models.IntegerField(default=0)
    question = models.ForeignKey(Question, on_delete = models.CASCADE)
    timespent = models.IntegerField(null=True, blank=True)
    type_of_answer = models.CharField(max_length=24)
    user_mcq_answer = models.ManyToManyField(
        McqTestCase, blank=True,
        related_name = "user_mcq_answer"
    )
    correct_mcq_answer = models.ManyToManyField(
        McqTestCase, blank=True,
        related_name = "correct_mcq_answer"
    )
    user_string_answer = RichTextUploadingField(_('text'), blank=True, null=True)
    user_boolean_answer = models.BooleanField(blank=True, null=True)
    correct_fillup_answer = models.ForeignKey(
        FillUpSolution, on_delete = models.CASCADE,
        null=True, blank=True,
        related_name="correct_fillup_answer"
    )
    user_fillup_option_answer = models.ForeignKey(
        FillUpWithOption, on_delete = models.CASCADE, blank=True, null=True,
        related_name = "user_fillup_option_answer"
    )
    correct_fillup_option_answer = models.ForeignKey(
        FillUpWithOption, on_delete = models.CASCADE,
        null=True, blank=True,
        related_name="correct_fillup_option_answer"
    )
    correct_boolean_answer = models.ForeignKey(
        TrueFalseSolution, on_delete = models.CASCADE,
        null=True, blank=True,
        related_name="correct_boolean_answer"
    )
    correct_string_answer = models.ForeignKey(
        StringTestCase, on_delete = models.CASCADE,
        null=True, blank=True,
        related_name="correct_string_answer"
    )
    user_subjective_answer = RichTextUploadingField(_('user subjective answer'), blank=True, null=True)
    user_subjective_answer_image = models.FileField(_('user subjective answer image'), upload_to=user_subjective_answer_image, blank=True, null=True)
    user_subjective_answer_images = models.ManyToManyField(UserSubjectiveAnswerImage, blank = True)
    teacher_subjective_comment = RichTextUploadingField(_('teacher subjective comment'), blank=True, null=True)
    status = models.BooleanField(default=False)
    score = models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)

    def __str__(self):
        return("{} | {} ".format(self.user, self.type_of_answer))

class PaperInstructions(core_models.TimestampedModel):
    paper = models.ForeignKey(LearnerPapers, on_delete = models.CASCADE)
    instruction = models.CharField(max_length=200, blank=True, null=True)

    def __unicode__(self):
        return "{}-{}".format(self.paper, self.instruction)

class LearnerHistory(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    questions = models.ManyToManyField(Question, blank=True)
    learner_exam = models.ManyToManyField(courses_models.LearnerExams, blank=True, null=True)
    papers =  models.ManyToManyField(LearnerPapers, blank=True, null=True)
    total_practice_time = models.IntegerField(blank=False,null=False,default=0)
    total_paper_time = models.IntegerField(blank=False,null=False,default=0)
    total_questions = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}".format(self.user.username)

class LearnerExamHistory(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    questions = models.ManyToManyField(Question, blank=True)
    total_questions = models.IntegerField(blank=False,null=False,default=0)
    exam = models.ForeignKey(courses_models.Exam, on_delete = models.CASCADE, blank = True, null=True)
    papers =  models.ManyToManyField(LearnerPapers, blank=True, null=True)
    total_practice_time = models.IntegerField(blank=False,null=False,default=0)
    total_paper_time = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}-{}".format(self.user.username, self.exam.title)

class LearnerExamPracticeHistory(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    questions = models.ManyToManyField(Question, blank=True)
    exam = models.ForeignKey(courses_models.Exam, on_delete = models.CASCADE, blank = True, null=True)
    papers =  models.ManyToManyField(LearnerPapers, blank=True, null=True)
    score =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    total_marks =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    percentage = models.IntegerField(blank=False,null=False,default=0)
    total_time = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    time_taken = models.IntegerField(blank=False,null=False,default=0)
    total_questions = models.IntegerField(blank=False,null=False,default=0)
    attempted = models.IntegerField(blank=False,null=False,default=0)
    skipped = models.IntegerField(blank=False,null=False,default=0)
    correct = models.IntegerField(blank=False,null=False,default=0)
    unchecked = models.IntegerField(blank=False,null=False,default=0)
    incorrect = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}-{}".format(self.user.username, self.exam.title)

class LearnerExamPaperHistory(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    questions = models.ManyToManyField(Question, blank=True)
    exam = models.ForeignKey(courses_models.Exam, on_delete = models.CASCADE, blank = True, null=True)
    papers =  models.ManyToManyField(LearnerPapers, blank=True, null=True)
    score =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    total_marks =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    percentage = models.IntegerField(blank=False,null=False,default=0)
    total_time = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    time_taken = models.IntegerField(blank=False,null=False,default=0)
    total_questions = models.IntegerField(blank=False,null=False,default=0)
    attempted = models.IntegerField(blank=False,null=False,default=0)
    skipped = models.IntegerField(blank=False,null=False,default=0)
    correct = models.IntegerField(blank=False,null=False,default=0)
    unchecked = models.IntegerField(blank=False,null=False,default=0)
    incorrect = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}-{}".format(self.user.username, self.exam.title)

class PostQuerySuggestiveQuestions(core_models.TimestampedModel):
    text = models.CharField(max_length=1100, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "{}-{}".format(self.text)

class LearnerQuery(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True, null=True)
    exam = models.ForeignKey(courses_models.Exam, on_delete = models.CASCADE, blank = True, null=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    email = models.CharField(max_length=70, blank=True, null=True)
    contact = models.CharField(max_length=20, blank=True, null=True)
    query = models.CharField(max_length=1100, blank=True, null=True)
    reply = models.CharField(max_length=1100, blank=True, null=True)
    is_replied = models.BooleanField(default=False)

    def __str__(self):
        return "{}-{}".format(self.user.username)

class QuestionIdentifiers(core_models.TimestampedModel):
    question = models.ForeignKey(Question, on_delete = models.CASCADE, blank=True, null=True)
    identifier = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return "{}-{}".format(self.question.id, self.identifier)

class InstituteClassRoom(core_models.TimestampedModel):
    """
    Model to store name of the classes
    """
    institute = models.ForeignKey(Institute, on_delete = models.CASCADE, blank = True,null = True,)
    branch=models.ForeignKey(BranchSchool,on_delete=models.CASCADE, blank = True,null = True,related_name="branchname")
    grade = models.ForeignKey(core_models.UserClass, on_delete = models.CASCADE, blank = True)
    name = models.CharField(max_length=50)
    blocked_students = models.ManyToManyField(User, related_name="blocked_students", blank=True)
    room_teacher = models.ForeignKey(User, on_delete = models.CASCADE, blank=True, null=True)
    unique_id = models.CharField(max_length=30, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    session = models.ForeignKey(core_models.UserSeasson,on_delete=models.CASCADE ,blank=True, null=True)

    # def __str__(self):
    #     return  ("{} - {}".format(self.institute.name, self.name))


class Batch(core_models.TimestampedModel):
    teacher = models.ForeignKey(User, on_delete = models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    batch_code = models.CharField(max_length=20, blank=True, null=True, unique=True)
    students = models.ManyToManyField(User, related_name="students", blank=True)
    is_active = models.BooleanField(default=True)
    grade = models.ForeignKey(core_models.UserClass, on_delete = models.CASCADE, blank = True,null=True,related_name="gradename")
    institute_room = models.ForeignKey(InstituteClassRoom, on_delete = models.CASCADE, blank = True, null=True)
    unique_id = models.CharField(max_length=30, blank=True, null=True)

    def __str__(self):
        return "{}-{}-{}".format(self.teacher.username, self.name, self.batch_code)


class BatchTotalActualPapers(core_models.TimestampedModel):
    batch = models.ForeignKey(Batch, on_delete = models.CASCADE, blank = True)
    count = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}-{}".format(self.batch.name, self.count)
    
class BatchTotalPracticePapers(core_models.TimestampedModel):
    batch = models.ForeignKey(Batch, on_delete = models.CASCADE, blank = True)
    count = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}-{}".format(self.batch.name, self.count)

class LearnerBatches(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    batch = models.ForeignKey(Batch, on_delete = models.CASCADE, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "{}-{}".format(self.user.username, self.batch.name)

class MentorPapers(core_models.TimestampedModel):
    mentor = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    exam = models.ForeignKey(courses_models.Exam, on_delete = models.CASCADE, blank=True, null=True)
    batch = models.ForeignKey(Batch, on_delete = models.CASCADE, blank=True, null=True)
    questions = models.ManyToManyField(Question, blank=True, null=True)
    subjects = models.ManyToManyField(courses_models.Subject, blank=True, null=True)
    chapters = models.ManyToManyField(courses_models.Chapter, blank=True, null=True)
    score = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    marks = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    total_time = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    difficulty_level = models.IntegerField(blank=False,null=False,default=5)
    time_taken = models.IntegerField(blank=False,null=False,default=0)
    paper_count = models.IntegerField(blank=False,null=False,default=0)
    paper_type = models.CharField(max_length=24, choices = paper_type, blank=False,null=False)
    show_time = models.BooleanField(default=True)
    submitted = models.BooleanField(default=False)
    exam_start_date_time = models.DateTimeField("Start Date and Time of the Exam",blank=True, null=True)
    exam_end_date_time = models.DateTimeField("End Date and Time of the Exam",blank=True, null=True)

    def __str__(self):
        return "{}-{}-{}".format(self.mentor.username, self.exam, self.paper_type)

class MentorPaperInstructions(core_models.TimestampedModel):
    paper = models.ForeignKey(MentorPapers, on_delete = models.CASCADE)
    instruction = models.CharField(max_length=200, blank=True, null=True)

    def __unicode__(self):
        return "{}-{}".format(self.paper, self.instruction)

class MentorPaperAnswerPaper(models.Model):
    user = models.ForeignKey(User, on_delete = models.CASCADE)
    mentor_paper = models.ForeignKey(MentorPapers, on_delete = models.CASCADE, blank=True, null=True)
    reattempt_papers = models.ManyToManyField('self', symmetrical=False, blank=True, null=True)
    start_time = models.DateTimeField("Start Date and Time of the qp", default = timezone.now)
    paper_complete = models.BooleanField(default=False)
    attempt_order = models.IntegerField("Number of Attempt paper",default=0)
    score =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    marks =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    pause_count = models.IntegerField(blank=False,null=False,default=0)
    remaining_time = models.IntegerField(blank=True,null=True,default=0)
    paper_type = models.CharField(max_length=24, choices = paper_type, blank=False,null=False)
    bookmarks = models.ManyToManyField(LearnerBookmarks, related_name='user_bookmarks',
        blank = True, null=True)
    percentage = models.IntegerField("Total Percentage",default=0)
    time_taken = models.IntegerField("Number of minutes to finish paper",default=0)
    total_time = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    total_questions =  models.IntegerField(blank=False,null=False,default=0)
    attempted = models.IntegerField(blank=False,null=False,default=0)
    correct = models.IntegerField(blank=False,null=False,default=0)
    incorrect = models.IntegerField(blank=False,null=False,default=0)
    unchecked = models.IntegerField(blank=False,null=False,default=0)
    submitted = models.BooleanField(default=False)
    remarks = models.CharField(max_length=1100, blank=True, null=True)
    attempted_date = models.DateTimeField(null=True, blank=True)
    question_unanswered = models.ManyToManyField(
        Question, related_name='paper_question_unanswered',
        blank = True
    )
    question_answered = models.ManyToManyField(
        Question, related_name='paper_question_answered',
        blank = True
    )
    question_markforreview = models.ManyToManyField(
        Question, related_name='paper_question_markforreview',
        blank = True
    )
    question_save_markforreview = models.ManyToManyField(
        Question, related_name='paper_question_save_markforreview',
        blank = True
    )
    question_order = models.TextField(blank=True, default='')

    def __str__(self):
        return("MentorPaperAnswerPaper of User {}".format(
                self.user.username
            )
        )

class UserAnswerMentorPaper(models.Model):
    user = models.ForeignKey(User, on_delete = models.CASCADE)
    answer_paper = models.ForeignKey(MentorPaperAnswerPaper, on_delete = models.CASCADE)
    attempt_order = models.IntegerField(default=0)
    question = models.ForeignKey(Question, on_delete = models.CASCADE)
    timespent = models.IntegerField(null=True, blank=True)
    type_of_answer = models.CharField(max_length=24)
    user_mcq_answer = models.ManyToManyField(
        McqTestCase, blank=True,
        related_name = "user_mcq_answer_mentor_paper"
    )
    correct_mcq_answer = models.ManyToManyField(
        McqTestCase, blank=True,
        related_name = "correct_mcq_answer_mentor_paper"
    )
    user_string_answer = RichTextUploadingField(_('text'), blank=True, null=True)
    user_boolean_answer = models.BooleanField(blank=True, null=True)
    correct_fillup_answer = models.ForeignKey(
        FillUpSolution, on_delete = models.CASCADE,
        null=True, blank=True,
        related_name="correct_fillup_answer_mentor_paper"
    )
    user_fillup_option_answer = models.ForeignKey(
        FillUpWithOption, on_delete = models.CASCADE, blank=True, null=True,
        related_name = "user_fillup_option_answer_mentor_paper"
    )
    correct_fillup_option_answer = models.ForeignKey(
        FillUpWithOption, on_delete = models.CASCADE,
        null=True, blank=True,
        related_name="correct_fillup_option_answer_mentor_paper"
    )
    correct_boolean_answer = models.ForeignKey(
        TrueFalseSolution, on_delete = models.CASCADE,
        null=True, blank=True,
        related_name="correct_boolean_answer_mentor_paper"
    )
    correct_string_answer = models.ForeignKey(
        StringTestCase, on_delete = models.CASCADE,
        null=True, blank=True,
        related_name="correct_string_answer_mentor_paper"
    )
    user_subjective_answer = RichTextUploadingField(_('user subjective answer'), blank=True, null=True)
    user_subjective_answer_image = models.FileField(_('user subjective answer image'), upload_to=user_subjective_answer_image, blank=True, null=True)
    user_subjective_answer_images = models.ManyToManyField(UserSubjectiveAnswerImage, blank = True)
    teacher_subjective_comment = RichTextUploadingField(_('teacher subjective comment'), blank=True, null=True)
    status = models.BooleanField(default=False)
    score = models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)

    def __str__(self):
        return("{} | {} ".format(self.user, self.type_of_answer))

class LearnerBatchHistory(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    questions = models.ManyToManyField(Question, blank=True)
    batch = models.ForeignKey(Batch, on_delete = models.CASCADE, blank = True, null=True)
    papers =  models.ManyToManyField(MentorPapers, blank=True, null=True)
    total_paper_count = models.IntegerField(blank=False,null=False,default=0)
    total_practice_count = models.IntegerField(blank=False,null=False,default=0)
    total_practice_time_taken = models.IntegerField(blank=False,null=False,default=0)
    total_paper_time_taken = models.IntegerField(blank=False,null=False,default=0)
    paper_score =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    total_paper_marks =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    practice_score =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    total_practice_marks = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    paper_percentage = models.IntegerField(blank=False,null=False,default=0)
    practice_percentage = models.IntegerField(blank=False,null=False,default=0)
    total_paper_time = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    total_practice_time = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    total_questions = models.IntegerField(blank=False,null=False,default=0)
    total_attempted_paper = models.IntegerField(blank=False,null=False,default=0)
    total_skipped_paper = models.IntegerField(blank=False,null=False,default=0)
    total_correct_paper = models.IntegerField(blank=False,null=False,default=0)
    total_incorrect_paper = models.IntegerField(blank=False,null=False,default=0)
    total_attempted_practice = models.IntegerField(blank=False,null=False,default=0)
    total_skipped_practice = models.IntegerField(blank=False,null=False,default=0)
    total_correct_practice = models.IntegerField(blank=False,null=False,default=0)
    total_incorrect_practice = models.IntegerField(blank=False,null=False,default=0)
    is_blocked = models.BooleanField(default=False)

    def __str__(self):
        return "{}-{}".format(self.user.username, self.batch.name)

class TemporaryMentorPaperLearnerBookmarks(core_models.TimestampedModel):
    learner_exam = models.ForeignKey(courses_models.LearnerExams, on_delete = models.CASCADE, blank=True, null=True)
    paper = models.ForeignKey(MentorPaperAnswerPaper, on_delete = models.CASCADE, blank=True, null=True)
    subject = models.ForeignKey(courses_models.Subject, on_delete = models.CASCADE, blank=True, null=True)
    chapter = models.ForeignKey(courses_models.Chapter, on_delete = models.CASCADE, blank=True, null=True)
    question = models.ForeignKey(Question, on_delete = models.CASCADE, blank=True, null=True)

    def __str__(self):
        return "{}-{}".format(self.learner_exam.exam.title, self.question.type_of_question)
    
class ReportedErrorneousQuestion(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    exam = models.ForeignKey(courses_models.Exam, on_delete = models.CASCADE, blank = True, null=True)
    question = models.ForeignKey(Question, on_delete = models.CASCADE, blank=True, null=True)
    issue_type = models.CharField(max_length=50, blank=True, null=True)
    query = models.CharField(max_length=1100, blank=True, null=True)
    reply = models.CharField(max_length=1100, blank=True, null=True)
    is_replied = models.BooleanField(default=False)

    def __str__(self):
        return "{}-{}".format(self.user.username, self.exam.title)

class ContactUs(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True, null=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    email = models.CharField(max_length=70, blank=True, null=True)
    contact = models.CharField(max_length=20, blank=True, null=True)
    query = models.CharField(max_length=1100, blank=True, null=True)

    def __str__(self):
        return "{}-{}".format(self.user.username, self.query)

class FAQ(core_models.TimestampedModel):
    is_active = models.BooleanField(default=True)
    title = models.CharField(max_length=150)
    content = RichTextUploadingField(_('content'), blank=True, null=True)

    def __str__(self):
        return ("{}".format(self.title))

class MentorFAQ(core_models.TimestampedModel):
    is_active = models.BooleanField(default=True)
    title = models.CharField(max_length=150)
    content = RichTextUploadingField(_('content'), blank=True, null=True)

    def __str__(self):
        return ("{}".format(self.title))

class BannerSliderImages(core_models.TimestampedModel):
    image = models.ImageField(upload_to=banner_image_upload_to, blank=True)
    title = models.CharField(max_length=200, blank = True, null=True)
    link = models.CharField(max_length=700, blank = True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "{}-{}".format(self.link, self.title)
        
class LearnerBlockedBatches(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    batch = models.ForeignKey(Batch, on_delete = models.CASCADE, blank=True, null=True)

    def __str__(self):
        return "{}-{}".format(self.user.username, self.batch.name)

class MockPaperExamDetails(core_models.TimestampedModel):
    exam = models.ForeignKey(courses_models.Exam, on_delete = models.CASCADE)
    difficulty_level = models.IntegerField(blank=False,null=False,default=5)
    show_time = models.BooleanField(default=True)
    chapters = models.ManyToManyField(courses_models.Chapter, blank = True)

    def __str__(self):
        return  ("{}".format(self.exam.title))

class MockPaperSubjectDetails(core_models.TimestampedModel):
    exam = models.ForeignKey(courses_models.Exam, on_delete = models.CASCADE)
    subject = models.ForeignKey(courses_models.Subject, on_delete = models.CASCADE)
    chapters = models.ManyToManyField(courses_models.Chapter, blank = True)

    def __str__(self):
        return  ("{}".format(self.exam.title))

class MockPaperSubjectQuestionTypeDetails(core_models.TimestampedModel):
    exam = models.ForeignKey(courses_models.Exam, on_delete = models.CASCADE)
    subject = models.ForeignKey(courses_models.Subject, on_delete = models.CASCADE)
    type_of_question = models.CharField(max_length=24, choices = question_type)
    total_questions = models.IntegerField(blank=False,null=False,default=0)
    total_time = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return  ("{}".format(self.exam.title))

class TemporaryMentorPaperReplaceQuestions(core_models.TimestampedModel):
    paper = models.ForeignKey(MentorPapers, on_delete = models.CASCADE, blank=True, null=True)
    questions = models.ManyToManyField(Question, blank = True, null=True)

    def __str__(self):
        return "{}-{}".format(self.paper.paper_count, self.questions)

class TemporaryMentorPracticeReplaceQuestions(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True, null=True)
    exam = models.ForeignKey(courses_models.Exam, on_delete = models.CASCADE)
    chapter = models.ForeignKey(courses_models.Chapter, on_delete = models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete = models.CASCADE, blank=True, null=True)
    questions = models.ManyToManyField(Question, blank = True, null=True)
    exam_end_date_time = models.DateTimeField("End Date and Time of the Exam",blank=True, null=True)
    difficulty_level = models.IntegerField(blank=False,null=False,default=5)

    def __str__(self):
        return "{}-{}".format(self.exam.title, self.batch.name)

class TemporaryMentorActualPaperReplaceQuestions(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True, null=True)
    exam = models.ForeignKey(courses_models.Exam, on_delete = models.CASCADE)
    chapters = models.ManyToManyField(courses_models.Chapter, blank=True, null=True)
    batch = models.ForeignKey(Batch, on_delete = models.CASCADE, blank=True, null=True)
    questions = models.ManyToManyField(Question, blank = True, null=True)
    show_time = models.BooleanField(default=True)
    exam_start_date_time = models.DateTimeField("Start Date and Time of the Exam",blank=True, null=True)
    exam_end_date_time = models.DateTimeField("End Date and Time of the Exam",blank=True, null=True)
    difficulty_level = models.IntegerField(blank=False,null=False,default=5)

    def __str__(self):
        return "{}-{}".format(self.exam.title, self.batch.name)

class LearnerExamGoals(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True, null=True)
    exam = models.ForeignKey(courses_models.Exam, on_delete = models.CASCADE, blank=True, null=True)
    title = models.CharField(max_length=200)
    last_date = models.DateTimeField(null=True, blank=True)
    syllabus = models.CharField(max_length=50, choices = syllabus, blank=True, null=True)
    level = models.CharField(max_length=50, choices = proficiency_level, blank=True, null=True)
    chapters = models.ManyToManyField(courses_models.Chapter, blank=True, null=True)
    subjects = models.ManyToManyField(courses_models.Subject, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    evaluation_done = models.BooleanField(default=False)
    assessment_done = models.BooleanField(default=False)
    assessment_skipped = models.BooleanField(default=False)
    count = models.IntegerField(blank=False,null=False,default=0)
    learn_percentage = models.IntegerField(blank=False,null=False,default=0)
    revise_percentage = models.IntegerField(blank=False,null=False,default=0)
    practice_percentage = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}-{}".format(self.user, self.title)

class SelfAssessExamAnswerPaper(models.Model):
    user = models.ForeignKey(User, on_delete = models.CASCADE)
    goal = models.ForeignKey(LearnerExamGoals, on_delete = models.CASCADE, blank=True, null=True)
    questions = models.ManyToManyField(courses_models.SelfAssessQuestion, blank=True, null=True)
    start_time = models.DateTimeField("Start Date and Time of the qp", default = timezone.now)
    paper_complete = models.BooleanField(default=False)
    total_questions =  models.IntegerField(blank=False,null=False,default=0)
    attempted = models.IntegerField(blank=False,null=False,default=0)
    attempted_date = models.DateTimeField(null=True, blank=True)
    question_unanswered = models.ManyToManyField(
        courses_models.SelfAssessQuestion, related_name='question_unanswered',
        blank = True
    )
    question_answered = models.ManyToManyField(
        courses_models.SelfAssessQuestion, related_name='question_answered',
        blank = True
    )
    question_order = models.TextField(blank=True, default='')

    def __str__(self):
        return("SelfAssessAnswerPaper of User {}".format(
                self.user.username
            )
        )

class SelfAssessUserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete = models.CASCADE)
    answer_paper = models.ForeignKey(SelfAssessExamAnswerPaper, on_delete = models.CASCADE)
    attempt_order = models.IntegerField(default=0)
    question = models.ForeignKey(courses_models.SelfAssessQuestion, on_delete = models.CASCADE)
    type_of_answer = models.CharField(max_length=24)
    user_mcq_answer = models.ManyToManyField(
        courses_models.SelfAssessMcqOptions, blank=True,
        related_name = "user_mcq_answer"
    )
    user_string_answer = models.CharField(max_length=200, blank=True, null=True)
    teacher_comment = RichTextUploadingField(_('teacher comment'), blank=True, null=True)
    status = models.BooleanField(default=False)
    score = models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)

    def __str__(self):
        return("{} | {} ".format(self.user, self.type_of_answer))

class GoalAssessmentExamAnswerPaper(models.Model):
    user = models.ForeignKey(User, on_delete = models.CASCADE)
    goal = models.ForeignKey(LearnerExamGoals, on_delete = models.CASCADE, blank=True, null=True)
    questions = models.ManyToManyField(Question, blank=True, null=True)
    subjects = models.ManyToManyField(courses_models.Subject, blank=True, null=True)
    chapters = models.ManyToManyField(courses_models.Chapter, blank=True, null=True)
    paper_type = models.CharField(max_length=24, choices = paper_type, blank=False,null=False)
    show_time = models.BooleanField(default=True)
    submitted = models.BooleanField(default=False)
    score =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    marks =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    started = models.BooleanField(default=False)
    pregoal_paper = models.BooleanField(default=False)
    start_time = models.DateTimeField("Start Date and Time of the qp", default = timezone.now)
    paper_complete = models.BooleanField(default=False)
    pause_count = models.IntegerField(blank=False,null=False,default=0)
    total_questions =  models.IntegerField(blank=False,null=False,default=0)
    attempted = models.IntegerField(blank=False,null=False,default=0)
    attempted_date = models.DateTimeField(null=True, blank=True)
    percentage = models.IntegerField("Total Percentage",default=0)
    time_taken = models.IntegerField("Number of minutes to finish paper",default=0)
    total_time = models.IntegerField(blank=False,null=False,default=0)
    paper_count = models.IntegerField(blank=False,null=False,default=0)
    remaining_time = models.IntegerField(blank=True,null=True,default=0)
    correct = models.IntegerField(blank=False,null=False,default=0)
    unchecked = models.IntegerField(blank=False,null=False,default=0)
    incorrect = models.IntegerField(blank=False,null=False,default=0)
    question_unanswered = models.ManyToManyField(
        Question, related_name='goal_question_unanswered',
        blank = True
    )
    question_answered = models.ManyToManyField(
        Question, related_name='goal_question_answered',
        blank = True
    )
    question_markforreview = models.ManyToManyField(
        Question, related_name='goal_question_markforreview',
        blank = True
    )
    question_save_markforreview = models.ManyToManyField(
        Question, related_name='goal_question_save_markforreview',
        blank = True
    )
    question_order = models.TextField(blank=True, default='')

    def __str__(self):
        return("SelfAssessAnswerPaper of User {}".format(
                self.user.username
            )
        )

class GoalAssessmentUserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete = models.CASCADE)
    answer_paper = models.ForeignKey(GoalAssessmentExamAnswerPaper, on_delete = models.CASCADE)
    attempt_order = models.IntegerField(default=0)
    question = models.ForeignKey(Question, on_delete = models.CASCADE)
    timespent = models.IntegerField(null=True, blank=True)
    type_of_answer = models.CharField(max_length=24)
    user_mcq_answer = models.ManyToManyField(
        McqTestCase, blank=True,
        related_name = "goal_user_mcq_answer"
    )
    correct_mcq_answer = models.ManyToManyField(
        McqTestCase, blank=True,
        related_name = "goal_correct_mcq_answer"
    )
    user_string_answer = RichTextUploadingField(_('text'), blank=True, null=True)
    user_boolean_answer = models.BooleanField(blank=True, null=True)
    correct_fillup_answer = models.ForeignKey(
        FillUpSolution, on_delete = models.CASCADE,
        null=True, blank=True,
        related_name="goal_correct_fillup_answer"
    )
    user_fillup_option_answer = models.ForeignKey(
        FillUpWithOption, on_delete = models.CASCADE, blank=True, null=True,
        related_name = "goal_user_fillup_option_answer"
    )
    correct_fillup_option_answer = models.ForeignKey(
        FillUpWithOption, on_delete = models.CASCADE,
        null=True, blank=True,
        related_name="goal_correct_fillup_option_answer"
    )
    correct_boolean_answer = models.ForeignKey(
        TrueFalseSolution, on_delete = models.CASCADE,
        null=True, blank=True,
        related_name="goal_correct_boolean_answer"
    )
    correct_string_answer = models.ForeignKey(
        StringTestCase, on_delete = models.CASCADE,
        null=True, blank=True,
        related_name="goal_correct_string_answer"
    )
    user_subjective_answer = RichTextUploadingField(_('user subjective answer'), blank=True, null=True)
    user_subjective_answer_image = models.FileField(_('user subjective answer image'), upload_to=user_subjective_answer_image, blank=True, null=True)
    user_subjective_answer_images = models.ManyToManyField(UserSubjectiveAnswerImage, blank = True)
    teacher_subjective_comment = RichTextUploadingField(_('teacher subjective comment'), blank=True, null=True)
    status = models.BooleanField(default=False)
    score = models.DecimalField(blank=False,null=False,default=0, max_digits=10, decimal_places=2)


    def __str__(self):
        return("{} | {} ".format(self.user, self.type_of_answer))


# class GoalAssessmentPaperInstructions(core_models.TimestampedModel):
#     paper = models.ForeignKey(GoalAssessmentExamAnswerPaper, on_delete = models.CASCADE)
#     instruction = models.CharField(max_length=200, blank=True, null=True)

#     def __unicode__(self):
#         return "{}-{}".format(self.paper, self.instruction)

class GoalAssessmentExamPaperInstructions(core_models.TimestampedModel):
    paper = models.ForeignKey(GoalAssessmentExamAnswerPaper, on_delete = models.CASCADE)
    instruction = models.CharField(max_length=200, blank=True, null=True)

    def __unicode__(self):
        return "{}-{}".format(self.paper, self.instruction)

class LearnerGoalHistory(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    questions = models.ManyToManyField(Question, blank=True)
    total_questions = models.IntegerField(blank=False,null=False,default=0)
    goal = models.ForeignKey(LearnerExamGoals, on_delete = models.CASCADE, blank = True, null=True)
    papers =  models.ManyToManyField(GoalAssessmentExamAnswerPaper, blank=True, null=True)
    total_practice_time = models.IntegerField(blank=False,null=False,default=0)
    total_paper_time = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}-{}".format(self.user.username, self.exam.title)

class LearnerGoalPracticeHistory(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    questions = models.ManyToManyField(Question, blank=True)
    goal = models.ForeignKey(LearnerExamGoals, on_delete = models.CASCADE, blank = True, null=True)
    papers =  models.ManyToManyField(GoalAssessmentExamAnswerPaper, blank=True, null=True)
    score =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    total_marks =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    percentage = models.IntegerField(blank=False,null=False,default=0)
    total_time = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    time_taken = models.IntegerField(blank=False,null=False,default=0)
    total_questions = models.IntegerField(blank=False,null=False,default=0)
    attempted = models.IntegerField(blank=False,null=False,default=0)
    skipped = models.IntegerField(blank=False,null=False,default=0)
    correct = models.IntegerField(blank=False,null=False,default=0)
    unchecked = models.IntegerField(blank=False,null=False,default=0)
    incorrect = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}-{}".format(self.user.username, self.exam.title)

class LearnerGoalPaperHistory(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    questions = models.ManyToManyField(Question, blank=True)
    goal = models.ForeignKey(LearnerExamGoals, on_delete = models.CASCADE, blank = True, null=True)
    papers =  models.ManyToManyField(GoalAssessmentExamAnswerPaper, blank=True, null=True)
    score =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    total_marks =  models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    percentage = models.IntegerField(blank=False,null=False,default=0)
    total_time = models.DecimalField(blank=False,null=False,default=0, max_digits=20, decimal_places=2)
    time_taken = models.IntegerField(blank=False,null=False,default=0)
    total_questions = models.IntegerField(blank=False,null=False,default=0)
    attempted = models.IntegerField(blank=False,null=False,default=0)
    skipped = models.IntegerField(blank=False,null=False,default=0)
    correct = models.IntegerField(blank=False,null=False,default=0)
    unchecked = models.IntegerField(blank=False,null=False,default=0)
    incorrect = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}-{}".format(self.user.username, self.exam.title)

class ChapterMasterFTag(core_models.TimestampedModel):
    chapter = models.ForeignKey(courses_models.Chapter, on_delete = models.CASCADE)
    questions = models.ManyToManyField(Question, blank=True, null=True)

    def __str__(self):
        return  ("{} - {}".format(self.chapter.title, self.questions.count()))

class TemporaryPaperSubjectQuestionDistribution(core_models.TimestampedModel):
    learner_paper = models.ForeignKey(LearnerPapers, on_delete = models.CASCADE, blank=True, null=True)
    mentor_paper = models.ForeignKey(MentorPapers, on_delete = models.CASCADE, blank=True, null=True)
    goal_paper = models.ForeignKey(GoalAssessmentExamAnswerPaper, on_delete = models.CASCADE, blank=True, null=True)
    subject = models.ForeignKey(courses_models.Subject, on_delete = models.CASCADE, blank=True, null=True)
    chapter = models.ForeignKey(courses_models.Chapter, on_delete = models.CASCADE, blank=True, null=True)
    question = models.ForeignKey(Question, on_delete = models.CASCADE)

    def __str__(self):
        return  ("{} - {}".format(self.subject.title, self.question.id))

class UserClassRoom(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    institute_rooms = models.ManyToManyField(InstituteClassRoom, blank=True, null=True)

    # def __str__(self):
    #     return  ("{} - {}".format(self.institute.name, self.name))

class UnregisteredMentorBatch(core_models.TimestampedModel):
    phonenumber = models.CharField(null=True, blank=True, max_length=15)
    institute_room = models.ForeignKey(InstituteClassRoom, on_delete = models.CASCADE, blank=True, null=True)

    def __str__(self):
        return "Text: {}  ID: {}".format(self.phonenumber, self.institute_room)

class LearnerExamGoalPath(core_models.TimestampedModel):
    goal = models.ForeignKey(LearnerExamGoals, on_delete = models.CASCADE, blank=True, null=True)
    counter = models.IntegerField(blank=False,null=False,default=0)
    previous_path_id = models.IntegerField(blank=False,null=False,default=0)
    next_path_id = models.IntegerField(blank=False,null=False,default=0)
    frozen_date = models.DateTimeField(null=True, blank=True)
    freeze = models.BooleanField(default=False)
    learn_percentage = models.IntegerField(blank=False,null=False,default=0)
    revise_percentage = models.IntegerField(blank=False,null=False,default=0)
    practice_percentage = models.IntegerField(blank=False,null=False,default=0)
    done_with_assessment = models.BooleanField(default=False)
    paper = models.ForeignKey(LearnerPapers, on_delete = models.CASCADE, blank=True, null=True)

    def __str__(self):
        return "{}".format(self.goal.title)

class GoalPathLearnChapterHistory(core_models.TimestampedModel):
    path = models.ForeignKey(LearnerExamGoalPath, on_delete = models.CASCADE, blank=True, null=True)
    chapter = models.ForeignKey(courses_models.Chapter, on_delete = models.CASCADE, blank=True, null=True)
    percentage = models.IntegerField(blank=False,null=False,default=0)
    is_done = models.BooleanField(default=False)

    def __str__(self):
        return "{}".format(self.path.goal.title)

class GoalPathLearnChapterHintHistory(core_models.TimestampedModel):
    learn_chapter = models.ForeignKey(GoalPathLearnChapterHistory, on_delete = models.CASCADE, blank=True, null=True)
    order = models.IntegerField(blank=False,null=False,default=0)
    chapter_hint = models.ForeignKey(courses_models.ChapterHints, on_delete = models.CASCADE, blank=True, null=True)
    last_check_date = models.DateTimeField(null=True, blank=True)
    checked = models.BooleanField(default=False)

    def __str__(self):
        return "{}".format(self.learn_chapter.path.goal.title)

class GoalPathReviseChapterHistory(core_models.TimestampedModel):
    path = models.ForeignKey(LearnerExamGoalPath, on_delete = models.CASCADE, blank=True, null=True)
    chapter = models.ForeignKey(courses_models.Chapter, on_delete = models.CASCADE, blank=True, null=True)
    percentage = models.IntegerField(blank=False,null=False,default=0)
    frozen_date = models.DateTimeField(null=True, blank=True)
    is_done = models.BooleanField(default=False)

    def __str__(self):
        return "{}".format(self.path.goal.title)

class GoalPathReviseChapterHintHistory(core_models.TimestampedModel):
    revise_chapter = models.ForeignKey(GoalPathReviseChapterHistory, on_delete = models.CASCADE, blank=True, null=True)
    order = models.IntegerField(blank=False,null=False,default=0)
    chapter_hint = models.ForeignKey(courses_models.ChapterHints, on_delete = models.CASCADE, blank=True, null=True)
    last_check_date = models.DateTimeField(null=True, blank=True)
    checked = models.BooleanField(default=False)

    def __str__(self):
        return "{}".format(self.revise_chapter.path.goal.title)

class StudentInstituteChangeInvitation(core_models.TimestampedModel):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = True)
    inviting_institute_room = models.ForeignKey(InstituteClassRoom, on_delete = models.CASCADE, blank=True, null=True)

    def __str__(self):
        return "User: {}  Room: {}".format(self.user, self.inviting_institute_room)

class MentorBookmarks(core_models.TimestampedModel):
    mentor_exam = models.ForeignKey(courses_models.MentorExams, on_delete = models.CASCADE, blank=True, null=True)
    subject = models.ForeignKey(courses_models.Subject, on_delete = models.CASCADE, blank=True, null=True)
    chapter = models.ForeignKey(courses_models.Chapter, on_delete = models.CASCADE, blank=True, null=True)
    question = models.ForeignKey(Question, on_delete = models.CASCADE, blank=True, null=True)

    def __unicode__(self):
        return "{}-{}".format(self.mentor_exam.exam.title, self.question)

class MentorExamChapters(core_models.TimestampedModel):
    mentor_exam = models.ForeignKey(courses_models.MentorExams, on_delete = models.CASCADE, blank=True, null=True)
    subject = models.ForeignKey(courses_models.Subject, on_delete = models.CASCADE, blank=True, null=True)
    chapter = models.ForeignKey(courses_models.Chapter, on_delete = models.CASCADE, blank=True, null=True)
    total_bookmarks = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}-{} Bookmarks: {}".format(self.mentor_exam.exam.title, self.chapter.title, self.total_bookmarks)

class MentorExamSubjects(core_models.TimestampedModel):
    mentor_exam = models.ForeignKey(courses_models.MentorExams, on_delete = models.CASCADE, blank=True, null=True)
    subject = models.ForeignKey(courses_models.Subject, on_delete = models.CASCADE, blank=True, null=True)
    chapters = models.ManyToManyField(MentorExamChapters, blank=True, null=True)
    total_bookmarks = models.IntegerField(blank=False,null=False,default=0)

    def __str__(self):
        return "{}-{} Bookmarks: {}".format(self.mentor_exam, self.subject.title, self.total_bookmarks)