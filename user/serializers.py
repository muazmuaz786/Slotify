from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import serializers
from user.models import User

class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password",
            "role",
            "first_name",
            "last_name",
            "date_of_birth",
            "profile_picture",
            "date_joined",
            "bio",
            "phone_number",
            "is_verified",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "date_joined", "role", "is_verified", "created_at", "updated_at"]

    def create(self, validated_data):
        if validated_data.get("role") == "admin":
            raise serializers.ValidationError(
                "The Admin role must be created by an admin user, not via this serializer."
            )

        if validated_data.get("profile_picture") and not validated_data["profile_picture"].content_type.startswith("image/"):
            raise serializers.ValidationError("The uploaded file must be an image.")

        if User.objects.filter(username=validated_data["username"]).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        
        if User.objects.filter(phone_number=validated_data.get("phone_number", "")).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        
        if validated_data.get("date_of_birth") and (timezone.now().date() - validated_data["date_of_birth"]).days < 6570:
            raise serializers.ValidationError("User must be at least 18 year old.")
        


        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            date_of_birth=validated_data.get("date_of_birth"),
            profile_picture=validated_data.get("profile_picture"),
            bio=validated_data.get("bio", ""),
            phone_number=validated_data.get("phone_number", ""),
        )
        return user

    def update(self, instance, validated_data):
        username = validated_data.get("username")
        if username and User.objects.exclude(pk=instance.pk).filter(username=username).exists():
            raise serializers.ValidationError("A user with this username already exists.")

        phone_number = validated_data.get("phone_number")
        if phone_number and User.objects.exclude(pk=instance.pk).filter(phone_number=phone_number).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")

        if validated_data.get("date_of_birth") and (timezone.now().date() - validated_data["date_of_birth"]).days < 6570:
            raise serializers.ValidationError("User must be at least 18 year old.")

        for attr, value in validated_data.items():
            if attr == "password":
                instance.set_password(value)
            elif attr == "profile_picture":
                if value and not value.content_type.startswith("image/"):
                    raise serializers.ValidationError("The uploaded file must be an image.")
                setattr(instance, attr, value)
            else:
                setattr(instance, attr, value)
        instance.save()
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.pop("password", None)

        display_name = f"{instance.first_name} {instance.last_name}".strip()
        representation["full_name"] = display_name
        representation["profile_picture"] = (
            instance.profile_picture.url if instance.profile_picture else None
        )
        return representation


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs["username"],
            password=attrs["password"]
        )

        if not user:
            raise serializers.ValidationError("invalid username or password")

        attrs["user"] = user

        user.last_login = timezone.now()
        user.save()
        
        return attrs
