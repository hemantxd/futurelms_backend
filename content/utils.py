from collections import OrderedDict
from decimal import DivisionByZero
from statistics import mode
from content.serializers import LearnerPaperSerializer, QuestionSerializer, ViewBatchSerializer
import os
import re
import zipfile
import time
import csv
from itertools import tee
from random import sample
from . import models
from rest_framework import serializers, status
import datetime
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from rest_framework.response import Response
import re
import pandas as pd
import numpy as np

from docx import Document
import html
from docx.shared import Inches
from html.parser import HTMLParser

from content import models as content_models
from profiles import models as profile_models
from courses import models as course_models
from authentication import models as auth_models

from io import BytesIO
from django.db.models import Count, Func
from django.utils.html import strip_tags
from django.db.models import Q


def fraction_percentage(a, b):
    if b == 0:
        return 0
    else:
        return round(a / b * 100)

def current_milli_time(): return int(round(time.time() * 1000))

class UserSubjectiveAnswerImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = content_models.UserSubjectiveAnswerImage
        fields = ('id','user_subjective_answer_image')

def bulkuploadquestioncsv(csv_file, opid=None, **kwargs):
    alerts, question_ids = [], []
    save_questions = True   # Boolean Flag | Change to False If any error in Csv
    # Reading the Csv File
    file_extension = (str(csv_file).split('.'))[-1]

    if(file_extension != 'csv'):
        alerts.append(('Error', "The file uploaded is not a CSV file."))
        return(alerts, False)

    try:
        reader = csv.DictReader(
            csv_file.read().decode('latin-1').encode('utf-8').decode('utf-8').splitlines())
        reader1, reader2 = tee(reader, 2)  # Making two iterables for iteration(Google This XD)
    except TypeError:
        alerts.append(('Error', "Bad CSV file"))
        return(alerts, False)

def get_converted_questions(assessmentpaper_id):
    assessmentpaper = models.LearnerPapers.objects.get(
        id=assessmentpaper_id)
    subjectIds = [] 
    for subject in assessmentpaper.subjects.all():
        subjectIds.append(subject.id)
    for question in assessmentpaper.questions.all():
        # quesDetail = QuestionSerializer(question).data
        
        tagIds = []
        for tag in question.linked_topics.all():
            tagIds.append(tag.id)
        chapter_obj = course_models.Chapter.objects.filter(subject__in=subjectIds, topics__in=tagIds)
        question_data = []
        # if user_answer:
            # user_mcq_answer = user_answer[0].user_mcq_answer.all()
        user_dict = dict(id=question.id, 
                    difficulty=question.difficulty, is_active=question.is_active, 
                    type_of_question=question.type_of_question, question_identifier=question.question_identifier,
                    subject=chapter_obj[0].subject.id)
        question_data.append(user_dict)
    return assessmentpaper, question_data

def get_learner_subject_chapters(user, examid, subjectid):
   
    chapter_objs = course_models.Chapter.objects.select_related("subject").prefetch_related(
            "topics", "hints").filter(subject__id=subjectid, show=True).values("id", "title").order_by('order')
    chapter_data = []
    learner_exam_obj = course_models.LearnerExams.objects.filter(exam=examid, user=user).last()
    for chapter in chapter_objs:
        # print ("chapteraa", examid, subjectid, chapter)
        if not learner_exam_obj:
            learner_chapter_obj = None
        else:
            learner_chapter_obj = content_models.LearnerExamPracticeChapters.objects.select_related("subject, chapter").filter(learner_exam=learner_exam_obj, chapter__id=chapter['id']).values("total_questions", "attempted", "percentage").last()
        
        if learner_chapter_obj:
            if learner_chapter_obj['percentage'] < 0:
                percentage = 0
            else:
                percentage = learner_chapter_obj['percentage']
            user_dict = dict(id=chapter['id'], title=chapter['title'],
                        total_questions=learner_chapter_obj['total_questions'], attempted=learner_chapter_obj['attempted'], 
                        percentage=percentage)
        else:
            user_dict = dict(id=chapter['id'], title=chapter['title'],
                        total_questions=None, attempted=None, 
                        percentage=None)
        chapter_data.append(user_dict)
    return chapter_data

def get_student_assessment_questions(student, assessmentpaper_id):
    assessmentpaper = models.LearnerPapers.objects.select_related("learner_exam"
    ).prefetch_related("subjects", "questions").get(id=assessmentpaper_id)

    answerpaper_obj = models.AnswerPaper.objects.select_related("user", 
    "assessment_paper").prefetch_related("question_markforreview", 
    "question_save_markforreview").filter(user=student, assessment_paper=assessmentpaper)

    remaining_time = 0
    subjectIds = assessmentpaper.subjects.values_list("id", flat=True)
    if (answerpaper_obj.count() == 0):
        questions = assessmentpaper.questions.all()
        questions_id = questions.values_list("id", flat=True)
        answerpaper = models.AnswerPaper.objects.create(
            user=student, assessment_paper=assessmentpaper, 
            attempt_order=1, attempted_date=datetime.datetime.today(), 
            question_order=list(questions_id))
        answerpaper.question_unanswered.add(*list(questions))
        answerpaper.save()
        question_list = models.Question.objects.prefetch_related("linked_topics", "tags", "contents", "contents__language", "languages").filter(id__in=questions)
        if assessmentpaper.pause_count > 0:
            remaining_time = assessmentpaper.remaining_time
        else:
            remaining_time = assessmentpaper.total_time*60
    elif (answerpaper_obj.filter(paper_complete=False).count() > 0):
        starttime = answerpaper_obj.last().start_time
        currenttime = timezone.now()
        if (currenttime >= (starttime + timedelta(minutes=int(assessmentpaper.total_time)))):
            if assessmentpaper.pause_count > 0:
                if assessmentpaper.remaining_time <= 0:
                    answerpaper = answerpaper_obj.last()
                    answerpaper.paper_complete = True
                    answerpaper.time_taken = assessmentpaper.total_time
                    answerpaper.save()
                    # question_list = models.Question.objects.filter(id=None)
                    question_list = []
                else:
                    question_id = answerpaper_obj.last().question_order
                    question_ids = re.sub("[^0-9,]", "", question_id)
                    question_ids = question_ids.split(',')
                    question_list = models.Question.objects.prefetch_related("linked_topics", "tags", "contents", "contents__language", "languages").filter(
                        id__in=question_ids)
                    time_spent = (currenttime - starttime).seconds
            
                    remaining_time = assessmentpaper.remaining_time
            else:
                answerpaper = answerpaper_obj.last()
                answerpaper.paper_complete = True
                answerpaper.time_taken = assessmentpaper.total_time
                answerpaper.save()
                # question_list = models.Question.objects.filter(id=None)
                question_list = []
        else:
            question_id = answerpaper_obj.last().question_order
            question_ids = re.sub("[^0-9,]", "", question_id)
            question_ids = question_ids.split(',')
            question_list = models.Question.objects.prefetch_related("linked_topics", "tags", "contents", "contents__language", "languages").filter(
                id__in=question_ids)
            time_spent = (currenttime - starttime).seconds
            
            if assessmentpaper.pause_count > 0:
                remaining_time = assessmentpaper.remaining_time
            else:
                remaining_time = assessmentpaper.total_time*60 - time_spent
    else:
        # question_list = models.Question.objects.filter(id=None)
        question_list = []

    question_newlist = []
    chapter_objs = course_models.Chapter.objects.select_related("subject").prefetch_related(
            "topics", "hints").filter(subject__in=subjectIds).values_list("id", flat=True)

    for question in question_list:
        
        # tagIds = question.linked_topics.values_list("id", flat=True)
        masterTagObj = models.ChapterMasterFTag.objects.filter(chapter__in=chapter_objs, questions=question).last()
        # print ("mastertagquestionjjaabb", question.id, masterTagObj.chapter.id, masterTagObj.chapter.subject.id)
        # chapter_obj = chapter_objs.filter(topics__in=tagIds)
        tmpquessubjectObj = models.TemporaryPaperSubjectQuestionDistribution.objects.filter(learner_paper=assessmentpaper, question=question).last()
        if not tmpquessubjectObj:
            tmpquessubjectObj = models.TemporaryPaperSubjectQuestionDistribution.objects.create(learner_paper=assessmentpaper, question=question)
            try:
                chapter_obj = course_models.Chapter.objects.select_related("subject").filter(id=masterTagObj.chapter.id).last()
            except:
                tagIds = question.linked_topics.values_list("id", flat=True)
                chapter_obj = course_models.Chapter.objects.select_related("subject").filter(topics__in=tagIds).last()
            tmpquessubjectObj.chapter = chapter_obj
            tmpquessubjectObj.subject = chapter_obj.subject
            tmpquessubjectObj.save()
        if tmpquessubjectObj and not tmpquessubjectObj.chapter:
            # tmpchapter_objs = course_models.Chapter.objects.select_related("subject").prefetch_related(
            # "topics", "hints").filter(subject__id=tmpquessubjectObj.subject.id).values_list("id", flat=True)
            # # print ("tmpchapter_objs", tmpchapter_objs)
            # masterTagObj = models.ChapterMasterFTag.objects.filter(chapter__in=tmpchapter_objs, questions=question).last()
            try:
                chapter_obj = course_models.Chapter.objects.select_related("subject").filter(id=masterTagObj.chapter.id).last()
            except:
                tagIds = question.linked_topics.values_list("id", flat=True)
                chapter_obj = course_models.Chapter.objects.select_related("subject").filter(topics__in=tagIds).last()
            tmpquessubjectObj.chapter = chapter_obj
            tmpquessubjectObj.save()
        contents = []
        options = []
        fillupoptions = []
        for content in question.contents.values("language__id", "language__text", "id", "text") :
            lang_dic = dict(id=content["language__id"], text=content["language__text"])
            content_dic = dict(id=content["id"], text=content["text"], language=lang_dic)
            contents.append(content_dic)
            if content["language__text"] == 'English' and question.type_of_question in ['mcq', 'mcc', 'assertion']:
                options_obj = models.McqTestCase.objects.filter(questioncontent__id=content["id"])
                for option in options_obj:
                    option_dic = dict(id=option.id, correct=option.correct, text=option.text)
                    options.append(option_dic)
            if content["language__text"] == 'English' and question.type_of_question == 'fillup_option':
                options_obj = models.FillUpWithOption.objects.filter(questioncontent__id=content["id"])
                for option in options_obj:
                    option_dic = dict(id=option.id, correct=option.correct, text=option.text)
                    fillupoptions.append(option_dic)

        if tmpquessubjectObj:
            user_dict = dict(id=question.id, contents=contents, options=options, fillupoptions=fillupoptions,
                    type_of_question=question.type_of_question,
                    subject=tmpquessubjectObj.subject.id, ideal_time=question.ideal_time)
        else:
            user_dict = dict(id=question.id, contents=contents, options=options, fillupoptions=fillupoptions,
                    type_of_question=question.type_of_question,
                    subject=masterTagObj.chapter.subject.id, ideal_time=question.ideal_time)
        question_newlist.append(user_dict)
    
    question_data = []
    mark_for_review_obj = answerpaper_obj.last().question_markforreview.all()
    question_save_markforreview_obj = answerpaper_obj.last().question_save_markforreview.all()
    
    user_answers = models.UserAnswer.objects.select_related('answer_paper', 'question','correct_fillup_answer').prefetch_related("correct_mcq_answer", "user_mcq_answer").filter(
            answer_paper=answerpaper_obj.last(), question__in=question_list)
    question_useranswer_map = {}
    for user_answer in user_answers:
        question_useranswer_map[user_answer.question.id] = user_answer

    for question in question_list:
        subject = None
        for ques in question_newlist:
            if ques['id'] == question.id:
                subject = ques['subject']
                break
        
        user_answer = question_useranswer_map.get(question.id)
        mark_for_review = question in mark_for_review_obj
        save_mark_for_review = question in question_save_markforreview_obj
        if user_answer:
            if (user_answer.type_of_answer == 'boolean'):
                user_boolean_answer = user_answer.user_boolean_answer
                user_dict = dict(question=question.id, attempt=True, s_review=save_mark_for_review, user_boolean_answer=user_boolean_answer, subject=subject)
                question_data.append(user_dict)
            if (user_answer.type_of_answer == 'mcq' or user_answer.type_of_answer == 'mcc' or user_answer.type_of_answer == 'assertion'):
                user_mcq_answer = user_answer.user_mcq_answer.all()
                user_dict = dict(question=question.id, attempt=True, s_review=save_mark_for_review, user_mcq_answer=[
                                 option.id for option in user_mcq_answer], subject=subject)
                question_data.append(user_dict)
            if (user_answer.type_of_answer == 'fillup' or user_answer.type_of_answer == 'numerical'):
                user_string_answer = user_answer.user_string_answer.strip()
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_string_answer=user_string_answer, subject=subject)
                question_data.append(user_dict)
            if (user_answer.type_of_answer == 'fillup_option'):
                user_fillup_option_answer = user_answer.user_fillup_option_answer
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_fillup_option_answer=user_fillup_option_answer.id, subject=subject)
                question_data.append(user_dict)
            if user_answer.type_of_answer == 'subjective':
                user_subjective_answer = user_answer.user_subjective_answer
                user_subjective_answer_image = user_answer[
                    0].user_subjective_answer_image.url if user_answer.user_subjective_answer_image else None
                user_subjective_answer_images = UserSubjectiveAnswerImageSerializer(user_answer.user_subjective_answer_images, many=True).data
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_subjective_answer=user_subjective_answer, subject=subject,  
                                 user_subjective_answer_image=user_subjective_answer_image, 
                                 user_subjective_answer_images=user_subjective_answer_images)
                question_data.append(user_dict)
        else:
            user_dict = dict(question=question.id,
                             attempt=False, review=mark_for_review, subject=subject)
            question_data.append(user_dict)
    sorted_question_list = sorted(question_newlist, key=lambda x: x['subject'])
    sorted_question_data = sorted(question_data, key=lambda x: x['subject'])
    return sorted_question_list, remaining_time, sorted_question_data

