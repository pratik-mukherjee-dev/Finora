from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from . import services


class AuthStateView(APIView):
    """Public: tells the frontend whether the single local account exists yet."""
    permission_classes = (AllowAny,)

    def get(self, request):
        return Response({"initialized": User.objects.exists()})


class RegisterView(APIView):
    """Public, first-run only: create the local account and return JWT tokens."""
    permission_classes = (AllowAny,)

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        if not username or not password:
            return Response(
                {"detail": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = services.register_first_user(username, password)
        except services.AlreadyInitialized:
            return Response(
                {"detail": "An account already exists on this device."},
                status=status.HTTP_409_CONFLICT,
            )
        refresh = RefreshToken.for_user(user)
        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh)},
            status=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        # Stateless logout: this single-user offline app keeps no server-side
        # token blacklist. The client discards its stored tokens, which fully
        # ends the session.
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({
            "user_id": request.user.id,
            "username": request.user.username,
        })