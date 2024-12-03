from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(Communication)
admin.site.register(BatchThird)
admin.site.register(APIKeysForVerify)
admin.site.register(BarBloomLevel)
admin.site.register(BloomLevelValues)
admin.site.register(OverAllBloomLevelValues)

#admin.site.register(City)
#admin.site.register(State)
#admin.site.register(Institute)
#admin.site.register(InstituteClassRoom)
#admin.site.register(Profile)
#admin.site.register(UserBoard)
#admin.site.register(UserGroup)
#admin.site.register(UserClassRoom)
#admin.site.register(Batch)
#admin.site.register(LearnerBatches)
#admin.site.register(StudentInstituteChangeInvitation)
