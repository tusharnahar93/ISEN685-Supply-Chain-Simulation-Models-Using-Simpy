''' MULTI-PRODUCT, TWO-TIER SUPPLY CHAIN SYSTEM '''

import random
import simpy
import numpy
import os
import pandas

randomSeed=5
# Change the location of the data file in the following line
os.chdir('C:/Users/gvish/Desktop/ISEN 685/FINAL FILES')
x1=pandas.ExcelFile('Multi-Product Data File.xlsx')
df1=x1.parse('Sheet1')
df2=x1.parse('Sheet3')
noofitems=df1.shape[0]




class P:
    # SPECIFY THE SIMULATION TIME(RUN TIME) IN DAYS
    simulationTimeMax = 60
    '''This is the Parameter Class with different parameters viz. Re-order Point, Order Upto Qty,
    Initial Inventory, Unit Manufacturing Cost, Ordering Cost, Unit Holding Cost, Unit Penalty Cost,
    Lead Time, and a few corresponding global variables which have to be calculated viz. On Order Qty,
    Total and Satisfied Demand, Total costs, Total inventories etc.'''
    ROP_DC = df1['ReorderPoint_DC'].values.tolist()
    Order_Upto=df1['Order_Upto_Qty'].values.tolist()
    Initial_Inv_DC=df1['Initial_Inventory_DC'].values.tolist()
    # flag1 is used to calculate the total number of customers
    flag1=[0]*noofitems
    # flag2 is used to calculate the total number of unsatisfied customers
    flag2=[0]*noofitems
    on_order=[0]*noofitems
    Inv =None
    total_demand=[0]*noofitems
    satisfied_demand=[0]*noofitems
    ordering_cost = df1['Ordering_cost'].values.tolist()
    unit_manufacturing_cost=df1['Manufacturing_Cost (Per Unit)'].values.tolist()
    unit_holding_cost=df1['Holding_Cost (Per Unit per time period)'].values.tolist()
    unit_penalty_cost=df1['Penalty_Cost (per unit)'].values.tolist()
    total_ordering_cost=[0]*noofitems
    total_holding_cost=[0]*noofitems
    total_penalty_cost=[0]*noofitems
    total_overall_cost=[0]*noofitems
    no_orders=[0]*noofitems
    tot_inv=[0]*noofitems
    units_manufactured=[0]*noofitems
    total_ordering_cost_allitems=0
    total_holding_cost_allitems=0
    total_penalty_cost_allitems=0
    total_overall_cost_allitems=0
    distribution_leadtime=df2['Distribution -LeadTime(Days)'].values.tolist()
    a_leadtime=df2['a(LeadTime)'].values.tolist()
    b_leadtime=df2['b(LeadTime)'].values.tolist()
    c_leadtime=df2['c(LeadTime)'].values.tolist()
    distribution_manufacturingtime =df2['Distribution -ManufacturingTime'].values.tolist()
    a_manufacturingtime=df2['a(ManufacturingTime)'].values.tolist()
    b_manufacturingtime=df2['b(ManufacturingTime)'].values.tolist()
    c_manufacturingtime=df2['c(ManufacturingTime)'].values.tolist()
    distribution_demand =df2['Distribution - Demand'].values.tolist()
    a_demand=df2['a(Demand)'].values.tolist()
    b_demand=df2['b(Demand)'].values.tolist()
    c_demand=df2['c(Demand)'].values.tolist()
    distribution_processingtime =df2['Distribution -ProcessingTime'].values.tolist()
    a_processingtime=df2['a(ProcessingTime)'].values.tolist()
    b_processingtime=df2['b(ProcessingTime)'].values.tolist()
    c_processingtime=df2['c(ProcessingTime)'].values.tolist()
    Interarrival_time=df1['InterArrivalTime'].values.tolist()
    Review_Period=df1['Review Period'].values.tolist()
    
