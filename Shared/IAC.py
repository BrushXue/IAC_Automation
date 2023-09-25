"""
(Purpose) IAC.py is a module that contains functions used in the IAC report
"""


def degree_days(ZIP: str, mode: str, Tbase: int=65, history: int=4) -> float:
    """
    Automatically calculate degree days based on daily average temperature
    The result should be equal to degreedays.net
    :param ZIP: ZIP code as string
    :param mode: "heating" or "cooling" as string
    :param Tbase (optional): Base temperature as integer, default is 65 (degF)
    :param history (optional): Number of years of historical data as integer, default is 4
    :return: Degree days as float
    """
    # if ZIP code is invalid
    if ZIP.isdigit() == False:
        raise Exception("ZIP code must be 5 digits")
    if len(ZIP) != 5:
        raise Exception("ZIP code must be 5 digits")
    
    # select mode or throw error
    if mode == "cooling":
        sign = 1
    elif mode == "heating":
        sign = -1
    else:
        raise Exception("Mode must be 'heating' or 'cooling'")
    
    # if temp is not an integer between 32 and 212 degF
    if type(Tbase) != int:
        raise Exception("Base temperature must be an integer")
    if Tbase < 32 or Tbase > 212:
        raise Exception("Base temperature must be between 32 and 212 degF")
    
    # if history is not a positive integer between 1 and 5
    if type(history) != int:
        raise Exception("History must be a integer")
    if history < 1 or history > 5:
        raise Exception("History must be between 1 and 5")
    
    data = weather_data(ZIP, "daily", history)

    data['degreeday'] = data.apply(lambda x: max((x['tavg'] - Tbase) * sign, 0), axis=1)
    degreedays = data.degreeday.sum() / history
    return degreedays

def degree_hours(ZIP: str, mode: str, basetemp: int=65, setback: int=None, schedule: tuple=((9,17),)*5+((0,0),)*2, history: int=4) -> float:
    """
    Automatically calculate degree hours based on hourly data
    The result is usually higher than degreedays.net
    :param ZIP: ZIP code as string
    :param mode: "heating" or "cooling" as string
    :param basetemp (optional): Base temperature as integer, default is 65 degF
    :param setback (optional): Setback temperature as integer, default is None (eqauls to base temperature)
    :param schedule (optional): Weekly operating hours as a tuple of 7 tuples of 2 integers, default is 9am-5pm, Mon.-Fri. 
    For example, ((0,24),(0,24),(0,24),(9,17),(9,17),(0,0),(0,0)) is 24 hrs, Mon-Wed, 9am-5pm, Thu-Fri, holiday, Sat-Sun
    :param history (optional): Number of years of historical data as integer, default is 4
    :return: Degree hours as float
    """
    # if ZIP code is invalid
    if ZIP.isdigit() == False:
        raise Exception("ZIP code must be 5 digits")
    if len(ZIP) != 5:
        raise Exception("ZIP code must be 5 digits")
    
    # select mode or throw error
    if mode == "cooling":
        sign = 1
    elif mode == "heating":
        sign = -1
    else:
        raise Exception("Mode must be 'heating' or 'cooling'")
    
    # if basetemp is not an integer between 32 and 212 degF
    if type(basetemp) != int:
        raise Exception("Base temperature must be an integer")
    if basetemp < 32 or basetemp > 212:
        raise Exception("Base temperature must be between 32 and 212 degF")
    
    # if setback is provided
    if setback != None:
        if type(setback) != int:
            raise Exception("Setback temperature must be an integer")
        if setback < 32 or setback > 212:
            raise Exception("Setback temperature must be between 32 and 212 degF")
    else:
        setback = basetemp

    # Validate schedule
    if type(schedule) != tuple:
        raise Exception("Schedule must be a tuple")
    if len(schedule) != 7:
        raise Exception("Schedule must be a tuple of 7 tuples")
    for i in range(7):
        if type(schedule[i]) != tuple:
            raise Exception("Schedule must be a tuple of 7 tuples")
        if len(schedule[i]) != 2:
            raise Exception("Schedule must be a tuple of 7 tuples of 2 integers")
        if type(schedule[i][0]) != int or type(schedule[i][1]) != int:
            raise Exception("Schedule must be a tuple of 7 tuples of 2 integers")
        if schedule[i][0] < 0 or schedule[i][1] > 24:
            raise Exception("Invalid schedule")
        if schedule[i][0] > schedule[i][1]:
            raise Exception("Operating hours must be earlier than closing hours")
        
    # if history is not a positive integer between 1 and 5
    if type(history) != int:
        raise Exception("History must be a integer")
    if history < 1 or history > 5:
        raise Exception("History must be between 1 and 5")

    data = weather_data(ZIP, "hourly", history)
    data['Tbase'] = basetemp
    data['day'] = data.index.dayofweek
    data['hour'] = data.index.hour
    for day in range(7):
        data.loc[(data['day'] == day) & (data['hour'] < schedule[day][0]), 'Tbase'] = setback
        data.loc[(data['day'] == day) & (data['hour'] >= schedule[day][1]), 'Tbase'] = setback
    data['degreehour'] = data.apply(lambda x: max((x['temp'] - x['Tbase'])*sign, 0), axis=1)
    degreehours = data.degreehour.sum() / history
    return degreehours

