# coding: utf-8
import random
import urllib  # Python URL functions
import requests
from django.core.mail import send_mail
from django.conf import settings

def send_exception_email(body):
    send_mail(
        subject="Some Error occurred",
        recipient_list=[settings.ADMIN_EMAIL],
        from_email=settings.DEFAULT_FROM_EMAIL,
        message=body
    )

def AwsSmsMessage(mobile_numbers, message):
    """
    :param mobile_numbers list
    :param message:
    :return: send message on each number present in list
    """

    mobile_numbers = mobile_numbers if isinstance(mobile_numbers, (list, tuple)) else [mobile_numbers]
    values = {'Message': message}
    failed = []
    success = []
    for number in mobile_numbers:
        values['PhoneNumber'] = "91"+str(number)
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json'}
        url = "https://3cr512bq8f.execute-api.ap-southeast-1.amazonaws.com/dev" # API URL
        try:
            requests.post(url, json=values, headers=headers)
            success.append(number)
        except:
            failed.append(number)
    return success, failed

def FactorSmsMessage(mobile_numbers, message):
    """
    :param mobile_numbers list
    :param message:
    :return: send message on each number present in list
    """

    mobile_numbers = mobile_numbers if isinstance(mobile_numbers, (list, tuple)) else [mobile_numbers]
    values = {'From': 'APTINN', 'Msg': message}
    failed = []
    success = []
    for number in mobile_numbers:
        values['To'] = "91"+str(number)
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json'}
        url = "http://2factor.in/API/V1/907b09c2-a174-11e9-ade6-0200cd936042/ADDON_SERVICES/SEND/TSMS" # API URL
        try:
            requests.post(url, json=values, headers=headers)
            success.append(number)
        except:
            failed.append(number)
    return success, failed
    
def SmsMessage(mobile_numbers, senderid, message, provider):
    """
    :param mobile_numbers list
    :param message:
    :return: send message on each number present in list
    """

    mobile_numbers = mobile_numbers if isinstance(mobile_numbers, (list, tuple)) else [mobile_numbers]
    
    if provider and provider=='aws':
        values = {'Message': message}
        failed = []
        success = []
        for number in mobile_numbers:
            values['PhoneNumber'] = "91"+str(number)
            headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json'}
            url = "https://3cr512bq8f.execute-api.ap-southeast-1.amazonaws.com/dev" # API URL
            try:
                requests.post(url, json=values, headers=headers)
                success.append(number)
            except:
                failed.append(number)
        return success, failed
    elif provider and provider=='2factor':
        values = {'From':senderid, 'TemplateName':'1707163317624747950'}
        # for k, v in vars_data:
        #     values[k] = v
        failed = []
        success = []
        for number in mobile_numbers:
            
            values['To'] = "91"+str(number)
            headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json'}
            # url = "http://2factor.in/API/V1/907b09c2-a174-11e9-ade6-0200cd936042/ADDON_SERVICES/SEND/TSMS" # API URL
            url = "http://priority.muzztech.in/sms_api/sendsms.php?username=erdrclasses&password=muzztechsms&mobile={0}&sendername=ERDRCL&message={1}&templateid=1707163317624747950".format(number, message)
            try:
                r = requests.get(url)
                success.append(number)
                data = r.json()
                print ("dataaaa", data)
                if data['Status'] == 'Success':
                    success.append(number)
                elif data['Status'] == 'Error':
                    failed.append(number)
            except:
                print ("failed")
                failed.append(number)
        return success, failed


