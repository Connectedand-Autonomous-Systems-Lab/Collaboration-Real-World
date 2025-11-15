import threading

threads = threading.enumerate()

for t in threads:
    print(t.name, t.ident)

print(threading.active_count())