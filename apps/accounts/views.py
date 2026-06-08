from rest_framework.views import APIView
from .models import Account, Transaction, TransactionLog
from rest_framework.response import Response
from .serializers import AccountSerializer, TransactionSerializer
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework import status, viewsets
from rest_framework.decorators import action
from utils.choices import AccountStatus, TransactionStatus
from django.db import transaction
from rest_framework.permissions import IsAuthenticated


#GenericAPIView + mixin Imports
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin,CreateModelMixin,DestroyModelMixin,RetrieveModelMixin,UpdateModelMixin


#APIView
class AccountAPIView(APIView):
    
    def get(self, request, id=None):
        
        if id:
            #if api enpoint requests one account detail
            account = get_object_or_404(Account, id=id)
            serializer = AccountSerializer(account)
            return Response(serializer.data)
        #otherwise return list of accounts
        account = Account.objects.all()
        serializer = AccountSerializer(account,many = True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = AccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
        
    def patch(self, request, id):
        account = get_object_or_404(Account, id=id)
        serializer = AccountSerializer(account, data=request.data, partial = True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    def delete(self, request, id):
        account = get_object_or_404(Account, id=id)
        temp = account.account_number
        account.delete()
        return Response({"message": f"successfully deleted {temp}."},
            status=status.HTTP_200_OK)

#GenericAPIview + Mixin
#this is easiest and cleanest version
#this is used only if we have no custom logics
#as it already provides the CRUD operations with simple, plain requirements
#not versatile as APIView for large scale systems
    

class accountGenericView(GenericAPIView,CreateModelMixin,ListModelMixin,RetrieveModelMixin,UpdateModelMixin,DestroyModelMixin):
    queryset=Account.objects.all()
    serializer_class=AccountSerializer
    lookup_field = "id"
    
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
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

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
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    
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