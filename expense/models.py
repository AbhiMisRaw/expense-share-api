from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from user.models import User


class ExpenseManager(models.Manager):
    def get_object_by_id(self, id):
        try:
            instance = self.get(id=id)
            return instance
        except (ObjectDoesNotExist, ValueError, TypeError):
            return Http404


class Expense(models.Model):
    EXACT = "EXACT"
    PERCENTAGE = "PERCENTAGE"
    EQUAL = "EQUAL"
    SPLIT_TYPE = (
        (EXACT, "Specify Amount"),
        (EQUAL, "Divide Equally"),
        (PERCENTAGE, "Divide based on Percentage"),
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    split_type = models.CharField(max_length=20, choices=SPLIT_TYPE)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = ExpenseManager()

    def __str__(self) -> str:
        return f"{self.title[:15]} {self.amount} INR"


class ExpenseSplit(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.user} {self.value}"
