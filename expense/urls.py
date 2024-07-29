from django.urls import path
from rest_framework import routers
from .views import (
    ExpenseViewSet,
    participants_expenses,
    participant_expense_detail,
    my_total_expense,
    download_single_expense,
)

router = routers.SimpleRouter()

router.register(r"expenses", ExpenseViewSet, basename="expense")


urlpatterns = [
    *router.urls,
    path("expenses/share", participants_expenses),
    path("expenses/share/<int:pk>", participant_expense_detail),
    path("expenses/share/<int:pk>/download", download_single_expense),
    path("my-expense/download", my_total_expense),
]
