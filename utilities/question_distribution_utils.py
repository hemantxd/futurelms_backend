


from typing import List, Optional

from constants import DifficultyRange
from content.models import ChapterMasterFTag, Question, QuestionLanguage, TemporaryPaperSubjectQuestionDistribution
from courses.models import Chapter
import logging
logger = logging.getLogger(__name__)
import copy

class QuestionDistribution:


    def __init__(self) -> None:
        pass

    
    @staticmethod
    def do_equal_distribution_for_ids(total_questions: int, ids: List[int]) -> List[int]:
        """
        Evaluates the questions required for each subject/chapter. 

        Args:
            total_questions (int): [Total questions to distribute among]
            ids (List[int]): [subject/chapter ids]

        Returns:
            List[int]: [Denotes the questions required corresponding to each subject]
        """
        total_ids = len(ids)
        id_wise_question_count = [total_questions//total_ids]*total_ids
        remaining = total_questions % total_ids
        while remaining > 0:
            id_wise_question_count[remaining] += 1
            remaining -=1 
        return id_wise_question_count
    
    @staticmethod
    def get_questions_for_subject(paperid, papertype,
        subject_id: int, chapter_ids: List[int], 
        language: QuestionLanguage = None, difficulty_range: List[int] = None, question_types: List[str] = None,
        count: Optional[int] = None
    ):
        """
        Returns the total questions required for the given subject

        Args:
            count (int): [Total questions required for given subject]
            subject_id (int): [description]
            chapter_ids (List[int]): [description]
            language (QuestionLanguage): [description]
            difficulty_range (List[int]): [description]
            question_types (List[str]): [description]
        """
        assert subject_id, "subject id can not be null" 
        assert chapter_ids, "chapter ids can not be null"
        query_params = {}
        if difficulty_range:
            query_params["difficulty__in"] = difficulty_range
        if language:
            query_params["languages"] = language
        if question_types is not None or len(question_types) != 0:
            query_params["type_of_question__in"] = question_types
        
        mastertag_objs = ChapterMasterFTag.objects.select_related("chapter").prefetch_related("questions").filter(
            chapter__in=chapter_ids, chapter__subject_id=subject_id)
        tempquesIds = mastertag_objs.values_list("questions", flat=True)
        # equally distribute questions based on chapters as well        
        _questions = Question.objects.filter(
            id__in=tempquesIds, is_active=True, **query_params).values_list("id", flat=True
            ).order_by("?").distinct()[:count]
        
        # make sure to exclude the new questions
        exclude_ids = []
        exclude_ids.extend(set(_questions))
        questions_so_far = len(set(_questions))
        logger.info(f"questions count for subject {subject_id} {questions_so_far}")
        
        # what if _questions.count() is lesser to required count ?
        count -= questions_so_far
        tmpCount = 5
        query_params.update({"difficulty__in": DifficultyRange.allRange})
        while count > 0 and tmpCount > 0:
            additional_questions = Question.objects.filter(
                id__in=tempquesIds, is_active=True, 
                **query_params).values_list("id", flat=True
                ).exclude(id__in=exclude_ids).order_by("?").distinct()[:count]
            new_questions = set(additional_questions)
            exclude_ids.extend(new_questions)
            count -= len(new_questions)
            tmpCount -= 1
        
        if papertype == 'learnerpaper':
            # [TemporaryPaperSubjectQuestionDistribution.objects.create(learner_paper_id=paperid, subject_id=subject_id, question_id=ques) for ques in exclude_ids]
            for ques in exclude_ids:
                TemporaryPaperSubjectQuestionDistribution.objects.create(learner_paper_id=paperid, subject_id=subject_id, question_id=ques)
        elif papertype == 'mentorpaper':
            for ques in exclude_ids:
                TemporaryPaperSubjectQuestionDistribution.objects.create(mentor_paper_id=paperid, subject_id=subject_id, question_id=ques)
        return exclude_ids

    @classmethod
    def get_equally_distributed_subjectwise_questions(
        cls, paperid, papertype, subject_ids: List[int], difficulty_range: List[int], chapter_ids: List[int], 
        total_questions: int, language=None, question_types: List[str] = None
        ):
        subject_ids = list(set(subject_ids))
        subjectwise_questions_required = cls.do_equal_distribution_for_ids(total_questions, subject_ids)
        logger.info(f"subjectwise quesstion distribution {subjectwise_questions_required}")
        question_ids = []
        for index, count in enumerate(subjectwise_questions_required, 0):
            subject_chapter_ids = Chapter.objects.filter(id__in=chapter_ids, subject__id=subject_ids[index])
            res = cls.get_questions_for_subject(paperid, papertype,
                    subject_ids[index], subject_chapter_ids, language, 
                    difficulty_range, question_types, count)
            question_ids.extend([obj for obj in res])
        logger.info (f"total questions are {len(question_ids)}")
        # questions = Question.objects.filter(id__in=question_ids)
        return question_ids

    @staticmethod
    def distribute_based_on_type_of_questions(questions: List[Question]) -> dict:
        """[summary]

        Args:
            questions (List[questions]): [description]

        Returns:
            dict: [description]
        """
        type_of_questions = {}

        for question in questions:
            question_type = question.type_of_question
            try:
                type_of_questions[question_type] += 1
            except KeyError:
                type_of_questions[question_type] = 1
                    
        return type_of_questions

    
    @staticmethod
    def get_questions_equally(
        subject_id: int, chapter_ids: List[int], 
        language: QuestionLanguage = None, difficulty_range: List[int] = None, question_types: List[str] = None,
        count: Optional[int] = None
    ):
        """
        Returns the total questions in random order required for the given subject and chapter list.
        Equally distributes the questions based on
            - subject
                - chapters

        Args:
            count (int): [Total questions required for given subject]
            subject_id (int): [description]
            chapter_ids (List[int]): [description]
            language (QuestionLanguage): [description]
            difficulty_range (List[int]): [description]
            question_types (List[str]): [description]
        """
        assert subject_id, "subject id can not be null" 
        assert chapter_ids, "chapter ids can not be null"
        query_params = {}
        if difficulty_range:
            query_params["difficulty__in"] = difficulty_range
        if language:
            query_params["languages"] = language
        if question_types is not None or len(question_types) != 0:
            query_params["type_of_question__in"] = question_types

        chapters = Chapter.objects.select_related("subject").prefetch_related("topics").filter(
            subject__id=subject_id, 
            id__in=chapter_ids
        )
        chapter_wise_distribution = QuestionDistribution.do_equal_distribution_for_ids(
            count, chapters.values_list("id", flat=True))
        exclude_ids = []
        for idx, chapter in enumerate(chapters):
            topic_ids = chapter.topics.values_list("id", flat=True)
            required_questions = chapter_wise_distribution[idx]
            # equally distribute questions based on chapters as well
            _questions = Question.objects.prefetch_related("linked_topics").filter(
                linked_topics__id__in=topic_ids, is_active=True, **query_params).values_list("id", flat=True
                ).exclude(id__in=exclude_ids).order_by("?").distinct()[:required_questions]
            
            questions_so_far = len(set(_questions))
            # make sure to exclude the new questions
            exclude_ids.extend(set(_questions))
            logger.info(f"questions count for subject {subject_id} and chapater {chapter.id} {questions_so_far}")
            
            required_questions -= questions_so_far
            while required_questions > 0 :
                # what if _questions.count() is lesser to required count ?
                # since order_by("?") may return duplicate record as well that's why
                # we have to look for questions till we meet our count
                query_params.update({"difficulty__in": DifficultyRange.allRange})
                additional_questions = Question.objects.filter(
                    linked_topics__id__in=topic_ids, is_active=True, **query_params).values_list("id", flat=True
                    ).exclude(id__in=exclude_ids).order_by("?").distinct()[:required_questions]
                logger.info(f"length of unique ids are {set(additional_questions)}")
                exclude_ids.extend(additional_questions)
                required_questions -= len(set(additional_questions))
        logger.info (f"exclude ids count for subject {subject_id} is {len(exclude_ids)}")
        return exclude_ids