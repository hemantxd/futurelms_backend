from django.urls import path
from .views import *


urlpatterns = [

    path('profile/',ProfileRetrieveAPIView.as_view(),name='profile'),
    path('SchoolBranchApiView',SchoolBranchApiView.as_view(),name='SchoolBranchApiView'),
    path('SeassonViewApi',SeassonViewApi.as_view(),name='SeassonViewApi'),
    path('CreateSchoolAndSeassonApi',CreateSchoolAndSeassonApi.as_view(),name='CreateSchoolAndSeassonApi'),
    path('CreateSeassonOnExistsBranchApi',CreateSeassonOnExistsBranchApi.as_view(),name='CreateSeassonOnExistsBranchApi'),
    path('SchoolClassApiView',SchoolClassApiView.as_view(),name='SchoolClassApiView'),
    path('FetchTotalStudentsCountInSchoolViewSet1',FetchTotalStudentsCountInSchoolViewSet1.as_view(),name='FetchTotalStudentsCountInSchoolViewSet1'),
    path('GetSeassonViewApi',GetSeassonViewApi.as_view(),name='GetSeassonViewApi'),

    #create and view section of the class
    path('vieworcreateclassroom', InstituteClassRoomViewSet.as_view(),name='vieworcreateclassroom'),
    path('DeLeteSectionView',DeLeteSectionView.as_view(),name='DeLeteSectionView'),
    path('InstituteClassRoomByIdViewSet/<pk>',InstituteClassRoomByIdViewSet.as_view(),name='InstituteClassRoomByIdViewSet'),

    #path('AddStudentToRoomView',AddStudentToRoomView.as_view(),name='AddStudentToRoomView'),
    path('FetchRoomBatchesViewSet',FetchRoomBatchesViewSet.as_view(),name='FetchRoomBatchesViewSet'),
    path('FetchClassSectionViewSet',FetchClassSectionViewSet.as_view(),name='FetchClassSectionViewSet'),
    path('EditBatchViewSet/<pk>/',EditBatchViewSet1.as_view(),name='EditBatchViewSet'),
    path('FetchStudentsInRoomViewSet',FetchStudentsInRoomViewSet.as_view(),name='FetchStudentsInRoomViewSet'),
    path('StudentRegisterApiView',StudentRegisterApiView.as_view(),name='StudentRegisterApiView'),

    path('DeactivateBatchView/<pk>/',DeactivateBatchView.as_view(),name='DeactivateBatchView'),
    path('ActivateBatchView/<pk>/',ActivateBatchView.as_view(),name='ActivateBatchView'),
    path('RemoveAndBlockUserFromBatchView',RemoveAndBlockUserFromBatchView.as_view(),name='RemoveAndBlockUserFromBatchView'),
    path('CheckIfBlockedViewSet',CheckIfBlockedViewSet.as_view(),name='CheckIfBlockedViewSet'),
    path('FetchBlockedUserInBatchViewSet',FetchBlockedUserInBatchViewSet.as_view(),name='FetchBlockedUserInBatchViewSet'),
    path('UnblockUserFromBatchViewSet',UnblockUserFromBatchViewSet.as_view(),name='UnblockUserFromBatchViewSet'),
    path('GetMentorListAPIView',GetMentorListAPIView.as_view(),name='GetMentorListAPIView'),
    path('AddMentorWithUserIdAndNumber',AddMentorWithUserIdAndNumber.as_view(),name='AddMentorWithUserIdAndNumber'),
    path('AssignMentorInClassAndBatch',AssignMentorInClassAndBatch.as_view(),name='AssignMentorInClassAndBatch'),
    path('DeactivateMentorInBatchView',DeactivateMentorInBatchView.as_view(),name='DeactivateMentorInBatchView'),
    path('ActivateMentorInBatchView',ActivateMentorInBatchView.as_view(),name='ActivateMentorInBatchView'),
    path('CreateClassRoomBatchView',CreateClassRoomBatchView.as_view(),name='CreateClassRoomBatchView'),
    
    #search api
    path('StudentSearchApiView',StudentSearchApiView.as_view(),name='StudentSearchApiView'),
    path('StudentSearchMobileApiView',StudentSearchMobileApiView.as_view(),name='StudentSearchMobileApiView'),
    path('StudentSearchSchoolRegisterNumberApiView',StudentSearchSchoolRegisterNumberApiView.as_view(),name='StudentSearchSchoolRegisterNumberApiView'),
    path('StudentSearchClassAndSectionApiView',StudentSearchClassAndSectionApiView.as_view(),name='StudentSearchClassAndSectionApiView'),
 
    #upload xls file 
    path('AddStudentInBulk',AddStudentInBulk.as_view(),name='AddStudentInBulk'),
    path('AddSingleStudentInBatchViewSet',AddSingleStudentInBatchViewSet.as_view(),name="AddSingleStudentInBatchViewSet"),
    path('EditStudentInBatchViewSet',EditStudentInBatchViewSet.as_view(),name='EditStudentInBatchViewSet'),

    #communication message api
    path('CommunicationAPIView',SendMessageAllStudentsAPIView.as_view(),name='CommunicationAPIView'),
    path('ClassWiseSendMessage',SendMessageClassAndSectionWise.as_view(),name='ClassWiseSendMessage'),
    path('SendMessageClassWiseOnSection',SendMessageClassWise.as_view(),name="SendMessageClassWiseOnSection"),
    path('SendMessageStudentWise',SendMessageStudentWise.as_view(),name='SendMessageStudentWise'),
    path('SendMessageStudentUserIdWise',SendMessageStudentUserIdWise.as_view(),name='SendMessageStudentUserIdWise'),
    path('StudentsViewMessageAPIView',StudentsViewMessageAPIView.as_view(),name='StudentsViewMessageAPIView'),

    #Mentor work report url
    path('BatchPaperCountView/<int:batch_id>/',BatchStudentPaperCountView.as_view(),name='BatchStudentPaperCountView'),
    path('mentorpapers/', FetchMentorPapersViewSetAPI.as_view(),name='mentorpapers'),
    path('batch/<pk>/', EditBatchViewSetAPI.as_view(), name='editbatch'),
    path('learnerbatchhistory/', FetchLearnerBatchHistoryViewSetAPI.as_view(),name='learnerbatchhistory'),
    path('getallmentorpaperanswerpapers/', FetchAllAnswerPapersInTheMentorPaperViewSetAPI.as_view(),name='getallmentorpaperanswerpapers'),
    path('mentorassessmentpaper_allreports/<int:assessmentpaper_id>/',MentorAssessmentPaperAllUserReportViewAPI.as_view(), name='api_mentorassessmentpaper_allreports'),
    path('mentorassessment_questionreport/<int:assessmentpaper_id>/',MentorAssessmentQuestionWiseAnalysisReportViewAPI.as_view(), name='api_mentorassessment_questionreport'),
    path('mentorassessment_singlequestionreport/<int:assessmentpaper_id>/',MentorAssessmentSingleQuestionAnalysisReportViewAPI.as_view(), name='api_mentorassessment_singlequestionreport'),
    path('learnerpapers/', FetchLearnerPapersViewSetAPI.as_view(),name='learnerpapers'),
    path('mentorpapersfourinapage/', FetchMentorPapersFourInAPageViewSetAPI.as_view(),name='mentorpapersfourinapage'),
    path('mentorpapers/<pk>/', FetchMentorPaperByIdViewSetAPI.as_view(),name='viewmentorpapers'),
    path('deletetemporaryreplacementquestions/', DeleteMentorPaperTempQuesReplaceViewSetAPI.as_view(),name='deletetemporaryreplacementquestions'),
    path('solution/', SolutionViewSetAPI.as_view(), name='solution'),
    path('question/<pk>/', EditQuestionViewSetAPI.as_view(),name='editquestion'),
    path('mcqtestcase/', MCQTestCaseViewSetAPI.as_view(),name='mcqtestcase'),
    path('findreplacementquestion/',FindReplacementQuestionViewSetAPI.as_view(),name='findreplacementquestion'),
    path('replacequestion/',ReplaceQuestionInMentorPaperViewAPI.as_view(),name='replacequestion'),
    path('courses/', CourseViewSetAPI.as_view(), name='courses'),
    path('courses/all/', AllCourseViewSetAPI.as_view(), name='allcourses'),
    path('courses/<pk>/', EditCourseViewAPI.as_view(), name='editcourse'),
    path('fillupsolution/', FillUpSolutionViewSetAPI.as_view(),name='fillupsolution'),
    path('fillupsolution/<pk>/', EditFillUpViewSetAPI.as_view(),name='editfillupsolution'),
    path('fillwithoption/', FillUpWithOptionCaseViewSetAPI.as_view(),name='fillwithoption'),
    path('fillwithoption/<pk>/', EditFillUpWithOptionViewSetAPI.as_view(),name='editfillwithoption'),
    path('booleansolution/', BooleanTypeViewSetAPI.as_view(),name='booleansolution'),
    path('booleansolution/<pk>/', EditBooleanTypeViewSetAPI.as_view(),name='editbooleansolution'),
    



    #Show Section of particular class 
    path('ShowSectionOfClass',ShowSectionOfClass.as_view(),name='ShowSectionOfClass'),

    #New Api for Studet and Mentor for outside 
    path('allexamname',AllExamIdAndExamName.as_view(),name='allexamname'),
    path('AllExamDetails/<pk>/',AllExamDetails.as_view(),name='AllExamDetails'),
    path('RegisterMentorWitEmailAndPassword',RegisterMentorWitEmailAndPassword.as_view(),name='RegisterMentorWitEmailAndPassword'),
    path('RegisterUserWitEmailAndPassword',RegisterUserWitEmailAndPassword.as_view(),name='RegisterUserWitEmailAndPassword'),
    path('StudentChangePassword',StudentChangePassword.as_view(),name='StudentChangePassword'),
    path('MentorChangePassword',MentorChangePassword.as_view(),name='MentorChangePassword'),
    path('DeactivateBatchView1/<pk>/',DeactivateBatchView1.as_view(),name='DeactivateBatchView'),
    path('ActivateBatchView1/<pk>/',ActivateBatchView1.as_view(),name='ActivateBatchView'),
    path('DeLeteBatchView/<pk>/',DeLeteBatchView.as_view(),name='DeLeteBatchView'),
    path('FetchRoomBatchesViewSet1',BatchViewSet1.as_view(),name='FetchRoomBatchesViewSet1'),
    path('FetchRoomBatchesViewSet2',FetchRoomBatchesViewSet2.as_view(),name='FetchRoomBatchesViewSet2'),
    path('InstituteClassRoomViewSet2',InstituteClassRoomViewSet2.as_view(),name='InstituteClassRoomViewSet2'),
    
    path('AddStudentRoomBatchView',AddStudentRoomBatchView.as_view(),name='AddStudentRoomBatchView'),
    path('AddMentorRoomBatchView',CreateClassRoomBatchView1.as_view(),name='AddMentorRoomBatchView'),


    

    #school api for create grou and and create school 
    
    path('RegisterSchoolWitEmailAndPassword',RegisterSchoolWitEmailAndPassword.as_view(),name='RegisterSchoolWitEmailAndPassword'),
    path('RegisterSuperUser',RegisterSuperUser.as_view(),name='RegisterSuperUser'),
    
    # path('SchoolHomeViewApi',SchoolHomeViewApi.as_view(),name='SchoolHomeViewApi'),
    # path('InstituteApiView',InstituteApiView.as_view(),name='InstituteApiView'),
    # path('InstituteProfileApiView',InstituteProfileApiView.as_view(),name='InstituteProfileApiView'),

    ## Start Api For Bloom Level Question and Content Url 

    #path('bloom_level',Bloom_level.as_view(),name='Bloom_level'),
    path('filterquestionview',FetchQuestionsByFilterViewSetAPI.as_view(),name='filterquestionview'),
    path('overallbloomlevel',OverAllBloomLevel.as_view(),name='overallbloomlevel'),
    path('BloomLevelExamView',BloomLevelExamWiseViewSet.as_view(),name = 'BloomLevelExamView'),
    path('allbloomlevelexam',AllBloomLevelLearnerExamViewSet.as_view(),name='allbloomlevelexam'),
    path('SaveBloomData',SaveBloomData.as_view(),name='SaveBloomData'),
    path('BloomLevelHistoryViewSet',BloomLevelHistoryViewSet.as_view(),name='BloomLevelHistoryViewSet'),
    path('QuestionBloomText',QuestionBloomText.as_view(),name='QuestionBloomText'),
    path('QuestionBloomTextId',QuestionBloomTextId.as_view(),name='QuestionBloomTextId'),
    path('ShowQuestionData',ShowQuestionData.as_view()),
    path('Count_Currently_logged',Count_Currently_logged.as_view()),
    path('test_deploy',TestDeploy.as_view()),
    

]