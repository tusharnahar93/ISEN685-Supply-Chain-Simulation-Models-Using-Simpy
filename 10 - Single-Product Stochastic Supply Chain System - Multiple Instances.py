'''STOCHASTIC SINGLE PRODUCT SUPPLY CHAIN SYSTEM - MULTIPLE INSTANCES'''

import random
import simpy
import numpy
import os
import pandas
import scipy.stats

n=10 # no of repetitions
confidence=0.95 #confidence level 
# Change the location of the data file in the following line
os.chdir('C:/Users/gvish/Desktop/ISEN 685/FINAL FILES')
x1=pandas.ExcelFile('Single-Product Data File.xlsx')
df1=x1.parse('Sheet1')
df2=x1.parse('Sheet3')


class P:
    # SPECIFY THE SIMULATION TIME(RUN TIME) IN DAYS
    simulationTimeMax = 61
    '''This is the Parameter Class with different parameters viz. Store order size, Re-order Point, 
    Order Upto Qty, Initial Inventory, Unit Manufacturing Cost, Ordering Cost, Unit Holding Cost, 
    Unit Penalty Cost, Lead Time, and a few corresponding global variables which have to be calculated
    viz. On Order Qty, Total and Satisfied Demand, Total costs, Total inventories etc.'''
    ROP_DC = df1.iat[0,df1.columns.get_loc("ReorderPoint_DC")]
    Order_Upto=df1.iat[0,df1.columns.get_loc("Order_Upto_Qty")]
    Initial_Inv_DC=df1.iat[0,df1.columns.get_loc("Initial_Inventory_DC")]
    # flag1 is used to calculate the total number of customers
    flag1 = 0
    # flag2 is used to calculate the total number of unsatisfied customers
    flag2=0
    on_order=0
    Inv = None
    total_demand=0
    satisfied_demand=0
    ordering_cost = df1.iat[0,df1.columns.get_loc("Ordering_cost")]
    unit_manufacturing_cost=df1.iat[0,df1.columns.get_loc("Manufacturing_Cost (Per Unit)")]
    unit_holding_cost=df1.iat[0,df1.columns.get_loc("Holding_Cost (Per Unit per time period)")]
    unit_penalty_cost=df1.iat[0,df1.columns.get_loc("Penalty_Cost (per unit)")]
    total_ordering_cost=0
    total_holding_cost=0
    total_penalty_cost=0
    total_overall_cost=0
    no_orders=0
    tot_inv=0
    units_manufactured=0
    distribution_leadtime=df2.iat[df2.loc[df2['Parameter']=='LeadTime(Days)'].index[0],1]
    a_leadtime=df2.iat[df2.loc[df2['Parameter']=='LeadTime(Days)'].index[0],2]
    b_leadtime=df2.iat[df2.loc[df2['Parameter']=='LeadTime(Days)'].index[0],3]
    c_leadtime=df2.iat[df2.loc[df2['Parameter']=='LeadTime(Days)'].index[0],4]
    distribution_manufacturingtime =df2.iat[df2.loc[df2['Parameter']=='ManufacturingTime(Minutes)'].index[0],1]
    a_manufacturingtime=df2.iat[df2.loc[df2['Parameter']=='ManufacturingTime(Minutes)'].index[0],2]
    b_manufacturingtime=df2.iat[df2.loc[df2['Parameter']=='ManufacturingTime(Minutes)'].index[0],3]
    c_manufacturingtime=df2.iat[df2.loc[df2['Parameter']=='ManufacturingTime(Minutes)'].index[0],4]
    distribution_demand = df2.iat[df2.loc[df2['Parameter']=='Demand'].index[0],1]
    a_demand=df2.iat[df2.loc[df2['Parameter']=='Demand'].index[0],2]
    b_demand=df2.iat[df2.loc[df2['Parameter']=='Demand'].index[0],3]
    c_demand=df2.iat[df2.loc[df2['Parameter']=='Demand'].index[0],4]
    distribution_processingtime = df2.iat[df2.loc[df2['Parameter']=='ProcessingTime(Minutes)'].index[0],1]
    a_processingtime=df2.iat[df2.loc[df2['Parameter']=='ProcessingTime(Minutes)'].index[0],2]
    b_processingtime=df2.iat[df2.loc[df2['Parameter']=='ProcessingTime(Minutes)'].index[0],3]
    c_processingtime=df2.iat[df2.loc[df2['Parameter']=='ProcessingTime(Minutes)'].index[0],4]
    servicelevel_type1=0
    servicelevel_type2=0
    sl1=[]
    sl2=[]
    thc=[]
    toc=[]
    tpc=[]
    tovc=[]


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
        self.lead_time=distribution(P.distribution_leadtime,P.a_leadtime,P.b_leadtime,P.c_leadtime)
        P.on_order+=qty
        manufacturing_time=0
        P.total_ordering_cost+=P.ordering_cost+qty*P.unit_manufacturing_cost
        P.units_manufactured+=qty
        for i in range(qty):
            manufacturing_time+=distribution(P.distribution_manufacturingtime,P.a_manufacturingtime,P.b_manufacturingtime,P.c_manufacturingtime)
        manufacturing_time=manufacturing_time/(24*60)
        yield self.env.timeout(manufacturing_time)
        yield self.env.timeout(self.lead_time)
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
        self.demand=distribution(P.distribution_demand,P.a_demand,P.b_demand,P.c_demand)            
        P.total_demand+=self.demand
    def ordertoDC (self) :
        '''This is the DC order generating function. This fuction places orders to the DC. If the DC
        inventory level is lesser than the order quantity, partial fulfillment of the order takes place
        and the customer is unsatisfied. If the inventory is 0, customer leaves empty handed and is 
        unsatisfied.Otherwise, the customer waits for a processing time duration and receives the order
        and is satisfied.'''
        print('Time {1}: {0} places order of {2} to DC'.format(self.name ,self.env.now, self.demand))
        if P.Inv.DC_inv.level<self.demand :
            if P.Inv.DC_inv.level==0:
                print('Time {1}: {0} leaves empty handed'.format(self.name,self.env.now))
                P.total_penalty_cost+=self.demand*P.unit_penalty_cost
            else:
                processing_time=0
                for i in range(self.demand-P.Inv.DC_inv.level):
                    processing_time+=distribution(df2.iat[df2.loc[df2['Parameter']=='ProcessingTime(Minutes)'].index[0],1],df2.iat[df2.loc[df2['Parameter']=='ProcessingTime(Minutes)'].index[0],2],df2.iat[df2.loc[df2['Parameter']=='ProcessingTime(Minutes)'].index[0],3],df2.iat[df2.loc[df2['Parameter']=='ProcessingTime(Minutes)'].index[0],4])
                processing_time=processing_time/(24*60)
                yield self.env.timeout(processing_time)
                print('Time {1}: {0} receives only {2} units'.format(self.name,self.env.now,P.Inv.DC_inv.level))
                P.total_penalty_cost+=(self.demand-P.Inv.DC_inv.level)*P.unit_penalty_cost
                P.satisfied_demand+=P.Inv.DC_inv.level
                yield P.Inv.DC_inv.get(P.Inv.DC_inv.level)
            P.flag2=P.flag2+1
        else:
            processing_time=0
            for i in range(self.demand):
                processing_time+=distribution(P.distribution_processingtime,P.a_processingtime,P.b_processingtime,P.c_processingtime)
            processing_time=processing_time/(24*60)
            yield self.env.timeout(processing_time)
            P.satisfied_demand+=self.demand
            yield P.Inv.DC_inv.get(self.demand)
            print('Time {1}: {0} receives order from DC'.format(self.name , self.env.now))
                
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
            P.total_holding_cost+=P.Inv.DC_inv.level*P.unit_holding_cost
            P.tot_inv+=P.Inv.DC_inv.level
            DCOrderGenerator(self.env,name='Store')

