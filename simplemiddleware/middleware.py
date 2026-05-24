import logging
import time
from django.utils.deprecation import MiddlewareMixin

#logger config 
logger = logging.getLogger('request_logging')

class SimpleLoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        '''here the processing of the client request is done
        before views is called
        '''
        request._start_time = time.time()
    
    def process_response(self, request, response):
        '''handles what is sent as response of the request,
        extract and log them
        '''
        #time taken for request to response
        duration = time.time() - getattr(request, '_start_time', time.time())
        
        #get ip, browser info, request type
        ip_addr = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'UNKNOWN')
        path = request.path
        http_method = request.method

        #actual log the data
        logger.info(
            f"IP: {ip_addr} , Browser: {user_agent}"
            f"Request Method: {http_method} , Time taken: {duration:.2f}s"
            f"Response code: {response.status_code}"
        )

        return response
    def get_client_ip(self, request):
        '''here we get the browser/client ip from the request'''
        x_forwared_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwared_for:
            actual_ip = x_forwared_for.split(',')[0]
        else:
            actual_ip = request.META.get('REMOTE_ADDR')
        return actual_ip
            