def get_student_assessment_report(user, assessmentpaper_id):
    assessmentpaper = models.LearnerPapers.objects.prefetch_related("subjects", "chapters", "questions"
    ).select_related("learner_exam").get(id=assessmentpaper_id)
    question_types = course_models.QuestionType.objects.values("negative_marks", "marks", "type_of_question").filter(exam__id=assessmentpaper.learner_exam.exam.id)
    question_type_dict = {}
    for question_type in question_types:
        question_type_dict[question_type["type_of_question"]] = {"negative_marks": question_type["negative_marks"], "marks": question_type["marks"]}
    
    answer_paper = models.AnswerPaper.objects.filter(
        user=user, assessment_paper=assessmentpaper).last()

    user_answer = models.UserAnswer.objects.filter(answer_paper=answer_paper).select_related(
            "answer_paper", "user", "question",  "correct_fillup_answer", "correct_boolean_answer", 
            "correct_string_answer").prefetch_related("user_mcq_answer", "correct_mcq_answer", "question__linked_topics")
   
    total_score = assessmentpaper.marks
    corrected = 0
    unchecked = 0
    score = 0
    
    subjects = assessmentpaper.subjects.all()
    allsubject_ids = subjects.values_list("id", flat=True)
    subject_data = {}
    chapter_data = {}
    incorrect_question_ids = []
    correct_question_ids = []
    skipped_question_ids = []
    
    tagIds =  assessmentpaper.questions.values_list("linked_topics", flat=True).all()

    if assessmentpaper.paper_type == 'paper':
        chapters = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(subject__in=subjects, topics__in=tagIds).distinct()
    else:
        chapterstmp = assessmentpaper.chapters.all()
        chaptrIds = [cp.id for cp in chapterstmp]
        chapters = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(id__in=chaptrIds).distinct()
        if not chapters:
            chapters = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(subject__in=allsubject_ids, topics__in=tagIds).distinct()
    
    subject_ids = []
    allchapter_ids = []
    incorrect_ques = []

    for subject in subjects:
        subject_data[subject.id] = dict(id=subject.id, title = subject.title, score=0, total=0, percentage=0, attempted=0, correct=0, incorrect=0, unchecked=0)

    for chapter in chapters:
        chapter_data[chapter["id"]] = dict(id=chapter["id"], title = chapter["title"], score=0, total=0, percentage=0, subject=chapter["subject__id"], attempted=0, correct=0, incorrect=0, unchecked=0)
        allchapter_ids.append(chapter["id"])
        subject_ids.append(chapter["subject__id"])
 
    # print ("chapterdaatta", chapter_data)
    # chapter_objs = course_models.Chapter.objects.select_related("subject").values("subject__id", "id").filter(subject__in=subject_ids, id__in=allchapter_ids)
    for data in user_answer:
        totalSubject = 0
        scoredSubject = 0
        uncheckedSubject = 0
        # attended_question_ids.append(data.question.id)
        ques_obj = data.question
        ques_dic = dict(id=ques_obj.id, type_of_question = ques_obj.type_of_question)

        tmpquessubjectObj = models.TemporaryPaperSubjectQuestionDistribution.objects.filter(learner_paper=assessmentpaper, question=ques_obj).last()
        chapter_obj = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(id=tmpquessubjectObj.chapter.id).last()
        subject_id = tmpquessubjectObj.subject.id
        chapter_id = chapter_obj["id"]
        if not chapter_obj["id"] in chapter_data:
            tmpTagIds = []
            tmpTagIds = ques_obj.linked_topics.values_list("id", flat=True).all()
            chapter_obj = chapters.values("subject__id", "id", "title").filter(topics__in=tmpTagIds).first()
            if not chapter_obj:
                tmpchapter_objs = course_models.Chapter.objects.select_related("subject").prefetch_related(
                "topics", "hints").filter(subject__in=subject_ids).values_list("id", flat=True)
                masterTagObj = models.ChapterMasterFTag.objects.filter(chapter__in=tmpchapter_objs, questions=ques_obj).last()
                chapter_obj = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(id=masterTagObj.chapter.id).last()
                # chapter_data[chapter_obj["id"]] = dict(id=chapter_obj["id"], title = chapter_obj["title"], score=0, total=0, percentage=0, subject=chapter_obj["subject__id"], attempted=0, correct=0, incorrect=0, unchecked=0)
            subject_id = chapter_obj["subject__id"]
            chapter_id = chapter_obj["id"]
        question_type_answers = question_type_dict.get(data.type_of_answer)
        if (data.type_of_answer == 'mcq' or data.type_of_answer == 'mcc' or data.type_of_answer == 'assertion'):
            user_mcq_answer = data.user_mcq_answer.all()
            tmp_mcq_answer  = user_mcq_answer
            user_mcq_answer = user_mcq_answer.values_list('id') 
            
            correct_mcq_answer = data.correct_mcq_answer.all().values_list('id')
            # case when all options of mcq match
            if set(user_mcq_answer) == set(correct_mcq_answer):
                corrected += 1
                correct_question_ids.append(ques_dic['id'])
                if data.type_of_answer == 'mcq':
                    score += question_type_answers["marks"]
                    totalSubject += question_type_answers["marks"]
                    scoredSubject += question_type_answers["marks"]
                elif data.type_of_answer == 'mcc':
                    score += question_type_answers["marks"]
                    totalSubject += question_type_answers["marks"]
                    scoredSubject += question_type_answers["marks"]
                else:
                    score += question_type_answers["marks"]
                    totalSubject += question_type_answers["marks"]
                    scoredSubject += question_type_answers["marks"]
            # case when any one of the options of mcq does not match
            else:
                ques_dic['user_answer'] = [
                                 option.id for option in tmp_mcq_answer]
                incorrect_ques.append(ques_dic)
                incorrect_question_ids.append(ques_dic['id'])
                if data.type_of_answer == 'mcq':
                    totalSubject += question_type_answers["marks"]
                    if question_type_answers["negative_marks"]:
                        score -= question_type_answers["negative_marks"]
                        scoredSubject -= question_type_answers["negative_marks"]
                elif data.type_of_answer == 'mcc':
                    totalSubject += question_type_answers["marks"]
                    if question_type_answers["negative_marks"]:
                        score -= question_type_answers["negative_marks"]
                        scoredSubject -= question_type_answers["negative_marks"]
                else:
                    totalSubject += question_type_answers["marks"]
                    if question_type_answers["negative_marks"]:
                        score -= question_type_answers["negative_marks"]
                        scoredSubject -= question_type_answers["negative_marks"]
        elif (data.type_of_answer == 'fillup'):
            user_string_answer = str(data.user_string_answer.strip())
            correct_fillup_answer = str(strip_tags(data.correct_fillup_answer.text).strip())
            totalSubject += question_type_answers["marks"]
            if user_string_answer.lower() == correct_fillup_answer.lower():
                corrected += 1
                correct_question_ids.append(ques_dic['id'])
                if data.type_of_answer == 'fillup':
                    score += question_type_answers["marks"]
                    scoredSubject += question_type_answers["marks"]
            else:
                ques_dic['user_answer'] = user_string_answer
                incorrect_ques.append(ques_dic)
                incorrect_question_ids.append(ques_dic['id'])
                if question_type_answers["negative_marks"]:
                    score -= question_type_answers["negative_marks"]
                    scoredSubject -= question_type_answers["negative_marks"]
        elif (data.type_of_answer == 'fillup_option'):
            user_fillup_option_answer = data.user_fillup_option_answer.id
            correct_fillup_option_answer = data.correct_fillup_option_answer.id
            totalSubject += question_type_answers["marks"]
            if user_fillup_option_answer == correct_fillup_option_answer:
                corrected += 1
                correct_question_ids.append(ques_dic['id'])
                score += question_type_answers["marks"]
                scoredSubject += question_type_answers["marks"]
            else:
                ques_dic['user_answer'] = user_fillup_option_answer
                incorrect_ques.append(ques_dic)
                incorrect_question_ids.append(ques_dic['id'])
                score -= question_type_answers["negative_marks"]
                scoredSubject -= question_type_answers["negative_marks"]
        elif (data.type_of_answer == 'boolean'):
            user_boolean_answer = str(data.user_boolean_answer)
            correct_boolean_answer = str(data.correct_boolean_answer.option)
            totalSubject += question_type_answers["marks"]
            if user_boolean_answer == correct_boolean_answer:
                corrected += 1
                correct_question_ids.append(ques_dic['id'])
                score += question_type_answers["marks"]
                scoredSubject += question_type_answers["marks"]
            else:
                ques_dic['user_answer'] = user_boolean_answer
                incorrect_ques.append(ques_dic)
                incorrect_question_ids.append(ques_dic['id'])
                score -= question_type_answers["negative_marks"]
                scoredSubject -= question_type_answers["negative_marks"]
                
        elif data.type_of_answer == 'numerical':
            user_string_answer = str(data.user_string_answer.strip())
            correct_string_answer = str(data.correct_string_answer.text)
            totalSubject += question_type_answers["marks"]
            if user_string_answer.lower() == correct_string_answer.lower():
                corrected += 1
                correct_question_ids.append(ques_dic['id'])
                score += question_type_answers["marks"]
                scoredSubject += question_type_answers["marks"]
            else:
                ques_dic['user_answer'] = user_string_answer
                incorrect_ques.append(ques_dic)
                incorrect_question_ids.append(ques_dic['id'])
                if question_type_answers["negative_marks"]:
                    score -= question_type_answers["negative_marks"]
                    scoredSubject -= question_type_answers["negative_marks"]
        elif data.type_of_answer == 'subjective':
            unchecked += 1
            uncheckedSubject += 1
    
        subject_data[subject_id]['score'] += scoredSubject
        subject_data[subject_id]['total'] += totalSubject
        subject_data[subject_id]['attempted'] += 1
        chapter_data[chapter_id]['score'] += scoredSubject
        chapter_data[chapter_id]['total'] += totalSubject
        chapter_data[chapter_id]['attempted'] += 1

        if scoredSubject > 0:
            subject_data[subject_id]['correct'] += 1
            chapter_data[chapter_id]['correct'] += 1
        elif uncheckedSubject > 0:
            subject_data[subject_id]['unchecked'] += 1
            chapter_data[chapter_id]['unchecked'] += 1
        else:
            subject_data[subject_id]['incorrect'] += 1
            chapter_data[chapter_id]['incorrect'] += 1
            
    all_question_ids = assessmentpaper.questions.values_list("id", flat=True).all()
    attended_question_ids = user_answer.values_list("question", flat=True)
    skipped_question_ids = list(set(all_question_ids) - set(attended_question_ids))
    
    finalSubjects = []
    for key, val in subject_data.items():
        if val['total'] == 0:
            continue
        try:
            percentage = (val['score'] * 100) / val['total']
        except:
            percentage = 0
        subject_data[key]['percentage'] = percentage
        finalSubjects.append(subject_data[key])

    finalChapters = []
    for key, val in chapter_data.items():
        if val['total'] == 0:
            continue
        try:
            percentage = (val['score'] * 100) / val['total']
        except:
            percentage = 0

        chapter_data[key]['percentage'] = percentage
        finalChapters.append(chapter_data[key])
    message = {}
    try:
        percentage = (score * 100) / total_score
    except:
        percentage = 0
    total_user_answers = len(user_answer)
    total_question_ids = len(all_question_ids)
    data = {
        "attempted": total_user_answers,
        "corrected": corrected,
        "skipped": total_question_ids - total_user_answers,
        "incorrected": (total_user_answers-unchecked) - corrected,
        "unchecked": unchecked,
        "totalquestion": total_question_ids,
        "score": score,
        "totalscore":  total_score,
        "percentage": percentage,
        "time_taken": answer_paper.time_taken,
        "subjects": finalSubjects,
        "chapters": finalChapters,
        "incorrect_questions": incorrect_ques,
        "all_question_ids": all_question_ids,
        "incorrect_question_ids": incorrect_question_ids,
        "correct_question_ids": correct_question_ids,
        "skipped_question_ids": skipped_question_ids,
        "message": message
    }
    return data

def get_leaderboard(exam_id, user):
    exam_obj = course_models.Exam.objects.get(id=int(exam_id))
    learner_exam_obj = course_models.LearnerExams.objects.filter(exam=exam_obj)
    ids  = []
    for learnerexam in learner_exam_obj:
        ids.append(learnerexam.id)
    learner_papers = models.LearnerPapers.objects.filter(learner_exam__in=ids, paper_type='paper', submitted=True)
    # print ("examobjaa", exam_obj, learner_papers)
    leaderboard_data = []
    for paper in learner_papers:
        count = 0
        # print ("useraa", paper.user.id, paper.user.profile.first_name)
        try:
            answer_paper_obj = models.AnswerPaper.objects.get(assessment_paper=int(paper.id))
        except:
            answer_paper_obj = None
        if not answer_paper_obj:
            try:
                data_dict = dict(userid=paper.user.id, name=paper.user.profile.first_name + ' ' + paper.user.profile.last_name, profile_img=None, learner_exam=paper.learner_exam.id, time_spent=0, score=paper.score, total_marks=paper.marks, total_question=len(paper.questions.all()))
            except:
                data_dict = dict(userid=paper.user.id, name=paper.user.profile.first_name, profile_img=None, learner_exam=paper.learner_exam.id, time_spent=0, score=paper.score, total_marks=paper.marks, total_question=len(paper.questions.all()))
        else:
            try:
                data_dict = dict(userid=paper.user.id, name=paper.user.profile.first_name + ' ' + paper.user.profile.last_name, profile_img=None, learner_exam=paper.learner_exam.id, time_spent=answer_paper_obj.time_taken, score=paper.score, total_marks=paper.marks, total_question=len(paper.questions.all()))
            except:
                data_dict = dict(userid=paper.user.id, name=paper.user.profile.first_name, profile_img=None, learner_exam=paper.learner_exam.id, time_spent=answer_paper_obj.time_taken, score=paper.score, total_marks=paper.marks, total_question=len(paper.questions.all()))
        
        for i in range(0, len(leaderboard_data)):
            if leaderboard_data[i]['userid'] == data_dict['userid']:
                count += 1
                leaderboard_data[i]['time_spent'] += data_dict['time_spent']
                leaderboard_data[i]['score'] += data_dict['score']
                leaderboard_data[i]['total_marks'] += data_dict['total_marks']
                leaderboard_data[i]['total_question'] += data_dict['total_question']

        if count == 0:
            leaderboard_data.append(data_dict)
    sorted_data = sorted(leaderboard_data, key=lambda x: x['score'], reverse=True)
    top_sorted_data = sorted(leaderboard_data, key=lambda x: x['score'], reverse=True)[:50]
    my_data = []
    for i in range(0, len(sorted_data)):
        if sorted_data[i]['userid'] == user.id:
            sorted_data[i]['rank'] = i+1
            my_data = sorted_data[i]
    return top_sorted_data, my_data