def weather_data(ZIP, mode: str, history: int):
    """
    Get raw weather data from meteostat
    :param ZIP: ZIP code as string
    :param mode: "daily" or "hourly" as string
    :param history: Number of years of historical data as integer
    :return: Pandas DataFrame
    """
    from meteostat import Point, Hourly, Daily, units
    from datetime import datetime
    import numpy, pgeocode

    # Get coordinate from ZIP code
    location = pgeocode.Nominatim('us').query_postal_code(ZIP)
    # Invalid ZIP code
    if numpy.isnan(location.latitude) or numpy.isnan(location.longitude):
        raise Exception("ZIP code not found")
    Point.method = 'nearest'
    plant = Point(location.latitude, location.longitude)

    # Get daily data from history to 2022
    # As of Sep 2023, most stations doesn't have daily data after Apr 2022.
    starttime = datetime(2023 - history, 1, 1)
    endtime = datetime(2022, 12, 31, 23, 59)

    # fetch data
    if mode == "daily":
        data = Daily(plant, starttime, endtime)
    elif mode == "hourly":
        data = Hourly(plant, starttime, endtime)
    else:
        raise Exception("Mode must be 'daily' or 'hourly'")
    data.convert(units.imperial)
    data.normalize()
    # https://github.com/meteostat/meteostat-python/issues/130
    #data = data.interpolate()
    data = data.fetch()
    return data

def validate_arc(ARC):
    """
    Validate ARC input
    :param ARC: Full ARC number as a string
    """
    # json5 is too slow, use json instead.
    import os, json
    # Validate if ARC is in x.xxxx.xxx format
    ARCsplit = ARC.split('.')
    if len(ARCsplit) != 3:
        raise Exception("ARC number must be in x.xxxx.x format")
    # if ARC split are nut full numbers
    for i in range(len(ARCsplit)):
        if ARCsplit[i].isdigit() == False:
            raise Exception("ARC number must be in x.xxxx.x format")
    
    # Parse ARC code
    code = ARCsplit[0] + '.' + ARCsplit[1]
    # Read ARC.json5 as dictionary
    arc_path = os.path.dirname(os.path.abspath(__file__))
    ARCdict = json.load(open(os.path.join(arc_path, 'ARC.json')))
    desc = ARCdict[code]
    if desc == None:
        print("ARC code not found.")
    else:
        print(code + ": "+ desc)

    # Parse application code
    app = ARCsplit[2]
    if app == '1':
        print("Application code 1: Manufacturing Process")
    elif app == '2':
        print("Application code 2: Process Support")
    elif app == '3':
        print("Application code 3: Building and Grounds")
    elif app == '4':
        print("Application code 4: Administrative")
    else:
        print("Application code not found.")

    print("")

def grouping_num(dic: dict) -> dict:
    """
    Add thousand separator to numbers in a dictionary and format it to string
    :param dic: EasyDict
    :return: Dictionary with keys in thousand separator
    """
    import locale
    # set locale to US
    locale.setlocale(locale.LC_ALL, 'en_US')
    for key in dic.keys():
        if type(dic[key]) == int:
            dic[key] = locale.format_string('%d', dic[key], grouping=True)
        elif type(dic[key]) == float:
            dic[key] = locale.format_string('%g', dic[key], grouping=True)
        else:
            pass
    return dic

