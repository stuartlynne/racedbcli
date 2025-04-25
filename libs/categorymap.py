import sys

# map registered category to event category
localride_spring_series_map_categories = {

    "Elite Men Cat 1/2/3":         "Elite",
    "Elite Women Cat 1/2/3":       "Elite",
    "Men Cat 3":                    "Cat 3",
    "Men Cat 4":                    "Cat 4",
    "Master Men A":                 "Master A",
    "Men Novice / Cat 5":           "Cat 5",
    "Master Men B":                 "Master B",
    "Women Cat 3,4,5":              "Cat 3/4/5",

    "Open Cat 1,2,3":               "Elite",
    "Women Cat 1,2,3":              "Elite",
    "Men Master":                   "Master A", 
    "Men Cat 3, 4":                 "Cat 3",
    "Men Cat 4":                    "Cat 4",
    "Men Cat 5, Novice":            "Cat 5",
    "Women Cat 3, 4 , 5, Novice":   "Cat 3/4/5"
}

# map registered category to event category
thrashers_spring_series_map_categories = {
    "Cat 1/2 Men":                  "Elite",
    "Cat 1/2/3 Women":              "Elite",
    "Cat 3 Men":                    "Cat 3",
    "Cat 4 Men":                    "Cat 4",
    "Master Men":                   "Master A",
    "Men's Beer League 40+":        "Master B",
    "Open Men (Cat 5)":             "Cat 5",
    "Open Women (Cat 4)":           "Cat 3/4/5",
    "Youth Price":                  "Cat 5"

}

# check event category against license category
# check license, gender, age to get list of event categories allowed
spring_series_event_categories = [
        # License               Gender  (Min, Max),  Allowed_Categories
        ('Elite',               None,   (19,None),   ['Elite', ]),
        ('Under 23',            None,   (19,23),     ['Elite', ]),
        ('Master 35-44',        'M',    (35,44),     ['Master A', 'Master B', ]),
        ('Master 45-54',        'M',    (45,54),     ['Master A', 'Master B', ]),
        ('Master 55-64',        'M',    (55,64),     ['Master A', 'Master B', ]),
        ('Master 65+',          'M',    (65,None),   ['Master A', 'Master B', ]),

        ('Master 35-44',        'F',    (35,44),     ['Cat 3/4/5', ]),
        ('Master 45-54',        'F',    (45,54),     ['Cat 3/4/5', ]),
        ('Master 55-64',        'F',    (55,64),     ['Cat 3/4/5', ]),
        ('Master 65+',          'F',    (65,None),   ['Cat 3/4/5', ]),

        ('Cat 1',               'M',    (None, None),['Elite', ]),
        ('Cat 2',               'M',    (None, None),['Elite', ]),
        ('Cat 3',               'M',    (None, None),['Cat 3', ]),
        ('Cat 4',               'M',    (None, None),['Cat 4', ]),
        ('Cat 5',               'M',    (None, None),['Cat 5', ]),

        ('Cat 1',               'F',    (None, None),['Elite', ]),
        ('Cat 2',               'F',    (None, None),['Elite', ]),
        ('Cat 3',               'F',    (None, None),['Cat 3/4/5', ]),
        ('Cat 4',               'F',    (None, None),['Cat 3/4/5', ]),
        ('Cat 5',               'F',    (None, None),['Cat 3/4/5', ]),

        ('Junior',              'M',    (17, 18),    ['Elite', 'Cat 3', 'Cat 4', 'Cat 5'],),
        ('Youth',               'M',    (None, 16),    ['Cat 3', 'Cat 4', 'Cat 5'],),
        ('Under 17',            'M',    (15, 16),    ['Cat 3', 'Cat 4', 'Cat 5'],),
        ('Under 15',            'M',    (13, 14),    ['Cat 3', 'Cat 4', 'Cat 5'],),
        ('Under 13',            'M',    (None, 12),  ['Cat 3', 'Cat 4', 'Cat 5'],),
        ('Junior',              'F',    (17, 18),    ['Elite', 'Cat 3', 'Cat 4', 'Cat 5'],),
        ('Youth',               'F',    (None, 16),    ['Cat 3', 'Cat 4', 'Cat 5'],),
        ('Under 17',            'F',    (15, 16),    ['Cat 3', 'Cat 4', 'Cat 5'],),
        ('Under 15',            'F',    (13, 14),    ['Cat 4', 'Cat 5'],),
        ('Under 13',            'F',    (None, 12),  ['Cat 5'],),
        (None,                  None,   (20, None),  ['Novice', ]),
]

