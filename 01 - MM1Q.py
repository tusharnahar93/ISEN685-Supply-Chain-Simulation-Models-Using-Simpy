'''The M/M/1 queue is a single server system with infinite waiting space, where
the customers arrive according to a Poisson process and the processing time at 
the counter is according to an Exponential distribution.''' 

import random
import simpy
RANDOM_SEED = 42
NUM_SERVERS = 1 # Number of servers at the counter
#x=input('Enter Process Time in minutes - ')
#y=input('Enter Mean Inter Arrival Time in minutes - ')
PROCESS_TIME = 55 #int(x) # Minutes it takes to serve customer
INTERARRIVAL_TIME = 60 #int(y) #Mean Inter-arrival time bet. customers in mins
SIM_TIME = 1000 # Simulation time in minutes
busy_time = 0 # Used for calculating Utilization

class MM1Q(object):
    '''A store having limited number of servers (``NUM_SERVERS``) to serve 
    customers in parallel. The customers have to wait for one of the servers to
    be free. When a server is free they can order their requirement and wait 
    for it to be finished (which takes exp(PROCESS_TIME) minutes).'''
    def __init__(self, env, num_servers, process_time):
        self.env = env
        self.server = simpy.Resource(env, num_servers)
        self.process_time = process_time
    def serve(self, operation):
        '''This function is to simulate the processing operation by waiting for
        the required period of time.'''
        yield self.env.timeout(random.expovariate(1/PROCESS_TIME))

def customer(env, name, store):
    '''The customer (each having a name) arrives at the store (store), and waits 
    for a server to be free, places their order, waits for it to be completed 
    and then leaves.'''
    print('%s arrives at the store at %.2f.' % (name, env.now))
    with store.server.request() as request:
        yield request
        print('%s reaches the counter at %.2f.' % (name, env.now))
        starting_time=env.now
        yield env.process(store.serve(name))
        print('%s leaves the counter at %.2f.' % (name, env.now))
        ending_time=env.now
        '''To calculate utilization, we need the total operating time of the 
        servers. So, we create a global variable(busytime) to store the operating
        time for every customer cumulatively.'''
        global busy_time
        busy_time += ending_time-starting_time

def arrival(env, num_servers, process_time, interarrival_time):
    '''Create a store, a first customer and keep generating customers according
    to a Poisson process'''
    store = MM1Q(env, num_servers, process_time)
    i=0
    env.process(customer(env, 'Customer %d' % i, store))
    while True:
        yield env.timeout(random.expovariate(1/INTERARRIVAL_TIME))
        i += 1
        env.process(customer(env, 'Customer %d' % i, store))

random.seed(RANDOM_SEED) # This helps reproducing the results

# Create an environment and start the arrival process.
env = simpy.Environment()
env.process(arrival(env, NUM_SERVERS, PROCESS_TIME, INTERARRIVAL_TIME))
# Execute
env.run(until=SIM_TIME)
# Calculate and display utilization as the ratio of busy_time and total time.
print('Utilization = {}% '.format(busy_time/env.now*100))

