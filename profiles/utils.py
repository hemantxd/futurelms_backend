import re
import os
import csv
import time
import random
import string
import csv
from itertools import tee
import pandas as pd
import datetime
from django.conf import settings
from django.utils import timezone
from profiles import models as profile_models
from courses import models as courses_models
from authentication import models as authentication_models
from rest_framework import serializers
#from core.s3_upload import upload_to_s3_or_copy_to_media_file
from core import models as core_models

def isValidEmail(email):
    if(re.match("^.+@(\[?)[a-zA-Z0-9-.]+.([a-zA-Z]{2,3}|[0-9]{1,3})(]?)$", email) != None):
        return True
    return False

def current_milli_time(): return int(round(time.time() * 1000))

def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

def bulkuploadUserCSV(csv_file, institute_id, grade_id):
    alerts = []
    save_users = True   # Boolean Flag | Change to False If any error in Csv
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

    required_fields = ['S.No', 'FirstName', 'LastName','UserName',
                        'Email', 'PhoneNumber']
        
    fieldnames = [ field for field in reader.fieldnames ]

    for field in required_fields:
        if field not in fieldnames:
            alerts.append(('Error', "The CSV file does not contain the required headers"))
            return(alerts, False)
    
    temp_cond_list = []
    existing_emails_object =  authentication_models.User.objects.values('email')
    existing_emails = [i['email'] for i in existing_emails_object]
    existing_username_object = authentication_models.User.objects.values('username')
    existing_username = [i['username'] for i in existing_username_object]
    # existing_phonenumber_object = authentication_models.User.objects.values('phonenumber')
    # existing_phonenumber = [i['phonenumber']
    #                         for i in existing_phonenumber_object]
    
    for row in reader1:
        sno, fname, lname = row['S.No'], row['FirstName'], row['LastName']
        username, email, phno= row['UserName'], row['Email'], row['PhoneNumber']
        if(not(sno or fname or lname or username or email or phno)):
            alerts.append(('Error', "Empty Row"))
            save_users = False
            return(alerts, False)
        if(not sno):
            save_users = False
            alerts.append(('Error', "Enter S.No"))
        if(not fname):
            alerts.append((sno, "Enter FirstName"))
            save_users = False
        if(username):
            if(username in temp_cond_list):
                alerts.append((sno, "username - {} is repeated multiple times in the file".format(username)))
                return(alerts, False)
            else:
                temp_cond_list.append(username)
            if(username in existing_username):
                alerts.append((username, "Username Already Registered"))
                save_users = False
            if(len(username) < 5):
                alerts.append((username, "UserName length Should be atleast 5 Characters."))
                save_users=False
        if(email):
            if(email in temp_cond_list):
                alerts.append((sno, "Email - {} is repeated multiple times in the file".format(email)))
                return(alerts, False)
            else:
                temp_cond_list.append(email)
            if(email in existing_emails):
                alerts.append((email, "Email Already Registered"))
                save_users = False
            elif(not(isValidEmail(email))):
                alerts.append((email, "Invalid Email"))
                save_users = False
        if(phno):
            if(phno in temp_cond_list):
                alerts.append((sno, "Phone Number - {} is repeated multiple times in the file".format(phno)))
                return(alerts, False)
            else:
                temp_cond_list.append(phno)
            # if(phno in existing_phonenumber):
            #     alerts.append((phno, "PhoneNumber Already Registered"))
                # save_users = False
            if(len(phno) != 10):
                alerts.append((sno, "PhoneNumber Should have 10 digits!"))
                save_users = False            
    if(save_users):
        last_user_created_id = authentication_models.User.objects.all().last().id
        data = []
        institute_id
        institute_obj = profile_models.Institute.objects.get(id=int(institute_id))
        grade_obj = core_models.UserClass.objects.get(id=int(grade_id))
        for row in reader2:
            last_user_created_id += 1
            sno, fname, lname = row['S.No'], row['FirstName'], row['LastName']
            username, email, phno = row['UserName'], row['Email'], row['PhoneNumber']
            if(not(email)):
                email = None
            new_user = authentication_models.User(email=email, phonenumber=phno)
            if(not(username)):
                username = str(10000 + last_user_created_id)
            new_user.username = username
            password = randomString(8)
            new_user.set_password(password)
            new_user.is_individual = False
            new_user.save()
            new_user_profile = new_user.profile
            new_user_profile.first_name = fname
            new_user_profile.institute = institute_obj
            new_user_profile.studentClass = grade_obj
            if(lname):  new_user_profile.last_name = lname
            if(phno):
                new_user_profile.contact_verified = True
            new_user_profile.save()
            
            userdata = {
                'FirstName': fname,
                'LastName': lname,
                'Email': email,
                'PhoneNumber': phno,
                'Username': username,
                'Password': password
            }
            data.append(userdata)
    if(save_users):  return(data, True)
    else:  return(alerts, False)