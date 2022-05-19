## This file shall define the mappings between the device identifier and the respective elements
## (buses/lines/transformers) measured.
BUS = 0
LINE = 1
TRANSFORMER = 2
UNKNOWN = -1

# Single Substation Configuration
modbus_unit_number_mappings = {
0: {'element': LINE, 'idx': 0},
1: {'element': BUS,  'idx': 0},
2: {'element': LINE, 'idx': 4},
3: {'element': BUS,  'idx': 1},
4: {'element': LINE, 'idx': 1},
5: {'element': BUS,  'idx': 4},
6: {'element': LINE, 'idx': 2},
7: {'element': BUS,  'idx': 5},
8: {'element': LINE, 'idx': 3},
9: {'element': BUS,  'idx': 2},
10:{'element': BUS,  'idx': 3},
11:{'element': LINE, 'idx': 5},
12:{'element': BUS,  'idx': 6},
13:{'element': LINE, 'idx': 6},
14:{'element': BUS,  'idx': 7},
15:{'element': LINE, 'idx': 10},
16:{'element': BUS,  'idx': 8},
17:{'element': BUS,  'idx': 9},
18:{'element': LINE, 'idx': 7},
19:{'element': BUS,  'idx': 10},
20:{'element': LINE, 'idx': 8},
21:{'element': BUS,  'idx': 11},
22:{'element': LINE, 'idx': 9},
23:{'element': BUS,  'idx': 12},
24:{'element': LINE, 'idx': 11},
25:{'element': BUS,  'idx': 13},
26:{'element': LINE, 'idx': 12},
27:{'element': BUS,  'idx': 14},
28:{'element': LINE, 'idx': 13},
29:{'element': BUS,  'idx': 15},
30:{'element': TRANSFORMER, 'idx': 0},
31:{'element': TRANSFORMER, 'idx': 1}
}

# Define mapping between line/switch index and circuit breaker name here. This is purely for visualization.
load_elements_line_cb_name = {
0:"CB-10", 4:"CB-20", 3:"CB-100", 1:"CB-11", 2:"CB-12", 5:"CB-22", 6:"CB-21", 7:"CB-31", 8:"CB-32", 9:"CB-33", 11:"CB-41", 12:"CB-42", 13:"CB-43"
}


# ------------------------------Extension Stations------------------------------------------
# 3 Substations Configuration
modbus_unit_number_mappings.update({
# Substation 2
32: {'element': LINE, 'idx': 14},
33: {'element': BUS,  'idx': 20},
34: {'element': LINE, 'idx': 15},
35: {'element': BUS,  'idx': 21},
36: {'element': LINE, 'idx': 16},
37: {'element': BUS,  'idx': 22},
38: {'element': LINE, 'idx': 17},
39: {'element': BUS,  'idx': 23},
40: {'element': LINE, 'idx': 18},
41: {'element': BUS,  'idx': 24},
42:{'element': LINE, 'idx': 19},
43:{'element': BUS,  'idx': 25},
44:{'element': LINE, 'idx': 20},
45:{'element': BUS,  'idx': 26},
46:{'element': LINE, 'idx': 21},
47:{'element': BUS,  'idx': 27},
48:{'element': TRANSFORMER, 'idx': 2},
49:{'element': TRANSFORMER, 'idx': 3},

# Substation 3
50: {'element': LINE, 'idx': 22},
51: {'element': BUS,  'idx': 28},
52: {'element': LINE, 'idx': 23},
53: {'element': BUS,  'idx': 29},
54: {'element': LINE, 'idx': 24},
55: {'element': BUS,  'idx': 30},
56: {'element': LINE, 'idx': 25},
57: {'element': BUS,  'idx': 31},
58:{'element': TRANSFORMER, 'idx': 4},
59:{'element': TRANSFORMER, 'idx': 5},
})

# Define mapping between line/switch index and circuit breaker name here. This is purely for visualization.
#load_elements_line_cb_name.update({
#})
