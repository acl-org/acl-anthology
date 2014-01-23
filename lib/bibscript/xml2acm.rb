require "rexml/document"
include REXML

def authorNames(names)
	result = ""
	for i in 0..names.size-1 do
		result += names[i]
		if i != (names.size() - 1)
			result += ", "
		end
		if i == names.size - 2
			result += "and "
		end
	end
	return result
end

def editorNames(names)
	result = ""
	for i in 0..names.size-1 do
		result += names[i] + "(Ed.)"
		if i != (names.size() - 1)
			result += ", "
		end
		if i == names.size - 2
			result += "and "
		end
	end
	return result
end

fileName = ARGV[0]
document = Document.new File.new(fileName)

multiple = XPath.first(document, "//modsCollection")

acm = ""

if not multiple
	volume = document.elements["mods/relatedItem/titleInfo/title"].text
	title = document.elements["mods/titleInfo/title"].text
	names = []
	document.elements.each("mods/name") do |element|
		names.push(element.elements["namePart[@type='given']"].text + " " + element.elements["namePart[@type='family']"].text)
	end

	date = document.elements["mods/originInfo/dateIssued"].text
	url = document.elements["mods/location/url"]
	startPage = document.elements["part/extent/start"]
	endPage = document.elements["part/extent/end"]

	acm += "#{authorNames(names)}. #{date}. #{title}. "
	acm += "In <em>#{volume}</em>. "
	# acm += publisher, address
	# if startPage and endPage
	# 	acm += "#{startPage}-#{endPage}. "
	# end
	if url != nil
		acm += url.text
	end
else
	volume_title = document.elements["modsCollection/titleInfo/title"].text
	names = []
	document.elements.each("modsCollection/name") do |element|
		names.push(element.elements["namePart[@type='given']"].text + " " + element.elements["namePart[@type='family']"].text)
	end
	date = document.elements["modsCollection/originInfo/dateIssued"].text
	#url = document.elements["mods/location/url"]

	acm += "#{editorNames(names)}. #{date}. <em>#{volume_title}</em>. "
end

puts acm