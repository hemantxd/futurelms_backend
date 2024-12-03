from django.db import models

class Countries(models.Model):
    sortname = models.CharField(max_length=255, null=False, blank=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    phonecode = models.CharField(max_length=255, null=False, blank=False)

    def __str__(self):
        return self.name

class States(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    country = models.ForeignKey(Countries, on_delete=models.CASCADE)
    def __str__(self):
        return self.name


class Cities(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    state = models.ForeignKey(States, on_delete=models.CASCADE)

    def __str__(self):
        return self.name