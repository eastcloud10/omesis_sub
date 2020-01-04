import pysubs2
import re
from auto_sub import find_type_file

def del_empty(subs):
    for line in subs:
        if not re.search('\w',line.text):
            subs.remove(line)
    return subs
    
def del_duplicate(subs):
    for line in subs:
        for line2 in subs:
            if line is not line2:
                if line.start == line2.start and line.end == line2.end and line.text == line2.text:
                    print("del dupl:"+str(line.start))
                    subs.remove(line2)
    return subs
    
def continued_line(subs):
    for line in subs:
        for line2 in subs:
            if line is not line2:
                if line.end == line2.start and line.text == line2.text:
                    line2.start = line.start
                    subs.remove(line)
    return subs

ass_name = find_type_file(".ass")
subs = pysubs2.load(ass_name)
subs = del_empty(subs)
subs = del_duplicate(subs)
subs = continued_line(subs)
subs.save("[clean]"+ass_name)
input()