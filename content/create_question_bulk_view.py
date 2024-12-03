
import json
from . import models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from courses import models as course_models
from django.db import transaction

class BulkCreateQuestion(APIView):
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
                    'Review Rejected'
                ]

    def post(self, request, *args, **kwargs):

        data_items = request.data
        response = {
            "failed": [],
            "success": []
        }
        for  data in data_items:
            try:
                _response = create_question(data)
                response["success"].append({"key": data["id"], "status": "created", "db_id": _response.id})
            except Exception as e:
                response["failed"].append({"key": data["id"], "status": "Failed", "exception": str(e)})
        return Response(response, status=status.HTTP_201_CREATED)


def create_question(data: json):
    question_identifier = data['id']
    with transaction.atomic():
        identifier_obj = models.QuestionIdentifiers.objects.filter(identifier=question_identifier).exists()
        if identifier_obj:
            return 
        
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
        # print ("subtypeaaaa", val['Subtype'])
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
                    ques_obj.is_active = val['Marking']['Status'] in BulkCreateQuestion.trueStatus
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
                if 'hi' in val:
                    # print ("yesjahii", val['hi'])
                    
                    hindi_obj, _ = models.QuestionLanguage.objects.get_or_create(text='Hindi')
                    ques_obj.languages.add(hindi_obj)
                    ques_obj.save()

                    if 'hints' in val['hi']:
                        if len(val['hi']['hints']) > 0:
                            hindi_content = models.QuestionContent.objects.create(text=val['hi']['question_txt'], language=hindi_obj, hint=val['hi']['hints'][0]['body'])
                        else:
                            hindi_content = models.QuestionContent.objects.create(text=val['hi']['question_txt'], language=hindi_obj)
                    else:
                        hindi_content = models.QuestionContent.objects.create(text=val['hi']['question_txt'], language=hindi_obj)
                    contentIds.append(hindi_content.id)

                    if quesType == 'subjective':
                        solution_hindi = models.Solution.objects.create(questioncontent=hindi_content, text=val['hi']['answers'][0]['explanation'])
                    if quesType == 'mcq' or quesType == 'assertion':
                        for answer in val['hi']['answers']:
                            models.McqTestCase.objects.create(questioncontent=hindi_content, text=answer['body'], correct=answer['is_correct'])
                            if answer['is_correct']:
                                solution_hindi = models.Solution.objects.create(questioncontent=hindi_content, text=answer['explanation'])
                    if quesType == 'mcc':
                        solutionbody = None
                        count = 0
                        hindi_content_solution = models.Solution.objects.get(questioncontent=hindi_content)
                        for answer in val['hi']['answers']:
                            models.McqTestCase.objects.create(questioncontent=hindi_content, text=answer['body'], correct=answer['is_correct'])
                            if answer['is_correct']:
                                count += 1
                                if count > 1:
                                    solutionbody += answer['explanation']
                                    solution_hindi = hindi_content_solution
                                    solution_hindi.text = solutionbody
                                    solution_hindi.save()
                                elif count == 1:
                                    solutionbody = answer['explanation']
                                    solution_hindi_initial = models.Solution.objects.create(questioncontent=hindi_content)
                                    solution_hindi_initial.text = solutionbody
                                    solution_hindi_initial.save()
                    if quesType == 'boolean':
                        for answer in val['hi']['answers']:
                            if answer['explanation'] != '':
                                models.TrueFalseSolution.objects.create(questioncontent=hindi_content, option=answer['is_correct'])
                                solution_hindi = models.Solution.objects.create(questioncontent=hindi_content, text=answer['explanation'])
                    if quesType == 'fillup':
                        for answer in val['hi']['answers']:
                            if answer['is_correct']:
                                models.FillUpSolution.objects.create(questioncontent=hindi_content, text=answer['body'])
                                solution_hindi = models.Solution.objects.create(questioncontent=hindi_content, text=answer['explanation'])
                    if quesType == 'fillup_option':
                        for answer in val['hi']['answers']:
                            models.FillUpWithOption.objects.create(questioncontent=hindi_content, text=answer['body'], correct=answer['is_correct'])
                            if answer['is_correct']:
                                solution_hindi = models.Solution.objects.create(questioncontent=hindi_content, text=answer['explanation'])
                elif 'en' in val:
                    eng_obj, _ = models.QuestionLanguage.objects.get_or_create(text='English')
                    ques_obj.languages.add(eng_obj)
                    ques_obj.save()

                    if 'hints' in val['en']:
                        if len(val['en']['hints']) > 0:
                            eng_content = models.QuestionContent.objects.create(text=val['en']['question_txt'], language=eng_obj, hint=val['en']['hints'][0]['body'])
                        else:
                            eng_content = models.QuestionContent.objects.create(text=val['en']['question_txt'], language=eng_obj)
                    else:
                        eng_content = models.QuestionContent.objects.create(text=val['en']['question_txt'], language=eng_obj)
                    contentIds.append(eng_content.id)
                    if quesType == 'subjective':
                        solution_eng = models.Solution.objects.create(questioncontent=eng_content, text=val['en']['answers'][0]['explanation'])
                    if quesType == 'mcq' or quesType == 'assertion':
                        for answer in val['en']['answers']:
                            models.McqTestCase.objects.create(questioncontent=eng_content, text=answer['body'], correct=answer['is_correct'])
                            if answer['is_correct']:
                                solution_eng = models.Solution.objects.create(questioncontent=eng_content, text=answer['explanation'])
                    if quesType == 'mcc':
                        solutionbody = None
                        count = 0
                        for answer in val['en']['answers']:
                            models.McqTestCase.objects.create(questioncontent=eng_content, text=answer['body'], correct=answer['is_correct'])
                            if answer['is_correct']:
                                count += 1
                                if count > 1:
                                    solutionbody += answer['explanation']
                                    solution_eng = models.Solution.objects.get(questioncontent=eng_content)
                                    solution_eng.text = solutionbody
                                    solution_eng.save()
                                elif count == 1:
                                    solutionbody = answer['explanation']
                                    solution_eng_initial = models.Solution.objects.create(questioncontent=eng_content)
                                    solution_eng_initial.text = solutionbody
                                    solution_eng_initial.save()
                    if quesType == 'boolean':
                        for answer in val['en']['answers']:
                            if answer['explanation'] != '':
                                models.TrueFalseSolution.objects.create(questioncontent=eng_content, option=answer['is_correct'])
                                solution_eng = models.Solution.objects.create(questioncontent=eng_content, text=answer['explanation'])
                    if quesType == 'fillup':
                        for answer in val['en']['answers']:
                            if answer['is_correct']:
                                models.FillUpSolution.objects.create(questioncontent=eng_content, text=answer['body'])
                                solution_eng = models.Solution.objects.create(questioncontent=eng_content, text=answer['explanation'])
                    if quesType == 'fillup_option':
                        for answer in val['en']['answers']:
                            models.FillUpWithOption.objects.create(questioncontent=eng_content, text=answer['body'], correct=answer['is_correct'])
                            if answer['is_correct']:
                                solution_eng = models.Solution.objects.create(questioncontent=eng_content, text=answer['explanation'])
                allcontents = models.QuestionContent.objects.filter(id__in=contentIds)
                for content in allcontents:
                    ques_obj.contents.add(content)
                    ques_obj.save()
                    
        ques_obj.save()
        return ques_obj.id