# Cycling BC 2025 Road
# Road :: Elite :: Cat 1'
# Road :: Under 23 :: Cat 1'
#
# Road :: Elite :: Cat 2'
# Road :: Master 45-54 :: Cat 2'
# Road :: Master 55-64 :: Cat 2'
#
# Road :: Elite :: Cat 3'
# Road :: Master 35-44 :: Cat 3'
# Road :: Under 23 :: Cat 3'
#
# Road :: Elite :: Cat 4'
# Road :: Junior :: Cat 4'
# Road :: Master 35-44 :: Cat 4'
# Road :: Master 45-54 :: Cat 4'
# Road :: Master 55-64 :: Cat 4'
# Road :: Under 23 :: Cat 4'
#
# Road :: Elite :: Cat 5'
# Road :: Junior :: Cat 5'
# Road :: Master 35-44 :: Cat 5'
# Road :: Master 45-54 :: Cat 5'
# Road :: Master 55-64 :: Cat 5'
# Road :: Youth :: Under 17 :: Cat 5'
#
# Road :: Youth :: Under 13'
# Road :: Youth :: Under 15'


thrashers_extras = [
        "RFID Timing Tag -", 
        "Junior W/M Pricing", 
        "Second Race Add On", 
        "THRASHERS T-Shirt - Small", 
        "THRASHERS T-Shirt - S", 
        "THRASHERS T-Shirt - Medium",
        "THRASHERS T-Shirt - M",
        "THRASHERS T-Shirt - Large", 
        "THRASHERS T-Shirt - L", 

        "Single Day License -", ]

# map registered category to event category
thrashers_map_categories = {
        "Elite Men":            "Elite",
        "Elite Women":          "Elite",
        "Master Men Elite":     "Master A",
        "Master Men A":     "Master A",
        "Men's Beer League":    "Master B",
        "Men's Beer B":    "Master B",
        "Master Men 55+":       "Master 55+",
        "Master Women":         "Master",
        "U17 Men":              "U17",
        "U15 Men":              "U15",
        "U13 Men":              "U13",
        "U17 Women":            "U17",
        "U15 Women":            "U15",
        "U13 Women":            "U13",

        "Intermediate Men":     "Intermediate",
        "Intermediate Women":   "Intermediate",
        "Novice Men":           "Novice",
        "Novice Women":         "Novice",
        "Youth Price":          "Youth",
}
# check license, gender, age to get list of event categories allowed
thrashers_cross_event_categories = [
        # License               Gender  (Min, Max),  Allowed_Categories
        ('Cat 5',               None,   (None, None),['Novice', ]),
        ('Cat 4',               None,   (None, 40),  ['Intermediate', ]),
        ('Cat 3',               None,   (None, None),['Intermediate',  ]),

        #(None,                  'M',    (35,None),   ['Master A', 'Master', ]),
        #(None,                  'F',    (35,None),   ['Master', ]),

        ('Elite',               'M',    (19,None),   ['Elite', ]),
        ('Elite',               'F',    (19,None),   ['Elite', ]),
        ('Under 23',            None,   (19,23),     ['Elite', ]),

        ('Master',              'M',    (35,44),     ['Elite', 'Master A', 'Master B', ]),
        ('Master',              'M',    (45,55),     ['Elite', 'Master A', 'Master B', ]),
        ('Master',              'M',    (55,None),   ['Master A', 'Master B', 'Master 55+', ],),

        ('Master',              'F',    (35,None),   ['Elite', 'Master', ]),

        ('Junior',              None,  (17, 18),    ['Elite', ]),
        ('Youth',               None,  (15, 16),    ['U17', ]),
        ('Youth',               None,  (13, 14),    ['U15', ]),
        ('Youth',               None,  (None, 12),  ['U13', ]),
        ('ANY',                 None,  (20, None),  ['Single Speed', ]),
        (None,                  None,  (20, None),  ['Novice', ]),
]
vanier_cross_extras = [ ]
vanier_map_categories = {
        "Novice Men Race no. 1": "Novice",           
        "U15 Men Race no. 1 or Class As Selected.": "U15",
        "U13 Mens Race no. 1 or Class As Selected.": "U13",
        "Youth Beginners Race no. 1": "Youth Beginners",

        "U17 Men Race no. 2 or Class As Selected.": "U17",
        "Intermediate Men Race no. 2": "Intermediate",

        "Masters Women Race no. 3": "Master",
        "U17 Women Race no. 3 or Class As Selected": "U17",
        "U15 Women Race no. 3 or Class As Selected": "U15",
        "U13 Women Race no. 3 or Class As Selected.": "U13",
        "Intermediate Women Race no. 3": "Intermediate",                                          

        "Masters B Men Race no. 4": "Master B",
        "Super Masters Men 55+ Race no. 4": "Master 55+",

        "Elite Men Race no. 5": "Elite",
        "Elite Women Race no. 5": "Elite",
        "Masters A Men Race no. 5": "Master A",
        "Novice Women Race no. 3": "Novice",                                                
        "Single Speed Race no. 2": "Single Speed",                                          
}