class Inventory :
    '''This class is used to monitor the Inventory of the DC and undertake manufacturing operations
    to replenish the DC inventory'''
    def __init__(self,env):
        '''This is the initialization function which is called along with the class. It is used to 
        create containers for storing Inventory. It calls the DC Inventory monitoring function.'''
        self.env = env
        self.DC_inv=[]
        self.mon_procDC = []
        for i in range(noofitems):
          self.DC_inv.append(simpy.Container(env,init = P.Initial_Inv_DC[i]))
          self.mon_procDC.append(env.process(self.monitor_DC_inv(env,i)))
        self.manufacturing_time=[0]*noofitems
    def replenish_DC_inv(self,env,qty,i):
        '''This is the DC inventory replenishing function. The manufacturing process takes place in this
        function. The manufacturing process is essentially waiting for the manufacturing time duration and 
        then for the lead time duration and then adding the units to the DC inventory.'''
        self.lead_time=distribution(P.distribution_leadtime[i],P.a_leadtime[i],P.b_leadtime[i],P.c_leadtime[i])
        P.on_order[i]+=qty
        self.manufacturing_time[i]=0
        P.total_ordering_cost[i]+=P.ordering_cost[i]+qty*P.unit_manufacturing_cost[i]
        P.units_manufactured[i]+=qty
        for x in range(0,qty):
            self.manufacturing_time[i]+=distribution(P.distribution_manufacturingtime[i],P.a_manufacturingtime[i],P.b_manufacturingtime[i],P.c_manufacturingtime[i])
        self.manufacturing_time[i]=self.manufacturing_time[i]/(24*60)
        yield self.env.timeout(self.manufacturing_time[i])
        yield self.env.timeout(self.lead_time)
        yield self.DC_inv[i].put(qty)
        print ('Time {0}: DC replenishment order for Item {1} is added to inventory'.format(self.env.now,i+1))
        P.on_order[i]=0             
    def monitor_DC_inv(self,env,i):
        '''This is the DC inventory monitoring function. It checks whether the inventory falls below the 
        re-order point. On order quantity is also considered while checking this condition. If the level 
        is below the ROP then it calls the DC inventory replenishing function. The yield statement at the 
        end (timeout) is used for controlling the frequency of the review(periodic review system).'''
        while True:    
            if self.DC_inv[i].level+P.on_order[i]<=P.ROP_DC[i]:
                print('Time {0}: Inventory less than ROP for item {2}. Inventory is {1}.'.format(self.env.now,self.DC_inv[i].level,i+1))
                print ('Time {0}: DC places replenishment order to SUPPLIER for item {1}.'.format(self.env.now,i+1))
                qty=P.Order_Upto[i]-self.DC_inv[i].level
                P.no_orders[i]+=1
                env.process(self.replenish_DC_inv(env,qty-P.on_order[i],i))
            else:
                print('Time {0}: Inventory more than ROP for item {2}. Inventory is {1}.'.format(self.env.now,self.DC_inv[i].level,i+1))
            yield self.env.timeout(P.Review_Period[i])
            
class DCOrderGenerator(object):
    '''This class is used to generate orders for the DC'''
    def __init__(self,env,name,i):
        '''This is the initialization function which is called along with the class. It calls the 
        DC order generating function.'''
        self.env = env
        self.action = self.env.process(self.ordertoDC(i))
        self.name = name
        self.demand=distribution(P.distribution_demand[i],P.a_demand[i],P.b_demand[i],P.c_demand[i])            
        P.total_demand[i]+=self.demand
        self.processing_time=[0]*noofitems
    def ordertoDC (self,i) :
        '''This is the DC order generating function. This fuction places orders to the DC. If the DC
        inventory level is lesser than the order quantity, partial fulfillment of the order takes place
        and the customer is unsatisfied. If the inventory is 0, customer leaves empty handed and is unsatisfied.
        Otherwise, the customer waits for a processing time duration and receives the order and is satisfied.
        '''
        print('Time {1}: {0} places order of {2} units of Item {3} to DC.'.format(self.name ,self.env.now, self.demand,i+1))
        if P.Inv.DC_inv[i].level<self.demand:
            if P.Inv.DC_inv[i].level==0:
                print('Time {1}: {0} leaves empty handed.'.format(self.name,self.env.now))
                P.total_penalty_cost[i]+=self.demand*P.unit_penalty_cost[i]
                P.flag2[i]=P.flag2[i]+1
            else:   
                self.processing_time[i]=0
                for x in range(self.demand-P.Inv.DC_inv[i].level):
                    self.processing_time[i]+=distribution(P.distribution_processingtime[i],P.a_processingtime[i],P.b_processingtime[i],P.c_processingtime[i])
                self.processing_time[i]=self.processing_time[i]/(24*60)
                yield self.env.timeout(self.processing_time[i])
                print('Time {1}: {0} receives only {2} units of item {3}.'.format(self.name,self.env.now,P.Inv.DC_inv[i].level,i+1))
                P.total_penalty_cost[i]+=(self.demand-P.Inv.DC_inv[i].level)*P.unit_penalty_cost[i]
                P.satisfied_demand[i]+=P.Inv.DC_inv[i].level
                yield P.Inv.DC_inv[i].get(P.Inv.DC_inv[i].level)
                P.flag2[i]=P.flag2[i]+1
        else:
            self.processing_time[i]=0
            for x in range(self.demand):
                self.processing_time[i]+=distribution(P.distribution_processingtime[i],P.a_processingtime[i],P.b_processingtime[i],P.c_processingtime[i])
            self.processing_time[i]=self.processing_time[i]/(24*60)
            yield self.env.timeout(self.processing_time[i])
            P.satisfied_demand[i]+=self.demand
            yield P.Inv.DC_inv[i].get(self.demand)
            print('Time {1}: {0} receives order from DC of item {2}.'.format(self.name,self.env.now,i+1))
                