def get_assessment_answers_history(student, assessmentpaper_id):
    assessmentpaper = models.LearnerPapers.objects.get(
        id=assessmentpaper_id)
    answerpaper_obj = models.AnswerPaper.objects.filter(
        user=student, assessment_paper=assessmentpaper)
    
    subjectIds = []
    # for subject in assessmentpaper.subjects.all():
    #     subjectIds.append(subject.id)
    
    subjectIds.extend(assessmentpaper.subjects.values_list("id", flat=True).all())
    
    if (len(answerpaper_obj.filter(paper_complete=True)) > 0):
        question_id = answerpaper_obj.last().question_order
        question_ids = re.sub("[^0-9,]", "", question_id)
        question_ids = question_ids.split(',')
        question_list = models.Question.objects.filter(
            id__in=question_ids)
    else:
        question_list = models.Question.objects.filter(id=None)

    question_newlist = []
    for question in question_list:
        # quesDetail = QuestionSerializer(question).data
        tagIds = []
        # for tag in question.linked_topics.all():
        #     tagIds.append(tag.id)
        tagIds.extend(question.linked_topics.values_list("id", flat=True).all())
        # chapter_obj = course_models.Chapter.objects.filter(subject__in=subjectIds, topics__in=tagIds)
        chapter_objs = course_models.Chapter.objects.select_related("subject").prefetch_related(
            "topics", "hints").filter(subject__in=subjectIds).values_list("id", flat=True)
        masterTagObj = models.ChapterMasterFTag.objects.filter(chapter__in=chapter_objs, questions=question).last()
        
        contents = []
        for content in question.contents.all():
            lang_obj = models.QuestionLanguage.objects.get(id=int(content.language.id))
            lang_dic = dict(id=lang_obj.id, text=lang_obj.text)
            content_dic = dict(id=content.id, text=content.text, language=lang_dic)
            contents.append(content_dic)
        tags = []
        for tag in question.tags.all():
            tag_obj = models.QuestionTag.objects.get(id=int(tag.id))
            tag_dic = dict(id=tag_obj.id, text=tag_obj.text)
            tags.append(tag_dic)
        user_dict = dict(id=question.id, contents=contents,
                    difficulty=question.difficulty, is_active=question.is_active, 
                    type_of_question=question.type_of_question, question_identifier=question.question_identifier,
                    subject=masterTagObj.chapter.subject.id, tags=tags, ideal_time=question.ideal_time)
        question_newlist.append(user_dict)
    # print ("question_newlist", question_newlist)
    question_data = []
    mark_for_review_obj = answerpaper_obj.last().question_markforreview.all()
    question_save_markforreview_obj = answerpaper_obj.last(
    ).question_save_markforreview.all()
    for question in question_list:
        subject = None
        # for ques in question_newlist:
        #     if ques['id'] == question.id:
        #         subject = ques['subject']
        shared_item = [element for element in question_newlist if element['id'] == question.id]
        subject = shared_item[0]['subject']
        user_answer = models.UserAnswer.objects.filter(
            answer_paper=answerpaper_obj.last(), question=question)
        mark_for_review = True if(question in mark_for_review_obj) else False
        save_mark_for_review = True if(
            question in question_save_markforreview_obj) else False
        if user_answer:
            if (user_answer[0].type_of_answer == 'boolean'):
                user_boolean_answer = user_answer[0].user_boolean_answer
                for i in range(0, len(question_newlist)):
                    if question_newlist[i]['id'] == question.id:
                        question_newlist[i]['user_answer'] = user_boolean_answer
                user_dict = dict(question=question.id, attempt=True, s_review=save_mark_for_review, user_boolean_answer=user_boolean_answer, subject=subject)
                question_data.append(user_dict)
            if (user_answer[0].type_of_answer == 'mcq' or user_answer[0].type_of_answer == 'mcc' or user_answer[0].type_of_answer == 'assertion'):
                user_mcq_answer = user_answer[0].user_mcq_answer.all()
                for i in range(0, len(question_newlist)):
                    if question_newlist[i]['id'] == question.id:
                        question_newlist[i]['user_answer'] = [
                                 option.id for option in user_mcq_answer]
                user_dict = dict(question=question.id, attempt=True, s_review=save_mark_for_review, user_mcq_answer=[
                                 option.id for option in user_mcq_answer], subject=subject)
                question_data.append(user_dict)
            if (user_answer[0].type_of_answer == 'fillup' or user_answer[0].type_of_answer == 'numerical'):
                user_string_answer = user_answer[0].user_string_answer.strip()
                for i in range(0, len(question_newlist)):
                    if question_newlist[i]['id'] == question.id:
                        question_newlist[i]['user_answer'] = user_string_answer
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_string_answer=user_string_answer, subject=subject)
                question_data.append(user_dict)
            if (user_answer[0].type_of_answer == 'fillup_option'):
                user_fillup_option_answer = user_answer[0].user_fillup_option_answer
                for i in range(0, len(question_newlist)):
                    if question_newlist[i]['id'] == question.id:
                        question_newlist[i]['user_answer'] = user_fillup_option_answer.id
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_fillup_option_answer=user_fillup_option_answer.id, subject=subject)
                question_data.append(user_dict)
            if user_answer[0].type_of_answer == 'subjective':
                user_subjective_answer = user_answer[0].user_subjective_answer
                for i in range(0, len(question_newlist)):
                    if question_newlist[i]['id'] == question.id:
                        question_newlist[i]['user_answer'] = user_subjective_answer
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_subjective_answer=user_subjective_answer, subject=subject)
                question_data.append(user_dict)
        else:
            user_dict = dict(question=question.id,
                             attempt=False, review=mark_for_review, subject=subject)
            question_data.append(user_dict)
    sorted_question_list = sorted(question_newlist, key=lambda x: x['subject'])
    sorted_question_data = sorted(question_data, key=lambda x: x['subject'])
    return sorted_question_list, sorted_question_data
    
def get_mentor_batch_paper_assessment_questions(student, assessmentpaper_id):
    assessmentpaper = models.MentorPapers.objects.get(
        id=assessmentpaper_id)
    answerpaper_obj = models.MentorPaperAnswerPaper.objects.filter(
        user=student, mentor_paper=assessmentpaper)
    remaining_time = 0
    subjectIds = []
    subjects = assessmentpaper.subjects.all()
    subjectIds = [subject.id for subject in subjects]
    if (len(answerpaper_obj) == 0):
        questions = assessmentpaper.questions.all()
        questions_id = [question.id for question in questions]
        # print ("questions ids", questions_id)
        answerpaper = models.MentorPaperAnswerPaper.objects.create(
            user=student, mentor_paper=assessmentpaper)
        answerpaper.question_order = questions_id
        answerpaper.attempt_order = 1
        answerpaper.attempted_date = datetime.datetime.today()
        answerpaper.question_unanswered.add(*list(questions))
        answerpaper.save()
        question_list = models.Question.objects.filter(id__in=questions_id)
        if answerpaper.pause_count > 0:
            remaining_time = answerpaper.remaining_time
        else:
            remaining_time = assessmentpaper.total_time*60
        # print ("question_list", question_list, remaining_time)
    elif (len(answerpaper_obj.filter(paper_complete=False)) > 0):
        # print ("answerpaper objaaa", answerpaper_obj)
        starttime = answerpaper_obj.last().start_time
        currenttime = timezone.now()
        if (currenttime >= (starttime + timedelta(minutes=int(assessmentpaper.total_time)))):
            if answerpaper_obj.last().pause_count > 0:
                if answerpaper_obj.last().remaining_time <= 0:
                    answerpaper = answerpaper_obj.last()
                    answerpaper.paper_complete = True
                    answerpaper.time_taken = assessmentpaper.total_time
                    answerpaper.save()
                    question_list = models.Question.objects.filter(id=None)
                else:
                    answerpaper = answerpaper_obj.last()
                    question_id = answerpaper_obj.last().question_order
                    question_ids = re.sub("[^0-9,]", "", question_id)
                    question_ids = question_ids.split(',')
                    question_list = models.Question.objects.filter(
                        id__in=question_ids)
                    time_spent = (currenttime - starttime).seconds
                    remaining_time = answerpaper.remaining_time
            else:
                answerpaper = answerpaper_obj.last()
                answerpaper.paper_complete = True
                answerpaper.time_taken = assessmentpaper.total_time
                answerpaper.save()
                question_list = models.Question.objects.filter(id=None)
        else:
            answerpaper = answerpaper_obj.last()
            question_id = answerpaper_obj.last().question_order
            question_ids = re.sub("[^0-9,]", "", question_id)
            question_ids = question_ids.split(',')
            question_list = models.Question.objects.filter(
                id__in=question_ids)
            time_spent = (currenttime - starttime).seconds
            
            if answerpaper.pause_count > 0:
                remaining_time = answerpaper.remaining_time
            else:
                remaining_time = assessmentpaper.total_time*60 - time_spent
        # print ("question_list", question_list, remaining_time)
    else:
        question_list = models.Question.objects.filter(id=None)

    question_newlist = []
    chapter_objs = course_models.Chapter.objects.select_related("subject").prefetch_related(
            "topics", "hints").filter(subject__in=subjectIds).values_list("id", flat=True)
    for question in question_list:
        # masterTagObj = models.ChapterMasterFTag.objects.filter(chapter__in=chapter_objs, questions=question).last()
        # tmpquessubjectObj, _ = models.TemporaryPaperSubjectQuestionDistribution.objects.get_or_create(mentor_paper=assessmentpaper, question=question)
        # if not tmpquessubjectObj.chapter:
        #     chapter_obj = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(id=masterTagObj.chapter.id).last()
        #     tmpquessubjectObj.chapter_id = chapter_obj['id']
        #     tmpquessubjectObj.subject_id = chapter_obj['subject__id']
        #     tmpquessubjectObj.save()
        
        masterTagObj = models.ChapterMasterFTag.objects.filter(chapter__in=chapter_objs, questions=question).last()
        tmpquessubjectObj = models.TemporaryPaperSubjectQuestionDistribution.objects.filter(mentor_paper=assessmentpaper, question=question).last()
        if not tmpquessubjectObj:
            tmpquessubjectObj = models.TemporaryPaperSubjectQuestionDistribution.objects.create(mentor_paper=assessmentpaper, question=question)
            try:
                chapter_obj = course_models.Chapter.objects.select_related("subject").filter(id=masterTagObj.chapter.id).last()
            except:
                tagIds = question.linked_topics.values_list("id", flat=True)
                chapter_obj = course_models.Chapter.objects.select_related("subject").filter(topics__in=tagIds).last()
            tmpquessubjectObj.chapter = chapter_obj
            tmpquessubjectObj.subject = chapter_obj.subject
            tmpquessubjectObj.save()
        if tmpquessubjectObj and not tmpquessubjectObj.chapter:
            try:
                chapter_obj = course_models.Chapter.objects.select_related("subject").filter(id=masterTagObj.chapter.id).last()
            except:
                tagIds = question.linked_topics.values_list("id", flat=True)
                chapter_obj = course_models.Chapter.objects.select_related("subject").filter(topics__in=tagIds).last()
            tmpquessubjectObj.chapter = chapter_obj
            tmpquessubjectObj.save()
        contents = []
        options = []
        fillupoptions = []
        # for content in question.contents.all():
        #     lang_obj = models.QuestionLanguage.objects.get(id=int(content.language.id))
        #     lang_dic = dict(id=lang_obj.id, text=lang_obj.text)
        #     content_dic = dict(id=content.id, text=content.text, language=lang_dic)
        #     contents.append(content_dic)
        for content in question.contents.values("language__id", "language__text", "id", "text") :
            lang_dic = dict(id=content["language__id"], text=content["language__text"])
            content_dic = dict(id=content["id"], text=content["text"], language=lang_dic)
            contents.append(content_dic)
            if content["language__text"] == 'English' and question.type_of_question in ['mcq', 'mcc', 'assertion']:
                options_obj = models.McqTestCase.objects.filter(questioncontent__id=content["id"])
                for option in options_obj:
                    option_dic = dict(id=option.id, correct=option.correct, text=option.text)
                    options.append(option_dic)
            if content["language__text"] == 'English' and question.type_of_question == 'fillup_option':
                options_obj = models.FillUpWithOption.objects.filter(questioncontent__id=content["id"])
                for option in options_obj:
                    option_dic = dict(id=option.id, correct=option.correct, text=option.text)
                    fillupoptions.append(option_dic)
        if tmpquessubjectObj:
            user_dict = dict(id=question.id, contents=contents, options=options, fillupoptions=fillupoptions,
                        type_of_question=question.type_of_question,
                        subject=tmpquessubjectObj.subject.id, ideal_time=question.ideal_time)
        else:
            user_dict = dict(id=question.id, contents=contents, options=options, fillupoptions=fillupoptions,
                        type_of_question=question.type_of_question,
                        subject=masterTagObj.chapter.subject.id, ideal_time=question.ideal_time)
        question_newlist.append(user_dict)
    # print ("question_newlist", question_newlist)
    question_data = []
    mark_for_review_obj = answerpaper_obj.last().question_markforreview.all()
    # print ("mark_for_review_obj", mark_for_review_obj)
    question_save_markforreview_obj = answerpaper_obj.last(
    ).question_save_markforreview.all()
    for question in question_list:
        subject = None
        for ques in question_newlist:
            if ques['id'] == question.id:
                subject = ques['subject']
                break
        user_answer = models.UserAnswerMentorPaper.objects.filter(
            answer_paper=answerpaper_obj.last(), question=question)
        # print("useranswer", user_answer)
        mark_for_review = True if(question in mark_for_review_obj) else False
        save_mark_for_review = True if(
            question in question_save_markforreview_obj) else False
        if user_answer:
            if (user_answer[0].type_of_answer == 'boolean'):
                user_boolean_answer = user_answer[0].user_boolean_answer
                user_dict = dict(question=question.id, attempt=True, s_review=save_mark_for_review, user_boolean_answer=user_boolean_answer, subject=subject)
                question_data.append(user_dict)
            if (user_answer[0].type_of_answer == 'mcq' or user_answer[0].type_of_answer == 'mcc' or user_answer[0].type_of_answer == 'assertion'):
                user_mcq_answer = user_answer[0].user_mcq_answer.all()
                user_dict = dict(question=question.id, attempt=True, s_review=save_mark_for_review, user_mcq_answer=[
                                 option.id for option in user_mcq_answer], subject=subject)
                question_data.append(user_dict)
            if (user_answer[0].type_of_answer == 'fillup' or user_answer[0].type_of_answer == 'numerical'):
                user_string_answer = user_answer[0].user_string_answer.strip()
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_string_answer=user_string_answer, subject=subject)
                question_data.append(user_dict)
            if (user_answer[0].type_of_answer == 'fillup_option'):
                user_fillup_option_answer = user_answer[0].user_fillup_option_answer
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_fillup_option_answer=user_fillup_option_answer.id, subject=subject)
                question_data.append(user_dict)
            if user_answer[0].type_of_answer == 'subjective':
                user_subjective_answer = user_answer[0].user_subjective_answer
                user_subjective_answer_image = user_answer[
                    0].user_subjective_answer_image.url if user_answer[0].user_subjective_answer_image else None
                user_subjective_answer_images = UserSubjectiveAnswerImageSerializer(user_answer[0].user_subjective_answer_images, many=True).data
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_subjective_answer=user_subjective_answer, subject=subject,  user_subjective_answer_image=user_subjective_answer_image, user_subjective_answer_images=user_subjective_answer_images)
                question_data.append(user_dict)
        else:
            user_dict = dict(question=question.id,
                             attempt=False, review=mark_for_review, subject=subject)
            question_data.append(user_dict)
    sorted_question_list = sorted(question_newlist, key=lambda x: x['subject'])
    sorted_question_data = sorted(question_data, key=lambda x: x['subject'])
    return sorted_question_list, remaining_time, sorted_question_data