junkyard_cross_extras = [ 
                        "RFID Timing Tag - CAD $5 -", 
                         "Second Race Add On", 
                         "Second Race Add On    (enter 2nd race category in next section)",
                         "Second Race Add On (enter 2nd race category in next section)",
                         ]
junkyard_map_categories = {
        "Novice Men": "Novice",           
        "U15 Men": "U15",
        "U13 Men": "U13",
        "Novice Boys Discount Rate": "Youth Beginners",
        "Youth Beginner": "Youth Beginners",

        "U17 Men": "U17",
        "Intermediate Men (U19)": "Intermediate",
        "Intermediate Men": "Intermediate",
        "Intermediate Boys Discount Rate": "Intermediate",
        "Single Speed Men": "Single Speed",                                          
        "Single Speed Women": "Single Speed",                                          
        "Single Speed Men Add-On Price": "Single Speed",                                          
        "Single Speed Women Add-On Price": "Single Speed",                                          


        "Master 40+ Women": "Master",
        "U17 Women": "U17",
        "U15 Women": "U15",
        "U13 Women.": "U13",
        "Intermediate Women": "Intermediate",                                          
        "Intermediate Women (U19)": "Intermediate",                                          
        "Novice Women": "Novice",                                                
        "Novice Girls Discount Rate": "Novice",                                                

        "Master Men B 40+": "Master B",
        "Master C Men 55+": "Master 55+",

        "Elite Men": "Elite",
        "Elite Men U19": "Elite",
        "Elite Boys Discount Rate": "Elite",
        "Elite Women": "Elite",
        "Elite Girls Discount Rate": "Elite",
        "Elite Women U19": "Elite",
        "Master Men A 40+": "Master A",
}

pumpkin_cross_extras = [ 
                        "RFID Timing Tag - CAD $5 -", 
                        "Women's Clinic",
                         ]
