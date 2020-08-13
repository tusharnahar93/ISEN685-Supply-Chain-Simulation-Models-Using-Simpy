'''The CONWIP system is a pull system where the departure of an entity pulls the
next entity into the server. The processing time at the server is according to 
an Exponential distribution.''' 

import random
import simpy
RANDOM_SEED = 42
NUM_SERVERS = 3 # Number of servers at the counter
SIM_TIME = 50 # Simulation time in minutes
busy_time = 0
mintime=50
# Used for calculating Utilization
class CONWIP(object):
   '''A store having limited number of servers (``NUM_SERVERS``) to serve 
   customers in parallel. The customers have to wait for one of the servers to
   be free. When a server is free they can order their requirement and wait 
   for it to be finished (which takes exp(PROCESS_TIME) minutes).'''
   def __init__(self, env, num_servers):
       self.env = env
       self.server = simpy.Resource(env, capacity = num_servers)
   def serve(self, operation):
       yield self.env.timeout(random.triangular(low=0.1 , high=0.3 , mode = 0.2))

def customer(env, name, store):
   '''The customer (each having a name) arrives at the store (store), and waits 
   for a server to call them once the previous customer has been served, places
   their order, waits for it to be completed and then leaves.'''
   print('%s arrives at the store at %.2f.' % (name, env.now))
   with store.server.request() as request:
       yield request
       #print ('Number of servers busy = ',store.server.count)
       print('%s reaches the counter at %.2f.' % (name, env.now))
       starting_time=env.now
       yield env.process(store.serve(name))
       print('%s leaves the counter at %.2f.' % (name, env.now))
       ending_time=env.now
       a=store.server.count
       while(NUM_SERVERS-a>=0):
           yield env.process(generator(env))
           a +=1
       '''To calculate utilization, we need the total operating time of the 
       servers. So, we create a global variable(busytime) to store the operating
       time for every customer cumulatively.'''
       global busy_time,mintime
       if(env.now <= mintime):
           busy_time=0
       busy_time += ending_time-starting_time
def arrival(env, num_servers):
   '''Create a store and  a first customer'''
   global store,i
   store = CONWIP(env, num_servers)
   i=0
   yield env.timeout(0)
   env.process(customer(env, 'Customer %d' % i, store))

def generator(env):
   '''Create a customer whenever this function is called i.e. whenever the 
   server is free.'''
   global i
   i +=1
   yield env.timeout(0)
   env.process(customer(env, 'Customer %d' % i, store))

random.seed(RANDOM_SEED) # This helps reproducing the results

# Create an environment and start the arrival process.
env = simpy.Environment()
env.process(arrival(env, NUM_SERVERS))
# Execute
env.run(until=SIM_TIME)
# Calculate and display utilization as the ratio of busy_time and total time.
#print('Utilization = {}% '.format(busy_time/(env.now-mintime)*100/3))