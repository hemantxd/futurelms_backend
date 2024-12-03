
from pydoc_data.topics import topics
from django.utils import timezone
from rest_framework.views import APIView
from authentication.serializers import UserSerializer
from core.models import UserGroup
import courses
from rest_framework import viewsets
from rest_framework.exceptions import ParseError
from core import permissions
from core import paginations as core_paginations
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, RetrieveUpdateAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, FileUploadParser
from courses.serializers import SelfAssesQuestionSerializer, ViewSelfAssesQuestionSerializer
from notification.models import NotificationType, Notifications

from profiles import models as profiles_models
from . import models, serializers
from content import utils as content_utils
from courses import models as course_models
import random
from django.http import JsonResponse
from datetime import timedelta
import json
from authentication import models as auth_models
from constants import ExamType, DifficultyRange, QuestionLanguage
from utilities.question_distribution_utils import QuestionDistribution
import logging
from django.db.models import Sum
from django.db.models import Q
import requests
import uuid
from io import BytesIO
from django.core.files import File
import pandas as pd
from django.core.exceptions import ObjectDoesNotExist

import content

logger = logging.getLogger(__name__)

class CreateQuestion(APIView):
    # permission_classes = [IsAuthenticatedOrReadOnly, ]
    trueStatus = ['Draft',
                    'Pending Review',
                    'Approved',
                    'Published',
                    'Pending Approval (Published atleast once)',
                    'Approved (Published atleast once)',
                    'Unpublished (Pending Approval)',
                    'Review OK',
                    'Pending assignment',
                    'Pending Approval',
                    'Approved (Need not be published before)',
                    'Published UAT Accepted']

    falseStatus = [
                    'Expired',
                    'Deprecated',
                    'Rejected',
                    'UAT Rejected',
                    'Testing Status',
                    'Approved Rejected',
                    'Review Rejected',
                    'Linked'
                ]

    def post(self, request, *args, **kwargs):
        data = request.data
        question_identifier = data['id']
        
        identifier_obj = models.QuestionIdentifiers.objects.filter(identifier=question_identifier).exists()
        if identifier_obj:
            return Response({}, status=status.HTTP_201_CREATED)
        
        quesTagIds = []
        quesType = None
        difficulty = 1
        ideal_time = 0
        languageIds = []
        contentIds = []
        doInactive = False
        languages = models.QuestionLanguage.objects.all()
        jsonify_data = json.loads(data['questiondata']) 
        all_tags = jsonify_data.get("AllTags", [])    
        for tag in all_tags:
            topic = course_models.Topic.objects.filter(title=tag).last()
            if not topic:
                topic = course_models.Topic.objects.create(title=tag, description=tag)
            quesTagIds.append(topic)
            
        val = jsonify_data.get("QuestionInfo", [])
        difficulty = val['Difficulty']
        ideal_time = val['Ideal_time']
        if val['Subtype'] == 'SingleChoice':
            quesType = 'mcq'
        elif val['Subtype'] == 'Subjective':
            quesType = 'subjective'
        elif val['Subtype'] == 'SubjectiveAnswer':
            quesType = 'subjective'
        elif val['Subtype'] == 'TrueFalse':
            quesType = 'boolean'
        elif val['Subtype'] == 'FillInTheBlanks':
            quesType = 'fillup'
        elif val['Subtype'] == 'SingleDropDown':
            quesType = 'fillup_option'
        elif val['Subtype'] == 'Assertion':
            quesType = 'assertion'
        elif val['Subtype'] == 'MultipleChoice':
            quesType = 'mcc'
        elif val['Subtype'] == 'PassageComprehension':
            quesType = 'comprehension'
        elif val['Subtype'] == 'LinkedComprehension':
            quesType = 'comprehension'
        elif val['Subtype'] == 'Integer':
            quesType = 'fillup'
        elif val['Subtype'] == 'SubjectiveNumerical':
            quesType = 'fillup'
        elif val['Subtype'] == 'MatrixMatchGrid':
            quesType = 'fillup_option'
            doInactive = True
        elif val['Subtype'] == 'MatrixMatchSingleChoice':
            quesType = 'mcq'
        elif val['Subtype'] == 'MultipleFillInTheBlanks':
            quesType = 'mcc'
        elif val['Subtype'] == 'MultipleDropDown':
            quesType = 'fillup_option'
            doInactive = True
        
        # create question and questionIdentifier
        ques_obj = models.Question.objects.create(
            difficulty=difficulty, is_active=True, is_verified=True,
            type_of_question=quesType,question_identifier=question_identifier,
            ideal_time=ideal_time
        )
        models.QuestionIdentifiers.objects.create(question=ques_obj, identifier=question_identifier)
        
        for tag in quesTagIds:
            ques_obj.linked_topics.add(tag)
            ques_obj.save()
        
        ques_obj.bloom_level = val.get('Bloom_level', None)
        ques_obj.sub_type = val.get('Subtype', None)
        ques_obj.total_language = val.get('TotalLanguage', None)
        ques_obj.question_info_id = val.get('ID', None)
        ques_obj.skill = val.get('Skill', None)
        ques_obj.is_active = not doInactive
        ques_obj.save()
        
        for i, val in jsonify_data.items():
            
            if i == 'Temp_Info':
                if 'Marking' in val:
                    
                    ques_obj.is_active = val['Marking']['Status'] in self.trueStatus
                    ques_obj.status = val['Marking']['Status']
                    
                    ques_obj.forwarded = val['Marking'].get('Forworded', False)
                    ques_obj.perfetly = val['Marking'].get('Perfetly', None)
                    ques_obj.formatting_needed = val['Marking'].get('FormatingNeeded', None)
                    ques_obj.waste_data = val['Marking'].get('WasteData', None)
                    ques_obj.solution_missing = val['Marking'].get('SolutionMissing', False)
                    ques_obj.edit_after_password = val['Marking'].get('EditAfterForword', False)
                    ques_obj.primary_check = val['Marking'].get('PrimaryCheck', None)
                    ques_obj.error_image = val['Marking'].get('ErrorImage', False)
                    ques_obj.faculty_check = val['Marking'].get('FacultyCheck', None)


                if 'Shorting' in val:
                    ques_obj.assigned_code = val['Shorting'].get('AssignedCode', None)
                    ques_obj.question_id = val['Shorting'].get('QuestionID', None)
                    ques_obj.author_code = val['Shorting'].get('AutherCode', None)
                    ques_obj.tag_count = val['Shorting'].get('TagCount', None)
                    ques_obj.update_code = val['Shorting'].get('UpdateCode', None)
                
                
        # for i, val in json.loads(data['questiondata']).items():
            elif i == 'AssociatedQuestions':
                try:
                    ques_obj.associated_questions = json.dumps(val)
                except:
                    ques_obj.associated_questions = None
                
        # for i, val in json.loads(data['questiondata']).items():
            elif i == 'QuestionData':
                for language in languages:
                    if language.short_text in val:
                        # lang_obj = models.QuestionLanguage.objects.get(short_text=language.short_text)
                        ques_obj.languages.add(language)
                        ques_obj.save()

                        lang_content = models.QuestionContent.objects.create(language=language)
                        if 'hints' in val[language.short_text]:
                            if len(val[language.short_text]['hints']) > 0:
                                lang_content.text=val[language.short_text]['question_txt']
                                lang_content.hint=val[language.short_text]['hints'][0]['body']
                                lang_content.save()
                            else:
                                lang_content.text=val[language.short_text]['question_txt']
                                lang_content.save()
                        else:
                            lang_content.text=val[language.short_text]['question_txt']
                            lang_content.save()
                        contentIds.append(lang_content.id)

                        solution_lang = models.Solution.objects.create(questioncontent=lang_content)
                        if quesType == 'subjective':
                            solution_lang.text=val[language.short_text]['answers'][0]['explanation']
                            solution_lang.save()
                        if quesType == 'mcq' or quesType == 'assertion':
                            for answer in val[language.short_text]['answers']:
                                models.McqTestCase.objects.create(questioncontent=lang_content, text=answer['body'], correct=answer['is_correct'])
                                if answer['is_correct']:
                                    solution_lang.text=answer['explanation']
                                    solution_lang.save()
                        if quesType == 'mcc':
                            solutionbody = None
                            count = 0
                            # lang_content_solution = models.Solution.objects.get(questioncontent=lang_content)
                            for answer in val[language.short_text]['answers']:
                                models.McqTestCase.objects.create(questioncontent=lang_content, text=answer['body'], correct=answer['is_correct'])
                                if answer['is_correct']:
                                    count += 1
                                    if count > 1:
                                        solutionbody += answer['explanation']
                                        solution_lang.text = solutionbody
                                        solution_lang.save()
                                    elif count == 1:
                                        solutionbody = answer['explanation']
                                        solution_lang.text = solutionbody
                                        solution_lang.save()
                        if quesType == 'boolean':
                            for answer in val[language.short_text]['answers']:
                                if answer['explanation'] != '':
                                    models.TrueFalseSolution.objects.create(questioncontent=lang_content, option=answer['is_correct'])
                                    solution_lang.text=answer['explanation']
                                    solution_lang.save()
                        if quesType == 'fillup':
                            for answer in val[language.short_text]['answers']:
                                if answer['is_correct']:
                                    models.FillUpSolution.objects.create(questioncontent=lang_content, text=answer['body'])
                                    solution_lang.text=answer['explanation']
                                    solution_lang.save()
                        if quesType == 'fillup_option':
                            for answer in val[language.short_text]['answers']:
                                models.FillUpWithOption.objects.create(questioncontent=lang_content, text=answer['body'], correct=answer['is_correct'])
                                if answer['is_correct']:
                                    solution_lang.text=answer['explanation']
                                    solution_lang.save()
                # if 'hi' in val:
                #     # print ("yesjahii", val['hi'])
                    
                #     hindi_obj, _ = models.QuestionLanguage.objects.get_or_create(text='Hindi')
                #     ques_obj.languages.add(hindi_obj)
                #     ques_obj.save()

                #     if 'hints' in val['hi']:
                #         if len(val['hi']['hints']) > 0:
                #             hindi_content = models.QuestionContent.objects.create(text=val['hi']['question_txt'], language=hindi_obj, hint=val['hi']['hints'][0]['body'])
                #         else:
                #             hindi_content = models.QuestionContent.objects.create(text=val['hi']['question_txt'], language=hindi_obj)
                #     else:
                #         hindi_content = models.QuestionContent.objects.create(text=val['hi']['question_txt'], language=hindi_obj)
                #     contentIds.append(hindi_content.id)

                #     if quesType == 'subjective':
                #         solution_hindi = models.Solution.objects.create(questioncontent=hindi_content, text=val['hi']['answers'][0]['explanation'])
                #     if quesType == 'mcq' or quesType == 'assertion':
                #         for answer in val['hi']['answers']:
                #             models.McqTestCase.objects.create(questioncontent=hindi_content, text=answer['body'], correct=answer['is_correct'])
                #             if answer['is_correct']:
                #                 solution_hindi = models.Solution.objects.create(questioncontent=hindi_content, text=answer['explanation'])
                #     if quesType == 'mcc':
                #         solutionbody = None
                #         count = 0
                #         hindi_content_solution = models.Solution.objects.get(questioncontent=hindi_content)
                #         for answer in val['hi']['answers']:
                #             models.McqTestCase.objects.create(questioncontent=hindi_content, text=answer['body'], correct=answer['is_correct'])
                #             if answer['is_correct']:
                #                 count += 1
                #                 if count > 1:
                #                     solutionbody += answer['explanation']
                #                     solution_hindi = hindi_content_solution
                #                     solution_hindi.text = solutionbody
                #                     solution_hindi.save()
                #                 elif count == 1:
                #                     solutionbody = answer['explanation']
                #                     solution_hindi_initial = models.Solution.objects.create(questioncontent=hindi_content)
                #                     solution_hindi_initial.text = solutionbody
                #                     solution_hindi_initial.save()
                #     if quesType == 'boolean':
                #         for answer in val['hi']['answers']:
                #             if answer['explanation'] != '':
                #                 models.TrueFalseSolution.objects.create(questioncontent=hindi_content, option=answer['is_correct'])
                #                 solution_hindi = models.Solution.objects.create(questioncontent=hindi_content, text=answer['explanation'])
                #     if quesType == 'fillup':
                #         for answer in val['hi']['answers']:
                #             if answer['is_correct']:
                #                 models.FillUpSolution.objects.create(questioncontent=hindi_content, text=answer['body'])
                #                 solution_hindi = models.Solution.objects.create(questioncontent=hindi_content, text=answer['explanation'])
                #     if quesType == 'fillup_option':
                #         for answer in val['hi']['answers']:
                #             models.FillUpWithOption.objects.create(questioncontent=hindi_content, text=answer['body'], correct=answer['is_correct'])
                #             if answer['is_correct']:
                #                 solution_hindi = models.Solution.objects.create(questioncontent=hindi_content, text=answer['explanation'])
                # elif 'en' in val:
                #     eng_obj, _ = models.QuestionLanguage.objects.get_or_create(text='English')
                #     ques_obj.languages.add(eng_obj)
                #     ques_obj.save()

                #     if 'hints' in val['en']:
                #         if len(val['en']['hints']) > 0:
                #             eng_content = models.QuestionContent.objects.create(text=val['en']['question_txt'], language=eng_obj, hint=val['en']['hints'][0]['body'])
                #         else:
                #             eng_content = models.QuestionContent.objects.create(text=val['en']['question_txt'], language=eng_obj)
                #     else:
                #         eng_content = models.QuestionContent.objects.create(text=val['en']['question_txt'], language=eng_obj)
                #     contentIds.append(eng_content.id)
                #     if quesType == 'subjective':
                #         solution_eng = models.Solution.objects.create(questioncontent=eng_content, text=val['en']['answers'][0]['explanation'])
                #     if quesType == 'mcq' or quesType == 'assertion':
                #         for answer in val['en']['answers']:
                #             models.McqTestCase.objects.create(questioncontent=eng_content, text=answer['body'], correct=answer['is_correct'])
                #             if answer['is_correct']:
                #                 solution_eng = models.Solution.objects.create(questioncontent=eng_content, text=answer['explanation'])
                #     if quesType == 'mcc':
                #         solutionbody = None
                #         count = 0
                #         for answer in val['en']['answers']:
                #             models.McqTestCase.objects.create(questioncontent=eng_content, text=answer['body'], correct=answer['is_correct'])
                #             if answer['is_correct']:
                #                 count += 1
                #                 if count > 1:
                #                     solutionbody += answer['explanation']
                #                     solution_eng = models.Solution.objects.get(questioncontent=eng_content)
                #                     solution_eng.text = solutionbody
                #                     solution_eng.save()
                #                 elif count == 1:
                #                     solutionbody = answer['explanation']
                #                     solution_eng_initial = models.Solution.objects.create(questioncontent=eng_content)
                #                     solution_eng_initial.text = solutionbody
                #                     solution_eng_initial.save()
                #     if quesType == 'boolean':
                #         for answer in val['en']['answers']:
                #             if answer['explanation'] != '':
                #                 models.TrueFalseSolution.objects.create(questioncontent=eng_content, option=answer['is_correct'])
                #                 solution_eng = models.Solution.objects.create(questioncontent=eng_content, text=answer['explanation'])
                #     if quesType == 'fillup':
                #         for answer in val['en']['answers']:
                #             if answer['is_correct']:
                #                 models.FillUpSolution.objects.create(questioncontent=eng_content, text=answer['body'])
                #                 solution_eng = models.Solution.objects.create(questioncontent=eng_content, text=answer['explanation'])
                #     if quesType == 'fillup_option':
                #         for answer in val['en']['answers']:
                #             models.FillUpWithOption.objects.create(questioncontent=eng_content, text=answer['body'], correct=answer['is_correct'])
                #             if answer['is_correct']:
                #                 solution_eng = models.Solution.objects.create(questioncontent=eng_content, text=answer['explanation'])
                allcontents = models.QuestionContent.objects.filter(id__in=contentIds)
                for content in allcontents:
                    ques_obj.contents.add(content)
                    ques_obj.save()
                    
        ques_obj.save()
                       
        return Response({}, status=status.HTTP_201_CREATED)

class BulkEditQuestion(APIView):
    trueStatus = ['Draft',
                    'Pending Review',
                    'Approved',
                    'Published',
                    'Pending Approval (Published atleast once)',
                    'Approved (Published atleast once)',
                    'Unpublished (Pending Approval)',
                    'Review OK',
                    'Pending assignment',
                    'Pending Approval',
                    'Approved (Need not be published before)',
                    'Published UAT Accepted']

    falseStatus = [
                    'Expired',
                    'Deprecated',
                    'Rejected',
                    'UAT Rejected',
                    'Testing Status',
                    'Approved Rejected',
                    'Review Rejected',
                    'Linked'
                ]

    def post(self, request, *args, **kwargs):
        data = request.data
        question_identifier = data['id']
        editQuestion = False

        languages = models.QuestionLanguage.objects.all()
        
        identifier_obj = models.QuestionIdentifiers.objects.filter(identifier=question_identifier).exists()
        if identifier_obj:
            editQuestion = True
        
        quesTagIds = []
        quesType = None
        difficulty = 1
        ideal_time = 0
        languageIds = []
        contentIds = []
        doInactive = False
        jsonify_data = json.loads(data['questiondata'])
        all_tags = jsonify_data.get("AllTags", [])    
        for tag in all_tags:
            topic = course_models.Topic.objects.filter(title=tag).last()
            if not topic:
                topic = course_models.Topic.objects.create(title=tag, description=tag)
            quesTagIds.append(topic)
            
        val = jsonify_data.get("QuestionInfo", [])
        difficulty = val['Difficulty']
        ideal_time = val['Ideal_time']
        if val['Subtype'] == 'SingleChoice':
            quesType = 'mcq'
        elif val['Subtype'] == 'Subjective':
            quesType = 'subjective'
        elif val['Subtype'] == 'SubjectiveAnswer':
            quesType = 'subjective'
        elif val['Subtype'] == 'TrueFalse':
            quesType = 'boolean'
        elif val['Subtype'] == 'FillInTheBlanks':
            quesType = 'fillup'
        elif val['Subtype'] == 'SingleDropDown':
            quesType = 'fillup_option'
        elif val['Subtype'] == 'Assertion':
            quesType = 'assertion'
        elif val['Subtype'] == 'MultipleChoice':
            quesType = 'mcc'
        elif val['Subtype'] == 'PassageComprehension':
            quesType = 'comprehension'
        elif val['Subtype'] == 'LinkedComprehension':
            quesType = 'comprehension'
        elif val['Subtype'] == 'Integer':
            quesType = 'fillup'
        elif val['Subtype'] == 'SubjectiveNumerical':
            quesType = 'fillup'
        elif val['Subtype'] == 'MatrixMatchGrid':
            quesType = 'fillup_option'
            doInactive = True
        elif val['Subtype'] == 'MatrixMatchSingleChoice':
            quesType = 'mcq'
        elif val['Subtype'] == 'MultipleFillInTheBlanks':
            quesType = 'mcc'
        elif val['Subtype'] == 'MultipleDropDown':
            quesType = 'fillup_option'
            doInactive = True
        
        if editQuestion:
            ques_obj = models.Question.objects.filter(question_identifier=question_identifier).last()
            ques_obj.linked_topics.clear()
            ques_obj.languages.clear()
            # ques_obj.tags.clear()
            for content in ques_obj.contents.all():
                models.QuestionContent.objects.get(id=content.id).delete()
            ques_obj.contents.clear()
            ques_obj.save()
        else:
            ques_obj = models.Question.objects.create(
                difficulty=difficulty, is_active=True, is_verified=True,
                type_of_question=quesType,question_identifier=question_identifier,
                ideal_time=ideal_time
            )
            models.QuestionIdentifiers.objects.create(question=ques_obj, identifier=question_identifier)
        
        for tag in quesTagIds:
            ques_obj.linked_topics.add(tag)
            ques_obj.save()
        
        ques_obj.bloom_level = val.get('Bloom_level', None)
        ques_obj.sub_type = val.get('Subtype', None)
        ques_obj.total_language = val.get('TotalLanguage', None)
        ques_obj.question_info_id = val.get('ID', None)
        ques_obj.skill = val.get('Skill', None)
        ques_obj.is_active = not doInactive
        ques_obj.save()
        
        for i, val in jsonify_data.items():
            
            if i == 'Temp_Info':
                if 'Marking' in val:
                    
                    ques_obj.is_active = val['Marking']['Status'] in self.trueStatus
                    ques_obj.status = val['Marking']['Status']
                    
                    ques_obj.forwarded = val['Marking'].get('Forworded', False)
                    ques_obj.perfetly = val['Marking'].get('Perfetly', None)
                    ques_obj.formatting_needed = val['Marking'].get('FormatingNeeded', None)
                    ques_obj.waste_data = val['Marking'].get('WasteData', None)
                    ques_obj.solution_missing = val['Marking'].get('SolutionMissing', False)
                    ques_obj.edit_after_password = val['Marking'].get('EditAfterForword', False)
                    ques_obj.primary_check = val['Marking'].get('PrimaryCheck', None)
                    ques_obj.error_image = val['Marking'].get('ErrorImage', False)
                    ques_obj.faculty_check = val['Marking'].get('FacultyCheck', None)


                if 'Shorting' in val:
                    ques_obj.assigned_code = val['Shorting'].get('AssignedCode', None)
                    ques_obj.question_id = val['Shorting'].get('QuestionID', None)
                    ques_obj.author_code = val['Shorting'].get('AutherCode', None)
                    ques_obj.tag_count = val['Shorting'].get('TagCount', None)
                    ques_obj.update_code = val['Shorting'].get('UpdateCode', None)
                
                
        # for i, val in json.loads(data['questiondata']).items():
            elif i == 'AssociatedQuestions':
                try:
                    ques_obj.associated_questions = json.dumps(val)
                except:
                    ques_obj.associated_questions = None
                
        # for i, val in json.loads(data['questiondata']).items():
            elif i == 'QuestionData':
                for language in languages:
                    if language.short_text in val:
                        # lang_obj = models.QuestionLanguage.objects.get(short_text=language.short_text)
                        ques_obj.languages.add(language)
                        ques_obj.save()
                        lang_content = models.QuestionContent.objects.create(language=language)
                        if 'hints' in val[language.short_text]:
                            if len(val[language.short_text]['hints']) > 0:
                                lang_content.text=val[language.short_text]['question_txt']
                                lang_content.hint=val[language.short_text]['hints'][0]['body']
                                lang_content.save()
                            else:
                                lang_content.text=val[language.short_text]['question_txt']
                                lang_content.save()
                        else:
                            lang_content.text=val[language.short_text]['question_txt']
                            lang_content.save()
                        contentIds.append(lang_content.id)

                        solution_lang, _ = models.Solution.objects.get_or_create(questioncontent=lang_content)
                        if quesType == 'subjective':
                            solution_lang.text=val[language.short_text]['answers'][0]['explanation']
                            solution_lang.save()
                        if quesType == 'mcq' or quesType == 'assertion':
                            for answer in val[language.short_text]['answers']:
                                models.McqTestCase.objects.create(questioncontent=lang_content, text=answer['body'], correct=answer['is_correct'])
                                if answer['is_correct']:
                                    solution_lang.text=answer['explanation']
                                    solution_lang.save()
                        if quesType == 'mcc':
                            solutionbody = None
                            count = 0
                            # lang_content_solution = models.Solution.objects.get(questioncontent=lang_content)
                            for answer in val[language.short_text]['answers']:
                                models.McqTestCase.objects.create(questioncontent=lang_content, text=answer['body'], correct=answer['is_correct'])
                                if answer['is_correct']:
                                    count += 1
                                    if count > 1:
                                        solutionbody += answer['explanation']
                                        solution_lang.text = solutionbody
                                        solution_lang.save()
                                    elif count == 1:
                                        solutionbody = answer['explanation']
                                        solution_lang.text = solutionbody
                                        solution_lang.save()
                        if quesType == 'boolean':
                            for answer in val[language.short_text]['answers']:
                                if answer['explanation'] != '':
                                    models.TrueFalseSolution.objects.create(questioncontent=lang_content, option=answer['is_correct'])
                                    solution_lang.text=answer['explanation']
                                    solution_lang.save()
                        if quesType == 'fillup':
                            for answer in val[language.short_text]['answers']:
                                if answer['is_correct']:
                                    models.FillUpSolution.objects.create(questioncontent=lang_content, text=answer['body'])
                                    solution_lang.text=answer['explanation']
                                    solution_lang.save()
                        if quesType == 'fillup_option':
                            for answer in val[language.short_text]['answers']:
                                models.FillUpWithOption.objects.create(questioncontent=lang_content, text=answer['body'], correct=answer['is_correct'])
                                if answer['is_correct']:
                                    solution_lang.text=answer['explanation']
                                    solution_lang.save()
                    
                allcontents = models.QuestionContent.objects.filter(id__in=contentIds)
                for content in allcontents:
                    ques_obj.contents.add(content)
                    ques_obj.save()
                    
        ques_obj.save()
                       
        return Response({}, status=status.HTTP_201_CREATED)

class RemoveLanguageContentFromQuestion(APIView):

    def put(self, request, *args, **kwargs):
        data = request.data
        question_identifier = data['id']
        language = data['language']
        
        lang_obj = models.QuestionLanguage.objects.get(short_text=language)
        question_obj = models.Question.objects.filter(question_identifier=question_identifier).last()
        contents = question_obj.contents.all()
        contentIds = [cp.id for cp in contents]
        models.QuestionContent.objects.filter(id__in=contentIds, language=lang_obj).delete()
        return Response({'status': 'done'}, status=status.HTTP_201_CREATED)

class AddRemoveFTagFromQuestion(APIView):

    def put(self, request, *args, **kwargs):
        data = request.data
        question_identifier = data['id']
        addFtags = data['addftags']
        removeFtags = data['removeftags']
        
        question_obj = models.Question.objects.filter(question_identifier=question_identifier).last()
        if not question_obj:
            return Response({}, status=status.HTTP_201_CREATED)
 
        for tag in addFtags:
            topic = course_models.Topic.objects.filter(title=tag).last()
            if not topic:
                topic = course_models.Topic.objects.create(title=tag, description=tag)
            question_obj.linked_topics.add(topic)
            question_obj.save()
        for tag in removeFtags:
            topic = course_models.Topic.objects.filter(title=tag).last()
            if not topic:
                pass
            else:
                question_obj.linked_topics.remove(topic)
            question_obj.save()

        return Response({}, status=status.HTTP_201_CREATED)
                

class QuestionTagViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.QuestionTagSerializer

    def get_queryset(self):
        return models.QuestionTag.objects.all().order_by('id')

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuestionLanguageViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.QuestionLanguageSerializer

    def get_queryset(self):
        return models.QuestionLanguage.objects.all().order_by('id').order_by('id')

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EditQuestionTagViewSetViewSet(RetrieveUpdateAPIView):
    queryset = models.QuestionTag.objects.all()
    serializer_class = serializers.QuestionTagSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        level_obj = models.QuestionTag.objects.filter(pk=self.kwargs.get('pk'))
        if not level_obj:
            raise ParseError("Question tag with this id DoesNotExist")
        return level_obj

class ActivateDeactivateQuestion(APIView):

    def put(self, request, *args, **kwargs):
        data = request.data
        quesid = data['id']
        is_active = data['is_active']
        
        question_obj = models.Question.objects.get(id=quesid)
        if not question_obj:
            return Response({}, status=status.HTTP_201_CREATED)
 
        question_obj.is_active = is_active
        question_obj.save()

        return Response({}, status=status.HTTP_201_CREATED)

class SearchQuestionTagViewSetViewSet(ListAPIView):
    queryset = models.QuestionTag.objects.all()
    serializer_class = serializers.QuestionTagSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        searchtext = self.request.query_params.get('text')
        if searchtext:
            tag_obj = models.QuestionTag.objects.filter(
                text__contains=searchtext).order_by('id')
            if tag_obj:
                return tag_obj
            else:
                return []


class QuestionViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.QuestionSerializer
    create_class = serializers.CreateQuestionSerializer

    def get_queryset(self):
        question_id = self.request.query_params.get('question_id')
        if question_id:
            question = models.Question.objects.filter(
                id=int(question_id)).order_by('id')
            return question
        return models.Question.objects.filter(is_active=True).order_by('id')

    def create(self, request, *args, **kwargs):
        if profiles_models.Profile.objects.get(user=request.user).user_group.name in ['admin']:
            serializer = self.create_class(
                data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({"message": "You do not have permission to create question"}, status=status.HTTP_400_BAD_REQUEST)


class EditQuestionViewSet(RetrieveUpdateAPIView):
    queryset = models.Question.objects.all()
    serializer_class = serializers.QuestionSerializer
    update_serializer_class = serializers.EditQuestionSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        question = models.Question.objects.filter(pk=self.kwargs.get('pk'))
        if not question:
            raise ParseError("Question with this id DoesNotExist")
        return question

    def update(self, request, *args, **kwargs):
        question = models.Question.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            question, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(question).data, status=status.HTTP_200_OK)

class FetchQuestionByIdPaperViewSet(RetrieveAPIView):
    queryset = models.Question.objects.all()
    serializer_class = serializers.QuestionInPaperSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        question = models.Question.objects.filter(pk=self.kwargs.get('pk'))
        if not question:
            raise ParseError("Question with this id DoesNotExist")
        return question


class FetchQuestionsByTagsViewSet(ListAPIView):
    queryset = models.Question.objects.all()
    serializer_class = serializers.ShortQuestionSerializer
    pagination_class = core_paginations.CustomPagination
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        topic = self.request.query_params.get('topic')
        order = self.request.query_params.get('order')
        if topic:
            topic_obj = course_models.Topic.objects.get(id=int(topic))
            if order:
                question_obj = models.Question.objects.prefetch_related("contents").filter(
                    linked_topics=topic_obj).order_by(order)
            else:
                question_obj = models.Question.objects.prefetch_related("contents").filter(
                    linked_topics=topic_obj)
            if question_obj:
                return question_obj
            else:
                return []

class QuestionCountByTypeAndTagsViewSet(APIView):
    # queryset = models.Question.objects.all()
    serializer_class = serializers.QuestionSerializer
    permission_classes = (IsAuthenticated,)
    # parser_classes = (FormParser, MultiPartParser)

    def put(self, request, *args, **kwargs):
        topic = self.request.query_params.get('topic')
        ques_type = self.request.query_params.get('type')
        count = 0
        if topic:
            topic_obj = course_models.Topic.objects.get(id=int(topic))
            question_obj = models.Question.objects.filter(
                linked_topics=topic_obj, type_of_question=ques_type).count()
            if question_obj:
                count = question_obj
            else:
                count = 0
        return Response({'count': count})

class QuestionContentViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, permissions.IsQuestionAdminUser,]
    pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.QuestionContentSerializer
    create_class = serializers.CreateQuestionContentSerializer

    def get_queryset(self):
        questioncontent_id = self.request.query_params.get(
            'questioncontent_id')
        if questioncontent_id:
            questioncontent = models.QuestionContent.objects.filter(
                id=int(questioncontent_id))
            return questioncontent
        return models.QuestionContent.objects.filter(is_active=True)

    def create(self, request, *args, **kwargs):
        serializer = self.create_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EditQuestionContentViewSet(RetrieveUpdateAPIView):
    queryset = models.Question.objects.all()
    serializer_class = serializers.QuestionContentSerializer
    update_serializer_class = serializers.EditQuestionContentSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser,)

    def get_queryset(self):
        questioncontent = models.QuestionContent.objects.filter(
            pk=self.kwargs.get('pk'))
        if not questioncontent:
            raise ParseError("Question content with this id DoesNotExist")
        return questioncontent

    def update(self, request, *args, **kwargs):
        questioncontent = models.QuestionContent.objects.get(
            pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            questioncontent, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(questioncontent).data, status=status.HTTP_200_OK)


class SolutionViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.SolutionSerializer
    create_class = serializers.CreateSolutionSerializer

    def get_queryset(self):
        content_id = self.request.query_params.get('content')
        if content_id:
            content_obj = models.QuestionContent.objects.get(
                id=int(content_id))
            solution = models.Solution.objects.filter(
                questioncontent=content_obj)
            return solution
        return models.Solution.objects.all()

    def create(self, request, *args, **kwargs):
        if profiles_models.Profile.objects.get(user=request.user).user_group.name in ['admin']:
            serializer = self.create_class(
                data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({"message": "You do not have permission to create question"}, status=status.HTTP_400_BAD_REQUEST)


class EditSolutionViewSet(RetrieveUpdateAPIView):
    queryset = models.Solution.objects.all()
    serializer_class = serializers.SolutionSerializer
    update_serializer_class = serializers.EditSolutionSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser,)

    def get_queryset(self):
        solution = models.Solution.objects.filter(pk=self.kwargs.get('pk'))
        if not solution:
            raise ParseError("Solution with this id DoesNotExist")
        return solution

    def update(self, request, *args, **kwargs):
        solution = models.Solution.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            solution, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(solution).data, status=status.HTTP_200_OK)


class FillUpSolutionViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.FillUpSolutionSerializer
    create_class = serializers.CreateFillUpSolutionSerializer

    def get_queryset(self):
        content_id = self.request.query_params.get('content')
        if content_id:
            content_obj = models.QuestionContent.objects.get(
                id=int(content_id))
            solution = models.FillUpSolution.objects.filter(
                questioncontent=content_obj)
            return solution
        return models.FillUpSolution.objects.all()

    def create(self, request, *args, **kwargs):
        if profiles_models.Profile.objects.get(user=request.user).user_group.name in ['admin']:
            serializer = self.create_class(
                data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({"message": "You do not have permission to create question"}, status=status.HTTP_400_BAD_REQUEST)


class EditFillUpViewSet(RetrieveUpdateAPIView):
    queryset = models.FillUpSolution.objects.all()
    serializer_class = serializers.FillUpSolutionSerializer
    update_serializer_class = serializers.EditFillUpSolutionSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser,)

    def get_queryset(self):
        solution = models.FillUpSolution.objects.filter(
            pk=self.kwargs.get('pk'))
        if not solution:
            raise ParseError("Fill Up with this id DoesNotExist")
        return solution

    def update(self, request, *args, **kwargs):
        solution = models.FillUpSolution.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            solution, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(solution).data, status=status.HTTP_200_OK)

class StringTestCaseViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.StringTestCaseSerializer
    create_class = serializers.CreateStringTestCaseSerializer

    def get_queryset(self):
        content_id = self.request.query_params.get('content')
        if content_id:
            content_obj = models.QuestionContent.objects.get(
                id=int(content_id))
            solution = models.StringTestCase.objects.filter(
                questioncontent=content_obj)
            return solution
        return models.StringTestCase.objects.all()

    def create(self, request, *args, **kwargs):
        if profiles_models.Profile.objects.get(user=request.user).user_group.name in ['admin']:
            serializer = self.create_class(
                data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({"message": "You do not have permission to create question"}, status=status.HTTP_400_BAD_REQUEST)


class EditStringTestCaseViewSet(RetrieveUpdateAPIView):
    queryset = models.StringTestCase.objects.all()
    serializer_class = serializers.StringTestCaseSerializer
    update_serializer_class = serializers.EditStringTestCaseSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser,)

    def get_queryset(self):
        solution = models.StringTestCase.objects.filter(
            pk=self.kwargs.get('pk'))
        if not solution:
            raise ParseError("Fill Up with this id DoesNotExist")
        return solution

    def update(self, request, *args, **kwargs):
        solution = models.StringTestCase.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            solution, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(solution).data, status=status.HTTP_200_OK)


class MCQTestCaseViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.MCQTestCaseSerializer
    create_class = serializers.CreateMCQTestCaseSerializer

    def get_queryset(self):
        content_id = self.request.query_params.get('content')
        if content_id:
            content_obj = models.QuestionContent.objects.get(
                id=int(content_id))
            solution = models.McqTestCase.objects.filter(
                questioncontent=content_obj).order_by('id')
            return solution
        return models.McqTestCase.objects.all().order_by('id')

    def create(self, request, *args, **kwargs):
        if profiles_models.Profile.objects.get(user=request.user).user_group.name in ['admin']:
            serializer = self.create_class(
                data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({"message": "You do not have permission to create question"}, status=status.HTTP_400_BAD_REQUEST)


class EditMCQViewSet(RetrieveUpdateAPIView):
    queryset = models.McqTestCase.objects.all()
    serializer_class = serializers.MCQTestCaseSerializer
    update_serializer_class = serializers.EditMCQSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser,)

    def get_queryset(self):
        solution = models.McqTestCase.objects.filter(pk=self.kwargs.get('pk'))
        if not solution:
            raise ParseError("McqTestCase with this id DoesNotExist")
        return solution

    def update(self, request, *args, **kwargs):
        solution = models.McqTestCase.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            solution, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(solution).data, status=status.HTTP_200_OK)

class FetchLearnerPapersViewSet(ListAPIView):
    queryset = models.LearnerPapers.objects.all()
    serializer_class = serializers.LearnerPaperSerializer
    pagination_class = core_paginations.CustomPagination
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        learner_paper_obj = models.LearnerPapers.objects.select_related("user", "learner_exam"
        ).prefetch_related("questions", "bookmarks", "subjects").filter(user=user)
        if learner_paper_obj:
            return learner_paper_obj
        else:
            return []
    