def get_mentor_paper_student_assessment_report(user, assessmentpaper_id):
    assessmentpaper = models.MentorPapers.objects.get(
        id=assessmentpaper_id)
    # answer_paper = quiz_models.AnswerPaper.objects.get(
    #     user=user, assessment_paper=assessmentpaper)
    exam_obj = course_models.Exam.objects.get(id=int(assessmentpaper.exam.id))
    # print ("examobj", exam_obj)
    try:
        mcq_linked_obj = course_models.QuestionType.objects.get(exam=exam_obj, type_of_question='mcq')
    except:
        mcq_linked_obj = None
    # print ("mcq_linked_obj", mcq_linked_obj)
    try:
        mcc_linked_obj = course_models.QuestionType.objects.get(exam=exam_obj, type_of_question='mcc')
    except:
        mcc_linked_obj = None
    try:
        fillup_linked_obj = course_models.QuestionType.objects.get(exam=exam_obj, type_of_question='fillup')
    except:
        fillup_linked_obj = None
    try:
        numerical_linked_obj = course_models.QuestionType.objects.get(exam=exam_obj, type_of_question='numerical')
    except:
        numerical_linked_obj = None
    try:
        fillupoption_linked_obj = course_models.QuestionType.objects.get(exam=exam_obj, type_of_question='fillup_option')
    except:
        fillupoption_linked_obj = None
    try:
        boolean_linked_obj = course_models.QuestionType.objects.get(exam=exam_obj, type_of_question='boolean')
    except:
        boolean_linked_obj = None
    try:
        assertion_linked_obj = course_models.QuestionType.objects.get(exam=exam_obj, type_of_question='assertion')
    except:
        assertion_linked_obj = None
    answer_paper = models.MentorPaperAnswerPaper.objects.filter(
        user=user, mentor_paper=assessmentpaper).last()
    user_answer = models.UserAnswerMentorPaper.objects.filter(
        answer_paper=answer_paper)
    # print ("answer_paper", answer_paper, user_answer)
    question_id = answer_paper.question_order
    question_ids = re.sub("[^0-9,]", "", question_id)
    question_ids = question_ids.split(',')
    total_score = assessmentpaper.marks
    corrected = 0
    unchecked = 0
    score = 0
    allsubject_ids = []
    subjects = assessmentpaper.subjects.all()
    allsubject_ids = [subject.id for subject in subjects]
    subject_ids = []
    # chapter_ids = []
    # subject_data = []
    # chapter_data = []
    subject_data = {}
    chapter_data = {}
    incorrect_question_ids = []
    correct_question_ids = []
    skipped_question_ids = []
    all_question_ids = []
    attended_question_ids = []
    all_question_ids.extend(assessmentpaper.questions.values_list("id", flat=True).all())
    tagIds =  assessmentpaper.questions.values_list("linked_topics", flat=True).all()
    # allques_obj = models.Question.objects.filter(id__in=all_question_ids)
    # tagIds = []
    # tagIds.extend(allques_obj.values_list("linked_topics", flat=True).all())
    # chapters = course_models.Chapter.objects.filter(subject__in=allsubject_ids, topics__in=tagIds).distinct()
    # if assessmentpaper.paper_type == 'paper':
    #     chapters = course_models.Chapter.objects.filter(subject__in=allsubject_ids, topics__in=tagIds).distinct()
    # else:
    #     chapters = assessmentpaper.chapters.all()
    #     if not chapters:
    #         chapters = course_models.Chapter.objects.filter(subject__in=allsubject_ids, topics__in=tagIds).distinct()
    # subject_ids.extend(chapters.values_list("subject", flat=True))
   
    if assessmentpaper.paper_type == 'paper':
        chapters = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(subject__in=subjects, topics__in=tagIds).distinct()
    else:
        chapterstmp = assessmentpaper.chapters.all()
        chaptrIds = [cp.id for cp in chapterstmp]
        chapters = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(id__in=chaptrIds).distinct()
        if not chapters:
            chapters = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(subject__in=allsubject_ids, topics__in=tagIds).distinct()
    # subjects = course_models.Subject.objects.filter(
    #     id__in=subject_ids)
    incorrect_ques = []
    # unusedChapters = []
    # unusedSubjects = []
    
    for subject in subjects:
        subject_data[subject.id] = dict(id=subject.id, title = subject.title, score=0, total=0, percentage=0, attempted=0, correct=0, incorrect=0, unchecked=0)

    for chapter in chapters:
        chapter_data[chapter["id"]] = dict(id=chapter["id"], title = chapter["title"], score=0, total=0, percentage=0, subject=chapter["subject__id"], attempted=0, correct=0, incorrect=0, unchecked=0)
        subject_ids.append(chapter["subject__id"])
 
    attended_question_ids.extend(user_answer.values_list("question", flat=True))
    for data in user_answer:
        totalSubject = 0
        scoredSubject = 0
        uncheckedSubject = 0

        ques_obj = data.question
        ques_dic = dict(id=ques_obj.id, type_of_question = ques_obj.type_of_question)

        tmpquessubjectObj = models.TemporaryPaperSubjectQuestionDistribution.objects.filter(mentor_paper=assessmentpaper, question=ques_obj).last()
        chapter_obj = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(id=tmpquessubjectObj.chapter.id).last()
        
        subject_id = tmpquessubjectObj.subject.id
        chapter_id = chapter_obj["id"]

        # ques_obj = models.Question.objects.get(id=data.question.id)
        # ques_dic = dict(id=ques_obj.id, type_of_question = ques_obj.type_of_question)
        # tagIds = []
        # tagIds = ques_obj.linked_topics.values_list("id", flat=True).all()
        # chapter_obj = chapters.filter(topics__in=tagIds).first()
        # if not chapter_obj:
        #     tmpchapter_objs = course_models.Chapter.objects.select_related("subject").prefetch_related(
        #     "topics", "hints").filter(subject__in=subject_ids).values_list("id", flat=True)
        #     masterTagObj = models.ChapterMasterFTag.objects.filter(chapter__in=tmpchapter_objs, questions=ques_obj).last()
        #     chapter_obj = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(id=masterTagObj.chapter.id).last()
        #     chapter_data[chapter_obj["id"]] = dict(id=chapter_obj["id"], title = chapter_obj["title"], score=0, total=0, percentage=0, subject=chapter_obj["subject__id"], attempted=0, correct=0, incorrect=0, unchecked=0)
        # subject_id = chapter_obj["subject__id"]
        # chapter_id = chapter_obj["id"]
        if (data.type_of_answer == 'mcq' or data.type_of_answer == 'mcc' or data.type_of_answer == 'assertion'):
            user_mcq_answer = data.user_mcq_answer.all().values_list('id')
            tmp_user_mcq_ans = data.user_mcq_answer.all()
            correct_mcq_answer = data.correct_mcq_answer.all().values_list('id')
            if set(user_mcq_answer) == set(correct_mcq_answer):
                corrected += 1
                correct_question_ids.append(ques_dic['id'])
                if data.type_of_answer == 'mcq':
                    score += mcq_linked_obj.marks
                    totalSubject += mcq_linked_obj.marks
                    scoredSubject += mcq_linked_obj.marks
                elif data.type_of_answer == 'mcc':
                    score += mcc_linked_obj.marks
                    totalSubject += mcc_linked_obj.marks
                    scoredSubject += mcc_linked_obj.marks
                else:
                    score += assertion_linked_obj.marks
                    totalSubject += assertion_linked_obj.marks
                    scoredSubject += assertion_linked_obj.marks
            else:
                ques_dic['user_answer'] = [
                                 option.id for option in tmp_user_mcq_ans]
                incorrect_ques.append(ques_dic)
                incorrect_question_ids.append(ques_dic['id'])
                if data.type_of_answer == 'mcq':
                    totalSubject += mcq_linked_obj.marks
                    if mcq_linked_obj.negative_marks:
                        score -= mcq_linked_obj.negative_marks
                        scoredSubject -= mcq_linked_obj.negative_marks
                elif data.type_of_answer == 'mcc':
                    totalSubject += mcc_linked_obj.marks
                    if mcc_linked_obj.negative_marks:
                        score -= mcc_linked_obj.negative_marks
                        scoredSubject -= mcc_linked_obj.negative_marks
                else:
                    totalSubject += assertion_linked_obj.marks
                    if assertion_linked_obj.negative_marks:
                        score -= assertion_linked_obj.negative_marks
                        scoredSubject -= assertion_linked_obj.negative_marks
        elif (data.type_of_answer == 'fillup'):
            user_string_answer = str(data.user_string_answer.strip())
            correct_fillup_answer = str(strip_tags(data.correct_fillup_answer.text).strip())
            totalSubject += fillup_linked_obj.marks
            if user_string_answer.lower() == correct_fillup_answer.lower():
                corrected += 1
                correct_question_ids.append(ques_dic['id'])
                if data.type_of_answer == 'fillup':
                    score += fillup_linked_obj.marks
                    scoredSubject += fillup_linked_obj.marks
            else:
                ques_dic['user_answer'] = user_string_answer
                incorrect_ques.append(ques_dic)
                incorrect_question_ids.append(ques_dic['id'])
                if fillup_linked_obj.negative_marks:
                    score -= fillup_linked_obj.negative_marks
                    scoredSubject -= fillup_linked_obj.negative_marks
        elif (data.type_of_answer == 'fillup_option'):
            user_fillup_option_answer = data.user_fillup_option_answer.id
            correct_fillup_option_answer = data.correct_fillup_option_answer.id
            totalSubject += fillupoption_linked_obj.marks
            if user_fillup_option_answer == correct_fillup_option_answer:
                corrected += 1
                correct_question_ids.append(ques_dic['id'])
                score += fillupoption_linked_obj.marks
                scoredSubject += fillupoption_linked_obj.marks
            else:
                ques_dic['user_answer'] = user_fillup_option_answer
                incorrect_ques.append(ques_dic)
                incorrect_question_ids.append(ques_dic['id'])
                score -= fillupoption_linked_obj.negative_marks
                scoredSubject -= fillupoption_linked_obj.negative_marks
        elif (data.type_of_answer == 'boolean'):
            user_boolean_answer = str(data.user_boolean_answer)
            correct_boolean_answer = str(data.correct_boolean_answer.option)
            totalSubject += boolean_linked_obj.marks
            if user_boolean_answer == correct_boolean_answer:
                corrected += 1
                correct_question_ids.append(ques_dic['id'])
                score += boolean_linked_obj.marks
                scoredSubject += boolean_linked_obj.marks
            else:
                ques_dic['user_answer'] = user_boolean_answer
                incorrect_ques.append(ques_dic)
                incorrect_question_ids.append(ques_dic['id'])
                score -= boolean_linked_obj.negative_marks
                scoredSubject -= boolean_linked_obj.negative_marks
                
        elif data.type_of_answer == 'numerical':
            user_string_answer = str(data.user_string_answer.strip())
            correct_string_answer = str(data.correct_string_answer.text)
            totalSubject += numerical_linked_obj.marks
            if user_string_answer.lower() == correct_string_answer.lower():
                corrected += 1
                correct_question_ids.append(ques_dic['id'])
                score += numerical_linked_obj.marks
                scoredSubject += numerical_linked_obj.marks
            else:
                ques_dic['user_answer'] = user_string_answer
                incorrect_ques.append(ques_dic)
                incorrect_question_ids.append(ques_dic['id'])
                if numerical_linked_obj.negative_marks:
                    score -= numerical_linked_obj.negative_marks
                    scoredSubject -= numerical_linked_obj.negative_marks
        elif data.type_of_answer == 'subjective':
            unchecked += 1
            uncheckedSubject += 1
        # for i in range(0, len(subject_data)):
        #     if subject_data[i]['id'] == subject_id:
        #         subject_data[i]['score'] += scoredSubject
        #         subject_data[i]['total'] += totalSubject
        #         subject_data[i]['attempted'] += 1
        #         if scoredSubject > 0:
        #             subject_data[i]['correct'] += 1
        #         elif uncheckedSubject > 0:
        #             subject_data[i]['unchecked'] += 1
        #         else:
        #             subject_data[i]['incorrect'] += 1
        # for i in range(0, len(chapter_data)):
        #     if chapter_data[i]['id'] == chapter_id:
        #         chapter_data[i]['score'] += scoredSubject
        #         chapter_data[i]['total'] += totalSubject
        #         chapter_data[i]['attempted'] += 1
        #         if scoredSubject > 0:
        #             chapter_data[i]['correct'] += 1
        #         elif uncheckedSubject > 0:
        #             chapter_data[i]['unchecked'] += 1
        #         else:
        #             chapter_data[i]['incorrect'] += 1
    

        subject_data[subject_id]['score'] += scoredSubject
        subject_data[subject_id]['total'] += totalSubject
        subject_data[subject_id]['attempted'] += 1
        chapter_data[chapter_id]['score'] += scoredSubject
        chapter_data[chapter_id]['total'] += totalSubject
        chapter_data[chapter_id]['attempted'] += 1

        if scoredSubject > 0:
            subject_data[subject_id]['correct'] += 1
            chapter_data[chapter_id]['correct'] += 1
        elif uncheckedSubject > 0:
            subject_data[subject_id]['unchecked'] += 1
            chapter_data[chapter_id]['unchecked'] += 1
        else:
            subject_data[subject_id]['incorrect'] += 1
            chapter_data[chapter_id]['incorrect'] += 1
    # for i in range(0, len(subject_data)):
    #     if subject_data[i]['total'] == 0:
    #         unusedSubjects.append(subject_data[i]['id'])
    #         continue
    #     try:
    #         percentage = (subject_data[i]['score'] * 100) / subject_data[i]['total']
    #     except:
    #         percentage = 0
    #     subject_data[i]['percentage'] = percentage
    # for i in range(0, len(chapter_data)):
    #     if chapter_data[i]['total'] == 0:
    #         unusedChapters.append(chapter_data[i]['id'])
    #         continue
    #     try:
    #         percentage = (chapter_data[i]['score'] * 100) / chapter_data[i]['total']
    #     except:
    #         percentage = 0
    #     chapter_data[i]['percentage'] = percentage
    # finalChapters = [x for x in chapter_data if x['id'] not in unusedChapters]
    # finalSubjects = [x for x in subject_data if x['id'] not in unusedSubjects]
    # message = {}
    # try:
    #     percentage = (score * 100) / total_score
    # except:
    #     percentage = 0
    finalSubjects = []
    for key, val in subject_data.items():
        if val['total'] == 0:
            continue
        try:
            percentage = (val['score'] * 100) / val['total']
        except:
            percentage = 0
        subject_data[key]['percentage'] = percentage
        finalSubjects.append(subject_data[key])

    finalChapters = []
    for key, val in chapter_data.items():
        if val['total'] == 0:
            continue
        try:
            percentage = (val['score'] * 100) / val['total']
        except:
            percentage = 0

        chapter_data[key]['percentage'] = percentage
        finalChapters.append(chapter_data[key])
    
    message = {}
    try:
        percentage = (score * 100) / total_score
    except:
        percentage = 0
    # total_user_answers = len(user_answer)
    # total_question_ids = len(all_question_ids)
    skipped_question_ids = list(set(all_question_ids) - set(attended_question_ids))
    profileObj = profile_models.Profile.objects.get(user=user)
    try:
        full_name = profileObj.first_name + ' ' + profileObj.last_name
    except:
        full_name = profileObj.first_name
    data = {
        "attempted": len(user_answer),
        "corrected": corrected,
        "skipped": len(assessmentpaper.questions.all()) - len(user_answer),
        "incorrected": (len(user_answer)-unchecked) - corrected,
        "unchecked": unchecked,
        "totalquestion": len(assessmentpaper.questions.all()),
        "score": score,
        "full_name": full_name,
        "totalscore":  total_score,
        "percentage": percentage,
        "time_taken": answer_paper.time_taken,
        "subjects": finalSubjects,
        "chapters": finalChapters,
        "incorrect_questions": incorrect_ques,
        "incorrect_question_ids": incorrect_question_ids,
        "correct_question_ids": correct_question_ids,
        "skipped_question_ids": skipped_question_ids,
        "message": message
    }
    return data