class Store(object) :
    '''This class is to generate orders according to the frequency desired'''
    def __init__(self,env) :
        '''This is the initialization function which is called along with the class. It calls the 
        generating function.'''
        self.env = env
        self.action = []
        for i in range(noofitems):
            self.action.append(env.process(self.Generator(i)))
            
    def Generator(self,n) :
        '''This is the generating function. The inter-arrival time between orders can be controlled here.
        It calls the Order Generator class after the inter-arrival time.'''
        while True :
            interarrivalTime_DC =P.Interarrival_time[n]
            yield self.env.timeout(interarrivalTime_DC)
            print('Inventory of item {1} at beginning of Day is {0}'.format(P.Inv.DC_inv[n].level,n+1))
            P.flag1[n]+=1
            P.total_holding_cost[n]+=P.Inv.DC_inv[n].level*P.unit_holding_cost[n]
            P.tot_inv[n]+=P.Inv.DC_inv[n].level
            DCOrderGenerator(self.env,name='Store',i=n)

def distribution(dist,a,b,c):
    '''This function created a dictionary that matches the option selected in the drop-down menu of the
    excel file to the distribution.'''
    switcher = {
            "Uniform(a=LowestValue b=HighestValue)": random.uniform(a,b),
            "Triangular(a=LowestValue b=HighestValue c=MostLikelyValue)":random.triangular(a,b,c),
            "Poisson(a=MeanValue)":numpy.random.poisson(a)
            }
    return switcher.get(dist,0)            

def model() :
    '''This is the executable body of the program. It creates and environment and calls the Store and 
    Inventory classes. Duration of the run is controlled here. It prints all the desired data.'''
    random.seed(randomSeed)
    numpy.random.seed(randomSeed)
    envr = simpy.Environment()
    Store(envr)
    P.Inv = Inventory(envr)  
    envr.run(until = P.simulationTimeMax)
    for i in range(noofitems):
        print("\n\n                           Item {0}\n".format(i+1))
        P.total_overall_cost[i]=P.total_holding_cost[i]+P.total_ordering_cost[i]+P.total_penalty_cost[i]
        print('{} customers left empty handed'.format(P.flag2[i]))
        print('--------------Total Customers = {}'.format(P.flag1[i]))
        print('--------------Satisfied Customers = {}'.format(P.flag1[i]-P.flag2[i]))
        print('--------------Unsatisfied Customers = {}'.format(P.flag2[i]))
        print('--------------Total Demand = {}'.format(P.total_demand[i]))
        print('--------------Satisfied Demand = {}'.format(P.satisfied_demand[i]))
        print('--------------Unsatisfied Demand = {}'.format(P.total_demand[i]-P.satisfied_demand[i]))
        print('--------------Type 1 Service Level = {}%'.format((P.flag1[i]-P.flag2[i])*100/P.flag1[i]))
        print('--------------Type 2 Service Level = {}%'.format((P.satisfied_demand[i])*100/P.total_demand[i]))
        print('--------------HOLDING COST = ${}'.format(P.total_holding_cost[i]))
        print('--------------ORDERING COST = ${}'.format(P.total_ordering_cost[i]))
        print('--------------PENALTY COST = ${}'.format(P.total_penalty_cost[i]))
        print('--------------OVERALL COST = ${}'.format(P.total_overall_cost[i]))
        print('--------------Number of Orders = {}'.format(P.no_orders[i]))
        print('--------------Total Inventory = {}'.format(P.tot_inv[i]))
        print('--------------Number of units manufactured = {}'.format(P.units_manufactured[i]))    
    for i in range(noofitems):
        P.total_holding_cost_allitems += P.total_holding_cost[i]
        P.total_ordering_cost_allitems += P.total_ordering_cost[i]
        P.total_penalty_cost_allitems += P.total_holding_cost[i]
        P.total_overall_cost_allitems += P.total_overall_cost[i]
    
    print("\n                          For ALL Items\n")
    print('--------------HOLDING COST = ${}'.format(P.total_holding_cost_allitems))
    print('--------------ORDERING COST = ${}'.format(P.total_ordering_cost_allitems))
    print('--------------PENALTY COST = ${}'.format(P.total_penalty_cost_allitems))
    print('--------------OVERALL COST = ${}'.format(P.total_overall_cost_allitems))

# Command for execution
model()