pumpkin_map_categories = {
        "Novice Men": "Novice",           
        "Boys U15": "U15",
        "Boys U13": "U13",
        "Youth Beginner": "Youth Beginners",
        "Youth Beginners": "Youth Beginners",

        "Boys U17": "U17",
        "Intermediate Men (U19)": "Intermediate",
        "Intermediate Men": "Intermediate",
        "Single Speed Men Add-On Price": "Single Speed",                                          
        "Single Speed Women Add-On Price": "Single Speed",                                          
        "Single Speed Women": "Single Speed",                                          
        "Single Speed Men": "Single Speed",                                          

        "Master 40+ Women": "Master",
        "U17 Women": "U17",
        "Girls U15": "U15",
        "Girls U13": "U13",
        "Intermediate Girls Discount Rate": "Intermediate",                                          
        "Intermediate Boys Discount Rate": "Intermediate",                                          
        "Intermediate Women": "Intermediate",                                          
        "Intermediate Women (U19)": "Intermediate",                                          
        "Novice Women": "Novice",                                                
        "Novice Boys Discount Rate": "Novice",
        "Novice Girls Discount Rate": "Novice",

        'Junior':                       'Junior',
        "Master A Men 40+": "Master A",
        "Master B Men 40+": "Master B",
        "Master C Men 55+": "Master 55+",

        "Elite Men": "Elite",
        "Elite Men U19": "Elite",
        "Elite Boys Discount Rate": "Elite",
        "Elite Girls Discount Rate": "Elite",
        "Elite Women": "Elite",
        "Elite Women U19": "Elite",
}

vanier_cross_event_categories = [
        # License               Gender  (Min, Max),  Allowed_Categories
        ('Cat 5',               None,   (None, None),['Novice', ]),
        ('Cat 4',               None,   (None, 40),  ['Intermediate', ]),
        ('Cat 3',               None,   (None, None),['Intermediate',  ]),

        #(None,                  'M',    (35,None),   ['Master A', 'Master', ]),
        #(None,                  'F',    (35,None),   ['Master', ]),

        ('Elite',               'M',    (19,None),   ['Elite', ]),
        ('Elite',               'F',    (19,None),   ['Elite', ]),
        ('Under 23',            None,   (19,23),     ['Elite', ]),

        ('Master',              'M',    (35,44),     ['Elite', 'Master A', 'Master B', ]),
        ('Master',              'M',    (45,55),     ['Elite', 'Master A', 'Master B', ]),
        ('Master',              'M',    (55,None),   ['Master A', 'Master B', 'Master 55+', ],),

        ('Master',              'F',    (35,None),   ['Elite', 'Master', ]),

        ('Junior',              None,  (17, 18),    ['Elite', ]),
        ('Youth',               None,  (15, 16),    ['U17', ]),
        ('Youth',               None,  (13, 14),    ['U15', ]),
        ('Youth',               None,  (None, 12),  ['U13', ]),
        ('ANY',                 None,  (20, None),  ['Single Speed', ]),
        (None,                  None,  (None, 19),  ['Youth Beginners', ]),
        (None,                  None,  (20, None),  ['Novice', ]),
]



 
# Map the Registration Categories to the Event Categories
bcrrtt2024_map_categories = {
        'Elite Men':                            'Elite',
        'U23 Men':                              'U23',
        'Elite Women':                          'Elite',
        'U23 Women':                            'U23',
        'Master Men (A) 35-44':                 'Master A 35-44',
        'Master Men (B) 45-54':                 'Master B 45-54',
        'Master Men (C) 55-64':                 'Master C 55-64',
        'Master Men (D) 65+':                   'Master D 65+',
        'Junior Men U19':                       'Junior U19',
        'Cadet Men U17':                        'U17',
        'Master Women (A) 35-44':               'Master A 35-44',
        'Master Women (B) 45-54':               'Master B 45-54',
        'Master Women (C) 55-64':               'Master C/D 55+',
        'Junior Women U19':                     'Junior U19',
        'Women U17':                            'U17',
        'Open Men (non-championship)':          'Open',
        'Open Women (non-championship)':        'Open',
        'Open Youth A':                         'Open Youth A', 
        'Open Youth B':                         'Open Youth B',
        'Open Merckx Men (non-championship)':   'Open',
        'Open Merckx Women (non-championship)': 'Open Women',
}
# List of allowed categories based on License Category
provincial_event_categories = [
        # Age       Gender      (Min, Max), Event Categories
        ('Elite',    None,  (23,None),  ['Elite', 'Open', ]),
        ('Under 23', None,  (19,23),    ['U23', 'Open',]),
        ('Master',   None,  (35,44),    ['Master A 35-44', 'Open', ]),
        ('Master',   None,  (45,54),    ['Master B 45-54', 'Open', ]),
        ('Master',   'M',   (55,64),    ['Master C 55-64', 'Open', ]),
        ('Master',   'M',   (65,None),  ['Master D 65+', 'Open', ]),
        ('Master',   'F',   (55,64),    ['Master C/D 55+', 'Open', ]),
        ('Master',   'F',   (55,64),    ['Master C/D 55+', 'Open', ]),
        ('Junior',   'M',   (17, 18),   ['Junior U19', 'Open Men', ]),
        ('Junior',   'F',   (17, 18),   ['Junior U19', 'Open Women', ]),
        ('Youth',    'M',   (15, 16),   ['Cadet U17', 'Open Men']),
        ('Youth',    'F',   (15, 16),   ['Cadet U17', 'Open Women']),
        ('Youth',    None,  (None, 13), ['Open Youth A', 'Open Youth B']),
        (None,       None,  (None, 19), ['Open Youth A', 'Open Youth B']),
        (None,       None,  (20, None), ['Open', ]),
]

