.PHONY: install migrate localrun productionrun loaddata
	
install:
	pip install --upgrade setuptools pip
	pip install -r requirements.txt

lmigrate:
	python manage.py makemigrations --settings=config.local
	python manage.py migrate --settings=config.local

pmigrate:
	python manage.py migrate --settings=config.production --noinput

lcollectstatic:
	python manage.py collectstatic --settings=config.local --noinput

pcollectstatic:
	python manage.py collectstatic --settings=config.production --noinput -i ckeditor -i admin -i bootstrap_admin
	# python manage.py collectstatic --settings=config.production --noinput

localrun:
	python manage.py runserver 0.0.0.0:8081 --settings=config.local

productionrun:
	python manage.py runserver 0.0.0.0:8081 --settings=config.production

loaddata:
	# python manage.py loaddata fixtures/countrystatecity.countries.json --settings=config.production
	# python manage.py loaddata fixtures/countrystatecity.states.json --settings=config.production
	# python manage.py loaddata fixtures/countrystatecity.cities.json --settings=config.production
	python manage.py loaddata fixtures/authentication.user.json --settings=config.production
	python manage.py loaddata fixtures/profiles.profile.json --settings=config.production
# 	python manage.py loaddata fixtures/courses.subject.json
# 	python manage.py loaddata fixtures/courses.standard.json
# 	python manage.py loaddata fixtures/courses.substd.json
# 	python manage.py loaddata fixtures/courses.standard.json
# 	python manage.py loaddata fixtures/courses.course.json
# 	python manage.py loaddata fixtures/courses.package.json
# 	python manage.py loaddata fixtures/courses.chapter.json
# 	python manage.py loaddata fixtures/courses.topic.json
# 	python manage.py loaddata fixtures/quiz.questiontag.json
# 	python manage.py loaddata fixtures/quiz.question.json
# 	python manage.py loaddata fixtures/quiz.solution.json
# 	python manage.py loaddata fixtures/quiz.mcqtestcase.json


