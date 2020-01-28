import pysubs2
import os
import re
from auto_sub import find_type_file

ASS_FILENAME = find_type_file('.ass')
subs = pysubs2.load(ASS_FILENAME, encoding="utf-8")
for line in subs:
    if re.search("^YZ：",line.text):
        line.style = "ray字幕"
        line.text = re.search("(?<=：)\S+",line.text).group(0)
    elif re.search("^OZ：",line.text):
        line.style = "rio字幕"
        line.text = re.search("(?<=：)\S+",line.text).group(0)
    elif re.search("^O：",line.text):
        line.style = "rio1通常"
        line.text = re.search("(?<=：)\S+",line.text).group(0)
    elif re.search("^Y：",line.text):
        line.style = "ray1通常"
        line.text = re.search("(?<=：)\S+",line.text).group(0)
    elif re.search("^Z：",line.text):
        line.style = "加厚边框注释"
        line.text = re.search("(?<=：)\S+",line.text).group(0)     
            
subs.save('ass_'+ASS_FILENAME, encoding="utf-8")