class FetchLearnerPapersByIdViewSet(RetrieveUpdateAPIView):
    queryset = models.LearnerPapers.objects.select_related("user", "learner_exam"
        ).prefetch_related("questions", "bookmarks", "subjects", "questions__tags", "questions__linked_topics", 
        "questions__contents", "questions__contents__language").all()
    serializer_class = serializers.LearnerPaperSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        learner_paper_obj = self.queryset.filter(pk=self.kwargs.get('pk'))
        if not learner_paper_obj:
            raise ParseError("Learner paper with this id DoesNotExist")
        return learner_paper_obj

    def list(self, request, *args, **kwargs):
        paper_obj = models.LearnerPapers.objects.select_related("user", "learner_exam"
        ).prefetch_related("questions", "bookmarks", "subjects", "questions__tags", "questions__linked_topics", 
        "questions__contents", "questions__contents__language").get(id=self.kwargs.get('pk'))
        assessmentpaperdetails = serializers.LearnerPaperSerializer(paper_obj, context={'request': request})
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            return Response({
                'paperdetails':assessmentpaperdetails.data,
                'question_data':queryset[1],
            })
        return Response({'error': 'Error in Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class FetchQuestionsByFilterView(UpdateAPIView):
    serializer_class = serializers.CardViewLearnerPaperSerializer

    def put(self, request, *args, **kwargs):
        # topicIds = []
        user = self.request.user
        subjectIds = []
        
        exam = request.data.get('exam', None)
        if not exam:
            return Response({"message": "Invalid exam request"}, status=status.HTTP_400_BAD_REQUEST)
        
        exam_obj = course_models.Exam.objects.get(id=int(exam))
        if not exam_obj.is_active:
            learnerexamtmpobj = course_models.LearnerExams.objects.filter(user=user, exam=exam_obj)
            if learnerexamtmpobj:
                learnerexamtmpobj = learnerexamtmpobj.first()
                learnerexamtmpobj.is_active=False
                learnerexamtmpobj.save()
            return Response({"message": "Oops! Exam has been deactivated by admin"}, status=status.HTTP_400_BAD_REQUEST)
        
        question_types = request.data.get('quesTypes', None)
        difficulty = request.data.get('difficulty', 1)
        
        if len(question_types) == 0:
            return Response({"message": "Please select at least one question type"}, status=status.HTTP_400_BAD_REQUEST)

        chapters = request.data.get('chapters')
        paper_type = request.data.get('type')
        show_time = request.data.get('show_time')
        chapters_obj = course_models.Chapter.objects.filter(id__in=chapters)
        subjectIds.extend(chapters_obj.values_list("subject", flat=True))
        
        # topicIds.extend(chapters_obj.values_list("topics", flat=True).all())
        
        try:
            total_ques = int(request.data.get('totalQues'))
        except:
            total_ques = 0
        
        if paper_type == ExamType.PAPER:
            learner_papercount_obj, _ = models.LearnerTotalActualPapers.objects.get_or_create(user=user)
            total_time = request.data.get('totalTime')
            learner_papercount_obj.count += 1
            learner_papercount_obj.save()
            count = learner_papercount_obj.count
            
        else:
            learner_practicecount_obj, _ = models.LearnerTotalPracticePapers.objects.get_or_create(user=user)
            total_time = 1200
            learner_practicecount_obj.count += 1
            learner_practicecount_obj.save()
            count = learner_practicecount_obj.count
            
            
        
        learner_paper_obj = models.LearnerPapers.objects.create(
            user=user, paper_type=paper_type, paper_count=count, show_time=show_time)
        learner_paper_obj.subjects.add(*subjectIds)
        learner_paper_obj.save()
    
        if paper_type == ExamType.PRACTICE:
            learner_paper_obj.chapters.add(*chapters)
            learner_paper_obj.save()
        
        try:
            learner_exam = int(request.data.get('learnerExam'))
            learner_exam_obj = course_models.LearnerExams.objects.get(id=int(learner_exam))
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
        
        learner_history_obj, _ = models.LearnerHistory.objects.get_or_create(user=user)
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
                return Response({"message": "No questions found"}, status=status.HTTP_400_BAD_REQUEST)
            learner_paper_obj.total_time = total_time
            learner_paper_obj.questions.add(*questions)
            learner_paper_obj.save()
            learner_history_obj.papers.add(learner_paper_obj)
            learner_history_obj.total_questions += len(questions)
            learner_history_obj.questions.add(*questions)
            learner_history_obj.save()
            total_marks = 0
          
            instruction_ques = "Total Questions: " + str(learner_paper_obj.questions.count())
            paper_instruction_obj3 = models.PaperInstructions.objects.create(paper=learner_paper_obj,instruction=instruction_ques)
            if learner_paper_obj.paper_type == 'paper':
                instruction_time = "Total Time (in Min): " + str(total_time)
                paper_instruction_obj = models.PaperInstructions.objects.create(paper=learner_paper_obj,instruction=instruction_time)
            if exam:
                learnerexam_history_obj, _ = models.LearnerExamHistory.objects.get_or_create(user=user, exam=exam_obj)
                
                if learner_paper_obj.paper_type == ExamType.PAPER:
                    learnerexam_practice_history_obj = None
                    learnerexam_paper_history_obj,_ = models.LearnerExamPaperHistory.objects.get_or_create(user=user, exam=exam_obj)
                else:
                    learnerexam_paper_history_obj = None
                    learnerexam_practice_history_obj, _ = models.LearnerExamPracticeHistory.objects.get_or_create(user=user, exam=exam_obj)
                    
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

                paper_instruction_obj2 = models.PaperInstructions.objects.create(paper=learner_paper_obj)

                distribution_based_on_type = QuestionDistribution.distribute_based_on_type_of_questions(
                    learner_paper_obj.questions.all()
                )
                
                total_marks_grouped_by_exam_type_of_question = course_models.QuestionType.objects.filter(
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
            return Response({"message": "error in fetching questions"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(learner_paper_obj).data, status=201)

class SharedLearnerPaperLinkingView(UpdateAPIView):
    serializer_class = serializers.LearnerPaperSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        try:
            paperid = request.data.get('paper')
            learner_paper_obj = models.LearnerPapers.objects.get(id=int(paperid))
        except:
            learner_paper_obj = None
        if not learner_paper_obj:
            return Response({"message": "error in fetching paper details"}, status=status.HTTP_400_BAD_REQUEST)
        
        find_linked_paper = models.SharedPapers.objects.filter(shared_to=user, shared_paper=learner_paper_obj).exists()
        if find_linked_paper:
            return Response({"message": "paper already accepted"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            instructions = models.PaperInstructions.objects.filter(paper=learner_paper_obj)
            learner_papercount_obj, _ = models.LearnerTotalActualPapers.objects.get_or_create(user=user)
            learner_practicecount_obj, _ = models.LearnerTotalPracticePapers.objects.get_or_create(user=user)
            exam_obj = course_models.Exam.objects.get(id=int(learner_paper_obj.learner_exam.exam.id))
            learner_exam_obj, _ = course_models.LearnerExams.objects.get_or_create(
            exam=exam_obj, user=user, defaults={"is_active": True})
            if not exam_obj.is_active:
                learner_exam_obj.is_active=False
                learner_exam_obj.save()
                return Response({"message": "Oops! Exam has been deactivated by admin"}, status=status.HTTP_400_BAD_REQUEST)
            
            if not learner_exam_obj.is_active:
                learner_exam_obj.is_active = True
                learner_exam_obj.save()
            if learner_paper_obj.paper_type == 'paper':
                learner_papercount_obj.count += 1
                learner_papercount_obj.save()
            else:
                learner_practicecount_obj.count += 1
                learner_practicecount_obj.save()
            new_learner_paper_obj = models.LearnerPapers.objects.create(user=user, paper_type=learner_paper_obj.paper_type)
            if learner_paper_obj.paper_type == 'practice':
                new_learner_paper_obj.chapters.add(*(learner_paper_obj.chapters.all()))
            shared_to_me_count_obj = models.SharedPapers.objects.filter(shared_to=user).order_by('id').last()
            shared_by_me_count_obj = models.SharedPapers.objects.filter(sharer=learner_paper_obj.user).order_by('id').last()
            shared_paper_obj = models.SharedPapers.objects.create(sharer=learner_paper_obj.user, shared_to=user, shared_paper=learner_paper_obj, newly_created_paper=new_learner_paper_obj)

            learnerexam_history_obj, _ = models.LearnerExamHistory.objects.get_or_create(user=user, exam=exam_obj)
            
            if learner_paper_obj.paper_type == ExamType.PAPER:
                learnerexam_practice_history_obj = None
                learnerexam_paper_history_obj,_ = models.LearnerExamPaperHistory.objects.get_or_create(user=user, exam=exam_obj)
            else:
                learnerexam_paper_history_obj = None
                learnerexam_practice_history_obj, _ = models.LearnerExamPracticeHistory.objects.get_or_create(user=user, exam=exam_obj)
                    
            learnerexam_history_obj.total_questions += (learner_paper_obj.questions.all()).count()
            learnerexam_history_obj.save()
            
            learnerexam_history_obj.questions.add(*(learner_paper_obj.questions.all()))
            learnerexam_history_obj.papers.add(new_learner_paper_obj)
            learnerexam_history_obj.save()
            if learnerexam_practice_history_obj:
                learnerexam_practice_history_obj.questions.add(*(learner_paper_obj.questions.all()))
                learnerexam_practice_history_obj.papers.add(new_learner_paper_obj)
                learnerexam_practice_history_obj.save()
            else:
                learnerexam_paper_history_obj.questions.add(*(learner_paper_obj.questions.all()))
                learnerexam_paper_history_obj.papers.add(new_learner_paper_obj)
                learnerexam_paper_history_obj.save()
                    
            papercount = 1
            if shared_to_me_count_obj:
                papercount = shared_to_me_count_obj.shared_to_me_paper_count + 1
            shared_paper_obj.shared_to_me_paper_count = papercount
            shared_paper_obj.save()
            papercount2 = 1
            if shared_by_me_count_obj:
                papercount2 = shared_by_me_count_obj.shared_by_me_paper_count + 1
            shared_paper_obj.shared_by_me_paper_count = papercount2
            shared_paper_obj.save()
            for instruction in instructions:
                models.PaperInstructions.objects.create(paper=new_learner_paper_obj, instruction=instruction.instruction)
            new_learner_paper_obj.learner_exam = learner_exam_obj
            new_learner_paper_obj.questions.add(*(learner_paper_obj.questions.all()))
            new_learner_paper_obj.subjects.add(*(learner_paper_obj.subjects.all()))
            new_learner_paper_obj.marks = learner_paper_obj.marks
            # new_learner_paper_obj.save()
            new_learner_paper_obj.total_time = learner_paper_obj.total_time
            new_learner_paper_obj.paper_type = learner_paper_obj.paper_type
            new_learner_paper_obj.save()
            if new_learner_paper_obj.paper_type == 'paper':
                new_learner_paper_obj.paper_count = learner_papercount_obj.count
                new_learner_paper_obj.save()
            else:
                new_learner_paper_obj.paper_count = learner_practicecount_obj.count
                new_learner_paper_obj.save()
        return Response(self.serializer_class(new_learner_paper_obj).data, status=201)

class CheckSharedpaperStatusViewSet(ListAPIView):
    queryset = models.SharedPapers.objects.all()
    serializer_class = serializers.LearnerPaperSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        learner_paper_obj = models.LearnerPapers.objects.filter(pk=self.kwargs.get('pk'))
        if not learner_paper_obj:
            raise ParseError("Learner paper with this id DoesNotExist")
        return learner_paper_obj

    def list(self, request, *args, **kwargs):
        user = self.request.user
        learnerpaper = models.LearnerPapers.objects.get(id=self.kwargs.get('pk'))
        assessmentpaperdetails = serializers.LearnerPaperSerializer(learnerpaper, context={'request': request})
        paper_obj = models.SharedPapers.objects.filter(
            shared_paper=learnerpaper, shared_to=user).last()
        if not paper_obj:
            return Response({"message": "paper not accepted"}, status=status.HTTP_400_BAD_REQUEST)
        accepted_paper_obj = serializers.SharedPaperSerializer(paper_obj, context={'request': request})
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            return Response(accepted_paper_obj.data)
        return Response({'error': 'Error in Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class ReattemptPaperLinkingView(UpdateAPIView):
    serializer_class = serializers.LearnerPaperSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        try:
            paperid = request.data.get('paper')
            learner_paper_obj = models.LearnerPapers.objects.get(id=int(paperid))
        except:
            learner_paper_obj = None
            # raise ParseError("Data with this id DoesNotExist")
        if not learner_paper_obj:
            return Response({"message": "error in fetching paper details"}, status=status.HTTP_400_BAD_REQUEST)
       
        else:
            if learner_paper_obj.actual_paper:
                try:
                    actual_paper_obj = models.LearnerPapers.objects.get(id=int(learner_paper_obj.actual_paper.id))
                except:
                    actual_paper_obj = None
            else:
                actual_paper_obj = None
            instructions = models.PaperInstructions.objects.filter(paper=learner_paper_obj)
            learner_papercount_obj, _ = models.LearnerTotalActualPapers.objects.get_or_create(user=user)
            learner_practicecount_obj, _ = models.LearnerTotalPracticePapers.objects.get_or_create(user=user)
            
            new_learner_paper_obj = models.LearnerPapers.objects.create(user=user, paper_type=learner_paper_obj.paper_type)
            if learner_paper_obj.paper_type == 'practice':
                new_learner_paper_obj.chapters.add(*(learner_paper_obj.chapters.all()))
            for instruction in instructions:
                models.PaperInstructions.objects.create(paper=new_learner_paper_obj, instruction=instruction.instruction)
            try:
                new_learner_paper_obj.learner_exam = learner_paper_obj.learner_exam
                new_learner_paper_obj.save()
            except:
                new_learner_paper_obj.learner_exam = None
            exam_obj = course_models.Exam.objects.get(id=int(learner_paper_obj.learner_exam.exam.id))
            if not exam_obj.is_active:
                learnerexamtmpobj = course_models.LearnerExams.objects.get(user=user, exam=exam_obj)
                if learnerexamtmpobj:
                    learnerexamtmpobj.is_active=False
                    learnerexamtmpobj.save()
                return Response({"message": "Oops! Exam has been deactivated by admin"}, status=status.HTTP_400_BAD_REQUEST)
            learnerexamtmpobj = course_models.LearnerExams.objects.get(user=user, exam=exam_obj)
            if learnerexamtmpobj:
                learnerexamtmpobj.is_active=True
                learnerexamtmpobj.save()
            learnerexam_history_obj, _ = models.LearnerExamHistory.objects.get_or_create(user=user, exam=exam_obj)
            if learner_paper_obj.paper_type == 'paper':
                learnerexam_practice_history_obj = None
                learnerexam_paper_history_obj, _ = models.LearnerExamPaperHistory.objects.get_or_create(user=user, exam=exam_obj)
                learner_papercount_obj.count += 1
                learner_papercount_obj.save()
                new_learner_paper_obj.paper_count=learner_papercount_obj.count
                new_learner_paper_obj.save()
            else:
                learnerexam_paper_history_obj = None
                learnerexam_practice_history_obj, _ = models.LearnerExamPracticeHistory.objects.get_or_create(user=user, exam=exam_obj)
                learner_practicecount_obj.count += 1
                learner_practicecount_obj.save()
                new_learner_paper_obj.paper_count=learner_practicecount_obj.count
                new_learner_paper_obj.save()
            learnerexam_history_obj.total_questions += len(learner_paper_obj.questions.all())
            learnerexam_history_obj.save()
            new_learner_paper_obj.questions.add(*(learner_paper_obj.questions.all()))
            new_learner_paper_obj.save()
            new_learner_paper_obj.subjects.add(*(learner_paper_obj.subjects.all()))
            new_learner_paper_obj.save()
            learnerexam_history_obj.questions.add(*(learner_paper_obj.questions.all()))
            learnerexam_history_obj.save()
            if learnerexam_practice_history_obj:
                learnerexam_practice_history_obj.questions.add(*(learner_paper_obj.questions.all()))
                learnerexam_practice_history_obj.save()
            else:
                learnerexam_paper_history_obj.questions.add(*(learner_paper_obj.questions.all()))
                learnerexam_paper_history_obj.save()
            
            try:
                new_learner_paper_obj.marks = learner_paper_obj.marks
                new_learner_paper_obj.save()
            except:
                new_learner_paper_obj.marks = None
            try:
                new_learner_paper_obj.total_time = learner_paper_obj.total_time
                new_learner_paper_obj.save()
            except:
                new_learner_paper_obj.total_time = None
            try:
                new_learner_paper_obj.paper_type = learner_paper_obj.paper_type
                new_learner_paper_obj.save()
            except:
                new_learner_paper_obj.paper_type = None

            if actual_paper_obj:
                actual_paper_obj.reattempt_papers.add(new_learner_paper_obj)
                actual_paper_obj.save()
                new_learner_paper_obj.actual_paper = actual_paper_obj
                new_learner_paper_obj.save()
            else:
                learner_paper_obj.reattempt_papers.add(new_learner_paper_obj)
                learner_paper_obj.save()
                new_learner_paper_obj.actual_paper = learner_paper_obj
                new_learner_paper_obj.save()
            learnerexam_history_obj.papers.add(new_learner_paper_obj)
            learnerexam_history_obj.save()
            if learnerexam_practice_history_obj:
                learnerexam_practice_history_obj.papers.add(new_learner_paper_obj)
                learnerexam_practice_history_obj.save()
            else:
                learnerexam_paper_history_obj.papers.add(new_learner_paper_obj)
                learnerexam_paper_history_obj.save()
        return Response(self.serializer_class(new_learner_paper_obj).data, status=201)

class BulkUploadQuestion(CreateAPIView):
    queryset = models.Question.objects.all()
    serializer_class = serializers.QuestionSerializer
    permission_classes = [IsAuthenticated, permissions.IsQuestionAdminUser]
    parser_class = (FileUploadParser)

    def create(self, request, *args, **kwargs):
        csv_file = request.FILES['csv_file']
        # If error = True then mssg is a List of error strings.
        # If error = False then mssg is a List of Question ids.
        mssg, no_error = content_utils.bulkuploadquestioncsv(csv_file=csv_file)

        if(no_error):
            question_data = models.Question.objects.filter(id__in=mssg)
            serializer = self.serializer_class(question_data, many=True)
            return Response({'data': serializer.data, 'status': True, 'uploaded': no_error}, status=status.HTTP_200_OK)
        else:
            return Response({'errors': mssg, 'status': False, 'uploaded': no_error}, status=status.HTTP_200_OK)

class LearnerHistoryViewSet(ListAPIView, CreateAPIView):
    queryset = models.LearnerHistory.objects.all()
    serializer_class = serializers.ViewLearnerHistorySerializer
    create_serializer_class = serializers.LearnerHistorySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        # user = self.request.user
        # learner_obj = models.LearnerHistory.objects.filter(
        #     user=user)
        # if learner_obj:
        #     return learner_obj
        # else:
        #     return []
        # user = self.request.user
        try:
            user=None
            if self.request.query_params.get('user'):
                user= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                user = self.request.user
        except:
            user = self.request.user
        learner_obj = models.LearnerHistory.objects.select_related("user"
        ).prefetch_related("learner_exam", "questions", "papers").filter(user=user)
        if learner_obj:
            return learner_obj
        else:
            return []

    def create(self, request, *args, **kwargs):
        serializer = self.create_serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class LearnerExamHistoryViewSet(ListAPIView):
    queryset = models.LearnerExamHistory.objects.all()
    serializer_class = serializers.LearnerExamHistorySerializer
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
        exam_id = self.request.query_params.get('exam')
        exam_obj = course_models.Exam.objects.get(id=int(exam_id))
        if not exam_obj:
            raise ParseError("Exam with this id DoesNotExist")
        learner_obj = models.LearnerExamHistory.objects.filter(
            user=user, exam=exam_obj)
        if learner_obj:
            return learner_obj
        else:
            return []
        # return models.LearnerHistory.objects.all()

class LearnerExamPracticeHistoryViewSet(ListAPIView):
    queryset = models.LearnerExamPracticeHistory.objects.all()
    serializer_class = serializers.LearnerExamPracticeHistorySerializer
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
        exam_id = self.request.query_params.get('exam')
        exam_obj = course_models.Exam.objects.get(id=int(exam_id))
        if not exam_obj:
            raise ParseError("Exam with this id DoesNotExist")
        learner_obj = models.LearnerExamPracticeHistory.objects.filter(
            user=user, exam=exam_obj)
        if learner_obj:
            return learner_obj
        else:
            return []

class LearnerExamPaperHistoryViewSet(ListAPIView):
    queryset = models.LearnerExamPaperHistory.objects.all()
    serializer_class = serializers.LearnerExamPaperHistorySerializer
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
        exam_id = self.request.query_params.get('exam')
        exam_obj = course_models.Exam.objects.get(id=int(exam_id))
        if not exam_obj:
            raise ParseError("Exam with this id DoesNotExist")
        learner_obj = models.LearnerExamPaperHistory.objects.filter(
            user=user, exam=exam_obj)
        if learner_obj:
            return learner_obj
        else:
            return []

class FetchLatestLearnerPapersViewSet(ListAPIView):
    queryset = models.LearnerPapers.objects.all()
    serializer_class = serializers.CardViewLearnerPaperSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = core_paginations.CustomPagination4

    def get_queryset(self):
        user = self.request.user
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            exam_obj = course_models.Exam.objects.get(id=int(exam_id))
            if exam_obj:
                learnerexam_obj = course_models.LearnerExams.objects.get(user=user, exam=exam_obj)
                learner_paper_obj = models.LearnerPapers.objects.filter(user=user, learner_exam=learnerexam_obj)
            if not exam_obj:
                raise ParseError("Exam with this id DoesNotExist")
        if not exam_id:
            learner_paper_obj = models.LearnerPapers.objects.filter(user=user)
        if learner_paper_obj:
            return learner_paper_obj
        else:
            return []

class FetchOverallLatestLearnerPapersViewSet(ListAPIView):
    queryset = models.LearnerPapers.objects.all()
    serializer_class = serializers.CardViewLearnerPaperSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = core_paginations.CustomPagination3

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
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            exam_obj = course_models.Exam.objects.get(id=int(exam_id))
            if exam_obj:
                learnerexam_obj = course_models.LearnerExams.objects.get(user=user, exam=exam_obj)
                learner_paper_obj = models.LearnerPapers.objects.filter(user=user, learner_exam=learnerexam_obj)
            if not exam_obj:
                raise ParseError("Exam with this id DoesNotExist")
        if not exam_id:
            learner_paper_obj = models.LearnerPapers.objects.filter(user=user)
        if learner_paper_obj:
            return learner_paper_obj
        else:
            return []


class SharedByMePapersViewSet(ListAPIView):
    queryset = models.SharedPapers.objects.all()
    serializer_class = serializers.SharedPaperSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = core_paginations.CustomPagination6

    def get_queryset(self):
        user = self.request.user
        paper_obj = models.SharedPapers.objects.filter(sharer=user).order_by('-id')
        if paper_obj:
            return paper_obj
        else:
            return []

class SharedToMePapersViewSet(ListAPIView):
    queryset = models.SharedPapers.objects.all()
    serializer_class = serializers.SharedPaperSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = core_paginations.CustomPagination6

    def get_queryset(self):
        user = self.request.user
        paper_obj = models.SharedPapers.objects.filter(shared_to=user).order_by('-id')
        if paper_obj:
            return paper_obj
        else:
            return []

class PapersInstructionsViewSet(ListAPIView):
    queryset = models.PaperInstructions.objects.all()
    serializer_class = serializers.PaperInstructionsSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        paper_id = self.request.query_params.get('paper')
        if paper_id:
            paper_obj = models.LearnerPapers.objects.get(id=int(paper_id))
            instruction_obj = models.PaperInstructions.objects.filter(paper=paper_obj).order_by('id')
            if instruction_obj:
                return instruction_obj
            else:
                return []

class MentorPapersInstructionsViewSet(ListAPIView):
    queryset = models.MentorPaperInstructions.objects.all()
    serializer_class = serializers.MentorPaperInstructionsSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        paper_id = self.request.query_params.get('paper')
        if paper_id:
            paper_obj = models.MentorPapers.objects.get(id=int(paper_id))
            instruction_obj = models.MentorPaperInstructions.objects.filter(paper=paper_obj).order_by('id')
            if instruction_obj:
                return instruction_obj
            else:
                return []
        
class FillUpWithOptionCaseViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.FillWithOptionCaseSerializer
    create_class = serializers.CreateFillWithOptionSerializer

    def get_queryset(self):
        content_id = self.request.query_params.get('content')
        if content_id:
            content_obj = models.QuestionContent.objects.get(
                id=int(content_id))
            solution = models.FillUpWithOption.objects.filter(
                questioncontent=content_obj).order_by('id')
            return solution
        return models.FillUpWithOption.objects.all().order_by('id')

    def create(self, request, *args, **kwargs):
        if profiles_models.Profile.objects.get(user=request.user).user_group.name in ['admin']:
            serializer = self.create_class(
                data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({"message": "You do not have permission to create question"}, status=status.HTTP_400_BAD_REQUEST)


class EditFillUpWithOptionViewSet(RetrieveUpdateAPIView):
    queryset = models.McqTestCase.objects.all()
    serializer_class = serializers.FillWithOptionCaseSerializer
    update_serializer_class = serializers.EditFillWithOptionSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser,)

    def get_queryset(self):
        solution = models.FillUpWithOption.objects.filter(pk=self.kwargs.get('pk'))
        if not solution:
            raise ParseError("McqTestCase with this id DoesNotExist")
        return solution

    def update(self, request, *args, **kwargs):
        solution = models.FillUpWithOption.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            solution, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(solution).data, status=status.HTTP_200_OK)

class BooleanTypeViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.BooleanTypeSerializer
    create_class = serializers.CreateBooleanTypeSerializer

    def get_queryset(self):
        content_id = self.request.query_params.get('content')
        if content_id:
            content_obj = models.QuestionContent.objects.get(
                id=int(content_id))
            solution = models.TrueFalseSolution.objects.filter(
                questioncontent=content_obj)
            return solution
        return models.TrueFalseSolution.objects.all()

    def create(self, request, *args, **kwargs):
        if profiles_models.Profile.objects.get(user=request.user).user_group.name in ['admin']:
            serializer = self.create_class(
                data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({"message": "You do not have permission to create question"}, status=status.HTTP_400_BAD_REQUEST)


class EditBooleanTypeViewSet(RetrieveUpdateAPIView):
    queryset = models.TrueFalseSolution.objects.all()
    serializer_class = serializers.BooleanTypeSerializer
    update_serializer_class = serializers.CreateBooleanTypeSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, permissions.IsQuestionAdminUser,)

    def get_queryset(self):
        solution = models.TrueFalseSolution.objects.filter(
            pk=self.kwargs.get('pk'))
        if not solution:
            raise ParseError("Data with this id DoesNotExist")
        return solution

    def update(self, request, *args, **kwargs):
        solution = models.TrueFalseSolution.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            solution, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(solution).data, status=status.HTTP_200_OK)

class QuestionAssessmentPaperView(ListAPIView, CreateAPIView):
    serializer_class = serializers.QuestionSerializer
    permission_classes = [IsAuthenticated,]
    
    def get_question_data(self):
        
        questions, remaining_time , question_data = content_utils.get_student_assessment_questions(
            self.request.user, self.kwargs.get('assessmentpaper_id'))
        if not questions:
            return (None, None, None)
        return questions , remaining_time, question_data

    def list(self, request, *args, **kwargs):
        
        assessmentpaper_obj = models.LearnerPapers.objects.select_related(
            "user", "learner_exam", "learner_exam__exam").prefetch_related(
                "questions", "bookmarks", "subjects", "questions__contents", "learner_exam__exam__userboard",
                "learner_exam__exam__subjects", "learner_exam__exam__userclass"
        ).get(id=self.kwargs.get('assessmentpaper_id'))
       
        currenttime = timezone.now()
        answer_paper_obj = models.AnswerPaper.objects.filter(user=self.request.user ,assessment_paper=assessmentpaper_obj)
        if answer_paper_obj:
            starttime = answer_paper_obj.last().start_time
            if answer_paper_obj.last().paper_complete:
                assessmentpaper_obj.submitted = True
                assessmentpaper_obj.save()
                return Response({'exam_status': 'your paper has been finished' }, status=status.HTTP_200_OK)
            else:
                if assessmentpaper_obj.pause_count > 0:
                    if (assessmentpaper_obj.remaining_time <= 0):
                        assessmentpaper_obj.submitted = True
                        assessmentpaper_obj.save()
                        return Response({'exam_status': 'your paper has been finished' }, status=status.HTTP_200_OK)
                else:
                    if (currenttime >= (starttime + timedelta(minutes=int(assessmentpaper_obj.total_time)))):
                        assessmentpaper_obj.submitted = True
                        assessmentpaper_obj.save()
                        return Response({'exam_status': 'your paper has been finished' }, status=status.HTTP_200_OK)
      
        assessmentpaperdetails = serializers.LearnerPaperSerializer(assessmentpaper_obj, context={'request': request})
        queryset = self.get_question_data()
        if queryset:
            # serializer = self.get_serializer(queryset[0], many=True)
            answer_paper_obj = models.AnswerPaper.objects.filter(user=self.request.user ,assessment_paper=assessmentpaper_obj)
            if answer_paper_obj:
                answer_paper = answer_paper_obj.last().id
                return Response({
                    'assessmentpaperdetails':assessmentpaperdetails.data,
                    'answer_paper':answer_paper,
                    'attempt_order':1,
                    'remaining_time':queryset[1],
                    'question_data':queryset[2],
                    'questions': queryset[0]
                })
        return Response({'error': 'Error in Assessment Test Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)


    def create(self, request, *args, **kwargs):
        assessmentpaper_obj = models.LearnerPapers.objects.get(id=self.kwargs.get('assessmentpaper_id'))
        # reports = content_utils.get_student_assessment_report(self.request.user, assessmentpaper_obj.id)
        answer_paper = models.AnswerPaper.objects.filter(user=self.request.user, assessment_paper=assessmentpaper_obj).last()
       
        # assessmentpaper_obj.score = reports['score']
        # assessmentpaper_obj.save()
        # answer_paper.percentage = reports['percentage']
        # answer_paper.total_questions = reports['totalquestion']
        # answer_paper.attempted = reports['attempted']
        # answer_paper.correct = reports['corrected']
        # answer_paper.incorrect = reports['incorrected']
        answer_paper.total_time = assessmentpaper_obj.total_time
        answer_paper.save()
        answer_paper.paper_complete = True
        currenttime = timezone.now()
        starttime = answer_paper.start_time
        time_spent = ((currenttime - starttime).seconds / 60)
        if int(time_spent) > int(assessmentpaper_obj.total_time):
            answer_paper.time_taken = assessmentpaper_obj.total_time
            assessmentpaper_obj.time_taken = assessmentpaper_obj.total_time
        else:
            answer_paper.time_taken = int(time_spent)
            assessmentpaper_obj.time_taken = int(time_spent)
        answer_paper.save()
        assessmentpaper_obj.submitted = True
        assessmentpaper_obj.save()

        return Response({'status': 'Assessment Paper Completed.'}, status=status.HTTP_200_OK)

class MentorQuestionAssessmentPaperView(ListAPIView, CreateAPIView):
    serializer_class = serializers.QuestionSerializer
    permission_classes = [IsAuthenticated,]

    def get_queryset(self):
        questions, remaining_time , question_data = content_utils.get_mentor_batch_paper_assessment_questions(self.request.user, self.kwargs.get('assessmentpaper_id'))
        if not questions:
            return models.Question.objects.filter(id=None)
        return questions , remaining_time, question_data

    def list(self, request, *args, **kwargs):
        assessmentpaper_obj = models.MentorPapers.objects.get(id=self.kwargs.get('assessmentpaper_id'))
       
        currenttime = timezone.now()
        
        exam_start_date_time = assessmentpaper_obj.exam_start_date_time
        if currenttime < exam_start_date_time:
            exam_start_date_time = exam_start_date_time + timezone.timedelta(hours=5, minutes=30)
            return Response({'exam_status': 'You can Start your paper on date {} and time {}'.format(exam_start_date_time.strftime("%d/%m/%Y"), exam_start_date_time.strftime("%I:%M %p"))}, status=status.HTTP_200_OK)
        answer_paper_obj = models.MentorPaperAnswerPaper.objects.filter(user=self.request.user ,mentor_paper=assessmentpaper_obj)
        if answer_paper_obj:
            starttime = answer_paper_obj.last().start_time
            if answer_paper_obj.last().paper_complete:
                answer_paper_obj.submitted = True
                answer_paper_obj.save()
                return Response({'exam_status': 'your paper has been finished' }, status=status.HTTP_200_OK)
            else:
                if answer_paper_obj.last().pause_count > 0:
                    if (answer_paper_obj.last().remaining_time <= 0):
                        answer_paper_obj.submitted = True
                        answer_paper_obj.save()
                        return Response({'exam_status': 'your paper has been finished' }, status=status.HTTP_200_OK)
                else:
                    if (currenttime >= (starttime + timedelta(minutes=int(assessmentpaper_obj.total_time)))):
                        answer_paper_obj.submitted = True
                        answer_paper_obj.save()
                        return Response({'exam_status': 'your paper has been finished' }, status=status.HTTP_200_OK)
        else:
            exam_end_date_time = assessmentpaper_obj.exam_end_date_time
            if exam_end_date_time and currenttime > exam_end_date_time:
                return Response({'exam_status': 'your paper has been finished' }, status=status.HTTP_200_OK)
      
        assessmentpaperdetails = serializers.MentorPaperSerializer(assessmentpaper_obj, context={'request': request})
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            # serializer = self.get_serializer(queryset[0], many=True)
            answer_paper_obj = models.MentorPaperAnswerPaper.objects.filter(user=self.request.user ,mentor_paper=assessmentpaper_obj)
            if answer_paper_obj:
                answer_paper = answer_paper_obj.last().id
                return Response({
                    'assessmentpaperdetails':assessmentpaperdetails.data,
                    'answer_paper':answer_paper,
                    'attempt_order':1,
                    'remaining_time':queryset[1],
                    'question_data':queryset[2],
                    'questions': queryset[0]
                })
        return Response({'error': 'Error in Assessment Test Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)


    def create(self, request, *args, **kwargs):
        assessmentpaper_obj = models.MentorPapers.objects.get(id=self.kwargs.get('assessmentpaper_id'))
        # reports = content_utils.get_student_assessment_report(self.request.user, assessmentpaper_obj.id)
        answer_paper = models.MentorPaperAnswerPaper.objects.filter(user=self.request.user, mentor_paper=assessmentpaper_obj).last()
       
        answer_paper.total_time = assessmentpaper_obj.total_time
        answer_paper.marks = assessmentpaper_obj.marks
        answer_paper.save()
        answer_paper.paper_complete = True
        currenttime = timezone.now()
        starttime = answer_paper.start_time
        time_spent = ((currenttime - starttime).seconds / 60)
        if int(time_spent) > int(assessmentpaper_obj.total_time):
            answer_paper.time_taken = assessmentpaper_obj.total_time
        else:
            answer_paper.time_taken = int(time_spent)
        answer_paper.submitted = True
        answer_paper.save()

        return Response({'status': 'Assessment Paper Completed.'}, status=status.HTTP_200_OK)

class ProcessAssessmentPaperPostSubmitView(CreateAPIView):
    serializer_class = serializers.QuestionSerializer
    permission_classes = [IsAuthenticated,]

    def create(self, request, *args, **kwargs):
        assessmentpaper_obj = models.LearnerPapers.objects.get(id=self.kwargs.get('assessmentpaper_id'))
        
        reports = content_utils.get_student_assessment_report(self.request.user, assessmentpaper_obj.id)
        answer_paper = models.AnswerPaper.objects.filter(user=self.request.user, assessment_paper=assessmentpaper_obj).last()
       
        assessmentpaper_obj.score = reports['score']
        assessmentpaper_obj.save()
        learner_exam_obj = course_models.LearnerExams.objects.get(id=int(assessmentpaper_obj.learner_exam.id))
        for subject in reports['subjects']:
            subject_obj = course_models.Subject.objects.get(id=int(subject['id']))
            
            exam_subject_obj, _ = models.LearnerExamSubjects.objects.get_or_create(learner_exam=learner_exam_obj, subject=subject_obj)
            if assessmentpaper_obj.paper_type == 'practice':
                exam_paper_subject_obj = None
                
                exam_practice_subject_obj, _ = models.LearnerExamPracticeSubjects.objects.get_or_create(learner_exam=learner_exam_obj, subject=subject_obj)
            else:
                exam_practice_subject_obj = None
                
                exam_paper_subject_obj, _ = models.LearnerExamPaperSubjects.objects.get_or_create(learner_exam=learner_exam_obj, subject=subject_obj)
            
            exam_subject_obj.total_marks += subject['total']
            exam_subject_obj.score += subject['score']
            exam_subject_obj.attempted += subject['attempted']
            exam_subject_obj.correct += subject['correct']
            exam_subject_obj.incorrect += subject['incorrect']
            exam_subject_obj.unchecked += subject['unchecked']
            exam_subject_obj.save()
            if exam_subject_obj.total_marks == 0:
                exam_subject_obj.percentage = 0
            else:
                exam_subject_obj.percentage = (exam_subject_obj.score * 100) / exam_subject_obj.total_marks
            exam_subject_obj.save()
            if exam_practice_subject_obj:
                exam_practice_subject_obj.total_marks += subject['total']
                exam_practice_subject_obj.score += subject['score']
                exam_practice_subject_obj.attempted += subject['attempted']
                exam_practice_subject_obj.correct += subject['correct']
                exam_practice_subject_obj.incorrect += subject['incorrect']
                exam_practice_subject_obj.unchecked += subject['unchecked']
                exam_practice_subject_obj.save()
                if  exam_practice_subject_obj.total_marks == 0:
                    exam_practice_subject_obj.percentage = 0
                else:
                    exam_practice_subject_obj.percentage = (exam_practice_subject_obj.score * 100) / exam_practice_subject_obj.total_marks
                exam_practice_subject_obj.save()
            else:
                exam_paper_subject_obj.total_marks += subject['total']
                exam_paper_subject_obj.score += subject['score']
                exam_paper_subject_obj.attempted += subject['attempted']
                exam_paper_subject_obj.correct += subject['correct']
                exam_paper_subject_obj.incorrect += subject['incorrect']
                exam_paper_subject_obj.unchecked += subject['unchecked']
                exam_paper_subject_obj.save()
                if exam_paper_subject_obj.total_marks == 0:
                    exam_paper_subject_obj.percentage = 0
                else:
                    exam_paper_subject_obj.percentage = (exam_paper_subject_obj.score * 100) / exam_paper_subject_obj.total_marks
                exam_paper_subject_obj.save()
        for chapter in reports['chapters']:
            chapterobj = course_models.Chapter.objects.get(id=int(chapter['id']))
            subject_obj = course_models.Subject.objects.get(id=int(chapterobj.subject.id))
            
            chapter_obj, _ = models.LearnerExamChapters.objects.get_or_create(learner_exam=learner_exam_obj, chapter=chapterobj, subject=subject_obj)
            
            chaper_subject_obj, _ = models.LearnerExamSubjects.objects.get_or_create(learner_exam=learner_exam_obj, subject=subject_obj)
            if assessmentpaper_obj.paper_type == 'practice':
                chaper_paper_subject_obj = None
                chapter_paper_obj = None
                
                chaper_practice_subject_obj, _ = models.LearnerExamPracticeSubjects.objects.get_or_create(learner_exam=learner_exam_obj, subject=subject_obj)
                
                chapter_practice_obj, _ = models.LearnerExamPracticeChapters.objects.get_or_create(learner_exam=learner_exam_obj, chapter=chapterobj, subject=subject_obj)
            else:
                chaper_practice_subject_obj = None
                chapter_practice_obj = None
                chaper_paper_subject_obj, _ = models.LearnerExamPaperSubjects.objects.get_or_create(learner_exam=learner_exam_obj, subject=subject_obj)
                chapter_paper_obj, _ = models.LearnerExamPaperChapters.objects.get_or_create(learner_exam=learner_exam_obj, chapter=chapterobj, subject=subject_obj)
           
            chaper_subject_obj.chapters.add(chapter_obj)
            chaper_subject_obj.save()
            chapter_obj.total_marks += chapter['total']
            chapter_obj.score += chapter['score']
            chapter_obj.attempted += chapter['attempted']
            chapter_obj.correct += chapter['correct']
            chapter_obj.incorrect += chapter['incorrect']
            chapter_obj.unchecked += chapter['unchecked']
            chapter_obj.save()
            if chapter_obj.total_marks == 0:
                chapter_obj.percentage = 0
            else:
                chapter_obj.percentage = (chapter_obj.score * 100) / chapter_obj.total_marks
            chapter_obj.save()
            if chapter_practice_obj:
                chaper_practice_subject_obj.chapters.add(chapter_practice_obj)
                chaper_practice_subject_obj.save()
                chapter_practice_obj.total_marks += chapter['total']
                chapter_practice_obj.score += chapter['score']
                chapter_practice_obj.attempted += chapter['attempted']
                chapter_practice_obj.correct += chapter['correct']
                chapter_practice_obj.incorrect += chapter['incorrect']
                chapter_practice_obj.unchecked += chapter['unchecked']
                chapter_practice_obj.save()
                if chapter_practice_obj.total_marks == 0:
                    chapter_practice_obj.percentage = 0
                else:
                    chapter_practice_obj.percentage = (chapter_practice_obj.score * 100) / chapter_practice_obj.total_marks
                chapter_practice_obj.save()
            else:
                chaper_paper_subject_obj.chapters.add(chapter_paper_obj)
                chaper_paper_subject_obj.save()
                chapter_paper_obj.total_marks += chapter['total']
                chapter_paper_obj.score += chapter['score']
                chapter_paper_obj.attempted += chapter['attempted']
                chapter_paper_obj.correct += chapter['correct']
                chapter_paper_obj.incorrect += chapter['incorrect']
                chapter_paper_obj.unchecked += chapter['unchecked']
                chapter_paper_obj.save()
                if chapter_paper_obj.total_marks == 0:
                    chapter_paper_obj.percentage = 0
                else:
                    chapter_paper_obj.percentage = (chapter_paper_obj.score * 100) / chapter_paper_obj.total_marks
                chapter_paper_obj.save()
        answer_paper.percentage = reports['percentage']
        answer_paper.total_questions = reports['totalquestion']
        answer_paper.attempted = reports['attempted']
        answer_paper.correct = reports['corrected']
        answer_paper.incorrect = reports['incorrected']
        answer_paper.unchecked = reports['unchecked']
        answer_paper.save()
        examObj = course_models.Exam.objects.get(id=int(assessmentpaper_obj.learner_exam.exam.id))
        # learnerexam_history_obj = models.LearnerExamHistory.objects.get(user=self.request.user, exam=examObj)
        learnerexam_history_obj, _ = models.LearnerExamHistory.objects.get_or_create(user=self.request.user, exam=examObj)
        # learner_history_obj = models.LearnerHistory.objects.get(user=self.request.user)
        learner_history_obj, _ = models.LearnerHistory.objects.get_or_create(user=self.request.user)
        
        temporary_bookmarks_obj = models.TemporaryLearnerBookmarks.objects.filter(paper=assessmentpaper_obj)
        for bookmark in temporary_bookmarks_obj:
            # exam_subject_obj = models.LearnerExamSubjects.objects.get(learner_exam=bookmark.learner_exam, subject=bookmark.subject)
            exam_subject_obj, _ = models.LearnerExamSubjects.objects.get_or_create(learner_exam=bookmark.learner_exam, subject=bookmark.subject)
            # exam_chapter_obj = models.LearnerExamChapters.objects.get(learner_exam=bookmark.learner_exam, chapter=bookmark.chapter, subject=bookmark.subject)
            exam_chapter_obj, _ = models.LearnerExamChapters.objects.get_or_create(learner_exam=bookmark.learner_exam, chapter=bookmark.chapter, subject=bookmark.subject)
            bookmark_obj = models.LearnerBookmarks.objects.create(learner_exam=bookmark.learner_exam, subject=bookmark.subject, question=bookmark.question, chapter=bookmark.chapter)
            assessmentpaper_obj.bookmarks.add(bookmark_obj)
            assessmentpaper_obj.save()
            exam_subject_obj.total_bookmarks += 1
            exam_subject_obj.save()
            exam_chapter_obj.total_bookmarks += 1
            exam_chapter_obj.save()
        models.TemporaryLearnerBookmarks.objects.filter(paper=assessmentpaper_obj).delete()
        if assessmentpaper_obj.paper_type == 'practice':
            # learnerexam_practice_history_obj = models.LearnerExamPracticeHistory.objects.get(user=self.request.user, exam=examObj)
            learnerexam_practice_history_obj, _ = models.LearnerExamPracticeHistory.objects.get_or_create(user=self.request.user, exam=examObj)
            learnerexam_history_obj.total_practice_time = learnerexam_history_obj.total_practice_time + answer_paper.time_taken
            learnerexam_history_obj.save()
            learnerexam_practice_history_obj.total_time = learnerexam_practice_history_obj.total_time + assessmentpaper_obj.total_time
            learnerexam_practice_history_obj.time_taken = learnerexam_practice_history_obj.time_taken + answer_paper.time_taken
            learnerexam_practice_history_obj.total_marks = learnerexam_practice_history_obj.total_marks + reports['totalscore']
            learnerexam_practice_history_obj.score = learnerexam_practice_history_obj.score + reports['score']
            learnerexam_practice_history_obj.attempted = learnerexam_practice_history_obj.attempted + reports['attempted']
            learnerexam_practice_history_obj.correct = learnerexam_practice_history_obj.correct + reports['corrected']
            learnerexam_practice_history_obj.skipped = learnerexam_practice_history_obj.skipped + reports['skipped']
            learnerexam_practice_history_obj.incorrect = learnerexam_practice_history_obj.incorrect + reports['incorrected']
            learnerexam_practice_history_obj.unchecked = learnerexam_practice_history_obj.unchecked + reports['unchecked']
            learnerexam_practice_history_obj.total_questions = learnerexam_practice_history_obj.total_questions + reports['totalquestion']
            learnerexam_practice_history_obj.save()
            if learnerexam_practice_history_obj.total_marks == 0:
                learnerexam_practice_history_obj.percentage = 0
            else:
                learnerexam_practice_history_obj.percentage = (learnerexam_practice_history_obj.score * 100) / learnerexam_practice_history_obj.total_marks
            learnerexam_practice_history_obj.save()
            learner_history_obj.total_practice_time = learner_history_obj.total_practice_time + answer_paper.time_taken
            # learner_history_obj.total_questions += reports['totalquestion']
            learner_history_obj.save()
        else:
            # learnerexam_paper_history_obj = models.LearnerExamPaperHistory.objects.get(user=self.request.user, exam=examObj)
            learnerexam_paper_history_obj, _ = models.LearnerExamPaperHistory.objects.get_or_create(user=self.request.user, exam=examObj)
            learnerexam_history_obj.total_paper_time = learnerexam_history_obj.total_paper_time + answer_paper.time_taken
            learnerexam_history_obj.save()
            learnerexam_paper_history_obj.total_time = learnerexam_paper_history_obj.total_time + assessmentpaper_obj.total_time
            learnerexam_paper_history_obj.time_taken = learnerexam_paper_history_obj.time_taken + answer_paper.time_taken
            learnerexam_paper_history_obj.total_marks = learnerexam_paper_history_obj.total_marks + reports['totalscore']
            learnerexam_paper_history_obj.score = learnerexam_paper_history_obj.score + reports['score']
            learnerexam_paper_history_obj.attempted = learnerexam_paper_history_obj.attempted + reports['attempted']
            learnerexam_paper_history_obj.correct = learnerexam_paper_history_obj.correct + reports['corrected']
            learnerexam_paper_history_obj.skipped = learnerexam_paper_history_obj.skipped + reports['skipped']
            learnerexam_paper_history_obj.incorrect = learnerexam_paper_history_obj.incorrect + reports['incorrected']
            learnerexam_paper_history_obj.unchecked = learnerexam_paper_history_obj.unchecked + reports['unchecked']
            learnerexam_paper_history_obj.total_questions = learnerexam_paper_history_obj.total_questions + reports['totalquestion']
            learnerexam_paper_history_obj.save()
            if learnerexam_paper_history_obj.total_marks == 0:
                learnerexam_paper_history_obj.percentage = 0
            else:
                learnerexam_paper_history_obj.percentage = (learnerexam_paper_history_obj.score * 100) / learnerexam_paper_history_obj.total_marks
            learnerexam_paper_history_obj.save()
            learner_history_obj.total_paper_time = learner_history_obj.total_paper_time + answer_paper.time_taken
            # learner_history_obj.total_questions += reports['totalquestion']
            learner_history_obj.save()
        # models.TemporaryPaperSubjectQuestionDistribution.objects.filter(learner_paper=assessmentpaper_obj).delete()
        return Response({'status': 'Assessment Paper Processing Completed.'}, status=status.HTTP_200_OK)

class ProcessMentorPaperPostSubmitView(CreateAPIView):
    serializer_class = serializers.QuestionSerializer
    permission_classes = [IsAuthenticated,]

    def create(self, request, *args, **kwargs):
        assessmentpaper_obj = models.MentorPapers.objects.get(id=self.kwargs.get('assessmentpaper_id'))
        
        reports = content_utils.get_mentor_paper_student_assessment_report(self.request.user, assessmentpaper_obj.id)
        answer_paper = models.MentorPaperAnswerPaper.objects.filter(user=self.request.user, mentor_paper=assessmentpaper_obj).last()
       
        answer_paper.score = reports['score']
        answer_paper.percentage = reports['percentage']
        answer_paper.total_questions = reports['totalquestion']
        answer_paper.attempted = reports['attempted']
        answer_paper.correct = reports['corrected']
        answer_paper.incorrect = reports['incorrected']
        answer_paper.unchecked = reports['unchecked']
        answer_paper.save()
        batch_obj = models.Batch.objects.get(id=int(assessmentpaper_obj.batch.id))
        if batch_obj:
            # learner_batch_history_obj = models.LearnerBatchHistory.objects.get(batch=batch_obj, user=self.request.user)
            learner_batch_history_obj, _ = models.LearnerBatchHistory.objects.get_or_create(batch=batch_obj, user=self.request.user)
            learner_batch_history_obj.total_questions += answer_paper.total_questions
            if assessmentpaper_obj.paper_type == 'paper':
                learner_batch_history_obj.total_paper_count += 1
                learner_batch_history_obj.total_paper_time_taken += answer_paper.time_taken
                learner_batch_history_obj.paper_score += answer_paper.score
                learner_batch_history_obj.total_paper_marks += assessmentpaper_obj.marks
                learner_batch_history_obj.total_paper_time += assessmentpaper_obj.total_time
                learner_batch_history_obj.total_attempted_paper += answer_paper.attempted
                learner_batch_history_obj.total_correct_paper += answer_paper.correct
                learner_batch_history_obj.total_incorrect_paper += answer_paper.incorrect
                learner_batch_history_obj.save()
                if learner_batch_history_obj.total_paper_marks == 0:
                    learner_batch_history_obj.paper_percentage = 0
                else:
                    learner_batch_history_obj.paper_percentage = (learner_batch_history_obj.paper_score * 100) / learner_batch_history_obj.total_paper_marks
            else:
                learner_batch_history_obj.total_practice_count += 1
                learner_batch_history_obj.total_practice_time_taken += answer_paper.time_taken
                learner_batch_history_obj.practice_score += answer_paper.score
                learner_batch_history_obj.total_practice_marks += assessmentpaper_obj.marks
                learner_batch_history_obj.total_practice_time += assessmentpaper_obj.total_time
                learner_batch_history_obj.total_attempted_practice += answer_paper.attempted
                learner_batch_history_obj.total_correct_practice += answer_paper.correct
                learner_batch_history_obj.total_incorrect_practice += answer_paper.incorrect
                learner_batch_history_obj.save()
                if learner_batch_history_obj.total_practice_marks == 0:
                    learner_batch_history_obj.practice_percentage = 0
                else:
                    learner_batch_history_obj.practice_percentage = (learner_batch_history_obj.practice_score * 100) / learner_batch_history_obj.total_practice_marks
                
        learner_batch_history_obj.save()
        temporary_bookmarks_obj = models.TemporaryMentorPaperLearnerBookmarks.objects.filter(paper=answer_paper)
        for bookmark in temporary_bookmarks_obj:
            # exam_subject_obj = models.LearnerExamSubjects.objects.get(learner_exam=bookmark.learner_exam, subject=bookmark.subject)
            exam_subject_obj, _ = models.LearnerExamSubjects.objects.get_or_create(learner_exam=bookmark.learner_exam, subject=bookmark.subject)
            # exam_chapter_obj = models.LearnerExamChapters.objects.get(learner_exam=bookmark.learner_exam, chapter=bookmark.chapter, subject=bookmark.subject)
            exam_chapter_obj, _ = models.LearnerExamChapters.objects.get_or_create(learner_exam=bookmark.learner_exam, chapter=bookmark.chapter, subject=bookmark.subject)
            bookmark_obj = models.LearnerBookmarks.objects.create(learner_exam=bookmark.learner_exam, subject=bookmark.subject, question=bookmark.question, chapter=bookmark.chapter)
            answer_paper.bookmarks.add(bookmark_obj)
            answer_paper.save()
            exam_subject_obj.total_bookmarks += 1
            exam_subject_obj.save()
            exam_chapter_obj.total_bookmarks += 1
            exam_chapter_obj.save()
        models.TemporaryMentorPaperLearnerBookmarks.objects.filter(paper=answer_paper).delete()
        return Response({'status': 'Mentor Assessment Paper Processing Completed.'}, status=status.HTTP_200_OK)

class PostAnswerView(CreateAPIView):
    serializer_class = serializers.PostAnswerSerializer
    response_serializer_class = serializers.UserAnswerSerializer
    permission_classes = [IsAuthenticated,]

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        answer_paper = models.AnswerPaper.objects.get(id=request.data['answer_paper'])
        question = models.Question.objects.get(id=request.data['question'])
        user_answer = models.UserAnswer.objects.filter(answer_paper=answer_paper, question=question)
        if request.data['is_cleared']:
            answer_paper.question_answered.remove(question)
            answer_paper.question_unanswered.add(question)
            answer_paper.question_markforreview.remove(question)
            answer_paper.question_save_markforreview.remove(question)
            if user_answer:
                user_answer[0].delete()
        else:
            answer_paper.question_unanswered.remove(question)
            answer_paper.question_answered.add(question)
            answer_paper.question_markforreview.remove(question)
            answer_paper.question_save_markforreview.remove(question)
        if request.data['mark_for_review']:
            answer_paper.question_markforreview.add(question)
        if request.data['save_mark_for_review']:
            answer_paper.question_save_markforreview.add(question)
            answer_paper.question_markforreview.remove(question)
        answer_paper.save()
        headers = self.get_success_headers(serializer.data)
        return Response(self.response_serializer_class(user_answer.last()).data, status=status.HTTP_201_CREATED, headers=headers)

class PostAnswerMentorPaperView(CreateAPIView):
    serializer_class = serializers.PostAnswerMentorPaperSerializer
    response_serializer_class = serializers.UserAnswerMentorPaperSerializer
    permission_classes = [IsAuthenticated,]

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        answer_paper = models.MentorPaperAnswerPaper.objects.get(id=request.data['answer_paper'])
        question = models.Question.objects.get(id=request.data['question'])
        user_answer = models.UserAnswerMentorPaper.objects.filter(answer_paper=answer_paper, question=question)
        if request.data['is_cleared']:
            answer_paper.question_answered.remove(question)
            answer_paper.question_unanswered.add(question)
            answer_paper.question_markforreview.remove(question)
            answer_paper.question_save_markforreview.remove(question)
            if user_answer:
                user_answer[0].delete()
        else:
            answer_paper.question_unanswered.remove(question)
            answer_paper.question_answered.add(question)
            answer_paper.question_markforreview.remove(question)
            answer_paper.question_save_markforreview.remove(question)
        if request.data['mark_for_review']:
            answer_paper.question_markforreview.add(question)
        if request.data['save_mark_for_review']:
            answer_paper.question_save_markforreview.add(question)
            answer_paper.question_markforreview.remove(question)
        answer_paper.save()
        headers = self.get_success_headers(serializer.data)
        return Response(self.response_serializer_class(user_answer.last()).data, status=status.HTTP_201_CREATED, headers=headers)

class AssessmentPaperReportView(ListAPIView):
    permission_classes = [IsAuthenticated,]

    def get_queryset(self):
        try:
            if self.request.query_params.get('user'):
                user= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                user = self.request.user
        except:
            user = self.request.user
        reports = content_utils.get_student_assessment_report(user, self.kwargs.get('assessmentpaper_id'))

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
        return Response({'error': 'Error in Assessment Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class MentorAssessmentPaperReportView(ListAPIView):
    permission_classes = [IsAuthenticated,]

    def get_queryset(self):
        try:
            user=None
            if self.request.query_params.get('user'):
                user= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                user = self.request.user
        except:
            user = self.request.user
        reports = content_utils.get_mentor_paper_student_assessment_report(user, self.kwargs.get('assessmentpaper_id'))

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
        return Response({'error': 'Error in Assessment Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class FetchAnswerPapersForMultipleLearnerpapersView(UpdateAPIView):
    serializer_class = serializers.AnswerPaperSerializer

    def put(self, request, *args, **kwargs):
        try:
            try:
                user=None
                if self.request.query_params.get('user'):
                    user= auth_models.User.objects.get(username=self.request.query_params.get('user'))
                else:
                    user = self.request.user
            except:
                user = self.request.user
            learnerPaperIds = request.data.get('papers')
            answer_paper_obj = models.AnswerPaper.objects.filter(user=user, assessment_paper__in=learnerPaperIds).order_by('-id')
        except:
            return Response({"message": "error in fetching papers"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(answer_paper_obj, many=True).data, status=201)

class SaveBookMarkView(UpdateAPIView):
    serializer_class = serializers.LearnerPaperSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        try:
            questionid = request.data.get('question')
            ques_obj = models.Question.objects.get(id=int(questionid))
        except:
            ques_obj = None
            # raise ParseError("Data with this id DoesNotExist")
        if not ques_obj:
            return Response({"message": "question with this id does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            paperid = request.data.get('paper')
            learner_paper_obj = models.LearnerPapers.objects.get(id=int(paperid))
        except:
            learner_paper_obj = None
            # raise ParseError("Data with this id DoesNotExist")
        if not learner_paper_obj:
            return Response({"message": "error in fetching paper details"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            subjectid = request.data.get('subject')
            subject_obj = course_models.Subject.objects.get(id=int(subjectid))
            # chapter
            tagIds = []
            ftags = ques_obj.linked_topics.all()
            tagIds = [tag.id for tag in ftags]
            # for tag in ques_obj.linked_topics.all():
            #     tagIds.append(tag.id)
            chapter_obj = course_models.Chapter.objects.filter(subject=subject_obj, topics__in=tagIds).last()
            learner_exam_obj = course_models.LearnerExams.objects.get(id=int(learner_paper_obj.learner_exam.id))
            chaper_subject_obj, _ = models.LearnerExamSubjects.objects.get_or_create(learner_exam=learner_exam_obj, subject=subject_obj)
            exam_chapter_obj, _ = models.LearnerExamChapters.objects.get_or_create(learner_exam=learner_exam_obj, chapter=chapter_obj, subject=subject_obj)
            try: 
                find_bookmark_obj = models.LearnerBookmarks.objects.get(learner_exam=learner_exam_obj, subject=subject_obj, question=ques_obj, chapter=chapter_obj)
            except:
                find_bookmark_obj = None
            try: 
                find_temp_bookmark_obj = models.TemporaryLearnerBookmarks.objects.get(learner_exam=learner_exam_obj, subject=subject_obj, question=ques_obj, chapter=chapter_obj)
            except:
                find_temp_bookmark_obj = None
            if find_temp_bookmark_obj:
                return Response({"message": "question already bookmarked in this exam"}, status=status.HTTP_400_BAD_REQUEST)
                
            if find_bookmark_obj:
                return Response({"message": "question already bookmarked in this exam"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                bookmark_obj = models.TemporaryLearnerBookmarks.objects.create(learner_exam=learner_exam_obj, paper=learner_paper_obj, subject=subject_obj, question=ques_obj, chapter=chapter_obj)
               
        return Response(self.serializer_class(learner_paper_obj).data, status=201)

class SaveMentorPaperBookMarkView(UpdateAPIView):
    serializer_class = serializers.MentorLearnerAnswerPaperSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        try:
            questionid = request.data.get('question')
            ques_obj = models.Question.objects.get(id=int(questionid))
        except:
            ques_obj = None
        if not ques_obj:
            return Response({"message": "question with this id does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            paperid = request.data.get('paper')
            learner_paper_obj = models.MentorPaperAnswerPaper.objects.get(id=int(paperid))
        except:
            learner_paper_obj = None
        if not learner_paper_obj:
            return Response({"message": "error in fetching paper details"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            subjectid = request.data.get('subject')
            subject_obj = course_models.Subject.objects.get(id=int(subjectid))
            # chapter
            tagIds = []
            for tag in ques_obj.linked_topics.all():
                tagIds.append(tag.id)
            chapter_obj = course_models.Chapter.objects.filter(subject=subject_obj, topics__in=tagIds).last()
            try:
                tmp_learner_exam_obj = course_models.LearnerExams.objects.filter(exam=learner_paper_obj.mentor_paper.exam.id, user=user)
            except:
                tmp_learner_exam_obj = None
            if not tmp_learner_exam_obj:
                learner_exam_obj = course_models.LearnerExams.objects.create(exam=learner_paper_obj.mentor_paper.exam.id, user=user, is_active=True)
            else:
                learner_exam_obj = course_models.LearnerExams.objects.get(exam=learner_paper_obj.mentor_paper.exam.id, user=user)
            try:
                tmp_exam_subject_obj = models.LearnerExamSubjects.objects.filter(learner_exam=learner_exam_obj, subject=subject_obj)
            except:
                tmp_exam_subject_obj = None
            if not tmp_exam_subject_obj:
                exam_subject_obj = models.LearnerExamSubjects.objects.create(learner_exam=learner_exam_obj, subject=subject_obj)
            else:
                chaper_subject_obj = models.LearnerExamSubjects.objects.get(learner_exam=learner_exam_obj, subject=subject_obj)
            
            exam_chapter_obj, _ = models.LearnerExamChapters.objects.get_or_create(learner_exam=learner_exam_obj, chapter=chapter_obj, subject=subject_obj)
            try: 
                find_bookmark_obj = models.LearnerBookmarks.objects.get(learner_exam=learner_exam_obj, subject=subject_obj, question=ques_obj, chapter=chapter_obj)
            except:
                find_bookmark_obj = None
            try: 
                find_temp_bookmark_obj = models.TemporaryMentorPaperLearnerBookmarks.objects.get(learner_exam=learner_exam_obj, subject=subject_obj, question=ques_obj, chapter=chapter_obj)
            except:
                find_temp_bookmark_obj = None
            if find_temp_bookmark_obj:
                return Response({"message": "question already bookmarked in this exam"}, status=status.HTTP_400_BAD_REQUEST)
                
            if find_bookmark_obj:
                return Response({"message": "question already bookmarked in this exam"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                bookmark_obj = models.TemporaryMentorPaperLearnerBookmarks.objects.create(learner_exam=learner_exam_obj, paper=learner_paper_obj, subject=subject_obj, question=ques_obj, chapter=chapter_obj)
            
        return Response(self.serializer_class(learner_paper_obj).data, status=201)

class FetchBookmarksViewSetViewSet(ListAPIView):
    queryset = models.LearnerBookmarks.objects.all()
    serializer_class = serializers.BookmarksSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        examid = self.request.query_params.get('exam')
        subjectid = self.request.query_params.get('subject')
        chapterid = self.request.query_params.get('chapter')
        if examid and subjectid and chapterid:
            exam_obj = course_models.LearnerExams.objects.get(id=int(examid))
            subject_obj = course_models.Subject.objects.get(id=int(subjectid))
            chapter_obj = course_models.Chapter.objects.get(id=int(chapterid))
            bookmark_obj = models.LearnerBookmarks.objects.filter(
                learner_exam=exam_obj, subject=subject_obj, chapter=chapter_obj)
            if bookmark_obj:
                return bookmark_obj
            else:
                return []

class LearnerExamChaptersViewSet(ListAPIView):
    queryset = models.LearnerExamChapters.objects.all()
    serializer_class = serializers.LearnerExamChapterSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        subject_id = self.request.query_params.get('subject')
        learner_exam_id = self.request.query_params.get('learnerexam')
        if not learner_exam_id:
            exam_id = self.request.query_params.get('exam')
            exam_obj = course_models.Exam.objects.get(id=int(exam_id))
            learner_exam_obj = course_models.LearnerExams.objects.get(user=user, exam=exam_obj)
        else:   
            learner_exam_obj = course_models.LearnerExams.objects.get(id=int(learner_exam_id))
        subject_obj = course_models.Subject.objects.get(id=int(subject_id))
        if not learner_exam_obj:
            raise ParseError("Learner Exam with this id DoesNotExist")
        chapter_obj = models.LearnerExamChapters.objects.filter(
            learner_exam=learner_exam_obj, subject=subject_obj)
        if chapter_obj:
            return chapter_obj
        else:
            return []

class LearnerExamSubjectsViewSet(ListAPIView):
    queryset = models.LearnerExamSubjects.objects.all()
    serializer_class = serializers.LearnerExamSubjectSerializer
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
        learner_exam_id = self.request.query_params.get('learnerexam')
        if not learner_exam_id:
            exam_id = self.request.query_params.get('exam')
            exam_obj = course_models.Exam.objects.get(id=int(exam_id))
            learner_exam_obj = course_models.LearnerExams.objects.get(user=user, exam=exam_obj)
        else:   
            learner_exam_obj = course_models.LearnerExams.objects.get(id=int(learner_exam_id))
        if not learner_exam_obj:
            raise ParseError("Learner Exam with this id DoesNotExist")
        subject_obj = models.LearnerExamSubjects.objects.filter(
            learner_exam=learner_exam_obj)
        if subject_obj:
            return subject_obj
        else:
            return []

class LearnerExamPracticeChaptersViewSet(ListAPIView):
    queryset = models.LearnerExamPracticeChapters.objects.all()
    serializer_class = serializers.LearnerExamPracticeChapterSerializer
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
        subject_id = self.request.query_params.get('subject')
        learner_exam_id = self.request.query_params.get('learnerexam')
        if not learner_exam_id:
            exam_id = self.request.query_params.get('exam')
            exam_obj = course_models.Exam.objects.get(id=int(exam_id))
            learner_exam_obj = course_models.LearnerExams.objects.get(user=user, exam=exam_obj)
        else:   
            learner_exam_obj = course_models.LearnerExams.objects.get(id=int(learner_exam_id))
        subject_obj = course_models.Subject.objects.get(id=int(subject_id))
        if not learner_exam_obj:
            raise ParseError("Learner Exam with this id DoesNotExist")
        chapter_obj = models.LearnerExamPracticeChapters.objects.filter(
            learner_exam=learner_exam_obj, subject=subject_obj)
        if chapter_obj:
            return chapter_obj
        else:
            return []

class LearnerExamPracticeSubjectsViewSet(ListAPIView):
    queryset = models.LearnerExamPracticeSubjects.objects.all()
    serializer_class = serializers.LearnerExamPracticeSubjectSerializer
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
        learner_exam_id = self.request.query_params.get('learnerexam')
        if not learner_exam_id:
            exam_id = self.request.query_params.get('exam')
            exam_obj = course_models.Exam.objects.get(id=int(exam_id))
            learner_exam_obj = course_models.LearnerExams.objects.get(user=user, exam=exam_obj)
        else:   
            learner_exam_obj = course_models.LearnerExams.objects.get(id=int(learner_exam_id))
        if not learner_exam_obj:
            raise ParseError("Learner Exam with this id DoesNotExist")
        subject_obj = models.LearnerExamPracticeSubjects.objects.filter(
            learner_exam=learner_exam_obj)
        if subject_obj:
            return subject_obj
        else:
            return []

class LearnerExamPaperChaptersViewSet(ListAPIView):
    queryset = models.LearnerExamPaperChapters.objects.all()
    serializer_class = serializers.LearnerExamPaperChapterSerializer
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
        subject_id = self.request.query_params.get('subject')
        learner_exam_id = self.request.query_params.get('learnerexam')
        if not learner_exam_id:
            exam_id = self.request.query_params.get('exam')
            exam_obj = course_models.Exam.objects.get(id=int(exam_id))
            learner_exam_obj = course_models.LearnerExams.objects.get(user=user, exam=exam_obj)
        else:   
            learner_exam_obj = course_models.LearnerExams.objects.get(id=int(learner_exam_id))
        subject_obj = course_models.Subject.objects.get(id=int(subject_id))
        if not learner_exam_obj:
            raise ParseError("Learner Exam with this id DoesNotExist")
        chapter_obj = models.LearnerExamPaperChapters.objects.filter(
            learner_exam=learner_exam_obj, subject=subject_obj)
        if chapter_obj:
            return chapter_obj
        else:
            return []

class LearnerExamPaperSubjectsViewSet(ListAPIView):
    queryset = models.LearnerExamPaperSubjects.objects.all()
    serializer_class = serializers.LearnerExamPaperSubjectSerializer
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
        learner_exam_id = self.request.query_params.get('learnerexam')
        if not learner_exam_id:
            exam_id = self.request.query_params.get('exam')
            exam_obj = course_models.Exam.objects.get(id=int(exam_id))
            learner_exam_obj = course_models.LearnerExams.objects.get(user=user, exam=exam_obj)
        else:   
            learner_exam_obj = course_models.LearnerExams.objects.get(id=int(learner_exam_id))
        if not learner_exam_obj:
            raise ParseError("Learner Exam with this id DoesNotExist")
        subject_obj = models.LearnerExamPaperSubjects.objects.filter(
            learner_exam=learner_exam_obj)
        if subject_obj:
            return subject_obj
        else:
            return []

class OverallLeaderboard(ListAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if not exam_id:
            raise ParseError("Please select any exam")
        try:    
            exam_obj = course_models.Exam.objects.get(id=int(exam_id))
        except:   
            exam_obj = None
        if not exam_obj:
            raise ParseError("Exam with this id DoesNotExist")
        leaderboard_data, my_data = content_utils.get_leaderboardpanda(exam_id, user=self.request.user)
        if not leaderboard_data:
            return None
        else:
            return leaderboard_data, my_data

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            return Response({
                'leaderboard_data':queryset[0],
                'my_data': queryset[1]
            })
        return Response({'error': 'Error in Fetching Leaderboard.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class PauseLearnePaperViewSet(UpdateAPIView):
    serializer_class = serializers.CardViewLearnerPaperSerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        try:
            remainingseconds = request.data.get('remainingSeconds')
            learner_paper_id = request.data.get('paper')
            if not learner_paper_id:
                raise ParseError("Please enter paper id")
            else:   
                learner_paper_obj = models.LearnerPapers.objects.get(id=int(learner_paper_id))
            if not learner_paper_obj:
                raise ParseError("Learner Paper with this id DoesNotExist")
            if learner_paper_obj.pause_count >= 2:
                raise ParseError("Maximum 2 pause are allowed")
            learner_paper_obj.pause_count += 1
            learner_paper_obj.remaining_time = remainingseconds
            learner_paper_obj.save()
        except:
            return Response({"message": "Maximum 2 pause are allowed"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(learner_paper_obj).data, status=201)

class ResumeLearnePaperViewSet(UpdateAPIView):
    serializer_class = serializers.CardViewLearnerPaperSerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        try:
            remainingseconds = request.data.get('remainingSeconds')
            learner_paper_id = request.data.get('paper')
            if not learner_paper_id:
                raise ParseError("Please enter paper id")
            else:   
                learner_paper_obj = models.LearnerPapers.objects.get(id=int(learner_paper_id))
            if not learner_paper_obj:
                raise ParseError("Learner Paper with this id DoesNotExist")
            learner_paper_obj.remaining_time = remainingseconds
            if learner_paper_obj.remaining_time > 0:
                learner_paper_obj.submitted = False
            learner_paper_obj.save()
        except:
            return Response({"message": "error in resuming the exam"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(learner_paper_obj).data, status=201)

class PauseLearnerMentorPaperViewSet(UpdateAPIView):
    serializer_class = serializers.MentorLearnerAnswerPaperSerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        try:
            remainingseconds = request.data.get('remainingSeconds')
            learner_paper_id = request.data.get('paper')
            if not learner_paper_id:
                raise ParseError("Please enter paper id")
            else:   
                learner_paper_obj = models.MentorPaperAnswerPaper.objects.get(id=int(learner_paper_id))
            if not learner_paper_obj:
                raise ParseError("Learner Paper with this id DoesNotExist")
            if learner_paper_obj.pause_count >= 2:
                raise ParseError("Maximum 2 pause are allowed")
            learner_paper_obj.pause_count += 1
            learner_paper_obj.remaining_time = remainingseconds
            learner_paper_obj.save()
        except:
            return Response({"message": "Maximum 2 pause are allowed"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(learner_paper_obj).data, status=201)

class ResumeLearnerMentorPaperViewSet(UpdateAPIView):
    serializer_class = serializers.MentorLearnerAnswerPaperSerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        try:
            remainingseconds = request.data.get('remainingSeconds')
            learner_paper_id = request.data.get('paper')
            if not learner_paper_id:
                raise ParseError("Please enter paper id")
            else:   
                learner_paper_obj = models.MentorPaperAnswerPaper.objects.get(id=int(learner_paper_id))
            if not learner_paper_obj:
                raise ParseError("Learner Paper with this id DoesNotExist")
            learner_paper_obj.remaining_time = remainingseconds
            if learner_paper_obj.remaining_time > 0:
                learner_paper_obj.submitted = False
            learner_paper_obj.save()
        except:
            return Response({"message": "error in resuming the exam"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(learner_paper_obj).data, status=201)

class AssessmentPaperAnswersHistoryView(ListAPIView, CreateAPIView):
    serializer_class = serializers.QuestionSerializer
    permission_classes = [IsAuthenticated,]

    def get_queryset(self):
        questions , question_data = content_utils.get_assessment_answers_history(self.request.user, self.kwargs.get('assessmentpaper_id'))
        if not questions:
            # return blank queryset if questions not received
            return models.Question.objects.filter(id=None)
        return questions, question_data

    def list(self, request, *args, **kwargs):
        assessmentpaper_obj = models.LearnerPapers.objects.get(id=self.kwargs.get('assessmentpaper_id'))
        answer_paper_obj = models.AnswerPaper.objects.filter(user=self.request.user ,assessment_paper=assessmentpaper_obj)
        assessmentpaperdetails = serializers.LearnerPaperSerializer(assessmentpaper_obj, context={'request': request})
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            serializer = self.get_serializer(queryset[0], many=True)
            answer_paper_obj = models.AnswerPaper.objects.filter(user=self.request.user ,assessment_paper=assessmentpaper_obj)
            if answer_paper_obj:
                answer_paper = answer_paper_obj.last().id
                return Response({
                    # 'assessmentpaperdetails':assessmentpaperdetails.data,
                    'answer_paper':answer_paper,
                    # 'attempt_order':1,
                    'question_data':queryset[1],
                    'questions': queryset[0]
                })
        return Response({'error': 'Error in Assessment Test Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class PostQuerySuggestiveQuestionsViewSet(ListAPIView, CreateAPIView):
    serializer_class = serializers.PostQueryQuestionsSerializer
    create_class = serializers.PostQueryQuestionsSerializer

    def get_queryset(self):
        queries = models.PostQuerySuggestiveQuestions.objects.all()
        if queries:
            return queries
        else:
            return []

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class EditPostQuerySuggestiveQuestionViewSet(RetrieveUpdateAPIView):
    queryset = models.PostQuerySuggestiveQuestions.objects.all()
    serializer_class = serializers. PostQueryQuestionsSerializer
    update_serializer_class = serializers.PostQueryQuestionsSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        question = models.PostQuerySuggestiveQuestions.objects.filter(pk=self.kwargs.get('pk'))
        if not question:
            raise ParseError("Question with this id DoesNotExist")
        return question

    def update(self, request, *args, **kwargs):
        question = models.PostQuerySuggestiveQuestions.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            question, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(question).data, status=status.HTTP_200_OK)

class CreateUserQueryViewSet(ListAPIView, CreateAPIView):
    # permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.LearnerQuerySerializer
    create_class = serializers.LearnerQuerySerializer

    def get_queryset(self):
        user=self.request.user
        queries = models.LearnerQuery.objects.filter(user=user)
        if queries:
            return queries
        else:
            return []
        # return models.LearnerQuery.objects.all().order_by('id')

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class FetchUserQueriesViewSet(ListAPIView,):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.LearnerQuerySerializer
    pagination_class = core_paginations.CustomPagination

    def get_queryset(self):
        queries = models.LearnerQuery.objects.all()
        if queries:
            return queries
        else:
            return []

class SubjectiveAnswerImageView(CreateAPIView):
    serializer_class = serializers.PostUserSubjectiveAnswerImageSerializer
    permission_classes = [IsAuthenticated, permissions.IsStudent]

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        subjective_image = serializer.save()

        return Response(serializers.UserSubjectiveAnswerImageSerializer(subjective_image).data, status=status.HTTP_201_CREATED)

class BatchViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.ViewBatchSerializer
    create_class = serializers.CreateBatchSerializer

    def get_queryset(self):
        user = self.request.user
        batches = models.Batch.objects.filter(teacher=user, is_active=True)
        if batches:
            return batches
        else:
            return []
        # return models.LearnerQuery.objects.all().order_by('id')

    def create(self, request, *args, **kwargs):
        serializer = self.create_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EditBatchViewSet(RetrieveUpdateAPIView):
    queryset = models.Batch.objects.all()
    serializer_class = serializers.ViewBatchSerializer
    update_serializer_class = serializers.CreateBatchSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        batch = models.Batch.objects.filter(pk=self.kwargs.get('pk'))
        if not batch:
            raise ParseError("Batch with this id DoesNotExist")
        return batch

    def update(self, request, *args, **kwargs):
        batch = models.Batch.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            batch, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(batch).data, status=status.HTTP_200_OK)

class SearchMentorBatchViewSetViewSet(ListAPIView):
    queryset = models.Batch.objects.all()
    serializer_class = serializers.ViewBatchSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        searchtext = self.request.query_params.get('code')
        if searchtext:
            try:
                batch_obj = models.Batch.objects.filter(
                batch_code=searchtext, is_active=True)
            except:
                batch_obj = None
            return batch_obj

class JoinBatchViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.LearnerBatchSerializer
    create_class = serializers.LearnerBatchSerializer

    def get_queryset(self):
        user = self.request.user
        # batches = models.LearnerBatches.objects.filter(user=user, batch__is_active=True)
        batches = models.LearnerBatches.objects.filter(user=user, is_active=True)
        if batches:
            return batches
        else:
            return []
        # return models.LearnerQuery.objects.all().order_by('id')

    def create(self, request, *args, **kwargs):
        serializer = self.create_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class MakeMentorPaperView(UpdateAPIView):
    serializer_class = serializers.MentorPaperSerializer

    def put(self, request, *args, **kwargs):
        # topicIds = []
        user = self.request.user
        subjectIds = []
        exam = request.data.get('exam', None)
        if not exam:
            return Response({"message": "Invalid exam request"}, status=status.HTTP_400_BAD_REQUEST)
        exam_obj = course_models.Exam.objects.get(id=int(exam))
        if not exam_obj:
            return Response({"message": "Exam not found"}, status=status.HTTP_400_BAD_REQUEST)
        if not exam_obj.is_active:
            mentorexamtmpobj = course_models.MentorExams.objects.get(user=user, exam=exam_obj)
            if mentorexamtmpobj:
                mentorexamtmpobj.is_active=False
                mentorexamtmpobj.save()
            return Response({"message": "Oops! Exam has been deactivated by admin"}, status=status.HTTP_400_BAD_REQUEST)
        
        chapters = request.data.get('chapters')
        paper_type = request.data.get('type')
        show_time = request.data.get('show_time')
        chapters_obj = course_models.Chapter.objects.filter(id__in=chapters)
        subjectIds.extend(chapters_obj.values_list("subject", flat=True))
        # topicIds.extend(chapters_obj.values_list("topics", flat=True).all())
        try:
            total_ques = int(request.data.get('totalQues'))
        except:
            total_ques = 0
        try:
            batch_obj = models.Batch.objects.get(id=int(request.data.get('batch')))
        except:
            return Response({"message": "Batch not found"}, status=status.HTTP_400_BAD_REQUEST)
        if paper_type == ExamType.PAPER:
            batch_papercount_obj, _ = models.BatchTotalActualPapers.objects.get_or_create(batch=batch_obj)
            total_time = request.data.get('totalTime')
            batch_papercount_obj.count += 1
            batch_papercount_obj.save()
            count = batch_papercount_obj.count
        else:
            batch_practicecount_obj, _ = models.BatchTotalPracticePapers.objects.get_or_create(batch=batch_obj)
            total_time = 12000
            batch_practicecount_obj.count += 1
            batch_practicecount_obj.save()
            count = batch_practicecount_obj.count
        mentor_paper_obj = models.MentorPapers.objects.create(mentor=user, exam=exam_obj, batch=batch_obj, paper_type=paper_type, paper_count=count, show_time=show_time)
        if paper_type == ExamType.PRACTICE:
            mentor_paper_obj.chapters.add(*chapters)
            mentor_paper_obj.save()
        try:
            start_date = request.data.get('startDate')
            start_time = request.data.get('startTime')
            if not start_date or not start_time:
                if mentor_paper_obj.paper_type == 'paper':
                    batch_papercount_obj.count -= 1
                    batch_papercount_obj.save()
                else:
                    batch_practicecount_obj.count -= 1
                    batch_practicecount_obj.save()
                mentor_paper_obj.delete()
                return Response({"message": "Start Date and Time is required"}, status=status.HTTP_400_BAD_REQUEST)
            mentor_paper_obj.exam_start_date_time = content_utils.formatDateTime(start_date, start_time) if(
            start_date and start_time) else None
        except:
            mentor_paper_obj.exam_start_date_time = None
        try:
            end_date = request.data.get('endDate')
            end_time = request.data.get('endTime')
            if paper_type == ExamType.PAPER:
                if not end_date or not end_time:
                    if mentor_paper_obj.paper_type == 'paper':
                        batch_papercount_obj.count -= 1
                        batch_papercount_obj.save()
                    else:
                        batch_practicecount_obj.count -= 1
                        batch_practicecount_obj.save()
                    mentor_paper_obj.delete()
                    return Response({"message": "End Date and Time is required"}, status=status.HTTP_400_BAD_REQUEST)
            mentor_paper_obj.exam_end_date_time = content_utils.formatDateTime(end_date, end_time) if(
            end_date and end_time) else None
        except:
            mentor_paper_obj.exam_end_date_time = None
        if mentor_paper_obj.exam_end_date_time and mentor_paper_obj.exam_start_date_time > mentor_paper_obj.exam_end_date_time:
                if mentor_paper_obj.paper_type == 'paper':
                    batch_papercount_obj.count -= 1
                    batch_papercount_obj.save()
                else:
                    batch_practicecount_obj.count -= 1
                    batch_practicecount_obj.save()
                mentor_paper_obj.delete()
                return Response({"message": "Start date can not be greater than end date"}, status=status.HTTP_400_BAD_REQUEST)
        currenttime = timezone.now()
        exam_start_date_time = mentor_paper_obj.exam_start_date_time
        if exam_start_date_time < currenttime:
            
            if mentor_paper_obj.paper_type == 'paper':
                    batch_papercount_obj.count -= 1
                    batch_papercount_obj.save()
            else:
                batch_practicecount_obj.count -= 1
                batch_practicecount_obj.save()
            mentor_paper_obj.delete()
            return Response({"message": "Start Date can not be in past"}, status=status.HTTP_400_BAD_REQUEST)
        mentor_paper_obj.save()
        mentor_paper_obj.subjects.add(*subjectIds)
        mentor_paper_obj.save()
        
        question_types = request.data.get('quesTypes', None)
        difficulty = request.data.get('difficulty', 1)
        range1 = [1,2,3]
        range2 = [4,5,6,7]
        range3 = [8,9,10]
        allRange = [1,2,3,4,5,6,7,8,9,10]
        selectedRange = []
        if difficulty in range1:
            selectedRange = range1
        elif difficulty in range2:
            selectedRange = range2
        else:
            selectedRange = range3
        try:
            if request.data.get('anydifficulty'):
                selectedRange = DifficultyRange.allRange
        except:
            selectedRange = selectedRange
        eng_obj = models.QuestionLanguage.objects.get(text='English')
        try:
            
            questions = QuestionDistribution.get_equally_distributed_subjectwise_questions(
               mentor_paper_obj.id, 'mentorpaper', subjectIds, selectedRange, chapters,  total_ques, eng_obj, question_types
            )
            logger.info(f"Questions count {len(questions)}")
            
            if len(questions) == 0:
                if mentor_paper_obj.paper_type == 'paper':
                    batch_papercount_obj.count -= 1
                    batch_papercount_obj.save()
                else:
                    batch_practicecount_obj.count -= 1
                    batch_practicecount_obj.save()
                mentor_paper_obj.delete()
                return Response({"message": "No questions found"}, status=status.HTTP_400_BAD_REQUEST)
            mentor_paper_obj.total_time = total_time
            mentor_paper_obj.questions.add(*list(questions))
            mentor_paper_obj.save()

            total_marks = 0
            instruction_ques = "Total Questions: " + str(len(mentor_paper_obj.questions.all()))
            paper_instruction_obj3 = models.MentorPaperInstructions.objects.create(paper=mentor_paper_obj,instruction=instruction_ques)
            if mentor_paper_obj.paper_type == 'paper':
                instruction_time = "Total Time (in Min): " + str(total_time)
                paper_instruction_obj = models.MentorPaperInstructions.objects.create(paper=mentor_paper_obj,instruction=instruction_time)
            if exam:
                paper_instruction_obj2 = models.MentorPaperInstructions.objects.create(paper=mentor_paper_obj)
                
                distribution_based_on_type = QuestionDistribution.distribute_based_on_type_of_questions(
                    mentor_paper_obj.questions.all()
                )
                
                total_marks_grouped_by_exam_type_of_question = course_models.QuestionType.objects.filter(
                    exam=exam_obj, 
                    type_of_question__in=[mentor_paper_obj.questions.all().values_list("type_of_question", flat=True)],
                ).exclude(type_of_question="subjective").values("exam", "type_of_question"
                ).order_by("exam").annotate(total_marks=Sum("marks"))
                
                for marks in total_marks_grouped_by_exam_type_of_question:
                    multiplier = distribution_based_on_type.get(marks["type_of_question"], 0)    
                    total_marks += marks["total_marks"]*multiplier
                instruction_marks = "Max. Marks: " + str(total_marks)
                mentor_paper_obj.marks = total_marks
                mentor_paper_obj.save()
                paper_instruction_obj2.instruction = instruction_marks
                paper_instruction_obj2.save()
                teacher_profile = profiles_models.Profile.objects.get(user=batch_obj.teacher)
                notification_type = NotificationType.objects.get(name="admin")
                for student in batch_obj.students.all():
                    if batch_obj.institute_room:
                        if mentor_paper_obj.paper_type == 'paper':
                            notification_text  = "Paper created and shared in batch: " + batch_obj.institute_room.grade.name + " - " + batch_obj.institute_room.name
                            message = "Mentor " + teacher_profile.first_name + " has created and shared a paper in your batch " + batch_obj.institute_room.grade.name + " - " + batch_obj.institute_room.name
                        else:
                            notification_text  = "Practice paper created and shared in batch: " + batch_obj.institute_room.grade.name + " - " + batch_obj.institute_room.name
                            message = "Mentor " + teacher_profile.first_name + " has created and shared a practice paper in your batch " + batch_obj.institute_room.grade.name + " - " + batch_obj.institute_room.name
                    else:
                        if mentor_paper_obj.paper_type == 'paper':
                            notification_text  = "Paper created and shared in batch: " + batch_obj.name
                            message = "Mentor " + teacher_profile.first_name + " has created and shared a paper in your batch " + batch_obj.name
                        else:
                            notification_text  = "Practice paper created and shared in batch: " + batch_obj.name
                            message = "Mentor " + teacher_profile.first_name + " has created and shared a practice paper in your batch " + batch_obj.name
                    Notifications.objects.create(user=student, mentor_paper=mentor_paper_obj, batch=batch_obj, notification=message, subject=notification_text, type=notification_type)
        except:
            if mentor_paper_obj.paper_type == 'paper':
                batch_papercount_obj.count -= 1
                batch_papercount_obj.save()
            else:
                batch_practicecount_obj.count -= 1
                batch_practicecount_obj.save()
            mentor_paper_obj.delete()
            return Response({"message": "error in fetching questions"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(mentor_paper_obj).data, status=201)

class TemporaryBookmarkSetViewSet(ListAPIView):
    queryset = models.TemporaryLearnerBookmarks.objects.all()
    serializer_class = serializers.TemporaryBookmarksSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        paperid = self.request.query_params.get('paper')
        if paperid:
            bookmark_obj = models.TemporaryLearnerBookmarks.objects.filter(paper=paperid)
            return bookmark_obj
        return self.queryset

class TemporaryBookmarkMentorPaperSetViewSet(ListAPIView):
    queryset = models.TemporaryMentorPaperLearnerBookmarks.objects.all()
    serializer_class = serializers.TemporaryMentorPaperBookmarksSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        paperid = self.request.query_params.get('paper')
        if paperid:
            try:
                bookmark_obj = models.TemporaryMentorPaperLearnerBookmarks.objects.filter(
                paper=paperid)
            except:
                bookmark_obj = None
            return bookmark_obj

class FetchMentorPapersViewSet(ListAPIView):
    queryset = models.MentorPapers.objects.all()
    serializer_class = serializers.CardViewMentorPaperSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = core_paginations.CustomPagination5

    def get_queryset(self):
        user = self.request.user
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            batch_obj = models.Batch.objects.get(id=int(batch_id))
            if batch_obj:
                learner_paper_obj = models.MentorPapers.objects.filter(batch=batch_obj)
            if not batch_obj:
                raise ParseError("Batch with this id DoesNotExist")
        if not batch_id:
            learner_paper_obj = models.MentorPapers.objects.filter(mentor=user)
        if learner_paper_obj:
            return learner_paper_obj
        else:
            return []

class FetchActualMentorPapersRelativeGrowthViewSet(ListAPIView):
    queryset = models.MentorPapers.objects.all()
    serializer_class = serializers.CardViewMentorPaperSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = core_paginations.CustomPagination10

    def get_queryset(self):
        user = self.request.user
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            batch_obj = models.Batch.objects.get(id=int(batch_id))
            if batch_obj:
                learner_paper_obj = models.MentorPapers.objects.filter(batch=batch_obj, paper_type='paper')
            if not batch_obj:
                raise ParseError("Batch with this id DoesNotExist")
        if not batch_id:
            learner_paper_obj = models.MentorPapers.objects.filter(mentor=user, paper_type='paper')
        if learner_paper_obj:
            return learner_paper_obj
        else:
            return []

class FetchMentorPapersFourInAPageViewSet(ListAPIView):
    queryset = models.MentorPapers.objects.all()
    serializer_class = serializers.CardViewMentorPaperSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = core_paginations.CustomPagination4

    def get_queryset(self):
        user = self.request.user
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            batch_obj = models.Batch.objects.get(id=int(batch_id))
            if batch_obj:
                learner_paper_obj = models.MentorPapers.objects.filter(batch=batch_obj)
            if not batch_obj:
                raise ParseError("Batch with this id DoesNotExist")
        if not batch_id:
            learner_paper_obj = models.MentorPapers.objects.filter(mentor=user)
        if learner_paper_obj:
            return learner_paper_obj
        else:
            return []

class FetchCompletedMentorPapersViewSet(ListAPIView):
    queryset = models.MentorPapers.objects.all()
    serializer_class = serializers.CardViewMentorPaperSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = core_paginations.CustomPagination5

    def get_queryset(self):
        user = self.request.user
        try:
            if self.request.query_params.get('user'):
                studentuser= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                studentuser = self.request.user
        except:
            studentuser = self.request.user
        batch_id = self.request.query_params.get('batch')
        mentorpaperids = []
        if batch_id:
            batch_obj = models.Batch.objects.get(id=int(batch_id))
            if not batch_obj:
                raise ParseError("Batch with this id DoesNotExist")
            if batch_obj:
                temp_learner_paper_obj = models.MentorPapers.objects.filter(batch=batch_obj)
                paperIds = []
                paperIds = [paper.id for paper in temp_learner_paper_obj]
                answer_paper = models.MentorPaperAnswerPaper.objects.filter(user=studentuser,
                    mentor_paper__in=paperIds)
                mentorpaperids = [paper.mentor_paper.id for paper in answer_paper]
                learner_paper_obj = models.MentorPapers.objects.filter(id__in=mentorpaperids)

        if not batch_id:
            learner_paper_obj = models.MentorPapers.objects.filter(mentor=user)
        if learner_paper_obj:
            return learner_paper_obj
        else:
            return []

class FetchCompletedMentorPapersFourInAPageViewSet(ListAPIView):
    queryset = models.MentorPapers.objects.all()
    serializer_class = serializers.CardViewMentorPaperSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = core_paginations.CustomPagination4

    def get_queryset(self):
        user = self.request.user
        try:
            if self.request.query_params.get('user'):
                studentuser= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                studentuser = self.request.user
        except:
            studentuser = self.request.user
        batch_id = self.request.query_params.get('batch')
        mentorpaperids = []
        if batch_id:
            batch_obj = models.Batch.objects.get(id=int(batch_id))
            if not batch_obj:
                raise ParseError("Batch with this id DoesNotExist")
            if batch_obj:
                temp_learner_paper_obj = models.MentorPapers.objects.filter(batch=batch_obj)
                paperIds = []
                paperIds = [paper.id for paper in temp_learner_paper_obj]
                answer_paper = models.MentorPaperAnswerPaper.objects.filter(user=studentuser,
                    mentor_paper__in=paperIds)
                mentorpaperids = [paper.mentor_paper.id for paper in answer_paper]
                learner_paper_obj = models.MentorPapers.objects.filter(id__in=mentorpaperids)

        if not batch_id:
            learner_paper_obj = models.MentorPapers.objects.filter(mentor=user)
        if learner_paper_obj:
            return learner_paper_obj
        else:
            return []

class FetchPendingMentorPapersViewSet(ListAPIView):
    queryset = models.MentorPapers.objects.all()
    serializer_class = serializers.CardViewMentorPaperSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = core_paginations.CustomPagination5

    def get_queryset(self):
        user = self.request.user
        try:
            if self.request.query_params.get('user'):
                studentuser= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                studentuser = self.request.user
        except:
            studentuser = self.request.user
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            batch_obj = models.Batch.objects.get(id=int(batch_id))
            if not batch_obj:
                raise ParseError("Batch with this id DoesNotExist")
            if batch_obj:

                currenttime = timezone.now()
                assessment_test_obj = models.MentorPapers.objects.filter(
                    batch=batch_obj)
                paperIds = []
                paperIds = [paper.id for paper in assessment_test_obj]
                answer_paper = models.MentorPaperAnswerPaper.objects.filter(user=studentuser,
                    mentor_paper__in=paperIds)
                attempted_mentor_papers_ids = [paper.mentor_paper.id for paper in answer_paper]
                learner_paper_obj = models.MentorPapers.objects.filter(
                    Q(batch=batch_obj, exam_end_date_time__gte=currenttime) | Q(batch=batch_obj, exam_end_date_time=None)).exclude(id__in=attempted_mentor_papers_ids)

        if not batch_id:
            learner_paper_obj = models.MentorPapers.objects.filter(mentor=user)
        if learner_paper_obj:
            return learner_paper_obj
        else:
            return []

class FetchPendingMentorPapersFourInAPageViewSet(ListAPIView):
    queryset = models.MentorPapers.objects.all()
    serializer_class = serializers.CardViewMentorPaperSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = core_paginations.CustomPagination4

    def get_queryset(self):
        user = self.request.user
        try:
            if self.request.query_params.get('user'):
                studentuser= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                studentuser = self.request.user
        except:
            studentuser = self.request.user
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            batch_obj = models.Batch.objects.get(id=int(batch_id))
            if not batch_obj:
                raise ParseError("Batch with this id DoesNotExist")
            if batch_obj:

                currenttime = timezone.now()
                assessment_test_obj = models.MentorPapers.objects.filter(
                    batch=batch_obj)
                paperIds = []
                paperIds = [paper.id for paper in assessment_test_obj]
                answer_paper = models.MentorPaperAnswerPaper.objects.filter(user=studentuser,
                    mentor_paper__in=paperIds)
                attempted_mentor_papers_ids = [paper.mentor_paper.id for paper in answer_paper]
                learner_paper_obj = models.MentorPapers.objects.filter(
                    Q(batch=batch_obj, exam_end_date_time__gte=currenttime) | Q(batch=batch_obj, exam_end_date_time=None)).exclude(id__in=attempted_mentor_papers_ids)

        if not batch_id:
            learner_paper_obj = models.MentorPapers.objects.filter(mentor=user)
        if learner_paper_obj:
            return learner_paper_obj
        else:
            return []


class FetchOverMentorPapersViewSet(ListAPIView):
    queryset = models.MentorPapers.objects.all()
    serializer_class = serializers.CardViewMentorPaperSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = core_paginations.CustomPagination5

    def get_queryset(self):
        user = self.request.user
        try:
            if self.request.query_params.get('user'):
                studentuser= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                studentuser = self.request.user
        except:
            studentuser = self.request.user
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            batch_obj = models.Batch.objects.get(id=int(batch_id))
            if not batch_obj:
                raise ParseError("Batch with this id DoesNotExist")
            if batch_obj:

                currenttime = timezone.now()
                assessment_test_obj = models.MentorPapers.objects.filter(
                    batch=batch_obj)
                paperIds = []
                paperIds = [paper.id for paper in assessment_test_obj]
                answer_paper = models.MentorPaperAnswerPaper.objects.filter(user=studentuser,
                    mentor_paper__in=paperIds)
                attempted_mentor_papers_ids = [paper.mentor_paper.id for paper in answer_paper]
                learner_paper_obj = models.MentorPapers.objects.filter(
                    Q(batch=batch_obj, exam_end_date_time__lte=currenttime)).exclude(id__in=attempted_mentor_papers_ids)

        if not batch_id:
            learner_paper_obj = models.MentorPapers.objects.filter(mentor=user)
        if learner_paper_obj:
            return learner_paper_obj
        else:
            return []

class FetchOverMentorPapersFourInAPageViewSet(ListAPIView):
    queryset = models.MentorPapers.objects.all()
    serializer_class = serializers.CardViewMentorPaperSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = core_paginations.CustomPagination4

    def get_queryset(self):
        user = self.request.user
        try:
            if self.request.query_params.get('user'):
                studentuser= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                studentuser = self.request.user
        except:
            studentuser = self.request.user
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            batch_obj = models.Batch.objects.get(id=int(batch_id))
            if not batch_obj:
                raise ParseError("Batch with this id DoesNotExist")
            if batch_obj:

                currenttime = timezone.now()
                assessment_test_obj = models.MentorPapers.objects.filter(
                    batch=batch_obj)
                paperIds = []
                paperIds = [paper.id for paper in assessment_test_obj]
                answer_paper = models.MentorPaperAnswerPaper.objects.filter(user=studentuser,
                    mentor_paper__in=paperIds)
                attempted_mentor_papers_ids = [paper.mentor_paper.id for paper in answer_paper]
                learner_paper_obj = models.MentorPapers.objects.filter(
                    Q(batch=batch_obj, exam_end_date_time__lte=currenttime)).exclude(id__in=attempted_mentor_papers_ids)

        if not batch_id:
            learner_paper_obj = models.MentorPapers.objects.filter(mentor=user)
        if learner_paper_obj:
            return learner_paper_obj
        else:
            return []

class FetchMentorPaperByIdViewSet(RetrieveUpdateAPIView):
    queryset = models.MentorPapers.objects.all()
    serializer_class = serializers.MentorPaperSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        mentor_paper_obj = models.MentorPapers.objects.filter(pk=self.kwargs.get('pk'))
        if not mentor_paper_obj:
            raise ParseError("Mentor paper with this id DoesNotExist")
        return mentor_paper_obj

    def list(self, request, *args, **kwargs):
        paper_obj = models.MentorPapers.objects.get(id=self.kwargs.get('pk'))
        assessmentpaperdetails = serializers.MentorPaperSerializer(paper_obj, context={'request': request})
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            serializer = self.get_serializer(queryset[0], many=True)
            return Response({
                'paperdetails':assessmentpaperdetails.data,
                'question_data':queryset[1],
            })
        return Response({'error': 'Error in Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)



class FetchLearnerBatchHistoryViewSet(ListAPIView):
    queryset = models.LearnerBatchHistory.objects.all()
    serializer_class = serializers.LearnerBatchHistorySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            batch_obj = models.Batch.objects.get(id=int(batch_id))
            if batch_obj:
                learner_batch_history_obj = models.LearnerBatchHistory.objects.filter(batch=batch_obj, is_blocked=False)
            if not batch_obj:
                raise ParseError("Batch with this id DoesNotExist")
        if not batch_id:
            raise ParseError("Please select at least one batch")
        if learner_batch_history_obj:
            return learner_batch_history_obj
        else:
            return []

class ReportQuestionViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    serializer_class = serializers.ReportedQuestionSerializer
    create_class = serializers.ReportedQuestionSerializer

    def get_queryset(self):
        user=self.request.user
        queries = models.ReportedErrorneousQuestion.objects.filter(user=user)
        if queries:
            return queries
        else:
            return []

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class FetchReportedQuestionsViewSet(ListAPIView,):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.ReportedQuestionSerializer
    pagination_class = core_paginations.CustomPagination

    def get_queryset(self):
        queries = models.ReportedErrorneousQuestion.objects.all()
        if queries:
            return queries
        else:
            return []

class ContactUsViewSet(ListAPIView, CreateAPIView):
    # permission_classes = [IsAuthenticated, ]
    serializer_class = serializers.ContactUsSerializer
    create_class = serializers.ContactUsSerializer

    def get_queryset(self):
        user=self.request.user
        queries = models.ContactUs.objects.filter(user=user)
        if queries:
            return queries
        else:
            return []

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class FetchContactUsViewSet(ListAPIView,):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.ContactUsSerializer
    pagination_class = core_paginations.CustomPagination

    def get_queryset(self):
        queries = models.ContactUs.objects.all()
        if queries:
            return queries
        else:
            return []

class FAQViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    serializer_class = serializers.FAQSerializer
    create_class = serializers.FAQSerializer

    def get_queryset(self):
        user=self.request.user
        queries = models.FAQ.objects.filter(user=user)
        if queries:
            return queries
        else:
            return []

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class FetchFAQViewSet(ListAPIView,):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.FAQSerializer

    def get_queryset(self):
        queries = models.FAQ.objects.all().order_by('id')
        if queries:
            return queries
        else:
            return []

class EditFAQViewSetViewSet(RetrieveUpdateAPIView):
    queryset = models.FAQ.objects.all()
    serializer_class = serializers.FAQSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        level_obj = models.FAQ.objects.filter(pk=self.kwargs.get('pk'))
        if not level_obj:
            raise ParseError("FAQ with this id DoesNotExist")
        return level_obj
    
    def delete(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            hint_obj = models.FAQ.objects.get(pk=int(id))
            hint_obj.delete()
        except:
            return Response({"message": "Please enter valid FAQ id"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "FAQ deleted successfully"}, status=201)

class DeleteBookmarkViewSet(RetrieveUpdateAPIView):
    queryset = models.LearnerBookmarks.objects.all()
    serializer_class = serializers.BookmarksSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        bookmark_obj = models.LearnerBookmarks.objects.filter(pk=self.kwargs.get('pk'))
        if not bookmark_obj:
            raise ParseError("Bookmark with this id DoesNotExist")
        return bookmark_obj
    
    def delete(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            bookmark_obj = models.LearnerBookmarks.objects.get(pk=int(id))
            learner_exam_obj = course_models.LearnerExams.objects.get(id=int(bookmark_obj.learner_exam.id))
            chapter_obj = course_models.Chapter.objects.get(id=int(bookmark_obj.chapter.id))
            subject_obj = course_models.Subject.objects.get(id=int(bookmark_obj.subject.id))
            try:
                lec_obj = models.LearnerExamChapters.objects.get(learner_exam=learner_exam_obj, chapter=chapter_obj, subject=subject_obj)
            except:
                lec_obj = None
            if lec_obj:
                lec_obj.total_bookmarks -= 1
                lec_obj.save()
            try:
                les_obj = models.LearnerExamSubjects.objects.get(learner_exam=learner_exam_obj, subject=subject_obj)
            except:
                les_obj = None
            if les_obj:
                les_obj.total_bookmarks -= 1
                les_obj.save()
            bookmark_obj.delete()
        except:
            return Response({"message": "Please enter valid Bookmark id"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Bookmark deleted successfully"}, status=201)

class DeleteTemporaryBookmarkViewSet(RetrieveUpdateAPIView):
    queryset = models.TemporaryLearnerBookmarks.objects.all()
    serializer_class = serializers.TemporaryBookmarksSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        bookmark_obj = models.TemporaryLearnerBookmarks.objects.filter(pk=self.kwargs.get('pk'))
        if not bookmark_obj:
            raise ParseError("Bookmark with this id DoesNotExist")
        return bookmark_obj
    
    def delete(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            bookmark_obj = models.TemporaryLearnerBookmarks.objects.get(pk=int(id))
            bookmark_obj.delete()
        except:
            return Response({"message": "Please enter valid Bookmark id"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Bookmark deleted successfully"}, status=201)


class FindReplacementQuestionViewSet(ListAPIView):
    queryset = models.Question.objects.all()
    serializer_class = serializers.QuestionSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        question_id = self.request.query_params.get('question')
        paper_id = self.request.query_params.get('paper')
        paper_obj = models.MentorPapers.objects.get(id=int(paper_id))
        if not paper_obj:
            raise ParseError("Paper with this id DoesNotExist")
        currenttime = timezone.now()
        if currenttime >= paper_obj.exam_start_date_time:
            raise ParseError("You cannot replace the question once the test has started")
        quesIds = []
        questions = paper_obj.questions.all()
        quesIds = [question.id for question in questions]
        tempques = None
        
        tempques, _ = models.TemporaryMentorPaperReplaceQuestions.objects.get_or_create(paper=paper_obj)
        tmpqueslist = tempques.questions.all()
        if len(tmpqueslist) > 0:
            for ques in tmpqueslist:
                quesIds.append(ques.id)
        if question_id:
            question_obj = models.Question.objects.get(id=int(question_id))
            if question_obj:
                tagIds = []
                ftags = question_obj.linked_topics.all()
                tagIds = [tag.id for tag in ftags]
                eng_obj = models.QuestionLanguage.objects.get(text='English')
                try:
                    new_ques_obj = models.Question.objects.filter(is_active=True, linked_topics__in=tagIds, languages=eng_obj, difficulty=question_obj.difficulty, type_of_question=question_obj.type_of_question).order_by('?').distinct().exclude(id__in=quesIds)[:1]
                    
                except:
                    return Response({"message": "no replacement question found"}, status=status.HTTP_400_BAD_REQUEST)
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

class ReplaceQuestionInMentorPaperView(UpdateAPIView):
    serializer_class = serializers.MentorPaperSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        try:
            questionid = request.data.get('question')
            ques_obj = models.Question.objects.get(id=int(questionid))
        except:
            ques_obj = None
        if not ques_obj:
            return Response({"message": "question with this id does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            newquestionid = request.data.get('newquestion')
            newquestion_obj = models.Question.objects.get(id=int(newquestionid))
        except:
            newquestion_obj = None
        if not newquestion_obj:
            return Response({"message": "replacement question with this id does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            paperid = request.data.get('paper')
            assessmentpaper_obj = models.MentorPapers.objects.get(id=int(paperid))
            currenttime = timezone.now()
            exam_end_date_time = assessmentpaper_obj.exam_end_date_time
            if currenttime >= exam_end_date_time:
                return Response({'message': 'you cannot change the questions now, you are ahead of exam start time..' }, status=status.HTTP_400_BAD_REQUEST)
        except:
            assessmentpaper_obj = None
        if not assessmentpaper_obj:
            return Response({"message": "error in fetching paper details"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            assessmentpaper_obj.questions.remove(ques_obj)
            assessmentpaper_obj.save()
            assessmentpaper_obj.questions.add(newquestion_obj)
            assessmentpaper_obj.save()
            models.TemporaryMentorPaperReplaceQuestions.objects.filter(paper=assessmentpaper_obj).delete()
           
        return Response(self.serializer_class(assessmentpaper_obj).data, status=201)

class FetchMentorlearnerAnswerPaperByIdViewSet(ListAPIView):
    queryset = models.MentorPaperAnswerPaper.objects.all()
    serializer_class = serializers.MentorLearnerAnswerPaperSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        user=self.request.user
        paperid = self.request.query_params.get('paper')
        if paperid:
            mentor_paper_obj = models.MentorPapers.objects.get(id=int(paperid))
            answer_paper_obj = models.MentorPaperAnswerPaper.objects.filter(mentor_paper=mentor_paper_obj, user=user)
            if answer_paper_obj:
                return answer_paper_obj
            else:
                return []
       
class RemoveAndBlockUserFromBatchView(UpdateAPIView):
    serializer_class = serializers.ViewBatchSerializer

    def put(self, request, *args, **kwargs):
        try:
            username = request.data.get('user')
            user_obj = auth_models.User.objects.get(username=username)
        except:
            user_obj = None
        if not user_obj:
            return Response({"message": "user with this username does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            batchid = request.data.get('batch')
            batch_obj = models.Batch.objects.get(id=int(batchid))
        except:
            batch_obj = None
        if not batch_obj:
            return Response({"message": "batch with this id does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                history_obj = models.LearnerBatchHistory.objects.get(batch=batch_obj, user=user_obj)
            except:
                history_obj = None
            if history_obj:
                history_obj.is_blocked = True
                history_obj.save()
            if batch_obj.institute_room:
                userroomobj = models.UserClassRoom.objects.filter(user=user_obj).last()
                userroomobj.institute_rooms.remove(batch_obj.institute_room)
                userroomobj.save()
                room_obj = models.InstituteClassRoom.objects.get(id=batch_obj.institute_room.id)
                room_obj.blocked_students.add(user_obj)
                room_obj.save()
            models.LearnerBlockedBatches.objects.create(user=user_obj, batch=batch_obj)
            models.LearnerBatches.objects.filter(user=user_obj, batch=batch_obj).delete()
            teacher_profile = profiles_models.Profile.objects.get(user=batch_obj.teacher)
            notification_type = NotificationType.objects.get(name="admin")
            if batch_obj.institute_room:
                notification_text  = "Blocked from batch: " + batch_obj.institute_room.grade.name + " - " + batch_obj.institute_room.name
                message = "Mentor " + teacher_profile.first_name + " has blocked you from batch " + batch_obj.institute_room.grade.name + " - " + batch_obj.institute_room.name
            else:
                notification_text  = "Blocked from batch: " + batch_obj.name
                message = "Mentor " + teacher_profile.first_name + " has blocked you from batch " + batch_obj.name
            Notifications.objects.create(user=user_obj, batch=batch_obj, notification=message, subject=notification_text, type=notification_type)

        return Response(self.serializer_class(batch_obj).data, status=201)

class CheckIfBlockedViewSet(ListAPIView):
    queryset = models.LearnerBatches.objects.all()
    serializer_class = serializers.LearnerBatchSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user=self.request.user
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            batch_obj = models.Batch.objects.get(id=int(batch_id))
            if batch_obj:
                try:
                    blocked_obj = models.LearnerBlockedBatches.objects.filter(user=user, batch=batch_obj)
                except:
                    blocked_obj = None
                if blocked_obj:
                    raise ParseError("You are blocked from this batch")
                try:
                    learner_batch_obj = models.LearnerBatches.objects.filter(user=user, batch=batch_obj)
                except:
                    return Response({"message": "not in this batch"}, status=status.HTTP_400_BAD_REQUEST)
            if not batch_obj:
                raise ParseError("Batch with this id DoesNotExist")
        if not batch_id:
            raise ParseError("Please enter batch id")
        if learner_batch_obj:
            return learner_batch_obj
        else:
            return []

class FetchAllAnswerPapersInTheMentorPaperViewSet(ListAPIView):
    queryset = models.MentorPaperAnswerPaper.objects.all()
    serializer_class = serializers.MentorLearnerAnswerPaperSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        paper_id = self.request.query_params.get('paper')
        if paper_id:
            paper_obj = models.MentorPapers.objects.get(id=int(paper_id))
            if paper_obj:
                learner_paper_obj = models.MentorPaperAnswerPaper.objects.filter(mentor_paper=paper_obj).order_by('score')
            if not paper_obj:
                raise ParseError("Paper with this id DoesNotExist")
        if not paper_id:
            raise ParseError("Please enter paper id")
        if learner_paper_obj:
            return learner_paper_obj
        else:
            return []

class FetchBlockedUserInBatchViewSet(ListAPIView):
    queryset = models.LearnerBlockedBatches.objects.all()
    serializer_class = serializers.LearnerBlockedBatchSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        user=self.request.user
        batchid = self.request.query_params.get('batch')
        if batchid:
            batch_obj = models.Batch.objects.get(id=int(batchid))
            blocked_obj = models.LearnerBlockedBatches.objects.filter(batch=batch_obj)
            if blocked_obj:
                return blocked_obj
            else:
                return []

class UnblockUserFromBatchViewSet(ListAPIView):
    queryset = models.LearnerBlockedBatches.objects.all()
    serializer_class = serializers.LearnerBlockedBatchSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        batchid = self.request.query_params.get('batch')
        username = self.request.query_params.get('user')
        if batchid:
            batch_obj = models.Batch.objects.get(id=int(batchid))
            user= auth_models.User.objects.get(username=username)
            models.LearnerBlockedBatches.objects.filter(batch=batch_obj, user=user).delete()
            try:
                history_obj = models.LearnerBatchHistory.objects.get(batch=batch_obj, user=user)
            except:
                history_obj = None
            if history_obj:
                history_obj.is_blocked = False
                history_obj.save()
            if batch_obj.institute_room:
                userroomobj = models.UserClassRoom.objects.filter(user=user).last()
                userroomobj.institute_rooms.add(batch_obj.institute_room)
                userroomobj.save()
                room_obj = models.InstituteClassRoom.objects.get(id=batch_obj.institute_room.id)
                room_obj.blocked_students.remove(user)
                room_obj.save()
            teacher_profile = profiles_models.Profile.objects.get(user=batch_obj.teacher)
            notification_type = NotificationType.objects.get(name="admin")
            if batch_obj.institute_room:
                notification_text  = "Unblocked from batch: " + batch_obj.institute_room.grade.name + " - " + batch_obj.institute_room.name
                message = "Mentor " + teacher_profile.first_name + " has unblocked you from batch " + batch_obj.institute_room.grade.name + " - " + batch_obj.institute_room.name
            else:
                notification_text  = "Unblocked from batch: " + batch_obj.name
                message = "Mentor " + teacher_profile.first_name + " has unblocked you from batch " + batch_obj.name
            Notifications.objects.create(user=user, batch=batch_obj, notification=message, subject=notification_text, type=notification_type)

            blocked_obj = models.LearnerBlockedBatches.objects.filter(batch=batch_obj)
            if blocked_obj:
                return blocked_obj
            else:
                return []

class MentorAssessmentPaperAllUserReportView(ListAPIView):
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
        return Response({'error': 'Error in Assessment Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class MentorAssessmentQuestionWiseAnalysisReportView(ListAPIView):
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
        return Response({'error': 'Error in Assessment Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class MentorAssessmentSingleQuestionAnalysisReportView(ListAPIView):
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
        return Response({'error': 'Error in Assessment Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class BatchAccuracyReportView(ListAPIView):
    permission_classes = [IsAuthenticated,]

    def get_queryset(self):
        reports = content_utils.MentorBatchWiseAccuracyAnalysisReport(self.request.user)

        if not reports:
            # return blank queryset if reports not received
            return None
        return reports
        

    def list(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            return Response(queryset)
        return Response({'error': 'Error in Report.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class BatchWiseLeaderboard(ListAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        batch_id = self.request.query_params.get('batch')
        if not batch_id:
            raise ParseError("Please select any batch")
        try:    
            batch_obj = models.Batch.objects.get(id=int(batch_id))
        except:   
            batch_obj = None
        if not batch_obj:
            raise ParseError("Batch with this id DoesNotExist")
        leaderboard_data = content_utils.get_batchwise_leaderboard(batch_id)
        if not leaderboard_data:
            return None
        else:
            return leaderboard_data

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            return Response({
                'leaderboard_data':queryset
            })
        return Response({'error': 'Error in Fetching Leaderboard.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class CumulativeBatchWiseLeaderboard(ListAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        leaderboard_data = content_utils.get_mentorallbatch_leaderboard(self.request.user)
        if not leaderboard_data:
            return None
        else:
            return leaderboard_data

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            return Response({
                'leaderboard_data':queryset
            })
        return Response({'error': 'Error in Fetching Leaderboard.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class MentorPaperAnswersHistoryView(ListAPIView):
    serializer_class = serializers.QuestionSerializer
    permission_classes = [IsAuthenticated,]

    def get_queryset(self):
        try:
            user=None
            if self.request.query_params.get('user'):
                user= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                user = self.request.user
        except:
            user = self.request.user
        questions , question_data = content_utils.get_mentorpaper_answers_history(user, self.kwargs.get('assessmentpaper_id'))
        if not questions:
            # return blank queryset if questions not received
            return models.Question.objects.filter(id=None)
        return questions, question_data

    def list(self, request, *args, **kwargs):
        user = self.request.user
        try:
            user=None
            if self.request.query_params.get('user'):
                user= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                user = self.request.user
        except:
            user = self.request.user
        assessmentpaper_obj = models.MentorPapers.objects.get(id=self.kwargs.get('assessmentpaper_id'))
        currenttime = timezone.now()
        # if assessmentpaper_obj.exam_end_date_time and assessmentpaper_obj.exam_end_date_time < currenttime:
        #     models.TemporaryPaperSubjectQuestionDistribution.objects.filter(mentor_paper=assessmentpaper_obj).delete()
        answer_paper_obj = models.MentorPaperAnswerPaper.objects.filter(user=user, mentor_paper=assessmentpaper_obj)
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            serializer = self.get_serializer(queryset[0], many=True)
            answer_paper_obj = models.MentorPaperAnswerPaper.objects.filter(user=user, mentor_paper=assessmentpaper_obj)
            if answer_paper_obj:
                answer_paper = answer_paper_obj.last().id
                return Response({
                    'answer_paper':answer_paper,
                    'attemp_date': answer_paper_obj.last().attempted_date,
                    'question_data':queryset[1],
                    'questions': queryset[0],
                    'remarks': answer_paper_obj.last().remarks
                })
        return Response({'error': 'Error in Mentor Test Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class MentorPaperStudentStatsView(ListAPIView):
    serializer_class = serializers.QuestionSerializer
    permission_classes = [IsAuthenticated,]

    def get_queryset(self):
        try:
            user=None
            if self.request.query_params.get('user'):
                user= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                user = self.request.user
        except:
            user = self.request.user
        leaderboard_data, my_data = content_utils.get_topper_data_in_mentorpaper(user, self.kwargs.get('assessmentpaper_id'))
        if not leaderboard_data:
            return None
        else:
            return leaderboard_data, my_data

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            return Response({
                'topper_data':queryset[0],
                'my_data': queryset[1]
            })
        return Response({'error': 'Error in Fetching Topper Data.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class UpdatePaperRemarkForUserView(UpdateAPIView):
    serializer_class = serializers.MentorLearnerAnswerPaperSerializer

    def put(self, request, *args, **kwargs):
        try:
            remarks = request.data.get('remarks')
            paper_id = request.data.get('paper')
            if not paper_id:
                raise ParseError("Please enter paper id")
            else:   
                learner_paper_obj = models.MentorPaperAnswerPaper.objects.get(id=int(paper_id))
            if not learner_paper_obj:
                raise ParseError("Answer Paper with this id DoesNotExist")
            learner_paper_obj.remarks = remarks
            learner_paper_obj.save()
            mentor_paper_obj = models.MentorPapers.objects.get(id=int(learner_paper_obj.mentor_paper.id))
            teacher_profile = profiles_models.Profile.objects.get(user=learner_paper_obj.mentor_paper.mentor)
            notification_type = NotificationType.objects.get(name="admin")
            if learner_paper_obj.mentor_paper.paper_type == 'paper':
                notification_text  = "Remark given for paper: Paper " + str(learner_paper_obj.mentor_paper.paper_count)
            else:
                notification_text  = "Remark given for practice paper: Practice " + str(learner_paper_obj.mentor_paper.paper_count)
            message = "Mentor " + teacher_profile.first_name + " has given the remark: " + remarks
            Notifications.objects.create(user=learner_paper_obj.user, mentor_paper=mentor_paper_obj, notification=message, subject=notification_text, type=notification_type)
        except:
            return Response({"message": "error in updating remarks"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(learner_paper_obj).data, status=201)

class FetchQuestionWiseUserAnswerInLearnerpaperAnswerViewSet(ListAPIView):
    queryset = models.UserAnswer.objects.all()
    serializer_class = serializers.UserAnswerSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        user=self.request.user
        paperid = self.request.query_params.get('paper')
        questionid = self.request.query_params.get('question')
        ques_obj = models.Question.objects.get(id=int(questionid))
        if paperid:
            paper_obj = models.LearnerPapers.objects.get(id=int(paperid))
            if not paper_obj:
                raise ParseError("Paper with this id DoesNotExist")
            answer_paper_obj = models.AnswerPaper.objects.filter(assessment_paper=paper_obj).last()
            if not answer_paper_obj:
                raise ParseError("Answer not found")
            user_answer_obj = models.UserAnswer.objects.filter(answer_paper=answer_paper_obj, question=ques_obj)
        if not paperid:
            raise ParseError("Please enter paper id")
        if user_answer_obj:
            return user_answer_obj
        else:
            return []
        
class FetchQuestionWiseUserAnswerInMentorpaperAnswerViewSet(ListAPIView):
    queryset = models.UserAnswerMentorPaper.objects.all()
    serializer_class = serializers.UserAnswerMentorPaperSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        user=self.request.user
        paperid = self.request.query_params.get('paper')
        questionid = self.request.query_params.get('question')
        ques_obj = models.Question.objects.get(id=int(questionid))
        try:
            user=None
            if self.request.query_params.get('user'):
                user= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                user = self.request.user
        except:
            user = self.request.user
        if paperid:
            paper_obj = models.MentorPapers.objects.get(id=int(paperid))
            if not paper_obj:
                raise ParseError("Paper with this id DoesNotExist")
            answer_paper_obj = models.MentorPaperAnswerPaper.objects.filter(mentor_paper=paper_obj, user=user).last()
            if not answer_paper_obj:
                raise ParseError("Answer not found")
            user_answer_obj = models.UserAnswerMentorPaper.objects.filter(answer_paper=answer_paper_obj, question=ques_obj, user=user)
        if not paperid:
            raise ParseError("Please enter paper id")
        if user_answer_obj:
            return user_answer_obj
        else:
            return []

class SetMockPaperParametersExamWiseViewSet(ListAPIView):
    serializer_class = serializers.MockPaperExamDetailsSerializer

    def put(self, request, *args, **kwargs):
        try:
            examid = request.data.get('exam')
            subject_data = request.data.get('subject_data')
            chapters = request.data.get('chapters')
            show_time = request.data.get('show_time')
            difficulty = request.data.get('difficulty')
            if not examid:
                raise ParseError("Please enter exam id")
            if not subject_data:
                raise ParseError("Please enter subject data")
            if not chapters:
                raise ParseError("Please enter chapters")
            
            if not difficulty:
                raise ParseError("Please enter difficulty")
            try:
                exam_obj = course_models.Exam.objects.get(id=int(examid))
            except:
                exam_obj = None
            if not exam_obj:
                return Response({"message": "Exam not found"}, status=status.HTTP_400_BAD_REQUEST)
            subjectIds = []
            models.MockPaperSubjectQuestionTypeDetails.objects.filter(exam=exam_obj).delete()
            models.MockPaperSubjectDetails.objects.filter(exam=exam_obj).delete()
            for subject in subject_data:
                subject_obj = course_models.Subject.objects.get(
                    pk=int(subject['subject']))
                subjectIds.append(subject_obj.id)
                mock_subject_chapters = models.MockPaperSubjectDetails.objects.create(exam=exam_obj, subject=subject_obj)
                mock_subject_chapters.chapters.add(*subject['chapters'])
                mock_subject_chapters.save()
               
                for ques_data in subject['data']:
                    # mock_subject_ques = models.MockPaperSubjectQuestionTypeDetails.objects.get(exam=exam_obj, subject=subject_obj, type_of_question=ques_data['ques_type'])
                    # if not mock_subject_ques:
                    mock_subject_ques = models.MockPaperSubjectQuestionTypeDetails.objects.create(exam=exam_obj, subject=subject_obj, type_of_question=ques_data['ques_type'])
                    
                    mock_subject_ques.total_questions = ques_data['questions']
                    mock_subject_ques.total_time = ques_data['time']
                    mock_subject_ques.save()
            # topicIds = []
            models.MockPaperExamDetails.objects.filter(exam=exam_obj).delete()
            # if not mock_exam:
            mock_exam = models.MockPaperExamDetails.objects.create(exam=exam_obj, difficulty_level=difficulty, show_time=show_time)
            
            mock_exam.chapters.add(*chapters)
            mock_exam.save()
            
        except:
            return Response({"message": "error in updating remarks"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(mock_exam).data, status=201)

class FetchMockExamDetailsViewSet(ListAPIView):
    queryset = models.MockPaperExamDetails.objects.all()
    serializer_class = serializers.MockPaperExamDetailsSerializer
    permission_classes = (IsAuthenticated,)
    # parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if not exam_id:
            raise ParseError("Please enter exam id")
        # parameter_obj = models.MockPaperExamDetails.objects.filter(exam__id=exam_id)
        parameter_obj = models.MockPaperExamDetails.objects.select_related(
            "exam").prefetch_related("chapters").filter(exam__id=exam_id)
        # if parameter_obj:
        return parameter_obj
        # else:
        #     return []

class ViewMockExamDetailsWithoutChapterViewSet(ListAPIView):
    queryset = models.MockPaperExamDetails.objects.all()
    serializer_class = serializers.ViewMockPaperExamDetailsSerializer
    permission_classes = (IsAuthenticated,)
    # parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if not exam_id:
            raise ParseError("Please enter exam id")
        parameter_obj = models.MockPaperExamDetails.objects.select_related(
            "exam").prefetch_related("chapters").filter(exam__id=exam_id)
        return parameter_obj

class FetchMockSubjectDetailsViewSet(ListAPIView):
    queryset = models.MockPaperSubjectDetails.objects.all()
    serializer_class = serializers.MockPaperSubjectDetailsSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            exam_obj = course_models.Exam.objects.get(id=int(exam_id))
            parameter_obj = models.MockPaperSubjectDetails.objects.filter(exam=exam_obj).order_by('id')
            if parameter_obj:
                return parameter_obj
            else:
                return []

class FetchMockSubjectQuestionTypeDetailsViewSet(ListAPIView):
    queryset = models.MockPaperSubjectQuestionTypeDetails.objects.all()
    serializer_class = serializers.MockPaperSubjectQuestionTypeDetailsSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            exam_obj = course_models.Exam.objects.get(id=int(exam_id))
            parameter_obj = models.MockPaperSubjectQuestionTypeDetails.objects.filter(exam=exam_obj).order_by('id')
            if parameter_obj:
                return parameter_obj
            else:
                return []

class GenerateMockPaperForExamView(UpdateAPIView):
    serializer_class = serializers.CardViewLearnerPaperSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        
        examid = request.data.get('exam')
        if not examid:
            raise ParseError("Please enter exam id")
        exam_obj = course_models.Exam.objects.get(pk=int(examid))
        if not exam_obj:
            raise ParseError("Exam with this id DoesNotExist")
        if not exam_obj.is_active:
            learnerexamtmpobj = course_models.LearnerExams.objects.get(user=user, exam=exam_obj)
            if learnerexamtmpobj:
                learnerexamtmpobj.is_active=False
                learnerexamtmpobj.save()
            return Response({"message": "Oops! Exam has been deactivated by admin"}, status=status.HTTP_400_BAD_REQUEST)
        
        mock_exam_obj = models.MockPaperExamDetails.objects.get(exam=exam_obj)
        if not mock_exam_obj:
            raise ParseError("No Mock paper available")
        
        totalTime = 0
        range1 = [1,2,3]
        range2 = [4,5,6,7]
        range3 = [8,9,10]
        allRange = [1,2,3,4,5,6,7,8,9,10]
        selectedRange = []
        if mock_exam_obj.difficulty_level in range1:
            selectedRange = range1
        elif mock_exam_obj.difficulty_level in range2:
            selectedRange = range2
        else:
            selectedRange = range3
        eng_obj = models.QuestionLanguage.objects.get(text='English')
        learner_papercount_obj, _ = models.LearnerTotalActualPapers.objects.get_or_create(user=user, defaults={"count": 0})
        learner_papercount_obj.count += 1
        learner_papercount_obj.save()
        learner_exam_obj, _ = course_models.LearnerExams.objects.get_or_create(
            exam=exam_obj, user=user, defaults={"is_active": True})

        learner_paper_obj = models.LearnerPapers.objects.create(
            user=user, paper_type='paper', paper_count=learner_papercount_obj.count,
            learner_exam=learner_exam_obj, show_time=mock_exam_obj.show_time)

        learner_history_obj, _ = models.LearnerHistory.objects.get_or_create(user=user)
        learnerexam_history_obj, _ = models.LearnerExamHistory.objects.get_or_create(user=user, exam=exam_obj)
        learnerexam_paper_history_obj, _ = models.LearnerExamPaperHistory.objects.get_or_create(user=user, exam=exam_obj)
        quesIds = []
        
        mock_subject_obj = models.MockPaperSubjectDetails.objects.select_related(
            "exam", "subject").prefetch_related("chapters").filter(exam=exam_obj)
        
        for mock_data in mock_subject_obj: 
            chapterids = []   
            chapters = mock_data.chapters.all()
            chapterids.extend(chapters.values_list("id", flat=True))
            mastertag_objs = models.ChapterMasterFTag.objects.filter(chapter__in=chapterids)
            tempquesIds = mastertag_objs.values_list("questions", flat=True)
          
            mock_ques_type_obj = models.MockPaperSubjectQuestionTypeDetails.objects.filter(exam=exam_obj, subject=mock_data.subject)
            question_types = mock_ques_type_obj.values_list("type_of_question", flat=True)
            # Applying filters on the top level with tupe_of_question and difficulty
            # will enforce the indexing and scan lesser records from dataset
            question_set = models.Question.objects.filter(id__in=tempquesIds,
                is_active=True,  languages=eng_obj, 
                type_of_question__in=question_types, difficulty__in=selectedRange,
            ).values_list("id", flat=True).exclude(id__in=quesIds)

            for mock_ques in mock_ques_type_obj:
                totalTime += mock_ques.total_time
                _questions = question_set.filter(
                    type_of_question=mock_ques.type_of_question).values_list("id", flat=True
                    ).exclude(id__in=quesIds).order_by("?").distinct()[:mock_ques.total_questions]
            
                # _questions = models.Question.objects.prefetch_related("linked_topics").filter(id__in=tempquesIds,
                #     type_of_question=mock_ques.type_of_question, difficulty__in=selectedRange,).values_list("id", flat=True
                #     ).exclude(id__in=quesIds).distinct()[:mock_ques.total_questions]

                for ques in _questions:
                    models.TemporaryPaperSubjectQuestionDistribution.objects.create(learner_paper_id=learner_paper_obj.id, subject=mock_data.subject, question_id=ques)
                quesIds.extend(_questions)
                required_more_questions = mock_ques.total_questions - len(_questions)
                count = 0
                while required_more_questions > 0:
                    count += 1
                    new_difficulty_range = [item for item in DifficultyRange.allRange if item not in selectedRange]
                    
                    extra_ques = question_set.filter(difficulty__in=new_difficulty_range, 
                    type_of_question=mock_ques.type_of_question).values_list("id", flat=True
                    ).exclude(id__in=quesIds).order_by("?").distinct()[:required_more_questions]
                
                    # extra_ques = models.Question.objects.prefetch_related("linked_topics").filter(id__in=tempquesIds, difficulty__in=new_difficulty_range, 
                    # type_of_question=mock_ques.type_of_question).values_list("id", flat=True
                    # ).exclude(id__in=quesIds).order_by("?").distinct()[:required_more_questions]
                    for ques in extra_ques:
                        models.TemporaryPaperSubjectQuestionDistribution.objects.create(learner_paper_id=learner_paper_obj.id, subject=mock_data.subject, question_id=ques)
                    quesIds.extend(extra_ques)
                    required_more_questions -= len(set(extra_ques))
                    _questions.union(extra_ques)
                    if count == 10:
                        break
                    
        random.shuffle(quesIds)
        total_ques = len(quesIds)
        if (not quesIds) or total_ques <= 0:
            learner_papercount_obj.count -= 1
            learner_papercount_obj.save()
            learner_paper_obj.delete()
            return Response({"message": "No questions found"}, status=status.HTTP_400_BAD_REQUEST)
        
        subjectIds = []
        subjectIds.extend(mock_subject_obj.values_list("subject", flat=True))
        learner_paper_obj.subjects.add(*subjectIds)
        learner_paper_obj.save()

        learner_history_obj.papers.add(learner_paper_obj)
        learner_history_obj.total_questions += total_ques
        learner_history_obj.save()
        learner_paper_obj.total_time = totalTime
        learner_paper_obj.save()
        learnerexam_history_obj.papers.add(learner_paper_obj)
        learnerexam_history_obj.save()
        learnerexam_paper_history_obj.papers.add(learner_paper_obj)
        learnerexam_paper_history_obj.save()
        try:
            total_marks = 0
            learnerexam_history_obj.total_questions += total_ques
            learnerexam_history_obj.save()
            learner_history_obj.questions.add(*quesIds)
            learner_paper_obj.questions.add(*quesIds)
            learner_history_obj.save()
            learner_paper_obj.save()
            learnerexam_history_obj.questions.add(*quesIds)
            learnerexam_history_obj.save()
            learnerexam_paper_history_obj.questions.add(*quesIds)
            learnerexam_paper_history_obj.save()
            # for ques_obj in final_questions:
            #     avg_marks_obj = course_models.QuestionType.objects.get(exam=exam_obj, type_of_question=ques_obj.type_of_question)
            #     if ques_obj.type_of_question != 'subjective':
            #         total_marks = total_marks + avg_marks_obj.marks
            instruction_ques = "Total Questions: " + str(total_ques)
            models.PaperInstructions.objects.create(paper=learner_paper_obj,instruction=instruction_ques)
            if learner_paper_obj.paper_type == 'paper':
                instruction_time = "Total Time (in Min): " + str(totalTime)
                models.PaperInstructions.objects.create(paper=learner_paper_obj,instruction=instruction_time)
            distribution_based_on_type = QuestionDistribution.distribute_based_on_type_of_questions(
                    learner_paper_obj.questions.all()
                )
            total_marks_grouped_by_exam_type_of_question = course_models.QuestionType.objects.filter(
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
            models.PaperInstructions.objects.create(paper=learner_paper_obj, instruction=instruction_marks)
            
        except:
            learner_papercount_obj.count -= 1
            learner_papercount_obj.save()
            learner_paper_obj.delete()
            return Response({"message": "error in fetching questions"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(learner_paper_obj).data, status=201)

class DeleteMentorPaperTempQuesReplaceViewSet(UpdateAPIView):
    queryset = models.TemporaryMentorPaperReplaceQuestions.objects.all()

    def put(self, request, *args, **kwargs):
        paperid = request.data.get('paper')
        if not paperid:
            raise ParseError("Please enter exam id")
        paperobj = models.MentorPapers.objects.get(id=int(paperid))
        if not paperobj:
            raise ParseError("Paper with this id DoesNotExist")
        try:
            hint_obj = models.TemporaryMentorPaperReplaceQuestions.objects.filter(paper=paperobj)
            hint_obj.delete()
        except:
            return Response({"message": "Some error while deletion"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Temporary replacement questions deleted successfully"}, status=201)

class BatchStudentPaperCountView(ListAPIView):
    serializer_class = serializers.MentorPaperSerializer
    permission_classes = [IsAuthenticated,]

    def get_queryset(self):
        try:
            user=None
            if self.request.query_params.get('user'):
                user= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                user = self.request.user
        except:
            user = self.request.user
        my_data = content_utils.get_user_papercount_in_batch(user, self.kwargs.get('batch_id'))
        if not my_data:
            return None
        else:
            return my_data

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            return Response({
                'paper_count_data': queryset[0]
            })
        return Response({'error': 'Error in Fetching Paper count Data.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class DeleteSubjectiveImageViewSet(RetrieveUpdateAPIView):
    queryset = models.UserSubjectiveAnswerImage.objects.all()
    serializer_class = serializers.UserSubjectiveAnswerImageSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        level_obj = models.UserSubjectiveAnswerImage.objects.filter(pk=self.kwargs.get('pk'))
        if not level_obj:
            raise ParseError("FAQ with this id DoesNotExist")
        return level_obj
    
    def delete(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            hint_obj = models.UserSubjectiveAnswerImage.objects.get(pk=int(id))
            hint_obj.delete()
        except:
            return Response({"message": "Please enter valid Image id"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Image deleted successfully"}, status=201)

class SearchQuestionByIdentifierSetViewSet(ListAPIView):
    queryset = models.Question.objects.all()
    serializer_class = serializers.QuestionSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        searchtext = self.request.query_params.get('text')
        if searchtext:
            ques_obj = models.Question.objects.filter(
                question_identifier__contains=searchtext).order_by('question_identifier')
            if ques_obj:
                return ques_obj
            else:
                return []

class FetchLastestQuestionViewSet(ListAPIView):
    queryset = models.Question.objects.all()
    serializer_class = serializers.QuestionSerializer

    def get_queryset(self):
        ques_obj = serializers.QuestionSerializer(models.Question.objects.all().order_by('-id')[0])
        if not ques_obj:
            return None
        else:
            return ques_obj.data

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            return Response({
                'latest_question_id':queryset['id'],
                'latest_question_identifier':queryset['question_identifier'],
            })
        return Response({'error': 'Error in Fetching Latest Question.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class BannerImagesViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    serializer_class = serializers.BannerImagesSerializer
    create_class = serializers.BannerImagesSerializer
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        banners = models.BannerSliderImages.objects.filter(is_active=True)
        if banners:
            return banners
        else:
            return []

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class FetchBannerImagesViewSet(ListAPIView,):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.BannerImagesSerializer

    def get_queryset(self):
        banners = models.BannerSliderImages.objects.filter(is_active=True).order_by('id')
        if banners:
            return banners
        else:
            return []

class EditBannerViewSetViewSet(RetrieveUpdateAPIView):
    queryset = models.BannerSliderImages.objects.all()
    serializer_class = serializers.BannerImagesSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        banner_obj = models.BannerSliderImages.objects.filter(pk=self.kwargs.get('pk'))
        if not banner_obj:
            raise ParseError("Banner with this id DoesNotExist")
        return banner_obj
    
    def delete(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            banner_obj = models.BannerSliderImages.objects.get(pk=int(id))
            banner_obj.delete()
        except:
            return Response({"message": "Please enter valid Banner id"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Banner deleted successfully"}, status=201)

class DeactivateBatchView(RetrieveUpdateAPIView):
    queryset = models.Batch.objects.all()
    serializer_class = serializers.ViewBatchSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        
        batch_obj = models.Batch.objects.select_related("teacher", "name", "teacher__profile", "batch_code", "students"
        ).filter(pk=self.kwargs.get('pk')).order_by('id')
        if not batch_obj:
            raise ParseError("Batch data with this id DoesNotExist")
        return batch_obj

    def put(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            batch_obj = models.Batch.objects.get(pk=int(id))
        except:
            return Response({"message": "Please enter valid id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            batch_obj.is_active = False
            batch_obj.save()
        except:
            return Response({"message": "error in deactivating the batch"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "batch deactivated successfully"}, status=201)

class DeleteMockPaperParametersExamWiseViewSet(ListAPIView):
    serializer_class = serializers.MockPaperExamDetailsSerializer

    def put(self, request, *args, **kwargs):
        try:
            examid = request.data.get('exam')
            if not examid:
                raise ParseError("Please enter exam id")
            
            try:
                exam_obj = course_models.Exam.objects.get(id=int(examid))
            except:
                exam_obj = None
            if not exam_obj:
                return Response({"message": "Exam not found"}, status=status.HTTP_400_BAD_REQUEST)
            models.MockPaperSubjectQuestionTypeDetails.objects.filter(exam=exam_obj).delete()
            models.MockPaperSubjectDetails.objects.filter(exam=exam_obj).delete()
            
            models.MockPaperExamDetails.objects.filter(exam=exam_obj).delete()
            
        except:
            return Response({"message": "error in updating remarks"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class('done').data, status=201)

class StudentPracticeChapterDataView(ListAPIView):
    serializer_class = serializers.LearnerExamPracticeChapterSerializer
    permission_classes = [IsAuthenticated,]

    def get_queryset(self):
        try:
            user=None
            if self.request.query_params.get('user'):
                user= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                user = self.request.user
        except:
            user = self.request.user
        my_data = content_utils.get_learner_subject_chapters(user, self.kwargs.get('exam'), self.request.query_params.get('subject'))
        if not my_data:
            return None
        else:
            return my_data

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            return Response({
                'chapters': queryset
            })
        return Response({'error': 'Error in Fetching Chapter Data.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class FindPracticeChapterQuestionsViewSet(UpdateAPIView):
    serializer_class = serializers.TemporaryMentorPracticeReplaceQuestionsSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        chapter_id = request.data.get('chapter')
        
        total_questions = request.data.get('totalQues')
        question_types = request.data.get('quesTypes')
        difficulty = request.data.get('difficulty')
        batch = request.data.get('batch')
        exam = request.data.get('exam')
        exam_obj = course_models.Exam.objects.get(id=int(exam))
        chapter_obj = course_models.Chapter.objects.get(id=int(chapter_id))
        subjectIds = []
        subjectIds.append(chapter_obj.subject.id)
        chapters = []
        chapters.append(chapter_id)
        batch_obj = models.Batch.objects.get(id=int(batch))
        if not batch_obj:
            raise ParseError("Batch with this id DoesNotExist")
        
        if difficulty in DifficultyRange.range1:
            selectedRange = DifficultyRange.range1
        elif difficulty in DifficultyRange.range2:
            selectedRange = DifficultyRange.range2
        else:
            selectedRange = DifficultyRange.range3
        tempques = None
        currenttime = timezone.now()
        end_date = request.data.get('endDate')
        end_time = request.data.get('endTime')
        if end_date == '':
            end_date = None
            end_time = None
            exam_end_date_time = None
        exam_end_date_time = content_utils.formatDateTime(end_date, end_time) if(
            end_date and end_time) else None
     
        if not end_date or not end_time:
            exam_end_date_time = None

        if exam_end_date_time and exam_end_date_time < currenttime:
            return Response({"message": "End Date can not be in past"}, status=status.HTTP_400_BAD_REQUEST)
        
        models.TemporaryMentorPracticeReplaceQuestions.objects.filter(user=user, exam=exam_obj, chapter=chapter_obj, batch=batch_obj).delete()
        tempques, _ = models.TemporaryMentorPracticeReplaceQuestions.objects.get_or_create(user=user, difficulty_level=difficulty, exam_end_date_time=exam_end_date_time, exam=exam_obj, chapter=chapter_obj, batch=batch_obj)
        
        # tagIds = []
        # ftags = tempques.chapter.topics.all()
        # tagIds = [tag.id for tag in ftags]
        eng_obj = models.QuestionLanguage.objects.get(text='English')
        try:
            questions = QuestionDistribution.get_equally_distributed_subjectwise_questions(
                0, 'tmpmentorpaper', subjectIds, selectedRange, chapters, total_questions, eng_obj, question_types
            )
        except:
            return Response({"message": "no question found"}, status=status.HTTP_400_BAD_REQUEST)
        
        if questions:
            tempques.questions.add(*(questions))
            tempques.save()
        return Response(self.serializer_class(tempques).data, status=201)

class FindPaperChapterQuestionsViewSet(UpdateAPIView):
    serializer_class = serializers.TemporaryMentorPaperReplaceQuestionsSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        chapters = request.data.get('chapters')
        
        total_questions = request.data.get('totalQues')
        question_types = request.data.get('quesTypes')
        difficulty = request.data.get('difficulty')
        batch = request.data.get('batch')
        show_time = request.data.get('show_time')
        exam = request.data.get('exam')
        exam_obj = course_models.Exam.objects.get(id=int(exam))
        # chapter_obj = course_models.Chapter.objects.get(id=int(chapter_id))
        # subjectIds.append(chapter_obj.subject.id)
        chapters_obj = course_models.Chapter.objects.filter(id__in=chapters)
        subjectIds = []
        subjectIds.extend(chapters_obj.values_list("subject", flat=True))
        # chapters = []
        # chapters.append(chapter_id)
        batch_obj = models.Batch.objects.get(id=int(batch))
        if not batch_obj:
            raise ParseError("Batch with this id DoesNotExist")
        
        if difficulty in DifficultyRange.range1:
            selectedRange = DifficultyRange.range1
        elif difficulty in DifficultyRange.range2:
            selectedRange = DifficultyRange.range2
        else:
            selectedRange = DifficultyRange.range3
        tempques = None
        currenttime = timezone.now()
        try:
            start_date = request.data.get('startDate')
            start_time = request.data.get('startTime')
            if start_date == '':
                start_date = None
                start_time = None
                exam_start_date_time = None
            if not start_date or not start_time:
                return Response({"message": "Start Date and Time is required"}, status=status.HTTP_400_BAD_REQUEST)
            exam_start_date_time = content_utils.formatDateTime(start_date, start_time) if(
            start_date and start_time) else None
        except:
            exam_start_date_time = None
        if exam_start_date_time and exam_start_date_time < currenttime:
            return Response({"message": "Start Date can not be in past"}, status=status.HTTP_400_BAD_REQUEST)
        end_date = request.data.get('endDate')
        end_time = request.data.get('endTime')
        if end_date == '':
            end_date = None
            end_time = None
            exam_end_date_time = None
        if not end_date or not end_time:
                return Response({"message": "End Date and Time is required"}, status=status.HTTP_400_BAD_REQUEST)
        exam_end_date_time = content_utils.formatDateTime(end_date, end_time) if(
            end_date and end_time) else None
     
        if not end_date or not end_time:
            exam_end_date_time = None

        if exam_end_date_time and exam_end_date_time < currenttime:
            return Response({"message": "End Date can not be in past"}, status=status.HTTP_400_BAD_REQUEST)
        
        if exam_end_date_time and exam_start_date_time > exam_end_date_time:
                return Response({"message": "Start date can not be greater than end date"}, status=status.HTTP_400_BAD_REQUEST)

        models.TemporaryMentorActualPaperReplaceQuestions.objects.filter(user=user, exam=exam_obj, batch=batch_obj).delete()
        tempques, _ = models.TemporaryMentorActualPaperReplaceQuestions.objects.get_or_create(user=user, show_time=show_time, difficulty_level=difficulty, exam_start_date_time=exam_start_date_time, exam_end_date_time=exam_end_date_time, exam=exam_obj, batch=batch_obj)
        tempques.chapters.add(*chapters)
        tempques.save()
        # tagIds = []
        # ftags = tempques.chapter.topics.all()
        # tagIds = [tag.id for tag in ftags]
        eng_obj = models.QuestionLanguage.objects.get(text='English')
        try:
            questions = QuestionDistribution.get_equally_distributed_subjectwise_questions(
                0, 'tmpmentorpaper', subjectIds, selectedRange, chapters, total_questions, eng_obj, question_types
            )
        except:
            return Response({"message": "no question found"}, status=status.HTTP_400_BAD_REQUEST)
        
        if questions:
            tempques.questions.add(*(questions))
            tempques.save()
        return Response(self.serializer_class(tempques).data, status=201)

class FetchTemporaryPracticeQuestionsViewSet(RetrieveUpdateAPIView):
    queryset = models.TemporaryMentorPracticeReplaceQuestions.objects.all()
    serializer_class = serializers.TemporaryMentorPracticeReplaceQuestionsSerializer
    update_serializer_class = serializers.TemporaryMentorPracticeReplaceQuestionsSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        tempObj = models.TemporaryMentorPracticeReplaceQuestions.objects.filter(pk=self.kwargs.get('pk'))
        if not tempObj:
            raise ParseError("Object with this id DoesNotExist")
        return tempObj

    def update(self, request, *args, **kwargs):
        question = models.TemporaryMentorPracticeReplaceQuestions.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            question, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(question).data, status=status.HTTP_200_OK)

class FetchTemporaryActualPaperQuestionsViewSet(RetrieveUpdateAPIView):
    queryset = models.TemporaryMentorActualPaperReplaceQuestions.objects.all()
    serializer_class = serializers.TemporaryMentorPaperReplaceQuestionsSerializer
    update_serializer_class = serializers.TemporaryMentorPaperReplaceQuestionsSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        tempObj = models.TemporaryMentorActualPaperReplaceQuestions.objects.filter(pk=self.kwargs.get('pk'))
        if not tempObj:
            raise ParseError("Object with this id DoesNotExist")
        return tempObj

    def update(self, request, *args, **kwargs):
        question = models.TemporaryMentorActualPaperReplaceQuestions.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            question, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(question).data, status=status.HTTP_200_OK)

class FindReplacementQuestionPracticeViewSet(ListAPIView):
    queryset = models.Question.objects.all()
    serializer_class = serializers.QuestionSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        question_id = self.request.query_params.get('question')
        tempobj_id = self.request.query_params.get('tempobj')
        temppractice_obj = models.TemporaryMentorPracticeReplaceQuestions.objects.get(id=int(tempobj_id))
        if not temppractice_obj:
            raise ParseError("Object with this id DoesNotExist")
        currenttime = timezone.now()
        # if currenttime >= paper_obj.exam_start_date_time:
        #     raise ParseError("You cannot replace the question once the test has started")
        quesIds = []
        questions = temppractice_obj.questions.all()
        quesIds = [question.id for question in questions]
      
        if question_id:
            question_obj = models.Question.objects.get(id=int(question_id))
            if question_obj:
                tagIds = []
                ftags = question_obj.linked_topics.all()
                tagIds = [tag.id for tag in ftags]
                eng_obj = models.QuestionLanguage.objects.get(text='English')
                try:
                    new_ques_obj = models.Question.objects.filter(is_active=True, linked_topics__in=tagIds, languages=eng_obj, difficulty=question_obj.difficulty, type_of_question=question_obj.type_of_question).order_by('?').distinct().exclude(id__in=quesIds)[:1]
                    
                except:
                    return Response({"message": "no replacement question found"}, status=status.HTTP_400_BAD_REQUEST)
            if not question_obj:
                raise ParseError("Question with this id DoesNotExist")
        if not question_id:
            raise ParseError("Please select at least one question")
        if new_ques_obj:
            return new_ques_obj
        else:
            return []

class FindReplacementQuestionPaperViewSet(ListAPIView):
    queryset = models.Question.objects.all()
    serializer_class = serializers.QuestionSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        question_id = self.request.query_params.get('question')
        tempobj_id = self.request.query_params.get('tempobj')
        temppaper_obj = models.TemporaryMentorActualPaperReplaceQuestions.objects.get(id=int(tempobj_id))
        if not temppaper_obj:
            raise ParseError("Object with this id DoesNotExist")
        currenttime = timezone.now()
        # if currenttime >= paper_obj.exam_start_date_time:
        #     raise ParseError("You cannot replace the question once the test has started")
        quesIds = []
        questions = temppaper_obj.questions.all()
        quesIds = [question.id for question in questions]
      
        if question_id:
            question_obj = models.Question.objects.get(id=int(question_id))
            if question_obj:
                tagIds = []
                ftags = question_obj.linked_topics.all()
                tagIds = [tag.id for tag in ftags]
                eng_obj = models.QuestionLanguage.objects.get(text='English')
                try:
                    new_ques_obj = models.Question.objects.filter(is_active=True, linked_topics__in=tagIds, languages=eng_obj, difficulty=question_obj.difficulty, type_of_question=question_obj.type_of_question).order_by('?').distinct().exclude(id__in=quesIds)[:1]
                    
                except:
                    return Response({"message": "no replacement question found"}, status=status.HTTP_400_BAD_REQUEST)
            if not question_obj:
                raise ParseError("Question with this id DoesNotExist")
        if not question_id:
            raise ParseError("Please select at least one question")
        if new_ques_obj:
            return new_ques_obj
        else:
            return []

class ReplaceQuestionInMentorPracticeTempObjView(UpdateAPIView):
    serializer_class = serializers.TemporaryMentorPracticeReplaceQuestionsSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        try:
            questionid = request.data.get('question')
            ques_obj = models.Question.objects.get(id=int(questionid))
        except:
            ques_obj = None
        if not ques_obj:
            return Response({"message": "question with this id does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            newquestionid = request.data.get('newquestion')
            newquestion_obj = models.Question.objects.get(id=int(newquestionid))
        except:
            newquestion_obj = None
        if not newquestion_obj:
            return Response({"message": "replacement question with this id does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            tmpobjid = request.data.get('tmpobj')
            tmp_obj = models.TemporaryMentorPracticeReplaceQuestions.objects.get(id=int(tmpobjid))
            currenttime = timezone.now()
            exam_end_date_time = tmp_obj.exam_end_date_time
            if exam_end_date_time and (currenttime >= exam_end_date_time):
                return Response({'message': 'you cannot change the questions now, you are ahead of exam end time..' }, status=status.HTTP_400_BAD_REQUEST)
        except:
            tmp_obj = None
        if not tmp_obj:
            return Response({"message": "error in fetching object details"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            tmp_obj.questions.remove(ques_obj)
            tmp_obj.save()
            tmp_obj.questions.add(newquestion_obj)
            tmp_obj.save()
            # models.TemporaryMentorPaperReplaceQuestions.objects.filter(paper=assessmentpaper_obj).delete()
           
        return Response(self.serializer_class(tmp_obj).data, status=201)

class ReplaceQuestionInMentorActualPaperTempObjView(UpdateAPIView):
    serializer_class = serializers.TemporaryMentorPaperReplaceQuestionsSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        try:
            questionid = request.data.get('question')
            ques_obj = models.Question.objects.get(id=int(questionid))
        except:
            ques_obj = None
        if not ques_obj:
            return Response({"message": "question with this id does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            newquestionid = request.data.get('newquestion')
            newquestion_obj = models.Question.objects.get(id=int(newquestionid))
        except:
            newquestion_obj = None
        if not newquestion_obj:
            return Response({"message": "replacement question with this id does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            tmpobjid = request.data.get('tmpobj')
            tmp_obj = models.TemporaryMentorActualPaperReplaceQuestions.objects.get(id=int(tmpobjid))
            currenttime = timezone.now()
            exam_end_date_time = tmp_obj.exam_end_date_time
            if exam_end_date_time and (currenttime >= exam_end_date_time):
                return Response({'message': 'you cannot change the questions now, you are ahead of exam end time..' }, status=status.HTTP_400_BAD_REQUEST)
        except:
            tmp_obj = None
        if not tmp_obj:
            return Response({"message": "error in fetching object details"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            tmp_obj.questions.remove(ques_obj)
            tmp_obj.save()
            tmp_obj.questions.add(newquestion_obj)
            tmp_obj.save()
            # models.TemporaryMentorActualPaperReplaceQuestions.objects.filter(paper=assessmentpaper_obj).delete()
           
        return Response(self.serializer_class(tmp_obj).data, status=201)


class MakeMentorPracticePaperView(UpdateAPIView):
    serializer_class = serializers.MentorPaperSerializer

    def put(self, request, *args, **kwargs):
        # topicIds = []
        user = self.request.user
        subjectIds = []
        tmpobjid = request.data.get('tmpobj')
        tmp_obj = models.TemporaryMentorPracticeReplaceQuestions.objects.get(id=int(tmpobjid))
        if not tmp_obj:
            return Response({"message": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)
        exam_obj = course_models.Exam.objects.get(id=int(tmp_obj.exam.id))
        if not exam_obj:
            return Response({"message": "Exam not found"}, status=status.HTTP_400_BAD_REQUEST)
        if not exam_obj.is_active:
            mentorexamtmpobj = course_models.MentorExams.objects.get(user=user, exam=exam_obj)
            if mentorexamtmpobj:
                mentorexamtmpobj.is_active=False
                mentorexamtmpobj.save()
            return Response({"message": "Oops! Exam has been deactivated by admin"}, status=status.HTTP_400_BAD_REQUEST)
        paper_type = 'practice'
        show_time = True
        chapters_obj = course_models.Chapter.objects.filter(id=tmp_obj.chapter.id)
        subjectIds.extend(chapters_obj.values_list("subject", flat=True))
        # topicIds.extend(chapters_obj.values_list("topics", flat=True).all())
      
        try:
            batch_obj = models.Batch.objects.get(id=int(tmp_obj.batch.id))
        except:
            return Response({"message": "Batch not found"}, status=status.HTTP_400_BAD_REQUEST)
        mentor_exam_obj = course_models.MentorExams.objects.get(user=user, exam=exam_obj)
        mentor_exam_obj.is_active = True
        mentor_exam_obj.batches.add(batch_obj)
        mentor_exam_obj.save()
        currenttime = timezone.now()
        batch_practicecount_obj, _ = models.BatchTotalPracticePapers.objects.get_or_create(batch=batch_obj)
        total_time = 12000
        batch_practicecount_obj.count += 1
        batch_practicecount_obj.save()
        count = batch_practicecount_obj.count
        mentor_paper_obj = models.MentorPapers.objects.create(mentor=user, exam=exam_obj, batch=batch_obj, difficulty_level=tmp_obj.difficulty_level, paper_type=paper_type, paper_count=count, show_time=show_time)
        if paper_type == ExamType.PRACTICE:
            mentor_paper_obj.chapters.add(tmp_obj.chapter)
            mentor_paper_obj.save()
        try:
            mentor_paper_obj.exam_start_date_time = currenttime
        except:
            mentor_paper_obj.exam_start_date_time = None
        
        mentor_paper_obj.exam_end_date_time = tmp_obj.exam_end_date_time
        if mentor_paper_obj.exam_end_date_time and mentor_paper_obj.exam_start_date_time > mentor_paper_obj.exam_end_date_time:
                batch_practicecount_obj.count -= 1
                batch_practicecount_obj.save()
                mentor_paper_obj.delete()
                return Response({"message": "Start date can not be greater than end date"}, status=status.HTTP_400_BAD_REQUEST)
        
        exam_start_date_time = mentor_paper_obj.exam_start_date_time
        if exam_start_date_time < currenttime:
            
            batch_practicecount_obj.count -= 1
            batch_practicecount_obj.save()
            mentor_paper_obj.delete()
            return Response({"message": "Start Date can not be in past"}, status=status.HTTP_400_BAD_REQUEST)
        mentor_paper_obj.save()
        mentor_paper_obj.subjects.add(*subjectIds)
        mentor_paper_obj.save()
        
        try:
            mentor_paper_obj.total_time = total_time
            mentor_paper_obj.questions.add(*(tmp_obj.questions.all()))
            mentor_paper_obj.save()

            total_marks = 0
            instruction_ques = "Total Questions: " + str(len(mentor_paper_obj.questions.all()))
            paper_instruction_obj3 = models.MentorPaperInstructions.objects.create(paper=mentor_paper_obj,instruction=instruction_ques)
            if mentor_paper_obj.paper_type == 'paper':
                instruction_time = "Total Time (in Min): " + str(total_time)
                paper_instruction_obj = models.MentorPaperInstructions.objects.create(paper=mentor_paper_obj,instruction=instruction_time)
            if exam_obj:
                paper_instruction_obj2 = models.MentorPaperInstructions.objects.create(paper=mentor_paper_obj)
                
                distribution_based_on_type = QuestionDistribution.distribute_based_on_type_of_questions(
                    mentor_paper_obj.questions.all()
                )
                
                total_marks_grouped_by_exam_type_of_question = course_models.QuestionType.objects.filter(
                    exam=exam_obj, 
                    type_of_question__in=[mentor_paper_obj.questions.all().values_list("type_of_question", flat=True)],
                ).exclude(type_of_question="subjective").values("exam", "type_of_question"
                ).order_by("exam").annotate(total_marks=Sum("marks"))
                
                for marks in total_marks_grouped_by_exam_type_of_question:
                    multiplier = distribution_based_on_type.get(marks["type_of_question"], 0)    
                    total_marks += marks["total_marks"]*multiplier
                instruction_marks = "Max. Marks: " + str(total_marks)
                mentor_paper_obj.marks = total_marks
                mentor_paper_obj.save()
                paper_instruction_obj2.instruction = instruction_marks
                paper_instruction_obj2.save()
                teacher_profile = profiles_models.Profile.objects.get(user=batch_obj.teacher)
                notification_type = NotificationType.objects.get(name="admin")
                for student in batch_obj.students.all():
                    if batch_obj.institute_room:
                        notification_text  = "Practice paper created and shared in batch: " + batch_obj.institute_room.grade.name + " - " + batch_obj.institute_room.name
                        message = "Mentor " + teacher_profile.first_name + " has created and shared a practice paper in your batch " + batch_obj.institute_room.grade.name + " - " + batch_obj.institute_room.name
                    else:
                        notification_text  = "Practice paper created and shared in batch: " + batch_obj.name
                        message = "Mentor " + teacher_profile.first_name + " has created and shared a practice paper in your batch " + batch_obj.name
                    Notifications.objects.create(user=student, mentor_paper=mentor_paper_obj, batch=batch_obj, notification=message, subject=notification_text, type=notification_type)
        except:
            batch_practicecount_obj.count -= 1
            batch_practicecount_obj.save()
            mentor_paper_obj.delete()
            return Response({"message": "error in fetching questions"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(mentor_paper_obj).data, status=201)


class MakeMentorActualPaperView(UpdateAPIView):
    serializer_class = serializers.MentorPaperSerializer

    def put(self, request, *args, **kwargs):
        # topicIds = []
        user = self.request.user
        subjectIds = []
        tmpobjid = request.data.get('tmpobj')
        tmp_obj = models.TemporaryMentorActualPaperReplaceQuestions.objects.get(id=int(tmpobjid))
        if not tmp_obj:
            return Response({"message": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)
        exam_obj = course_models.Exam.objects.get(id=int(tmp_obj.exam.id))
        if not exam_obj:
            return Response({"message": "Exam not found"}, status=status.HTTP_400_BAD_REQUEST)
        if not exam_obj.is_active:
            mentorexamtmpobj = course_models.MentorExams.objects.get(user=user, exam=exam_obj)
            if mentorexamtmpobj:
                mentorexamtmpobj.is_active=False
                mentorexamtmpobj.save()
            return Response({"message": "Oops! Exam has been deactivated by admin"}, status=status.HTTP_400_BAD_REQUEST)
        paper_type = 'paper'
        show_time = tmp_obj.show_time
        chapters_obj = course_models.Chapter.objects.filter(id__in=tmp_obj.chapters.all())
        subjectIds.extend(chapters_obj.values_list("subject", flat=True))
        # topicIds.extend(chapters_obj.values_list("topics", flat=True).all())
      
        try:
            batch_obj = models.Batch.objects.get(id=int(tmp_obj.batch.id))
        except:
            return Response({"message": "Batch not found"}, status=status.HTTP_400_BAD_REQUEST)
        mentor_exam_obj = course_models.MentorExams.objects.get(user=user, exam=exam_obj)
        mentor_exam_obj.is_active = True
        mentor_exam_obj.batches.add(batch_obj)
        mentor_exam_obj.save()
        currenttime = timezone.now()
        batch_paperecount_obj, _ = models.BatchTotalActualPapers.objects.get_or_create(batch=batch_obj)
        total_time = 12000
        batch_paperecount_obj.count += 1
        batch_paperecount_obj.save()
        count = batch_paperecount_obj.count
        mentor_paper_obj = models.MentorPapers.objects.create(mentor=user, exam=exam_obj, batch=batch_obj, difficulty_level=tmp_obj.difficulty_level, paper_type=paper_type, paper_count=count, show_time=show_time)
        if paper_type == ExamType.PRACTICE:
            mentor_paper_obj.chapters.add(*tmp_obj.chapters)
            mentor_paper_obj.save()
        try:
            mentor_paper_obj.exam_start_date_time = tmp_obj.exam_start_date_time
        except:
            mentor_paper_obj.exam_start_date_time = None
        
        mentor_paper_obj.exam_end_date_time = tmp_obj.exam_end_date_time
        mentor_paper_obj.save()
        if mentor_paper_obj.exam_end_date_time and mentor_paper_obj.exam_start_date_time > mentor_paper_obj.exam_end_date_time:
                batch_paperecount_obj.count -= 1
                batch_paperecount_obj.save()
                mentor_paper_obj.delete()
                return Response({"message": "Start date can not be greater than end date"}, status=status.HTTP_400_BAD_REQUEST)
        
        exam_start_date_time = mentor_paper_obj.exam_start_date_time
        if exam_start_date_time < currenttime:
            
            batch_paperecount_obj.count -= 1
            batch_paperecount_obj.save()
            mentor_paper_obj.delete()
            return Response({"message": "Start Date can not be in past"}, status=status.HTTP_400_BAD_REQUEST)
        mentor_paper_obj.save()
        mentor_paper_obj.subjects.add(*subjectIds)
        mentor_paper_obj.save()
        
        try:
            mentor_paper_obj.total_time = total_time
            mentor_paper_obj.questions.add(*(tmp_obj.questions.all()))
            mentor_paper_obj.save()

            total_marks = 0
            instruction_ques = "Total Questions: " + str(len(mentor_paper_obj.questions.all()))
            paper_instruction_obj3 = models.MentorPaperInstructions.objects.create(paper=mentor_paper_obj,instruction=instruction_ques)
            if mentor_paper_obj.paper_type == 'paper':
                instruction_time = "Total Time (in Min): " + str(total_time)
                paper_instruction_obj = models.MentorPaperInstructions.objects.create(paper=mentor_paper_obj,instruction=instruction_time)
            if exam_obj:
                paper_instruction_obj2 = models.MentorPaperInstructions.objects.create(paper=mentor_paper_obj)
                
                distribution_based_on_type = QuestionDistribution.distribute_based_on_type_of_questions(
                    mentor_paper_obj.questions.all()
                )
                
                total_marks_grouped_by_exam_type_of_question = course_models.QuestionType.objects.filter(
                    exam=exam_obj, 
                    type_of_question__in=[mentor_paper_obj.questions.all().values_list("type_of_question", flat=True)],
                ).exclude(type_of_question="subjective").values("exam", "type_of_question"
                ).order_by("exam").annotate(total_marks=Sum("marks"))
                
                for marks in total_marks_grouped_by_exam_type_of_question:
                    multiplier = distribution_based_on_type.get(marks["type_of_question"], 0)    
                    total_marks += marks["total_marks"]*multiplier
                instruction_marks = "Max. Marks: " + str(total_marks)
                mentor_paper_obj.marks = total_marks
                mentor_paper_obj.save()
                paper_instruction_obj2.instruction = instruction_marks
                paper_instruction_obj2.save()
                teacher_profile = profiles_models.Profile.objects.get(user=batch_obj.teacher)
                notification_type = NotificationType.objects.get(name="admin")
                for student in batch_obj.students.all():
                    if batch_obj.institute_room:
                        notification_text  = "Paper created and shared in batch: " + batch_obj.institute_room.grade.name + " - " + batch_obj.institute_room.name
                        message = "Mentor " + teacher_profile.first_name + " has created and shared a paper in your batch " + batch_obj.institute_room.grade.name + " - " + batch_obj.institute_room.name
                    else:
                        notification_text  = "Paper created and shared in batch: " + batch_obj.name
                        message = "Mentor " + teacher_profile.first_name + " has created and shared a paper in your batch " + batch_obj.name
                    Notifications.objects.create(user=student, mentor_paper=mentor_paper_obj, batch=batch_obj, notification=message, subject=notification_text, type=notification_type)
        except:
            batch_paperecount_obj.count -= 1
            batch_paperecount_obj.save()
            mentor_paper_obj.delete()
            return Response({"message": "error in fetching questions"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(mentor_paper_obj).data, status=201)

class LearnerExamGoalSViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    serializer_class = serializers.ViewLearnerExamGoalSerializer
    create_class = serializers.CreateLearnerExamGoalSerializer

    def get_queryset(self):
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            goals = models.LearnerExamGoals.objects.select_related("exam").prefetch_related("chapters"
            ).filter(user=self.request.user, exam__id=exam_id, is_active=True)
        else:
            goals = models.LearnerExamGoals.objects.select_related("exam").prefetch_related("chapters"
            ).filter(user=self.request.user, is_active=True)
        if goals:
            return goals
        else:
            return []

    def create(self, request, *args, **kwargs):
        serializer = self.create_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CreateExamGoalSelfAssessmentView(UpdateAPIView):
    serializer_class = serializers.SelfAssessAnswerPaperSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        
        goal = request.data.get('goal', None)
        if not goal:
            return Response({"message": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)
        
        goal_obj = models.LearnerExamGoals.objects.get(id=int(goal))
        exam_obj = course_models.Exam.objects.get(id=int(goal_obj.exam.id))
        course_models.LearnerExams.objects.get_or_create(user=user, exam=exam_obj)
        if not exam_obj.is_active:
            learnerexamtmpobj = course_models.LearnerExams.objects.filter(user=user, exam=exam_obj)
            if learnerexamtmpobj:
                learnerexamtmpobj = learnerexamtmpobj.first()
                learnerexamtmpobj.is_active=False
                learnerexamtmpobj.save()
            return Response({"message": "Oops! Exam has been deactivated by admin"}, status=status.HTTP_400_BAD_REQUEST)
        
        exam_self_assess_ques_obj = course_models.SelfAssessExamQuestions.objects.filter(exam=exam_obj)
        quesIds = [ques.question.id for ques in exam_self_assess_ques_obj]
        self_assess_ques_obj = course_models.SelfAssessQuestion.objects.filter(id__in=quesIds, is_active=True)
        if not self_assess_ques_obj:
            return Response({"message": "No questions found"}, status=status.HTTP_400_BAD_REQUEST)
        currenttime = timezone.now()
        paper_obj = models.SelfAssessExamAnswerPaper.objects.filter(
            user=user, goal=goal_obj).last()
        if not paper_obj:
            paper_obj = models.SelfAssessExamAnswerPaper.objects.create(
                user=user, goal=goal_obj, start_time = currenttime)
            paper_obj.questions.add(*self_assess_ques_obj)
            paper_obj.save()
            paper_obj.total_questions = len(paper_obj.questions.all())
            paper_obj.save()
        else:
            if paper_obj.paper_complete:
                return Response({"message": "You have already taken the self evaluation"}, status=status.HTTP_400_BAD_REQUEST)
            for ques in paper_obj.questions.all():
                if ques not in self_assess_ques_obj:
                    models.SelfAssessUserAnswer.objects.filter(question=ques).delete()
                    paper_obj.questions.remove(ques)
                    paper_obj.save()
            paper_obj.questions.add(*self_assess_ques_obj)
            paper_obj.save()
            paper_obj.total_questions = len(paper_obj.questions.all())
            paper_obj.save()
        return Response(self.serializer_class(paper_obj).data, status=201)

class FetchSelfAssessAnswerPaperViewSet(RetrieveAPIView,):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    lookup_field = 'pk'
    serializer_class = serializers.SelfAssessAnswerPaperSerializer

    def get_queryset(self):
        paper = models.SelfAssessExamAnswerPaper.objects.filter(pk=self.kwargs.get('pk'))
        if not paper:
            raise ParseError("Paper with this id DoesNotExist")
        return paper

class ExamAssessmentPaperView(ListAPIView, CreateAPIView):
    serializer_class = ViewSelfAssesQuestionSerializer
    permission_classes = [IsAuthenticated,]
    
    def get_queryset(self):
        
        questions, question_data = content_utils.get_student_self_assessment_questions(
            self.kwargs.get('assessmentpaper_id'))
        if not questions:
            return (None, None)
        return questions, question_data

    def list(self, request, *args, **kwargs):
     
        answer_paper_obj = models.SelfAssessExamAnswerPaper.objects.get(id=self.kwargs.get('assessmentpaper_id'))
        if answer_paper_obj.paper_complete:
            return Response({'exam_status': 'You have already taken your assessment', 'goal': answer_paper_obj.goal.id }, status=status.HTTP_200_OK)
           
        assessmentpaperdetails = serializers.SelfAssessAnswerPaperSerializer(answer_paper_obj, context={'request': request})
        # queryset = self.get_question_data()
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            # serializer = self.get_serializer(queryset[0], many=True)
            
            if answer_paper_obj:
                # answer_paper_obj_new = models.SelfAssessExamAnswerPaper.objects.filter(pk=self.kwargs.get('assessmentpaper_id'))
                return Response({
                    'assessmentpaperdetails':assessmentpaperdetails.data,
                    # 'answer_paper':answer_paper_obj_new.last(),
                    'question_data':queryset[1],
                    'questions': queryset[0]
                })
        return Response({'error': 'Error in Assessment Test Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    def create(self, request, *args, **kwargs):
        assessmentpaper_obj = models.SelfAssessExamAnswerPaper.objects.get(id=self.kwargs.get('assessmentpaper_id'))
        # reports = content_utils.get_student_assessment_report(self.request.user, assessmentpaper_obj.id)
        queryset = self.filter_queryset(self.get_queryset())
        questions = queryset[0]
        question_data = queryset[1]
        for i in range(0, len(questions)):
            if questions[i]['is_compulsory'] and (questions[i]['type_of_question'] == 'mcq' or questions[i]['type_of_question'] == 'mcc'):
                if not 'user_mcq_answer' in question_data[i]:
                    return Response({"message": "Please attempt all compulsory questions!"}, status=status.HTTP_400_BAD_REQUEST)
                if 'user_mcq_answer' in question_data[i] and len(question_data[i]['user_mcq_answer']) == 0:
                    return Response({"message": "Please attempt all compulsory questions!"}, status=status.HTTP_400_BAD_REQUEST)
            if questions[i]['is_compulsory'] and questions[i]['type_of_question'] == 'fillup':
                if not 'user_string_answer' in question_data[i]:
                    return Response({"message": "Please attempt all compulsory questions!"}, status=status.HTTP_400_BAD_REQUEST)
        goal_obj = models.LearnerExamGoals.objects.get(id=assessmentpaper_obj.goal.id)
        goal_obj.evaluation_done = True
        goal_obj.save()
        assessmentpaper_obj.paper_complete = True
        assessmentpaper_obj.save()

        return Response({'status': 'Assessment Paper Completed.'}, status=status.HTTP_200_OK)

class PostSelfAssessAnswerView(CreateAPIView):
    serializer_class = serializers.PostSelfAssessAnswerSerializer
    response_serializer_class = serializers.SelfAssessUserAnswerSerializer
    permission_classes = [IsAuthenticated,]

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        answer_paper = models.SelfAssessExamAnswerPaper.objects.get(id=request.data['answer_paper'])
        question = course_models.SelfAssessQuestion.objects.get(id=request.data['question'])
        user_answer = models.SelfAssessUserAnswer.objects.filter(answer_paper=answer_paper, question=question)
        answer_paper.question_unanswered.remove(question)
        answer_paper.question_answered.add(question)
        answer_paper.save()
        headers = self.get_success_headers(serializer.data)
        return Response(self.response_serializer_class(user_answer.last()).data, status=status.HTTP_201_CREATED, headers=headers)

class FetchGoalExamQuestionsView(UpdateAPIView):
    serializer_class = serializers.CardViewLearnerPaperSerializer

    def put(self, request, *args, **kwargs):
        # topicIds = []
        user = self.request.user
        subjectIds = []
        chapters = []
        goal = request.data.get('goal', None)
        if not goal:
            return Response({"message": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)
        
        goal_obj = models.LearnerExamGoals.objects.get(id=int(goal))
        exam_obj = course_models.Exam.objects.get(id=int(goal_obj.exam.id))
        if not exam_obj.is_active:
            learnerexamtmpobj = course_models.LearnerExams.objects.filter(user=user, exam=exam_obj)
            if learnerexamtmpobj:
                learnerexamtmpobj = learnerexamtmpobj.first()
                learnerexamtmpobj.is_active=False
                learnerexamtmpobj.save()
            return Response({"message": "Oops! Exam has been deactivated by admin"}, status=status.HTTP_400_BAD_REQUEST)
        
        ques_type_obj = course_models.QuestionType.objects.filter(exam=exam_obj)
        question_types = []
        question_types.extend(ques_type_obj.values_list("type_of_question", flat=True))
        difficulty = 5
        
        paper_type = 'paper'
        show_time = True
        chapters_obj = goal_obj.chapters.all()
        chapters.extend(chapters_obj.values_list("id", flat=True))
        subjectIds.extend(chapters_obj.values_list("subject", flat=True))
        
        # topicIds.extend(chapters_obj.values_list("topics", flat=True).all())
        
        avg_time_obj = course_models.ExamAverageTimePerQuestion.objects.filter(exam=exam_obj)
        try:
            total_ques = int(request.data.get('totalQues'))
        except:
            total_ques = 20
        total_time = total_ques * avg_time_obj.last().time

        learner_papercount_obj, _ = models.LearnerTotalActualPapers.objects.get_or_create(user=user)
        learner_papercount_obj.count += 1
        learner_papercount_obj.save()
        count = learner_papercount_obj.count
            
        learner_paper_obj = models.LearnerPapers.objects.create(
            user=user, paper_type=paper_type, paper_count=count, show_time=show_time)
        learner_paper_obj.subjects.add(*subjectIds)
        learner_paper_obj.save()
        
        try:
            learner_exam_obj, _ = course_models.LearnerExams.objects.get_or_create(user=user, exam=exam_obj)
            learner_exam_obj.is_active = True
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
        
        learner_history_obj, _ = models.LearnerHistory.objects.get_or_create(user=user)
        eng_obj = models.QuestionLanguage.objects.get(text=QuestionLanguage.ENGLISH)


        try:
            questions = QuestionDistribution.get_equally_distributed_subjectwise_questions(
                learner_paper_obj.id, 'learnerpaper', subjectIds, selectedRange, chapters,  total_ques, eng_obj, question_types
            )
            logger.info(f"Questions count {len(questions)}")
            
            if len(questions) == 0:
                learner_papercount_obj.count -= 1
                learner_papercount_obj.save()
                learner_paper_obj.delete()
                return Response({"message": "No questions found"}, status=status.HTTP_400_BAD_REQUEST)
            learner_paper_obj.total_time = total_time
            learner_paper_obj.questions.add(*list(questions))
            learner_paper_obj.save()
            learner_history_obj.papers.add(learner_paper_obj)
            learner_history_obj.total_questions += len(questions)
            learner_history_obj.questions.add(*list(questions))
            learner_history_obj.save()
            total_marks = 0
          
            instruction_ques = "Total Questions: " + str(learner_paper_obj.questions.count())
            paper_instruction_obj3 = models.PaperInstructions.objects.create(paper=learner_paper_obj,instruction=instruction_ques)
            if learner_paper_obj.paper_type == 'paper':
                instruction_time = "Total Time (in Min): " + str(total_time)
                paper_instruction_obj = models.PaperInstructions.objects.create(paper=learner_paper_obj,instruction=instruction_time)
            if exam_obj:
                learnerexam_history_obj, _ = models.LearnerExamHistory.objects.get_or_create(user=user, exam=exam_obj)
                
                learnerexam_paper_history_obj,_ = models.LearnerExamPaperHistory.objects.get_or_create(user=user, exam=exam_obj)
               
                learnerexam_history_obj.total_questions += questions.count()
                learnerexam_history_obj.save()
                
                learnerexam_history_obj.questions.add(*list(questions))
                learnerexam_history_obj.papers.add(learner_paper_obj)
                learnerexam_history_obj.save()
                learnerexam_paper_history_obj.questions.add(*list(questions))
                learnerexam_paper_history_obj.papers.add(learner_paper_obj)
                learnerexam_paper_history_obj.save()

                paper_instruction_obj2 = models.PaperInstructions.objects.create(paper=learner_paper_obj)

                distribution_based_on_type = QuestionDistribution.distribute_based_on_type_of_questions(
                    learner_paper_obj.questions.all()
                )
                
                total_marks_grouped_by_exam_type_of_question = course_models.QuestionType.objects.filter(
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
            learner_papercount_obj.count -= 1
            learner_papercount_obj.save()
            
            learner_paper_obj.delete()
            return Response({"message": "error in fetching questions"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(learner_paper_obj).data, status=201)

class EditLearnerGoalViewSet(RetrieveUpdateAPIView):
    queryset = models.Question.objects.all()
    serializer_class = serializers.ViewLearnerExamGoalSerializer
    update_serializer_class = serializers.ViewLearnerExamGoalSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        goal = models.LearnerExamGoals.objects.filter(pk=self.kwargs.get('pk'))
        if not goal:
            raise ParseError("Goal with this id DoesNotExist")
        return goal

    def update(self, request, *args, **kwargs):
        goal = models.LearnerExamGoals.objects.get(pk=self.kwargs.get('pk'))
        serializer = self.update_serializer_class(
            goal, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(goal).data, status=status.HTTP_200_OK)

class FetchExamGoalSelfAssessPaperSViewSet(ListAPIView):
    permission_classes = [IsAuthenticated, ]
    serializer_class = serializers.SelfAssessAnswerPaperSerializer

    def get_queryset(self):
        goal_id = self.request.query_params.get('goal')
        paper = models.SelfAssessExamAnswerPaper.objects.filter(user=self.request.user, goal__id=goal_id)
        if paper:
            return paper
        else:
            return []

class SyncChapterMasterFtagView(APIView):

    def put(self, request, *args, **kwargs):
        
        chapter = request.data.get('chapter', None)
        if not chapter:
            return Response({"message": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)
        
        chapter_obj = course_models.Chapter.objects.get(id=int(chapter))
        mastertag_obj, _ = models.ChapterMasterFTag.objects.get_or_create(chapter=chapter_obj)
        
        ftagids = chapter_obj.topics.values_list("id", flat=True)
        quesIds = models.Question.objects.prefetch_related("linked_topics").filter(
            linked_topics__in=ftagids,
            is_active=True).values_list("id", flat=True)
        
        try:
            mastertag_obj.questions.clear()
            mastertag_obj.save()
            mastertag_obj.questions.add(*quesIds)
            mastertag_obj.save()
        except Exception as e:
            return Response({"message": "Master Tag failed to update due to {e}"}, status=200)

        return Response({"message": "Master Tag succesfully updated "}, status=200)

class FetchQuestionsByChapterMasterFTagViewSet(ListAPIView):
    queryset = models.Question.objects.all()
    serializer_class = serializers.QuestionSerializer
    pagination_class = core_paginations.CustomPagination
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        chapter = self.request.query_params.get('chapter')
        if chapter:
            mastertag_obj = models.ChapterMasterFTag.objects.get(chapter__id=chapter)
            # quesIds = []
            quesIds = mastertag_obj.questions.values_list("id", flat=True)
            # quesIds = [que.id for que in ques]
            question_obj = models.Question.objects.filter(id__in=quesIds).order_by('id')
            return question_obj

class QuestionCountByTypeAndChapterMasterFTagViewSet(APIView):
    # queryset = models.Question.objects.all()
    serializer_class = serializers.QuestionSerializer
    permission_classes = (IsAuthenticated,)
    # parser_classes = (FormParser, MultiPartParser)

    def put(self, request, *args, **kwargs):
        ques_type = self.request.query_params.get('type')
        chapter = self.request.query_params.get('chapter')
        count = 0
        if chapter:
            mastertag_obj = models.ChapterMasterFTag.objects.get(chapter__id=chapter)
            quesIds = mastertag_obj.questions.values_list("id", flat=True)
            question_obj = models.Question.objects.filter(
                id__in=quesIds, type_of_question=ques_type).count()
            if question_obj:
                count = question_obj
            else:
                count = 0
        return Response({'count': count})

class TopTenExamsLeaderboard(ListAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        exam_data = content_utils.get_topten_exams()
        if not exam_data:
            return None
        else:
            return exam_data

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            return Response({
                'count_data': queryset
            })
        return Response({'error': 'Error in Fetching Data.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class LearnerGoalPathFetchQuestionsViewSet(UpdateAPIView):
    #permission_classes = (IsAuthenticated,)
    serializer_class = serializers.CardViewGoalAssessmentExamAnswerPaperSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        goal_obj = models.LearnerExamGoals.objects.get(id=request.data.get('goal', None))
        eng_obj = models.QuestionLanguage.objects.get(text='English') 
        check_pregoal_paper = models.GoalAssessmentExamAnswerPaper.objects.filter(goal=goal_obj, pregoal_paper=True).last()
        if check_pregoal_paper and (not check_pregoal_paper.paper_complete):
            return Response(self.serializer_class(check_pregoal_paper).data, status=201)
        elif check_pregoal_paper and (check_pregoal_paper.paper_complete):
            return Response({"message": "Oops! You have already attempted pre goal assessment paper"}, status=status.HTTP_400_BAD_REQUEST)
        ques_data = None
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json'}

        #url = "http://52.66.240.183/selfassessquestionids?learnerexamgoal={0}&language_id={1}".format(goal_obj.id, eng_obj.id)
        url = "http://20.40.54.177/selfassessquestionids?learnerexamgoal={0}&language_id={1}".format(goal_obj.id, eng_obj.id)
        #url = "http://127.0.0.1:8000/selfassessquestionids?learnerexamgoal={0}&language_id={1}".format(goal_obj.id, eng_obj.id)

        try:
            r = requests.get(url)
            ques_data = r.json()
            print("print krna h ",ques_data)
        except:
            ques_data = None
            print ("failed")
        
        subjectIds = []
        chapters = []

        exam_obj = course_models.Exam.objects.get(id=int(goal_obj.exam.id))
        if not exam_obj.is_active:
            learnerexamtmpobj = course_models.LearnerExams.objects.filter(user=user, exam=exam_obj)
            if learnerexamtmpobj:
                learnerexamtmpobj = learnerexamtmpobj.first()
                learnerexamtmpobj.is_active=False
                learnerexamtmpobj.save()
            return Response({"message": "Oops! Exam has been deactivated by admin"}, status=status.HTTP_400_BAD_REQUEST)
        
        paper_type = 'paper'
        show_time = True
        chapters_obj = goal_obj.chapters.all()
        chapters.extend(chapters_obj.values_list("id", flat=True))
        subjectIds.extend(chapters_obj.values_list("subject", flat=True))

        avg_time_obj = course_models.ExamAverageTimePerQuestion.objects.filter(exam=exam_obj)
        total_ques = 0
        # learner_papercount_obj, _ = models.LearnerTotalActualPapers.objects.get_or_create(user=user)
        # learner_papercount_obj.count += 1
        # learner_papercount_obj.save()
        # count = learner_papercount_obj.count
            
        learner_paper_obj = models.GoalAssessmentExamAnswerPaper.objects.create(
            user=user, goal=goal_obj, pregoal_paper=True, paper_type=paper_type, show_time=show_time)
        learner_paper_obj.subjects.add(*subjectIds)
        learner_paper_obj.save()
        learner_paper_obj.chapters.add(*chapters)
        learner_paper_obj.save()

        # learner_history_obj, _ = models.LearnerHistory.objects.get_or_create(user=user)

        questionIds = []
        for data in ques_data:
            subject_obj = course_models.Subject.objects.filter(id__in=subjectIds, title__icontains=data['subject_title']).last()
           
            
            for ques in data['questions']:
                if ques == 0:
                    continue
                learner_paper_obj.questions.add(ques)
                learner_paper_obj.save()
                questionIds.append(ques)
                total_ques += 1
                models.TemporaryPaperSubjectQuestionDistribution.objects.create(goal_paper_id=learner_paper_obj.id, subject_id=subject_obj.id, question_id=ques)
        
        total_time = total_ques * avg_time_obj.last().time
            
        try:
            learner_paper_obj.total_time = total_time
            learner_paper_obj.save()
            
            total_marks = 0
            
            instruction_ques = "Total Questions: " + str(learner_paper_obj.questions.count())
            paper_instruction_obj3 = models.GoalAssessmentExamPaperInstructions.objects.create(paper=learner_paper_obj,instruction=instruction_ques)
            if learner_paper_obj.paper_type == 'paper':
                instruction_time = "Total Time (in Min): " + str(total_time)
                paper_instruction_obj = models.GoalAssessmentExamPaperInstructions.objects.create(paper=learner_paper_obj,instruction=instruction_time)
            if exam_obj:
                # learnerexam_history_obj, _ = models.LearnerExamHistory.objects.get_or_create(user=user, exam=exam_obj)
                
                # learnerexam_paper_history_obj,_ = models.LearnerExamPaperHistory.objects.get_or_create(user=user, exam=exam_obj)
                
                # learnerexam_history_obj.total_questions += total_ques
                # learnerexam_history_obj.save()
                
                # learnerexam_history_obj.questions.add(*questionIds)
                # learnerexam_history_obj.papers.add(learner_paper_obj)
                # learnerexam_history_obj.save()
                # learnerexam_paper_history_obj.questions.add(*questionIds)
                # learnerexam_paper_history_obj.papers.add(learner_paper_obj)
                # learnerexam_paper_history_obj.save()

                paper_instruction_obj2 = models.GoalAssessmentExamPaperInstructions.objects.create(paper=learner_paper_obj)

                distribution_based_on_type = QuestionDistribution.distribute_based_on_type_of_questions(
                    learner_paper_obj.questions.all()
                )
                
                total_marks_grouped_by_exam_type_of_question = course_models.QuestionType.objects.filter(
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
            # learner_papercount_obj.count -= 1
            # learner_papercount_obj.save()
            
            learner_paper_obj.delete()
            return Response({"message": "error in fetching questions"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(learner_paper_obj).data, status=201)

class GoalQuestionAssessmentPaperView(ListAPIView, CreateAPIView):
    serializer_class = serializers.QuestionSerializer
    permission_classes = [IsAuthenticated,]
    
    def get_question_data(self):
        
        questions, remaining_time , question_data = content_utils.get_goal_assessment_questions(
            self.request.user, self.kwargs.get('assessmentpaper_id'))
        if not questions:
            return (None, None, None)
        return questions , remaining_time, question_data

    def list(self, request, *args, **kwargs):
        
        assessmentpaper_obj = models.GoalAssessmentExamAnswerPaper.objects.select_related(
            "user", "goal", "goal__exam").prefetch_related(
                "questions", "subjects", "questions__contents", "goal__exam__userboard",
                "goal__exam__subjects", "goal__exam__userclass"
        ).get(id=self.kwargs.get('assessmentpaper_id'))
       
        currenttime = timezone.now()
        # answer_paper_obj = models.AnswerPaper.objects.filter(user=self.request.user ,assessment_paper=assessmentpaper_obj)
        if assessmentpaper_obj:
            starttime = assessmentpaper_obj.start_time
            if assessmentpaper_obj.paper_complete:
                assessmentpaper_obj.submitted = True
                assessmentpaper_obj.save()
                return Response({'exam_status': 'your paper has been finished' }, status=status.HTTP_200_OK)
            else:
                if assessmentpaper_obj.pause_count > 0:
                    if (assessmentpaper_obj.remaining_time <= 0):
                        assessmentpaper_obj.submitted = True
                        assessmentpaper_obj.save()
                        return Response({'exam_status': 'your paper has been finished' }, status=status.HTTP_200_OK)
                else:
                    if (currenttime >= (starttime + timedelta(minutes=int(assessmentpaper_obj.total_time)))):
                        assessmentpaper_obj.submitted = True
                        assessmentpaper_obj.save()
                        return Response({'exam_status': 'your paper has been finished' }, status=status.HTTP_200_OK)
      
        assessmentpaperdetails = serializers.GoalAssessmentExamAnswerPaperSerializer(assessmentpaper_obj, context={'request': request})
        queryset = self.get_question_data()
        if queryset:
            answer_paper = assessmentpaper_obj.id
            return Response({
                'assessmentpaperdetails':assessmentpaperdetails.data,
                'answer_paper':answer_paper,
                'attempt_order':1,
                'remaining_time':queryset[1],
                'question_data':queryset[2],
                'questions': queryset[0]
            })
        return Response({'error': 'Error in Assessment Test Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)


    def create(self, request, *args, **kwargs):
        assessmentpaper_obj = models.GoalAssessmentExamAnswerPaper.objects.get(id=self.kwargs.get('assessmentpaper_id'))
      
        assessmentpaper_obj.paper_complete = True
        currenttime = timezone.now()
        starttime = assessmentpaper_obj.start_time
        time_spent = ((currenttime - starttime).seconds / 60)
        if int(time_spent) > int(assessmentpaper_obj.total_time):
            assessmentpaper_obj.time_taken = assessmentpaper_obj.total_time
        else:
            assessmentpaper_obj.time_taken = int(time_spent)
        assessmentpaper_obj.save()
        assessmentpaper_obj.submitted = True
        assessmentpaper_obj.save()

        return Response({'status': 'Assessment Paper Completed.'}, status=status.HTTP_200_OK)

class GoalPaperInstructionsViewSet(ListAPIView):
    queryset = models.GoalAssessmentExamPaperInstructions.objects.all()
    serializer_class = serializers.GoalPaperInstructionsSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        paper_id = self.request.query_params.get('paper')
        if paper_id:
            paper_obj = models.GoalAssessmentExamAnswerPaper.objects.get(id=int(paper_id))
            instruction_obj = models.GoalAssessmentExamPaperInstructions.objects.filter(paper=paper_obj).order_by('id')
            if instruction_obj:
                return instruction_obj
            else:
                return []

class GoalAssessmentPostAnswerView(CreateAPIView):
    serializer_class = serializers.PostAnswerGoalAssessmentSerializer
    response_serializer_class = serializers.GoalAssessmentUserAnswerSerializer
    permission_classes = [IsAuthenticated,]

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        answer_paper = models.GoalAssessmentExamAnswerPaper.objects.get(id=request.data['answer_paper'])
        question = models.Question.objects.get(id=request.data['question'])
        user_answer = models.GoalAssessmentUserAnswer.objects.filter(answer_paper=answer_paper, question=question)
        if request.data['is_cleared']:
            answer_paper.question_answered.remove(question)
            answer_paper.question_unanswered.add(question)
            answer_paper.question_markforreview.remove(question)
            answer_paper.question_save_markforreview.remove(question)
            if user_answer:
                user_answer[0].delete()
        else:
            answer_paper.question_unanswered.remove(question)
            answer_paper.question_answered.add(question)
            answer_paper.question_markforreview.remove(question)
            answer_paper.question_save_markforreview.remove(question)
        if request.data['mark_for_review']:
            answer_paper.question_markforreview.add(question)
        if request.data['save_mark_for_review']:
            answer_paper.question_save_markforreview.add(question)
            answer_paper.question_markforreview.remove(question)
        answer_paper.save()
        headers = self.get_success_headers(serializer.data)
        return Response(self.response_serializer_class(user_answer.last()).data, status=status.HTTP_201_CREATED, headers=headers)

class GoalAssessmentPaperPostSubmitView(CreateAPIView):
    serializer_class = serializers.QuestionSerializer
    permission_classes = [IsAuthenticated,]

    def create(self, request, *args, **kwargs):
        user = self.request.user
        assessmentpaper_obj = models.GoalAssessmentExamAnswerPaper.objects.get(id=self.kwargs.get('assessmentpaper_id'))
        
        reports = content_utils.get_student_goal_assessment_report(self.request.user, assessmentpaper_obj.id)
        # answer_paper = models.AnswerPaper.objects.filter(user=self.request.user, assessment_paper=assessmentpaper_obj).last()
       
        assessmentpaper_obj.score = reports['score']
        assessmentpaper_obj.save()
        # learner_exam_obj = course_models.LearnerExams.objects.get(id=int(assessmentpaper_obj.learner_exam.id))
        exam_obj = course_models.Exam.objects.get(id=int(assessmentpaper_obj.goal.exam.id))
        goal_obj = models.LearnerExamGoals.objects.get(id=int(assessmentpaper_obj.goal.id))
        learner_exam_obj = course_models.LearnerExams.objects.filter(user=user, exam=exam_obj).last()
        
        for subject in reports['subjects']:
            subject_obj = course_models.Subject.objects.get(id=int(subject['id']))
            exam_subject_obj, _ = models.LearnerExamSubjects.objects.get_or_create(learner_exam=learner_exam_obj, subject=subject_obj)
               
            exam_paper_subject_obj, _ = models.LearnerExamPaperSubjects.objects.get_or_create(learner_exam=learner_exam_obj, subject=subject_obj)
            
            exam_subject_obj.total_marks += subject['total']
            exam_subject_obj.score += subject['score']
            exam_subject_obj.attempted += subject['attempted']
            exam_subject_obj.correct += subject['correct']
            exam_subject_obj.incorrect += subject['incorrect']
            exam_subject_obj.unchecked += subject['unchecked']
            exam_subject_obj.save()
            if exam_subject_obj.total_marks == 0:
                exam_subject_obj.percentage = 0
            else:
                exam_subject_obj.percentage = (exam_subject_obj.score * 100) / exam_subject_obj.total_marks
            exam_subject_obj.save()
            
            exam_paper_subject_obj.total_marks += subject['total']
            exam_paper_subject_obj.score += subject['score']
            exam_paper_subject_obj.attempted += subject['attempted']
            exam_paper_subject_obj.correct += subject['correct']
            exam_paper_subject_obj.incorrect += subject['incorrect']
            exam_paper_subject_obj.unchecked += subject['unchecked']
            exam_paper_subject_obj.save()
            if exam_paper_subject_obj.total_marks == 0:
                exam_paper_subject_obj.percentage = 0
            else:
                exam_paper_subject_obj.percentage = (exam_paper_subject_obj.score * 100) / exam_paper_subject_obj.total_marks
            exam_paper_subject_obj.save()
        for chapter in reports['chapters']:
            chapterobj = course_models.Chapter.objects.get(id=int(chapter['id']))
            subject_obj = course_models.Subject.objects.get(id=int(chapterobj.subject.id))
            
            chapter_obj, _ = models.LearnerExamChapters.objects.get_or_create(learner_exam=learner_exam_obj, chapter=chapterobj, subject=subject_obj)
            
            chaper_subject_obj, _ = models.LearnerExamSubjects.objects.get_or_create(learner_exam=learner_exam_obj, subject=subject_obj)
            
            chaper_paper_subject_obj, _ = models.LearnerExamPaperSubjects.objects.get_or_create(learner_exam=learner_exam_obj, subject=subject_obj)
            chapter_paper_obj, _ = models.LearnerExamPaperChapters.objects.get_or_create(learner_exam=learner_exam_obj, chapter=chapterobj, subject=subject_obj)
           
            chaper_subject_obj.chapters.add(chapter_obj)
            chaper_subject_obj.save()
            chapter_obj.total_marks += chapter['total']
            chapter_obj.score += chapter['score']
            chapter_obj.attempted += chapter['attempted']
            chapter_obj.correct += chapter['correct']
            chapter_obj.incorrect += chapter['incorrect']
            chapter_obj.unchecked += chapter['unchecked']
            chapter_obj.save()
            if chapter_obj.total_marks == 0:
                chapter_obj.percentage = 0
            else:
                chapter_obj.percentage = (chapter_obj.score * 100) / chapter_obj.total_marks
            chapter_obj.save()
            
            chaper_paper_subject_obj.chapters.add(chapter_paper_obj)
            chaper_paper_subject_obj.save()
            chapter_paper_obj.total_marks += chapter['total']
            chapter_paper_obj.score += chapter['score']
            chapter_paper_obj.attempted += chapter['attempted']
            chapter_paper_obj.correct += chapter['correct']
            chapter_paper_obj.incorrect += chapter['incorrect']
            chapter_paper_obj.unchecked += chapter['unchecked']
            chapter_paper_obj.save()
            if chapter_paper_obj.total_marks == 0:
                chapter_paper_obj.percentage = 0
            else:
                chapter_paper_obj.percentage = (chapter_paper_obj.score * 100) / chapter_paper_obj.total_marks
            chapter_paper_obj.save()
        assessmentpaper_obj.percentage = reports['percentage']
        assessmentpaper_obj.total_questions = reports['totalquestion']
        assessmentpaper_obj.attempted = reports['attempted']
        assessmentpaper_obj.correct = reports['corrected']
        assessmentpaper_obj.incorrect = reports['incorrected']
        assessmentpaper_obj.unchecked = reports['unchecked']
        assessmentpaper_obj.save()
        learnergoal_history_obj, _ = models.LearnerGoalHistory.objects.get_or_create(user=self.request.user, goal=goal_obj)
        # learner_history_obj = models.LearnerHistory.objects.get(user=self.request.user)
        # learner_history_obj, _ = models.LearnerHistory.objects.get_or_create(user=self.request.user)
        
        # temporary_bookmarks_obj = models.TemporaryLearnerBookmarks.objects.filter(paper=assessmentpaper_obj)
        # for bookmark in temporary_bookmarks_obj:
        #     # exam_subject_obj = models.LearnerExamSubjects.objects.get(learner_exam=bookmark.learner_exam, subject=bookmark.subject)
        #     exam_subject_obj, _ = models.LearnerExamSubjects.objects.get_or_create(learner_exam=bookmark.learner_exam, subject=bookmark.subject)
        #     # exam_chapter_obj = models.LearnerExamChapters.objects.get(learner_exam=bookmark.learner_exam, chapter=bookmark.chapter, subject=bookmark.subject)
        #     exam_chapter_obj, _ = models.LearnerExamChapters.objects.get_or_create(learner_exam=bookmark.learner_exam, chapter=bookmark.chapter, subject=bookmark.subject)
        #     bookmark_obj = models.LearnerBookmarks.objects.create(learner_exam=bookmark.learner_exam, subject=bookmark.subject, question=bookmark.question, chapter=bookmark.chapter)
        #     assessmentpaper_obj.bookmarks.add(bookmark_obj)
        #     assessmentpaper_obj.save()
        #     exam_subject_obj.total_bookmarks += 1
        #     exam_subject_obj.save()
        #     exam_chapter_obj.total_bookmarks += 1
        #     exam_chapter_obj.save()
        # models.TemporaryLearnerBookmarks.objects.filter(paper=assessmentpaper_obj).delete()
        if assessmentpaper_obj.paper_type == 'practice':
            learnerexam_practice_history_obj, _ = models.LearnerGoalPracticeHistory.objects.get_or_create(user=self.request.user, goal=goal_obj)
            learnergoal_history_obj.total_practice_time = learnergoal_history_obj.total_practice_time + assessmentpaper_obj.time_taken
            learnergoal_history_obj.save()
            learnerexam_practice_history_obj.total_time = learnerexam_practice_history_obj.total_time + assessmentpaper_obj.total_time
            learnerexam_practice_history_obj.time_taken = learnerexam_practice_history_obj.time_taken + assessmentpaper_obj.time_taken
            learnerexam_practice_history_obj.total_marks = learnerexam_practice_history_obj.total_marks + reports['totalscore']
            learnerexam_practice_history_obj.score = learnerexam_practice_history_obj.score + reports['score']
            learnerexam_practice_history_obj.attempted = learnerexam_practice_history_obj.attempted + reports['attempted']
            learnerexam_practice_history_obj.correct = learnerexam_practice_history_obj.correct + reports['corrected']
            learnerexam_practice_history_obj.skipped = learnerexam_practice_history_obj.skipped + reports['skipped']
            learnerexam_practice_history_obj.incorrect = learnerexam_practice_history_obj.incorrect + reports['incorrected']
            learnerexam_practice_history_obj.unchecked = learnerexam_practice_history_obj.unchecked + reports['unchecked']
            learnerexam_practice_history_obj.total_questions = learnerexam_practice_history_obj.total_questions + reports['totalquestion']
            learnerexam_practice_history_obj.save()
            if learnerexam_practice_history_obj.total_marks == 0:
                learnerexam_practice_history_obj.percentage = 0
            else:
                learnerexam_practice_history_obj.percentage = (learnerexam_practice_history_obj.score * 100) / learnerexam_practice_history_obj.total_marks
            learnerexam_practice_history_obj.save()
            # learner_history_obj.total_practice_time = learner_history_obj.total_practice_time + answer_paper.time_taken
            # learner_history_obj.save()
        else:
            learnerexam_paper_history_obj, _ = models.LearnerGoalPaperHistory.objects.get_or_create(user=self.request.user, goal=goal_obj)
            learnergoal_history_obj.total_paper_time = learnergoal_history_obj.total_paper_time + assessmentpaper_obj.time_taken
            learnergoal_history_obj.save()
            learnerexam_paper_history_obj.total_time = learnerexam_paper_history_obj.total_time + assessmentpaper_obj.total_time
            learnerexam_paper_history_obj.time_taken = learnerexam_paper_history_obj.time_taken + assessmentpaper_obj.time_taken
            learnerexam_paper_history_obj.total_marks = learnerexam_paper_history_obj.total_marks + reports['totalscore']
            learnerexam_paper_history_obj.score = learnerexam_paper_history_obj.score + reports['score']
            learnerexam_paper_history_obj.attempted = learnerexam_paper_history_obj.attempted + reports['attempted']
            learnerexam_paper_history_obj.correct = learnerexam_paper_history_obj.correct + reports['corrected']
            learnerexam_paper_history_obj.skipped = learnerexam_paper_history_obj.skipped + reports['skipped']
            learnerexam_paper_history_obj.incorrect = learnerexam_paper_history_obj.incorrect + reports['incorrected']
            learnerexam_paper_history_obj.unchecked = learnerexam_paper_history_obj.unchecked + reports['unchecked']
            learnerexam_paper_history_obj.total_questions = learnerexam_paper_history_obj.total_questions + reports['totalquestion']
            learnerexam_paper_history_obj.save()
            if learnerexam_paper_history_obj.total_marks == 0:
                learnerexam_paper_history_obj.percentage = 0
            else:
                learnerexam_paper_history_obj.percentage = (learnerexam_paper_history_obj.score * 100) / learnerexam_paper_history_obj.total_marks
            learnerexam_paper_history_obj.save()
            # learner_history_obj.total_paper_time = learner_history_obj.total_paper_time + answer_paper.time_taken
            # learner_history_obj.save()
        goal_obj.assessment_done = True
        goal_obj.save()
        assessmentpaper_obj.paper_complete = True
        assessmentpaper_obj.save()
        # models.TemporaryPaperSubjectQuestionDistribution.objects.filter(goal_paper=assessmentpaper_obj).delete()
        return Response({'status': 'Assessment Paper Processing Completed.'}, status=status.HTTP_200_OK)

class FetchGoalPapersByIdViewSet(RetrieveUpdateAPIView):
    queryset = models.GoalAssessmentExamAnswerPaper.objects.select_related("user", "goal"
        ).prefetch_related("questions", "subjects", "questions__tags", "questions__linked_topics", 
        "questions__contents", "questions__contents__language").all()
    serializer_class = serializers.GoalAssessmentExamAnswerPaperSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        learner_paper_obj = self.queryset.filter(pk=self.kwargs.get('pk'))
        if not learner_paper_obj:
            raise ParseError("Learner paper with this id DoesNotExist")
        return learner_paper_obj

    def list(self, request, *args, **kwargs):
        paper_obj = models.GoalAssessmentExamAnswerPaper.objects.select_related("user", "learner_exam"
        ).prefetch_related("questions", "subjects", "questions__tags", "questions__linked_topics", 
        "questions__contents", "questions__contents__language").get(id=self.kwargs.get('pk'))
        assessmentpaperdetails = serializers.GoalAssessmentExamAnswerPaperSerializer(paper_obj, context={'request': request})
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            return Response({
                'paperdetails':assessmentpaperdetails.data,
                'question_data':queryset[1],
            })
        return Response({'error': 'Error in Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class FetchShortGoalPapersByIdViewSet(RetrieveAPIView):
    queryset = models.GoalAssessmentExamAnswerPaper.objects.select_related("user", "goal"
        ).prefetch_related("questions", "subjects", "questions__tags", "questions__linked_topics", 
        "questions__contents", "questions__contents__language").all()
    serializer_class = serializers.CardViewGoalAssessmentExamAnswerPaperSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        learner_paper_obj = self.queryset.filter(pk=self.kwargs.get('pk'))
        if not learner_paper_obj:
            raise ParseError("Learner paper with this id DoesNotExist")
        return learner_paper_obj

class PauseGoalPaperViewSet(UpdateAPIView):
    serializer_class = serializers.CardViewGoalAssessmentExamAnswerPaperSerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        try:
            remainingseconds = request.data.get('remainingSeconds')
            learner_paper_id = request.data.get('paper')
            if not learner_paper_id:
                raise ParseError("Please enter paper id")
            else:   
                learner_paper_obj = models.GoalAssessmentExamAnswerPaper.objects.get(id=int(learner_paper_id))
            if not learner_paper_obj:
                raise ParseError("Learner Paper with this id DoesNotExist")
            if learner_paper_obj.pause_count >= 2:
                raise ParseError("Maximum 2 pause are allowed")
            learner_paper_obj.pause_count += 1
            learner_paper_obj.remaining_time = remainingseconds
            learner_paper_obj.save()
        except:
            return Response({"message": "Maximum 2 pause are allowed"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(learner_paper_obj).data, status=201)

class ResumeGoalPaperViewSet(UpdateAPIView):
    serializer_class = serializers.CardViewGoalAssessmentExamAnswerPaperSerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        try:
            remainingseconds = request.data.get('remainingSeconds')
            learner_paper_id = request.data.get('paper')
            if not learner_paper_id:
                raise ParseError("Please enter paper id")
            else:   
                learner_paper_obj = models.GoalAssessmentExamAnswerPaper.objects.get(id=int(learner_paper_id))
            if not learner_paper_obj:
                raise ParseError("Learner Paper with this id DoesNotExist")
            learner_paper_obj.remaining_time = remainingseconds
            if learner_paper_obj.remaining_time > 0:
                learner_paper_obj.submitted = False
            learner_paper_obj.save()
        except:
            return Response({"message": "error in resuming the exam"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(learner_paper_obj).data, status=201)

class GoalAssessmentPaperReportView(ListAPIView):
    permission_classes = [IsAuthenticated,]

    def get_queryset(self):
        try:
            if self.request.query_params.get('user'):
                user= auth_models.User.objects.get(username=self.request.query_params.get('user'))
            else:
                user = self.request.user
        except:
            user = self.request.user
        reports = content_utils.get_student_goal_assessment_report(user, self.kwargs.get('assessmentpaper_id'))

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
        return Response({'error': 'Error in Assessment Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)


class SyncMasterFtagByParticularTagView(APIView):

    def put(self, request, *args, **kwargs):
        
        ftagid = request.data.get('ftag', None)
        if not ftagid:
            return Response({"message": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)
        
        tag_obj = course_models.Topic.objects.get(id=int(ftagid))
        chapters = course_models.Chapter.objects.filter(topics=tag_obj)
        
        for chapter in chapters:
            mastertag_obj = models.ChapterMasterFTag.objects.filter(chapter=chapter).last()
            if mastertag_obj:
                ftagids = chapter.topics.values_list("id", flat=True)
                quesIds = models.Question.objects.prefetch_related("linked_topics").filter(
                    linked_topics__in=ftagids,
                    is_active=True).values_list("id", flat=True)
                
                try:
                    mastertag_obj.questions.clear()
                    mastertag_obj.save()
                    mastertag_obj.questions.add(*quesIds)
                    mastertag_obj.save()
                except Exception as e:
                    return Response({"message": "Master Tag failed to update due to {e}"}, status=200)

        return Response({"message": "Master Tag succesfully updated "}, status=200)

class DeleteMentorPaperTemporaryBookmarkViewSet(RetrieveUpdateAPIView):
    queryset = models.TemporaryMentorPaperLearnerBookmarks.objects.all()
    serializer_class = serializers.TemporaryMentorPaperBookmarksSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        bookmark_obj = models.TemporaryMentorPaperLearnerBookmarks.objects.filter(pk=self.kwargs.get('pk'))
        if not bookmark_obj:
            raise ParseError("Bookmark with this id DoesNotExist")
        return bookmark_obj
    
    def delete(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            bookmark_obj = models.TemporaryMentorPaperLearnerBookmarks.objects.get(pk=int(id))
            bookmark_obj.delete()
        except:
            return Response({"message": "Please enter valid Bookmark id"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Bookmark deleted successfully"}, status=201)

class InstituteClassRoomViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.ViewInstituteClassRoomSerializer
    create_class = serializers.CreateInstituteRoomSerializer

    def get_queryset(self):
        institute = self.request.query_params.get('institute')
        if institute:
            rooms = models.InstituteClassRoom.objects.filter(institute__id=institute)
        else:
            rooms = models.InstituteClassRoom.objects.all()
        return rooms
        # return models.LearnerQuery.objects.all().order_by('id')

    def create(self, request, *args, **kwargs):
        serializer = self.create_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class InstituteClassRoomByIdViewSet(RetrieveAPIView):
    queryset = models.InstituteClassRoom.objects.all()
    serializer_class = serializers.ViewInstituteClassRoomSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        room = models.InstituteClassRoom.objects.filter(pk=self.kwargs.get('pk'))
        if not room:
            raise ParseError("Room with this id DoesNotExist")
        return room

class FetchRoomBatchesViewSet(ListAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.ViewBatchSerializer
    create_class = serializers.CreateBatchSerializer

    def get_queryset(self):
        room = self.request.query_params.get('room')
        batches = models.Batch.objects.filter(institute_room__id=room)
        if batches:
            return batches
        else:
            return []

class FetchStudentsInRoomViewSet(ListAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.ViewUserClassRoomSerializer

    def get_queryset(self):
        room = self.request.query_params.get('room')
        institute_room = models.InstituteClassRoom.objects.get(id=room)
        studentrooms = models.UserClassRoom.objects.filter(institute_rooms=institute_room)
        if studentrooms:
            return studentrooms
        else:
            return []

class LinkUserClassRoomViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.ViewUserClassRoomSerializer
    create_class = serializers.CreateUserRoomSerializer

    def get_queryset(self):
        user = self.request.user
        room = models.UserClassRoom.objects.filter(user=user)
        if room:
            return room
        else:
            return []
        # return models.LearnerQuery.objects.all().order_by('id')

    def create(self, request, *args, **kwargs):
        serializer = self.create_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CreateClassRoomBatchView(APIView):
    # serializer_class = serializers.ViewBatchSerializer

    def post(self, request, *args, **kwargs):
        try:
            phonenumber = request.data.get('phonenumber')
            room = request.data.get('room')
            institute_room = models.InstituteClassRoom.objects.get(id=room)
            user=None
            user= auth_models.User.objects.filter(phonenumber=phonenumber).last()
            if user:
                if user.profile.user_group.name == 'teacher':
                    tmp_batch_obj = models.Batch.objects.filter(teacher=user, institute_room=institute_room)
                    if tmp_batch_obj:
                        return Response({"message": "room batch already created for this mentor"}, status=status.HTTP_400_BAD_REQUEST)
                    batch_obj = models.Batch.objects.create(teacher=user, batch_code=uuid.uuid4().hex[:6].upper(), institute_room=institute_room)
                    # students = models.UserClassRoom.objects.filter(institute_rooms=institute_room)
                    if len(batch_obj.students.all()) >= 250:
                        return Response({"message": "Maximum 250 students are allowed in a batch"}, status=status.HTTP_400_BAD_REQUEST)
                    students = models.UserClassRoom.objects.prefetch_related("institute_rooms").filter(
                    institute_rooms=institute_room).values_list("user", flat=True)
                    batch_obj.students.add(*students)
                    batch_obj.save()
                    for student in students:
                        models.LearnerBatches.objects.create(user_id=student, batch=batch_obj)
                    message = "Room Batch Successfully Created and existing Room students have been added"
                else:
                    return Response({"message": "not a mentor account"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                unreg_batch_obj = models.UnregisteredMentorBatch.objects.create(phonenumber=phonenumber, institute_room=institute_room)
                message = "Room Assignment saved into buffer and will be created as soon as the mentor registers into MMP"
        except:
            return Response({"message": "error in assigning the room"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": message}, status=201)

class AddStudentToRoomView(APIView):

    def put(self, request, *args, **kwargs):
        
        phonenumber = request.data.get('phonenumber', None)
        fullname = request.data.get('fullname', None)
        # if not phonenumber:
        #     return Response({"message": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)
        
        groupObj = UserGroup.objects.get(name='student')
        room = request.data.get('room')
        institute_room = models.InstituteClassRoom.objects.get(id=room)
        last_user_created_id = auth_models.User.objects.all().last().id
        username = create_username(str(10000 + last_user_created_id))
        try:
            if phonenumber:
                userdata = profiles_models.Profile.objects.filter(user_group=groupObj, institute=institute_room.institute).filter(Q(user__username__icontains=phonenumber) | Q(user__email__icontains=phonenumber) | Q(user__phonenumber__icontains=phonenumber)).last()
                checkuser = profiles_models.Profile.objects.filter(Q(user__username__icontains=phonenumber) | Q(user__email__icontains=phonenumber) | Q(user__phonenumber__icontains=phonenumber)).last()
                if checkuser and checkuser.user_group.name != 'student':
                    return Response({"message": "Not a student"}, status=status.HTTP_400_BAD_REQUEST)
                if userdata:
                    userroom_obj, _ = models.UserClassRoom.objects.get_or_create(user=userdata.user)
                    userroom_obj.institute_rooms.add(institute_room)
                    userroom_obj.save()
                    batches_obj = models.Batch.objects.filter(institute_room=institute_room, is_active=True)
                    for batch in batches_obj:
                        if len(batch.students.all()) < 250:
                            try:
                                learner_batch_obj = models.LearnerBatches.objects.get(user=userdata.user, batch=batch)
                            except:
                                learner_batch_obj = None
                            
                            if not learner_batch_obj:
                                learner_batch_obj = models.LearnerBatches.objects.create(user=userdata.user, batch=batch)
                            batch.students.add(userdata.user)
                            batch.save()
                elif not userdata and checkuser:
                    # return Response({"message": "Invalid user"}, status=status.HTTP_400_BAD_REQUEST)
                    models.StudentInstituteChangeInvitation.objects.create(user=checkuser.user, inviting_institute_room=institute_room)
                else:
                    isAvailable = False
                    check_usage = profiles_models.Profile.objects.filter(user__phonenumber=phonenumber).exists()
                    if check_usage:
                        isAvailable = False
                    else:
                        isAvailable = True
                    if not isAvailable:
                        text = "Contact number " + phonenumber +  " already in use by another user"
                        return Response({"message": text}, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        user_obj = auth_models.User.objects.create(username=username, phonenumber=phonenumber, fullname=fullname)
                        user_obj.set_password(username)
                        user_obj.save()
                        profile_obj = profiles_models.Profile.objects.get(user=user_obj)
                        profile_obj.user_group=groupObj
                        profile_obj.account_verified = True
                        profile_obj.contact_verified = True
                        profile_obj.institute = institute_room.institute
                        profile_obj.save()
                        userroom_obj, _ = models.UserClassRoom.objects.get_or_create(user=user_obj)
                        userroom_obj.institute_rooms.add(institute_room)
                        userroom_obj.save()
                        batches_obj = models.Batch.objects.filter(institute_room=institute_room, is_active=True)
                        for batch in batches_obj:
                            if len(batch.students.all()) < 250:
                                try:
                                    learner_batch_obj = models.LearnerBatches.objects.get(user=user_obj, batch=batch)
                                except:
                                    learner_batch_obj = None
                                
                                if not learner_batch_obj:
                                    learner_batch_obj = models.LearnerBatches.objects.create(user=user_obj, batch=batch)
                                batch.students.add(user_obj)
                                batch.save()
            else:
                if not fullname:
                    text = "Please enter fullname"
                    return Response({"message": text}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    user_obj = auth_models.User.objects.create(username=username, fullname=fullname)
                    user_obj.set_password(username)
                    user_obj.save()
                    profile_obj = profiles_models.Profile.objects.get(user=user_obj)
                    profile_obj.user_group=groupObj
                    profile_obj.account_verified = True
                    profile_obj.contact_verified = True
                    profile_obj.institute = institute_room.institute
                    profile_obj.save()
                    userroom_obj, _ = models.UserClassRoom.objects.get_or_create(user=user_obj)
                    userroom_obj.institute_rooms.add(institute_room)
                    userroom_obj.save()
                    batches_obj = models.Batch.objects.filter(institute_room=institute_room, is_active=True)
                    for batch in batches_obj:
                        if len(batch.students.all()) < 250:
                            try:
                                learner_batch_obj = models.LearnerBatches.objects.get(user=user_obj, batch=batch)
                            except:
                                learner_batch_obj = None
                            
                            if not learner_batch_obj:
                                learner_batch_obj = models.LearnerBatches.objects.create(user=user_obj, batch=batch)
                            batch.students.add(user_obj)
                            batch.save()
        except Exception as e:
            return Response({"message": "failed to update due to {e}"}, status=200)

        return Response({"message": "User Rooms succesfully updated "}, status=200)

class BulkAddStudentsInClassRoom(APIView):
    # permission_classes = [IsAuthenticated, ]

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
            room = request.data.get('room')
            institute_room = models.InstituteClassRoom.objects.get(id=room)
            groupObj = UserGroup.objects.get(name='student')
            student_rooms = []
            new_users = []
            errors = []
            for index, row in df.iterrows():
                last_user_created_id = auth_models.User.objects.all().last().id
                username = create_username(str(10000 + last_user_created_id))
                if "phonenumber" in head_list:
                    try:
                        phonenumber = str(int(row["phonenumber"]))
                    except:
                        phonenumber = str(row["phonenumber"])
                    if not (len(phonenumber) == 10 and phonenumber != 'nan'):
                        phonenumber = None
                else:
                    phonenumber = None
                if "fullname" in head_list:
                    fullname = str(row["fullname"])
                    if not (len(fullname) > 0 and fullname != 'nan'):
                        fullname = None
                else:
                    fullname = None
                try:
                    if phonenumber:
                        userdata = profiles_models.Profile.objects.filter(user_group=groupObj, institute=institute_room.institute).filter(user__phonenumber__icontains=phonenumber).last()
                        checkuser = profiles_models.Profile.objects.filter(user__phonenumber__icontains=phonenumber).last()
                        if userdata:
                            userroom_obj, _ = models.UserClassRoom.objects.get_or_create(user=userdata.user)
                            userroom_obj.institute_rooms.add(institute_room)
                            userroom_obj.save()
                            batches_obj = models.Batch.objects.filter(institute_room=institute_room, is_active=True)
                            for batch in batches_obj:
                                if len(batch.students.all()) < 250:
                                    try:
                                        learner_batch_obj = models.LearnerBatches.objects.get(user=userdata.user, batch=batch)
                                    except:
                                        learner_batch_obj = None
                                    
                                    if not learner_batch_obj:
                                        learner_batch_obj = models.LearnerBatches.objects.create(user=userdata.user, batch=batch)
                                    batch.students.add(userdata.user)
                                    batch.save()
                            student_rooms.append(userroom_obj)
                        elif not userdata and checkuser:
                            text = "Invalid User: " + phonenumber
                            models.StudentInstituteChangeInvitation.objects.create(user=checkuser.user, inviting_institute_room=institute_room)
                            # errors.append(text)
                            pass
                        else:
                            isAvailable = False
                            check_usage = profiles_models.Profile.objects.filter(user__phonenumber=phonenumber).exists()
                            if check_usage:
                                isAvailable = False
                            else:
                                isAvailable = True
                            if not isAvailable:
                                text = "Contact number " + phonenumber +  " already in use by another user"
                                errors.append(text)
                            else:
                                user_obj = auth_models.User.objects.create(username=username, phonenumber=phonenumber, fullname=fullname)
                                user_obj.set_password(username)
                                user_obj.save()
                                user_dic = dict(name=fullname, username=username, phonenumber=phonenumber, password=username)
                                new_users.append(user_dic)
                                profile_obj = profiles_models.Profile.objects.get(user=user_obj)
                                profile_obj.user_group=groupObj
                                profile_obj.account_verified = True
                                profile_obj.contact_verified = True
                                profile_obj.institute = institute_room.institute
                                profile_obj.save()
                                userroom_obj, _ = models.UserClassRoom.objects.get_or_create(user=user_obj)
                                userroom_obj.institute_rooms.add(institute_room)
                                userroom_obj.save()
                                batches_obj = models.Batch.objects.filter(institute_room=institute_room, is_active=True)
                                for batch in batches_obj:
                                    if len(batch.students.all()) < 250:
                                        try:
                                            learner_batch_obj = models.LearnerBatches.objects.get(user=user_obj, batch=batch)
                                        except:
                                            learner_batch_obj = None
                                        
                                        if not learner_batch_obj:
                                            learner_batch_obj = models.LearnerBatches.objects.create(user=user_obj, batch=batch)
                                        batch.students.add(user_obj)
                                        batch.save()
                                student_rooms.append(userroom_obj)
                    else:
                        if not fullname:
                            text = "Please enter fullname"
                            errors.append(text)
                        else:
                            user_obj = auth_models.User.objects.create(username=username, fullname=fullname)
                            user_obj.set_password(username)
                            user_obj.save()
                            user_dic = dict(name=fullname, username=username, phonenumber='', password=username)
                            new_users.append(user_dic)
                            profile_obj = profiles_models.Profile.objects.get(user=user_obj)
                            profile_obj.user_group=groupObj
                            profile_obj.account_verified = True
                            profile_obj.contact_verified = True
                            profile_obj.institute = institute_room.institute
                            profile_obj.save()
                            userroom_obj, _ = models.UserClassRoom.objects.get_or_create(user=user_obj)
                            userroom_obj.institute_rooms.add(institute_room)
                            userroom_obj.save()
                            batches_obj = models.Batch.objects.filter(institute_room=institute_room, is_active=True)
                            for batch in batches_obj:
                                if len(batch.students.all()) < 250:
                                    try:
                                        learner_batch_obj = models.LearnerBatches.objects.get(user=user_obj, batch=batch)
                                    except:
                                        learner_batch_obj = None
                                    if not learner_batch_obj:
                                        learner_batch_obj = models.LearnerBatches.objects.create(user=user_obj, batch=batch)
                                    batch.students.add(user_obj)
                                    batch.save()
                            student_rooms.append(userroom_obj)
                except:
                    pass
        except:
            return Response({"message": "Some error occured"}, status=status.HTTP_400_BAD_REQUEST)
        roomdata = serializers.ViewUserClassRoomSerializer(student_rooms, many=True).data
        return Response({'errors': errors, "message": "List succesfully updated ", "signups": new_users, "rooms": roomdata}, status=200)

class LearnerGoalPathCreateLearChaptersViewSet(UpdateAPIView):
    serializer_class = serializers.ViewLearnerExamGoalSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        create_new = request.data.get('new', None)
        goal_obj = models.LearnerExamGoals.objects.get(id=request.data.get('goal', None))
        if not goal_obj:
            return Response({"message": "Oops! Goal doesnot exist"}, status=status.HTTP_400_BAD_REQUEST)
        previous_path = models.LearnerExamGoalPath.objects.filter(goal=goal_obj).order_by('counter').last()
        if create_new or (not previous_path):
            path_obj = models.LearnerExamGoalPath.objects.create(
            goal=goal_obj)
            if previous_path:
                counter = previous_path.counter + 1
                path_obj.counter=counter
                path_obj.previous_path_id=previous_path.id
                path_obj.save()
                previous_path.next_path_id = path_obj.id
                # previous_path.frozen_date = path_obj.created_at
                # previous_path.freeze = True
                if previous_path.paper:
                    if not previous_path.paper.submitted:
                        return Response({"message": "Oops! Your paper for current path is not yet submitted"}, status=status.HTTP_400_BAD_REQUEST)
                previous_path.save()
            else:
                counter = 1
                path_obj.counter=counter
                path_obj.save()
        
            chapter_data = None
            exam_obj = course_models.Exam.objects.get(id=int(goal_obj.exam.id))
            if not exam_obj.is_active:
                learnerexamtmpobj = course_models.LearnerExams.objects.filter(user=user, exam=exam_obj)
                if learnerexamtmpobj:
                    learnerexamtmpobj = learnerexamtmpobj.first()
                    learnerexamtmpobj.is_active=False
                    learnerexamtmpobj.save()
                return Response({"message": "Oops! Exam has been deactivated by admin"}, status=status.HTTP_400_BAD_REQUEST)
            headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json'}
            
            #url = "http://52.66.240.183/fetchsubtopicsformakinganypath?learnerexamgoal={0}&userid={1}".format(goal_obj.id, goal_obj.user.id)
            url = "http://20.40.54.177/fetchsubtopicsformakinganypath?learnerexamgoal={0}&userid={1}".format(goal_obj.id, goal_obj.user.id)

            try:
                r = requests.get(url)
                chapter_data = r.json()
            except:
                chapter_data = None
                # print ("failed")

            for data in chapter_data['learn']:
                for chapter in data['chapters']:
                    if chapter == 0:
                        continue
                    chapter_obj = course_models.Chapter.objects.get(id=chapter['id'])
                    path_learn_chapter_obj, _ = models.GoalPathLearnChapterHistory.objects.get_or_create(path=path_obj, chapter=chapter_obj)
                    
                    # for i in range(0, len(chapter['hints'])):
                    #     hint_obj = models.GoalPathLearnChapterHintHistory.objects.get_or_create(learn_chapter=path_learn_chapter_obj, order=chapter['hints'][i]['order'], chapter_hint__id=chapter['hints'][i]['id'])
                
                    for hint in chapter['hints']:
                        chapter_hint_obj = course_models.ChapterHints.objects.get(id=int(hint['id']))
                        models.GoalPathLearnChapterHintHistory.objects.get_or_create(learn_chapter=path_learn_chapter_obj, order=hint['order'], chapter_hint=chapter_hint_obj)
                        
            if 'revise' in chapter_data:
                for data in chapter_data['revise']:
                    for chapter in data['chapters']:
                        if chapter == 0:
                            continue
                        chapter_obj = course_models.Chapter.objects.get(id=chapter['id'])
                        path_revise_chapter_obj, _ = models.GoalPathReviseChapterHistory.objects.get_or_create(path=path_obj, chapter=chapter_obj)
                    
                        for hint in chapter['hints']:
                            chapter_hint_obj = course_models.ChapterHints.objects.get(id=int(hint['id']))
                            models.GoalPathReviseChapterHintHistory.objects.get_or_create(revise_chapter=path_revise_chapter_obj, order=hint['order'], chapter_hint=chapter_hint_obj)
                    
        return Response(self.serializer_class(goal_obj).data, status=201)

class FetchGoalPathsViewSet(ListAPIView):
    permission_classes = [IsAuthenticated, ]
    serializer_class = serializers.ViewLearnerExamGoalPathSerializer

    def get_queryset(self):
        goal = self.request.query_params.get('goal')
        goal_paths = models.LearnerExamGoalPath.objects.filter(goal__id=goal).order_by('id')
        if goal_paths:
            return goal_paths
        else:
            return []

class FetchPathLearnChaptersViewSet(ListAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.ViewGoalPathLearnChapterHistorySerializer

    def get_queryset(self):
        path = self.request.query_params.get('path')
        path_learn_history = models.GoalPathLearnChapterHistory.objects.filter(path__id=path)
        if path_learn_history:
            return path_learn_history
        else:
            return []

class FetchPathLearnChapterHintViewSet(ListAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.ViewGoalPathLearnChapterHintHistorySerializer

    def get_queryset(self):
        learn_chapter = self.request.query_params.get('learn_chapter')
        path_learn_chapter_hint_history = models.GoalPathLearnChapterHintHistory.objects.filter(learn_chapter__id=learn_chapter)
        if path_learn_chapter_hint_history:
            return path_learn_chapter_hint_history
        else:
            return []

class FetchPathReviseChaptersViewSet(ListAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.ViewGoalPathReviseChapterHistorySerializer

    def get_queryset(self):
        path = self.request.query_params.get('path')
        path_learn_history = models.GoalPathReviseChapterHistory.objects.filter(path__id=path)
        if path_learn_history:
            return path_learn_history
        else:
            return []

class FetchPathReviseChapterHintViewSet(ListAPIView):
    permission_classes = [IsAuthenticated, ]
    # pagination_class = core_paginations.CustomPagination
    serializer_class = serializers.ViewGoalPathReviseChapterHintHistorySerializer

    def get_queryset(self):
        revise_chapter = self.request.query_params.get('revise_chapter')
        path_learn_chapter_hint_history = models.GoalPathReviseChapterHintHistory.objects.filter(revise_chapter__id=revise_chapter)
        if path_learn_chapter_hint_history:
            return path_learn_chapter_hint_history
        else:
            return []

class UpdatePathLearnChapterHintViewSet(UpdateAPIView):
    serializer_class = serializers.ViewGoalPathLearnChapterHintHistorySerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        learnhint = request.data.get('learnhint')
        check_type = request.data.get('check')
        currenttime = timezone.now()
        if not learnhint:
            raise ParseError("Please select hint")
        else:   
            learn_chapter_hint_obj = models.GoalPathLearnChapterHintHistory.objects.get(id=int(learnhint))
        if not learn_chapter_hint_obj:
            raise ParseError("Learn Chapter Topic with this id DoesNotExist")
        path_obj = models.LearnerExamGoalPath.objects.get(id=int(learn_chapter_hint_obj.learn_chapter.path.id))
        if path_obj.freeze:
            raise ParseError("You can't update your previous path!")
        try:
            learn_chapter_hint_obj.checked = check_type
            learn_chapter_hint_obj.last_check_date = currenttime
            learn_chapter_hint_obj.save()
            all_learn_chapter_hints = models.GoalPathLearnChapterHintHistory.objects.filter(learn_chapter=learn_chapter_hint_obj.learn_chapter)
            count_checked = 0
            for chapter_hint in all_learn_chapter_hints:
                if chapter_hint.checked:
                    count_checked += 1
            learn_chapter_obj = models.GoalPathLearnChapterHistory.objects.get(id=int(learn_chapter_hint_obj.learn_chapter.id))
            if count_checked == len(all_learn_chapter_hints):
                learn_chapter_obj.percentage = 100
                learn_chapter_obj.is_done = True
                learn_chapter_obj.save()
            else:
                learn_chapter_obj.percentage = (count_checked/ len(all_learn_chapter_hints))*100
                learn_chapter_obj.is_done = False
                learn_chapter_obj.save()
        except:
            return Response({"message": "some error occured"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(learn_chapter_hint_obj).data, status=201)

class UpdatePathReviseChapterHintViewSet(UpdateAPIView):
    serializer_class = serializers.ViewGoalPathReviseChapterHintHistorySerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        revisehint = request.data.get('revisehint')
        check_type = request.data.get('check')
        currenttime = timezone.now()
        if not revisehint:
            raise ParseError("Please select hint")
        else:   
            revise_chapter_hint_obj = models.GoalPathReviseChapterHintHistory.objects.get(id=int(revisehint))
        if not revise_chapter_hint_obj:
            raise ParseError("Revise Chapter Topic with this id DoesNotExist")
        path_obj = models.LearnerExamGoalPath.objects.get(id=int(revise_chapter_hint_obj.revise_chapter.path.id))
        if path_obj.freeze:
            raise ParseError("You can't update your previous path!")
        try:
            revise_chapter_hint_obj.checked = check_type
            revise_chapter_hint_obj.last_check_date = currenttime
            revise_chapter_hint_obj.save()
            all_learn_chapter_hints = models.GoalPathReviseChapterHintHistory.objects.filter(revise_chapter=revise_chapter_hint_obj.revise_chapter)
            
            count_checked = 0
            for chapter_hint in all_learn_chapter_hints:
                if chapter_hint.checked:
                    count_checked += 1
            revise_chapter_obj = models.GoalPathReviseChapterHistory.objects.get(id=int(revise_chapter_hint_obj.revise_chapter.id))
            if count_checked == len(all_learn_chapter_hints):
                revise_chapter_obj.percentage = 100
                revise_chapter_obj.is_done = True
                revise_chapter_obj.save()
            else:
                revise_chapter_obj.percentage = (count_checked/ len(all_learn_chapter_hints))*100
                revise_chapter_obj.is_done = False
                revise_chapter_obj.save()
        except:
            return Response({"message": "some error occured"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(revise_chapter_hint_obj).data, status=201)

class SetGoalAssessmentSkipped(APIView):

    def put(self, request, *args, **kwargs):
        data = request.data
        goal = data['goal']
        
        goal_obj = models.LearnerExamGoals.objects.get(id=goal)
        if goal_obj.assessment_done:
            raise ParseError("Assessment is already completed")
        if goal_obj.assessment_skipped:
            raise ParseError("Assessment is already skipped")
        goal_obj.assessment_skipped=True
        goal_obj.save()
        return Response({'status': 'done'}, status=status.HTTP_201_CREATED)

class PreGoalPaperAnswersHistoryView(ListAPIView, CreateAPIView):
    serializer_class = serializers.QuestionSerializer
    permission_classes = [IsAuthenticated,]

    def get_queryset(self):
        questions, question_data = content_utils.get_pregoal_assessment_answers_history(self.request.user, self.kwargs.get('assessmentpaper_id'))
        
        if not questions:
            # return blank queryset if questions not received
            return models.Question.objects.filter(id=None)
        return questions, question_data

    def list(self, request, *args, **kwargs):
        answer_paper_obj = models.GoalAssessmentExamAnswerPaper.objects.get(id=self.kwargs.get('assessmentpaper_id'))
        # answer_paper_obj = models.AnswerPaper.objects.filter(user=self.request.user ,assessment_paper=assessmentpaper_obj)
        
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            serializer = self.get_serializer(queryset[0], many=True)
            # answer_paper_obj = models.AnswerPaper.objects.filter(user=self.request.user ,assessment_paper=assessmentpaper_obj)
            if answer_paper_obj:
                answer_paper = answer_paper_obj.id
                return Response({
                    # 'assessmentpaperdetails':assessmentpaperdetails.data,
                    'answer_paper':answer_paper,
                    # 'attempt_order':1,
                    'question_data':queryset[1],
                    'questions': queryset[0]
                })
        return Response({'error': 'Error in Assessment Test Paper.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class MentorFAQViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticated, ]
    serializer_class = serializers.MentorFAQSerializer
    create_class = serializers.MentorFAQSerializer

    def get_queryset(self):
        user=self.request.user
        queries = models.MentorFAQ.objects.filter(user=user)
        if queries:
            return queries
        else:
            return []

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class FetchMentorFAQViewSet(ListAPIView,):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = serializers.MentorFAQSerializer

    def get_queryset(self):
        queries = models.MentorFAQ.objects.all().order_by('id')
        if queries:
            return queries
        else:
            return []

class EditMentorFAQViewSetViewSet(RetrieveUpdateAPIView):
    queryset = models.MentorFAQ.objects.all()
    serializer_class = serializers.MentorFAQSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        level_obj = models.MentorFAQ.objects.filter(pk=self.kwargs.get('pk'))
        if not level_obj:
            raise ParseError("FAQ with this id DoesNotExist")
        return level_obj
    
    def delete(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            hint_obj = models.MentorFAQ.objects.get(pk=int(id))
            hint_obj.delete()
        except:
            return Response({"message": "Please enter valid FAQ id"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "FAQ deleted successfully"}, status=201)

class FetchStudentInstituteChangeInvitationViewSet(ListAPIView):
    permission_classes = [IsAuthenticated, ]
    serializer_class = serializers.StudentInstituteChangeInvitationSerializer

    def get_queryset(self):
        room = self.request.query_params.get('room')
        requests = models.StudentInstituteChangeInvitation.objects.filter(inviting_institute_room__id=room).order_by('id')
        if requests:
            return requests
        else:
            return []

class FetchStudentIncomingInstituteChangeRequestViewSet(ListAPIView):
    permission_classes = [IsAuthenticated, ]
    serializer_class = serializers.StudentInstituteChangeInvitationSerializer

    def get_queryset(self):
        requests = models.StudentInstituteChangeInvitation.objects.filter(user=self.request.user)
        if requests:
            return requests
        else:
            return []

class ApproveInstituteRoomRequestView(UpdateAPIView):
    queryset = models.LearnerBatches.objects.all()
    serializer_class = serializers.LearnerBatchSerializer
    permission_classes = (IsAuthenticated,)
    
    def put(self, request, *args, **kwargs):
        try:
            profileObj = profiles_models.Profile.objects.get(user=request.user)
            request_obj = models.StudentInstituteChangeInvitation.objects.filter(user=request.user)
            for invitation in request_obj:
                institute_obj = profiles_models.Institute.objects.get(id=invitation.inviting_institute_room.institute.id)
                profileObj.institute = institute_obj
                profileObj.save()
                institute_room = models.InstituteClassRoom.objects.get(id=invitation.inviting_institute_room.id)
                userroom_obj, _ = models.UserClassRoom.objects.get_or_create(user=request.user)
                userroom_obj.institute_rooms.add(institute_room)
                userroom_obj.save()
                batches_obj = models.Batch.objects.filter(institute_room=invitation.inviting_institute_room, is_active=True)
                for batch in batches_obj:
                    if len(batch.students.all()) < 250:
                        try:
                            learner_batch_obj = models.LearnerBatches.objects.get(user=request.user, batch=batch)
                        except:
                            learner_batch_obj = None
                        if not learner_batch_obj:
                            learner_batch_obj = models.LearnerBatches.objects.create(user=request.user, batch=batch)
                        batch.students.add(request.user)
                        batch.save()
            models.StudentInstituteChangeInvitation.objects.filter(user=request.user).delete()
        except:
            return Response({"message": "error in processing"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "user change request processed successfully"}, status=201)

class CheckForFirstPathCreationViewSet(UpdateAPIView):
    # serializer_class = serializers.ViewLearnerExamGoalSerializer

    def put(self, request, *args, **kwargs):
        goal_obj = models.LearnerExamGoals.objects.get(id=request.data.get('goal', None))
        if not goal_obj:
            return Response({"message": "Oops! Goal doesnot exist"}, status=status.HTTP_400_BAD_REQUEST)
        previous_path = models.LearnerExamGoalPath.objects.filter(goal=goal_obj).order_by('counter').last()
        if not previous_path:
            
            check_data = None
            headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json'}
        
           # url = "http://52.66.240.183/checkformakingfirstpath?learnerexamgoal={0}".format(goal_obj.id)
            url = "http://20.40.54.177/checkformakingfirstpath?learnerexamgoal={0}".format(goal_obj.id)

            try:
                r = requests.get(url)
                check_data = r.json()
            except:
                check_data = None
                # print ("failed")
            if check_data and check_data['status'] == 0:
                models.LearnerExamGoals.objects.filter(id=goal_obj.id).delete()

        return Response(check_data, status=201)

class CheckForSubsequentPathCreationViewSet(UpdateAPIView):
    # serializer_class = serializers.ViewLearnerExamGoalSerializer

    def put(self, request, *args, **kwargs):
        goal_obj = models.LearnerExamGoals.objects.get(id=request.data.get('goal', None))
        if not goal_obj:
            return Response({"message": "Oops! Goal doesnot exist"}, status=status.HTTP_400_BAD_REQUEST)
        previous_path = models.LearnerExamGoalPath.objects.filter(goal=goal_obj).order_by('counter').last()
        check_data = None
        currenttime = timezone.now()
        if previous_path:
            previous_path.frozen_date = currenttime
            previous_path.freeze = True
            previous_path.save()
            
            headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json'}

            #url = "http://52.66.240.183/checkformakinganypathexceptfirst?learnerexamgoal={0}".format(goal_obj.id)
            url = "http://20.40.54.177/checkformakinganypathexceptfirst?learnerexamgoal={0}".format(goal_obj.id)

            try:
                r = requests.get(url)
                check_data = r.json()
            except:
                check_data = None

        return Response(check_data, status=201)

class UserQueryReplyForUserView(UpdateAPIView):
    serializer_class = serializers.LearnerQuerySerializer

    def put(self, request, *args, **kwargs):
        try:
            reply = request.data.get('reply')
            query_id = request.data.get('query')
            if not query_id:
                raise ParseError("Please enter query id")
            else:   
                learner_query_obj = models.LearnerQuery.objects.get(id=int(query_id))
            if not learner_query_obj:
                raise ParseError("Query with this id DoesNotExist")
            learner_query_obj.reply = reply
            learner_query_obj.is_replied = True
            learner_query_obj.save()
            notification_type = NotificationType.objects.get(name="admin")
            if learner_query_obj.user:
                if learner_query_obj.exam:
                    notification_text  = "Notification regarding your query for exam: " + learner_query_obj.exam.title
                    Notifications.objects.create(user=learner_query_obj.user, exam=learner_query_obj.exam, notification=reply, subject=notification_text, type=notification_type)
                else:
                    notification_text  = "Notification regarding your query"
                    Notifications.objects.create(user=learner_query_obj.user, notification=reply, subject=notification_text, type=notification_type)
        except:
            return Response({"message": "error in updating remarks"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(learner_query_obj).data, status=201)

class UserReportedQuestionReplyForUserView(UpdateAPIView):
    serializer_class = serializers.ReportedQuestionSerializer

    def put(self, request, *args, **kwargs):
        try:
            reply = request.data.get('reply')
            query_id = request.data.get('id')
            if not query_id:
                raise ParseError("Please enter query id")
            else:   
                learner_query_obj = models.ReportedErrorneousQuestion.objects.get(id=int(query_id))
            if not learner_query_obj:
                raise ParseError("Query with this id DoesNotExist")
            learner_query_obj.reply = reply
            learner_query_obj.is_replied = True
            learner_query_obj.save()
            notification_type = NotificationType.objects.get(name="admin")
            notification_text  = "Notification regarding your reported question for exam: " + learner_query_obj.exam.title
            Notifications.objects.create(user=learner_query_obj.user, exam=learner_query_obj.exam, question=learner_query_obj.question, notification=reply, subject=notification_text, type=notification_type)
        except:
            return Response({"message": "error in updating remarks"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(learner_query_obj).data, status=201)

class LearnerGoalPercentageViewSet(UpdateAPIView):
    serializer_class = serializers.ViewLearnerExamGoalSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        goal_obj = models.LearnerExamGoals.objects.get(id=request.data.get('goal', None))
        if not goal_obj:
            return Response({"message": "Oops! Goal doesnot exist"}, status=status.HTTP_400_BAD_REQUEST)
        
        chapter_data = None
        exam_obj = course_models.Exam.objects.get(id=int(goal_obj.exam.id))
        if not exam_obj.is_active:
            learnerexamtmpobj = course_models.LearnerExams.objects.filter(user=user, exam=exam_obj)
            if learnerexamtmpobj:
                learnerexamtmpobj = learnerexamtmpobj.first()
                learnerexamtmpobj.is_active=False
                learnerexamtmpobj.save()
            return Response({"message": "Oops! Exam has been deactivated by admin"}, status=status.HTTP_400_BAD_REQUEST)
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json'}

        #url = "http://52.66.240.183/learnrevisepercent?learnerexamgoal={0}".format(goal_obj.id)
        url = "http://20.40.54.177/learnrevisepercent?learnerexamgoal={0}".format(goal_obj.id)

        try:
            r = requests.get(url)
            chapter_data = r.json()
        except:
            chapter_data = None
            # print ("failed")
        if chapter_data:
            goal_obj.learn_percentage = chapter_data['learn']
            goal_obj.revise_percentage = chapter_data['revise']
            goal_obj.save()

        return Response(self.serializer_class(goal_obj).data, status=201)

class ExamAllLearnerGoalsPercentageViewSet(UpdateAPIView):
    serializer_class = serializers.ViewLearnerExamGoalSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        exam_obj = course_models.Exam.objects.get(id=request.data.get('exam', None))
        if not exam_obj:
            return Response({"message": "Oops! Exam doesnot exist"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not exam_obj.is_active:
            learnerexamtmpobj = course_models.LearnerExams.objects.filter(user=user, exam=exam_obj)
            if learnerexamtmpobj:
                learnerexamtmpobj = learnerexamtmpobj.first()
                learnerexamtmpobj.is_active=False
                learnerexamtmpobj.save()
            return Response({"message": "Oops! Exam has been deactivated by admin"}, status=status.HTTP_400_BAD_REQUEST)
        goals = models.LearnerExamGoals.objects.filter(exam=exam_obj, user=user)
        
        for goal in goals:
            chapter_data = None
            
            headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json'}

            #url = "http://52.66.240.183/learnrevisepercent?learnerexamgoal={0}".format(goal.id)
            url = "http://20.40.54.177/learnrevisepercent?learnerexamgoal={0}".format(goal.id)

            try:
                r = requests.get(url)
                chapter_data = r.json()
            except:
                chapter_data = None
                
            if chapter_data:
                goal.learn_percentage = chapter_data['learn']
                goal.revise_percentage = chapter_data['revise']
                goal.save()

        return Response({"message": "Done"}, status=201)

class LearnerGoalPathPercentageViewSet(UpdateAPIView):
    serializer_class = serializers.ViewLearnerExamGoalPathSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        path_obj = models.LearnerExamGoalPath.objects.get(id=request.data.get('path', None))
        if not path_obj:
            return Response({"message": "Oops! Path doesnot exist"}, status=status.HTTP_400_BAD_REQUEST)
        
        chapter_data = None
        exam_obj = course_models.Exam.objects.get(id=int(path_obj.goal.exam.id))
        if not exam_obj.is_active:
            learnerexamtmpobj = course_models.LearnerExams.objects.filter(user=user, exam=exam_obj)
            if learnerexamtmpobj:
                learnerexamtmpobj = learnerexamtmpobj.first()
                learnerexamtmpobj.is_active=False
                learnerexamtmpobj.save()
            return Response({"message": "Oops! Exam has been deactivated by admin"}, status=status.HTTP_400_BAD_REQUEST)
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json'}

        #url = "http://52.66.240.183/learnrevisepercentforpath?pathid={0}".format(path_obj.id)
        url = "http://20.40.54.177/learnrevisepercentforpath?pathid={0}".format(path_obj.id)
        
        try:
            r = requests.get(url)
            chapter_data = r.json()
        except:
            chapter_data = None
            # print ("failed")
        if chapter_data:
            path_obj.learn_percentage = chapter_data['learn']
            path_obj.revise_percentage = chapter_data['revise']
            path_obj.save()

        return Response(self.serializer_class(path_obj).data, status=201)

class LearnerGoalPathUpdateWithAssessmentViewSet(UpdateAPIView):
    serializer_class = serializers.LearnerPaperSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        goal_obj = models.LearnerExamGoals.objects.get(id=request.data.get('goal', None))
        if not goal_obj:
            return Response({"message": "Oops! Goal doesnot exist"}, status=status.HTTP_400_BAD_REQUEST)
        current_path_obj = models.LearnerExamGoalPath.objects.filter(goal=goal_obj).order_by('counter').last()
        current_path_obj.done_with_assessment = True
        current_path_obj.freeze = False
        current_path_obj.save()
        
        path_learn_chapters = models.GoalPathLearnChapterHistory.objects.select_related(
                        "path").filter(path=current_path_obj).values_list("id", flat=True)
        selected_chapter_hints = models.GoalPathLearnChapterHintHistory.objects.filter(learn_chapter__in=path_learn_chapters, checked=True).values_list("learn_chapter", flat=True)
        
        if len(selected_chapter_hints) == 0:
            all_path_learn_chapters = models.GoalPathLearnChapterHistory.objects.select_related(
                        "path").filter(path=current_path_obj).values_list("chapter", flat=True)
            chapters = all_path_learn_chapters
            chapters_obj = course_models.Chapter.objects.filter(id__in=all_path_learn_chapters)
        else:
            filtered_learn_chapters = models.GoalPathLearnChapterHistory.objects.select_related(
                        "path").filter(id__in=selected_chapter_hints).values_list("chapter", flat=True)
            chapters = filtered_learn_chapters
            chapters_obj = course_models.Chapter.objects.filter(id__in=filtered_learn_chapters)
        subjectIds = []
        subjectIds.extend(chapters_obj.values_list("subject", flat=True))
     
        exam_obj = course_models.Exam.objects.get(id=int(goal_obj.exam.id))
        if not exam_obj.is_active:
            learnerexamtmpobj = course_models.LearnerExams.objects.filter(user=user, exam=exam_obj)
            if learnerexamtmpobj:
                learnerexamtmpobj = learnerexamtmpobj.first()
                learnerexamtmpobj.is_active=False
                learnerexamtmpobj.save()
            return Response({"message": "Oops! Exam has been deactivated by admin"}, status=status.HTTP_400_BAD_REQUEST)
        
        question_types = request.data.get('quesTypes', None)
        difficulty = request.data.get('difficulty', 1)
        
        if len(question_types) == 0:
            return Response({"message": "Please select at least one question type"}, status=status.HTTP_400_BAD_REQUEST)

        paper_type = ExamType.PAPER
        show_time = True
        
        # topicIds.extend(chapters_obj.values_list("topics", flat=True).all())
        
        total_ques = int(len(subjectIds)*10)

        avg_time_obj = course_models.ExamAverageTimePerQuestion.objects.filter(exam=exam_obj)
        
        total_time = total_ques * avg_time_obj.last().time
        
        learner_papercount_obj, _ = models.LearnerTotalActualPapers.objects.get_or_create(user=user)
        learner_papercount_obj.count += 1
        learner_papercount_obj.save()
        count = learner_papercount_obj.count
            
        learner_paper_obj = models.LearnerPapers.objects.create(
            user=user, paper_type=paper_type, paper_count=count, show_time=show_time, is_linked_goal=True, goal_id=goal_obj.id, path_id=current_path_obj.id)
        learner_paper_obj.subjects.add(*subjectIds)
        learner_paper_obj.save()
        current_path_obj.paper = learner_paper_obj
        current_path_obj.save()

        learner_exam,_ = course_models.LearnerExams.objects.get_or_create(user=user, exam=exam_obj)
        learner_paper_obj.learner_exam = learner_exam
        learner_paper_obj.save()

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
        
        learner_history_obj, _ = models.LearnerHistory.objects.get_or_create(user=user)
        eng_obj = models.QuestionLanguage.objects.get(text=QuestionLanguage.ENGLISH)

        try:
            questions = QuestionDistribution.get_equally_distributed_subjectwise_questions(
                learner_paper_obj.id, 'learnerpaper', subjectIds, selectedRange, chapters,  total_ques, eng_obj, question_types
            )
            logger.info(f"Questions count {len(questions)}")
            
            if len(questions) == 0:
                learner_papercount_obj.count -= 1
                learner_papercount_obj.save()
                learner_paper_obj.delete()
                return Response({"message": "No questions found"}, status=status.HTTP_400_BAD_REQUEST)
            learner_paper_obj.total_time = total_time
            learner_paper_obj.questions.add(*questions)
            learner_paper_obj.save()
            learner_history_obj.papers.add(learner_paper_obj)
            learner_history_obj.total_questions += len(questions)
            learner_history_obj.questions.add(*questions)
            learner_history_obj.save()
            total_marks = 0
          
            instruction_ques = "Total Questions: " + str(learner_paper_obj.questions.count())
            paper_instruction_obj3 = models.PaperInstructions.objects.create(paper=learner_paper_obj,instruction=instruction_ques)
            if learner_paper_obj.paper_type == 'paper':
                instruction_time = "Total Time (in Min): " + str(total_time)
                paper_instruction_obj = models.PaperInstructions.objects.create(paper=learner_paper_obj,instruction=instruction_time)
            if exam_obj:
                learnerexam_history_obj, _ = models.LearnerExamHistory.objects.get_or_create(user=user, exam=exam_obj)
                
                learnerexam_paper_history_obj,_ = models.LearnerExamPaperHistory.objects.get_or_create(user=user, exam=exam_obj)
               
                learnerexam_history_obj.total_questions += len(questions)
                learnerexam_history_obj.save()
                
                learnerexam_history_obj.questions.add(*questions)
                learnerexam_history_obj.papers.add(learner_paper_obj)
                learnerexam_history_obj.save()
                learnerexam_paper_history_obj.questions.add(*questions)
                learnerexam_paper_history_obj.papers.add(learner_paper_obj)
                learnerexam_paper_history_obj.save()

                paper_instruction_obj2 = models.PaperInstructions.objects.create(paper=learner_paper_obj)

                distribution_based_on_type = QuestionDistribution.distribute_based_on_type_of_questions(
                    learner_paper_obj.questions.all()
                )
                
                total_marks_grouped_by_exam_type_of_question = course_models.QuestionType.objects.filter(
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
                current_path_obj.freeze = True
                current_path_obj.save()
        except Exception as e:
            logger.info(f"Exception {e}")
            
            learner_papercount_obj.count -= 1
            learner_papercount_obj.save()
            learner_paper_obj.delete()
            return Response({"message": "error in fetching questions"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(learner_paper_obj).data, status=201)

class DeactivateAllBatchesView(UpdateAPIView):
    serializer_class = serializers.ViewBatchSerializer

    def put(self, request, *args, **kwargs):
        batch_obj = models.Batch.objects.filter(teacher=self.request.user, is_active=True)
        try:
            for batch in batch_obj:
                batch.is_active = False
                batch.save()
        except:
            return Response({"message": "error in deactivating all batches"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "batches deactivated successfully"}, status=201)

class ActivateBatchView(RetrieveUpdateAPIView):
    queryset = models.Batch.objects.all()
    serializer_class = serializers.ViewBatchSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        
        batch_obj = models.Batch.objects.select_related("teacher", "name", "teacher__profile", "batch_code", "students"
        ).filter(pk=self.kwargs.get('pk')).order_by('id')
        if not batch_obj:
            raise ParseError("Batch data with this id DoesNotExist")
        return batch_obj

    def put(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            batch_obj = models.Batch.objects.get(pk=int(id))
        except:
            return Response({"message": "Please enter valid id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            batch_obj.is_active = True
            batch_obj.save()
        except:
            return Response({"message": "error in activating the batch"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "batch activated successfully"}, status=201)

class SaveMentorBookMarkView(UpdateAPIView):
    serializer_class = serializers.MentorBookmarksSerializer

    def put(self, request, *args, **kwargs):
        user = self.request.user
        try:
            questionid = request.data.get('question')
            ques_obj = models.Question.objects.get(id=int(questionid))
        except:
            ques_obj = None
            # raise ParseError("Data with this id DoesNotExist")
        if not ques_obj:
            return Response({"message": "question with this id does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            examid = request.data.get('exam')
            exam_obj = course_models.Exam.objects.get(id=int(examid))
        except:
            exam_obj = None
            # raise ParseError("Data with this id DoesNotExist")
        if not exam_obj:
            return Response({"message": "error in fetching exam details"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            chapterIds = []
            tmppaperid = request.data.get('tmppaperid')
            tmppaper_obj = models.TemporaryMentorActualPaperReplaceQuestions.objects.get(id=int(tmppaperid))
            chapters = tmppaper_obj.chapters.all()
            chapterIds = [chapter.id for chapter in chapters]
            masterTagObj = models.ChapterMasterFTag.objects.filter(chapter__in=chapterIds, questions=ques_obj).last()
            chapter_obj = course_models.Chapter.objects.select_related("subject").filter(id=masterTagObj.chapter.id).last()
            # subjectid = request.data.get('subject')
            # subject_obj = course_models.Subject.objects.get(id=int(subjectid))
            # chapter
            # tagIds = []
            # ftags = ques_obj.linked_topics.all()
            # tagIds = [tag.id for tag in ftags]
            # chapter_obj = course_models.Chapter.objects.filter(subject=subject_obj, topics__in=tagIds).last()
            mentor_exam_obj = course_models.MentorExams.objects.get(user=user, exam=exam_obj)
            mentor_exam_obj.is_active = True
            mentor_exam_obj.save()
            exam_subject_obj, _ = models.MentorExamSubjects.objects.get_or_create(mentor_exam=mentor_exam_obj, subject=chapter_obj.subject)
            exam_chapter_obj, _ = models.MentorExamChapters.objects.get_or_create(mentor_exam=mentor_exam_obj, chapter=chapter_obj, subject=chapter_obj.subject)
            try: 
                find_bookmark_obj = models.MentorBookmarks.objects.get(mentor_exam=mentor_exam_obj, subject=chapter_obj.subject, question=ques_obj, chapter=chapter_obj)
            except:
                find_bookmark_obj = None
            if find_bookmark_obj:
                return Response({"message": "question already bookmarked in this exam"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                exam_subject_obj.total_bookmarks += 1
                exam_subject_obj.save()
                exam_chapter_obj.total_bookmarks += 1
                exam_chapter_obj.save()
                bookmark_obj = models.MentorBookmarks.objects.create(mentor_exam=mentor_exam_obj, subject=chapter_obj.subject, question=ques_obj, chapter=chapter_obj)
               
        return Response(self.serializer_class(bookmark_obj).data, status=201)

class DeleteMentorBookmarkViewSet(RetrieveUpdateAPIView):
    queryset = models.MentorBookmarks.objects.all()
    serializer_class = serializers.MentorBookmarksSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        bookmark_obj = models.MentorBookmarks.objects.filter(pk=self.kwargs.get('pk'))
        if not bookmark_obj:
            raise ParseError("Bookmark with this id DoesNotExist")
        return bookmark_obj
    
    def delete(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            bookmark_obj = models.MentorBookmarks.objects.get(pk=int(id))
            mentor_exam_obj = course_models.MentorExams.objects.get(id=int(bookmark_obj.mentor_exam.id))
            chapter_obj = course_models.Chapter.objects.get(id=int(bookmark_obj.chapter.id))
            subject_obj = course_models.Subject.objects.get(id=int(bookmark_obj.subject.id))
            try:
                lec_obj = models.MentorExamChapters.objects.get(mentor_exam=mentor_exam_obj, chapter=chapter_obj, subject=subject_obj)
            except:
                lec_obj = None
            if lec_obj:
                lec_obj.total_bookmarks -= 1
                lec_obj.save()
            try:
                les_obj = models.MentorExamSubjects.objects.get(mentor_exam=mentor_exam_obj, subject=subject_obj)
            except:
                les_obj = None
            if les_obj:
                les_obj.total_bookmarks -= 1
                les_obj.save()
            bookmark_obj.delete()
        except:
            return Response({"message": "Please enter valid Bookmark id"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Bookmark deleted successfully"}, status=201)

class FetchMentorBookmarksViewSetViewSet(ListAPIView):
    queryset = models.MentorBookmarks.objects.all()
    serializer_class = serializers.MentorBookmarksSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        examid = self.request.query_params.get('exam')
        subjectid = self.request.query_params.get('subject')
        chapterid = self.request.query_params.get('chapter')
        if examid and subjectid and chapterid:
            # exam_obj = course_models.Exam.objects.get(id=int(examid))
            mentor_exam_obj = course_models.MentorExams.objects.get(id=int(examid))
            subject_obj = course_models.Subject.objects.get(id=int(subjectid))
            chapter_obj = course_models.Chapter.objects.get(id=int(chapterid))
            bookmark_obj = models.MentorBookmarks.objects.filter(
                mentor_exam=mentor_exam_obj, subject=subject_obj, chapter=chapter_obj)
            if bookmark_obj:
                return bookmark_obj
            else:
                return []

class MentorExamChaptersViewSet(ListAPIView):
    queryset = models.MentorExamChapters.objects.all()
    serializer_class = serializers.MentorExamChapterSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        subject_id = self.request.query_params.get('subject')
        mentor_exam_id = self.request.query_params.get('mentorexam')
        if not mentor_exam_id:
            exam_id = self.request.query_params.get('exam')
            exam_obj = course_models.Exam.objects.get(id=int(exam_id))
            mentor_exam_obj = course_models.MentorExams.objects.get(user=user, exam=exam_obj)
        else:   
            mentor_exam_obj = course_models.MentorExams.objects.get(id=int(mentor_exam_id))
        subject_obj = course_models.Subject.objects.get(id=int(subject_id))
        if not mentor_exam_obj:
            raise ParseError("Mentor Exam with this id DoesNotExist")
        chapter_obj = models.MentorExamChapters.objects.filter(
            mentor_exam=mentor_exam_obj, subject=subject_obj)
        if chapter_obj:
            return chapter_obj
        else:
            return []

class MentorExamSubjectsViewSet(ListAPIView):
    queryset = models.MentorExamSubjects.objects.all()
    serializer_class = serializers.MentorExamSubjectSerializer
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
        mentor_exam_id = self.request.query_params.get('mentorexam')
        if not mentor_exam_id:
            exam_id = self.request.query_params.get('exam')
            exam_obj = course_models.Exam.objects.get(id=int(exam_id))
            mentor_exam_obj = course_models.MentorExams.objects.get(user=user, exam=exam_obj)
        else:   
            mentor_exam_obj = course_models.MentorExams.objects.get(id=int(mentor_exam_id))
        if not mentor_exam_obj:
            raise ParseError("Mentor Exam with this id DoesNotExist")
        subject_obj = models.MentorExamSubjects.objects.filter(
            mentor_exam=mentor_exam_obj)
        if subject_obj:
            return subject_obj
        else:
            return []

class FetchTotalClassRoomsInInstituteViewSet(ListAPIView,):
    permission_classes = [IsAuthenticatedOrReadOnly, ]

    def get_queryset(self):
        institute_id = self.request.query_params.get('institute', None)
        
        if not institute_id:
            raise ParseError("Please enter institute Id")
        
        institute_id = int(institute_id)
        
        room_count = models.InstituteClassRoom.objects.filter(institute__id=institute_id).count()
        return room_count

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        try:
            return Response({
                'totalrooms':queryset,
            })
        except:
            return Response({'error': 'Error.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class UpdateInstituteRoomTeacherView(UpdateAPIView):
    serializer_class = serializers.ViewBatchSerializer

    def put(self, request, *args, **kwargs):
        try:
            username = request.data.get('user')
            user_obj = auth_models.User.objects.get(username=username)
        except:
            user_obj = None
        if not user_obj:
            return Response({"message": "user with this username does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        room_id = self.request.data.get('room')
        if not room_id:
            raise ParseError("Please enter institute Id")
        room_obj = models.InstituteClassRoom.objects.get(id=int(room_id))
        room_obj.room_teacher = user_obj
        room_obj.save()
        return Response({"message": "room teacher updated successfully"}, status=201)

class DeactivateGoal(APIView):

    def put(self, request, *args, **kwargs):
        data = request.data
        goal_id = data['goal']
        goal_obj = models.LearnerExamGoals.objects.get(id=int(goal_id))
        if not goal_obj:
            return Response({"message": "Goal does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        goal_obj.is_active = False
        goal_obj.save()
        return Response({'status': 'done'}, status=status.HTTP_201_CREATED)

class FetchPathByIdPaperViewSet(RetrieveAPIView):
    queryset = models.LearnerExamGoalPath.objects.all()
    serializer_class = serializers.ViewLearnerExamGoalPathSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        path = models.LearnerExamGoalPath.objects.filter(pk=self.kwargs.get('pk'))
        if not path:
            raise ParseError("Path with this id DoesNotExist")
        return path

def create_username(username):
    check_count = 1
    while check_username(username):
        if check_count >= 2:
            username = username + str(check_count)
        if len(username) < 6:
            username = username + \
            "".join(map(str, random.sample(range(1, 10), 6-len(username))))
        check_count += 1
    return username

def check_username(username):
    try:
        auth_models.User.objects.get(username=username)
    except ObjectDoesNotExist:
        return False
    return True
