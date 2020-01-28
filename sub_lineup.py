import pysubs2
from auto_sub import find_type_file

print("油管轴（提供时间）：\n")
ytb_sub = pysubs2.load(find_type_file('.ass'))
print("翻译文本（提供文本）：\n")
translate_sub = pysubs2.load(find_type_file('.ass'))

for i in range(len(ytb_sub)):
    ytb_sub[i].text = translate_sub[i].text
    
ytb_sub.save("【合并的】.ass")