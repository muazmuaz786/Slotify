from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from user.permissions import IsAdmin, IsBookingManager
from user.serializers import UserSerializer, LoginSerializer
from user.paginition import UserPagination
from user.models import User


def set_jwt_cookies(response, access_token: str, refresh_token: str) -> None:
    """Attach JWT tokens to HttpOnly cookies (secure in production)."""
    access_max_age = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
    refresh_max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
    secure_cookie = not settings.DEBUG
    samesite = "None" if secure_cookie else "Lax"

    response.set_cookie(
        "access",
        access_token,
        max_age=access_max_age,
        httponly=True,
        secure=secure_cookie,
        samesite=samesite,
        path="/",
    )
    response.set_cookie(
        "refresh",
        refresh_token,
        max_age=refresh_max_age,
        httponly=True,
        secure=secure_cookie,
        samesite=samesite,
        path="/",
    )


class UserViewSet(ModelViewSet):
    def get_queryset(self):
        base_qs = User.objects.filter(deleted=False)
        if self.action == "list":
            return base_qs
        return base_qs.prefetch_related("following", "followers")

    def get_serializer(self, *args, **kwargs):
        if self.action == "login":
            return LoginSerializer(*args, **kwargs)
        return UserSerializer(*args, **kwargs)



    def get_permissions(self):
        if self.action in ["login", "refresh", "create", "retrieve"]:
            permission_classes = [AllowAny]
        elif self.action in ["follow", "unfollow", "logout"]:
            permission_classes = [IsAuthenticated]
        elif self.action in ["list"]:
            permission_classes = [IsAdmin]
        else:
            permission_classes = [IsAuthenticated, IsAdmin | IsBookingManager]
        return [permission() for permission in permission_classes]
    
    pagination_class = UserPagination    
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        cache_key = f"user_{instance.id}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)

        serializer = self.get_serializer(instance)
        cache.set(cache_key, serializer.data, timeout=3600)
        return Response(serializer.data, status=status.HTTP_200_OK)


    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def login(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        response = Response({"access": access_token, "refresh": str(refresh), "user": UserSerializer(user).data}, status=status.HTTP_200_OK)

        set_jwt_cookies(response, access_token, str(refresh))
        return response
    

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def refresh(self, request):
        refresh_token = request.COOKIES.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token not provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            new_refresh_token = str(refresh)
            response = Response({"access": access_token, "refresh": new_refresh_token}, status=status.HTTP_200_OK)
            set_jwt_cookies(response, access_token, new_refresh_token)
            return response
        except Exception as e:
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def logout(self, request):
        response = Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        response.delete_cookie("access", path="/")
        response.delete_cookie("refresh", path="/")
        return response
    
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def follow(self, request, pk=None):
        user_to_follow = self.get_object()
        if user_to_follow == request.user:
            return Response({"detail": "You cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)
        if user_to_follow.deleted:
            return Response({"detail": "Cannot follow a deleted user."}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.following.filter(pk=user_to_follow.pk).exists():
            return Response({"detail": "You are already following this user."}, status=status.HTTP_400_BAD_REQUEST)
        request.user.following.add(user_to_follow)
        request.user.save()
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def unfollow(self, request, pk=None):
        user_to_unfollow = self.get_object()
        if user_to_unfollow == request.user:
            return Response({"detail": "You cannot unfollow yourself."}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.following.filter(pk=user_to_unfollow.pk).exists():
            return Response({"detail": "You are not following this user."}, status=status.HTTP_400_BAD_REQUEST)
        request.user.following.remove(user_to_unfollow)
        request.user.save()
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        response = Response({"access": access_token, "refresh": str(refresh), "user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)
        set_jwt_cookies(response, access_token, str(refresh))
        return response
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        cache_key = f"user_{instance.id}"
        cache.delete(cache_key)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        cache_key = f"user_{instance.id}"
        cache.delete(cache_key)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def perform_destroy(self, instance):
        instance.deleted = True
        instance.save()
