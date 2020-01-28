import pysubs2
import os
import re
from auto_sub import find_type_file

print("请选择自动轴（提供字幕帧）：")
a = find_type_file('.ass')
print(a)
auto_ASS = pysubs2.load(a)
print("请选择合并轴(文本与所有时轴)：")
merged_ASS = pysubs2.load(find_type_file('.ass'))

for auto_line in auto_ASS:
    for normal_line in merged_ASS:
        if abs(auto_line.start - normal_line.start)<300:
            oldstart = normal_line.start
            normal_line.start = auto_line.start
            normal_line.style = auto_line.style
            for normal_line2 in merged_ASS:
                if normal_line2.end == oldstart:
                    normal_line2.end = normal_line.start
            break

        if abs(auto_line.end - normal_line.end)<300 :
            oldend = normal_line.end
            normal_line.end = auto_line.end
            normal_line.style = auto_line.style
            for normal_line2 in merged_ASS:
                if normal_line2.start == oldend:
                    normal_line2.start = normal_line.end
            break
            

merged_ASS.save("【自动校正】.ass")
            