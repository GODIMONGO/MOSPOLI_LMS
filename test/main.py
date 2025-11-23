import xml.etree.ElementTree as ET

tree = ET.parse("C:\\Users\\dbdgd\\pd\\test\\task-list.svg")
root = tree.getroot()

for elem in root.iter():
    if "stroke" in elem.attrib:
        elem.set("stroke", "#00FF00")   # новый цвет

tree.write("new.svg")
