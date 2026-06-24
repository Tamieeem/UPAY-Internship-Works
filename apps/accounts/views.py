from rest_framework.views import APIView
from .models import Account, Transaction, TransactionLog
from rest_framework.response import Response
from .serializers import AccountSerializer, TransactionSerializer, RegisterUserSerializer
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework import status, viewsets
from rest_framework.decorators import action
from utils.choices import AccountStatus, TransactionStatus
from django.db import transaction
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from .nested_serializers import TransactionWriteSerializer, TransactionNestedSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError



#GenericAPIView + mixin Imports
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework.mixins import ListModelMixin,CreateModelMixin,DestroyModelMixin,RetrieveModelMixin,UpdateModelMixin


#APIView
class AccountAPIView(APIView):
    
    def get(self, request, id=None):
        
        if id:
            #if api enpoint requests one account detail
            account = get_object_or_404(Account, id=id, user=request.user)
            serializer = AccountSerializer(account)
            return Response(serializer.data)
        #otherwise return list of accounts
        account = Account.objects.filter(user=request.user)
        serializer = AccountSerializer(account, many = True)
        return Response(serializer.data)
    
    
    def post(self, request):
        serializer = AccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # serializer.save()
        serializer.save(user=request.user)
        return Response(serializer.data)
        
    def patch(self, request, id):
        account = get_object_or_404(Account, id=id, user=request.user)
        serializer = AccountSerializer(account, data=request.data, partial = True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    def delete(self, request, id):
        account = get_object_or_404(Account, id=id, user=request.user)
        deleted_account = account.account_number
        account.delete()
        return Response({"message": f"successfully deleted {deleted_account}."},
            status=status.HTTP_200_OK)

#Refund using APIView.
class TransactionRefundAPIView(APIView):
    """
        Refund a transaction logic using APIView. Uses post()
        instead of action method. Manual object fetching as
        it's how the APIView works.
    """
    permission_classes = [IsAuthenticated]
    def post(self, request, id=None):
        original = get_object_or_404(Transaction.objects.filter(
            Q(from_account__user=request.user) | Q(to_account__user=request.user)), id=id)
        
        #check if transaction is already refunded, if yes, client gets 400 error message.
        if original.status == TransactionStatus.REFUNDED:
            return Response(
                {"detail": "Can't Refund a Already REFUNDED transaction"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if original.status != TransactionStatus.COMPLETED:
            return Response(
                {"detail": "No amount was transferred, Refund not applicable"},
                status=status.HTTP_400_BAD_REQUEST
            )
        with transaction.atomic():
            refund_creation = Transaction.objects.create(
                from_account = original.to_account,
                to_account = original.from_account,
                amount = original.amount,
                status = TransactionStatus.COMPLETED,
                reversal_of = original,
            )
            #must change original transaction status to avoid multi-refund
            original.status = TransactionStatus.REFUNDED
            original.save(update_fields=["status"])
            
            #audit log
            TransactionLog.objects.create(
                original_transaction = original,
                action = "REFUND",
                #which user got the refund
                actor = request.user,
            )
        return Response(
            TransactionSerializer(refund_creation, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

#Freeze with APIView
class AccountFreezeAPIView(APIView):
    """POST /api/v1/raw/accounts/{id}/freeze/ — APIView twin of the ViewSet's freeze action."""
    permission_classes = [IsAuthenticated]
    def post(self, request, id=None):
        account = get_object_or_404(Account, id=id, user=request.user)
        if account.status == AccountStatus.CLOSED:
            return Response({"detail": "Cannot freeze a closed account."},
                            status=status.HTTP_400_BAD_REQUEST)
        account.status = AccountStatus.FROZEN
        account.save(update_fields=["status"])
        return Response(AccountSerializer(account).data)



#GenericAPIview + Mixin
#this is easiest and cleanest version
#this is used only if we have no custom logics
#as it already provides the CRUD operations with simple, plain requirements
#not versatile as APIView for large scale systems
    

class accountGenericView(GenericAPIView,CreateModelMixin,ListModelMixin,RetrieveModelMixin,UpdateModelMixin,DestroyModelMixin):
    queryset=Account.objects.all()
    serializer_class=AccountSerializer
    lookup_field = "id"
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def get(self, request, id=None):
        if id:
            return self.retrieve(request, id=id)
        return self.list(request)
    def post(self, request):
        return self.create(request)
    
    def patch(self, request, id):
        return self.partial_update(request)
    
    def delete(self, request, id):
        return self.destroy(request)


#ModelViewSet 
#CUSTOM METHOD/ ACTION - Freeze an Account Logic
#this is simpler than APIView as
#this provides pre built create, delete, update, get operation codes
#its not commonly used as its less flexible than API view
#only useful when requirements are simple, less custom logic, only simple-plain requirements.

class AccountModelViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    
    def perform_create(self, serializer):
    # the owner comes from the authenticated request, never the client payload
        serializer.save(user=self.request.user)
        
    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def freeze(self, request, pk=None):
        """
        Custom action -> POST api/v1/accounts/{id}/freeze/

        detail=True  -> operates on ONE object (URL has the id); the router
        builds /accounts/{pk}/freeze/ automatically.
        Unlike a blind PATCH, this owns its rules: it can refuse to freeze
        an account that's already closed, and it only ever sets ONE status.
        """
        account = self.get_object()  

        if account.status == AccountStatus.CLOSED:
            return Response(
                {"detail": "Cannot freeze a closed account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        account.status = AccountStatus.FROZEN
        #change the status field in db
        account.save(update_fields=["status"]) 
        return Response(AccountSerializer(account).data)

#TransactionModelViewSet
#refund-- custom action

class TransactionModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer
    def get_queryset(self):
        user = self.request.user
        return Transaction.objects.filter(
            Q(from_account__user=user) | Q(to_account__user=user)
        )
    

    @action(detail=True, methods=["post"])
    def refund(self, request, pk=None):
        original = self.get_object()
        
        #check if transaction is already refunded, if yes, client gets 400 error message.
        if original.status == TransactionStatus.REFUNDED:
            return Response(
                {"detail": "Can't Refund a Already REFUNDED transaction"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if original.status != TransactionStatus.COMPLETED:
            return Response(
                {"detail": "No amount was transferred, Refund not applicable"},
                status=status.HTTP_400_BAD_REQUEST
            )
        with transaction.atomic():
            refund_creation = Transaction.objects.create(
                from_account = original.to_account,
                to_account = original.from_account,
                amount = original.amount,
                status = TransactionStatus.COMPLETED,
                reversal_of = original,
            )
            #must change original transaction status to avoid multi-refund
            original.status = TransactionStatus.REFUNDED
            original.save(update_fields=["status"])
            
            #audit log
            TransactionLog.objects.create(
                original_transaction = original,
                action = "REFUND",
                #which user got the refund
                actor = request.user,
            )
        return Response(
            TransactionSerializer(refund_creation).data,
            status=status.HTTP_201_CREATED
        )


#nested write serializer test APIView
class NestedTransactionCreateAPIView(APIView):
    """
        POST /api/v1/raw/transactions/create-nested/
        transaction with account creation(from_account) at same time.
    """
    def post(self, request):
        serializer = TransactionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transaction = serializer.save(user=request.user)
        return Response(
            TransactionNestedSerializer(transaction).data,
            status=status.HTTP_201_CREATED,
        )


#register user
class RegisterUserView(CreateAPIView):
    '''
        CreateAPIView for simply registering user without anything manual writing.
        Allowany is crucial override as we can't enforce "authenticated" before
        user is created or logged in. New user must have the permission to create
        and login. So Allowany is used here.
    '''
    permission_classes = [AllowAny]
    serializer_class = RegisterUserSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response(
            {
                "success": True,
                "message": "User registered successfully",
                "user": {
                    "id": user.id,
                    "username": user.username,
                }
            },
            status=status.HTTP_201_CREATED
        )
        

#logoutview - refresh token



class LogoutView(APIView):
    # IsAuthenticated: caller must present a valid ACCESS token to log out.
    # That guarantees request.user exists — a known principal performing the action.
    permission_classes = [IsAuthenticated]

    def post(self, request):
        #Logout targets the REFRESH token.
        #it just expires on its own in a few minutes. So the client sends us the
        refresh_token = request.data.get("refresh")

        # No token in the body = client mistake, not a server fault so clean 400.
        if refresh_token is None:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)

            #writes the token to the blacklist table. After this it can never be
            # used for a new access token again.
            token.blacklist()

        except TokenError:
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 205 Reset Content = "discard your local state" (the client should drop
        # both tokens now). 205 is the SimpleJWT convention.
        return Response(status=status.HTTP_205_RESET_CONTENT)