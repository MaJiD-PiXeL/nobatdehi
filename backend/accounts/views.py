from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer, token_pair_for


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "login"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):  # type: ignore[no-untyped-def]
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"user": UserSerializer(user).data, "tokens": token_pair_for(user)}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "login"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):  # type: ignore[no-untyped-def]
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        return Response({"user": UserSerializer(user).data, "tokens": token_pair_for(user)})


class MeView(APIView):
    def get(self, request):  # type: ignore[no-untyped-def]
        return Response(UserSerializer(request.user).data)

    def patch(self, request):  # type: ignore[no-untyped-def]
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class LogoutAllView(APIView):
    """Invalidate every outstanding refresh token belonging to the current user."""

    def post(self, request):  # type: ignore[no-untyped-def]
        for token in OutstandingToken.objects.filter(user=request.user):
            BlacklistedToken.objects.get_or_create(token=token)
        return Response(status=status.HTTP_204_NO_CONTENT)

