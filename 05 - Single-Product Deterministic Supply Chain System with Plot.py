'''DETERMINISTIC SINGLE PRODUCT SUPPLY CHAIN SYSTEM'''

import random
import simpy
import os
import pandas
from functools import partial, wraps
import matplotlib.pyplot as plt
import matplotlib.animation as animation

randomSeed=42
# Change the location of the data file in the following line
os.chdir('C:/Users/gvish/Desktop/ISEN 685/FINAL FILES')
x1=pandas.ExcelFile('Single-Product Data File.xlsx')
df1=x1.parse('Sheet1')
"The template for patch_resource function was obtained from the resource monitoring documentation for Simpy "

def patch_resource(resource, pre=None, post=None):
     """Patches 'resource' so that it calls the  'pre' before each
     put/get/request/release operation and the 'post' after each
     operation.  The only argument to these functions is the resource
     instance.

     """
     def get_wrapper(func):
         # Generate a wrapper for put/get/request/release
         @wraps(func)
         def wrapper(*args, **kwargs):
             # This is the actual wrapper
             # Call "pre" callback
             if pre:
                 pre(resource)

             # Perform actual operation
             ret = func(*args, **kwargs)

             # Call "post" callback
             if post:
                 post(resource)

             return ret
         return wrapper

     # Replace the original operations with our wrapper
     for name in ['put', 'get', 'request', 'release']:
         if hasattr(resource, name):
             setattr(resource, name, get_wrapper(getattr(resource, name)))

"""This is the 'post' function that will be called after put/get/request/release operation. 
The 'value' datapoint stores the time and resource level immediately after put/get/request/release operation. 
"""    
def inventorylevelmonitor_DC(data,resource):
    value =( resource._env.now , resource.level)
    data.append(value)


class P:        
    # SPECIFY THE SIMULATION TIME(RUN TIME) IN DAYS
    simulationTimeMax = 61
    '''This is the Parameter Class with different parameters viz. Store order size, Re-order Point, 
    Order Upto Qty, Initial Inventory, Unit Manufacturing Cost, Ordering Cost, Unit Holding Cost, 
    Unit Penalty Cost, Lead Time, and a few corresponding global variables which have to be calculated
    viz. On Order Qty, Total and Satisfied Demand, Total costs, Total inventories etc.'''
    STORE_ORDER_SIZE = df1.iat[0,df1.columns.get_loc("OrderSize_Store")]
    ROP_DC = df1.iat[0,df1.columns.get_loc("ReorderPoint_DC")]
    Order_Upto=df1.iat[0,df1.columns.get_loc("Order_Upto_Qty")]
    LEAD_TIME = df1.iat[0,df1.columns.get_loc("LeadTime(Weeks)")]
    Initial_Inv_DC=df1.iat[0,df1.columns.get_loc("Initial_Inventory_DC")]
    ordering_cost = df1.iat[0,df1.columns.get_loc("Ordering_cost")]
    unit_manufacturing_cost=df1.iat[0,df1.columns.get_loc("Manufacturing_Cost (Per Unit)")]
    unit_holding_cost=df1.iat[0,df1.columns.get_loc("Holding_Cost (Per Unit per time period)")]
    unit_penalty_cost=df1.iat[0,df1.columns.get_loc("Penalty_Cost (per unit)")]
    total_ordering_cost=0
    total_holding_cost=0
    total_penalty_cost=0
    total_overall_cost=0
    # flag1 is used to calculate the total number of customers
    flag1 = 0
    # flag2 is used to calculate the total number of unsatisfied customers
    flag2=0
    on_order=0    
    Inv = 0
    total_demand=0
    satisfied_demand=0
    no_orders=0
    tot_inv=0
    units_manufactured=0

