import asyncore, asynchat, socket, signal, threading, sys, pickle
from time import sleep

from helpers import *

#change these values only
PORT = 31337		# The port used by the server. Default 31337
DEBUG = True		# Output all kinds of random junk you probly really don't want to see?
#change these values only

#Global Variables
connectionClassList = []
connectionSocketList = []
shortest = sys.maxint
cities = []
route = []

#Packet Constants#
KEEP_ALIVE = 0  #C -> S #Keep-alive
C_REQ_WORK = 1  #C -> S #Request for work
C_SEND_RES = 2  #C -> S #Send result
C_REQ_UPDT = 3  #C -> S #Request meta-info update
##Server Packets##
S_SEND_UPD = 10 #S -> C #Send meta-info update
S_SERV_KIL = 11 #S -> C #Server Shutting down
##algorithm Packets##
S_WORK_GRE = 20 #S -> C #Send greedy algorithm work
S_WORK_MST = 21 #S -> C #Send MST algorithm work
##Improvement Packets##
S_IMP_SGMT = 30 #S -> C #Send improvement work, swapping segments
S_IMP_SCTY = 31 #S -> C #Send improvement work, swapping cities

#deal with signals
def signal_handler(signum, frame):
	server.sendKill();
	if signum == 2:
		signum = 'Control-c'
	print 'SHUTDOWN!  Reason:', signum
	sleep(1)
	exit()

#Returns a pickle-formatted string based on the packet ID and packet payload
def createPickle(self, id, payload):
	_pickle = pickle.dumps([id, payload])
	return _pickle

def metaPack(self, shortest, cities, route):
	_pickle = pickle.dumps([shortest, cities, route])
	return _pickle

#If client sends us a packet ID 0 (keep-alive)
#Then just pong one back to the client
#I think this is obsolete now, keeping to be safe.
def dealKeepAlive(self, payload):
	print 'replying to keep-alive from:', self.addr
	self.sendall( createPickle(self, KEEP_ALIVE, payload + " reply") )
	self.send("\r\n\r\n")

#Actually handles requests for work.
#For now, this just sends a static packet, to test.
def dealRequest(self, payload):
	if DEBUG:
		print "Request for work being handled!"
	self.sendall(createPickle(self, S_WORK_GRE, 7))
	self.send("\r\n\r\n")
	#7 is a placeholder.  PLEASE FIX

def dealResult(self, payload):
	length = route_length(cities, payload)
	if DEBUG:
		print "we got a result!", length
	#Actually do stuff later.

#The client asked for various meta-info, send it.
#Currently sends the length of shortest path so far,
#the list of cities, and the shortest path so far.
def dealMetaUpdate(self):
	if DEBUG:
		print "Request for meta-info update being handled."
	_pickle = metaPack(self, shortest, cities, route)
	self.sendall(createPickle(self, S_SEND_UPD, _pickle))
	self.send("\r\n\r\n")
	
#Class For handling the event-driven server
class PacketHandler(asynchat.async_chat):
	def __init__(self, _sock, addr):
		asynchat.async_chat.__init__(self, _sock)
		self.set_terminator("\r\n\r\n")
		self.request = None
		self.data = ""
		self.sock = _sock
		self.addr = addr
		print "handler set up!"

	def collect_incoming_data(self, data):
		self.data = self.data + data

	def found_terminator(self):
		data = self.data
		self.data = ""
		#lets load up that pickle!  (DOES NOT DEAL WITH INVALID PICKLE!)
		id, payload = pickle.loads(data)
		#assuming we actually received SOMETHING.....
		if data:
			if (DEBUG == 2):
				print id, payload
			if id == KEEP_ALIVE:
				dealKeepAlive(self, payload)
				#Client Sent keep-alive.  Reply to it.
			elif id == C_REQ_WORK:
				dealRequest(self, payload)
				#Client Requested work.  Call work handleing Function
			elif id == C_SEND_RES:
				print "Hey, we got a result.  Deal with it."
				dealResult(self, payload)
			elif id == C_REQ_UPDT:
				dealMetaUpdate(self)
				#Client requested Meta-info update.  Call function to send it.
			else:
				print 'something went wrong.', id, payload

#Class that sets up the event-driven server
#and passes data it receives to the PacketHandler() class
class AsyncServer(asyncore.dispatcher):
	def __init__(self, port):
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind(("", port))
		self.listen(5)
		print 'Server is now listening for connections.'

	def handle_request(self, channel, method, path, header):
		print "blah"

	#We have been told to shutdown!
	#Make sure we send the shutdown packet first!
	def sendKill(self):
		for _socketobject in connectionSocketList:
			try:
				_socketobject.send( createPickle(self, S_SERV_KIL, 'Server says SHUTDOWN!') )
				print str( _socketobject.getpeername()[0] ) + ':' + str( _socketobject.getpeername()[1] ) + ' was sent the shutdown signal!'
			except Exception:
				pass

	#We got a client connection!
	def handle_accept(self):
		pair = self.accept()
		if pair is None:
			print 'something is messed up', pair
			pass
		else:
			sock, addr = pair
			handler = PacketHandler(sock, addr)
			connectionClassList.append(self)
			connectionSocketList.append(sock)

	def handle_close(self):
		print self.addr, 'has disconnecteed!'
		self.close()

#set up signal handler(s)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGABRT, signal_handler)

#Set up
print "Setting up server..."
generate_test_set(15000,4000)
cities = return_set(15000)

#Run the event-driven server
print "Opening Socket..."
server = AsyncServer(PORT)
asyncore.loop(1)