from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy

from django.views.generic import (
    View, TemplateView, ListView, DetailView,
    CreateView, UpdateView, DeleteView,
)
from .models import Account


class FintechHome(TemplateView):
    '''renders the static home page, not query.'''
    
    template_name = "templates/account_view.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["Mfs"] = "Welcome to Upay home page"
        return context


class AccountTemplateView(TemplateView):
    '''
    Renders a static-ish page with context. No object/queryset
    machinery — just "show this template".
    '''
    template_name = "templates/account_view.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_accounts"] = Account.objects.count()
        return context
    
class AccountListView(ListView):
    '''Fetches a queryset and hands it to a template as `object_list`.'''
    model = Account
    context_object_name = "accounts_list"
    template_name = "templates/account_list.html"
    paginate_by = 20

class AccountDetailView(DetailView):
    '''Looks up a single object (by <pk> in the URL by default) and renders it.'''
    
    model = Account
    context_object_name = "account details"
    template_name = "templates/account_details.html"

class AccountCreateView(CreateView):
    model = Account
    fields = ["account_number", "status"]
    template_name = "templates/form.html"
    success_url = reverse_lazy("account-list")
    
class AccountUpdateView(UpdateView):
    """
    Like CreateView but loads an existing object first, so the form is
    pre-populated and POST updates instead of inserts.
    """
    model = Account
    fields = ["account_number", "status"]
    template_name = "accounts/form.html"
    success_url = reverse_lazy("account-list")


#DeleteView — confirmation page on GET, delete on POST.
class AccountDeleteView(DeleteView):
    """
    deletes the object on POST.
    """
    model = Account
    template_name = "accounts/confirm_delete.html"
    success_url = reverse_lazy("account-list")

class AccountBalanceView(View):
    def get(self,request,pk):
        account=Account.objects.get(pk=pk)
        return JsonResponse({'balance': str(account.balance)})