def distribution(dist,a,b,c):
    '''This function created a dictionary that matches the option selected in the drop-down menu of the
    excel file to the distribution.'''
    switcher = {
            "Uniform(a=LowestValue b=HighestValue)": random.uniform(a,b),
            "Triangular(a=LowestValue b=HighestValue c=MostLikelyValue)":random.triangular(a,b,c),
            "Poisson(a=MeanValue)":numpy.random.poisson(a)
            }
    return switcher.get(dist,0)            

'''This is a functon used to calculate  the confidence interval for an array for a given confidence level. 
The confidence level is calculated using the t-distribution with n-1 degrees of freedom. Where n are the number of
data points'''
def confidence_intervals(data, confidence=0.95): 
    n = len(data)
    m, se = numpy.mean(data), scipy.stats.sem(data)
    n = se * scipy.stats.t._ppf((1+confidence)/2., n-1)
    return m-n, m+n

def model(randomSeed) :
    '''This is the executable body of the program. It creates and environment and calls the Store and 
    Inventory classes. Duration of the run is controlled here. It prints all the desired data.'''
    random.seed(randomSeed)
    numpy.random.seed(randomSeed)
    envr = simpy.Environment()
    Store(envr)
    P.Inv = Inventory(envr)  
    envr.run(until = P.simulationTimeMax)
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
    P.servicelevel_type1=((P.flag1-P.flag2)*100/P.flag1)
    P.servicelevel_type2=((P.satisfied_demand)*100/P.total_demand)
    
    """ The following performance metrics are the return values for the model
    """
    return P.servicelevel_type1,P.servicelevel_type2,P.total_holding_cost,P.total_ordering_cost,P.total_penalty_cost,P.total_overall_cost 

