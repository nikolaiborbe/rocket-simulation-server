#Rocket parameters, for importing into main.py
#REMINDER: The coordinate system begins at the tip of the rocket, aka the nosetip. Every length in this file is
#          measured from the top of the rocket.


import numpy as np

############### General Parameters ###############

#General parameters
rocket_length = 5.085 #m
rocket_radius = 0.1225 #m
center_gravity = 2.98 #m  (from the top of the rocket)
dry_total_mass = 93.8 #kg

#Inertia
inertia_xx = 0.711 #kg*m^2
inertia_yy = 1631.815 #kg*m^2
inertia_zz = 1631.786 #kg*m^2
inertia_xy = -0.059 #kg*m^2
inertia_xz = -0.117 #kg*m^2
inertia_yz = -0.01 #kg*m^2

#Nosecone (including the nosetip)
nose_length = 0.8 #m
nose_type = "Von Karman"

#Fins
fin_beta = 63 #degrees
fin_span = 0.18 #m 
rootchord = 0.28 #m
tipchord = 0.14 #m
amount = 4 #number of fins
fin_position = 4.797 #m
cant_angle = 0 #degrees <--- we are not canting the fins

#Rail buttons
button_1 = 1.915 #m
button_2 = 0.3 #m
#button_3 = 0 #m <-- add this if we go for radax LL.

############### Tanks Parameters ###############
ambient_temp = 20

#Oxidizer
ox_length = 1.079 #m
ox_inner_radius = 0.0645 #m
ox_outer_radius = 0.115 #m
ox_eff_radius = np.sqrt(ox_inner_radius**2 + ox_outer_radius**2) #m
ox_pressure = 30 #bar
ox_volume = 27 #liters, remember this is 90% of actual tank volume
ox_temp = -20 #celsius
ox_position = 1.415 #m from bottom of the rocket to the center of the tank for some damn reason
ox_density = 998 #kg/m^3
ox_mass = ox_density * ox_volume * 0.001 #kg, assumes ox volume is in liters, converts to m^3


#Fuel
fuel_length = 1.171 #m
fuel_inner_radius = 0 #m
fuel_outer_radius = 0 #m
fuel_eff_radius = 0.06 #m
fuel_pressure = 35 #bar
fuel_volume = 13*0.9 #liters
fuel_temp = ambient_temp #celsius
fuel_position = 1.415 #m from bottom of the rocket to the center of the tank for some damn reason
fuel_density = 818 #kg/m^3, assumes 90% ethanol, 10% water by mass. this should be changed to calculate based on fuel composition and not just assume a density.
fuel_mass = fuel_density * fuel_volume * 0.001 #kg, assumes fuel volume is in liters, converts to m^3

#Fuel composition
ethanol_perc = 90 #as a percentage, i.e. write 70% as 70
water_perc = 10 #same as above

#N2
n2_length = 0.55 #m
n2_radius = 0.104 #m
temp_inital = ambient_temp #celsius
n2_volume = 12 #liters
temp_final = ambient_temp #celsius
n2_position = 2.94 #m from bottom of the rocket to the center of the tank for some damn reason
n2_pressure = 280 #bar
n2_mass = 3.6 #kg

############### Burn Parameters ###############
massflowrate = 4.3 #kg/s
OF_ratio = 3 #just a number, ratio. 

############### Chute Parameters ###############
#Drogue
drogue_cd = 1.5 #number
drogue_area = 1.4775 #m^2
drogue_cds = drogue_cd * drogue_area #cd * area
drogue_cord_lag = 0.2 #seconds
drogue_inflation_lag = 0.3 #seconds
drogue_total_lag = 0.5 #seconds
drogue_trigger = 0 #m/s, wtf is this?
drogue_sampling_rate = 105 #hz

#Main - WARNING WARNING WARNING THESE VALUES ARE PLACEHOLDERS FROM HEIMDALL, PLEASE ADD IN UNREEFED VALUES ONCE WE HAVE THEM!!!!!!!!!!!!!
main_cd = 2.2 #number
main_area = 13.858 #m^2
main_cds = 30.4876 #number, wtf is this?
main_cord_lag = 2.5 #seconds
main_inflation_lag = 2.5 #seconds
main_total_lag = 5 #seconds
main_trigger = 600 #m/s, wtf is this?
main_sampling_rate = 105 #hz

############### Launch Site and Rail Parameters ###############
#Site
latitude = 63.786667 #coordinates for Tarva
longitude = 9.363056 #coordinates for Tarva
max_expected_height = 12000 #m
elevation = 20 #m, launch site, meters over sea
map_size = 10000 #m

#Rail
rail_length = 12 #m
inclination = 82 #degrees, 0 is parallel to the horizon, i.e. flat.
heading = 225 #degrees on a compass

############### Files Parameters ###############
thrust_curve_file = "inputs/Estimated_thrust_curve_24.2.2026.csv"
atmosphere_file = "inputs/tarva_26_6_2024.nc"
drag_off_file = "inputs/drag.offH.csv"
drag_on_file = "inputs/drag.on.csv"
acceleration_output_file = "output/acceleration_data.csv"
kml_output_file = "flightpath.kml"