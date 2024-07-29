from rest_framework import routers

from user.views import (
    UserViewSet,
    UserRegisterViewSet,
    UserLoginViewSet,
    UserRefreshViewSet,
)

router = routers.SimpleRouter()

router.register(r"register", UserRegisterViewSet, basename="auth-register")
router.register(r"login", UserLoginViewSet, basename="auth-login")
router.register(r"refresh", UserRefreshViewSet, basename="auth-refresh")
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [*router.urls]