def get_mentor_paper_all_student_assessment_report(assessmentpaper_id):
    assessmentpaper = models.MentorPapers.objects.get(
        id=assessmentpaper_id)
    exam_obj = course_models.Exam.objects.get(id=int(assessmentpaper.exam.id))
    try:
        mcq_linked_obj = course_models.QuestionType.objects.get(exam=exam_obj, type_of_question='mcq')
    except:
        mcq_linked_obj = None
    try:
        mcc_linked_obj = course_models.QuestionType.objects.get(exam=exam_obj, type_of_question='mcc')
    except:
        mcc_linked_obj = None
    try:
        fillup_linked_obj = course_models.QuestionType.objects.get(exam=exam_obj, type_of_question='fillup')
    except:
        fillup_linked_obj = None
    try:
        numerical_linked_obj = course_models.QuestionType.objects.get(exam=exam_obj, type_of_question='numerical')
    except:
        numerical_linked_obj = None
    try:
        fillupoption_linked_obj = course_models.QuestionType.objects.get(exam=exam_obj, type_of_question='fillup_option')
    except:
        fillupoption_linked_obj = None
    try:
        boolean_linked_obj = course_models.QuestionType.objects.get(exam=exam_obj, type_of_question='boolean')
    except:
        boolean_linked_obj = None
    try:
        assertion_linked_obj = course_models.QuestionType.objects.get(exam=exam_obj, type_of_question='assertion')
    except:
        assertion_linked_obj = None
    student_test_data = []
    answer_papers = models.MentorPaperAnswerPaper.objects.filter(mentor_paper=assessmentpaper)
    for answerpaper in answer_papers:
        answer_paper = models.MentorPaperAnswerPaper.objects.get(id=answerpaper.id)
        user_answer = models.UserAnswerMentorPaper.objects.filter(
            answer_paper=answer_paper)
        question_id = answer_paper.question_order
        question_ids = re.sub("[^0-9,]", "", question_id)
        question_ids = question_ids.split(',')
        total_score = assessmentpaper.marks
        corrected = 0
        score = 0
        allsubject_ids = []
        subjects = assessmentpaper.subjects.all()
        allsubject_ids = [subject.id for subject in subjects]
        subject_ids = []
        chapter_ids = []
        subject_data = []
        chapter_data = []
        all_question_ids = []
        all_question_ids.extend(assessmentpaper.questions.values_list("id", flat=True).all())
        allques_obj = models.Question.objects.filter(id__in=all_question_ids)
        tagIds = []
        tagIds.extend(allques_obj.values_list("linked_topics", flat=True).all())
        # chapters = course_models.Chapter.objects.filter(subject__in=allsubject_ids, topics__in=tagIds).distinct()
        if assessmentpaper.paper_type == 'paper':
            chapters = course_models.Chapter.objects.filter(subject__in=allsubject_ids, topics__in=tagIds).distinct()
        else:
            chapters = assessmentpaper.chapters.all()
            if not chapters:
                chapters = course_models.Chapter.objects.filter(subject__in=allsubject_ids, topics__in=tagIds).distinct()
        subject_ids.extend(chapters.values_list("subject", flat=True))
       
        subjects = course_models.Subject.objects.filter(
            id__in=subject_ids)
        incorrect_ques = []
        
        for subject in subjects:
                user_dict = dict(id=subject.id, title = subject.title, score=0, total=0, percentage=0, attempted=0, correct=0, incorrect=0)
                subject_data.append(user_dict)
        for chapter in chapters:
                chapter_dict = dict(id=chapter.id, title = chapter.title, score=0, total=0, percentage=0, subject=chapter.subject.id, attempted=0, correct=0, incorrect=0)
                chapter_data.append(chapter_dict)
        for data in user_answer:
            totalSubject = 0
            scoredSubject = 0
            ques_obj = models.Question.objects.get(id=data.question.id)
            ques_dic = dict(id=ques_obj.id, type_of_question = ques_obj.type_of_question)
            tagIds = []
            ftags = ques_obj.linked_topics.all()
            tagIds = [tag.id for tag in ftags]
            chapter_obj = course_models.Chapter.objects.filter(subject__in=subject_ids, topics__in=tagIds)
            subject_id = chapter_obj[0].subject.id
            chapter_id = chapter_obj[0].id
            if (data.type_of_answer == 'mcq' or data.type_of_answer == 'mcc' or data.type_of_answer == 'assertion'):
                user_mcq_answer = data.user_mcq_answer.all().values_list('id')
                tmp_user_mcq_ans = data.user_mcq_answer.all()
                correct_mcq_answer = data.correct_mcq_answer.all().values_list('id')
                if set(user_mcq_answer) == set(correct_mcq_answer):
                    corrected += 1
                    if data.type_of_answer == 'mcq':
                        score += mcq_linked_obj.marks
                        totalSubject += mcq_linked_obj.marks
                        scoredSubject += mcq_linked_obj.marks
                    elif data.type_of_answer == 'mcc':
                        score += mcc_linked_obj.marks
                        totalSubject += mcc_linked_obj.marks
                        scoredSubject += mcc_linked_obj.marks
                    else:
                        score += assertion_linked_obj.marks
                        totalSubject += assertion_linked_obj.marks
                        scoredSubject += assertion_linked_obj.marks
                else:
                    ques_dic['user_answer'] = [
                                    option.id for option in tmp_user_mcq_ans]
                    incorrect_ques.append(ques_dic)
                    if data.type_of_answer == 'mcq':
                        totalSubject += mcq_linked_obj.marks
                        if mcq_linked_obj.negative_marks:
                            score -= mcq_linked_obj.negative_marks
                            scoredSubject -= mcq_linked_obj.negative_marks
                    elif data.type_of_answer == 'mcc':
                        totalSubject += mcc_linked_obj.marks
                        if mcc_linked_obj.negative_marks:
                            score -= mcc_linked_obj.negative_marks
                            scoredSubject -= mcc_linked_obj.negative_marks
                    else:
                        totalSubject += assertion_linked_obj.marks
                        if assertion_linked_obj.negative_marks:
                            score -= assertion_linked_obj.negative_marks
                            scoredSubject -= assertion_linked_obj.negative_marks
            elif (data.type_of_answer == 'fillup'):
                user_string_answer = str(data.user_string_answer.strip())
                correct_fillup_answer = str(strip_tags(data.correct_fillup_answer.text).strip())
                totalSubject += fillup_linked_obj.marks
                if user_string_answer.lower() == correct_fillup_answer.lower():
                    corrected += 1
                    if data.type_of_answer == 'fillup':
                        score += fillup_linked_obj.marks
                        scoredSubject += fillup_linked_obj.marks
                else:
                    ques_dic['user_answer'] = user_string_answer
                    incorrect_ques.append(ques_dic)
                    if fillup_linked_obj.negative_marks:
                        score -= fillup_linked_obj.negative_marks
                        scoredSubject -= fillup_linked_obj.negative_marks
            elif (data.type_of_answer == 'fillup_option'):
                user_fillup_option_answer = data.user_fillup_option_answer.id
                correct_fillup_option_answer = data.correct_fillup_option_answer.id
                totalSubject += fillupoption_linked_obj.marks
                if user_fillup_option_answer == correct_fillup_option_answer:
                    corrected += 1
                    score += fillupoption_linked_obj.marks
                    scoredSubject += fillupoption_linked_obj.marks
                else:
                    ques_dic['user_answer'] = user_fillup_option_answer
                    incorrect_ques.append(ques_dic)
                    score -= fillupoption_linked_obj.negative_marks
                    scoredSubject -= fillupoption_linked_obj.negative_marks
            elif (data.type_of_answer == 'boolean'):
                user_boolean_answer = str(data.user_boolean_answer)
                correct_boolean_answer = str(data.correct_boolean_answer.option)
                totalSubject += boolean_linked_obj.marks
                if user_boolean_answer == correct_boolean_answer:
                    corrected += 1
                    score += boolean_linked_obj.marks
                    scoredSubject += boolean_linked_obj.marks
                else:
                    ques_dic['user_answer'] = user_boolean_answer
                    incorrect_ques.append(ques_dic)
                    score -= boolean_linked_obj.negative_marks
                    scoredSubject -= boolean_linked_obj.negative_marks
                    
            elif data.type_of_answer == 'numerical':
                user_string_answer = str(data.user_string_answer.strip())
                correct_string_answer = str(data.correct_string_answer.text)
                totalSubject += numerical_linked_obj.marks
                if user_string_answer.lower() == correct_string_answer.lower():
                    corrected += 1
                    score += numerical_linked_obj.marks
                    scoredSubject += numerical_linked_obj.marks
                else:
                    ques_dic['user_answer'] = user_string_answer
                    incorrect_ques.append(ques_dic)
                    if numerical_linked_obj.negative_marks:
                        score -= numerical_linked_obj.negative_marks
                        scoredSubject -= numerical_linked_obj.negative_marks
            for i in range(0, len(subject_data)):
                if subject_data[i]['id'] == subject_id:
                    subject_data[i]['score'] += scoredSubject
                    subject_data[i]['total'] += totalSubject
                    subject_data[i]['attempted'] += 1
                    if scoredSubject > 0:
                        subject_data[i]['correct'] += 1
                    else:
                        subject_data[i]['incorrect'] += 1
            for i in range(0, len(chapter_data)):
                if chapter_data[i]['id'] == chapter_id:
                    chapter_data[i]['score'] += scoredSubject
                    chapter_data[i]['total'] += totalSubject
                    chapter_data[i]['attempted'] += 1
                    if scoredSubject > 0:
                        chapter_data[i]['correct'] += 1
                    else:
                        chapter_data[i]['incorrect'] += 1
        for i in range(0, len(subject_data)):
            try:
                percentage = (subject_data[i]['score'] * 100) / subject_data[i]['total']
            except:
                percentage = 0
            subject_data[i]['percentage'] = percentage
        for i in range(0, len(chapter_data)):
            try:
                percentage = (chapter_data[i]['score'] * 100) / chapter_data[i]['total']
            except:
                percentage = 0
            chapter_data[i]['percentage'] = percentage
        message = {}
        try:
            percentage = (score * 100) / total_score
        except:
            percentage = 0
        data = {
            "user": answer_paper.user.username,
            "attempted": len(user_answer),
            "corrected": corrected,
            "skipped": len(assessmentpaper.questions.all()) - len(user_answer),
            "incorrected": len(user_answer) - corrected,
            "totalquestion": len(assessmentpaper.questions.all()),
            "score": score,
            "totalscore":  total_score,
            "percentage": percentage,
            "time_taken": answer_paper.time_taken,
            "subjects": subject_data,
            "chapters": chapter_data,
            "incorrect_questions": incorrect_ques,
            "message": message
        }
        student_test_data.append(data)
    return student_test_data

def MentorAssessmentTestQuestionwiseAnalysisReport(assessment_test_id):
    assessment_test_obj = content_models.MentorPapers.objects.get(
        id=assessment_test_id)
    answer_paper = content_models.MentorPaperAnswerPaper.objects.filter(
        mentor_paper=assessment_test_obj)
    user_answer = content_models.UserAnswerMentorPaper.objects.filter(
        answer_paper__in=answer_paper).values('user', 'question', 'status', 'score', 'timespent')
   
    df = pd.DataFrame.from_records(user_answer)
    data = []
    if not df.empty:
        df_ = pd.DataFrame()
        df_['question_count'] = df.groupby('question')['status'].count()
        df_['question_true_count'] = df[df['status'] == 1].groupby('question')['status'].count()
        df_['question_timespent'] = df.groupby('question')['timespent'].mean()
        df_ = df_.fillna(0)
        df_['accuracy'] = df_.apply(lambda x: x['question_count'] if x['question_count'] == 0 else round(x['question_true_count'] * 100 / x['question_count'], 0), axis=1)
        df_['students'] = df.groupby('question')['user']
        df_data = df_.reset_index().values.tolist()
        for i in df_data:
            students = []
            question_obj = content_models.Question.objects.get(id=int(i[0]))
            students_obj = auth_models.User.objects.filter(id__in=i[5][1])
            for student in students_obj:
                try:
                    user_dict = dict(username=student.username, full_name=(student.profile.first_name + ' '+ student.profile.last_name))
                except:
                    user_dict = dict(username=student.username, full_name=(student.profile.first_name))
                students.append(user_dict)
            card = dict(question=QuestionSerializer(question_obj).data,attempted=int(i[1]), accuracy=int(i[4]), averagetime=round(i[3]), students=students)
            data.append(card)
    return {"data": data}

def MentorAssessmentIndividualQuestionAnalysisReport(assessment_test_id, question_id):
    assessment_test_obj = content_models.MentorPapers.objects.get(
        id=assessment_test_id)
    answer_paper = content_models.MentorPaperAnswerPaper.objects.filter(
        mentor_paper=assessment_test_obj)
    user_answer = content_models.UserAnswerMentorPaper.objects.filter(
        answer_paper__in=answer_paper, question=question_id).values('user', 'question', 'status', 'score', 'timespent')
    # print ("useranswer", user_answer, question_id)
    df = pd.DataFrame.from_records(user_answer)
    # data = [[], [], []]
    data = []
    if not df.empty:
        df_ = pd.DataFrame()
        df_['question_count'] = df.groupby('question')['status'].count()
        df_['question_true_count'] = df[df['status'] == 1].groupby('question')['status'].count()
        df_['question_timespent'] = df.groupby('question')['timespent'].mean()
        df_ = df_.fillna(0)
        df_['accuracy'] = df_.apply(lambda x: x['question_count'] if x['question_count'] == 0 else round(x['question_true_count'] * 100 / x['question_count'], 0), axis=1)
        df_['students'] = df.groupby('question')['user']
        df_data = df_.reset_index().values.tolist()
        for i in df_data:
            students = []
            question_obj = content_models.Question.objects.get(id=int(i[0]))
            students_obj = auth_models.User.objects.filter(id__in=i[5][1])
            for student in students_obj:
                try:
                    user_dict = dict(username=student.username, full_name=(student.profile.first_name + ' '+ student.profile.last_name))
                except:
                    user_dict = dict(username=student.username, full_name=(student.profile.first_name))
                students.append(user_dict)
            card = dict(question=QuestionSerializer(question_obj).data,attempted=int(i[1]), accuracy=int(i[4]), averagetime=round(i[3]), students=students)
            data.append(card)
    return {"data": data}

def MentorBatchWiseAccuracyAnalysisReport(user):
    batches = content_models.Batch.objects.filter(teacher=user, is_active=True)
    batch_data = []
    for batch in batches:
        assessment_test_obj = content_models.MentorPapers.objects.filter(
            batch=batch.id)
        paperids = [paper.id for paper in assessment_test_obj]
        answer_paper = content_models.MentorPaperAnswerPaper.objects.filter(
            mentor_paper__in=paperids, submitted=True).values('id', 'user', 'percentage', 'submitted', 'score', 'marks', 'time_taken')
        
        df = pd.DataFrame.from_records(answer_paper)
        data = None
        if not df.empty:
            # print ("averagetimeperc", df['time_taken'].mean(), df['percentage'].mean())
            card = dict(batch=ViewBatchSerializer(batch).data,attempted=len(answer_paper), accuracy=round(df['percentage'].mean()), averagetime=round(df['time_taken'].mean()))
            data = card
        else:
            card = dict(batch=ViewBatchSerializer(batch).data,attempted=0, accuracy=0, averagetime=0)
            data = card
        batch_data.append(data)
    return {"batch_data": batch_data}

def get_leaderboardpanda(exam_id, user):
    exam_obj = course_models.Exam.objects.get(id=int(exam_id))
    learner_exam_obj = course_models.LearnerExams.objects.filter(exam=exam_obj)
    ids  = []
    ids = [exam.id for exam in learner_exam_obj]
    learner_papers = models.LearnerPapers.objects.annotate(ques_len=Count('questions')).filter(
        learner_exam__in=ids, paper_type='paper', submitted=True).values('id', 'user', 'submitted', 'score', 'marks', 'time_taken', 'ques_len')
    # print ("examobjaa", exam_obj, learner_papers)
    leaderboard_data = []
    df = pd.DataFrame.from_records(learner_papers)
    if not df.empty:
        df_ = pd.DataFrame()
        df_['paper_count'] = df.groupby('user')['id'].count()
        df_['paper_true_count'] = df[df['submitted'] == 1].groupby('user')['submitted'].count()
        df_['question_timespent'] = df.groupby('user')['time_taken'].sum()
        df_ = df_.fillna(0)
        df_['score'] = df.groupby('user')['score'].sum()
        df_['total_questions'] = df.groupby('user')['ques_len'].sum()
        df_['students'] = df.groupby('user')['user']
        df_data = df_.reset_index().values.tolist()
        for i in df_data:
            students_obj = auth_models.User.objects.get(id__in=i[6][1])
            try:
                profile_pic = students_obj.profile.image.url
            except:
                profile_pic = None
            try:
                phonenumber = students_obj.phonenumber
            except:
                phonenumber = None
            try:
                email = students_obj.email
            except:
                email = None
            try:
                user_dict = dict(userid=students_obj.id, username=students_obj.username, full_name=(students_obj.profile.first_name + ' '+ students_obj.profile.last_name))
            except:
                user_dict = dict(userid=students_obj.id, username=students_obj.username, full_name=(students_obj.profile.first_name))
            
            card = dict(time_spent=i[3],score=int(i[4]), total_question=int(i[5]), userid=user_dict['userid'], name=user_dict['full_name'], profile_img=profile_pic, phonenumber=phonenumber, email=email)
            leaderboard_data.append(card)
    sorted_data = sorted(leaderboard_data, key=lambda x: x['score'], reverse=True)
    top_sorted_data = sorted(leaderboard_data, key=lambda x: x['score'], reverse=True)[:50]
    my_data = []
    for i in range(0, len(sorted_data)):
        if sorted_data[i]['userid'] == user.id:
            sorted_data[i]['rank'] = i+1
            my_data = sorted_data[i]
    return top_sorted_data, my_data

