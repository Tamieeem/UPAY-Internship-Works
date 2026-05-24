# Django Custom Request Logger

A lightweight, global HTTP request and response auditing middleware built for Django. It automatically tracks client IPs, browser types (User-Agents), status codes, and exact request processing execution times.

## Features
- **Global Interception**: Captures 100% of all incoming requests and outgoing responses across all apps via centralized middleware.
- **Client IP Tracking**: Extracts real user IPs through standard headers (`X-Forwarded-For`) even when behind load balancers or CDNs.
- **Performance Profiling**: Computes request processing duration down to the millisecond.
- **Production Logging**: Writes structured entries into dedicated local logs with automated dynamic folder initialization (`os.makedirs`).

## Log Output Format
Log streams are generated dynamically inside `logs/request_logs.log` matching the format below:
```text
INFO 2026-05-24 14:08:48,774 IP: 127.0.0.1 , Browser: Mozilla/5.0... Request Method: GET , Time taken: 0.04s Response code: 404
```
