from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AccountAPIView, accountGenericView, AccountModelViewSet

router = DefaultRouter()
router.register('accounts', AccountModelViewSet, basename="account")

urlpatterns = [
    path('api/v1/accounts/', AccountAPIView.as_view()),
    #for patch/delete apiview - same url 
    path('api/v1/accounts/<uuid:id>/', AccountAPIView.as_view()),

    #modelviewset urls
    path('api/v1/', include(router.urls)),

    
    #generic apiviews urls
    path('api/v1/generic/accounts/', accountGenericView.as_view()),
    path('api/v1/generic/accounts/<uuid:id>/', accountGenericView.as_view()),
]