def get_batchwise_leaderboard(batch_id):
    batch_obj = models.Batch.objects.get(id=int(batch_id))
    assessment_test_obj = content_models.MentorPapers.objects.filter(
            batch=batch_obj)
    paperids = [paper.id for paper in assessment_test_obj]
    answer_paper = content_models.MentorPaperAnswerPaper.objects.filter(
        mentor_paper__in=paperids, submitted=True).values('id', 'user', 'percentage', 'submitted', 'score', 'marks', 'time_taken', 'total_questions')
    leaderboard_data = []
    df = pd.DataFrame.from_records(answer_paper)
    if not df.empty:
        df_ = pd.DataFrame()
        df_['paper_count'] = df.groupby('user')['id'].count()
        df_['paper_true_count'] = df[df['submitted'] == 1].groupby('user')['submitted'].count()
        df_['question_timespent'] = df.groupby('user')['time_taken'].sum()
        df_ = df_.fillna(0)
        df_['score'] = df.groupby('user')['score'].sum()
        df_['total_questions'] = df.groupby('user')['total_questions'].sum()
        df_['students'] = df.groupby('user')['user']
        df_data = df_.reset_index().values.tolist()
        for i in df_data:
            students_obj = auth_models.User.objects.get(id__in=i[6][1])
            try:
                profile_pic = students_obj.profile.image.url
            except:
                profile_pic = None
            try:
                user_dict = dict(userid=students_obj.id, username=students_obj.username, full_name=(students_obj.profile.first_name + ' '+ students_obj.profile.last_name))
            except:
                user_dict = dict(userid=students_obj.id, username=students_obj.username, full_name=(students_obj.profile.first_name))
            
            card = dict(time_spent=i[3],score=int(i[4]), total_question=int(i[5]), userid=user_dict['userid'], name=user_dict['full_name'], profile_img=profile_pic)
            leaderboard_data.append(card)
    sorted_data = sorted(leaderboard_data, key=lambda x: x['score'], reverse=True)[:50]
    return sorted_data

def get_mentorallbatch_leaderboard(user):
    batches = content_models.Batch.objects.filter(teacher=user, is_active=True)
    batch_data = []
    for batch in batches:
        assessment_test_obj = content_models.MentorPapers.objects.filter(
            batch=batch.id)
        paperids = [paper.id for paper in assessment_test_obj]
        answer_paper = content_models.MentorPaperAnswerPaper.objects.filter(
            mentor_paper__in=paperids, submitted=True).values('id', 'user', 'percentage', 'submitted', 'score', 'marks', 'time_taken', 'total_questions')
        leaderboard_data = []
        df = pd.DataFrame.from_records(answer_paper)
        if not df.empty:
            df_ = pd.DataFrame()
            df_['paper_count'] = df.groupby('user')['id'].count()
            df_['paper_true_count'] = df[df['submitted'] == 1].groupby('user')['submitted'].count()
            df_['question_timespent'] = df.groupby('user')['time_taken'].sum()
            df_ = df_.fillna(0)
            df_['score'] = df.groupby('user')['score'].sum()
            df_['total_questions'] = df.groupby('user')['total_questions'].sum()
            df_['students'] = df.groupby('user')['user']
            df_data = df_.reset_index().values.tolist()
            for i in df_data:
                students_obj = auth_models.User.objects.get(id__in=i[6][1])
                try:
                    profile_pic = students_obj.profile.image.url
                except:
                    profile_pic = None
                user_dict = dict(userid=students_obj.id, username=students_obj.username, full_name=(students_obj.profile.first_name + ' '+ students_obj.profile.last_name))
                
                card = dict(time_spent=i[3],score=int(i[4]), total_question=int(i[5]), userid=user_dict['userid'], name=user_dict['full_name'], profile_img=profile_pic)
                leaderboard_data.append(card)
        # print ("leaderboard_Data", leaderboard_data)
        if len(leaderboard_data) > 0:
            sorted_data = sorted(leaderboard_data, key=lambda x: x['score'], reverse=True)[:5]
        else:
            sorted_data = []
        # print ("batch_Data", sorted_data, batch)
        final_batch_data = {"batch": ViewBatchSerializer(batch).data, "students": sorted_data}
        batch_data.append(final_batch_data)
    return batch_data

def get_topper_data_in_mentorpaper(user, assessment_test_id):
    assessment_test_obj = content_models.MentorPapers.objects.get(
        id=assessment_test_id)
    answer_paper = content_models.MentorPaperAnswerPaper.objects.filter(
        mentor_paper=assessment_test_obj, submitted=True).values('id', 'user', 'percentage', 'submitted', 'score', 'marks', 'time_taken', 'total_questions', 'remarks', 'attempted', 'correct', 'incorrect')
    topper_data = []
    df = pd.DataFrame.from_records(answer_paper)
    total_users=None
    if not df.empty:
        df_ = pd.DataFrame()
        df_['paper_count'] = df.groupby('user')['id'].count()
        df_['paper_true_count'] = df[df['submitted'] == 1].groupby('user')['submitted'].count()
        df_['question_timespent'] = df.groupby('user')['time_taken'].sum()
        df_ = df_.fillna(0)
        df_['score'] = df.groupby('user')['score'].sum()
        df_['total_questions'] = df.groupby('user')['total_questions'].sum()
        df_['students'] = df.groupby('user')['user']
        df_['remarks'] = df.groupby('user')['remarks']
        df_['attempted'] = df.groupby('user')['attempted'].sum()
        df_['correct'] = df.groupby('user')['correct'].sum()
        df_['incorrect'] = df.groupby('user')['incorrect'].sum()
        df_data = df_.reset_index().values.tolist()
        for i in df_data:
            total_users=i[1]
            students_obj = auth_models.User.objects.get(id__in=i[6][1])
            try:
                profile_pic = students_obj.profile.image.url
            except:
                profile_pic = None
            try:
                user_dict = dict(userid=students_obj.id, username=students_obj.username, full_name=(students_obj.profile.first_name + ' '+ students_obj.profile.last_name))
            except:
                user_dict = dict(userid=students_obj.id, username=students_obj.username, full_name=(students_obj.profile.first_name))
            card = dict(time_spent=i[3],score=int(i[4]), total_question=int(i[5]), username=user_dict['username'], userid=user_dict['userid'], name=user_dict['full_name'], profile_img=profile_pic, remarks=i[7][1], attempted=i[8], correct=i[9], incorrect=i[10])
            topper_data.append(card)
    sorted_data = sorted(topper_data, key=lambda x: x['score'], reverse=True)
    top_sorted_data = sorted(topper_data, key=lambda x: x['score'], reverse=True)[:1]
    user_data = None
    for i in range(0, len(sorted_data)):
        top_sorted_data[0]['total_students']=len(sorted_data)
        if sorted_data[i]['username'] == user.username:
            sorted_data[i]['rank'] = i+1
            user_data = sorted_data[i]
    return top_sorted_data[0], user_data

def get_mentorpaper_answers_history(student, assessmentpaper_id):
    assessmentpaper = models.MentorPapers.objects.get(
        id=assessmentpaper_id)
    answerpaper_obj = models.MentorPaperAnswerPaper.objects.filter(
        user=student, mentor_paper=assessmentpaper)
    remaining_time = 0
    subjectIds = []
    for subject in assessmentpaper.subjects.all():
        subjectIds.append(subject.id)
    if (len(answerpaper_obj.filter(submitted=True)) > 0):
        question_id = answerpaper_obj.last().question_order
        question_ids = re.sub("[^0-9,]", "", question_id)
        question_ids = question_ids.split(',')
        question_list = models.Question.objects.filter(
            id__in=question_ids)
        # print ("question_list", question_list, remaining_time)
    else:
        question_list = models.Question.objects.filter(id=None)

    question_newlist = []
    for question in question_list:
        # tagIds = []
        # for tag in question.linked_topics.all():
        #     tagIds.append(tag.id)
        # chapter_obj = course_models.Chapter.objects.filter(subject__in=subjectIds, topics__in=tagIds)
        chapter_objs = course_models.Chapter.objects.select_related("subject").prefetch_related(
            "topics", "hints").filter(subject__in=subjectIds).values_list("id", flat=True)
        masterTagObj = models.ChapterMasterFTag.objects.filter(chapter__in=chapter_objs, questions=question).last()
      
        contents = []
        for content in question.contents.all():
            lang_obj = models.QuestionLanguage.objects.get(id=int(content.language.id))
            lang_dic = dict(id=lang_obj.id, text=lang_obj.text)
            content_dic = dict(id=content.id, text=content.text, language=lang_dic)
            contents.append(content_dic)
        tags = []
        for tag in question.tags.all():
            tag_obj = models.QuestionTag.objects.get(id=int(tag.id))
            tag_dic = dict(id=tag_obj.id, text=tag_obj.text)
            tags.append(tag_dic)
        user_dict = dict(id=question.id, contents=contents,
                    difficulty=question.difficulty, is_active=question.is_active, 
                    type_of_question=question.type_of_question, question_identifier=question.question_identifier,
                    subject=masterTagObj.chapter.subject.id, tags=tags, ideal_time=question.ideal_time)
        question_newlist.append(user_dict)
    # print ("question_newlist", question_newlist)

    question_data = []
    mark_for_review_obj = answerpaper_obj.last().question_markforreview.all()
    question_save_markforreview_obj = answerpaper_obj.last(
    ).question_save_markforreview.all()
    for question in question_list:
        subject = None
        for ques in question_newlist:
            if ques['id'] == question.id:
                subject = ques['subject']
        user_answer = models.UserAnswerMentorPaper.objects.filter(
            answer_paper=answerpaper_obj.last(), question=question)
        mark_for_review = True if(question in mark_for_review_obj) else False
        save_mark_for_review = True if(
            question in question_save_markforreview_obj) else False
        if user_answer:
            if (user_answer[0].type_of_answer == 'boolean'):
                user_boolean_answer = user_answer[0].user_boolean_answer
                for i in range(0, len(question_newlist)):
                    if question_newlist[i]['id'] == question.id:
                        question_newlist[i]['user_answer'] = user_boolean_answer
                user_dict = dict(question=question.id, attempt=True, s_review=save_mark_for_review, user_boolean_answer=user_boolean_answer, subject=subject)
                question_data.append(user_dict)
            if (user_answer[0].type_of_answer == 'mcq' or user_answer[0].type_of_answer == 'mcc' or user_answer[0].type_of_answer == 'assertion'):
                user_mcq_answer = user_answer[0].user_mcq_answer.all()
                for i in range(0, len(question_newlist)):
                    if question_newlist[i]['id'] == question.id:
                        question_newlist[i]['user_answer'] = [
                                 option.id for option in user_mcq_answer]
                user_dict = dict(question=question.id, attempt=True, s_review=save_mark_for_review, user_mcq_answer=[
                                 option.id for option in user_mcq_answer], subject=subject)
                question_data.append(user_dict)
            if (user_answer[0].type_of_answer == 'fillup' or user_answer[0].type_of_answer == 'numerical'):
                user_string_answer = user_answer[0].user_string_answer.strip()
                for i in range(0, len(question_newlist)):
                    if question_newlist[i]['id'] == question.id:
                        question_newlist[i]['user_answer'] = user_string_answer
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_string_answer=user_string_answer, subject=subject)
                question_data.append(user_dict)
            if (user_answer[0].type_of_answer == 'fillup_option'):
                user_fillup_option_answer = user_answer[0].user_fillup_option_answer
                for i in range(0, len(question_newlist)):
                    if question_newlist[i]['id'] == question.id:
                        question_newlist[i]['user_answer'] = user_fillup_option_answer.id
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_fillup_option_answer=user_fillup_option_answer.id, subject=subject)
                question_data.append(user_dict)
            if user_answer[0].type_of_answer == 'subjective':
                user_subjective_answer = user_answer[0].user_subjective_answer
                for i in range(0, len(question_newlist)):
                    if question_newlist[i]['id'] == question.id:
                        question_newlist[i]['user_answer'] = user_subjective_answer
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_subjective_answer=user_subjective_answer, subject=subject)
                question_data.append(user_dict)
        else:
            user_dict = dict(question=question.id,
                             attempt=False, review=mark_for_review, subject=subject)
            # print ("user_dicta", user_dict)
            question_data.append(user_dict)
    quesIds = []
    sorted_question_list = sorted(question_newlist, key=lambda x: x['subject'])
    for question in sorted_question_list:
        quesIds.append(question['id'])
    sorted_question_data = sorted(question_data, key=lambda x: x['subject'])
    return sorted_question_list, sorted_question_data

def get_user_papercount_in_batch(user, batch_id):
    batch_obj = content_models.Batch.objects.get(id=int(batch_id))
    currenttime = timezone.now()
    assessment_test_obj = content_models.MentorPapers.objects.filter(
        batch=batch_obj)
    paperIds = []
    paperIds = [paper.id for paper in assessment_test_obj]
    total_papers_generated = len(assessment_test_obj)
    answer_paper = content_models.MentorPaperAnswerPaper.objects.filter(user=user,
        mentor_paper__in=paperIds)
    user_paper_data = []
    total_attempted = len(answer_paper)
    attempted_mentor_papers_ids = [paper.mentor_paper.id for paper in answer_paper]
    pending_mentor_papers = content_models.MentorPapers.objects.filter(
        Q(batch=batch_obj, exam_end_date_time__gte=currenttime) | Q(batch=batch_obj, exam_end_date_time=None)).exclude(id__in=attempted_mentor_papers_ids)
    total_pending = len(pending_mentor_papers)
    total_over = total_papers_generated - total_attempted - total_pending

    data = {
            "all": total_papers_generated,
            "attempted": total_attempted,
            "pending": total_pending,
            "over": total_over
        }
    user_paper_data.append(data)
    return user_paper_data