# ###############################################################################################################################################3

bc_cx_2024_map_categories = {
        'Elite Men':                            'Elite',
        'Elite Women':                          'Elite',
        'Men U23':                              'Under 23',
        'Women U23':                            'Under 23',
        'Master Men 35-44':                     'Master 35-44',
        'Master Women 35-44':                   'Master 35-44',
        'Master Men 45-54':                     'Master 45-54',
        'Master Women 45-55':                   'Master 45-54',
        'Master Women 45-54':                   'Master 45-54',
        'Master Men 55-64':                     'Master 55-64',
        'Master Women 55-64':                   'Master 55-64',
        'Master Men 65+':                       'Master 65+',
        'Master Women 65+':                     'Master 65+',
        'Junior Men U19':                       'Junior',
        'Junior Women U19':                     'Junior',
        'Men U17':                              'Under 17',
        'Men U15':                              'Under 15',
        'Men U13':                              'Under 13',
        'Women U17':                            'Under 17',
        'Women U15':                            'Under 15',
        'Women U13':                            'Under 13',
        'Open Men':                             'Open',
        'Open Women':                           'Open',
        'Single Speed Men':                     'Single Speed',
        'Single Speed Women':                   'Single Speed',
}
bc_cx_event_categories = [
        # Requested       Gender      (Min, Max), Event Categories
        #('Open',        None,  (None, None),   ['Open', ]),
        #('Single Speed',None, (None, None),    ['Single Speed', ]),
        ('Elite',       None,  (23,None),      ['Elite', 'Open', 'Single Speed', ]),
        ('Under 23',         None,  (19,22),   ['Under 23', 'Elite', 'Open', 'Single Speed',]),
        ('Master',      None,  (35,44),        ['Master 35-44', 'Open', 'Single Speed', ]),
        ('Master',      None,  (45,54),        ['Master 45-54', 'Open', 'Single Speed', ]),
        ('Master',      None,   (55,64),       ['Master 55-64', 'Open', 'Single Speed', ]),
        ('Master',      None,   (65,None),     ['Master 65+', 'Open', 'Single Speed', ]),
        ('Junior',      None,  (15, 18),       ['Junior', 'Open', 'Single Speed', ]),
        ('Under 17',    None,  (13, 16),       ['Under 17','Open', 'Single Speed', ]),
        ('Under 15',    None,  (13, 14),       ['Under 15','Open', 'Single Speed', ]),
        ('Under 13',    None,  (None, 12),     ['Under 13', ]),
]

bc_cx_extras = [
        "RFID Timing Tag -", 
        "THRASHERS T-Shirt - Small", 
        "THRASHERS T-Shirt - S", 
        "THRASHERS T-Shirt - Medium",
        "THRASHERS T-Shirt - M",
        "THRASHERS T-Shirt - Large", 
        "THRASHERS T-Shirt - L", 
        "THRASHERS T-Shirt - XL", 

        "Single Day License -", ]

