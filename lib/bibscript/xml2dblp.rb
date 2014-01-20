require "rexml/document"

fileName = ARGV[0]
document = REXML::Document.new File.new(fileName)
volume = document.elements["mods/relatedItem/titleInfo/title"].text
title = document.elements["mods/titleInfo/title"].text
names = []
document.elements.each("mods/name") do |element|
	names.push(element.elements["namePart[@type='given']"].text + " " + element.elements["namePart[@type='family']"].text)
end

def printNames(names)
	result = ""
	for i in 0..names.size-1 do
		result += names[i]
		if i != (names.size() -1)
			result += ", "
		end
	end
	result
end


date = document.elements["mods/originInfo/dateIssued"].text

# output = REXML::Document.new
# h2 = output.add_element "h2"
# h2.text = volume + ", " + date
# ul = output.add_element "ul"
# li = ul.add_element "li"
# li.text = printNames(names) + ":\n" +title + "."+"\n"+"0--0-"

# puts output.to_s 

output = ""
output += "<h2>#{volume}, #{date}</h2>\n"
output += "<ul>\n<li>#{printNames(names)}:\n#{title}.\n 0--0-\n</ul>"
puts output