def get_student_self_assessment_questions(paper_id):
    answerpaper_obj = models.SelfAssessExamAnswerPaper.objects.select_related("user", "goal"
    ).prefetch_related("questions").get(id=paper_id)
   
    examid = answerpaper_obj.goal.exam.id
    questions = answerpaper_obj.questions.all()
    questions_id = questions.values_list("id", flat=True)
    # print ("questionsaaids", list(questions_id))
    answerpaper_obj.question_order = list(questions_id)
    answerpaper_obj.save()
    # question_id = answerpaper_obj.question_order
    # question_ids = re.sub("[^0-9,]", "", question_id)
    # question_ids = question_ids.split(',')
    exam_self_assess_ques_obj = course_models.SelfAssessExamQuestions.objects.filter(exam__id=examid).order_by('order')
    # quesIds = [ques.question.id for ques in exam_self_assess_ques_obj]
        # print ("exam_self_assess_ques_obj", exam_self_assess_ques_obj, quesIds)
    # self_assess_ques_obj = course_models.SelfAssessQuestion.objects.filter(id__in=quesIds, is_active=True)
    # question_list = course_models.SelfAssessQuestion.objects.filter(
    #     id__in=quesIds).order_by('order')
    question_list_actual = [ques.question for ques in exam_self_assess_ques_obj]
    question_list = exam_self_assess_ques_obj
    question_data = []
    question_newlist = []
  
    user_answers = models.SelfAssessUserAnswer.objects.select_related('answer_paper', 'question').prefetch_related("user_mcq_answer").filter(
            answer_paper=answerpaper_obj, question__in=question_list_actual)
    question_useranswer_map = {}
    for user_answer in user_answers:
        question_useranswer_map[user_answer.question.id] = user_answer

    for question in question_list:
        if question.question.type_of_question == 'mcq' or question.question.type_of_question == 'mcc':
            options_list = []
            options = course_models.SelfAssessMcqOptions.objects.filter(questioncontent=question.question)
            for option in options:
                options_dict = dict(id=option.id, text= option.text)
                options_list.append(options_dict)
            user_dict = dict(id=question.question.id, is_active=question.question.is_active, order=question.order, is_numeric=question.question.is_numeric, is_compulsory=question.is_compulsory,
                        text=question.question.text, ideal_time=question.question.ideal_time, type_of_question=question.question.type_of_question, options=options_list)
        else:
            user_dict = dict(id=question.question.id, is_active=question.question.is_active, order=question.order, is_numeric=question.question.is_numeric, is_compulsory=question.is_compulsory,
                        text=question.question.text, ideal_time=question.question.ideal_time, type_of_question=question.question.type_of_question)
        question_newlist.append(user_dict)

    for question in question_list:
       
        user_answer = question_useranswer_map.get(question.question.id)
       
        if user_answer:

            if (user_answer.type_of_answer == 'mcq' or user_answer.type_of_answer == 'mcc'):
                user_mcq_answer = user_answer.user_mcq_answer.all()
                user_dict = dict(question=question.question.id, attempt=True, user_mcq_answer=[
                                    option.id for option in user_mcq_answer])
                question_data.append(user_dict)
            if (user_answer.type_of_answer == 'fillup'):
                user_string_answer = user_answer.user_string_answer.strip()
                user_dict = dict(question=question.question.id, attempt=True, user_string_answer=user_string_answer)
                question_data.append(user_dict)
        else:
            user_dict = dict(question=question.question.id,
                             attempt=False)
            question_data.append(user_dict)
    # print ("aahahba", question_newlist, question_data)
    return question_newlist, question_data

def get_topten_exams():
    learner_exams = course_models.LearnerExams.objects.filter(
        is_active=True).values('id', 'user', 'exam')
    exam_data = []
    df = pd.DataFrame.from_records(learner_exams)
    # print ("dfaa", df)
    if not df.empty:
        df_ = pd.DataFrame()
        df_['user_count'] = df.groupby('exam')['id'].count()
        df_ = df_.fillna(0)
        df_['exams'] = df.groupby('exam')['exam']
        df_data = df_.reset_index().values.tolist()
        
        for i in df_data:
            # print ("i[1]aa", i[1], i[2][0])
            exam_obj = course_models.Exam.objects.get(id=i[2][0])
            exam_dict = dict(examid=exam_obj.id, exam=exam_obj.title, total_users=i[1])
            exam_data.append(exam_dict)
        # print ("examdaataa", exam_data)
    sorted_data = sorted(exam_data, key=lambda x: x['total_users'], reverse=True)[:10]
    return sorted_data

def get_goal_assessment_questions(student, assessmentpaper_id):
    answerpaper_obj = models.GoalAssessmentExamAnswerPaper.objects.select_related("goal"
    ).prefetch_related("subjects", "questions", "question_markforreview", 
    "question_save_markforreview").get(id=assessmentpaper_id)

    # answerpaper_obj = models.AnswerPaper.objects.select_related("user", 
    # "assessment_paper").prefetch_related("question_markforreview", 
    # "question_save_markforreview").filter(user=student, assessment_paper=assessmentpaper)
    currenttime = timezone.now()
    remaining_time = 0
    subjectIds = answerpaper_obj.subjects.values_list("id", flat=True)
    if not answerpaper_obj.started:
        answerpaper_obj.start_time = currenttime
        answerpaper_obj.started = True
        answerpaper_obj.save()
    
    if answerpaper_obj.question_order == '':
        # print ("answerpaper_obj.question_order", answerpaper_obj.question_order)
        questions = answerpaper_obj.questions.all()
        questions_id = questions.values_list("id", flat=True)
        answerpaper_obj.question_order = list(questions_id)
        answerpaper_obj.save()
    if not answerpaper_obj.paper_complete:
        starttime = answerpaper_obj.start_time
        if (currenttime >= (starttime + timedelta(minutes=int(answerpaper_obj.total_time)))):
            if answerpaper_obj.pause_count > 0:
                if answerpaper_obj.remaining_time <= 0:
                    answerpaper = answerpaper_obj
                    answerpaper.paper_complete = True
                    answerpaper.time_taken = answerpaper_obj.total_time
                    answerpaper.save()
                    # question_list = models.Question.objects.filter(id=None)
                    question_list = []
                else:
                    questions = answerpaper_obj.questions.all()
                    question_ids = questions.values_list("id", flat=True)
                    question_list = models.Question.objects.prefetch_related("linked_topics", "tags", "contents", "contents__language", "languages").filter(
                        id__in=question_ids)
                    time_spent = (currenttime - starttime).seconds
            
                    remaining_time = answerpaper_obj.remaining_time
            else:
                answerpaper = answerpaper_obj
                answerpaper.paper_complete = True
                answerpaper.time_taken = answerpaper_obj.total_time
                answerpaper.save()
                # question_list = models.Question.objects.filter(id=None)
                question_list = []
        else:
            questions = answerpaper_obj.questions.all()
            question_ids = questions.values_list("id", flat=True)
            question_list = models.Question.objects.prefetch_related("linked_topics", "tags", "contents", "contents__language", "languages").filter(
                id__in=question_ids)
            time_spent = (currenttime - starttime).seconds
            
            if answerpaper_obj.pause_count > 0:
                remaining_time = answerpaper_obj.remaining_time
            else:
                remaining_time = answerpaper_obj.total_time*60 - time_spent
    else:
        # question_list = models.Question.objects.filter(id=None)
        question_list = []

    question_newlist = []
    chapter_objs = course_models.Chapter.objects.select_related("subject").prefetch_related(
            "topics", "hints").filter(subject__in=subjectIds).values_list("id", flat=True)

    for question in question_list:
        
        # tagIds = question.linked_topics.values_list("id", flat=True)
        masterTagObj = models.ChapterMasterFTag.objects.filter(chapter__in=chapter_objs, questions=question).last()
        # print ("mastertagquestionjjaabb", question.id, masterTagObj.chapter.id, masterTagObj.chapter.subject.id)
        # chapter_obj = chapter_objs.filter(topics__in=tagIds)
        tmpquessubjectObj = models.TemporaryPaperSubjectQuestionDistribution.objects.filter(goal_paper=answerpaper_obj, question=question).last()
        if not tmpquessubjectObj.chapter:
            try:
                chapter_obj = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(id=masterTagObj.chapter.id).last()
            except:
                tagIds = question.linked_topics.values_list("id", flat=True)
                chapter_obj = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(topics__in=tagIds).last()
            tmpquessubjectObj.chapter_id = chapter_obj['id']
            tmpquessubjectObj.save()
        contents = []
        options = []
        fillupoptions = []
        for content in question.contents.values("language__id", "language__text", "id", "text") :
            lang_dic = dict(id=content["language__id"], text=content["language__text"])
            content_dic = dict(id=content["id"], text=content["text"], language=lang_dic)
            contents.append(content_dic)
            if content["language__text"] == 'English' and question.type_of_question in ['mcq', 'mcc', 'assertion']:
                options_obj = models.McqTestCase.objects.filter(questioncontent__id=content["id"])
                for option in options_obj:
                    option_dic = dict(id=option.id, correct=option.correct, text=option.text)
                    options.append(option_dic)
            if content["language__text"] == 'English' and question.type_of_question == 'fillup_option':
                options_obj = models.FillUpWithOption.objects.filter(questioncontent__id=content["id"])
                for option in options_obj:
                    option_dic = dict(id=option.id, correct=option.correct, text=option.text)
                    fillupoptions.append(option_dic)

        if tmpquessubjectObj:
            user_dict = dict(id=question.id, contents=contents, options=options, fillupoptions=fillupoptions,
                    type_of_question=question.type_of_question,
                    subject=tmpquessubjectObj.subject.id, ideal_time=question.ideal_time)
        else:
            user_dict = dict(id=question.id, contents=contents, options=options, fillupoptions=fillupoptions,
                    type_of_question=question.type_of_question,
                    subject=masterTagObj.chapter.subject.id, ideal_time=question.ideal_time)
        question_newlist.append(user_dict)
    
    question_data = []
    mark_for_review_obj = answerpaper_obj.question_markforreview.all()
    question_save_markforreview_obj = answerpaper_obj.question_save_markforreview.all()
    
    user_answers = models.GoalAssessmentUserAnswer.objects.select_related('answer_paper', 'question','correct_fillup_answer').prefetch_related("correct_mcq_answer", "user_mcq_answer").filter(
            answer_paper=answerpaper_obj, question__in=question_list)
    question_useranswer_map = {}
    for user_answer in user_answers:
        question_useranswer_map[user_answer.question.id] = user_answer

    for question in question_list:
        subject = None
        for ques in question_newlist:
            if ques['id'] == question.id:
                subject = ques['subject']
                break
        
        user_answer = question_useranswer_map.get(question.id)
        mark_for_review = question in mark_for_review_obj
        save_mark_for_review = question in question_save_markforreview_obj
        if user_answer:
            if (user_answer.type_of_answer == 'boolean'):
                user_boolean_answer = user_answer.user_boolean_answer
                user_dict = dict(question=question.id, attempt=True, s_review=save_mark_for_review, user_boolean_answer=user_boolean_answer, subject=subject)
                question_data.append(user_dict)
            if (user_answer.type_of_answer == 'mcq' or user_answer.type_of_answer == 'mcc' or user_answer.type_of_answer == 'assertion'):
                user_mcq_answer = user_answer.user_mcq_answer.all()
                user_dict = dict(question=question.id, attempt=True, s_review=save_mark_for_review, user_mcq_answer=[
                                 option.id for option in user_mcq_answer], subject=subject)
                question_data.append(user_dict)
            if (user_answer.type_of_answer == 'fillup' or user_answer.type_of_answer == 'numerical'):
                user_string_answer = user_answer.user_string_answer.strip()
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_string_answer=user_string_answer, subject=subject)
                question_data.append(user_dict)
            if (user_answer.type_of_answer == 'fillup_option'):
                user_fillup_option_answer = user_answer.user_fillup_option_answer
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_fillup_option_answer=user_fillup_option_answer.id, subject=subject)
                question_data.append(user_dict)
            if user_answer.type_of_answer == 'subjective':
                user_subjective_answer = user_answer.user_subjective_answer
                user_subjective_answer_image = user_answer[
                    0].user_subjective_answer_image.url if user_answer.user_subjective_answer_image else None
                user_subjective_answer_images = UserSubjectiveAnswerImageSerializer(user_answer.user_subjective_answer_images, many=True).data
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_subjective_answer=user_subjective_answer, subject=subject,  
                                 user_subjective_answer_image=user_subjective_answer_image, 
                                 user_subjective_answer_images=user_subjective_answer_images)
                question_data.append(user_dict)
        else:
            user_dict = dict(question=question.id,
                             attempt=False, review=mark_for_review, subject=subject)
            question_data.append(user_dict)
    sorted_question_list = sorted(question_newlist, key=lambda x: x['subject'])
    sorted_question_data = sorted(question_data, key=lambda x: x['subject'])
    return sorted_question_list, remaining_time, sorted_question_data

