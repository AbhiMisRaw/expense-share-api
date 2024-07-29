from django.db import transaction
from rest_framework import serializers

from .models import Expense, ExpenseSplit
from user.models import User


class ExpenseSplitSerializer(serializers.ModelSerializer):
    user = serializers.CharField()  # this will help to collect username

    class Meta:
        model = ExpenseSplit
        fields = ["user", "value"]


class ExpenseSerializer(serializers.ModelSerializer):
    participants = serializers.SerializerMethodField()
    created = serializers.DateTimeField(read_only=True)
    updated = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Expense
        fields = [
            "id",
            # "owner",
            "title",
            "amount",
            "split_type",
            "created",
            "updated",
            "participants",
        ]

    def get_participants(self, obj):
        # Serialize related ExpenseSplit instances
        splits = obj.expensesplit_set.all()
        return ExpenseSplitSerializer(splits, many=True).data

    def create(self, validated_data):
        participants_data = self.initial_data.get("participants", [])

        # collecting unique user's username
        participants_set = set([data["user"] for data in participants_data])

        # validating all user must be unique
        if len(participants_data) != len(participants_set):
            raise serializers.ValidationError(
                "Duplicate user found in Participants instances, User must be unique."
            )

        if self.context["request"].user.username not in participants_set:
            raise serializers.ValidationError(
                "Owner of the Expense must be in Participants."
            )

        # Convert usernames to user instances and create ExpenseSplit objects
        user_list = []
        for participant_data in participants_data:
            username = participant_data.pop("user")

            user = User.objects.filter(username=username).first()
            if user is None:
                raise serializers.ValidationError(
                    f"User with username {username} does not exist."
                )
            user_list.append((user, participant_data.pop("value")))

        # After all validation we save the data
        # Atomic transaction block
        with transaction.atomic():
            # Save the expense
            expense = Expense.objects.create(
                owner=self.context["request"].user,
                title=validated_data["title"],
                amount=validated_data["amount"],
                split_type=validated_data["split_type"],
            )

            # Save the ExpenseSplit objects
            for user, value in user_list:
                ExpenseSplit.objects.create(expense=expense, user=user, value=value)

        return expense

    def update(self, instance, validated_data):
        participants_data = self.initial_data.get("participants", [])

        # Collect unique user's username
        participants_set = set(data["user"] for data in participants_data)

        # Validate all users must be unique
        if len(participants_data) != len(participants_set):
            raise serializers.ValidationError(
                "Duplicate user found in Participants instances, User must be unique."
            )

        if self.context["request"].user.username not in participants_set:
            raise serializers.ValidationError(
                "Owner of the Expense must be in Participants."
            )

        # Convert usernames to user instances and create ExpenseSplit objects
        user_list = []
        for participant_data in participants_data:
            username = participant_data.pop("user")

            user = User.objects.filter(username=username).first()
            if user is None:
                raise serializers.ValidationError(
                    f"User with username {username} does not exist."
                )
            user_list.append((user, participant_data.pop("value")))

        # Atomic transaction block
        with transaction.atomic():
            # Update the expense instance
            instance.title = validated_data.get("title", instance.title)
            instance.amount = validated_data.get("amount", instance.amount)
            instance.split_type = validated_data.get("split_type", instance.split_type)
            instance.save()

            # Delete old ExpenseSplit objects
            ExpenseSplit.objects.filter(expense=instance).delete()

            # Save new ExpenseSplit objects
            for user, value in user_list:
                ExpenseSplit.objects.create(expense=instance, user=user, value=value)

        return instance

    def validate(self, data):
        amount = data.get("amount")
        split_type = data.get("split_type")
        participants = self.initial_data.get("participants", [])
        print(f"PARTICIPANTS : {participants}")
        if split_type == Expense.EXACT:
            expense_list = [participant["value"] for participant in participants]

            total = sum(expense_list)

            if float(total) != amount:
                print(f"{amount} != {total}")
                raise serializers.ValidationError(
                    "The total of splits must equal the expense amount."
                )
        elif split_type == Expense.PERCENTAGE:
            total_percentage = sum(participant["value"] for participant in participants)
            if total_percentage != 100:
                raise serializers.ValidationError(
                    "The total percentage splits must equal 100%."
                )
        elif split_type == Expense.EQUAL:
            amount_array = [participant["value"] for participant in participants]
            amount_set = set(amount_array)
            if len(amount_set) != 1:
                raise serializers.ValidationError(
                    "You must define same amount for each"
                )
            if sum(amount_array) != amount:
                raise serializers.ValidationError(
                    "The total of splits must equal the expense amount."
                )

        return data



