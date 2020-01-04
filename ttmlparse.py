import xml.etree.ElementTree as ET
import pysubs2
from auto_sub import find_type_file

ttmlname = find_type_file('.ttml')
tree = ET.parse(ttmlname)
root = tree.getroot()
styles = root[0][0]
captions = root[1][0]
sublist = []
styledict = dict()

towritesubs = pysubs2.SSAFile()
for styling in styles:
    color = styling.get(u'{http://www.w3.org/ns/ttml#styling}color')
    stylename = styling.get(u'{http://www.w3.org/XML/1998/namespace}id')
    if color:
        if color == "white":
            r = 255
            g = 255
            b = 255
            a = 0
        elif color == "black":
            r = 0
            g = 0
            b = 0
            a = 0    
        else:        
            r = int(styling.get(u'{http://www.w3.org/ns/ttml#styling}color')[1:3],16)
            g = int(styling.get(u'{http://www.w3.org/ns/ttml#styling}color')[3:5],16)
            b = int(styling.get(u'{http://www.w3.org/ns/ttml#styling}color')[5:7],16)
            a = 0
        styledict[stylename] = (pysubs2.SSAStyle(primarycolor=pysubs2.Color(r=r,g=g,b=b,a=a)))


for line in captions:
    start = pysubs2.time.timestamp_to_ms(pysubs2.time.TIMESTAMP.match(line.get('begin')).groups())
    end = pysubs2.time.timestamp_to_ms(pysubs2.time.TIMESTAMP.match(line.get('end')).groups())
    if len(list(line))==0:
        print('------')
        text = line.text
        style = line.get('style')
        sublist.append(pysubs2.SSAEvent(start=start,end=end,text=text,style=style))
    else:
        for sentence in line:
            text = sentence.text
            style = sentence.get('style')
            sublist.append(pysubs2.SSAEvent(start=start,end=end,text=text,style=style))
towritesubs.events = sublist
towritesubs.styles=styledict



towritesubs.save(ttmlname + '.ass')

