from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import(
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from rest_framework.authtoken.views import obtain_auth_token

from .views import (
    AccountAPIView,
    accountGenericView,
    AccountModelViewSet,
    TransactionModelViewSet,
    TransactionRefundAPIView,
    AccountFreezeAPIView,
    NestedTransactionCreateAPIView,
    LogoutView,
    CustomTokenObtainPairView,
    LoginSessionListView,
    LoginSessionRevokeView
)

router = DefaultRouter()
router.register('accounts', AccountModelViewSet, basename="account")
router.register('transactions', TransactionModelViewSet, basename="transaction")

urlpatterns = [
    #auth urls-
    #token-auth
    path('api/v1/auth/token/', obtain_auth_token, name='drf-token'), #default drf token
    #jwt token
    
    path("api/v1/auth/jwt/create/", CustomTokenObtainPairView.as_view(), name="jwt_create"),
    path('api/v1/auth/jwt/refresh/', TokenRefreshView.as_view(), name='jwt-refresh'),
    path('api/v1/auth/jwt/verify/', TokenVerifyView.as_view(), name='jwt-verify'),
    
    path("api/v1/auth/logout/", LogoutView.as_view(), name="logout"),

    path("api/v1/auth/sessions/", LoginSessionListView.as_view(), name="session_list"),
    path("api/v1/auth/sessions/<uuid:session_id>/revoke/", LoginSessionRevokeView.as_view(), name="session_revoke"),

    
    #views-api-endpoints
    path('api/v1/raw/accounts/', AccountAPIView.as_view()),
    #for patch/delete apiview - same url
    path('api/v1/raw/accounts/<uuid:id>/freeze/', AccountFreezeAPIView.as_view()),
    path('api/v1/raw/accounts/<uuid:id>/', AccountAPIView.as_view()),
    path('api/v1/raw/transactions/<uuid:id>/refund/', TransactionRefundAPIView.as_view()),
    
    
    #nested write apiview endpoint
    path('api/v1/raw/transactions/create-nested/', NestedTransactionCreateAPIView.as_view()),
    
    
    #generic apiviews urls
    path('api/v1/generic/accounts/', accountGenericView.as_view()),
    path('api/v1/generic/accounts/<uuid:id>/', accountGenericView.as_view()),
    
    #modelviewset urls
    path('api/v1/', include(router.urls)),
]
