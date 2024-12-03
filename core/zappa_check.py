from django.core import management

def preassignmentstartnotification():
	management.call_command('preassignment_start_notification')