class CategoryMap:

    def __init__(self, organizer="thrashers", event_type="Road", ):

        self.event_type = event_type

        match event_type:
            case 'Road':
                match organizer:
                    case 'localride':
                        self.extras = pumpkin_cross_extras
                        self.map_categories = localride_spring_series_map_categories 
                        self.event_categories = spring_series_event_categories 
                    case 'thrashers':
                        self.extras = thrashers_extras
                        self.map_categories = thrashers_spring_series_map_categories 
                        self.event_categories = spring_series_event_categories 
            case 'Cyclocross':
                match organizer:
                    case 'thrashers':
                        self.extras = thrashers_cross_extras
                        self.map_categories = thrashers_map_categories
                        self.event_categories = thrashers_cross_event_categories
                    case 'vanier':
                        self.extras = vanier_cross_extras
                        self.map_categories = vanier_map_categories
                        self.event_categories = vanier_cross_event_categories
                    case 'junkyard':
                        self.extras = junkyard_cross_extras
                        self.map_categories = junkyard_map_categories
                        self.event_categories = vanier_cross_event_categories
                    case 'localride':
                        self.extras = pumpkin_cross_extras
                        self.map_categories = pumpkin_map_categories
                        self.event_categories = vanier_cross_event_categories
                    case 'provincials':
                        self.extras = []
                        self.map_categories = bcrrtt2024_map_categories
                        self.event_categories = [( age, gender, 
                                    (min_age if min_age is not None else None, max_age if max_age is not None else None), 
                                    categories)
                                for age, gender, (min_age, max_age), categories in bc_cx_event_categories ]


    def get_requested_category(self, registered_category):
        requestedCategory = ' '.join(registered_category.split()).replace('"', '')
        if requestedCategory in self.extras:
            return False, requestedCategory

        return True, self.map_categories.get(requestedCategory, f"{requestedCategory} NOT FOUND")




    def get_event_category(self, license_categories, gender, age, event_categories=None):
        #if not race_category:
        #    return None
        #licenses = license_categories.get('Road', [None])

        licenses = license_categories.get(self.event_type, [None])
        print('  get_event_category: license: %s gender: %s age: %s' % ( licenses, gender, age), file=sys.stderr)

        #if licenses is None:
        #    licenses = [None]

        allowed_categories = []
        for license in licenses:
            print('License: %s' % license, file=sys.stderr)
            #for category, allowedGender, (min_age, max_age), event_category in self.event_categories:
            for event_requirements in self.event_categories:
                print('----------------', file=sys.stderr)
                print(f"Event Requirements: {event_requirements}", file=sys.stderr)
                category, allowedGender, (min_age, max_age), event_category = event_requirements
                print(f"Category: checking {category} {allowedGender} min:{min_age} max:{max_age} {event_categories}", file=sys.stderr)
                #if category and not license:
                #    continue
                if allowedGender and allowedGender != gender:
                    #print(f"Gender {allowedGender} != {gender}", file=sys.stderr)
                    continue
                if category == 'ANY':
                    #allowed_categories.extend([for x in event_category if x not in allowed_categories])
                    allowed_categories.extend(x for x in event_category if x not in allowed_categories)
                    continue
                if license and category and license != category:
                    print(f"Category {license} != {category}", file=sys.stderr)
                    continue
                if age and min_age and int(age) < min_age:
                    print(f"Age age:{age} < min_age:{min_age}", file=sys.stderr)
                    continue
                if age and max_age and int(age) > max_age:
                    print(f"Age age:{age} > max_age:{max_age}", file=sys.stderr)
                    continue
                print(f"Category: extending {event_category}", file=sys.stderr)
                if event_category:
                    #allowed_categories.extend(for x in event_category if x not in allowed_categories)
                    allowed_categories.extend(x for x in event_category if x not in allowed_categories)

        return allowed_categories, {self.event_type: licenses}

