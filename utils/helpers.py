def get_client_ip(request):
        '''here we get the browser/client ip from the request'''
        x_forwared_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwared_for:
            actual_ip = x_forwared_for.split(',')[0]
        else:
            actual_ip = request.META.get('REMOTE_ADDR')
        return actual_ip
