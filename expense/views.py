# from django.shortcuts import render

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO


from django.db import transaction
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework import filters
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .models import Expense, ExpenseSplit

from .serializers import ExpenseSerializer
from user.models import User


class ExpenseViewSet(viewsets.ModelViewSet):
    filter_backends = [filters.OrderingFilter]
    # for ordering each expense
    ordering_fields = ["updated", "created"]
    ordering = ["-updated"]
    http_method_names = ["get", "post", "put", "delete"]
    # only for authenticated user
    permission_classes = (IsAuthenticated,)
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        return Expense.objects.filter(owner=self.request.user)

    def get_object(self):
        obj = Expense.objects.get_object_by_id(self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def create(self, request, *args, **kwargs):
        user_model = get_user_model()
        id = request.user.id

        user = User.objects.get_object_by_id(id=id)

        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            with transaction.atomic():
                # Delete related ExpenseSplit instances
                ExpenseSplit.objects.filter(expense=instance).delete()

                # Delete the Expense instance
                self.perform_destroy(instance)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_update(self, serializer):
        serializer.save()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def participants_expenses(request):
    user = request.user
    queryset = (
        Expense.objects.filter(expensesplit__user=user).exclude(owner=user).distinct()
    )

    if not queryset.exists():
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = ExpenseSerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def participant_expense_detail(request, pk):
    user = request.user
    try:
        expense = (
            Expense.objects.filter(expensesplit__user=user)
            .exclude(owner=user)
            .distinct()
            .get(id=pk)
        )
    except Expense.DoesNotExist:
        return Response(
            {"detail": "There is no such transactions"},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = ExpenseSerializer(expense)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_total_expense(request):
    user = request.user
    splits = ExpenseSplit.objects.filter(user=user)

    # Create a BytesIO buffer to hold the PDF data
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Set up title and column headers
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, height - 50, f"Balance Sheet for {user.username}")

    p.setFont("Helvetica", 10)
    y = height - 80
    p.drawString(50, y, "Date")
    p.drawString(150, y, "Title")
    p.drawString(250, y, "Total Amount")
    p.drawString(350, y, "Split Type")
    p.drawString(450, y, "Spent Amount")

    y -= 20
    p.line(50, y + 5, width - 50, y + 5)
    y -= 20
    total_amount = 0

    for split in splits:
        if split.expense.split_type == Expense.PERCENTAGE:
            value = (split.value / 100) * split.expense.amount
        else:
            value = split.value

        p.drawString(50, y, str(split.expense.created.strftime("%Y-%m-%d")))
        p.drawString(150, y, split.expense.title)
        p.drawString(250, y, str(split.expense.amount))
        p.drawString(350, y, split.expense.split_type)
        p.drawString(450, y, str(value))

        y -= 20
        p.line(50, y + 5, width - 50, y + 5)
        y -= 20
        total_amount += value

    p.drawString(50, y, "Total amount Spent")
    p.drawString(450, y, str(total_amount))

    p.showPage()
    p.save()

    # Move to the beginning of the StringIO buffer
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="balance_sheet_{user.username}.pdf"'
    )

    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_single_expense(request, pk):
    user = request.user
    try:
        expense = Expense.objects.filter(expensesplit__user=user).distinct().get(id=pk)
    except Expense.DoesNotExist:
        return Response(
            {"detail": "There is no such transactions"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Create a BytesIO buffer to hold the PDF data
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Set up title
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, height - 50, f"Expense Report for Expense ID: {pk}")

    # Add expense details
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 100, f"Title: {expense.title}")
    p.drawString(50, height - 120, f"Spend by: {expense.owner}")
    p.drawString(50, height - 140, f"Totla Spent amount : {expense.amount} INR")
    p.drawString(50, height - 160, f"Expense Type: {expense.split_type}")
    p.drawString(50, height - 180, f"Date: {expense.created.strftime('%Y-%m-%d')}")

    y = height - 180
    y -= 20
    p.line(50, y + 5, width - 50, y + 5)
    y -= 20
    p.drawString(50, y, "User")
    p.drawString(250, y, "Amount")

    y -= 20
    p.line(50, y + 5, width - 50, y + 5)
    y -= 20
    p.setFont("Helvetica", 13)

    # Add details for each split
    for split in expense.expensesplit_set.all():
        p.drawString(50, y, split.user.username)
        p.drawString(250, y, str(split.value))
        y -= 20
        p.line(50, y + 5, width - 50, y + 5)
        y -= 20

    p.showPage()
    p.save()

    # Move to the beginning of the StringIO buffer
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="expense_{pk}.pdf"'

    return response
