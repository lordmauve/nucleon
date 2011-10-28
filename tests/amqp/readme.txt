performance tests:

Start the test app:
nucleon.py start

Asynchronous:
ab -n 1000 -c 10 http://127.0.0.1:8888/push

Synchronous:
ab -n 1000 -c 10 http://127.0.0.1:8888/push_sync