def get_student_goal_assessment_report(user, assessmentpaper_id):
    assessmentpaper = models.GoalAssessmentExamAnswerPaper.objects.prefetch_related("subjects", "chapters", "questions"
    ).select_related("goal").get(id=assessmentpaper_id)
    question_types = course_models.QuestionType.objects.values("negative_marks", "marks", "type_of_question").filter(exam__id=assessmentpaper.goal.exam.id)
    question_type_dict = {}
    for question_type in question_types:
        question_type_dict[question_type["type_of_question"]] = {"negative_marks": question_type["negative_marks"], "marks": question_type["marks"]}
    
    # answer_paper = models.AnswerPaper.objects.filter(
    #     user=user, assessment_paper=assessmentpaper).last()

    user_answer = models.GoalAssessmentUserAnswer.objects.filter(answer_paper=assessmentpaper).select_related(
            "answer_paper", "user", "question",  "correct_fillup_answer", "correct_boolean_answer", 
            "correct_string_answer").prefetch_related("user_mcq_answer", "correct_mcq_answer", "question__linked_topics")
   
    total_score = assessmentpaper.marks
    corrected = 0
    unchecked = 0
    score = 0
    
    subjects = assessmentpaper.subjects.all()
    allsubject_ids = subjects.values_list("id", flat=True)
    subject_data = {}
    chapter_data = {}
    incorrect_question_ids = []
    correct_question_ids = []
    skipped_question_ids = []
    
    tagIds =  assessmentpaper.questions.values_list("linked_topics", flat=True).all()

    if assessmentpaper.paper_type == 'paper':
        chapters = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(subject__in=subjects, topics__in=tagIds).distinct()
    else:
        chapterstmp = assessmentpaper.chapters.all()
        chaptrIds = [cp.id for cp in chapterstmp]
        chapters = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(id__in=chaptrIds).distinct()
        if not chapters:
            chapters = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(subject__in=allsubject_ids, topics__in=tagIds).distinct()
    
    subject_ids = []
    allchapter_ids = []
    incorrect_ques = []

    for subject in subjects:
        subject_data[subject.id] = dict(id=subject.id, title = subject.title, score=0, total=0, percentage=0, attempted=0, correct=0, incorrect=0, unchecked=0)

    for chapter in chapters:
        chapter_data[chapter["id"]] = dict(id=chapter["id"], title = chapter["title"], score=0, total=0, percentage=0, subject=chapter["subject__id"], attempted=0, correct=0, incorrect=0, unchecked=0)
        allchapter_ids.append(chapter["id"])
        subject_ids.append(chapter["subject__id"])
 
    # chapter_objs = course_models.Chapter.objects.select_related("subject").values("subject__id", "id").filter(subject__in=subject_ids, id__in=allchapter_ids)
    for data in user_answer:
        totalSubject = 0
        scoredSubject = 0
        uncheckedSubject = 0
        # attended_question_ids.append(data.question.id)
        ques_obj = data.question
        ques_dic = dict(id=ques_obj.id, type_of_question = ques_obj.type_of_question)

        # tagIds = ques_obj.linked_topics.values_list("id", flat=True).all()
        # chapter_obj = chapters.filter(topics__in=tagIds).first()
        # if not chapter_obj:
        #     tmpchapter_objs = course_models.Chapter.objects.select_related("subject").prefetch_related(
        #     "topics", "hints").filter(subject__in=subject_ids).values_list("id", flat=True)
        #     masterTagObj = models.ChapterMasterFTag.objects.filter(chapter__in=tmpchapter_objs, questions=ques_obj).last()
        #     chapter_obj = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(id=masterTagObj.chapter.id).last()
        # subject_id = chapter_obj["subject__id"]
        # chapter_id = chapter_obj["id"]
        # print ("subject_id", subject_id, chapter_id)
        tmpquessubjectObj = models.TemporaryPaperSubjectQuestionDistribution.objects.filter(goal_paper=assessmentpaper, question=ques_obj).last()
        chapter_obj = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(id=tmpquessubjectObj.chapter.id).last()
        subject_id = tmpquessubjectObj.subject.id
        chapter_id = chapter_obj["id"]
        if not chapter_obj["id"] in chapter_data:
            tmpTagIds = []
            tmpTagIds = ques_obj.linked_topics.values_list("id", flat=True).all()
            chapter_obj = chapters.values("subject__id", "id", "title").filter(topics__in=tmpTagIds).first()
            if not chapter_obj:
                tmpchapter_objs = course_models.Chapter.objects.select_related("subject").prefetch_related(
                "topics", "hints").filter(subject__in=subject_ids).values_list("id", flat=True)
                masterTagObj = models.ChapterMasterFTag.objects.filter(chapter__in=tmpchapter_objs, questions=ques_obj).last()
                chapter_obj = course_models.Chapter.objects.select_related("subject").values("subject__id", "id", "title").filter(id=masterTagObj.chapter.id).last()
                # chapter_data[chapter_obj["id"]] = dict(id=chapter_obj["id"], title = chapter_obj["title"], score=0, total=0, percentage=0, subject=chapter_obj["subject__id"], attempted=0, correct=0, incorrect=0, unchecked=0)
            subject_id = chapter_obj["subject__id"]
            chapter_id = chapter_obj["id"]
        
        question_type_answers = question_type_dict.get(data.type_of_answer)
        if (data.type_of_answer == 'mcq' or data.type_of_answer == 'mcc' or data.type_of_answer == 'assertion'):
            user_mcq_answer = data.user_mcq_answer.all()
            tmp_mcq_answer  = user_mcq_answer
            user_mcq_answer = user_mcq_answer.values_list('id') 
            
            correct_mcq_answer = data.correct_mcq_answer.all().values_list('id')
            # case when all options of mcq match
            if set(user_mcq_answer) == set(correct_mcq_answer):
                corrected += 1
                correct_question_ids.append(ques_dic['id'])
                if data.type_of_answer == 'mcq':
                    score += question_type_answers["marks"]
                    totalSubject += question_type_answers["marks"]
                    scoredSubject += question_type_answers["marks"]
                elif data.type_of_answer == 'mcc':
                    score += question_type_answers["marks"]
                    totalSubject += question_type_answers["marks"]
                    scoredSubject += question_type_answers["marks"]
                else:
                    score += question_type_answers["marks"]
                    totalSubject += question_type_answers["marks"]
                    scoredSubject += question_type_answers["marks"]
            # case when any one of the options of mcq does not match
            else:
                ques_dic['user_answer'] = [
                                 option.id for option in tmp_mcq_answer]
                incorrect_ques.append(ques_dic)
                incorrect_question_ids.append(ques_dic['id'])
                if data.type_of_answer == 'mcq':
                    totalSubject += question_type_answers["marks"]
                    if question_type_answers["negative_marks"]:
                        score -= question_type_answers["negative_marks"]
                        scoredSubject -= question_type_answers["negative_marks"]
                elif data.type_of_answer == 'mcc':
                    totalSubject += question_type_answers["marks"]
                    if question_type_answers["negative_marks"]:
                        score -= question_type_answers["negative_marks"]
                        scoredSubject -= question_type_answers["negative_marks"]
                else:
                    totalSubject += question_type_answers["marks"]
                    if question_type_answers["negative_marks"]:
                        score -= question_type_answers["negative_marks"]
                        scoredSubject -= question_type_answers["negative_marks"]
        elif (data.type_of_answer == 'fillup'):
            user_string_answer = str(data.user_string_answer.strip())
            correct_fillup_answer = str(strip_tags(data.correct_fillup_answer.text).strip())
            totalSubject += question_type_answers["marks"]
            if user_string_answer.lower() == correct_fillup_answer.lower():
                corrected += 1
                correct_question_ids.append(ques_dic['id'])
                if data.type_of_answer == 'fillup':
                    score += question_type_answers["marks"]
                    scoredSubject += question_type_answers["marks"]
            else:
                ques_dic['user_answer'] = user_string_answer
                incorrect_ques.append(ques_dic)
                incorrect_question_ids.append(ques_dic['id'])
                if question_type_answers["negative_marks"]:
                    score -= question_type_answers["negative_marks"]
                    scoredSubject -= question_type_answers["negative_marks"]
        elif (data.type_of_answer == 'fillup_option'):
            user_fillup_option_answer = data.user_fillup_option_answer.id
            correct_fillup_option_answer = data.correct_fillup_option_answer.id
            totalSubject += question_type_answers["marks"]
            if user_fillup_option_answer == correct_fillup_option_answer:
                corrected += 1
                correct_question_ids.append(ques_dic['id'])
                score += question_type_answers["marks"]
                scoredSubject += question_type_answers["marks"]
            else:
                ques_dic['user_answer'] = user_fillup_option_answer
                incorrect_ques.append(ques_dic)
                incorrect_question_ids.append(ques_dic['id'])
                score -= question_type_answers["negative_marks"]
                scoredSubject -= question_type_answers["negative_marks"]
        elif (data.type_of_answer == 'boolean'):
            user_boolean_answer = str(data.user_boolean_answer)
            correct_boolean_answer = str(data.correct_boolean_answer.option)
            totalSubject += question_type_answers["marks"]
            if user_boolean_answer == correct_boolean_answer:
                corrected += 1
                correct_question_ids.append(ques_dic['id'])
                score += question_type_answers["marks"]
                scoredSubject += question_type_answers["marks"]
            else:
                ques_dic['user_answer'] = user_boolean_answer
                incorrect_ques.append(ques_dic)
                incorrect_question_ids.append(ques_dic['id'])
                score -= question_type_answers["negative_marks"]
                scoredSubject -= question_type_answers["negative_marks"]
                
        elif data.type_of_answer == 'numerical':
            user_string_answer = str(data.user_string_answer.strip())
            correct_string_answer = str(data.correct_string_answer.text)
            totalSubject += question_type_answers["marks"]
            if user_string_answer.lower() == correct_string_answer.lower():
                corrected += 1
                correct_question_ids.append(ques_dic['id'])
                score += question_type_answers["marks"]
                scoredSubject += question_type_answers["marks"]
            else:
                ques_dic['user_answer'] = user_string_answer
                incorrect_ques.append(ques_dic)
                incorrect_question_ids.append(ques_dic['id'])
                if question_type_answers["negative_marks"]:
                    score -= question_type_answers["negative_marks"]
                    scoredSubject -= question_type_answers["negative_marks"]
        elif data.type_of_answer == 'subjective':
            unchecked += 1
            uncheckedSubject += 1
    
        subject_data[subject_id]['score'] += scoredSubject
        subject_data[subject_id]['total'] += totalSubject
        subject_data[subject_id]['attempted'] += 1
        chapter_data[chapter_id]['score'] += scoredSubject
        chapter_data[chapter_id]['total'] += totalSubject
        chapter_data[chapter_id]['attempted'] += 1

        if scoredSubject > 0:
            subject_data[subject_id]['correct'] += 1
            chapter_data[chapter_id]['correct'] += 1
        elif uncheckedSubject > 0:
            subject_data[subject_id]['unchecked'] += 1
            chapter_data[chapter_id]['unchecked'] += 1
        else:
            subject_data[subject_id]['incorrect'] += 1
            chapter_data[chapter_id]['incorrect'] += 1
            
    all_question_ids = assessmentpaper.questions.values_list("id", flat=True).all()
    attended_question_ids = user_answer.values_list("question", flat=True)
    skipped_question_ids = list(set(all_question_ids) - set(attended_question_ids))
    
    finalSubjects = []
    for key, val in subject_data.items():
        if val['total'] == 0:
            continue
        try:
            percentage = (val['score'] * 100) / val['total']
        except:
            percentage = 0
        subject_data[key]['percentage'] = percentage
        finalSubjects.append(subject_data[key])

    finalChapters = []
    for key, val in chapter_data.items():
        if val['total'] == 0:
            continue
        try:
            percentage = (val['score'] * 100) / val['total']
        except:
            percentage = 0

        chapter_data[key]['percentage'] = percentage
        finalChapters.append(chapter_data[key])
    
    message = {}
    try:
        percentage = (score * 100) / total_score
    except:
        percentage = 0
    total_user_answers = len(user_answer)
    total_question_ids = len(all_question_ids)
    data = {
        "attempted": total_user_answers,
        "corrected": corrected,
        "skipped": total_question_ids - total_user_answers,
        "incorrected": (total_user_answers-unchecked) - corrected,
        "unchecked": unchecked,
        "totalquestion": total_question_ids,
        "score": score,
        "totalscore":  total_score,
        "percentage": percentage,
        "time_taken": assessmentpaper.time_taken,
        "subjects": finalSubjects,
        "chapters": finalChapters,
        "incorrect_questions": incorrect_ques,
        "all_question_ids": all_question_ids,
        "incorrect_question_ids": incorrect_question_ids,
        "correct_question_ids": correct_question_ids,
        "skipped_question_ids": skipped_question_ids,
        "message": message
    }
    return data


def get_pregoal_assessment_answers_history(student, assessmentpaper_id):
    answerpaper_obj = models.GoalAssessmentExamAnswerPaper.objects.get(
        id=assessmentpaper_id)

    subjectIds = []
    # for subject in assessmentpaper.subjects.all():
    #     subjectIds.append(subject.id)
    
    subjectIds.extend(answerpaper_obj.subjects.values_list("id", flat=True).all())
    
    if answerpaper_obj:
        question_id = answerpaper_obj.question_order
        question_ids = re.sub("[^0-9,]", "", question_id)
        question_ids = question_ids.split(',')
        question_list = models.Question.objects.filter(
            id__in=question_ids)
    else:
        question_list = models.Question.objects.filter(id=None)

    question_newlist = []
    for question in question_list:
        # quesDetail = QuestionSerializer(question).data
        tagIds = []
        # for tag in question.linked_topics.all():
        #     tagIds.append(tag.id)
        tagIds.extend(question.linked_topics.values_list("id", flat=True).all())
        # chapter_obj = course_models.Chapter.objects.filter(subject__in=subjectIds, topics__in=tagIds)
        chapter_objs = course_models.Chapter.objects.select_related("subject").prefetch_related(
            "topics", "hints").filter(subject__in=subjectIds).values_list("id", flat=True)
        masterTagObj = models.ChapterMasterFTag.objects.filter(chapter__in=chapter_objs, questions=question).last()
        
        contents = []
        for content in question.contents.all():
            lang_obj = models.QuestionLanguage.objects.get(id=int(content.language.id))
            lang_dic = dict(id=lang_obj.id, text=lang_obj.text)
            content_dic = dict(id=content.id, text=content.text, language=lang_dic)
            contents.append(content_dic)
        tags = []
        for tag in question.tags.all():
            tag_obj = models.QuestionTag.objects.get(id=int(tag.id))
            tag_dic = dict(id=tag_obj.id, text=tag_obj.text)
            tags.append(tag_dic)
        user_dict = dict(id=question.id, contents=contents,
                    difficulty=question.difficulty, is_active=question.is_active, 
                    type_of_question=question.type_of_question, question_identifier=question.question_identifier,
                    subject=masterTagObj.chapter.subject.id, tags=tags, ideal_time=question.ideal_time)
        question_newlist.append(user_dict)
    # print ("question_newlist", question_newlist)
    question_data = []
    mark_for_review_obj = answerpaper_obj.question_markforreview.all()
    question_save_markforreview_obj = answerpaper_obj.question_save_markforreview.all()
    for question in question_list:
        subject = None
        # for ques in question_newlist:
        #     if ques['id'] == question.id:
        #         subject = ques['subject']
        shared_item = [element for element in question_newlist if element['id'] == question.id]
        subject = shared_item[0]['subject']
        user_answer = models.GoalAssessmentUserAnswer.objects.filter(
            answer_paper=answerpaper_obj, question=question)
        mark_for_review = True if(question in mark_for_review_obj) else False
        save_mark_for_review = True if(
            question in question_save_markforreview_obj) else False
        if user_answer:
            if (user_answer[0].type_of_answer == 'boolean'):
                user_boolean_answer = user_answer[0].user_boolean_answer
                for i in range(0, len(question_newlist)):
                    if question_newlist[i]['id'] == question.id:
                        question_newlist[i]['user_answer'] = user_boolean_answer
                user_dict = dict(question=question.id, attempt=True, s_review=save_mark_for_review, user_boolean_answer=user_boolean_answer, subject=subject)
                question_data.append(user_dict)
            if (user_answer[0].type_of_answer == 'mcq' or user_answer[0].type_of_answer == 'mcc' or user_answer[0].type_of_answer == 'assertion'):
                user_mcq_answer = user_answer[0].user_mcq_answer.all()
                for i in range(0, len(question_newlist)):
                    if question_newlist[i]['id'] == question.id:
                        question_newlist[i]['user_answer'] = [
                                 option.id for option in user_mcq_answer]
                user_dict = dict(question=question.id, attempt=True, s_review=save_mark_for_review, user_mcq_answer=[
                                 option.id for option in user_mcq_answer], subject=subject)
                question_data.append(user_dict)
            if (user_answer[0].type_of_answer == 'fillup' or user_answer[0].type_of_answer == 'numerical'):
                user_string_answer = user_answer[0].user_string_answer.strip()
                for i in range(0, len(question_newlist)):
                    if question_newlist[i]['id'] == question.id:
                        question_newlist[i]['user_answer'] = user_string_answer
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_string_answer=user_string_answer, subject=subject)
                question_data.append(user_dict)
            if (user_answer[0].type_of_answer == 'fillup_option'):
                user_fillup_option_answer = user_answer[0].user_fillup_option_answer
                for i in range(0, len(question_newlist)):
                    if question_newlist[i]['id'] == question.id:
                        question_newlist[i]['user_answer'] = user_fillup_option_answer.id
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_fillup_option_answer=user_fillup_option_answer.id, subject=subject)
                question_data.append(user_dict)
            if user_answer[0].type_of_answer == 'subjective':
                user_subjective_answer = user_answer[0].user_subjective_answer
                for i in range(0, len(question_newlist)):
                    if question_newlist[i]['id'] == question.id:
                        question_newlist[i]['user_answer'] = user_subjective_answer
                user_dict = dict(question=question.id, attempt=True,
                                 s_review=save_mark_for_review, user_subjective_answer=user_subjective_answer, subject=subject)
                question_data.append(user_dict)
        else:
            user_dict = dict(question=question.id,
                             attempt=False, review=mark_for_review, subject=subject)
            question_data.append(user_dict)
    sorted_question_list = sorted(question_newlist, key=lambda x: x['subject'])
    sorted_question_data = sorted(question_data, key=lambda x: x['subject'])
    return sorted_question_list, sorted_question_data

def formatDateTime(date, time):
    if date and time:
        newDate = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        newTime = datetime.datetime.strptime(time, '%H:%M').time()
        newdatetime = datetime.datetime.combine(newDate, newTime)
        return timezone.make_aware(newdatetime)
    else:
        return None