# Command for execution
"""
The model is run multiple times and the performance measure are stored in the array
"""
for i in range(n):
    sl01,sl02,thc,toc,tpc,tovc=model(i) 
    P.flag1=0
    P.flag2=0
    P.on_order=0
    P.total_demand=0
    P.satisfied_demand=0
    P.servicelevel_type1=0
    P.servicelevel_type2=0
    P.total_holding_cost=0
    P.total_ordering_cost=0
    P.total_penalty_cost=0
    P.total_overall_cost=0
    P.sl1.append(sl01)
    P.sl2.append(sl02)
    P.thc.append(thc)
    P.toc.append(toc)
    P.tpc.append(tpc)
    P.tovc.append(tovc)

print('Type 1 Service Level : {}'.format(P.sl1))
print('Type 2 Service Level : {}'.format(P.sl2))

avg_sl1_l,avg_sl1_r=confidence_intervals(P.sl1,confidence)
avg_sl2_l,avg_sl2_r=confidence_intervals=confidence_intervals(P.sl2,confidence)

'''The following are the average values obtained from multiple repitions'''

print('The average Type 1 service level over {0} repetition is {1}%'.format(n,numpy.mean(P.sl1)))
print('The average Type 2 service level over {0} repetition is {1}%'.format(n,numpy.mean(P.sl2)))
print('The average total holding cost over {0} repetition is ${1}'.format(n,numpy.mean(P.thc)))
print('The average total ordering cost over {0} repetition is ${1}'.format(n,numpy.mean(P.toc)))
print('The average total penalty cost over {0} repetition is ${1}'.format(n,numpy.mean(P.tpc)))
print('The average total overall cost over {0} repetition is ${1}'.format(n,numpy.mean(P.tovc)))

print('The confidence interval for type 1 service level is [{0},{1}]'.format(avg_sl1_l,avg_sl1_r))
print('The confidence interval for type 1 service level is [{0},{1}]'.format(avg_sl2_l,avg_sl2_r))