class Inventory :
    '''This class is used to monitor the Inventory of the DC and undertake manufacturing operations
    to replenish the DC inventory'''
    def __init__(self,env):
        '''This is the initialization function which is called along with the class. It is used to 
        create containers for storing Inventory. It calls the DC Inventory monitoring function.'''
        self.env = env
        self.DC_inv = simpy.Container(env,init = P.Initial_Inv_DC)
        self.mon_procDC = env.process(self.monitor_DC_inv(env))        
    def replenish_DC_inv(self,env,qty):
        '''This is the DC inventory replenishing function. The manufacturing process takes place in this
        function. The manufacturing process is essentially waiting for the manufacturing time duration and 
        then for the lead time duration and then adding the units to the DC inventory.'''
        P.on_order+=qty
        P.total_ordering_cost+=P.ordering_cost+qty*P.unit_manufacturing_cost
        P.units_manufactured+=qty
        manufacturing_time=15*qty/(24*60)
        yield self.env.timeout(manufacturing_time)
        yield self.env.timeout(P.LEAD_TIME)
        yield self.DC_inv.put(qty)
        print ('Time {0}: DC replenishment order is added to inventory'.format(self.env.now))
        P.on_order=0            
    def monitor_DC_inv(self,env):
        '''This is the DC inventory monitoring function. It checks whether the inventory falls below the 
        re-order point. On order quantity is also considered while checking this condition. If the level 
        is below the ROP then it calls the DC inventory replenishing function. The yield statement at the 
        end (timeout) is used for controlling the frequency of the review(periodic review system).'''
        while True:    
            if self.DC_inv.level+P.on_order<=P.ROP_DC:
                print('Time {0}: Inventory less than ROP. Inventory is {1}'.format(self.env.now,self.DC_inv.level))
                print ('Time {0}: DC places replenishment order to SUPPLIER'.format(self.env.now))
                qty=P.Order_Upto-self.DC_inv.level
                P.no_orders+=1
                env.process(self.replenish_DC_inv(env,qty-P.on_order))
            else:
                print('Time {0}: Inventory more than ROP. Inventory is {1}'.format(self.env.now,self.DC_inv.level))
            yield self.env.timeout(5)
            
class DCOrderGenerator(object):
    '''This class is used to generate orders for the DC'''
    def __init__(self,env,name=''):
        '''This is the initialization function which is called along with the class. It calls the 
        DC order generating function.'''
        self.env = env
        self.action = self.env.process(self.ordertoDC( ))
        self.name = name
    def ordertoDC (self) :
        '''This is the DC order generating function. This fuction places orders to the DC. If the DC
        inventory level is lesser than the order quantity, partial fulfillment of the order takes place
        and the customer is unsatisfied. If the inventory is 0, customer leaves empty handed and is 
        unsatisfied.Otherwise, the customer waits for a processing time duration and receives the order
        and is satisfied.'''
        print('Time {1}: {0} places order to DC'.format(self.name ,self.env.now))
        if P.Inv.DC_inv.level<P.STORE_ORDER_SIZE :
            if P.Inv.DC_inv.level==0:
                print('Time {1}: {0} leaves empty handed'.format(self.name,self.env.now))
                P.total_penalty_cost+=P.STORE_ORDER_SIZE*P.unit_penalty_cost
            else:
                yield self.env.timeout(2*P.Inv.DC_inv.level/(24*60))
                print('Time {1}: {0} receives only {2} units'.format(self.name,self.env.now,P.Inv.DC_inv.level))
                P.satisfied_demand+=P.Inv.DC_inv.level
                P.total_penalty_cost+=(P.STORE_ORDER_SIZE-P.Inv.DC_inv.level)*P.unit_penalty_cost
                yield P.Inv.DC_inv.get(P.Inv.DC_inv.level)
            P.flag2+=1
        else:
            yield self.env.timeout(2*P.STORE_ORDER_SIZE/(24*60))
            P.satisfied_demand+=P.STORE_ORDER_SIZE
            yield P.Inv.DC_inv.get(P.STORE_ORDER_SIZE)
            print('Time {1}: {0} receives order from DC'.format(self.name , self.env.now) )
        #print('Inventory at end of Day is {}'.format(P.Inv.DC_inv.level))
        
