'''PUSH SYSTEM G/G/n''' 

import random
import simpy
RANDOM_SEED = 42
NUM_SERVERS = 2 # Number of servers at the counter
SIM_TIME = 10000 # Simulation time in minutes
busy_time = 0 # Used for calculating Utilization

class Q(object):
    '''A store having limited number of servers (``NUM_SERVERS``) to serve 
    customers in parallel. The customers have to wait for one of the servers to
    be free. When a server is free they can order their requirement and wait 
    for it to be finished (which follows a triangular).'''
    def __init__(self, env, num_servers):
        self.env = env
        self.server = simpy.Resource(env, num_servers)
    def serve(self, operation):
        yield self.env.timeout(random.triangular(6,18,12))

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

def arrival(env, num_servers):
    '''Create a store, a first customer and keep generating customers according
    to a Poisson process'''
    store = Q(env, num_servers)
    i=0
    env.process(customer(env, 'Customer %d' % i, store))
    while True:
        yield env.timeout(random.expovariate(1/4))
        i += 1
        env.process(customer(env, 'Customer %d' % i, store))

random.seed(RANDOM_SEED) # This helps reproducing the results

# Create an environment and start the arrival process.
env = simpy.Environment()
env.process(arrival(env, NUM_SERVERS))
# Execute
env.run(until=SIM_TIME)
# Calculate and display utilization as the ratio of busy_time and total time.
print('Utilization = {}% '.format(busy_time/env.now*100/3))

