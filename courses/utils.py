from . import models


def get_subject_chapters(exam_id):
    examobj = models.Exam.objects.prefetch_related("subjects").filter(id=exam_id)
    subject_data = []
    if not examobj:
        return subject_data
    examobj = examobj.first()
    subjects = examobj.subjects.filter(show=True).order_by("order").all()
    
    for subject in subjects:
        chapters = subject.chapters.values_list("id", "title").filter(show=True).order_by("order")        
        chapter_data = []
        for chapter in chapters:
            chapter_data.append({"id": chapter[0], "title": chapter[1], "subject": subject.id})
        user_dict = dict(id=subject.id, title = subject.title, chapters=chapter_data)
        subject_data.append(user_dict)
    
    return subject_data