class Store(object) :
    '''This class is to generate orders according to the frequency desired'''
    def __init__(self,env) :
        '''This is the initialization function which is called along with the class. It calls the 
        generating function.'''
        self.env = env
        self.action = env.process(self.Generator())
    def Generator(self) :
        '''This is the generating function. The inter-arrival time between orders can be controlled here.
        It calls the Order Generator class after the inter-arrival time.'''
        while True :
            interarrivalTime_DC = 1
            yield self.env.timeout(interarrivalTime_DC)
            print('Inventory at beginning of Day is {}'.format(P.Inv.DC_inv.level))
            P.flag1+=1
            P.total_demand+=P.STORE_ORDER_SIZE
            P.total_holding_cost+=P.Inv.DC_inv.level*P.unit_holding_cost
            P.tot_inv+=P.Inv.DC_inv.level
            DCOrderGenerator(self.env,name='Store')

def model() :
    '''This is the executable body of the program. It creates and environment and calls the Store and 
    Inventory classes. Duration of the run is controlled here. It prints all the desired data.'''
    plt.style.use('ggplot')
    data=[]
    ims=[]
    fig = plt.figure()
    ax1 = fig.add_subplot(1,1,1)
    ax1.clear()
    random.seed(randomSeed)
    envr = simpy.Environment()
    Store(envr)
    P.Inv = Inventory(envr)
    resourcemonitor=partial(inventorylevelmonitor_DC,data)
    patch_resource(P.Inv.DC_inv , post=resourcemonitor)
    envr.run(until = P.simulationTimeMax)
    
    """This is a loop that creates an array of plot images and stores it in an array. The 
    first plot is an empty plot and the subsequent plots have an additional datapoint.
    """
    
    for i in range(len(data)):
        datax=[x[0] for x in data[0:i]]
        datay=[x[1] for x in data[0:i]]
        ax1.set_xlabel('Time(Days)')
        ax1.set_ylabel('Inventory')
        plt1, =ax1.plot(datax,datay,color ='blue')
        ims.append([plt1])
        
    "This creates a video using an array of images"
    
    ani= animation.ArtistAnimation(fig,ims,interval=50)
    ani.save('Single-Product Deterministic Supply Chain System - Plot.mp4', fps=1)
    plt.show() 

    P.total_overall_cost=P.total_holding_cost+P.total_ordering_cost+P.total_penalty_cost
    print('{} customers left empty handed'.format(P.flag2))
    print('--------------Total Customers = {}'.format(P.flag1))
    print('--------------Satisfied Customers = {}'.format(P.flag1-P.flag2))
    print('--------------Unsatisfied Customers = {}'.format(P.flag2))
    print('--------------Total Demand = {}'.format(P.total_demand))
    print('--------------Satisfied Demand = {}'.format(P.satisfied_demand))
    print('--------------Unsatisfied Demand = {}'.format(P.total_demand-P.satisfied_demand))
    print('--------------Type 1 Service Level = {}%'.format((P.flag1-P.flag2)*100/P.flag1))
    print('--------------Type 2 Service Level = {}%'.format((P.satisfied_demand)*100/P.total_demand))
    print('--------------HOLDING COST = ${}'.format(P.total_holding_cost))
    print('--------------ORDERING COST = ${}'.format(P.total_ordering_cost))
    print('--------------PENALTY COST = ${}'.format(P.total_penalty_cost))
    print('--------------OVERALL COST = ${}'.format(P.total_overall_cost))
    print('--------------Number of Orders = {}'.format(P.no_orders))
    print('--------------Total Inventory = {}'.format(P.tot_inv))
    print('--------------Number of units manufactured = {}'.format(P.units_manufactured))

# Command for execution
model()