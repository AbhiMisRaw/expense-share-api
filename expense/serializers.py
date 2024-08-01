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

        # Checking user must be in participants too.
        if self.context["request"].user.username not in participants_set:
            raise serializers.ValidationError(
                "Owner of the Expense must be in Participants."
            )

        # this is list of tuple containing (user, value)
        user_list = []
        # Convert usernames to user instances and create ExpenseSplit objects
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

        # Checking user must be in participants too.
        if self.context["request"].user.username not in participants_set:
            raise serializers.ValidationError(
                "Owner of the Expense must be in Participants."
            )

        # this is list of tuple containing (user, value)
        user_list = []
        # Convert usernames to user instances and and also checking if user exist or not.
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
        """
        Here we are validating some Critical cases as defined below.
        1. Expense amount must be in Natural Number [1-n]
        2. Validation on each Participation amount defined in Requirement.

        Here, We didn't validate the user's in participation array bcz validate method is executed and
        check for any potentital error in initial request-middleware cycle.
        It means that user's existance logic will be executed first in initail stage and then during
        ExpenseSplit object. So it's a good if we use this logic in create/update method.

        """
        amount = data.get("amount")
        if amount <= 0:
            raise serializers.ValidationError(
                "Expense Amount must be a positive Number."
            )

        split_type = data.get("split_type")
        participants = self.initial_data.get("participants", [])
        print(f"PARTICIPANTS : {participants}")

        value_list = []
        for participant in participants:
            value_list.append(participant["value"])

        if split_type == Expense.EXACT:

            total = sum(value_list)
            if float(total) != amount:
                print(f"{amount} != {total}")
                raise serializers.ValidationError(
                    "The total of splits must equal the expense amount."
                )

        elif split_type == Expense.PERCENTAGE:
            total_percentage = sum(value_list)
            if total_percentage != 100:
                raise serializers.ValidationError(
                    "The total percentage splits must equal 100%."
                )
        elif split_type == Expense.EQUAL:
            amount_set = set(value_list)
            if len(amount_set) != 1:
                raise serializers.ValidationError(
                    "You must define same amount for each"
                )
            if sum(value_list) != amount:
                raise serializers.ValidationError(
                    "The total of splits must equal the expense amount."
                )

        return data