def dollar(varlist: list, dic: dict, digits: int=0) -> str:
    """
    Format numbers in a dictionary and to currency string
    :param varlist: List of keys in the dictionary
    :param dic: EasyDict
    :param digits: Number of digits, default is 0
    :return: Dictionary with keys in formatted currency string
    """
    import locale
    # if varlist is not a list of strings
    if type(varlist) != list:
        raise Exception("Variable list must be a list of strings")
    for var in varlist:
        if type(var) != str:
            raise Exception("Variable list must be a list of strings")
        if var not in dic.keys():
            raise Exception("Variable not found in dictionary")
    # if digits is not a natural number
    if type(digits) != int:
        raise Exception("Digits must be a natural number")
    if digits < 0:
        raise Exception("Digits must be a natural number")
    # set locale to US
    locale.setlocale(locale.LC_ALL, 'en_US')
    locale._override_localeconv={'frac_digits':digits}
    for var in varlist:
        dic[var] = locale.currency(dic[var], grouping=True)
    return dic

def combine_words(words: list) -> str:
    """
    :param words: list of strings
    :return: string of words separated by "," and "and"
    """
    # if words is not a list
    if type(words) != list:
        raise Exception("Input must be a list of strings")
    combined = ""
    for i in range(len(words)):  
        # if word is not a string
        if type(words[i]) != str:
            raise Exception("Input must be a list of strings")
        combined = combined + words[i]    
        if i < len(words) - 2:
            combined = combined + ', '
        if i == len(words) - 2:
            combined = combined + ' and ' 
        else:
            pass
    return combined

def add_image(doc, tag: str, image_path: str, wd):
    """
    Add image to Word document, search for tag in doc and replace with the image
    :param doc: Document
    :param tag: Image tag as string
    :param image_path: Path to the image as string
    :param wd: Image width
    :return: None
    """
    import os
    # if tag is not a string
    if type(tag) != str:
        raise Exception("Tag must be a string")
    # if image file is not found
    if os.path.isfile(image_path) == False:
        raise Exception("Image file not found")
    found_tag = False
    for p in doc.paragraphs:
        if tag in p.text:
            p.text = p.text.replace(tag, '')
            r = p.add_run()
            r.add_picture(image_path, width=wd)
            found_tag = True
            break
    if found_tag == False:
        # Throw error if tag is not found 
        raise Exception("Tag "+ tag +" not found")

def add_eqn(doc, tag: str, eqn_input):
    """
    Add equation to Word document, search for eqn in doc and replace with eqn_input
    :param doc: Document
    :param tag: Equation tag as string
    :param eqn_input: Word Equation object
    :return: None
    """
    # if tag is not a string
    if type(tag) != str:
        raise Exception("Tag must be a string")
    found_tag = False
    for p in doc.paragraphs:
        if tag in p.text:
            p.text = p.text.replace(tag, '')
            word_math = latex2word(eqn_input)
            p._element.append(word_math)
            found_tag = True
            break
    if found_tag == False:
        # Throw error if tag is not found 
        raise Exception("Tag "+ tag +" not found")
def latex2word(latex_input: str):
    """
    Convert LaTeX equation to Word equation
    :param latex_input: LaTeX equation as a string
    :return: Word equation object
    """
    import os, latex2mathml.converter
    from lxml import etree
    #if latex input is not a string
    if type(latex_input) != str:
        raise Exception("LaTeX equation must be a string")
    mathml = latex2mathml.converter.convert(latex_input)
    tree = etree.fromstring(mathml)
    script_path = os.path.dirname(os.path.abspath(__file__))
    xslt = etree.parse(os.path.join(script_path,'..','Shared','MML2OMML.XSL'))
    transform = etree.XSLT(xslt)
    new_dom = transform(tree)
    return new_dom.getroot()

def payback(ACS: float, IC: float) -> str:
    """
    Format payback period by year and month
    :param ACS: Annual Cost Savings ($/yr) as float
    :param IC: Implementation Cost ($) as float
    :return: formatted Payback Period as string
    """
    import math
    # if ACS or IC is not a number
    if type(ACS) != int and type(ACS) != float:
        raise Exception("Annual Cost Savings must be a number")
    if type(IC) != int and type(IC) != float:
        raise Exception("Implementation Cost must be a number")
    PB = IC / ACS
    if PB <= 11.0 / 12.0:
        PB = math.ceil(PB * 12.0)
        PBstr = str(PB) + " month"
    else:
        PB = math.ceil(PB * 10.0) / 10.0
        PBstr = str(PB).rstrip("0").rstrip(".") + " year"
    if PB > 1.0:
        PBstr = PBstr + "s"
    return PBstr